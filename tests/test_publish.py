import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from lyricvid.publish import (
    PublishInfo, clean_hashtags, credit_block, fill_template, generate_ai,
)

INFO = dict(artist_fa="احسان خواجه امیری", artist_en="Ehsan Khajeh Amiri",
            title_fa="نبرده رنج", title_en="Naborde Ranj")


def test_template_is_bilingual_and_within_limits():
    info = fill_template(PublishInfo(**INFO, rights_status="content_id"))
    assert info.youtube_title == "احسان خواجه امیری - نبرده رنج | Ehsan Khajeh Amiri - Naborde Ranj (Lyrics)"
    assert len(info.youtube_title) <= 100
    assert "Content ID claim is accepted" in info.description
    assert "#PersianMusic" in info.hashtags and len(info.hashtags) <= 15


def test_needs_review_adds_no_rights_claim():
    block = credit_block(PublishInfo(**INFO))
    assert "Artist: Ehsan Khajeh Amiri" in block
    assert "permission" not in block and "Content ID" not in block


def test_clean_hashtags():
    assert clean_hashtags(["#Lyrics", "lyrics", "متن آهنگ", "a,b"]) == ["#Lyrics", "#متن_آهنگ", "#ab"]


class FakeWorker(BaseHTTPRequestHandler):
    reply: dict = {}
    seen: dict = {}

    def do_POST(self):  # noqa: N802
        FakeWorker.seen = {"auth": self.headers["authorization"],
                           "body": json.loads(self.rfile.read(int(self.headers["content-length"])))}
        status = 401 if self.headers["authorization"] != "Bearer tok" else 200
        payload = json.dumps(FakeWorker.reply if status == 200 else {"error": "unauthorized"})
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))

    def log_message(self, *args):
        pass


@pytest.fixture()
def worker_url():
    server = HTTPServer(("127.0.0.1", 0), FakeWorker)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_generate_ai_keeps_user_values_and_adds_credits(worker_url):
    model_json = {"artist_fa": "WRONG", "title_fa": "نبرده رنج", "title_en": "Naborde Ranj",
                  "youtube_title": "T", "description": "hook\nhook en", "hashtags": ["#a", "b"]}
    FakeWorker.reply = {"text": "Sure!\n```json\n" + json.dumps(model_json, ensure_ascii=False) + "\n```",
                        "provider": "workers-ai", "model": "@cf/openai/gpt-oss-120b"}
    info = PublishInfo(artist_fa="احسان خواجه امیری", artist_en="Ehsan Khajeh Amiri",
                       rights_status="permission")
    out = generate_ai(info, ["برام هیچ حسی شبیه تو نیست"], worker_url, "tok")
    assert out.artist_fa == "احسان خواجه امیری"  # user value wins over the model
    assert out.title_en == "Naborde Ranj"  # missing value filled in
    assert out.description.startswith("hook\nhook en\n\n")
    assert "Published with permission from Ehsan Khajeh Amiri." in out.description
    assert out.description.rstrip().endswith("#a #b")
    assert out.generated_by == "workers-ai · @cf/openai/gpt-oss-120b"
    assert "برام هیچ حسی" in FakeWorker.seen["body"]["prompt"]


def test_generate_ai_bad_token(worker_url):
    with pytest.raises(RuntimeError, match="token"):
        generate_ai(PublishInfo(**INFO), [], worker_url, "wrong")
