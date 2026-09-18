"""ffmpeg/ffprobe helpers: probing, command building, running with progress."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .ass import project_to_ass
from .models import FONTS_DIR, Project

ASS_NAME = "lyrics.ass"
FONTS_SUBDIR = "fonts"
BG_NAME = "bg.png"

# Hide console windows spawned from the GUI on Windows.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def find_tool(name: str) -> str:
    override = os.environ.get(f"LYRICVID_{name.upper()}")
    path = override or shutil.which(name)
    if not path:
        raise FileNotFoundError(f"{name} not found on PATH (or set LYRICVID_{name.upper()})")
    return path


def probe_duration(path: str | Path) -> float:
    out = subprocess.run(
        [find_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True, creationflags=_NO_WINDOW,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


class RenderCancelled(Exception):
    pass


@dataclass
class Workdir:
    """Temp dir holding lyrics.ass, fonts/ and the pre-scaled background.

    Relative paths inside it mean filter args need no Windows path escaping, and
    scaling the background once avoids re-decoding a 4K image for every frame.
    A Workdir can be kept and re-synced (the GUI preview does this).
    """
    path: Path
    _bg_key: tuple | None = None

    @classmethod
    def create(cls) -> "Workdir":
        wd = cls(Path(tempfile.mkdtemp(prefix="lyricvid_")))
        (wd.path / FONTS_SUBDIR).mkdir()
        return wd

    @classmethod
    def prepare(cls, project: Project) -> "Workdir":
        wd = cls.create()
        wd.sync(project)
        return wd

    def sync(self, project: Project) -> None:
        bg = Path(project.background_path).resolve()
        key = (str(bg), bg.stat().st_mtime, project.export.resolution)
        if key != self._bg_key:
            subprocess.run(
                [find_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
                 "-i", str(bg), "-vf", _background_chain(project),
                 "-frames:v", "1", "-update", "1", BG_NAME],
                cwd=self.path, check=True, capture_output=True, creationflags=_NO_WINDOW,
            )
            self._bg_key = key
        (self.path / ASS_NAME).write_text(project_to_ass(project), encoding="utf-8")
        font_src = Path(project.resolved_style().font_file)
        if not font_src.is_absolute():
            font_src = FONTS_DIR / font_src
        dest = self.path / FONTS_SUBDIR / font_src.name
        if font_src.exists() and not dest.exists():
            shutil.copy2(font_src, dest)

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def _background_chain(project: Project) -> str:
    w, h = project.export.size
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={w}:{h},setsar=1")


def _subs_filter() -> str:
    return f"subtitles={ASS_NAME}:fontsdir={FONTS_SUBDIR}"


def render_cmd(
    project: Project, out_path: str | Path, duration: float, progress: bool = False
) -> list[str]:
    """Full render; must run with cwd set to a prepared Workdir."""
    fps = project.export.fps
    vf = f"[0:v]{_subs_filter()},format=yuv420p[v]"
    cmd = [
        find_tool("ffmpeg"), "-hide_banner", "-y",
        "-loop", "1", "-framerate", str(fps), "-i", BG_NAME,
        "-i", str(Path(project.audio_path).resolve()),
        "-filter_complex", vf, "-map", "[v]", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "stillimage",
        "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{duration:.3f}", "-movflags", "+faststart",
    ]
    if progress:
        cmd += ["-progress", "pipe:1", "-nostats"]
    cmd.append(str(Path(out_path).resolve()))
    return cmd


def frame_cmd(project: Project, t: float, out_path: str | Path) -> list[str]:
    """Single preview frame; must run with cwd set to a prepared Workdir."""
    # Shift the still's timestamp to t so libass renders the lyric active at t.
    vf = f"setpts=PTS+{t:.3f}/TB,{_subs_filter()}"
    return [
        find_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
        "-i", BG_NAME,
        "-vf", vf, "-frames:v", "1", "-update", "1", str(Path(out_path).resolve()),
    ]


def render_frame(
    project: Project, t: float, out_path: str | Path, workdir: Workdir | None = None
) -> None:
    wd = workdir or Workdir.create()
    try:
        wd.sync(project)
        subprocess.run(frame_cmd(project, t, out_path), cwd=wd.path, check=True,
                       capture_output=True, creationflags=_NO_WINDOW)
    finally:
        if workdir is None:
            wd.cleanup()


def render_video(
    project: Project,
    out_path: str | Path,
    on_progress: Callable[[float], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    duration = probe_duration(project.audio_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wd = Workdir.prepare(project)
    try:
        proc = subprocess.Popen(
            render_cmd(project, out_path, duration, progress=True), cwd=wd.path,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=_NO_WINDOW,
        )
        stderr_tail: list[str] = []

        def drain() -> None:
            for line in proc.stderr:  # type: ignore[union-attr]
                stderr_tail.append(line)
                del stderr_tail[:-40]

        threading.Thread(target=drain, daemon=True).start()
        for line in proc.stdout:  # type: ignore[union-attr]
            if cancelled and cancelled():
                proc.kill()
                proc.wait()
                Path(out_path).unlink(missing_ok=True)
                raise RenderCancelled()
            frac = parse_progress_line(line, duration)
            if frac is not None and on_progress:
                on_progress(frac)
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed:\n" + "".join(stderr_tail))
        if on_progress:
            on_progress(1.0)
    finally:
        wd.cleanup()


def parse_progress_line(line: str, duration: float) -> float | None:
    key, _, value = line.strip().partition("=")
    if key in ("out_time_us", "out_time_ms") and value.lstrip("-").isdigit() and duration > 0:
        # Despite its name, out_time_ms is also in microseconds.
        return min(max(int(value) / 1e6 / duration, 0.0), 1.0)
    return None
