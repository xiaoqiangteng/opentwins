from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.common import api_error
from app.adapters.mqtt_adapter import MQTTAdapter
from app.config import settings

router = APIRouter(prefix="/api/debug/mqtt", tags=["mqtt"])


@router.get("/status")
def status():
    try:
        MQTTAdapter(settings).ping()
        return {"status": "ok", "message": f"MQTT reachable: {settings.mqtt_host}:{settings.mqtt_port}"}
    except Exception as exc:
        raise api_error(exc)


@router.get("/tail")
def tail(topic: str = Query(default=None), seconds: int = 10, limit: int = 20):
    try:
        return {
            "topic": topic or settings.mqtt_default_topic,
            "messages": MQTTAdapter(settings).tail(topic or settings.mqtt_default_topic, seconds, limit),
        }
    except Exception as exc:
        raise api_error(exc)
