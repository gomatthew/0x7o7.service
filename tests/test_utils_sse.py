import json

from src.server import utils


class FakeResponse:
    def __init__(self, lines):
        self.lines = lines
        self.status_checked = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        self.status_checked = True

    def iter_lines(self):
        yield from self.lines


def test_http_stream_request_parses_only_data_fields(monkeypatch):
    response = FakeResponse([
        "event: ping",
        "",
        ": keepalive",
        "id: 42",
        "data: not json",
        'data: {"event":"message","answer":"hello"}',
        "data: [DONE]",
        'data: {"event":"message","answer":"must not be emitted"}',
    ])
    monkeypatch.setattr(utils.httpx, "stream", lambda **_kwargs: response)

    assert list(utils.http_stream_request("https://dify.invalid", "POST")) == [
        json.dumps({"event": "message", "answer": "hello"}, separators=(",", ":")),
    ]
    assert response.status_checked is True


def test_http_stream_request_forwards_error_then_stops(monkeypatch):
    response = FakeResponse([
        'data: {"event":"error","message":"upstream failed"}',
        'data: {"event":"message","answer":"must not be emitted"}',
    ])
    monkeypatch.setattr(utils.httpx, "stream", lambda **_kwargs: response)

    assert list(utils.http_stream_request("https://dify.invalid", "POST")) == [
        '{"event":"error","message":"upstream failed"}',
    ]
