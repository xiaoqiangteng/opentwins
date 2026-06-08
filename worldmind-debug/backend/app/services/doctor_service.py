from __future__ import annotations

from typing import Any, Callable, Dict, List, Union

from app.adapters.ditto_adapter import DittoAdapter
from app.adapters.grafana_adapter import GrafanaAdapter
from app.adapters.influx_adapter import InfluxAdapter
from app.adapters.mqtt_adapter import MQTTAdapter
from app.adapters.telegraf_adapter import TelegrafAdapter
from app.config import Settings
from app.models.schemas import ComponentCheck, DoctorResult, now_iso


class DoctorService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ditto = DittoAdapter(settings)
        self.mqtt = MQTTAdapter(settings)
        self.influx = InfluxAdapter(settings)
        self.grafana = GrafanaAdapter(settings)
        self.telegraf = TelegrafAdapter(settings)

    def _check(self, name: str, fn: Callable[[], Union[Dict[str, Any], str, bool]]) -> ComponentCheck:
        try:
            result = fn()
            if isinstance(result, dict):
                status = result.pop("status", "ok")
                message = result.pop("message", "ok")
                return ComponentCheck(name=name, status=status, message=message, details=result)
            return ComponentCheck(name=name, status="ok", message=str(result))
        except Exception as exc:
            return ComponentCheck(name=name, status="error", message=str(exc))

    def run(self) -> DoctorResult:
        components: List[ComponentCheck] = [
            self._check("mqtt", lambda: {"message": "reachable"} if self.mqtt.ping() else {"status": "error", "message": "unreachable"}),
            self._check("ditto", lambda: {"message": f"api reachable: {self.settings.ditto_base_url}"} if self.ditto.ping() else {"status": "error", "message": "unreachable"}),
            self._check("ditto_connections", self._connections_check),
            self._check("influxdb", lambda: {"message": f"reachable bucket={self.settings.influx_bucket}"} if self.influx.ping() else {"status": "error", "message": "unreachable"}),
            self._check("telegraf", self.telegraf.status),
            self._check("grafana", lambda: {"message": f"reachable: {self.settings.grafana_url}"} if self.grafana.ping() else {"status": "error", "message": "unreachable"}),
        ]
        status = "ok"
        if any(item.status == "error" for item in components):
            status = "error"
        elif any(item.status == "warning" for item in components):
            status = "warning"
        elif all(item.status == "skipped" for item in components):
            status = "skipped"
        return DoctorResult(status=status, checked_at=now_iso(), components=components)

    def _connections_check(self) -> Dict[str, Any]:
        conns = self.ditto.list_connections()
        if not conns:
            return {"status": "warning", "message": "未发现 Ditto Connections"}
        summaries = []
        for conn in conns:
            cid = conn.get("id") or conn.get("name")
            summaries.append({"id": cid, "connectionType": conn.get("connectionType"), "connectionStatus": conn.get("connectionStatus")})
        return {"message": f"connections={len(conns)}", "connections": summaries}
