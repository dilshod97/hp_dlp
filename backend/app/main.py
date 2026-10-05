"""HP DLP — FastAPI ilovasi."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routers import ingest, dashboard, auth_router, users, updates


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="HP DLP API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(users.router)
app.include_router(updates.router)
app.include_router(ingest.router)
app.include_router(dashboard.router)

# Skrinshotlarni panelda ko'rsatish uchun (keyinroq token bilan himoyalanadi).
os.makedirs(settings.media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.get("/health")
def health():
    return {"status": "ok"}
