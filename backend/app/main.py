"""FastAPI application entrypoint for the Grounded backend."""

from fastapi import FastAPI

from app.api.v1.router import api_router


app = FastAPI(title="Grounded Backend", version="0.1.0")
app.include_router(api_router)
