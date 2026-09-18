"""Automatic first-pass timing: LRCLIB synced lyrics if found, else the audio guess."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import autotime, lrc
from .models import Line


@dataclass
class AutoTimeResult:
    lines: list[Line]
    source: str  # human-readable description of where the timing came from
    exact: bool  # True for LRCLIB timing, False for the rough audio guess


def _fill_gaps(spans: list[tuple[float, float] | None], duration: float) -> list[tuple[float, float]]:
    """Unmatched lines get evenly spaced slots between their matched neighbours."""
    out: list[tuple[float, float]] = []
    i, n = 0, len(spans)
    while i < n:
        if spans[i] is not None:
            out.append(spans[i])
            i += 1
            continue
        j = i
        while j < n and spans[j] is None:
            j += 1
        lo = out[-1][1] if out else 0.0
        hi = spans[j][0] if j < n else duration
        step = max(0.3, (hi - lo) / (j - i))
        for k in range(j - i):
            out.append((round(lo + k * step, 3), round(lo + (k + 1) * step, 3)))
        i = j
    return out


def auto_time(
    audio_path: str | Path,
    texts: list[str],
    duration: float,
    features: autotime.VocalFeatures | None = None,
    online: bool = True,
) -> AutoTimeResult:
    if online:
        try:
            found = lrc.fetch_synced(audio_path, duration, texts)
        except Exception:  # noqa: BLE001 - offline or API trouble: fall back
            found = None
        if found:
            versions, name = found
            spans = lrc.consensus(texts, versions, duration)
            matched = sum(s is not None for s in spans)
            if matched >= max(1, len(texts) // 2):
                filled = _fill_gaps(spans, duration)
                note = "" if matched == len(texts) else f", {len(texts) - matched} line(s) estimated"
                count = f"median of {len(versions)} versions" if len(versions) > 1 else "1 version"
                return AutoTimeResult([Line(t, s, e) for t, (s, e) in zip(texts, filled)],
                                      f"LRCLIB synced lyrics: {name}, {count}{note}", True)
    feats = features or autotime.analyze(audio_path)
    spans = autotime.guess(feats, texts)
    return AutoTimeResult([Line(t, s, e) for t, (s, e) in zip(texts, spans)],
                          "rough guess from the audio, please check every line", False)


def guess_rest(features: autotime.VocalFeatures, lines: list[Line], t: float) -> list[Line]:
    """Keep lines that start before t, re-guess the rest from t onward."""
    keep = [l for l in lines if l.start < t]
    rest = lines[len(keep):]
    if not rest:
        return lines
    if keep and keep[-1].end > t:
        keep[-1] = Line(keep[-1].text, keep[-1].start, t)
    spans = autotime.guess(features, [l.text for l in rest], start_after=t)
    return keep + [Line(l.text, s, e) for l, (s, e) in zip(rest, spans)]
