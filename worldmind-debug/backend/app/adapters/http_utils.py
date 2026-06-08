from __future__ import annotations

from typing import Any, Dict

import requests


def response_payload(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return {"text": resp.text[:2000]}


def ok_result(message: str, **details: Any) -> Dict[str, Any]:
    return {"status": "ok", "message": message, **details}


def error_result(message: str, **details: Any) -> Dict[str, Any]:
    return {"status": "error", "message": message, **details}


def warning_result(message: str, **details: Any) -> Dict[str, Any]:
    return {"status": "warning", "message": message, **details}
