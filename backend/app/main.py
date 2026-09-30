from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, engine
from . import models  # noqa: F401: register tables before create_all
from .routes import auth, events, images, incidents, pets


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Pawlice Report API", lifespan=lifespan)
session_secret = os.getenv("SESSION_SECRET", "")
if len(session_secret) < 32:
    raise RuntimeError("SESSION_SECRET must be set to at least 32 random characters")
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="pawlice_session",
    same_site="lax",
    https_only=False,
)
app.include_router(auth.router)
app.include_router(pets.router)
app.include_router(incidents.router)
app.include_router(events.router)
app.include_router(images.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
