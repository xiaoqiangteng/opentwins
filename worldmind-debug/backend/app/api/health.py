from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.models.schemas import now_iso
from app.services.doctor_service import DoctorService

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "worldmind-debug-api", "time": now_iso()}


@router.get("/doctor")
def doctor():
    return DoctorService(settings).run()
