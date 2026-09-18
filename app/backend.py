"""Python side of the QML UI: project state, lines model, preview and export jobs."""
from __future__ import annotations

import copy
import time
import tempfile
import threading
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import (
    Property, QAbstractListModel, QByteArray, QModelIndex, QObject, Qt, QTimer, QUrl,
    Signal, Slot,
)

from lyricvid.ffmpeg import RenderCancelled, Workdir, probe_duration, render_frame, render_video
from lyricvid.lyrics import clean_line, parse_lyrics, read_lyrics_file, respread, spread_evenly
from lyricvid import fonts
from lyricvid.ffmpeg import nvenc_available
from lyricvid.models import (
    FONTS_DIR, USER_PRESETS_DIR, Line, Project, list_presets, resolve_font, slugify,
)
from lyricvid import autotime
from lyricvid.sync import auto_time, guess_rest
from lyricvid.timing import apply_drag
from lyricvid.waveform import compute_peaks


def _local(url: QUrl | str) -> str:
    if isinstance(url, QUrl):
        return url.toLocalFile()
    return QUrl(url).toLocalFile() if url.startswith("file:") else url


class LinesModel(QAbstractListModel):
    TextRole = Qt.UserRole + 1
    StartRole = Qt.UserRole + 2
    EndRole = Qt.UserRole + 3

    edited = Signal()
    textEdited = Signal()

    undoAvailableChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lines: list[Line] = []
        self.duration = 0.0
        self._snap: list[tuple[float, float]] | None = None
        self._undo: list[list[Line]] = []

    def roleNames(self) -> dict[int, QByteArray]:
        return {self.TextRole: QByteArray(b"text"), self.StartRole: QByteArray(b"start"),
                self.EndRole: QByteArray(b"end")}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._lines)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        line = self._lines[index.row()]
        return {self.TextRole: line.text, self.StartRole: line.start,
                self.EndRole: line.end}.get(role)

    def lines(self) -> list[Line]:
        return self._lines

    def reset(self, lines: list[Line], keep_undo: bool = False) -> None:
        if not keep_undo:
            self._undo.clear()
            self.undoAvailableChanged.emit()
        self.beginResetModel()
        self._lines = lines
        self.endResetModel()

    def _push_undo(self) -> None:
        self._undo.append([Line(l.text, l.start, l.end) for l in self._lines])
        del self._undo[:-100]
        self.undoAvailableChanged.emit()

    def _get_can_undo(self) -> bool:
        return bool(self._undo)

    canUndo = Property(bool, _get_can_undo, notify=undoAvailableChanged)

    @Slot()
    def undo(self) -> None:
        if self._undo:
            lines = self._undo.pop()
            self.undoAvailableChanged.emit()
            self.reset(lines, keep_undo=True)
            self.edited.emit()

    # Timeline drags: spans are recomputed from the drag-start snapshot on every move.
    @Slot(int)
    def beginDrag(self, row: int) -> None:
        self._push_undo()
        self._snap = [(l.start, l.end) for l in self._lines]

    @Slot(int, str, float)
    def dragMove(self, row: int, mode: str, dt: float) -> None:
        if self._snap is None or not 0 <= row < len(self._lines):
            return
        spans = apply_drag(self._snap, row, mode, dt, self.duration)
        first = last = None
        for i, (a, b) in enumerate(spans):
            line = self._lines[i]
            if (line.start, line.end) != (a, b):
                line.start, line.end = a, b
                first = i if first is None else first
                last = i
        if first is not None:
            self.dataChanged.emit(self.index(first), self.index(last))
            self.edited.emit()

    @Slot()
    def endDrag(self) -> None:
        if self._snap == [(l.start, l.end) for l in self._lines] and self._undo:
            self._undo.pop()  # nothing actually moved
            self.undoAvailableChanged.emit()
        self._snap = None

    @Slot(int, str, str, result=bool)
    def setField(self, row: int, field: str, value: str) -> bool:
        if not 0 <= row < len(self._lines):
            return False
        line = self._lines[row]
        self._push_undo()
        try:
            if field == "text":
                line.text = clean_line(value)
            elif field in ("start", "end"):
                setattr(line, field, round(max(0.0, parse_time(value)), 3))
            else:
                return False
        except ValueError:
            return False
        idx = self.index(row)
        self.dataChanged.emit(idx, idx)
        self.edited.emit()
        if field == "text":
            self.textEdited.emit()
        return True

    @Slot(int, result=float)
    def midpoint(self, row: int) -> float:
        if 0 <= row < len(self._lines):
            l = self._lines[row]
            return (l.start + l.end) / 2
        return 0.0


