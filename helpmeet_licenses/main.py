from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from helpmeet_licenses.config import settings
from helpmeet_licenses.database import engine
from helpmeet_licenses.models import Base  # noqa: F401 — registra tablas
from helpmeet_licenses import models  # noqa: F401
from helpmeet_licenses.routers import licenses, admin, gumroad

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Helpmeet License Server", version="1.0.0", lifespan=lifespan)

allowed_origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(licenses.router)
app.include_router(admin.router)
app.include_router(gumroad.router)

@app.get("/health")
@app.get("/salud")
def health():
    return {"ok": True}
