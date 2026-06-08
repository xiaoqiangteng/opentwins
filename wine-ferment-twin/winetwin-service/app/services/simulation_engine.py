"""
嵌入式仿真引擎 —— 将 Wine Simulator 核心逻辑嵌入 Winetwin Service。
支持 start / pause / reset 控制，通过 MQTT 发布孪生体数据。
"""

import math
import random
import threading
import time
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
import paho.mqtt.client as mqtt

from app.core.config import settings


# ── 物理模型（复用 wine-simulator/fermentation_model.py 逻辑）───────────────

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def brix_to_sg(brix):
    return 1 + brix / (258.6 - ((brix / 258.2) * 227.1))


def stage_from_progress(progress):
    if progress < 0.10:
        return "initial"
    if progress < 0.80:
        return "active"
    if progress < 0.98:
        return "late"
    return "finished"


def simulate_point(tank, elapsed_hours):
    total_hours = float(tank.get("total_hours", 288))
    b0 = float(tank["initial_brix"])
    bf = float(tank["final_brix"])
    max_alc = float(tank["max_alcohol"])
    # 从 tank 配置读取动力学参数，提供默认值
    fermentation_k_mult = float(tank.get("fermentation_k_mult", 1.0))   # 发酵速率倍数
    heat_amplitude = float(tank.get("heat_amplitude", 4.0))              # 发酵热幅度 (°C)
    daily_temp_amplitude = float(tank.get("daily_temp_amplitude", 0.6))  # 日温度波动幅度 (°C)
    co2_peak = float(tank.get("co2_peak", 7200))                         # CO2 峰值 (ppm)
    co2_peak_pos = float(tank.get("co2_peak_pos", 0.32))                 # CO2 峰位 (占 total_hours 比例)
    co2_peak_width = float(tank.get("co2_peak_width", 0.14))             # CO2 峰宽 (占 total_hours 比例)
    ph_drop_rate = float(tank.get("ph_drop_rate", 0.08))                 # pH 下降速率

    k = math.log(max((b0 - bf) / 0.15, 1.01)) / total_hours * fermentation_k_mult
    brix = bf + (b0 - bf) * math.exp(-k * elapsed_hours)
    progress = clamp((b0 - brix) / (b0 - bf), 0, 1)
    heat = heat_amplitude * math.sin(math.pi * progress) if progress < 1 else 0
    daily = daily_temp_amplitude * math.sin(2 * math.pi * (elapsed_hours % 24) / 24.0)
    temp = float(tank["target_temp"]) + heat + daily + random.uniform(-0.25, 0.25)
    co2 = (
        420
        + co2_peak
        * math.exp(
            -((elapsed_hours - total_hours * co2_peak_pos) ** 2)
            / (2 * (total_hours * co2_peak_width) ** 2)
        )
        + random.uniform(-90, 90)
    )
    ph = float(tank["initial_ph"]) - ph_drop_rate * progress + random.uniform(-0.025, 0.025)
    pressure = 101.3 + min(3.5, co2 / 4200) + random.uniform(-0.15, 0.15)
    return {
        "temperature": round(temp, 2),
        "ph": round(ph, 2),
        "brix": round(brix, 2),
        "specific_gravity": round(brix_to_sg(max(brix, 0)), 4),
        "co2": round(max(250, co2), 1),
        "pressure": round(pressure, 2),
        "liquid_level": round(float(tank.get("liquid_level", 82.0)), 1),
        "alcohol_estimation": round(max_alc * progress, 2),
        "fermentation_progress": round(progress * 100, 1),
        "fermentation_stage": stage_from_progress(progress),
    }


# ── 异常注入（复用 wine-simulator/anomaly_injector.py 逻辑）────────────────

