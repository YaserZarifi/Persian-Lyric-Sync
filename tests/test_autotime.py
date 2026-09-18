import numpy as np

from lyricvid.autotime import LEAD_IN, SR, analyze_pcm, guess, text_weight

TEXTS = [
    "برام هیچ حسی شبیه تو نیست؛ کنارِ تو درگیرِ آرامشم",
    "همین از تمامِ جهان کافیه",
    "برام هیچ حسی؛ شبیه تو نیست",
    "تو؛ پایانِ هر جستجوی منی",
    "تماشای تو؛ عینِ آرامشه… تو زیباترین، آرزوی منی",
    "منو از این عذاب رها نمی کنی",
]


def synth_song(seed=0):
    """Band = uncorrelated L/R noise; 'vocals' = centred harmonic tones per phrase."""
    rng = np.random.default_rng(seed)
    t_cursor, phrases, parts = 8.0, [], []
    for i, text in enumerate(TEXTS):
        dur = text_weight(text) * 0.07
        phrases.append((t_cursor, t_cursor + dur))
        t_cursor += dur + (6.0 if i == 2 else 0.45)  # instrumental break after line 3
    total = t_cursor + 4.0
    n = int(total * SR)
    t = np.arange(n) / SR
    left = rng.normal(0, 0.05, n)
    right = rng.normal(0, 0.05, n)
    voice = np.zeros(n)
    for a, b in phrases:
        idx = (t >= a) & (t < b)
        f0 = 220 + 40 * np.sin(2 * np.pi * 0.7 * t[idx])
        tone = sum(np.sin(2 * np.pi * k * f0 * t[idx]) / k for k in range(1, 8))
        voice[idx] = 0.25 * tone * (0.7 + 0.3 * np.sin(2 * np.pi * 4 * t[idx]) ** 2)
    stereo = np.stack([left + voice, right + voice], axis=1).astype(np.float32)
    return stereo, phrases


def test_guess_finds_phrase_starts():
    stereo, phrases = synth_song()
    spans = guess(analyze_pcm(stereo), TEXTS)
    for (s, e), (a, b) in zip(spans, phrases):
        assert abs((s + LEAD_IN) - a) < 0.4, (s, a)
        assert e >= b - 0.4
    # the line before the instrumental break must not stay on screen through it
    assert spans[2][1] < phrases[3][0] - 3.0


def test_guess_respects_start_after():
    stereo, phrases = synth_song()
    spans = guess(analyze_pcm(stereo), TEXTS[3:], start_after=phrases[3][0] - 1.0)
    assert abs((spans[0][0] + LEAD_IN) - phrases[3][0]) < 0.4
