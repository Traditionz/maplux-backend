import pytest
from fastapi import HTTPException
from starlette.requests import Request

from security.cookie import ACCESS_COOKIE, BearerOrCookieAuth


def _request(*, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers or [],
        "client": ("test", 123),
        "server": ("test", 80),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_auth_reads_authorization_header():
    scheme = BearerOrCookieAuth()
    request = _request(headers=[(b"authorization", b"Bearer header-token")])
    assert await scheme(request) == "header-token"


@pytest.mark.asyncio
async def test_auth_reads_access_cookie():
    scheme = BearerOrCookieAuth()
    request = _request()
    request._cookies = {ACCESS_COOKIE: "cookie-token"}
    assert await scheme(request) == "cookie-token"


@pytest.mark.asyncio
async def test_auth_rejects_missing_and_basic():
    scheme = BearerOrCookieAuth()
    with pytest.raises(HTTPException) as missing:
        await scheme(_request())
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException):
        await scheme(_request(headers=[(b"authorization", b"Basic abc")]))


@pytest.mark.asyncio
async def test_auth_auto_error_false_returns_none():
    scheme = BearerOrCookieAuth(auto_error=False)
    assert await scheme(_request()) is None
