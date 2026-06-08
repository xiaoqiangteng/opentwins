#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional
from urllib.parse import quote
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


API_BASE = os.getenv("WM_DEBUG_API_URL", "http://localhost:18080/api/debug").rstrip("/")
TIMEOUT = float(os.getenv("WM_DEBUG_TIMEOUT", "20"))


def _url(path: str) -> str:
    return f"{API_BASE}{path}"


def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = _url(path)
    if params:
        clean_params = {k: v for k, v in params.items() if v is not None}
        url = f"{url}?{urlencode(clean_params)}"
    return _request_json("GET", url)


def _post(path: str, payload: Dict[str, Any]) -> Any:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return _request_json("POST", _url(path), body=body)


def _request_json(method: str, url: str, body: Optional[bytes] = None) -> Any:
    req = Request(url, data=body, method=method)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            text = resp.read().decode("utf-8")
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(text).get("detail", text)
        except ValueError:
            detail = text
        raise RuntimeError(str(detail)) from exc
    except URLError as exc:
        raise RuntimeError(f"无法连接 Debug API: {exc}") from exc
    return json.loads(text)


def _dump(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _status_label(status: str) -> str:
    labels = {"ok": "[OK]   ", "warning": "[WARN] ", "error": "[ERROR]", "skipped": "[SKIP] "}
    return labels.get(status, "[INFO] ")


def cmd_doctor(_args: argparse.Namespace) -> None:
    data = _get("/doctor")
    for item in data.get("components", []):
        print(f"{_status_label(item.get('status', ''))} {item.get('name')}: {item.get('message')}")
        details = item.get("details") or {}
        if details:
            print(f"       {json.dumps(details, ensure_ascii=False)}")
    print(f"Result: {data.get('status')}")


def cmd_mqtt_tail(args: argparse.Namespace) -> None:
    data = _get("/mqtt/tail", {"topic": args.topic, "seconds": args.seconds, "limit": args.limit})
    messages = data.get("messages", [])
    if not messages:
        print(f"未收到 MQTT 消息: topic={data.get('topic')} seconds={args.seconds}")
        return
    for msg in messages:
        print(f"{msg.get('received_at')} {msg.get('topic')}")
        _dump(msg.get("payload"))


def cmd_twin_echo(args: argparse.Namespace) -> None:
    data = _get(f"/ditto/things/{quote(args.thing_id, safe='')}")
    _dump(data)


def cmd_twin_watch(args: argparse.Namespace) -> None:
    feature = quote(args.feature, safe="")
    thing_id = quote(args.thing_id, safe="")
    while True:
        try:
            data = _get(f"/ditto/things/{thing_id}/features/{feature}/value")
            value = data.get("value")
            if isinstance(value, dict) and "value" in value:
                value = value["value"]
            line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {args.feature}={json.dumps(value, ensure_ascii=False)}"
            if args.feature.lower() == "ph":
                try:
                    ph = float(value)
                    if ph < 3.2:
                        line += "  [WARN below threshold]"
                except (TypeError, ValueError):
                    pass
            print(line, flush=True)
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n已停止 watch")
            return
        except Exception as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            time.sleep(args.interval)


def cmd_conn_list(_args: argparse.Namespace) -> None:
    _dump(_get("/ditto/connections"))


def cmd_conn_status(args: argparse.Namespace) -> None:
    _dump(_get(f"/ditto/connections/{quote(args.connection_id, safe='')}/status"))


def cmd_conn_metrics(args: argparse.Namespace) -> None:
    _dump(_get(f"/ditto/connections/{quote(args.connection_id, safe='')}/metrics"))


def cmd_conn_logs(args: argparse.Namespace) -> None:
    _dump(_get(f"/ditto/connections/{quote(args.connection_id, safe='')}/logs"))


def cmd_influx_recent(args: argparse.Namespace) -> None:
    data = _get(
        "/influx/query",
        {"measurement": args.measurement, "bucket": args.bucket, "minutes": args.minutes},
    )
    if not data.get("rows"):
        print(data.get("message", "InfluxDB 查询为空"))
        return
    _dump(data)


def cmd_trace(args: argparse.Namespace) -> None:
    _dump(_get(f"/trace/{quote(args.trace_id, safe='')}"))


def cmd_trace_add(args: argparse.Namespace) -> None:
    payload = json.loads(args.payload) if args.payload else None
    _dump(_post("/trace", {"trace_id": args.trace_id, "stage": args.stage, "status": args.status, "message": args.message, "payload": payload}))


def cmd_config_show(_args: argparse.Namespace) -> None:
    _dump({"WM_DEBUG_API_URL": API_BASE, "WM_DEBUG_TIMEOUT": TIMEOUT})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wmctl", description="WorldMind OpenTwins Debug CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="一键健康检查")
    doctor.set_defaults(func=cmd_doctor)

    mqtt = sub.add_parser("mqtt", help="MQTT 调试")
    mqtt_sub = mqtt.add_subparsers(dest="mqtt_command", required=True)
    mqtt_tail = mqtt_sub.add_parser("tail", help="订阅 MQTT topic 并输出消息样例")
    mqtt_tail.add_argument("--topic", default="telemetry/#")
    mqtt_tail.add_argument("--seconds", type=int, default=10)
    mqtt_tail.add_argument("--limit", type=int, default=20)
    mqtt_tail.set_defaults(func=cmd_mqtt_tail)

    twin = sub.add_parser("twin", help="Ditto Thing 调试")
    twin_sub = twin.add_subparsers(dest="twin_command", required=True)
    twin_echo = twin_sub.add_parser("echo", help="查看 Ditto Thing 当前状态")
    twin_echo.add_argument("thing_id")
    twin_echo.set_defaults(func=cmd_twin_echo)
    twin_watch = twin_sub.add_parser("watch", help="周期性查看 feature 值")
    twin_watch.add_argument("thing_id")
    twin_watch.add_argument("--feature", required=True)
    twin_watch.add_argument("--interval", type=float, default=2)
    twin_watch.set_defaults(func=cmd_twin_watch)

    conn = sub.add_parser("conn", help="Ditto Connection 调试")
    conn_sub = conn.add_subparsers(dest="conn_command", required=True)
    conn_list = conn_sub.add_parser("list", help="列出 Ditto Connections")
    conn_list.set_defaults(func=cmd_conn_list)
    for name, func in (("status", cmd_conn_status), ("metrics", cmd_conn_metrics), ("logs", cmd_conn_logs)):
        item = conn_sub.add_parser(name)
        item.add_argument("connection_id")
        item.set_defaults(func=func)

    influx = sub.add_parser("influx", help="InfluxDB 调试")
    influx_sub = influx.add_subparsers(dest="influx_command", required=True)
    recent = influx_sub.add_parser("recent", help="查询最近时序数据")
    recent.add_argument("--measurement", required=True)
    recent.add_argument("--bucket", default=None)
    recent.add_argument("--minutes", type=int, default=60)
    recent.set_defaults(func=cmd_influx_recent)

    trace = sub.add_parser("trace", help="查看 trace_id 链路")
    trace.add_argument("trace_id")
    trace.set_defaults(func=cmd_trace)

    trace_add = sub.add_parser("trace-add", help="写入一条本地调试 trace")
    trace_add.add_argument("trace_id")
    trace_add.add_argument("--stage", required=True)
    trace_add.add_argument("--status", required=True)
    trace_add.add_argument("--message", default=None)
    trace_add.add_argument("--payload", default=None, help="JSON 字符串")
    trace_add.set_defaults(func=cmd_trace_add)

    config = sub.add_parser("config", help="CLI 配置")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    show = config_sub.add_parser("show", help="查看当前 Debug 配置")
    show.set_defaults(func=cmd_config_show)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
