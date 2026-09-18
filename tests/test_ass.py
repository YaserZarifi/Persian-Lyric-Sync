from lyricvid.ass import ass_color, build_ass
from lyricvid.models import Line, StylePreset


def test_style_uses_auto_base_direction():
    # Encoding -1 = libass picks RTL for Persian lines; anything else lays them out LTR.
    ass = build_ass([Line("سلام!", 0, 1)], StylePreset(), (1920, 1080))
    style_line = next(l for l in ass.splitlines() if l.startswith("Style:"))
    assert style_line.endswith(",-1")


def test_ass_color_is_bgr_with_alpha():
    assert ass_color("#FF8000") == "&H000080FF"
    assert ass_color("#000000", 128) == "&H80000000"


def test_entrance_animations():
    from lyricvid.ass import entrance_tags

    assert "\t(0,200,0.6,\fscx100\fscy100)" in entrance_tags(StylePreset(animation="pop"), 1920, 1080)
    slide = entrance_tags(StylePreset(animation="slide_up", alignment=2, margin_v=60), 1920, 1080)
    assert "\move(960,1060,960,1020,0,200)" in slide


def test_watermark_text_sits_below_logo():
    s = StylePreset(watermark_text="@chan", watermark_position="top_left")
    ass = build_ass([Line("a", 0, 1)], s, (1920, 1080), duration=30, logo_height=100)
    wm = next(l for l in ass.splitlines() if l.startswith("Style: Watermark"))
    assert wm.split(",")[18] == "7" and wm.split(",")[21] == "150"  # an7, MarginV 40+100+10
    assert "Dialogue: 1,0:00:00.00,0:00:30.00,Watermark" in ass
