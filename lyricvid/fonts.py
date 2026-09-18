"""Font discovery: bundled and user-added TTF/OTF files and the names libass needs."""
from __future__ import annotations

import functools
import shutil
from pathlib import Path

from .models import USER_FONTS_DIR, font_dirs

FONT_SUFFIXES = {".ttf", ".otf"}


@functools.lru_cache(maxsize=64)
def _info(path: str, mtime: float) -> tuple[str, int]:
    from fontTools.ttLib import TTFont

    font = TTFont(path, lazy=True, fontNumber=0)
    names = {(r.nameID, r.platformID): r.toUnicode() for r in font["name"].names
             if r.nameID in (1, 4)}
    # Legacy family (name ID 1) is what libass matches an ASS Fontname against.
    family = names.get((1, 3)) or names.get((1, 1)) or Path(path).stem
    weight = font["OS/2"].usWeightClass if "OS/2" in font else 400
    return family, weight


def font_info(path: str | Path) -> tuple[str, int]:
    """(ASS family name, weight class) for a font file."""
    p = Path(path)
    return _info(str(p), p.stat().st_mtime)


def list_fonts() -> list[dict]:
    out, seen = [], set()
    for d in font_dirs():
        if not d.exists():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix.lower() in FONT_SUFFIXES and p.name not in seen:
                try:
                    family, weight = font_info(p)
                except Exception:  # noqa: BLE001 - skip unreadable fonts
                    continue
                seen.add(p.name)
                out.append({"file": p.name, "family": family, "weight": weight, "path": str(p)})
    return out


def add_font(src: str | Path) -> dict:
    """Copy a font into the user font folder so presets can refer to it by file name."""
    src = Path(src)
    if src.suffix.lower() not in FONT_SUFFIXES:
        raise ValueError("Only .ttf and .otf fonts are supported")
    family, weight = font_info(src)
    USER_FONTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = USER_FONTS_DIR / src.name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return {"file": dest.name, "family": family, "weight": weight, "path": str(dest)}
