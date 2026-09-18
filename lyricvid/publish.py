"""YouTube publish text: title, description, hashtags, artist credit and rights note.

The AI (through the Cloudflare Worker in worker/) only writes the creative parts. The
credit and rights lines are always assembled here from what the user entered, so a
model can never invent or drop them.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field, fields

RIGHTS_STATUSES = ("needs_review", "permission", "content_id", "royalty_free")
TITLE_MAX = 100  # YouTube limit
DESCRIPTION_MAX = 5000
HASHTAGS_MAX = 15


@dataclass
class PublishInfo:
    artist_fa: str = ""
    artist_en: str = ""
    title_fa: str = ""
    title_en: str = ""
    label: str = ""
    rights_status: str = "needs_review"
    rights_notes: str = ""
    # Generated (editable) output
    youtube_title: str = ""
    description: str = ""
    hashtags: list[str] = field(default_factory=list)
    generated_by: str = ""

    @classmethod
    def from_dict(cls, d: dict | None) -> "PublishInfo":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})

    def to_dict(self) -> dict:
        return asdict(self)


# ---- deterministic parts ---------------------------------------------------------

def _join(*parts: str, sep: str = " - ") -> str:
    return sep.join(p.strip() for p in parts if p and p.strip())


def credit_block(info: PublishInfo) -> str:
    """Bilingual credit + rights lines, built only from what the user entered."""
    artist_fa = info.artist_fa or info.artist_en
    artist_en = info.artist_en or info.artist_fa
    title = _join(info.title_fa, info.title_en, sep=" / ")
    lines = [f"🎤 خواننده: {artist_fa}" if artist_fa else "",
             f"🎤 Artist: {artist_en}" if artist_en else "",
             f"🎵 آهنگ / Song: {title}" if title else "",
             f"🏷 Label: {info.label}" if info.label else ""]
    owner = info.label or artist_en or "the original artist"
    owner_fa = info.label or artist_fa or "صاحب اثر"
    rights = {
        "permission": [f"منتشر شده با اجازه‌ی {owner_fa}.", f"Published with permission from {owner}."],
        "content_id": [f"تمامی حقوق این اثر متعلق به {owner_fa} است. این ویدیو صرفاً برای معرفی اثر ساخته شده است.",
                       f"All rights to this music belong to {owner}. This lyric video is made for "
                       "promotion only; any Content ID claim is accepted."],
        "royalty_free": ["موسیقی بدون حق نشر (Royalty-free).", "Music: royalty-free."],
        "needs_review": [],
    }[info.rights_status if info.rights_status in RIGHTS_STATUSES else "needs_review"]
    block = [l for l in lines if l] + ([""] + rights if rights else [])
    if info.rights_notes.strip():
        block += [info.rights_notes.strip()]
    return "\n".join(block).strip()


def clean_hashtags(tags) -> list[str]:
    if isinstance(tags, str):
        tags = re.split(r"[\s,،]+", tags)
    out: list[str] = []
    for t in tags or []:
        t = re.sub(r"[^\w‌]", "", str(t).replace(" ", "_").lstrip("#"))
        if t and t.lower() not in {x.lower() for x in out}:
            out.append(t)
    return [f"#{t}" for t in out[:HASHTAGS_MAX]]


def assemble_description(body: str, info: PublishInfo, hashtags: list[str]) -> str:
    parts = [body.strip(), credit_block(info), " ".join(hashtags)]
    return "\n\n".join(p for p in parts if p)[:DESCRIPTION_MAX]


def template_title(info: PublishInfo) -> str:
    fa = _join(info.artist_fa, info.title_fa)
    en = _join(info.artist_en, info.title_en)
    title = _join(fa, en + " (Lyrics)" if en else "", sep=" | ") or "Lyric video"
    return title[:TITLE_MAX]


def template_hashtags(info: PublishInfo) -> list[str]:
    base = [info.artist_fa, info.artist_en, info.title_fa, info.title_en,
            "متن_آهنگ", "آهنگ_جدید", "PersianMusic", "Lyrics", "IranianMusic"]
    return clean_hashtags([b.replace(" ", "_") for b in base if b])


def fill_template(info: PublishInfo) -> PublishInfo:
    """Offline fallback: no AI, just a clean bilingual layout."""
    tags = template_hashtags(info)
    body_lines = [
        f"متن آهنگ {info.title_fa or info.title_en} از {info.artist_fa or info.artist_en}"
        if (info.title_fa or info.title_en) else "",
        f"{info.artist_en or info.artist_fa} - {info.title_en or info.title_fa} (Lyrics)"
        if (info.title_en or info.title_fa) else "",
    ]
    info.youtube_title = template_title(info)
    info.hashtags = tags
    info.description = assemble_description("\n".join(l for l in body_lines if l), info, tags)
    info.generated_by = "template"
    return info


# ---- AI -----------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You write YouTube metadata for a Persian lyric-video channel (the 7clouds style: one "
    "song per video, lyrics on screen). You are fluent in Persian and English and know "
    "the standard English spellings Persian artists use on streaming services. "
    "Reply with a single JSON object and nothing else."
)


def build_prompt(info: PublishInfo, lyrics: list[str]) -> str:
    excerpt = "\n".join(lyrics[:12])
    known = {k: v for k, v in {
        "artist_fa": info.artist_fa, "artist_en": info.artist_en,
        "title_fa": info.title_fa, "title_en": info.title_en,
    }.items() if v}
    return f"""Song information we already know (keep these values exactly, fill in the missing ones):
{json.dumps(known, ensure_ascii=False, indent=2)}

