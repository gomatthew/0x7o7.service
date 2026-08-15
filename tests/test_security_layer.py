# -*- coding: utf-8 -*-
import asyncio
from types import SimpleNamespace

from fastapi import BackgroundTasks

from src.server.service.auth_service import user_login
from src.server.service.user_service import send_verify_code, user_register
from src.server.utils import RateLimitException, ai_rate_limit, get_client_ip


class FakeRequest:
    def __init__(self, ip="127.0.0.1", token=None, authorization=None):
        self.client = SimpleNamespace(host=ip)
        self.headers = {}
        if authorization:
            self.headers["authorization"] = authorization
        self.cookies = {}
        if token:
            self.cookies["access_token"] = token


class FakeResponse:
    def __init__(self):
        self.cookies = {}

    def set_cookie(self, **kwargs):
        self.cookies[kwargs["key"]] = kwargs


def run(coro):
    return asyncio.run(coro)


def test_send_verify_code_success(monkeypatch):
    calls = {}

    async def fake_exists(key):
        return False

    async def fake_rate_limit(key, limit, ttl):
        calls["rate_key"] = key
        return False, 1

    async def fake_set(key, value, ex):
        calls.setdefault("sets", []).append((key, value, ex))
        return True

    monkeypatch.setattr("src.server.service.user_service.async_exists", fake_exists)
    monkeypatch.setattr("src.server.service.user_service.async_rate_limit", fake_rate_limit)
    monkeypatch.setattr("src.server.service.user_service.async_set", fake_set)
    monkeypatch.setattr("src.server.service.user_service.send_mail", lambda **kwargs: None)

    resp = run(send_verify_code(FakeRequest(), BackgroundTasks(), email="USER@example.com"))

    assert resp["status"] == 200
    assert calls["sets"][0][0] == "verify_code:user@example.com"
    assert len(calls["sets"][0][1]) == 6
    assert calls["sets"][0][2] == 600
    assert calls["sets"][1][0] == "verify_cooldown:user@example.com"
    assert calls["sets"][1][2] == 60


def test_send_verify_code_cooldown(monkeypatch):
    async def fake_exists(key):
        return key.startswith("verify_cooldown")

    monkeypatch.setattr("src.server.service.user_service.async_exists", fake_exists)

    resp = run(send_verify_code(FakeRequest(), BackgroundTasks(), email="a@test.com"))

    assert resp["status"] == 429
    assert resp["message"] == "verify.cooldown"


def test_register_verify_code_success(monkeypatch):
    deleted = []
    created = {}

    async def fake_exists(key):
        return False

    async def fake_get(key):
        return "123456"

    async def fake_delete(key):
        deleted.append(key)
        return True

    monkeypatch.setattr("src.server.service.user_service.async_exists", fake_exists)
    monkeypatch.setattr("src.server.service.user_service.async_get", fake_get)
    monkeypatch.setattr("src.server.service.user_service.async_delete", fake_delete)
    monkeypatch.setattr("src.server.service.user_service.user_checkin_from_db", lambda **kwargs: ("success", True, 200))
    def fake_add_user(user_obj):
        created["user"] = user_obj
        return 7

    monkeypatch.setattr("src.server.service.user_service.add_user", fake_add_user)
    monkeypatch.setattr("src.server.service.user_service.send_mail", lambda **kwargs: None)

    resp = run(user_register(
        FakeRequest(),
        BackgroundTasks(),
        user_nickname="Demo",
        mail="a@test.com",
        phone=None,
        user_password="password",
        verify_code="123456",
    ))

    assert resp["status"] == 200
    assert resp["data"]["user_id"] == 7
    assert created["user"].role == "guest"
    assert "verify_code:a@test.com" in deleted
    assert "verify_fail:a@test.com" in deleted


def test_register_verify_code_fail_lock(monkeypatch):
    async def fake_exists(key):
        return False

    async def fake_get(key):
        return "123456"

    async def fake_rate_limit(key, limit, ttl):
        return True, 6

    monkeypatch.setattr("src.server.service.user_service.async_exists", fake_exists)
    monkeypatch.setattr("src.server.service.user_service.async_get", fake_get)
    monkeypatch.setattr("src.server.service.user_service.async_rate_limit", fake_rate_limit)

    resp = run(user_register(
        FakeRequest(),
        BackgroundTasks(),
        user_nickname="Demo",
        mail="a@test.com",
        phone=None,
        user_password="password",
        verify_code="000000",
    ))

    assert resp["status"] == 429
    assert resp["message"] == "verify.locked"


def test_login_ip_rate_limit(monkeypatch):
    async def fake_rate_limit(key, limit, ttl):
        return True, 6

    monkeypatch.setattr("src.server.service.auth_service.async_rate_limit", fake_rate_limit)

    resp = run(user_login(FakeRequest(), FakeResponse(), BackgroundTasks(), username="a@test.com", password="bad"))

    assert resp["status"] == 429
    assert resp["message"] == "login.rateLimited"


def test_ai_rate_limit_guest(monkeypatch):
    async def fake_rate_limit(key, limit, ttl):
        if key.startswith("ai_guest"):
            return True, 4
        return False, 1

    monkeypatch.setattr("src.server.utils.async_rate_limit", fake_rate_limit)

    try:
        run(ai_rate_limit(FakeRequest(), token=None))
    except RateLimitException as e:
        assert e.message == "ai.guestLimit"
    else:
        raise AssertionError("guest limit should raise")


def test_ai_rate_limit_ip(monkeypatch):
    async def fake_rate_limit(key, limit, ttl):
        if key.startswith("ai_ip"):
            return True, 11
        return False, 1

    monkeypatch.setattr("src.server.utils.async_rate_limit", fake_rate_limit)

    try:
        run(ai_rate_limit(FakeRequest(), token=None))
    except RateLimitException as e:
        assert e.message == "ai.ipLimit"
    else:
        raise AssertionError("ip limit should raise")


def test_ai_rate_limit_admin_bypass(monkeypatch):
    async def fake_rate_limit(key, limit, ttl):
        raise AssertionError("admin should bypass ai rate limit")

    monkeypatch.setattr("src.server.utils.async_rate_limit", fake_rate_limit)
    monkeypatch.setattr("src.server.utils.token_handler.verify_token", lambda token: {"data": {"id": 1}})
    monkeypatch.setattr("src.server.utils.get_user_by_id", lambda user_id: SimpleNamespace(id=1, role="admin"))

    assert run(ai_rate_limit(FakeRequest(), token="admin-token")) == "1"


def test_ai_rate_limit_admin_bearer_bypass(monkeypatch):
    async def fake_rate_limit(key, limit, ttl):
        raise AssertionError("admin bearer token should bypass ai rate limit")

    monkeypatch.setattr("src.server.utils.async_rate_limit", fake_rate_limit)
    monkeypatch.setattr("src.server.utils.token_handler.verify_token", lambda token: {"data": {"id": 1}})
    monkeypatch.setattr("src.server.utils.get_user_by_id", lambda user_id: SimpleNamespace(id=1, role="admin"))

    request = FakeRequest(authorization="Bearer admin-token")

    assert run(ai_rate_limit(request, token=None)) == "1"


def test_client_ip_prefers_trusted_real_ip_over_spoofable_forwarded_chain():
    request = FakeRequest(ip="172.18.0.2")
    request.headers = {
        "x-real-ip": "203.0.113.8",
        "x-forwarded-for": "198.51.100.99, 203.0.113.8",
    }

    assert get_client_ip(request) == "203.0.113.8"
