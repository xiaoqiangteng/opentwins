from __future__ import annotations

from fastapi import APIRouter

from app.api.common import api_error
from app.adapters.grafana_adapter import GrafanaAdapter
from app.config import settings

router = APIRouter(prefix="/api/debug/grafana", tags=["grafana"])


@router.get("/datasources")
def datasources():
    try:
        return {"datasources": GrafanaAdapter(settings).list_datasources()}
    except Exception as exc:
        raise api_error(exc)
