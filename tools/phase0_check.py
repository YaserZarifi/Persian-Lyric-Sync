"""Phase 0 smoke test: does this ffmpeg's libass shape Persian correctly?

Renders one PNG per tricky line onto a flat background. Inspect the PNGs by eye:
joined letters, right-to-left order, ZWNJ half-spaces, mixed Persian/Latin/digits, wrapping.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lyricvid.ass import build_ass  # noqa: E402
from lyricvid.ffmpeg import find_tool  # noqa: E402
from lyricvid.models import FONTS_DIR, ROOT, Line, StylePreset  # noqa: E402

SAMPLES = [
    "برام هیچ حسی شبیه تو نیست",                      # plain joining
    "می‌خواهم نیم‌فاصله‌ها درست بمانند",               # ZWNJ
    "آهنگ Naborde Ranj از سال ۱۴۰۳ و 2024",            # mixed scripts + digits
    "تمامِ قلبِ تو؛ به من نمی رسه… همین که فکرمی؛ برای من بسه! و این خط باید بشکند",  # wrap
]


def main() -> None:
    out_dir = ROOT / "output" / "phase0"
    out_dir.mkdir(parents=True, exist_ok=True)
    style = StylePreset()
    lines = [Line(t, i * 2 + 0.0, i * 2 + 1.9) for i, t in enumerate(SAMPLES)]
    wd = Path(tempfile.mkdtemp(prefix="phase0_"))
    try:
        (wd / "t.ass").write_text(build_ass(lines, style, (1920, 1080)), encoding="utf-8")
        (wd / "fonts").mkdir()
        shutil.copy2(FONTS_DIR / style.font_file, wd / "fonts")
        for i in range(len(SAMPLES)):
            out = out_dir / f"sample_{i}.png"
            subprocess.run(
                [find_tool("ffmpeg"), "-hide_banner", "-loglevel", "warning", "-y",
                 "-f", "lavfi", "-i", "color=c=0x3a4a6a:s=1920x1080:r=30",
                 "-vf", f"setpts=PTS+{i * 2 + 1.0}/TB,subtitles=t.ass:fontsdir=fonts",
                 "-frames:v", "1", "-update", "1", str(out)],
                cwd=wd, check=True,
            )
            print(out)
    finally:
        shutil.rmtree(wd, ignore_errors=True)


if __name__ == "__main__":
    main()
