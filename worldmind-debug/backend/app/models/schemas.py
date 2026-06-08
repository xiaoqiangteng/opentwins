from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ComponentStatus = Literal["ok", "warning", "error", "skipped"]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class ComponentCheck(BaseModel):
    name: str
    status: ComponentStatus
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class DoctorResult(BaseModel):
    status: ComponentStatus
    checked_at: str
    components: List[ComponentCheck]


class ThingSummary(BaseModel):
    temperature: Optional[Any] = None
    ph: Optional[Any] = None
    humidity: Optional[Any] = None
    updated_at: Optional[Any] = None


class ThingEcho(BaseModel):
    thing_id: str
    source: str = "ditto"
    raw: Dict[str, Any]
    summary: ThingSummary


class TraceCreate(BaseModel):
    trace_id: str
    stage: str
    status: str
    message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class TraceStep(BaseModel):
    time: str
    stage: str
    status: str
    message: Optional[str] = None
    payload: Optional[Any] = None


class TraceResult(BaseModel):
    trace_id: str
    steps: List[TraceStep]
