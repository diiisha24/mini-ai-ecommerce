from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, text

from app.config import get_settings
from app.db import engine, init_db
from app.routers import ai, auth, orders, products, webhooks

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Mini AI E-Commerce API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(products.admin_router)
app.include_router(orders.router)
app.include_router(orders.admin_router)
app.include_router(webhooks.router)
app.include_router(ai.router)


@app.get("/api/health")
def health() -> dict:
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:  # noqa: BLE001 - health check reports, never raises
        return {"status": "degraded", "database": "unreachable"}
