import json
import time
import paho.mqtt.client as mqtt


class DittoMqttPublisher:
    def __init__(self, host, port, username=None, password=None, qos=1, topic_prefix='opentwins'):
        self.host = host
        self.port = int(port)
        self.qos = int(qos)
        self.topic_prefix = topic_prefix.strip('/')
        self.connected = False
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except Exception:
            self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        if username:
            self.client.username_pw_set(username, password)

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        self.connected = rc == 0
        if rc != 0:
            print(f"MQTT connect failed rc={rc}")

    def connect(self):
        self.client.connect(self.host, self.port, 60)
        self.client.loop_start()
        deadline = time.time() + 8
        while not self.connected and time.time() < deadline:
            time.sleep(0.1)
        if not self.connected:
            raise RuntimeError(f"MQTT connection timed out: {self.host}:{self.port}")

    def close(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish_features(self, namespace, tank_id, thing_id, parent_id, features):
        payload = {
            'topic': f'{namespace}/{tank_id}/things/twin/commands/merge',
            'headers': {'content-type': 'application/merge-patch+json'},
            'path': '/features',
            'value': features,
            'extra': {'thingId': thing_id, 'attributes': {'_parents': [parent_id]}},
        }
        topic = f'{self.topic_prefix}/{namespace}/{tank_id}'
        info = self.client.publish(topic, json.dumps(payload), qos=self.qos)
        info.wait_for_publish(timeout=5)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed rc={info.rc} topic={topic}")
        return info
