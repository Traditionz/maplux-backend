from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """Return HTTP errors as a consistent JSON errors list."""
    return JSONResponse({"errors": [exc.detail]}, status_code=exc.status_code)
