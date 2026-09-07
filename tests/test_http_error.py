import pytest
from fastapi import HTTPException
from starlette.requests import Request

from routers.handlers.http_error import http_exception_handler


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
            "client": ("test", 123),
            "server": ("test", 80),
        }
    )


@pytest.mark.asyncio
async def test_http_exception_handler_wraps_detail():
    response = await http_exception_handler(
        _request(), HTTPException(status_code=404, detail="User not found.")
    )
    assert response.status_code == 404
    assert response.body == b'{"errors":["User not found."]}'
