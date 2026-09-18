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


_CORNER_ALIGN = {"top_left": 7, "top_right": 9, "bottom_left": 1, "bottom_right": 3}


def _style_line(name: str, family: str, size: int, fill: str, outline: str, back: str,
                outline_w: float, shadow: float, align: int, ml: int, mr: int, mv: int) -> str:
    fields = [name, family, size, fill, fill, outline, back, 0, 0, 0, 0, 100, 100, 0, 0, 1,
              outline_w, shadow, align, ml, mr, mv,
              # Encoding -1 makes libass auto-detect the base direction (RTL for Persian);
              # the default LTR base puts line-final punctuation on the wrong side.
              -1]
    return "Style: " + ",".join(str(f) for f in fields)


def _anchor(style: StylePreset, w: int, h: int, k: float) -> tuple[int, int]:
    """Screen point libass anchors the line to, for \\move-based animation."""
    y = {2: h - style.margin_v * k, 8: style.margin_v * k}.get(style.alignment, h / 2)
    return round(w / 2), round(y)


def entrance_tags(style: StylePreset, w: int, h: int) -> str:
    k = h / 1080
    tags = f"\\fad({style.fade_in_ms},{style.fade_out_ms})"
    dur = max(style.fade_in_ms, 150)
    if style.animation == "pop":
        tags += f"\\fscx86\\fscy86\\t(0,{dur},0.6,\\fscx100\\fscy100)"
    elif style.animation == "slide_up":
        x, y = _anchor(style, w, h, k)
        tags = f"\\an{style.alignment}" + tags + f"\\move({x},{y + round(40 * k)},{x},{y},0,{dur})"
    return "{" + tags + "}"


def build_ass(
    lines: list[Line],
    style: StylePreset,
    size: tuple[int, int],
    duration: float | None = None,
    logo_height: int = 0,
) -> str:
    w, h = size
    # Style sizes are authored for 1080p; scale for other export heights.
    k = h / 1080
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
        _style_line("Default", style.font_family, round(style.font_size * k),
                    ass_color(style.fill_color), ass_color(style.outline_color),
                    ass_color(style.shadow_color, style.shadow_alpha),
                    round(style.outline_width * k, 2), round(style.shadow_depth * k, 2),
                    style.alignment, round(style.margin_h * k), round(style.margin_h * k),
                    round(style.margin_v * k)),
    ]
    wm_text = style.watermark_text.strip()
    if wm_text:
        alpha = round(255 * (1 - max(0.0, min(1.0, style.watermark_opacity))))
        margin = round(40 * k)
        # Sits just below/above the logo when both are used in the same corner.
        mv = margin + (logo_height + round(10 * k) if logo_height else 0)
        out.append(_style_line(
            "Watermark", style.font_family, round(34 * k),
            ass_color(style.fill_color, alpha), ass_color(style.outline_color, alpha),
            ass_color(style.shadow_color, 255), round(2 * k, 2), 0,
            _CORNER_ALIGN.get(style.watermark_position, 9), margin, margin, mv))
    out += [
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    tags = entrance_tags(style, w, h)
    for line in lines:
        if line.end <= line.start or not line.text.strip():
            continue
        out.append(
            f"Dialogue: 0,{ass_time(line.start)},{ass_time(line.end)},Default,,0,0,0,,"
            f"{tags}{escape_text(line.text)}"
        )
    if wm_text:
        end = duration if duration else max((l.end for l in lines), default=0) + 10
        out.append(f"Dialogue: 1,{ass_time(0)},{ass_time(end)},Watermark,,0,0,0,,"
                   f"{escape_text(wm_text)}")
    return "\n".join(out) + "\n"


def project_to_ass(project: Project, duration: float | None = None, logo_height: int = 0) -> str:
    return build_ass(project.lines, project.resolved_style(), project.export.size,
                     duration, logo_height)
