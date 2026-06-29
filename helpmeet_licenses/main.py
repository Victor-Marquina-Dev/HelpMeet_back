from contextlib import asynccontextmanager
from fastapi import FastAPI
from helpmeet_licenses.database import engine
from helpmeet_licenses.models import Base  # noqa: F401 — registra tablas
from helpmeet_licenses import models  # noqa: F401
from helpmeet_licenses.routers import licenses, admin, gumroad

@asynccontextmanager
async def lifespan(app: FastAPI):
    # En producción usar Alembic; aquí solo para dev sin migración previa.
    # Base.metadata.create_all(bind=engine)  # descomentar si no usas Alembic
    yield

app = FastAPI(title="Helpmeet License Server", version="1.0.0", lifespan=lifespan)
app.include_router(licenses.router)
app.include_router(admin.router)
app.include_router(gumroad.router)

@app.get("/health")
@app.get("/salud")
def health():
    return {"ok": True}
