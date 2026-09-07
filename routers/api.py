from fastapi import APIRouter

from routers import user_router

router = APIRouter()


def include_api_routes() -> None:
    """Include all REST routes on the top-level API router."""
    router.include_router(user_router.router)


include_api_routes()
