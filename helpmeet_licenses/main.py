from contextlib import asynccontextmanager
from fastapi import FastAPI
from helpmeet_licenses.routers import licenses

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Helpmeet License Server", version="1.0.0", lifespan=lifespan)
app.include_router(licenses.router)

@app.get("/health")
def health():
    return {"ok": True}
