"""Command line: build a project from raw inputs, render a frame, render the video."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .ffmpeg import probe_duration, render_frame, render_video
from .lyrics import read_lyrics_file, spread_evenly
from .sync import auto_time
from .models import Project


def cmd_init(a: argparse.Namespace) -> None:
    duration = probe_duration(a.audio)
    parsed = read_lyrics_file(a.lyrics_txt)
    if a.spread:
        lines, source = spread_evenly(parsed, duration), "spread evenly"
    else:
        r = auto_time(a.audio, [t for t in parsed if t], duration, online=not a.offline)
        lines, source = r.lines, r.source
    project = Project(
        audio_path=str(Path(a.audio).resolve()),
        background_path=str(Path(a.bg).resolve()),
        style_preset=a.preset,
        lines=lines,
    )
    project.save(a.output)
    print(f"{len(project.lines)} lines over {duration:.1f}s ({source}) -> {a.output}")


def cmd_frame(a: argparse.Namespace) -> None:
    render_frame(Project.load(a.project), a.t, a.output)
    print(a.output)


def cmd_render(a: argparse.Namespace) -> None:
    project = Project.load(a.project)
    if a.preset:
        project.style_preset = a.preset
    last = -1

    def progress(frac: float) -> None:
        nonlocal last
        pct = int(frac * 100)
        if pct != last:
            last = pct
            print(f"\r{pct:3d}%", end="", flush=True)

    render_video(project, a.output, progress)
    print(f"\n{a.output}")


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="lyricvid")
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("init", help="create a project JSON with automatic first-pass timing")
    s.add_argument("--audio", required=True)
    s.add_argument("--lyrics-txt", required=True)
    s.add_argument("--bg", required=True)
    s.add_argument("--preset", default="default-bold-outline")
    s.add_argument("--offline", action="store_true", help="skip the LRCLIB lookup")
    s.add_argument("--spread", action="store_true", help="spread lines evenly, no auto-timing")
    s.add_argument("-o", "--output", required=True)
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("frame", help="render one preview frame at time t")
    s.add_argument("project")
    s.add_argument("--t", type=float, required=True)
    s.add_argument("-o", "--output", required=True)
    s.set_defaults(func=cmd_frame)

    s = sub.add_parser("render", help="render the full MP4")
    s.add_argument("project")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--preset")
    s.set_defaults(func=cmd_render)

    a = p.parse_args(argv)
    a.func(a)
