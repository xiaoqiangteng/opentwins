from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.api.common import api_error
from app.adapters.influx_adapter import InfluxAdapter
from app.config import settings

router = APIRouter(prefix="/api/debug/influx", tags=["influxdb"])


@router.get("/query")
def query_recent(
    measurement: str = Query(...),
    bucket: Optional[str] = None,
    minutes: int = 60,
):
    try:
        rows = InfluxAdapter(settings).query_recent(bucket or settings.influx_bucket, measurement, minutes)
        message = "ok" if rows else "查询结果为空，请检查 Telegraf、bucket、measurement 和时间范围"
        return {"status": "ok", "message": message, "rows": rows}
    except Exception as exc:
        raise api_error(exc)
