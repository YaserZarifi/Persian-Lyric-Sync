"""WaveformItem: paints the visible slice of the audio envelope for the timeline."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Property, QObject, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtQml import QmlElement
from PySide6.QtQuick import QQuickPaintedItem

from lyricvid.waveform import PEAKS_PER_SEC

QML_IMPORT_NAME = "LyricVid"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
class WaveformItem(QQuickPaintedItem):
    """Draws peaks from `source.waveform` for [viewStart, viewStart + width/pxPerSec]."""

    sourceChanged = Signal()
    viewChanged = Signal()
    colorChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source: QObject | None = None
        self._view_start = 0.0
        self._pps = 50.0
        self._color = QColor("#5b6b8c")
        self.setAntialiasing(True)

    def _get_source(self):
        return self._source

    def _set_source(self, src) -> None:
        if src is self._source:
            return
        if self._source is not None:
            try:
                self._source.waveformChanged.disconnect(self.update)
            except RuntimeError:  # source already destroyed during teardown
                pass
        self._source = src
        if src is not None:
            src.waveformChanged.connect(self.update)
        self.sourceChanged.emit()
        self.update()

    source = Property(QObject, _get_source, _set_source, notify=sourceChanged)

    def _get_view_start(self) -> float:
        return self._view_start

    def _set_view_start(self, v: float) -> None:
        if v != self._view_start:
            self._view_start = v
            self.viewChanged.emit()
            self.update()

    viewStart = Property(float, _get_view_start, _set_view_start, notify=viewChanged)

    def _get_pps(self) -> float:
        return self._pps

    def _set_pps(self, v: float) -> None:
        if v > 0 and v != self._pps:
            self._pps = v
            self.viewChanged.emit()
            self.update()

    pxPerSec = Property(float, _get_pps, _set_pps, notify=viewChanged)

    def _get_color(self) -> QColor:
        return self._color

    def _set_color(self, c: QColor) -> None:
        self._color = QColor(c)
        self.colorChanged.emit()
        self.update()

    color = Property(QColor, _get_color, _set_color, notify=colorChanged)

    def paint(self, painter: QPainter) -> None:
        peaks = getattr(self._source, "waveform_peaks", None) if self._source else None
        w, h = int(self.width()), self.height()
        if peaks is None or len(peaks) == 0 or w <= 0:
            return
        # Max over the peak-index range [start, end) each pixel column covers. A trailing
        # zero stands in for columns past the end of the song.
        n = len(peaks)
        padded = np.append(peaks, np.float32(0.0))
        t = self._view_start + np.arange(w + 1, dtype=np.float64) / self._pps
        idx = np.clip((t * PEAKS_PER_SEC).astype(np.int64), 0, n)
        starts = idx[:-1]
        ends = np.minimum(np.maximum(idx[1:], starts + 1), n)
        pairs = np.empty(2 * w, dtype=np.int64)
        pairs[0::2], pairs[1::2] = starts, np.maximum(ends, starts)
        vals = np.maximum.reduceat(padded, pairs)[0::2]
        mid = h / 2
        amp = vals * (mid - 2)
        top = [QPointF(x, mid - a) for x, a in enumerate(amp)]
        bottom = [QPointF(x, mid + a) for x, a in zip(range(w - 1, -1, -1), amp[::-1])]
        painter.setPen(self._color)
        painter.setBrush(self._color)
        painter.drawPolygon(QPolygonF(top + bottom))
