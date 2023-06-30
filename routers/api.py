from fastapi import APIRouter

from routers import user_router

router = APIRouter()


def include_api_routes():
    """ Include to router all api rest routes with version prefix """

    router.include_router(user_router.router)


include_api_routes()
