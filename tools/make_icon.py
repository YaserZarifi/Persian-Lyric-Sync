"""Draw the app icon (assets/icon.png + assets/icon.ico) with Qt, so it needs no design tool."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QGuiApplication, QImage, QLinearGradient, QPainter,
    QPainterPath, QPen,
)

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def draw(size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    s = size / 256

    # Night-sky rounded square, like the lyric-video backgrounds.
    grad = QLinearGradient(QPointF(0, 0), QPointF(0, size))
    grad.setColorAt(0, QColor("#2b1d5c"))
    grad.setColorAt(0.6, QColor("#b8336a"))
    grad.setColorAt(1, QColor("#ff8a5c"))
    body = QPainterPath()
    body.addRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 52 * s, 52 * s)
    p.fillPath(body, grad)

    # Persian "lyric" letter in white with a dark outline, as in the videos.
    fid = QFontDatabase.addApplicationFont(str(ASSETS / "fonts" / "Vazirmatn-FD-Black.ttf"))
    family = QFontDatabase.applicationFontFamilies(fid)[0]
    font = QFont(family)
    font.setPixelSize(int(150 * s))
    font.setWeight(QFont.Black)
    text = QPainterPath()
    text.addText(0, 0, font, "ت")
    box = text.boundingRect()
    text.translate(size / 2 - box.center().x(), size * 0.47 - box.center().y())
    p.setPen(QPen(QColor("#141019"), 14 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(text)
    p.fillPath(text, QColor("white"))

    # A small timeline bar with a playhead: "sync".
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 150))
    p.drawRoundedRect(QRectF(48 * s, 196 * s, 160 * s, 14 * s), 7 * s, 7 * s)
    p.setBrush(QColor("white"))
    p.drawRoundedRect(QRectF(48 * s, 196 * s, 92 * s, 14 * s), 7 * s, 7 * s)
    p.drawEllipse(QPointF(140 * s, 203 * s), 13 * s, 13 * s)
    p.end()
    return img


def main() -> None:
    app = QGuiApplication(sys.argv)  # noqa: F841 - fonts need an app instance
    draw(256).save(str(ASSETS / "icon.png"))
    # Qt's ICO writer stores one image per file; 256 px covers every Windows size.
    if not draw(256).save(str(ASSETS / "icon.ico"), "ICO"):
        raise SystemExit("ICO writer plugin not available")
    print(ASSETS / "icon.png", ASSETS / "icon.ico")


if __name__ == "__main__":
    main()
