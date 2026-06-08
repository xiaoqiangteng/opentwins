from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from app.config import Settings


class MQTTAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _client(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("缺少 paho-mqtt 依赖，请安装 worldmind-debug/backend/requirements.txt") from exc
        client = mqtt.Client()
        if self.settings.mqtt_username:
            client.username_pw_set(self.settings.mqtt_username, self.settings.mqtt_password or None)
        return client

    def ping(self) -> bool:
        client = self._client()
        try:
            client.connect(self.settings.mqtt_host, self.settings.mqtt_port, 5)
            client.disconnect()
            return True
        except Exception as exc:
            raise RuntimeError(f"MQTT 不可达: {exc}") from exc

    def tail(self, topic: str, seconds: int = 10, limit: int = 20) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        client = self._client()

        def on_message(_client, _userdata, msg):
            payload_text = msg.payload.decode("utf-8", errors="replace")
            try:
                payload: Any = json.loads(payload_text)
            except ValueError:
                payload = payload_text
            messages.append(
                {
                    "received_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "topic": msg.topic,
                    "payload": payload,
                    "qos": msg.qos,
                    "retain": msg.retain,
                }
            )
            if len(messages) >= limit:
                _client.disconnect()

        client.on_message = on_message
        try:
            client.connect(self.settings.mqtt_host, self.settings.mqtt_port, 10)
            client.subscribe(topic)
            client.loop_start()
            deadline = time.monotonic() + max(1, seconds)
            while time.monotonic() < deadline and len(messages) < limit:
                time.sleep(0.1)
            client.loop_stop()
            client.disconnect()
            return messages
        except Exception as exc:
            raise RuntimeError(f"MQTT tail 失败: {exc}") from exc

    def publish_test(self, topic: str, payload: Dict[str, Any]) -> bool:
        client = self._client()
        try:
            client.connect(self.settings.mqtt_host, self.settings.mqtt_port, 5)
            info = client.publish(topic, json.dumps(payload, ensure_ascii=False))
            info.wait_for_publish(timeout=5)
            client.disconnect()
            return bool(info.is_published())
        except Exception as exc:
            raise RuntimeError(f"MQTT publish 失败: {exc}") from exc
