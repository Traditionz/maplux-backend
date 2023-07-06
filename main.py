from fastapi import FastAPI, HTTPException

from config import API_PREFIX
from database import Base, engine
from routers.api import router
from routers.handlers.http_error import http_exception_handler

""" Start and configure the application """

# Start FastApi App
app = FastAPI()

# Mapping api routes
app.include_router(router, prefix=API_PREFIX)

# Add exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)

Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)

# TODO: Email confirmation
