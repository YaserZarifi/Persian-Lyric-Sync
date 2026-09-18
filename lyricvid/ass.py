"""Build an ASS subtitle document from a project + style preset."""
from __future__ import annotations

from .models import Line, Project, StylePreset


def ass_color(hex_color: str, alpha: int = 0) -> str:
    """#RRGGBB -> &HAABBGGRR (ASS alpha: 00 opaque, FF transparent)."""
    h = hex_color.lstrip("#")
    if len(h) == 8:  # #AARRGGBB, as Qt's color.toString(HexArgb) produces
        alpha = 255 - int(h[:2], 16)
        h = h[2:]
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ass_time(seconds: float) -> str:
    cs = max(0, round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def escape_text(text: str) -> str:
    # Braces open override blocks and backslashes start tags; neutralise both.
    return (text.replace("\\", "⧵")
                .replace("{", "｛").replace("}", "｝")
                .replace("\n", "\\N"))


def build_ass(lines: list[Line], style: StylePreset, size: tuple[int, int]) -> str:
    w, h = size
    # Style sizes are authored for 1080p; scale for other export heights.
    k = h / 1080
    fields = [
        "Default", style.font_family, round(style.font_size * k),
        ass_color(style.fill_color), ass_color(style.fill_color),
        ass_color(style.outline_color), ass_color(style.shadow_color, style.shadow_alpha),
        0, 0, 0, 0, 100, 100, 0, 0, 1,
        round(style.outline_width * k, 2), round(style.shadow_depth * k, 2),
        style.alignment, round(style.margin_h * k), round(style.margin_h * k),
        # Encoding -1 makes libass auto-detect the base direction (RTL for Persian);
        # the default LTR base puts line-final punctuation on the wrong side.
        round(style.margin_v * k), -1,
    ]
    out = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {w}",
        f"PlayResY: {h}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: " + ",".join(str(f) for f in fields),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    fade = f"{{\\fad({style.fade_in_ms},{style.fade_out_ms})}}"
    for line in lines:
        if line.end <= line.start or not line.text.strip():
            continue
        out.append(
            f"Dialogue: 0,{ass_time(line.start)},{ass_time(line.end)},Default,,0,0,0,,"
            f"{fade}{escape_text(line.text)}"
        )
    return "\n".join(out) + "\n"


def project_to_ass(project: Project) -> str:
    return build_ass(project.lines, project.resolved_style(), project.export.size)
