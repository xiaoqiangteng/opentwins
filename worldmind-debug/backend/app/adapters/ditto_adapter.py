from __future__ import annotations

from typing import Any, Dict, List, Tuple
from urllib.parse import quote

import requests

from app.adapters.http_utils import response_payload
from app.config import Settings


class DittoAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.ditto_base_url.rstrip("/")
        self.timeout = settings.request_timeout

    def _auth(self, devops: bool = False) -> Tuple[str, str]:
        if devops:
            return (self.settings.ditto_devops_user, self.settings.ditto_devops_password)
        return (self.settings.ditto_user, self.settings.ditto_password)

    def _get(self, path: str, devops: bool = False) -> Any:
        url = f"{self.base_url}{path}"
        resp = requests.get(url, auth=self._auth(devops), timeout=self.timeout)
        if resp.status_code in (401, 403) and devops:
            resp = requests.get(url, auth=self._auth(False), timeout=self.timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"Ditto HTTP {resp.status_code}: {response_payload(resp)}")
        return response_payload(resp)

    def ping(self) -> bool:
        self._get("/api/2/things")
        return True

    def list_things(self, namespace: str = "") -> List[Dict[str, Any]]:
        """列出 Ditto 中的所有 Thing，可按 namespace 过滤。"""
        if namespace:
            path = f"/api/2/things?namespace={quote(namespace, safe='')}"
        else:
            path = "/api/2/things"
        data = self._get(path)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            items = data.get("items") or data.get("things") or []
            return items if isinstance(items, list) else [data]
        return []

    def get_thing(self, thing_id: str) -> Dict[str, Any]:
        encoded = quote(thing_id, safe="")
        return self._get(f"/api/2/things/{encoded}")

    def get_feature_value(self, thing_id: str, feature: str) -> Any:
        encoded_thing = quote(thing_id, safe="")
        encoded_feature = quote(feature, safe="")
        return self._get(f"/api/2/things/{encoded_thing}/features/{encoded_feature}/properties")

    def list_connections(self) -> List[Dict[str, Any]]:
        data = self._get("/api/2/connections", devops=True)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            items = data.get("items") or data.get("connections") or []
            return items if isinstance(items, list) else [data]
        return []

    def get_connection_status(self, connection_id: str) -> Dict[str, Any]:
        encoded = quote(connection_id, safe="")
        data = self._get(f"/api/2/connections/{encoded}/status", devops=True)
        return data if isinstance(data, dict) else {"raw": data}

    def get_connection_metrics(self, connection_id: str) -> Dict[str, Any]:
        encoded = quote(connection_id, safe="")
        data = self._get(f"/api/2/connections/{encoded}/metrics", devops=True)
        return data if isinstance(data, dict) else {"raw": data}

    def get_connection_logs(self, connection_id: str) -> Dict[str, Any]:
        encoded = quote(connection_id, safe="")
        data = self._get(f"/api/2/connections/{encoded}/logs", devops=True)
        return data if isinstance(data, dict) else {"raw": data}
