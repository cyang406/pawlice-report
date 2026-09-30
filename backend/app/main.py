from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from . import models  # noqa: F401: register tables before create_all
from .routes import incidents, pets


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Pawlice Report API", lifespan=lifespan)
app.include_router(pets.router)
app.include_router(incidents.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
