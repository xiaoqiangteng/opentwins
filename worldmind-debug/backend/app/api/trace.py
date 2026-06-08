from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.models.schemas import TraceCreate
from app.services.trace_service import TraceService

router = APIRouter(prefix="/api/debug/trace", tags=["trace"])


@router.get("/{trace_id}")
def get_trace(trace_id: str):
    return TraceService(settings.trace_db_path).get(trace_id)


@router.post("")
def add_trace(item: TraceCreate):
    return TraceService(settings.trace_db_path).add(item)
