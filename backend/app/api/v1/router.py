"""API v1 router — registers all feature routers."""
from fastapi import APIRouter

from app.api.v1.endpoints.bins import router as bins_router
from app.api.v1.endpoints.alerts import alerts_router, collection_router
from app.api.v1.endpoints.demo import router as demo_router

api_router = APIRouter()

# Feature 1: Smart Bin Monitoring
api_router.include_router(bins_router)

# Feature 2: Alerts & Collection Priority
api_router.include_router(alerts_router)
api_router.include_router(collection_router)

# Feature 3: Demo Seed / Manual Reading
api_router.include_router(demo_router)
