"""Project and style-preset data model, stored as small JSON files."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS_DIR = ASSETS / "fonts"
PRESETS_DIR = ASSETS / "presets"

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
    ken_burns: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "StylePreset":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})

    @classmethod
    def load(cls, name_or_path: str) -> "StylePreset":
        p = Path(name_or_path)
        if not p.suffix:
            p = PRESETS_DIR / f"{name_or_path}.json"
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def save(self, path: Path | None = None) -> Path:
        path = path or PRESETS_DIR / f"{self.name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        return path


@dataclass
class Project:
    audio_path: str = ""
    background_path: str = ""
    style_preset: str = "default-bold-outline"
    export: ExportSettings = field(default_factory=ExportSettings)
    lines: list[Line] = field(default_factory=list)
    # Per-project style overrides on top of the named preset (set by the GUI).
    style: dict = field(default_factory=dict)
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
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        return cls(
            version=d.get("version", PROJECT_VERSION),
            audio_path=d.get("audio_path", ""),
            background_path=d.get("background_path", ""),
            style_preset=d.get("style_preset", "default-bold-outline"),
            export=ExportSettings(**d.get("export", {})),
            lines=[Line(**l) for l in d.get("lines", [])],
            style=d.get("style", {}),
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8-sig")))
