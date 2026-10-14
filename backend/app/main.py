"""SWM-ICS FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.v1.endpoints.health import router as health_router
from app.core.config import settings

app = FastAPI(
    title="SWM-ICS API",
    version="0.1.0",
    description="Smart Waste Management & Intelligent Collection System — Backend API",
)

# CORS — allow frontend dev servers (Live Server, Vite, etc.)
_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(health_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"name": "SWM-ICS API", "version": "0.1.0", "docs": "/docs"}
