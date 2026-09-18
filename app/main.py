"""Entry point: uv run python app/main.py"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QFontDatabase, QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from app.backend import Backend  # noqa: E402
import app.waveform_item  # noqa: E402,F401  (registers the LyricVid QML module)
from lyricvid.models import FONTS_DIR  # noqa: E402


def main() -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_MATERIAL_VARIANT", "Dense")
    QQuickStyle.setStyle("Material")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Persian Lyric Video")
    app.setOrganizationName("tiger")
    # Makes the bundled font available to QML for RTL lyric editing.
    for font in FONTS_DIR.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(font))

    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"backend": backend})
    engine.load(QUrl.fromLocalFile(str(ROOT / "app" / "qml" / "Main.qml")))
    if not engine.rootObjects():
        return 1
    if len(sys.argv) > 1:
        backend.openProject(QUrl.fromLocalFile(str(Path(sys.argv[1]).resolve())))
    code = app.exec()
    backend.shutdown()
    return code


if __name__ == "__main__":
    sys.exit(main())