def apply_anomaly(tank, point, elapsed_hours):
    a = tank.get("anomaly")
    if a == "temperature_high" and elapsed_hours >= 40:
        point["temperature"] = round(
            point["temperature"] + 4.8 + min(2.0, (elapsed_hours - 40) / 48), 2
        )
    elif a == "stuck_fermentation" and elapsed_hours >= 72:
        base = float(tank["initial_brix"])
        point["brix"] = round(
            max(point["brix"], base - 5.2 - (elapsed_hours - 72) * 0.015), 2
        )
        progress = max(
            0.0,
            min(100.0, (base - point["brix"]) / (base - float(tank["final_brix"])) * 100),
        )
        point["fermentation_progress"] = round(progress, 1)
        point["alcohol_estimation"] = round(
            float(tank["max_alcohol"]) * progress / 100, 2
        )
    elif a == "ph_abnormal" and elapsed_hours >= 96:
        point["ph"] = round(point["ph"] + 0.45, 2)
    elif a == "co2_low" and 36 <= elapsed_hours <= 120:
        point["co2"] = round(point["co2"] * 0.18, 1)
    elif a == "sensor_missing" and random.random() < 0.12:
        point["temperature"] = None
    elif a == "sensor_spike" and random.random() < 0.08:
        point["temperature"] = round(point["temperature"] + random.choice([-8, 8]), 2)
    return point


# ── 风险评估（复用 wine-simulator/wine_fermentation_simulator.py 逻辑）─────

UNITS = {
    "temperature": "C",
    "ph": "",
    "brix": "Bx",
    "specific_gravity": "",
    "co2": "ppm",
    "pressure": "kPa",
    "liquid_level": "%",
    "alcohol_estimation": "%vol",
    "fermentation_progress": "%",
}


def risk_and_score(tank, p):
    wt = tank.get("wine_type", "red")
    temp = p.get("temperature")
    ph = p.get("ph")
    co2 = p.get("co2")
    warn = 30 if wt == "red" else 18
    crit = 33 if wt == "red" else 22
    phlo = 3.1 if wt == "red" else 3.0
    phhi = 3.8 if wt == "red" else 3.7
    score = 100.0
    risk = "normal"
    rec = "继续正常发酵监控。"
    if temp is None:
        return "offline", 45.0, "请检查传感器电源、线路和网关连通性。"
    if temp > crit or (ph is not None and (ph < 3.0 or ph > 3.9)):
        risk = "critical"
        score -= 32
        rec = "请停止自动操作，检查发酵罐并启动纠正控制。"
    elif temp > warn:
        risk = "warning"
        score -= 18
        rec = "请启动冷却或降低目标温度。"
    if ph is not None and (ph < phlo or ph > phhi):
        risk = "critical" if risk != "offline" else risk
        score -= 18
        rec = "请检查酸度并校验 pH 传感器。"
    if (
        tank.get("anomaly") == "stuck_fermentation"
        and p["fermentation_progress"] < 40
        and p["fermentation_stage"] == "active"
    ):
        risk = "warning"
        score -= 22
        rec = "请检查酵母活性、营养物、氧气暴露和温度曲线。"
    if (
        p["fermentation_stage"] == "active"
        and co2 is not None
        and co2 < (1500 if wt == "red" else 1200)
    ):
        risk = "warning"
        score -= 12
        rec = "活跃发酵阶段 CO2 低于预期，请检查酵母活性。"
    if p["fermentation_progress"] >= 98 and risk == "normal":
        risk = "finished"
        rec = "发酵接近完成，请准备澄清和转罐计划。"
    return risk, round(max(0, min(100, score)), 1), rec


def as_features(point, risk, score, rec):
    now = datetime.now(timezone.utc).isoformat()
    out = {}
    for k, v in point.items():
        props = {"value": v, "observed_at": now}
        if k in UNITS:
            props["unit"] = UNITS[k]
        out[k] = {"properties": props}
    out["quality_score"] = {"properties": {"value": score, "observed_at": now}}
    out["risk_level"] = {"properties": {"value": risk, "observed_at": now}}
    out["recommendation"] = {"properties": {"value": rec, "observed_at": now}}
    return out


# ── MQTT 发布器 ────────────────────────────────────────────────────────────

