import pytest

from lyricvid.timing import MIN_LEN, apply_drag

SNAP = [(2.0, 5.0), (5.0, 8.0), (9.0, 12.0)]  # 0-1 touch, gap before 2


def test_move_clamped_by_neighbours():
    assert apply_drag(SNAP, 1, "move", 3.0, 60)[1] == (6.0, 9.0)   # stops at next start
    assert apply_drag(SNAP, 1, "move", -1.0, 60)[1] == (5.0, 8.0)  # touching prev: can't go back


def test_ripple_moves_all_following():
    out = apply_drag(SNAP, 1, "ripple", 2.5, 60)
    assert out[0] == SNAP[0] and out[1] == (7.5, 10.5) and out[2] == (11.5, 14.5)
    assert apply_drag(SNAP, 2, "ripple", 100, 20)[2] == (17.0, 20.0)  # clamped at song end


def test_linked_start_edge_drags_previous_end():
    out = apply_drag(SNAP, 1, "start", -1.0, 60)
    assert out[0] == (2.0, 4.0) and out[1] == (4.0, 8.0)
    out = apply_drag(SNAP, 1, "start", -10, 60)
    assert out[0][1] - out[0][0] == pytest.approx(MIN_LEN)


def test_unlinked_end_edge_stops_at_gap():
    assert apply_drag(SNAP, 1, "end", 5.0, 60) == [SNAP[0], (5.0, 9.0), SNAP[2]]
    assert apply_drag(SNAP, 1, "end", -10, 60)[1] == (5.0, 5.0 + MIN_LEN)


def test_v1_presets_still_load():
    from lyricvid.models import StylePreset

    assert StylePreset.from_dict({"ken_burns": False}).ken_burns == "off"
    assert StylePreset.from_dict({"ken_burns": True, "unknown": 1}).ken_burns == "zoom_in"
