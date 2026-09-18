"""ffmpeg/ffprobe helpers: probing, filter graph, rendering with progress."""
from __future__ import annotations

import functools
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
from .models import Project, StylePreset, resolve_font

ASS_NAME = "lyrics.ass"
FONTS_SUBDIR = "fonts"
BG_NAME = "bg.png"
WM_NAME = "watermark.png"

# Hide console windows spawned from the GUI on Windows.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def find_tool(name: str) -> str:
    override = os.environ.get(f"LYRICVID_{name.upper()}")
    path = override or shutil.which(name)
    if not path:
        raise FileNotFoundError(f"{name} not found on PATH (or set LYRICVID_{name.upper()})")
    return path


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, creationflags=_NO_WINDOW)


def probe_duration(path: str | Path) -> float:
    out = subprocess.run(
        [find_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True, creationflags=_NO_WINDOW,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def probe_size(path: str | Path) -> tuple[int, int]:
    out = subprocess.run(
        [find_tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", str(path)],
        capture_output=True, text=True, check=True, creationflags=_NO_WINDOW,
    ).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"])


@functools.lru_cache(maxsize=1)
def nvenc_available() -> bool:
    try:
        _run([find_tool("ffmpeg"), "-hide_banner", "-v", "error", "-f", "lavfi",
              "-i", "color=s=256x256", "-frames:v", "1", "-c:v", "h264_nvenc", "-f", "null", "-"])
        return True
    except Exception:  # noqa: BLE001 - no NVIDIA GPU/driver: use the CPU encoder
        return False


class RenderCancelled(Exception):
    pass


def _supersample(project: Project, style: StylePreset) -> float:
    """Ken Burns crops a moving window; render the source larger so it stays sharp."""
    if style.ken_burns == "off":
        return 1.0
    return 2.0 if project.export.size[1] <= 1440 else 1.25


@dataclass
class Workdir:
    """Temp dir holding lyrics.ass, fonts/, the prepared background and watermark.

    Relative paths inside it mean filter args need no Windows path escaping. Static work
    (scaling a 4K photo, dimming, blurring) happens once here instead of on every frame.
    A Workdir can be kept and re-synced (the GUI preview does this).
    """
    path: Path
    _bg_key: tuple | None = None
    _wm_key: tuple | None = None
    logo_size: tuple[int, int] | None = None

    @classmethod
    def create(cls) -> "Workdir":
        wd = cls(Path(tempfile.mkdtemp(prefix="lyricvid_")))
        (wd.path / FONTS_SUBDIR).mkdir()
        return wd

    @classmethod
    def prepare(cls, project: Project, duration: float | None = None) -> "Workdir":
        wd = cls.create()
        wd.sync(project, duration)
        return wd

    def sync(self, project: Project, duration: float | None = None) -> None:
        style = project.resolved_style()
        self._sync_background(project, style)
        self._sync_watermark(project, style)
        logo_h = self.logo_size[1] if self.logo_size else 0
        (self.path / ASS_NAME).write_text(project_to_ass(project, duration, logo_h),
                                          encoding="utf-8")
        font_src = resolve_font(style.font_file)
        dest = self.path / FONTS_SUBDIR / font_src.name
        if font_src.exists() and not dest.exists():
            shutil.copy2(font_src, dest)

    def _sync_background(self, project: Project, style: StylePreset) -> None:
        bg = Path(project.background_path).resolve()
        ss = _supersample(project, style)
        key = (str(bg), bg.stat().st_mtime, project.export.resolution, ss,
               style.bg_dim, style.bg_blur)
        if key == self._bg_key:
            return
        w, h = project.export.size
        sw, sh = round(w * ss / 2) * 2, round(h * ss / 2) * 2
        chain = [f"scale={sw}:{sh}:force_original_aspect_ratio=increase:flags=lanczos",
                 f"crop={sw}:{sh}", "setsar=1", "format=rgb24"]
        if style.bg_blur > 0:
            chain.append(f"gblur=sigma={style.bg_blur * sh / 1080:.2f}")
        if style.bg_dim > 0:
            m = max(0.0, 1.0 - min(style.bg_dim, 1.0))
            chain.append(f"colorchannelmixer=rr={m:.3f}:gg={m:.3f}:bb={m:.3f}")
        _run([find_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-i", str(bg),
              "-vf", ",".join(chain), "-frames:v", "1", "-update", "1", BG_NAME], cwd=self.path)
        self._bg_key = key

    def _sync_watermark(self, project: Project, style: StylePreset) -> None:
        src = Path(style.watermark_image) if style.watermark_image else None
        if not src or not src.exists():
            self.logo_size, self._wm_key = None, None
            (self.path / WM_NAME).unlink(missing_ok=True)
            return
        key = (str(src), src.stat().st_mtime, project.export.resolution,
               style.watermark_scale, style.watermark_opacity)
        if key == self._wm_key:
            return
        w = round(project.export.size[0] * max(0.02, style.watermark_scale) / 2) * 2
        op = max(0.0, min(1.0, style.watermark_opacity))
        _run([find_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
              "-vf", f"scale={w}:-2:flags=lanczos,format=rgba,colorchannelmixer=aa={op:.3f}",
              "-frames:v", "1", "-update", "1", WM_NAME], cwd=self.path)
        self.logo_size = probe_size(self.path / WM_NAME)
        self._wm_key = key

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def _ken_burns(style: StylePreset, project: Project, duration: float) -> str:
    w, h = project.export.size
    a = max(0.0, style.ken_burns_amount)
    p = f"clip(it/{max(duration, 0.1):.3f}\\,0\\,1)"
    z, x = {
        "zoom_in": (f"1+{a}*{p}", "(iw-iw/zoom)/2"),
        "zoom_out": (f"1+{a}*(1-{p})", "(iw-iw/zoom)/2"),
        "pan_left": (f"{1 + a}", f"(iw-iw/zoom)*{p}"),
        "pan_right": (f"{1 + a}", f"(iw-iw/zoom)*(1-{p})"),
    }[style.ken_burns]
    return (f"zoompan=z={z}:x={x}:y=(ih-ih/zoom)/2:d=1:s={w}x{h}"
            f":fps={project.export.fps}")


def _overlay_xy(style: StylePreset, project: Project) -> str:
    m = round(40 * project.export.size[1] / 1080)
    x = f"{m}" if style.watermark_position.endswith("left") else f"W-w-{m}"
    y = f"{m}" if style.watermark_position.startswith("top") else f"H-h-{m}"
    return f"x={x}:y={y}"


def filter_graph(project: Project, wd: Workdir, duration: float, t: float | None = None) -> str:
    """Background (+Ken Burns) -> logo -> lyrics. `t` renders a single preview frame."""
    style = project.resolved_style()
    shift = f"setpts=PTS+{t:.3f}/TB" if t is not None else ""
    if t is None:
        # Decode the still once and repeat it in memory; -loop 1 would re-decode the
        # (up to 4K) PNG for every output frame.
        steps = ["loop=loop=-1:size=1", f"setpts=N/({project.export.fps}*TB)"]
    else:
        steps = [shift]
    if style.ken_burns != "off":
        steps.append(_ken_burns(style, project, duration))
        if shift:  # zoompan restarts timestamps; libass needs the real time again
            steps.append(shift)
    graph = "[0:v]" + ",".join(steps) + "[bg]"
    base = "[bg]"
    if wd.logo_size:
        graph += f";[bg][1:v]overlay={_overlay_xy(style, project)}:format=auto[wm]"
        base = "[wm]"
    graph += f";{base}subtitles={ASS_NAME}:fontsdir={FONTS_SUBDIR},format=yuv420p[v]"
    return graph


def encoder_args(project: Project) -> tuple[list[str], str]:
    enc = project.export.encoder
    style = project.resolved_style()
    w, h = project.export.size
    if enc == "gpu" or (enc == "auto" and nvenc_available()):
        rate = max(8, round(25 * w * h / (1920 * 1080)))
        return (["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr",
                 "-cq", "19", "-b:v", "0", "-maxrate", f"{rate}M", "-bufsize", f"{2 * rate}M",
                 "-profile:v", "high"], "GPU (NVENC)")
    args = ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]
    if style.ken_burns == "off":
        args += ["-tune", "stillimage"]
    return args, "CPU (x264)"


def render_cmd(
    project: Project, wd: Workdir, out_path: str | Path, duration: float, progress: bool = False
) -> tuple[list[str], str]:
    """Full render; must run with cwd set to the prepared Workdir."""
    fps = project.export.fps
    enc, enc_name = encoder_args(project)
    cmd = [find_tool("ffmpeg"), "-hide_banner", "-y", "-i", BG_NAME]
    if wd.logo_size:
        cmd += ["-i", WM_NAME]
    audio_idx = 2 if wd.logo_size else 1
    cmd += ["-i", str(Path(project.audio_path).resolve()),
            "-filter_complex", filter_graph(project, wd, duration),
            "-map", "[v]", "-map", f"{audio_idx}:a:0",
            *enc, "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{duration:.3f}", "-movflags", "+faststart"]
    if progress:
        cmd += ["-progress", "pipe:1", "-nostats"]
    cmd.append(str(Path(out_path).resolve()))
    return cmd, enc_name


def frame_cmd(project: Project, wd: Workdir, t: float, duration: float, out_path: str | Path) -> list[str]:
    """Single preview frame; must run with cwd set to the prepared Workdir."""
    cmd = [find_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-i", BG_NAME]
    if wd.logo_size:
        cmd += ["-i", WM_NAME]
    return cmd + ["-filter_complex", filter_graph(project, wd, duration, t), "-map", "[v]",
                  "-frames:v", "1", "-update", "1", str(Path(out_path).resolve())]


def render_frame(
    project: Project, t: float, out_path: str | Path,
    workdir: Workdir | None = None, duration: float | None = None,
) -> None:
    if duration is None:
        duration = probe_duration(project.audio_path) if project.audio_path else max(t + 1, 60)
    wd = workdir or Workdir.create()
    try:
        wd.sync(project, duration)
        _run(frame_cmd(project, wd, t, duration, out_path), cwd=wd.path)
    finally:
        if workdir is None:
            wd.cleanup()


def render_video(
    project: Project,
    out_path: str | Path,
    on_progress: Callable[[float], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> str:
    """Render the MP4; returns the encoder used."""
    duration = probe_duration(project.audio_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wd = Workdir.prepare(project, duration)
    try:
        cmd, enc_name = render_cmd(project, wd, out_path, duration, progress=True)
        proc = subprocess.Popen(
            cmd, cwd=wd.path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
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
        return enc_name
    finally:
        wd.cleanup()


def parse_progress_line(line: str, duration: float) -> float | None:
    key, _, value = line.strip().partition("=")
    if key in ("out_time_us", "out_time_ms") and value.lstrip("-").isdigit() and duration > 0:
        # Despite its name, out_time_ms is also in microseconds.
        return min(max(int(value) / 1e6 / duration, 0.0), 1.0)
    return None
