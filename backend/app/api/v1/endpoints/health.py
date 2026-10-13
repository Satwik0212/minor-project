from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.db.session import engine
router = APIRouter(tags=["health"])
@router.get("/health/live")
def live(): return {"status": "ok"}
@router.get("/health/ready")
def ready():
    try:
        with engine.connect() as conn: conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
