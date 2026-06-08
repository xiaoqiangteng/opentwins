from __future__ import annotations

from fastapi import APIRouter

from app.api.common import api_error
from app.adapters.ditto_adapter import DittoAdapter
from app.config import settings
from app.services.echo_service import EchoService

router = APIRouter(prefix="/api/debug/ditto", tags=["ditto"])


@router.get("/things/{thing_id:path}/features/{feature}/value")
def get_feature_value(thing_id: str, feature: str):
    try:
        return {"thing_id": thing_id, "feature": feature, "value": DittoAdapter(settings).get_feature_value(thing_id, feature)}
    except Exception as exc:
        raise api_error(exc)


@router.get("/things/{thing_id:path}")
def get_thing(thing_id: str):
    try:
        raw = DittoAdapter(settings).get_thing(thing_id)
        return EchoService().summarize_thing(thing_id, raw)
    except Exception as exc:
        raise api_error(exc)


@router.get("/connections")
def list_connections():
    try:
        return {"connections": DittoAdapter(settings).list_connections()}
    except Exception as exc:
        raise api_error(exc)


@router.get("/connections/{connection_id}/status")
def connection_status(connection_id: str):
    try:
        return DittoAdapter(settings).get_connection_status(connection_id)
    except Exception as exc:
        raise api_error(exc)


@router.get("/connections/{connection_id}/metrics")
def connection_metrics(connection_id: str):
    try:
        return DittoAdapter(settings).get_connection_metrics(connection_id)
    except Exception as exc:
        raise api_error(exc)


@router.get("/connections/{connection_id}/logs")
def connection_logs(connection_id: str):
    try:
        return DittoAdapter(settings).get_connection_logs(connection_id)
    except Exception as exc:
        raise api_error(exc)
