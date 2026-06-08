from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    debug_api_host: str = "0.0.0.0"
    debug_api_port: int = 18080
    request_timeout: float = 5.0

    ditto_base_url: str = "http://localhost:8080"
    ditto_user: str = "ditto"
    ditto_password: str = "ditto"
    ditto_devops_user: str = "devops"
    ditto_devops_password: str = "foobar"

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_default_topic: str = "telemetry/#"

    influx_url: str = "http://localhost:8086"
    influx_token: str = ""
    influx_org: str = "opentwins"
    influx_bucket: str = "opentwins"

    grafana_url: str = "http://localhost:3000"
    grafana_api_token: str = ""

    trace_db_path: str = "./data/debug_trace.sqlite"
    kubernetes_namespace: str = "opentwins"
    helm_release: str = "opentwins"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            debug_api_host=_env("DEBUG_API_HOST", "0.0.0.0"),
            debug_api_port=_env_int("DEBUG_API_PORT", 18080),
            request_timeout=float(_env("DEBUG_REQUEST_TIMEOUT", "5") or "5"),
            ditto_base_url=_env("DITTO_BASE_URL", "http://localhost:8080").rstrip("/"),
            ditto_user=_env("DITTO_USER", _env("DITTO_USERNAME", "ditto")),
            ditto_password=_env("DITTO_PASSWORD", "ditto"),
            ditto_devops_user=_env("DITTO_DEVOPS_USER", "devops"),
            ditto_devops_password=_env("DITTO_DEVOPS_PASSWORD", "foobar"),
            mqtt_host=_env("MQTT_HOST", "localhost"),
            mqtt_port=_env_int("MQTT_PORT", 1883),
            mqtt_username=_env("MQTT_USERNAME", ""),
            mqtt_password=_env("MQTT_PASSWORD", ""),
            mqtt_default_topic=_env("MQTT_DEFAULT_TOPIC", "telemetry/#"),
            influx_url=_env("INFLUX_URL", "http://localhost:8086").rstrip("/"),
            influx_token=_env("INFLUX_TOKEN", ""),
            influx_org=_env("INFLUX_ORG", "opentwins"),
            influx_bucket=_env("INFLUX_BUCKET", "opentwins"),
            grafana_url=_env("GRAFANA_URL", "http://localhost:3000").rstrip("/"),
            grafana_api_token=_env("GRAFANA_API_TOKEN", ""),
            trace_db_path=_env("TRACE_DB_PATH", "./data/debug_trace.sqlite"),
            kubernetes_namespace=_env("KUBERNETES_NAMESPACE", "opentwins"),
            helm_release=_env("HELM_RELEASE", "opentwins"),
        )

    @property
    def trace_db_file(self) -> Path:
        return Path(self.trace_db_path)


settings = Settings.from_env()
