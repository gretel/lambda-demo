import re

from lambda_function_readable import lambda_handler, _abbreviate_user_agent as _ua

FAKE_EVENT = {
    "requestContext": {"http": {"sourceIp": "203.0.113.42"}},
    "headers": {
        "user-agent": "Mozilla/5.0 (X11; Linux) Chrome/120.0.6099.71 Safari/537.36"
    },
}


def _body(event=FAKE_EVENT):
    return lambda_handler(event, None)["body"]


def test_status_code():
    assert lambda_handler(FAKE_EVENT, None)["statusCode"] == 200


def test_content_type():
    assert lambda_handler(FAKE_EVENT, None)["headers"]["Content-Type"] == "text/html"


def test_body_is_html():
    body = _body()
    assert body.strip().startswith("<!DOCTYPE html>")
    assert body.strip().endswith("</html>")


def test_scroll_text_present():
    body = _body()
    assert "AWS CLOUD PRACTITIONER" in body
    assert "TEACHER TOM" in body
    assert "AWS LAMBDA" in body
    assert "ON PREMISE??" in body


def test_has_canvas():
    assert "<canvas" in _body()


def test_has_audio():
    assert "AudioContext" in _body()


def test_click_for_sound_hint():
    assert "click for sound" in _body()


def test_greeting_first():
    # Greeting (IP) appears before the static scroll text in the body
    body = _body()
    assert "HI TO" in body
    assert body.index("203.0.113.42") < body.index("KEEP LEARNING")


def test_ip_in_body():
    assert "203.0.113.42" in _body()


def test_ua_in_body():
    assert "Chrome/120" in _body()


def test_ua_abbreviation():
    assert _ua("Mozilla/5.0 Chrome/120.0.6099.71 Safari/537.36") == "Chrome/120"
    assert _ua("Mozilla/5.0 Firefox/121.0") == "Firefox/121"
    assert _ua("something unknown") == "something unknown"


def test_empty_event_fallback():
    body = _body({})
    assert "127.0.0.1" in body
    assert "local" in body


def test_xss_safe():
    evil = {
        "requestContext": {"http": {"sourceIp": "<script>alert(1)</script>"}},
        "headers": {"user-agent": "<img onerror=alert(1)>"},
    }
    body = _body(evil)
    assert "<script>alert" not in body
    assert "<img onerror" not in body


def test_generative_music():
    # Music is now procedurally generated — no hardcoded note arrays
    body = _body()
    assert "Math.random()" in body
    assert "buildScale" in body
