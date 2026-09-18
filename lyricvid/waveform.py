"""Audio peak envelope for drawing the timeline waveform."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from .ffmpeg import _NO_WINDOW, find_tool

PEAKS_PER_SEC = 100
_RATE = 8000


def compute_peaks(path: str | Path) -> np.ndarray:
    """Normalised (0..1) peak per 1/PEAKS_PER_SEC second, mono."""
    raw = subprocess.run(
        [find_tool("ffmpeg"), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(_RATE),
         "-f", "s16le", "-"],
        capture_output=True, check=True, creationflags=_NO_WINDOW,
    ).stdout
    samples = np.abs(np.frombuffer(raw, dtype=np.int16).astype(np.float32))
    hop = _RATE // PEAKS_PER_SEC
    n = len(samples) // hop
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    peaks = samples[: n * hop].reshape(n, hop).max(axis=1)
    ref = float(np.percentile(peaks, 99.5)) or 1.0
    # Mild gamma so quiet passages stay visible next to loud choruses.
    return (np.clip(peaks / ref, 0.0, 1.0) ** 0.7).astype(np.float32)
