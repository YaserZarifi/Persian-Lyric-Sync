# Persian Lyric Sync

Windows desktop app that turns an MP3, Persian lyrics and a background image into a
7clouds-style lyric video: bold outlined text, one line at a time, 1920x1080 MP4.

- **Correct Persian rendering**: text is rendered by libass (HarfBuzz + FriBidi) inside
  ffmpeg, so joining, RTL order, ZWNJ and mixed Persian/Latin lines come out right, and
  the preview frame matches the export.
- **Automatic first-pass timing**: synced lyrics from [LRCLIB](https://lrclib.net) are
  aligned letter by letter onto your own lines (median of all matching versions);
  otherwise a rough guess from the audio.
- **Draggable timeline**: waveform, drag lines to move, edges to resize, Shift+drag to
  shift everything after, arrow keys to nudge the selected line, playback with a live
  preview, undo. No lyrics file? Fetch the text and timing from LRCLIB.
- **Lyric-video look**: Ken Burns pan/zoom, background darken/blur, entrance animations
  (fade, pop, slide up), any TTF/OTF font, logo and channel-name watermark, all saved as
  reusable named presets.
- **Fast export**: NVIDIA NVENC when available (CPU x264 otherwise), 1080p/1440p/4K,
  30/60 fps. A 3:21 song exports in about 30 s (about 60 s with Ken Burns) on a laptop.

## Requirements

- Windows, [uv](https://docs.astral.sh/uv/)
- ffmpeg built with libass (e.g. the gyan.dev full build: `winget install Gyan.FFmpeg`)

## Run

```bash
uv run python app/main.py                     # GUI
uv run python app/main.py project.lyricproj.json
```

CLI:

```bash
uv run python -m lyricvid init --audio song.mp3 --lyrics-txt lyrics.txt --bg bg.jpg -o project.json
uv run python -m lyricvid render project.json -o out.mp4
uv run python -m lyricvid frame project.json --t 42 -o frame.png
```

Tests: `uv run --with pytest pytest -q tests`

## Windows app

```bash
uv run pyinstaller PersianLyricSync.spec --noconfirm   # -> dist/PersianLyricSync/PersianLyricSync.exe
powershell -File tools/make_shortcut.ps1               # desktop shortcut
```

ffmpeg is not bundled; it must be on PATH. Logs: `%APPDATA%\PersianLyricSyncpp.log`.

Auto-timing sends the song's title, artist and duration to lrclib.net (use `--offline`
on the CLI to skip it).

## Font

Bundles [Vazirmatn](https://github.com/rastikerdar/vazirmatn) (SIL Open Font License,
see `assets/fonts/OFL.txt`).
