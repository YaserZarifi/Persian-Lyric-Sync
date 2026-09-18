"""Timeline drag math: move / resize / ripple lines without creating overlaps."""
from __future__ import annotations

MIN_LEN = 0.2  # shortest allowed line, seconds
LINK_EPS = 0.05  # edges closer than this count as a shared boundary

Span = tuple[float, float]


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def apply_drag(snap: list[Span], row: int, mode: str, dt: float, duration: float) -> list[Span]:
    """Return new spans after dragging `row` by `dt` seconds, relative to `snap`.

    mode: "move"   shift the line, bounded by its neighbours
          "ripple" shift the line and every line after it
          "start"  move the start edge (drags a touching previous line's end along)
          "end"    move the end edge (drags a touching next line's start along)
    """
    spans = list(snap)
    s, e = snap[row]
    prev = snap[row - 1] if row > 0 else None
    nxt = snap[row + 1] if row + 1 < len(snap) else None
    limit = duration if duration > 0 else float("inf")

    if mode == "move":
        lo = (prev[1] if prev else 0.0) - s
        hi = (nxt[0] if nxt else limit) - e
        d = _clamp(dt, lo, max(lo, hi))
        spans[row] = (s + d, e + d)
    elif mode == "ripple":
        lo = (prev[1] if prev else 0.0) - s
        hi = limit - snap[-1][1]
        d = _clamp(dt, lo, max(lo, hi))
        for i in range(row, len(snap)):
            a, b = snap[i]
            spans[i] = (a + d, b + d)
    elif mode == "start":
        linked = prev is not None and abs(prev[1] - s) < LINK_EPS
        lo = (prev[0] + MIN_LEN) if linked else (prev[1] if prev else 0.0)
        new = _clamp(s + dt, lo, e - MIN_LEN)
        spans[row] = (new, e)
        if linked:
            spans[row - 1] = (prev[0], new)
    elif mode == "end":
        linked = nxt is not None and abs(nxt[0] - e) < LINK_EPS
        hi = (nxt[1] - MIN_LEN) if linked else (nxt[0] if nxt else limit)
        new = _clamp(e + dt, s + MIN_LEN, hi)
        spans[row] = (s, new)
        if linked:
            spans[row + 1] = (new, nxt[1])
    else:
        raise ValueError(mode)
    return [(round(a, 3), round(b, 3)) for a, b in spans]
