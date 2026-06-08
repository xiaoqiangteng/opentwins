from __future__ import annotations

from fastapi import HTTPException


def api_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=502, detail=str(exc))
