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
