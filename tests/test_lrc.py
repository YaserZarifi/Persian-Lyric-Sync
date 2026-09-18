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
    assert spans[1][0] == 30.48 and spans[1][1] == 41.0  # break: blank marker + 1 s
    assert spans[2][0] in (55.0, 60.0)  # either repeat is acceptable
    assert spans[3][0] == 65.0


def test_consensus_takes_median_start():
    shifted = [LRC.replace("[00:20.89]", f"[00:{20.89 + d:05.2f}]") for d in (0.0, 0.4, 3.0)]
    spans = consensus(USER, [parse_lrc(v) for v in shifted], 80.0)
    assert spans[0][0] == 21.29  # the 3 s outlier doesn't win


def test_blank_after_every_line_does_not_hide_lyrics():
    # Uploads that mark the end of every sung phrase: short gaps must not blank the screen.
    lrc = parse_lrc("""[00:29.44] تو ماهی و من ماهی این برکه ی کاشی
[00:31.59]
[00:36.34] اندوه بزرگیست زمانی که نباشی
[00:38.51]
[00:55.00] آه از نفس پاک تو و صبح نشابور
""")
    spans = align_to_lines(["تو ماهی و من ماهی این برکه ی کاشی", "اندوه بزرگیست زمانی که نباشی",
                            "آه از نفس پاک تو و صبح نشابور"], lrc, 70.0)
    assert spans[0] == (29.44, 36.34)  # 4.8 s gap: stays until the next line
    assert spans[1] == (36.34, 39.51)  # 16 s break: hides 1 s after the marker


def test_close_gaps():
    from lyricvid.timing import close_gaps

    assert close_gaps([(1, 2), (5, 6), (20, 21)]) == [(1, 5), (5, 6), (20, 21)]