def _em_ratio(font_file: str) -> float:
    """Qt pixel size per ASS font size unit.

    libass sizes a font so that winAscent + winDescent equals the ASS Fontsize, while Qt's
    pixelSize is the em size. The live overlay multiplies by this to match the export.
    """
    try:
        from fontTools.ttLib import TTFont

        path = Path(font_file)
        font = TTFont(path if path.is_absolute() else FONTS_DIR / path, lazy=True)
        os2 = font["OS/2"]
        return font["head"].unitsPerEm / (os2.usWinAscent + os2.usWinDescent)
    except Exception:  # noqa: BLE001 - fall back to a typical ratio
        return 0.8


def parse_time(text: str) -> float:
    """Accept seconds ('75.2') or m:ss(.cc) ('1:15.20')."""
    text = text.strip()
    if ":" in text:
        m, s = text.rsplit(":", 1)
        return int(m) * 60 + float(s)
    return float(text)


class Backend(QObject):
    projectChanged = Signal()
    lyricsChanged = Signal()
    styleChanged = Signal()
    dirtyChanged = Signal()
    busyChanged = Signal()
    previewChanged = Signal()
    progressChanged = Signal()
    statusChanged = Signal()
    errorOccurred = Signal(str)
    waveformChanged = Signal()

    # Worker-thread -> main-thread hops (queued automatically across threads).
    _previewDone = Signal(str, str)
    _exportProgress = Signal(float)
    _exportDone = Signal(str, str)
    _peaksDone = Signal(str, object)
    _autoTimeDone = Signal(object, str, bool)
    autoTimingChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._project = Project()
        self._project_path = ""
        self._duration = 0.0
        self._dirty = False
        self._model = LinesModel(self)
        self._model.edited.connect(self._on_lines_edited)
        self._model.textEdited.connect(self.lyricsChanged)
        self._model.modelReset.connect(self.lyricsChanged)

        self._tmp = Path(tempfile.mkdtemp(prefix="lyricvid_ui_"))
        self._preview_wd: Workdir | None = None
        self._preview_url = ""
        self._preview_seq = 0
        self._preview_time = 0.0
        self._preview_running = False
        self._preview_pending = False
        self._playing = False
        self._preview_timer = QTimer(self, singleShot=True, interval=120)
        self._preview_timer.timeout.connect(self._start_preview)

        self._exporting = False
        self._progress = 0.0
        self._qt_fonts: dict[str, tuple[str, int]] = {}
        self._nvenc = False
        threading.Thread(target=self._probe_nvenc, daemon=True).start()
        self._status = ""
        self._cancel = threading.Event()

        self.waveform_peaks = None
        self._peaksDone.connect(self._on_peaks_done)
        self._features: dict[str, autotime.VocalFeatures] = {}
        self._auto_timing = False
        self._autoTimeDone.connect(self._on_auto_time_done)
        self._previewDone.connect(self._on_preview_done)
        self._exportProgress.connect(self._on_export_progress)
        self._exportDone.connect(self._on_export_done)

    # ---- properties -------------------------------------------------------
    def _get_lines(self) -> LinesModel:
        return self._model

    lines = Property(QObject, _get_lines, constant=True)

    def _get_audio(self) -> str:
        return self._project.audio_path

    audioPath = Property(str, _get_audio, notify=projectChanged)

    def _get_audio_url(self) -> str:
        p = self._project.audio_path
        return QUrl.fromLocalFile(p).toString() if p else ""

    audioUrl = Property(str, _get_audio_url, notify=projectChanged)

    def _get_bg(self) -> str:
        return self._project.background_path

    backgroundPath = Property(str, _get_bg, notify=projectChanged)

    def _get_project_path(self) -> str:
        return self._project_path

    projectPath = Property(str, _get_project_path, notify=projectChanged)

    def _get_duration(self) -> float:
        return self._duration

    duration = Property(float, _get_duration, notify=projectChanged)

    def _get_lyrics_text(self) -> str:
        return "\n".join(l.text for l in self._model.lines())

    lyricsText = Property(str, _get_lyrics_text, notify=lyricsChanged)

    def _get_style(self) -> dict:
        style = asdict(self._project.resolved_style())
        style["em_ratio"] = _em_ratio(str(resolve_font(style["font_file"])))
        style["qt_family"], style["qt_weight"] = self._qt_font(style["font_file"])
        style["watermark_url"] = (QUrl.fromLocalFile(style["watermark_image"]).toString()
                                  if style["watermark_image"] else "")
        return style

    def _qt_font(self, font_file: str) -> tuple[str, int]:
        """Family/weight Qt uses for the live overlay (registers the file on first use)."""
        if font_file not in self._qt_fonts:
            path = resolve_font(font_file)
            family, weight = "Vazirmatn FD", 900
            try:
                from PySide6.QtGui import QFontDatabase

                fid = QFontDatabase.addApplicationFont(str(path))
                fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
                weight = fonts.font_info(path)[1]
                family = fams[0] if fams else family
            except Exception:  # noqa: BLE001 - overlay falls back to the default font
                pass
            self._qt_fonts[font_file] = (family, weight)
        return self._qt_fonts[font_file]

    # ---- presets, fonts, export settings -----------------------------------
    presetsChanged = Signal()
    fontsChanged = Signal()
    exportSettingsChanged = Signal()

    def _get_preset_names(self) -> list:
        return list_presets()

    presetNames = Property("QVariantList", _get_preset_names, notify=presetsChanged)

    def _get_preset(self) -> str:
        return self._project.style_preset

    currentPreset = Property(str, _get_preset, notify=styleChanged)

    def _get_style_modified(self) -> bool:
        return bool(self._project.style)

    styleModified = Property(bool, _get_style_modified, notify=styleChanged)

    def _get_preset_is_user(self) -> bool:
        return (USER_PRESETS_DIR / f"{self._project.style_preset}.json").exists()

    presetIsUser = Property(bool, _get_preset_is_user, notify=styleChanged)

    @Slot(str)
    def loadPreset(self, name: str) -> None:
        self._project.style_preset = name
        self._project.style = {}
        self._changed(restyle=True)
        self._set_status(f"Preset: {name}")

    @Slot(str)
    def savePresetAs(self, name: str) -> None:
        name = name.strip()
        if not name:
            return
        style = self._project.resolved_style()
        style.name = slugify(name)
        style.save()
        self._project.style_preset = style.name
        self._project.style = {}
        self.presetsChanged.emit()
        self._changed(restyle=True)
        self._set_status(f"Saved preset '{style.name}'")

    @Slot()
    def deletePreset(self) -> None:
        path = USER_PRESETS_DIR / f"{self._project.style_preset}.json"
        if not path.exists():
            return
        # Keep the look on this project: its values become overrides of the default.
        overrides = asdict(self._project.resolved_style())
        path.unlink()
        self._project.style_preset = "default-bold-outline"
        self._project.style = {k: v for k, v in overrides.items() if k != "name"}
        self.presetsChanged.emit()
        self._changed(restyle=True)

    def _get_fonts(self) -> list:
        return fonts.list_fonts()

    fontList = Property("QVariantList", _get_fonts, notify=fontsChanged)

    @Slot(QUrl)
    def addFont(self, url: QUrl) -> None:
        try:
            info = fonts.add_font(_local(url))
        except Exception as e:  # noqa: BLE001
            self.errorOccurred.emit(f"Could not add font: {e}")
            return
        self.fontsChanged.emit()
        self.setStyleValue("font_file", info["file"])

    @Slot(QUrl)
    def setWatermarkImage(self, url: QUrl) -> None:
        self.setStyleValue("watermark_image", "" if url.isEmpty() else _local(url))

    def _get_export(self) -> dict:
        e = self._project.export
        return {"resolution": e.resolution, "fps": e.fps, "encoder": e.encoder,
                "gpu": self._nvenc}

    exportSettings = Property("QVariantMap", _get_export, notify=exportSettingsChanged)

    @Slot(str, "QVariant")
    def setExportValue(self, key: str, value) -> None:
        if key not in ("resolution", "fps", "encoder"):
            return
        value = int(value) if key == "fps" else str(value)
        if getattr(self._project.export, key) == value:
            return
        setattr(self._project.export, key, value)
        self.exportSettingsChanged.emit()
        self._changed()

    style = Property("QVariantMap", _get_style, notify=styleChanged)

    def _get_dirty(self) -> bool:
        return self._dirty

    dirty = Property(bool, _get_dirty, notify=dirtyChanged)

    def _get_busy(self) -> bool:
        return self._exporting

    exporting = Property(bool, _get_busy, notify=busyChanged)

    def _get_preview_busy(self) -> bool:
        return self._preview_running

    previewBusy = Property(bool, _get_preview_busy, notify=previewChanged)

    def _get_preview(self) -> str:
        return self._preview_url

    previewUrl = Property(str, _get_preview, notify=previewChanged)

    def _get_preview_time(self) -> float:
        return self._preview_time

    previewTime = Property(float, _get_preview_time, notify=previewChanged)

    def _get_current_line(self) -> dict:
        t = self._preview_time
        for line in self._model.lines():
            if line.start <= t < line.end:
                return {"text": line.text, "start": line.start, "end": line.end}
        return {"text": "", "start": 0.0, "end": 0.0}

    currentLine = Property("QVariantMap", _get_current_line, notify=previewChanged)

    def _get_background_url(self) -> str:
        p = self._project.background_path
        return QUrl.fromLocalFile(p).toString() if p else ""

    backgroundUrl = Property(str, _get_background_url, notify=projectChanged)

    playingChanged = Signal()

    def _get_playing(self) -> bool:
        return self._playing

    def _set_playing(self, value: bool) -> None:
        if value == self._playing:
            return
        self._playing = value
        self.playingChanged.emit()
        if not value:  # paused: show the exact libass frame for where we stopped
            self.requestPreview(self._preview_time)

    playing = Property(bool, _get_playing, _set_playing, notify=playingChanged)

    def _get_progress(self) -> float:
        return self._progress

    exportProgress = Property(float, _get_progress, notify=progressChanged)

    def _get_status(self) -> str:
        return self._status

    status = Property(str, _get_status, notify=statusChanged)

    def _get_can_render(self) -> bool:
        return bool(self._project.background_path) and Path(self._project.background_path).exists()

    canPreview = Property(bool, _get_can_render, notify=projectChanged)

    def _get_auto_timing(self) -> bool:
        return self._auto_timing

    autoTiming = Property(bool, _get_auto_timing, notify=autoTimingChanged)

    def _get_can_auto_time(self) -> bool:
        return (bool(self._project.audio_path) and self._duration > 0
                and bool(self._model.lines()) and not self._auto_timing)

    canAutoTime = Property(bool, _get_can_auto_time, notify=autoTimingChanged)

    def _get_can_export(self) -> bool:
        return (self._get_can_render() and bool(self._project.audio_path)
                and bool(self._model.lines()))

    canExport = Property(bool, _get_can_export, notify=projectChanged)

    def _probe_nvenc(self) -> None:
        self._nvenc = nvenc_available()
        self.exportSettingsChanged.emit()

    # ---- helpers ----------------------------------------------------------
    def _set_dirty(self, value: bool) -> None:
        if value != self._dirty:
            self._dirty = value
            self.dirtyChanged.emit()

    def _set_status(self, text: str) -> None:
        self._status = text
        self.statusChanged.emit()

    def _sync_project(self) -> Project:
        self._project.lines = self._model.lines()
        return self._project

    def _load_duration(self) -> None:
        self._duration = 0.0
        self.waveform_peaks = None
        self.waveformChanged.emit()
        path = self._project.audio_path
        if path and Path(path).exists():
            try:
                self._duration = probe_duration(path)
            except Exception as e:  # noqa: BLE001 - surfaced to the user
                self.errorOccurred.emit(f"Could not read audio: {e}")
            else:
                def work() -> None:
                    try:
                        self._peaksDone.emit(path, compute_peaks(path))
                    except Exception:  # noqa: BLE001 - waveform is optional
                        self._peaksDone.emit(path, None)

                threading.Thread(target=work, daemon=True).start()
        self._model.duration = self._duration

    @Slot(str, object)
    def _on_peaks_done(self, path: str, peaks) -> None:
        if path == self._project.audio_path:
            self.waveform_peaks = peaks
            self.waveformChanged.emit()

    def _changed(self, *, restyle: bool = False) -> None:
        self._set_dirty(True)
        self.projectChanged.emit()
        self.autoTimingChanged.emit()
        if restyle:
            self.styleChanged.emit()
        self.requestPreview(self._preview_time)

    def _on_lines_edited(self) -> None:
        self._changed()

    # ---- project slots ----------------------------------------------------
    @Slot()
    def newProject(self) -> None:
        self._project = Project()
        self._project_path = ""
        self._duration = 0.0
        self._model.reset([])
        self._preview_url = ""
        self.previewChanged.emit()
        self.projectChanged.emit()
        self.styleChanged.emit()
        self.exportSettingsChanged.emit()
        self._set_dirty(False)
        self._set_status("New project")

    @Slot(QUrl)
    def openProject(self, url: QUrl) -> None:
        path = _local(url)
        try:
            project = Project.load(path)
        except Exception as e:  # noqa: BLE001
            self.errorOccurred.emit(f"Could not open project: {e}")
            return
        self._project = project
        self._project_path = path
        self._model.reset(project.lines)
        self._load_duration()
        self.projectChanged.emit()
        self.styleChanged.emit()
        self.exportSettingsChanged.emit()
        self._set_dirty(False)
        self.autoTimingChanged.emit()
        self._set_status(f"Opened {Path(path).name}")
        self.requestPreview(self._model.midpoint(0))

    @Slot(result=bool)
    def saveProject(self) -> bool:
        if not self._project_path:
            return False
        try:
            self._sync_project().save(self._project_path)
        except Exception as e:  # noqa: BLE001
            self.errorOccurred.emit(f"Could not save: {e}")
            return False
        self._set_dirty(False)
        self._set_status(f"Saved {Path(self._project_path).name}")
        return True

    @Slot(QUrl)
    def saveProjectAs(self, url: QUrl) -> None:
        path = _local(url)
        if not path.lower().endswith(".json"):
            path += ".lyricproj.json"
        self._project_path = path
        self.projectChanged.emit()
        self.saveProject()

    @Slot(QUrl)
    def setAudio(self, url: QUrl) -> None:
        self._project.audio_path = _local(url)
        self._load_duration()
        self._changed()
        self.autoTimingChanged.emit()
        if self._model.lines() and self._duration:
            self.autoTime()

    @Slot(QUrl)
    def setBackground(self, url: QUrl) -> None:
        self._project.background_path = _local(url)
        self._changed()

    @Slot(QUrl)
    def importLyrics(self, url: QUrl) -> None:
        try:
            parsed = read_lyrics_file(_local(url))
        except Exception as e:  # noqa: BLE001
            self.errorOccurred.emit(f"Could not read lyrics: {e}")
            return
        self._model.reset(spread_evenly(parsed, self._duration or 180.0))
        self._set_status(f"Imported {len(self._model.lines())} lines")
        self._changed()
        self.autoTimingChanged.emit()
        if self._duration:
            self.autoTime()

    @Slot(str)
    def applyLyricsText(self, text: str) -> None:
        """Replace line texts; keep existing timing if the line count is unchanged."""
        parsed = parse_lyrics(text)
        texts = [t for t in parsed if t is not None]
        old = self._model.lines()
        if len(texts) == len(old):
            lines = [Line(t, l.start, l.end) for t, l in zip(texts, old)]
        else:
            lines = spread_evenly(parsed, self._duration or 180.0)
        self._model.reset(lines)
        self._changed()
        if len(texts) != len(old) and self._duration:
            self.autoTime()

    @Slot()
    def spreadEvenly(self) -> None:
        self._model.reset(respread(self._model.lines(), self._duration or 180.0))
        self._changed()

    # ---- automatic timing -------------------------------------------------
    def _run_timing_job(self, status: str, job) -> None:
        self._auto_timing = True
        self.autoTimingChanged.emit()
        self._set_status(status)

        def work() -> None:
            try:
                lines, source, exact = job()
                self._autoTimeDone.emit(lines, source, exact)
            except Exception as e:  # noqa: BLE001
                self._autoTimeDone.emit(None, str(e), False)

        threading.Thread(target=work, daemon=True).start()

    def _features_for(self, path: str) -> autotime.VocalFeatures:
        # Only touched from worker threads, one job at a time.
        if path not in self._features:
            self._features = {path: autotime.analyze(path)}
        return self._features[path]

    @Slot()
    def autoTime(self) -> None:
        """LRCLIB synced lyrics if the song is found there, else a rough audio guess."""
        if not self._get_can_auto_time():
            return
        path, duration = self._project.audio_path, self._duration
        texts = [l.text for l in self._model.lines()]

        def job():
            r = auto_time(path, texts, duration, features=None)
            return r.lines, r.source, r.exact

        self._run_timing_job("Auto-timing: looking up synced lyrics…", job)

    @Slot()
    def guessRestFromPlayhead(self) -> None:
        """Keep lines before the playhead, re-guess the rest from the audio."""
        if not self._get_can_auto_time():
            return
        path, t = self._project.audio_path, self._preview_time
        lines = [Line(l.text, l.start, l.end) for l in self._model.lines()]

        def job():
            out = guess_rest(self._features_for(path), lines, t)
            kept = sum(1 for l in lines if l.start < t)
            return out, f"kept {kept} line(s) before the playhead, guessed the rest from the audio", False

        self._run_timing_job("Guessing the remaining lines…", job)

    @Slot(object, str, bool)
    def _on_auto_time_done(self, lines, source: str, exact: bool) -> None:
        self._auto_timing = False
        self.autoTimingChanged.emit()
        if lines is None:
            self._set_status("Auto-timing failed")
            self.errorOccurred.emit(f"Auto-timing failed: {source}")
            return
        if [l.text for l in lines] != [l.text for l in self._model.lines()]:
            self._set_status("Lyrics changed while auto-timing; nothing applied")
            return
        self._model._push_undo()
        self._model.reset(lines, keep_undo=True)
        self._set_status(("Timing from " if exact else "Timing: ") + source)
        self._changed()

    @Slot(str, "QVariant")
    def setStyleValue(self, key: str, value) -> None:
        if hasattr(value, "name") and not isinstance(value, str):  # QColor
            value = value.name()
        if key == "font_file":  # libass needs the family name inside that file
            try:
                self._project.style["font_family"] = fonts.font_info(resolve_font(value))[0]
            except Exception as e:  # noqa: BLE001
                self.errorOccurred.emit(f"Could not read font: {e}")
                return
        if self._project.style.get(key) == value:
            return
        self._project.style[key] = value
        self._changed(restyle=True)

    @Slot()
    def resetStyle(self) -> None:
        self._project.style = {}
        self._changed(restyle=True)

    # ---- preview ----------------------------------------------------------
    @Slot(float)
    def requestPreview(self, t: float) -> None:
        self._preview_time = max(0.0, t)
        self.previewChanged.emit()
        # While playing, QML draws a live overlay; ffmpeg frames would lag behind the audio.
        if self._playing:
            return
        if self._get_can_render() and not self._preview_timer.isActive():
            self._preview_timer.start()

    def _start_preview(self) -> None:
        if self._preview_running:
            self._preview_pending = True
            return
        self._preview_running = True
        self._preview_pending = False
        self.previewChanged.emit()
        if self._preview_wd is None:
            self._preview_wd = Workdir.create()
        project = copy.deepcopy(self._sync_project())
        self._preview_seq += 1
        out = self._tmp / f"preview_{self._preview_seq % 2}.png"
        t, wd = self._preview_time, self._preview_wd
        duration = self._duration or None

        def work() -> None:
            try:
                render_frame(project, t, out, workdir=wd, duration=duration)
                self._previewDone.emit(str(out), "")
            except Exception as e:  # noqa: BLE001
                self._previewDone.emit("", str(e))

        threading.Thread(target=work, daemon=True).start()

    @Slot(str, str)
    def _on_preview_done(self, path: str, error: str) -> None:
        self._preview_running = False
        if path:
            self._preview_url = QUrl.fromLocalFile(path).toString() + f"?v={self._preview_seq}"
        elif error:
            self._set_status(f"Preview failed: {error.splitlines()[0] if error else ''}")
        self.previewChanged.emit()
        if self._preview_pending:
            self._start_preview()

    # ---- export -----------------------------------------------------------
    @Slot(QUrl)
    def exportVideo(self, url: QUrl) -> None:
        if self._exporting or not self._get_can_export():
            return
        out = _local(url)
        if not out.lower().endswith(".mp4"):
            out += ".mp4"
        project = copy.deepcopy(self._sync_project())
        self._cancel.clear()
        self._exporting = True
        self._progress = 0.0
        self.busyChanged.emit()
        self.progressChanged.emit()
        self._set_status(f"Exporting {Path(out).name}…")

        def work() -> None:
            try:
                started = time.monotonic()
                enc = render_video(project, out, self._exportProgress.emit, self._cancel.is_set)
                self._exportDone.emit(out, f"{enc}, {time.monotonic() - started:.0f}s")
            except RenderCancelled:
                self._exportDone.emit("", "cancelled")
            except Exception as e:  # noqa: BLE001
                self._exportDone.emit("", str(e))

        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def cancelExport(self) -> None:
        self._cancel.set()

    @Slot(float)
    def _on_export_progress(self, frac: float) -> None:
        self._progress = frac
        self.progressChanged.emit()

    @Slot(str, str)
    def _on_export_done(self, out: str, error: str) -> None:
        self._exporting = False
        self.busyChanged.emit()
        if out:
            self._set_status(f"Exported {out} ({error})")
        elif error == "cancelled":
            self._progress = 0.0
            self.progressChanged.emit()
            self._set_status("Export cancelled")
        else:
            self._set_status("Export failed")
            self.errorOccurred.emit(error[-2000:])

    def shutdown(self) -> None:
        self._cancel.set()
        if self._preview_wd:
            self._preview_wd.cleanup()
