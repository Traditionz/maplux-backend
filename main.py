from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from starlette.datastructures import URL
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from config import env_vars
from database import Base, engine
from routers.api import router
from routers.handlers.http_error import http_exception_handler

""" Start and configure the application """

load_dotenv()

# Start FastApi App
app = FastAPI()

origins = [
    env_vars.CLIENT_ORIGIN,
]

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mapping api routes
app.include_router(router, prefix=env_vars.API_PREFIX)

# Add exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)

Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