First lyric lines (Persian):
{excerpt}

Return JSON with these keys:
- "artist_fa", "title_fa": the artist and song name in Persian script.
- "artist_en", "title_en": the usual English/Finglish spelling (e.g. "Ehsan Khajeh Amiri", "Naborde Ranj").
- "youtube_title": at most 100 characters, format "<artist_fa> - <title_fa> | <artist_en> - <title_en> (Lyrics)". Shorten the English half first if it is too long.
- "description": 3-5 short lines. Line 1: a one-sentence Persian hook about the song's mood (no invented facts about release dates, albums or awards). Line 2: the same in English. Then one Persian and one English line inviting viewers to subscribe for more Persian lyric videos. Do not include hashtags, credits or copyright text; those are added separately.
- "hashtags": 8-12 hashtags without spaces, mixing Persian and English: artist, song, mood, and general ones like #متن_آهنگ #PersianMusic #Lyrics.
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the AI reply")
    return json.loads(text[start:end + 1])


def call_worker(url: str, token: str, system: str, prompt: str, timeout: float = 90.0) -> dict:
    req = urllib.request.Request(
        url.rstrip("/") + "/",
        data=json.dumps({"system": system, "prompt": prompt, "max_tokens": 1500}).encode("utf-8"),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}",
                 "user-agent": "PersianLyricSync/0.1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        if e.code == 401:
            raise RuntimeError("The Worker rejected the app token (check AI settings)") from e
        raise RuntimeError(f"Worker error {e.code}: {detail}") from e


def generate_ai(info: PublishInfo, lyrics: list[str], url: str, token: str) -> PublishInfo:
    reply = call_worker(url, token, SYSTEM_PROMPT, build_prompt(info, lyrics))
    data = _extract_json(reply.get("text", ""))
    for key in ("artist_fa", "artist_en", "title_fa", "title_en"):
        if not getattr(info, key) and isinstance(data.get(key), str):
            setattr(info, key, data[key].strip())
    tags = clean_hashtags(data.get("hashtags")) or template_hashtags(info)
    title = str(data.get("youtube_title") or "").strip() or template_title(info)
    info.youtube_title = title[:TITLE_MAX]
    info.hashtags = tags
    info.description = assemble_description(str(data.get("description") or ""), info, tags)
    info.generated_by = f"{reply.get('provider', 'ai')} · {reply.get('model', '')}".strip(" ·")
    return info
