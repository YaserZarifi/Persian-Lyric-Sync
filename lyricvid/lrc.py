"""Synced lyrics from LRCLIB (lrclib.net) and mapping them onto the user's own lines.

The user's .txt rarely splits lines the same way as the LRC (here one txt line is two
LRC lines, and a repeated line is missing), so timing is transferred by aligning the
two texts letter by letter and reading each txt line's first letter's time.
"""
from __future__ import annotations

import difflib
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg import _NO_WINDOW, find_tool

API = "https://lrclib.net/api"
USER_AGENT = "persian-lyric-video/0.1 (https://github.com/YaserZarifi/Persian-Lyric-Sync)"

_LRC_TIME = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
_DIACRITICS = re.compile("[ً-ٰٟـ]")
_NORMALIZE = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه", "أ": "ا", "إ": "ا", "آ": "ا"})


@dataclass
class LrcLine:
    time: float
    text: str  # empty = end-of-singing marker


def parse_lrc(synced: str) -> list[LrcLine]:
    out = []
    for raw in synced.splitlines():
        stamps = list(_LRC_TIME.finditer(raw))
        if not stamps:
            continue
        text = _LRC_TIME.sub("", raw).strip()
        for m in stamps:
            out.append(LrcLine(int(m.group(1)) * 60 + float(m.group(2)), text))
    return sorted(out, key=lambda l: l.time)


def letters(text: str) -> str:
    """Comparable letters only: no spaces, punctuation, diacritics or ZWNJ."""
    text = _DIACRITICS.sub("", text.translate(_NORMALIZE)).lower()
    return "".join(ch for ch in text if ch.isalpha())


# ---- song identity ---------------------------------------------------------------

_JUNK = re.compile(r"\s*(\(\d+\)|\[\d+\]|\(\d+\s*kbps\)|~.*$|\|.*$)", re.I)


def song_identity(audio_path: str | Path) -> tuple[str, str]:
    """(artist, title) from tags, falling back to an 'Artist - Title' filename."""
    import subprocess

    artist = title = ""
    try:
        out = subprocess.run(
            [find_tool("ffprobe"), "-v", "error", "-show_entries", "format_tags=artist,title",
             "-of", "json", str(audio_path)],
            capture_output=True, text=True, encoding="utf-8", check=True,
            creationflags=_NO_WINDOW,
        ).stdout
        tags = {k.lower(): v for k, v in json.loads(out).get("format", {}).get("tags", {}).items()}
        artist, title = tags.get("artist", ""), tags.get("title", "")
    except Exception:  # noqa: BLE001 - tags are optional
        pass
    stem = Path(audio_path).stem
    if " - " in stem:
        fa, ft = stem.split(" - ", 1)
        artist = artist or fa
        title = title or ft
    clean = lambda s: _JUNK.sub("", s).strip(" -_")  # noqa: E731
    return clean(artist), clean(title or stem)


# ---- LRCLIB -----------------------------------------------------------------------

def _get(url: str, timeout: float = 10.0):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search(artist: str, title: str) -> list[dict]:
    results: dict[int, dict] = {}
    queries = [{"track_name": title, "artist_name": artist}, {"q": f"{artist} {title}"},
               {"q": title}]
    for params in queries:
        params = {k: v for k, v in params.items() if v}
        if not params:
            continue
        try:
            for r in _get(f"{API}/search?{urllib.parse.urlencode(params)}"):
                results.setdefault(r["id"], r)
        except Exception:  # noqa: BLE001 - try the next query form
            continue
    return list(results.values())


def good_matches(candidates: list[dict], duration: float, user_texts: list[str]) -> list[dict]:
    """Synced candidates close in length whose lyrics look like the user's, best first."""
    mine = letters("".join(user_texts))
    scored = []
    for c in candidates:
        if not c.get("syncedLyrics") or abs(float(c.get("duration") or 0) - duration) > 4:
            continue
        theirs = letters(" ".join(l.text for l in parse_lrc(c["syncedLyrics"])))
        sim = difflib.SequenceMatcher(None, mine, theirs, autojunk=False).ratio() if mine else 0.5
        if sim >= 0.45:
            scored.append((sim - abs(float(c["duration"]) - duration) * 0.02, c))
    return [c for _, c in sorted(scored, key=lambda x: -x[0])]


def fetch_synced(
    audio_path: str | Path, duration: float, user_texts: list[str]
) -> tuple[list[list[LrcLine]], str] | None:
    """All usable synced versions of the song (uploads often differ by ~1 s)."""
    artist, title = song_identity(audio_path)
    matches = good_matches(search(artist, title), duration, user_texts)
    if not matches:
        return None
    return [parse_lrc(m["syncedLyrics"]) for m in matches], f"{matches[0]['artistName']} – {matches[0]['trackName']}"


def consensus(
    user_texts: list[str], versions: list[list[LrcLine]], duration: float
) -> list[tuple[float, float] | None]:
    """Per-line median of each version's alignment."""
    import statistics

    per_version = [align_to_lines(user_texts, v, duration) for v in versions]
    spans: list[tuple[float, float] | None] = []
    for i in range(len(user_texts)):
        got = [pv[i] for pv in per_version if pv[i] is not None]
        if not got:
            spans.append(None)
            continue
        spans.append((round(statistics.median(s for s, _ in got), 3),
                      round(statistics.median(e for _, e in got), 3)))
    for i in range(len(spans) - 1):
        a, b = spans[i], spans[i + 1]
        if a and b and a[1] > b[0]:
            spans[i] = (a[0], b[0])
    return spans


# ---- transfer timing onto the user's lines ----------------------------------------

def align_to_lines(
    user_texts: list[str], lrc: list[LrcLine], duration: float
) -> list[tuple[float, float] | None]:
    """Timing for each user line from the LRC; None where nothing matched."""
    # Per-letter times: letters of an LRC line spread across its slot to the next stamp.
    lrc_chars: list[str] = []
    lrc_time: list[float] = []
    lrc_slot_end: list[float] = []
    for i, line in enumerate(lrc):
        nxt = lrc[i + 1].time if i + 1 < len(lrc) else duration
        chars = letters(line.text)
        span = min(nxt - line.time, 0.33 * len(chars) + 0.5)
        for k, ch in enumerate(chars):
            lrc_chars.append(ch)
            lrc_time.append(line.time + span * k / max(1, len(chars)))
            lrc_slot_end.append(nxt)

    user_chars: list[str] = []
    owner: list[int] = []
    for i, text in enumerate(user_texts):
        for ch in letters(text):
            user_chars.append(ch)
            owner.append(i)

    sm = difflib.SequenceMatcher(None, "".join(user_chars), "".join(lrc_chars), autojunk=False)
    first: dict[int, float] = {}
    last_end: dict[int, float] = {}
    for a, b, size in sm.get_matching_blocks():
        if size < 3:  # ignore coincidental one- or two-letter matches
            continue
        for k in range(size):
            row = owner[a + k]
            first.setdefault(row, lrc_time[b + k])
            last_end[row] = lrc_slot_end[b + k]

    spans: list[tuple[float, float] | None] = []
    for i in range(len(user_texts)):
        if i in first:
            spans.append((round(first[i], 3), round(max(last_end[i], first[i] + 0.3), 3)))
        else:
            spans.append(None)
    # A line never overlaps the next one.
    for i in range(len(spans) - 1):
        if spans[i] and spans[i + 1] and spans[i][1] > spans[i + 1][0]:
            spans[i] = (spans[i][0], spans[i + 1][0])
    return spans
