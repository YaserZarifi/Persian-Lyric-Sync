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
  shift everything after, playback with a live lyric overlay, undo.

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

Auto-timing sends the song's title, artist and duration to lrclib.net (use `--offline`
on the CLI to skip it).

## Font

Bundles [Vazirmatn](https://github.com/rastikerdar/vazirmatn) (SIL Open Font License,
see `assets/fonts/OFL.txt`).
