"""Entry point: uv run python app/main.py [project.lyricproj.json]"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QtMsgType, QTimer, QUrl, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QFontDatabase, QGuiApplication, QIcon  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

import app.waveform_item  # noqa: E402,F401  (registers the LyricVid QML module)
from app.backend import Backend  # noqa: E402
from lyricvid.ffmpeg import find_tool  # noqa: E402
from lyricvid.models import ASSETS, FONTS_DIR, ROOT, USER_DIR  # noqa: E402

FFMPEG_HELP = (
    "ffmpeg was not found. Install it (with libass) and restart the app:\n\n"
    "    winget install Gyan.FFmpeg\n\n"
    "or set the LYRICVID_FFMPEG and LYRICVID_FFPROBE environment variables."
)


LOG_PATH = USER_DIR / "app.log"


def _setup_logging() -> None:
    """Qt warnings and uncaught errors go to a log file (the packaged app has no console)."""
    import datetime
    import traceback

    USER_DIR.mkdir(parents=True, exist_ok=True)
    if LOG_PATH.exists() and LOG_PATH.stat().st_size > 1_000_000:
        LOG_PATH.unlink()
    log = open(LOG_PATH, "a", encoding="utf-8", buffering=1)  # noqa: SIM115 - lives for the app
    log.write(f"--- start {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n")
    levels = {QtMsgType.QtDebugMsg: "debug", QtMsgType.QtInfoMsg: "info",
              QtMsgType.QtWarningMsg: "warning", QtMsgType.QtCriticalMsg: "critical",
              QtMsgType.QtFatalMsg: "fatal"}

    def handler(kind, context, message):
        log.write(f"{levels.get(kind, kind)}: {message}\n")
        if sys.stderr:
            print(message, file=sys.stderr)

    qInstallMessageHandler(handler)
    sys.excepthook = lambda *exc: log.write("".join(traceback.format_exception(*exc)))


def main() -> int:
    _setup_logging()
    os.environ.setdefault("QT_QUICK_CONTROLS_MATERIAL_VARIANT", "Dense")
    QQuickStyle.setStyle("Material")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Persian Lyric Sync")
    app.setOrganizationName("tiger")
    app.setWindowIcon(QIcon(str(ASSETS / "icon.png")))
    # Makes the bundled font available to QML for RTL lyric editing.
    for font in FONTS_DIR.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(font))

    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"backend": backend})
    engine.load(QUrl.fromLocalFile(str(ROOT / "app" / "qml" / "Main.qml")))
    if not engine.rootObjects():
        return 1
    try:
        find_tool("ffmpeg")
        find_tool("ffprobe")
    except FileNotFoundError:
        QTimer.singleShot(0, lambda: backend.errorOccurred.emit(FFMPEG_HELP))
    if len(sys.argv) > 1:
        backend.openProject(QUrl.fromLocalFile(str(Path(sys.argv[1]).resolve())))
    code = app.exec()
    backend.shutdown()
    return code


if __name__ == "__main__":
    sys.exit(main())
