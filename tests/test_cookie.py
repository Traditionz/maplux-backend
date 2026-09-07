import pytest
from fastapi import HTTPException
from starlette.requests import Request

from security.cookie import OAuth2PasswordBearerCookie


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
async def test_cookie_reads_authorization_header():
    scheme = OAuth2PasswordBearerCookie(tokenUrl="/auth/login/")
    request = _request(headers=[(b"authorization", b"Bearer header-token")])
    assert await scheme(request) == "header-token"


@pytest.mark.asyncio
async def test_cookie_reads_authorization_cookie():
    scheme = OAuth2PasswordBearerCookie(tokenUrl="/auth/login/")
    request = _request()
    request._cookies = {"Authorization": "Bearer cookie-token"}
    assert await scheme(request) == "cookie-token"


@pytest.mark.asyncio
async def test_cookie_rejects_missing_and_basic_auth():
    scheme = OAuth2PasswordBearerCookie(tokenUrl="/auth/login/")
    with pytest.raises(HTTPException) as missing:
        await scheme(_request())
    assert missing.value.status_code == 401

    with pytest.raises(HTTPException):
        await scheme(_request(headers=[(b"authorization", b"Basic abc")]))


@pytest.mark.asyncio
async def test_cookie_auto_error_false_returns_none():
    scheme = OAuth2PasswordBearerCookie(
        tokenUrl="/auth/login/",
        auto_error=False,
        scopes={"read": "Read access"},
        scheme_name="CookieAuth",
    )
    assert await scheme(_request()) is None
    assert scheme.scheme_name == "CookieAuth"
