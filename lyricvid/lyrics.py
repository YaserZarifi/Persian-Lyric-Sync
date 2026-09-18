"""Plain-text lyric parsing and placeholder timing."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .models import Line

ZWNJ = "‌"

# Arabic code points that commonly sneak into Persian text from Arabic keyboards.
_PERSIAN_NORMALIZE = str.maketrans({
    "ي": "ی",  # ي -> ی
    "ى": "ی",  # ى -> ی
    "ك": "ک",  # ك -> ک
})

# Explicit bidi controls: libass/fribidi handle direction on their own, stray marks just
# fight with it. ZWNJ is deliberately NOT in this set, it's part of Persian spelling.
_BIDI_CONTROLS = re.compile("[‎‏‪-‮⁦-⁩؜﻿]")

# Decorations lyric sites append to lines (●♪♫ etc.), stripped from line ends.
_TRAILING_DECOR = re.compile(r"[\s●○•♪♫♬♩🎵🎶❤♥💔★☆]+$")


_HAS_LETTER = re.compile(r"[^\W\d_]")


def clean_line(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_PERSIAN_NORMALIZE)
    text = _BIDI_CONTROLS.sub("", text)
    text = _TRAILING_DECOR.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def parse_lyrics(raw: str) -> list[str | None]:
    """Return lyric lines; None marks a blank-line section break."""
    out: list[str | None] = []
    for raw_line in raw.splitlines():
        line = clean_line(raw_line)
        if line and not _HAS_LETTER.search(line):
            line = ""  # decoration-only lines like "───┤ ♩♬♫ ├───"
        if line:
            out.append(line)
        elif out and out[-1] is not None:
            out.append(None)
    while out and out[-1] is None:
        out.pop()
    return out


def read_lyrics_file(path: str | Path) -> list[str | None]:
    return parse_lyrics(Path(path).read_text(encoding="utf-8-sig"))


def spread_evenly(
    parsed: list[str | None],
    duration: float,
    lead_in: float = 2.0,
    tail: float = 2.0,
    section_gap: float = 1.5,
) -> list[Line]:
    """Placeholder timing until the sync UI exists: equal slots across the song."""
    texts = [t for t in parsed if t is not None]
    if not texts:
        return []
    breaks = sum(1 for t in parsed if t is None)
    usable = max(duration - lead_in - tail - breaks * section_gap, len(texts) * 0.5)
    slot = usable / len(texts)
    lines: list[Line] = []
    t = lead_in
    for item in parsed:
        if item is None:
            t += section_gap
            continue
        lines.append(Line(item, round(t, 3), round(t + slot, 3)))
        t += slot
    return lines


def respread(lines: list[Line], duration: float, **kw) -> list[Line]:
    return spread_evenly([l.text for l in lines], duration, **kw)