class _MqttPublisher:
    """轻量 MQTT 发布器，仅用于嵌入式引擎内部。"""

    def __init__(self, host, port, username=None, password=None, qos=1, topic_prefix="telemetry"):
        self.host = host
        self.port = int(port)
        self.qos = int(qos)
        self.topic_prefix = topic_prefix.strip("/")
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
            print(f"[simulation_engine] MQTT connect failed rc={rc}")

    def connect(self):
        self.client.connect(self.host, self.port, 60)
        self.client.loop_start()
        deadline = time.time() + 8
        while not self.connected and time.time() < deadline:
            time.sleep(0.1)
        if not self.connected:
            raise RuntimeError(f"MQTT connection timed out: {self.host}:{self.port}")

    def close(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    def publish_features(self, namespace, tank_id, thing_id, parent_id, features):
        payload = {
            "topic": f"{namespace}/{tank_id}/things/twin/commands/merge",
            "headers": {"content-type": "application/merge-patch+json"},
            "path": "/features",
            "value": features,
            "extra": {"thingId": thing_id, "attributes": {"_parents": [parent_id]}},
        }
        topic = f"{self.topic_prefix}/{namespace}/{tank_id}"
        info = self.client.publish(topic, json.dumps(payload), qos=self.qos)
        info.wait_for_publish(timeout=5)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed rc={info.rc} topic={topic}")
        return info


# ── 仿真引擎主体 ──────────────────────────────────────────────────────────

class SimulationEngine:
    """嵌入式仿真引擎，作为 Winetwin Service 的后台线程运行。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._elapsed = 0.0
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()
        self._pub = None
        self._started_at = datetime.now(timezone.utc)

        # 从配置文件加载仿真参数
        self._load_config()

    def _load_config(self):
        config_path = Path(settings.simulator_config_path)
        if config_path.exists():
            with config_path.open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
        else:
            cfg = {}

        sim_cfg = cfg.get("simulation", {})
        self._total_hours = float(sim_cfg.get("total_days", 12)) * 24
        self._speed = float(sim_cfg.get("speed", 3600))
        self._interval = float(sim_cfg.get("interval_seconds", 5))
        self._qos = int(sim_cfg.get("qos", 1))
        self._topic_prefix = sim_cfg.get("mqtt_topic_prefix", "telemetry")

        mqtt_cfg = cfg.get("mqtt", {})
        self._mqtt_host = settings.mqtt_host or mqtt_cfg.get("host", "127.0.0.1")
        self._mqtt_port = settings.mqtt_port or int(mqtt_cfg.get("port", 30511))
        self._mqtt_username = mqtt_cfg.get("username")
        self._mqtt_password = mqtt_cfg.get("password")

        ditto_cfg = cfg.get("ditto", {})
        self._namespace = ditto_cfg.get("namespace", "wine")

        self._tanks = cfg.get("tanks", [])
        for t in self._tanks:
            t["total_hours"] = self._total_hours

    @property
    def elapsed(self):
        with self._lock:
            return self._elapsed

    @property
    def running(self):
        with self._lock:
            return self._running

    @property
    def total_hours(self):
        return self._total_hours

    def status(self):
        with self._lock:
            elapsed = self._elapsed
            running = self._running
            started_at = self._started_at
        progress_pct = round(elapsed / self._total_hours * 100, 1) if self._total_hours > 0 else 0
        stage = "初始期"
        if progress_pct >= 98:
            stage = "已完成"
        elif progress_pct >= 80:
            stage = "后期"
        elif progress_pct >= 10:
            stage = "活跃发酵期"
        return {
            "elapsed_hours": round(elapsed, 1),
            "total_hours": self._total_hours,
            "progress_pct": progress_pct,
            "running": running,
            "stage": stage,
            "started_at": started_at.isoformat(),
        }

    def start(self):
        with self._lock:
            if self._running:
                return {"status": "already_running"}
            self._running = True

        # 确保后台线程在运行
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        return {"status": "started"}

    def pause(self):
        with self._lock:
            if not self._running:
                return {"status": "already_paused"}
            self._running = False
        return {"status": "paused"}

    # MQTT 连通性缓存
    _mqtt_last_failure = 0.0
    _MQTT_RETRY_INTERVAL = 60.0

    def _is_mqtt_available(self):
        """检查 MQTT 是否最近可用（失败后短时间内不再重试）。"""
        if self._pub is not None and self._pub.connected:
            return True
        return (time.monotonic() - self._mqtt_last_failure) >= self._MQTT_RETRY_INTERVAL

    def reset(self):
        with self._lock:
            self._running = False
            self._elapsed = 0.0
            self._started_at = datetime.now(timezone.utc)

        # 在后台线程中发布初始状态，避免阻塞 API 响应
        threading.Thread(target=self._publish_initial_state, daemon=True).start()
        return {"status": "reset"}

    def _publish_initial_state(self):
        """重置时将所有罐体推回初始状态。"""
        if not self._is_mqtt_available():
            print("[simulation_engine] MQTT unavailable, skip publish initial state")
            return
        try:
            if self._pub is None or not self._pub.connected:
                self._connect_mqtt()
            for tank in self._tanks:
                p = simulate_point(tank, 0.0)
                p = apply_anomaly(tank, p, 0.0)
                risk, score, rec = risk_and_score(tank, p)
                features = as_features(p, risk, score, rec)
                self._pub.publish_features(
                    self._namespace,
                    tank["tank_id"],
                    tank["thing_id"],
                    tank.get("parent_id", "wine:workshop_01"),
                    features,
                )
        except Exception as e:
            self._mqtt_last_failure = time.monotonic()
            print(f"[simulation_engine] publish initial state failed: {e}")

    def _connect_mqtt(self):
        if self._pub is not None:
            try:
                self._pub.close()
            except Exception:
                pass
        self._pub = _MqttPublisher(
            self._mqtt_host,
            self._mqtt_port,
            self._mqtt_username,
            self._mqtt_password,
            self._qos,
            self._topic_prefix,
        )
        self._pub.connect()

    def _loop(self):
        """仿真主循环，在后台线程中运行。"""
        print("[simulation_engine] thread started")

        # 尝试连接 MQTT（非阻塞：即使连接失败，仿真循环仍继续运行）
        try:
            self._connect_mqtt()
            print(f"[simulation_engine] MQTT connected {self._mqtt_host}:{self._mqtt_port}")
        except Exception as e:
            print(f"[simulation_engine] MQTT connect failed: {e} (simulation will continue without MQTT)")

        try:
            while not self._stop_event.is_set():
                with self._lock:
                    if not self._running:
                        # 暂停状态：短暂休眠后重新检查
                        pass
                    else:
                        # 运行状态：推进一步
                        for tank in self._tanks:
                            p = simulate_point(tank, self._elapsed)
                            p = apply_anomaly(tank, p, self._elapsed)
                            risk, score, rec = risk_and_score(tank, p)
                            features = as_features(p, risk, score, rec)

                            # 尝试通过 MQTT 发布；失败时自动重连
                            try:
                                if self._pub is None or not self._pub.connected:
                                    self._connect_mqtt()
                                self._pub.publish_features(
                                    self._namespace,
                                    tank["tank_id"],
                                    tank["thing_id"],
                                    tank.get("parent_id", "wine:workshop_01"),
                                    features,
                                )
                            except Exception as e:
                                print(f"[simulation_engine] MQTT publish failed: {e}")

                        self._elapsed += self._interval * self._speed / 3600.0

                        # 仿真完成，自动暂停
                        if self._elapsed >= self._total_hours:
                            self._elapsed = self._total_hours
                            self._running = False
                            print("[simulation_engine] fermentation cycle completed")

                time.sleep(self._interval)
        except Exception as e:
            print(f"[simulation_engine] loop error: {e}")
        finally:
            try:
                self._pub.close()
            except Exception:
                pass
            print("[simulation_engine] thread stopped")


# ── 全局单例 ──────────────────────────────────────────────────────────────

engine = SimulationEngine()
