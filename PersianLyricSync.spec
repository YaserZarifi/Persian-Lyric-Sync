# PyInstaller build: uv run pyinstaller PersianLyricSync.spec --noconfirm
# Output: dist/PersianLyricSync/PersianLyricSync.exe (ffmpeg is not bundled; it must be on PATH)
from pathlib import Path

root = Path(SPECPATH)

datas = [
    (str(root / "app" / "qml"), "app/qml"),
    (str(root / "assets"), "assets"),
]

# Qt modules the app never touches; leaving them out keeps the folder much smaller.
excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebView", "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DExtras",
    "PySide6.QtQuick3D", "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
    "PySide6.QtPdf", "PySide6.QtPdfQuick", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp",
    "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtTextToSpeech",
    "tkinter", "pytest",
]

# Audio playback: PyInstaller's Qt hook misses the QtMultimedia backend plugins and the
# FFmpeg libraries the ffmpeg backend loads, which leaves the player silent.
import PySide6  # noqa: E402

qt_dir = Path(PySide6.__file__).parent
binaries = [(str(dll), "PySide6/plugins/multimedia") for dll in (qt_dir / "plugins" / "multimedia").glob("*.dll")]
binaries += [(str(dll), "PySide6") for pattern in ("av*.dll", "sw*.dll") for dll in qt_dir.glob(pattern)]

a = Analysis(
    [str(root / "app" / "main.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=["app.waveform_item", "fontTools.ttLib.tables._n_a_m_e"],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PersianLyricSync",
    icon=str(root / "assets" / "icon.ico"),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="PersianLyricSync", upx=False)
