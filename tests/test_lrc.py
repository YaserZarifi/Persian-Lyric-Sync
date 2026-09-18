from lyricvid.lrc import align_to_lines, consensus, letters, parse_lrc

LRC = """[00:20.89] برام هیچ حسی شبیه تو نیست
[00:25.52] کنار تو درگیر آرامشم
[00:30.48] همین از تمام جهان کافیه
[00:34.55] همین که کنارت نفس میکشم
[00:40.00]
[00:55.00] همه شهر میگرده دنبال تو
[01:00.00] همه شهر میگرده دنبال تو
[01:05.00] منو از این عذاب رها نمیکنی
"""

# The user's txt merges pairs of LRC lines, adds diacritics/punctuation/ZWNJ, uses
# Arabic ي, and has the repeated line only once.
USER = [
    "برام هیچ حسی شبیه تو نیست؛ کنارِ تو درگیرِ آرامشم…",
    "همين از تمامِ جهان کافیه… همین که کنارت، نفس می‌کشم",
    "همه شهر می‌گرده دنبالِ تو…",
    "منو از این عذاب رها نمی کنی",
]


def test_letters_ignores_spelling_noise():
    assert letters("نفس می‌کشم!") == letters("نفس میکشم")
    assert letters("همين") == letters("همین")


def test_merged_lines_take_first_stamp_and_end_at_break():
    spans = align_to_lines(USER, parse_lrc(LRC), 80.0)
    assert spans[0] == (20.89, 30.48)
    assert spans[1][0] == 30.48 and spans[1][1] == 40.0  # ends at the blank marker
    assert spans[2][0] in (55.0, 60.0)  # either repeat is acceptable
    assert spans[3][0] == 65.0


def test_consensus_takes_median_start():
    shifted = [LRC.replace("[00:20.89]", f"[00:{20.89 + d:05.2f}]") for d in (0.0, 0.4, 3.0)]
    spans = consensus(USER, [parse_lrc(v) for v in shifted], 80.0)
    assert spans[0][0] == 21.29  # the 3 s outlier doesn't win
