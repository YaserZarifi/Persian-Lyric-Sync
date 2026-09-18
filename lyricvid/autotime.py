"""Rough automatic lyric timing from the audio alone (no speech recognition).

1. Vocal envelope: lead vocals are usually centre-panned, so take the mid channel's
   energy in the voice band minus the side channel's energy in the same band.
2. Phrase onsets: dips in that envelope (breaths between lines) followed by a rise.
3. Fit: dynamic programming picks one onset per lyric line so each line's *sung* time
   is proportional to its text length, preferring deep dips. Instrumental stretches
   cost nothing because only voiced time is counted.

The result is a first guess for the user to correct on the timeline.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .ffmpeg import _NO_WINDOW, find_tool

SR = 16000
HOP = 320  # 20 ms
FRAME_SEC = HOP / SR
N_FFT = 1024
VOICE_BAND = (250.0, 3500.0)

LEAD_IN = 0.15  # show a line slightly before it is sung
HOLD_GAP = 1.2  # gaps shorter than this keep the previous line on screen
TAIL = 0.5  # after the last voiced frame when a line is followed by a long break


@dataclass
class VocalFeatures:
    env_db: np.ndarray  # smoothed vocal envelope, dB, one value per frame
    voiced: np.ndarray  # bool per frame
    onsets: np.ndarray  # candidate phrase-start frames
    strength: np.ndarray  # dip depth (dB) for each onset

    @property
    def duration(self) -> float:
        return len(self.env_db) * FRAME_SEC


def decode_stereo(path: str | Path) -> np.ndarray:
    raw = subprocess.run(
        [find_tool("ffmpeg"), "-v", "error", "-i", str(path), "-vn", "-ac", "2",
         "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True, check=True, creationflags=_NO_WINDOW,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).reshape(-1, 2).astype(np.float32) / 32768.0


def _smooth(x: np.ndarray, frames: int) -> np.ndarray:
    if frames <= 1:
        return x
    k = np.ones(frames) / frames
    return np.convolve(np.pad(x, frames // 2, mode="edge"), k, mode="valid")[: len(x)]


def _band_energy(signal: np.ndarray, band: np.ndarray, window: np.ndarray) -> np.ndarray:
    n = 1 + max(0, len(signal) - N_FFT) // HOP
    frames = np.lib.stride_tricks.sliding_window_view(signal, N_FFT)[::HOP][:n]
    spec = np.abs(np.fft.rfft(frames * window, axis=1)) ** 2
    return spec[:, band].sum(axis=1)


def analyze_pcm(stereo: np.ndarray) -> VocalFeatures:
    if len(stereo) < N_FFT:
        stereo = np.pad(stereo, ((0, N_FFT - len(stereo)), (0, 0)))
    mid = (stereo[:, 0] + stereo[:, 1]) / 2
    side = (stereo[:, 0] - stereo[:, 1]) / 2
    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    band = (freqs >= VOICE_BAND[0]) & (freqs <= VOICE_BAND[1])
    window = np.hanning(N_FFT).astype(np.float32)
    em = _band_energy(mid, band, window)
    es = _band_energy(side, band, window)
    vocal = np.maximum(em - 0.8 * es, em * 0.05)
    env = _smooth(10 * np.log10(vocal + 1e-10), 5)  # 100 ms

    lo, hi = np.percentile(env, 10), np.percentile(env, 95)
    voiced = env > lo + 0.45 * (hi - lo)
    voiced = _smooth(voiced.astype(np.float32), 9) > 0.5  # drop blips under ~100 ms

    # Onsets: local minima with enough prominence, placed where the envelope rises again.
    s = _smooth(env, 9)  # 180 ms
    w = int(0.5 / FRAME_SEC)
    n = len(s)
    onsets, strength = [], []
    padded = np.pad(s, w, mode="edge")
    win = np.lib.stride_tricks.sliding_window_view(padded, 2 * w + 1)
    is_min = s <= win.min(axis=1)
    for m in np.flatnonzero(is_min):
        left = s[max(0, m - w):m + 1].max()
        right_seg = s[m:min(n, m + w + 1)]
        prom = min(left, right_seg.max()) - s[m]
        if prom < 2.5:
            continue
        rise = np.flatnonzero(right_seg >= s[m] + 0.5 * prom)
        f = m + (int(rise[0]) if len(rise) else 0)
        if not onsets or f - onsets[-1] > int(0.35 / FRAME_SEC):
            onsets.append(f)
            strength.append(min(prom, 20.0))
    # Voiced-run starts are onsets too (covers phrases that start from silence).
    runs = np.flatnonzero(np.diff(voiced.astype(np.int8)) == 1) + 1
    for f in runs:
        near = [i for i, o in enumerate(onsets) if abs(o - f) < int(0.3 / FRAME_SEC)]
        if near:
            strength[near[0]] = max(strength[near[0]], 12.0)
        else:
            onsets.append(int(f))
            strength.append(12.0)
    order = np.argsort(onsets)
    return VocalFeatures(env, voiced, np.asarray(onsets)[order].astype(np.int64),
                         np.asarray(strength)[order].astype(np.float64))


def analyze(path: str | Path) -> VocalFeatures:
    return analyze_pcm(decode_stereo(path))


def text_weight(text: str) -> float:
    """Rough singing-length proxy: letters plus a little per word."""
    letters = len(re.findall(r"\w", text))
    words = len(text.split())
    return letters + 1.5 * words + 2.0


def guess(
    features: VocalFeatures,
    texts: list[str],
    start_after: float = 0.0,
    end_before: float | None = None,
) -> list[tuple[float, float]]:
    """Return (start, end) seconds for each text, within [start_after, end_before]."""
    n_lines = len(texts)
    if n_lines == 0:
        return []
    voiced = features.voiced
    total = len(voiced)
    f0 = int(start_after / FRAME_SEC)
    f1 = min(total, int((end_before if end_before is not None else features.duration) / FRAME_SEC))
    cum = np.concatenate([[0], np.cumsum(voiced)]).astype(np.float64) * FRAME_SEC

    vidx = np.flatnonzero(voiced[f0:f1]) + f0
    if len(vidx) == 0:  # nothing voiced: fall back to even spacing
        step = (f1 - f0) * FRAME_SEC / n_lines
        return [(start_after + i * step, start_after + (i + 1) * step) for i in range(n_lines)]
    v_end = int(vidx[-1]) + 1

    mask = (features.onsets >= f0) & (features.onsets < v_end)
    cand = features.onsets[mask]
    strength = features.strength[mask]
    if len(cand) == 0 or cand[0] > vidx[0] + int(0.3 / FRAME_SEC):
        cand = np.concatenate([[vidx[0]], cand])
        strength = np.concatenate([[12.0], strength])
    m = len(cand)
    if m < n_lines:  # not enough phrase starts: pad with evenly spaced voiced frames
        extra = vidx[np.linspace(0, len(vidx) - 1, n_lines + 2).astype(int)[1:-1]]
        cand = np.unique(np.concatenate([cand, extra]))
        strength = np.array([features.strength[features.onsets == c][0]
                             if (features.onsets == c).any() else 0.0 for c in cand])
        m = len(cand)

    weights = np.array([text_weight(t) for t in texts])
    voiced_total = cum[v_end] - cum[cand[0]]
    expected = weights / weights.sum() * voiced_total

    def seg_cost(i: int, a: np.ndarray, b_frame: np.ndarray) -> np.ndarray:
        dur = cum[b_frame] - cum[a]
        ratio = (dur + 0.3) / (expected[i] + 0.3)
        return 4.0 * np.log(np.maximum(ratio, 1e-3)) ** 2

    bonus = strength / 10.0
    inf = np.inf
    cost = np.full((n_lines, m), inf)
    back = np.zeros((n_lines, m), dtype=np.int64)
    # Voiced time before the first line is mildly penalised (vocals usually start the lyrics).
    cost[0] = 0.4 * (cum[cand] - cum[cand[0]]) - bonus
    for i in range(1, n_lines):
        for j in range(i, m):
            ks = np.arange(i - 1, j)
            c = cost[i - 1, ks] + seg_cost(i - 1, cand[ks], np.full(len(ks), cand[j]))
            best = int(np.argmin(c))
            cost[i, j] = c[best] - bonus[j]
            back[i, j] = ks[best]
    final = cost[n_lines - 1] + seg_cost(n_lines - 1, cand, np.full(m, v_end))
    j = int(np.argmin(final))
    starts = [0] * n_lines
    for i in range(n_lines - 1, -1, -1):
        starts[i] = int(cand[j])
        j = int(back[i, j])

    spans = []
    for i, sf in enumerate(starts):
        nf = starts[i + 1] if i + 1 < n_lines else v_end
        seg = np.flatnonzero(voiced[sf:nf])
        last_voiced = (sf + int(seg[-1]) + 1) if len(seg) else nf
        start = max(start_after, sf * FRAME_SEC - LEAD_IN)
        next_start = nf * FRAME_SEC - LEAD_IN if i + 1 < n_lines else None
        end = last_voiced * FRAME_SEC + TAIL
        if next_start is not None and (next_start - end < HOLD_GAP or end > next_start):
            end = next_start
        if end_before is not None:
            end = min(end, end_before)
        spans.append((round(start, 3), round(max(end, start + 0.2), 3)))
    return spans
