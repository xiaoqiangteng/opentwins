from __future__ import annotations

from typing import Any, Dict, List

import requests

from app.adapters.http_utils import response_payload
from app.config import Settings


class InfluxAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.timeout = settings.request_timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.settings.influx_token:
            headers["Authorization"] = f"Token {self.settings.influx_token}"
        return headers

    def ping(self) -> bool:
        resp = requests.get(f"{self.settings.influx_url}/health", timeout=self.timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"InfluxDB health HTTP {resp.status_code}: {response_payload(resp)}")
        return True

    def query_recent(self, bucket: str, measurement: str, minutes: int = 60) -> List[Dict[str, Any]]:
        if not self.settings.influx_token:
            raise RuntimeError("INFLUX_TOKEN 未配置，无法执行 InfluxDB 查询")
        flux = f'''
from(bucket: "{bucket}")
  |> range(start: -{int(minutes)}m)
  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> limit(n: 50)
'''
        payload = {"query": flux, "type": "flux"}
        resp = requests.post(
            f"{self.settings.influx_url}/api/v2/query",
            params={"org": self.settings.influx_org},
            headers={**self._headers(), "Content-Type": "application/json", "Accept": "application/csv"},
            json=payload,
            timeout=max(self.timeout, 15),
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"InfluxDB query HTTP {resp.status_code}: {resp.text[:1000]}")
        rows: List[Dict[str, Any]] = []
        for line in resp.text.splitlines():
            if not line or line.startswith("#") or line.startswith(",result,table"):
                continue
            rows.append({"csv": line})
        return rows
