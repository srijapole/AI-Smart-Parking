
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.auth import router as auth_router
from backend.config import settings
from backend.database import engine
from backend.vehicles import router as vehicles_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check database connectivity at startup.
    # Alembic manages schema creation.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    yield

    engine.dispose()


app = FastAPI(
    title="Smart Parking API",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# Register API routers
app.include_router(auth_router)
app.include_router(vehicles_router)


@app.get("/health")
def health():
    return {"status": "ok"}
