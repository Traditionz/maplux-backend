from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


class BearerOrCookieAuth(HTTPBearer):
    """Accept a JWT from an Authorization Bearer header or an HttpOnly cookie."""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=False)
        self.raise_on_missing = auto_error

    async def __call__(self, request: Request) -> str | None:
        credentials = await super().__call__(request)
        if credentials is not None and credentials.scheme.lower() == "bearer":
            return credentials.credentials

        cookie_token = request.cookies.get(ACCESS_COOKIE)
        if cookie_token:
            return cookie_token

        if self.raise_on_missing:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None
