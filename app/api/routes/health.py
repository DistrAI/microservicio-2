"""
Router de Health Check
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.schemas import HealthResponse
from app.database.connection import get_db, test_connection
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check del servicio
    """
    db_status = "connected" if test_connection() else "disconnected"
    
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        database=db_status,
        timestamp=datetime.utcnow()
    )
