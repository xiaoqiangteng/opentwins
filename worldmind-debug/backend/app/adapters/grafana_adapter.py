from __future__ import annotations

from typing import Any, Dict, List

import requests

from app.adapters.http_utils import response_payload
from app.config import Settings


class GrafanaAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.timeout = settings.request_timeout

    def _headers(self) -> Dict[str, str]:
        if self.settings.grafana_api_token and self.settings.grafana_api_token != "change_me":
            return {"Authorization": f"Bearer {self.settings.grafana_api_token}"}
        return {}

    def ping(self) -> bool:
        resp = requests.get(f"{self.settings.grafana_url}/api/health", timeout=self.timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"Grafana health HTTP {resp.status_code}: {response_payload(resp)}")
        return True

    def list_datasources(self) -> List[Dict[str, Any]]:
        resp = requests.get(
            f"{self.settings.grafana_url}/api/datasources",
            headers=self._headers(),
            timeout=self.timeout,
        )
        if resp.status_code == 401:
            raise RuntimeError("Grafana API Token 未配置或无权限；可先确认 /api/health")
        if resp.status_code >= 400:
            raise RuntimeError(f"Grafana datasources HTTP {resp.status_code}: {response_payload(resp)}")
        data = response_payload(resp)
        return data if isinstance(data, list) else []

    def check_datasource(self, name: str) -> Dict[str, Any]:
        for item in self.list_datasources():
            if item.get("name") == name:
                return item
        raise RuntimeError(f"Grafana datasource 不存在: {name}")
