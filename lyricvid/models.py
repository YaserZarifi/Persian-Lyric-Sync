"""Project and style-preset data model, stored as small JSON files."""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

# Bundled files: the repo root, or PyInstaller's unpack dir in the packaged app.
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ASSETS = ROOT / "assets"
FONTS_DIR = ASSETS / "fonts"
PRESETS_DIR = ASSETS / "presets"  # built-in, read-only

# Per-user data, kept out of the repo: saved presets and added fonts.
USER_DIR = Path(os.environ.get("APPDATA", Path.home())) / "PersianLyricSync"
USER_PRESETS_DIR = USER_DIR / "presets"
USER_FONTS_DIR = USER_DIR / "fonts"

KEN_BURNS_MODES = ("off", "zoom_in", "zoom_out", "pan_left", "pan_right")
ANIMATIONS = ("fade", "pop", "slide_up")
WATERMARK_POSITIONS = ("top_left", "top_right", "bottom_left", "bottom_right")

PROJECT_VERSION = 1


@dataclass
class Line:
    text: str
    start: float
    end: float


@dataclass
class ExportSettings:
    resolution: str = "1920x1080"
    fps: int = 30
    encoder: str = "auto"  # auto (GPU if available) | gpu | cpu

    @property
    def size(self) -> tuple[int, int]:
        w, h = self.resolution.lower().split("x")
        return int(w), int(h)


@dataclass
class StylePreset:
    name: str = "default-bold-outline"
    font_file: str = "Vazirmatn-FD-Black.ttf"
    font_family: str = "Vazirmatn FD Black"
    font_size: int = 96
    fill_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: float = 8.0
    shadow_color: str = "#000000"
    shadow_depth: float = 3.0
    shadow_alpha: int = 128  # 0 = opaque, 255 = invisible (ASS convention)
    alignment: int = 5  # numpad layout: 5 = middle center
    margin_h: int = 120
    margin_v: int = 60
    fade_in_ms: int = 200
    fade_out_ms: int = 200
    animation: str = "fade"  # one of ANIMATIONS
    # Background
    ken_burns: str = "zoom_in"  # one of KEN_BURNS_MODES
    ken_burns_amount: float = 0.10  # extra zoom over the whole song
    bg_dim: float = 0.20  # 0 = untouched, 1 = black
    bg_blur: float = 0.0  # gaussian sigma at 1080p
    # Channel branding
    watermark_image: str = ""
    watermark_text: str = ""
    watermark_position: str = "top_right"
    watermark_scale: float = 0.12  # logo width as a fraction of the video width
    watermark_opacity: float = 0.85

    @classmethod
    def from_dict(cls, d: dict) -> "StylePreset":
        known = {f.name for f in fields(cls)}
        d = {k: v for k, v in d.items() if k in known}
        if isinstance(d.get("ken_burns"), bool):  # v1 presets stored a bool
            d["ken_burns"] = "zoom_in" if d["ken_burns"] else "off"
        return cls(**d)

    @classmethod
    def load(cls, name_or_path: str) -> "StylePreset":
        return cls.from_dict(json.loads(preset_path(name_or_path).read_text(encoding="utf-8")))

    def save(self, path: Path | None = None) -> Path:
        path = path or USER_PRESETS_DIR / f"{slugify(self.name)}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        return path


def slugify(name: str) -> str:
    slug = re.sub(r"[^\w\-]+", "-", name.strip(), flags=re.UNICODE).strip("-").lower()
    return slug or "preset"


def preset_path(name_or_path: str) -> Path:
    """User presets shadow built-in ones of the same name."""
    p = Path(name_or_path)
    if p.suffix:
        return p
    for d in (USER_PRESETS_DIR, PRESETS_DIR):
        cand = d / f"{name_or_path}.json"
        if cand.exists():
            return cand
    raise FileNotFoundError(name_or_path)


def list_presets() -> list[str]:
    names = {p.stem for d in (PRESETS_DIR, USER_PRESETS_DIR) if d.exists() for p in d.glob("*.json")}
    return sorted(names, key=lambda n: (n != "default-bold-outline", n))


def font_dirs() -> list[Path]:
    return [FONTS_DIR, USER_FONTS_DIR]


def resolve_font(font_file: str) -> Path:
    p = Path(font_file)
    if p.is_absolute():
        return p
    for d in font_dirs():
        if (d / p).exists():
            return d / p
    return FONTS_DIR / p


@dataclass
class Project:
    audio_path: str = ""
    background_path: str = ""
    style_preset: str = "default-bold-outline"
    export: ExportSettings = field(default_factory=ExportSettings)
    lines: list[Line] = field(default_factory=list)
    # Per-project style overrides on top of the named preset (set by the GUI).
    style: dict = field(default_factory=dict)
    # YouTube metadata, credits and rights note (lyricvid.publish.PublishInfo).
    publish: dict = field(default_factory=dict)
    version: int = PROJECT_VERSION

    def resolved_style(self) -> StylePreset:
        try:
            base = asdict(StylePreset.load(self.style_preset))
        except FileNotFoundError:
            base = asdict(StylePreset())
        base.update(self.style)
        return StylePreset.from_dict(base)

    def to_dict(self) -> dict:
        d = {
            "version": self.version,
            "audio_path": self.audio_path,
            "background_path": self.background_path,
            "style_preset": self.style_preset,
            "export": asdict(self.export),
            "lines": [asdict(l) for l in self.lines],
        }
        if self.style:
            d["style"] = self.style
        if self.publish:
            d["publish"] = self.publish
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        return cls(
            version=d.get("version", PROJECT_VERSION),
            audio_path=d.get("audio_path", ""),
            background_path=d.get("background_path", ""),
            style_preset=d.get("style_preset", "default-bold-outline"),
            export=ExportSettings(**{k: v for k, v in d.get("export", {}).items()
                                     if k in {f.name for f in fields(ExportSettings)}}),
            lines=[Line(**l) for l in d.get("lines", [])],
            style=d.get("style", {}),
            publish=d.get("publish", {}),
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8-sig")))
