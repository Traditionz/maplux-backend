from fastapi import APIRouter

from routers import auth_router, user_router

router = APIRouter()


@router.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


def include_api_routes() -> None:
    """Include all REST routes on the top-level API router."""
    router.include_router(auth_router.router)
    router.include_router(user_router.router)


include_api_routes()
