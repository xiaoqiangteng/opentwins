from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/debug/logs", tags=["logs"])


@router.get("/tail")
def tail_log(path: str = Query(...), lines: int = 100):
    log_path = Path(path)
    if not log_path.exists() or not log_path.is_file():
        return {"status": "error", "message": f"日志文件不存在: {path}", "lines": []}
    data = log_path.read_text(errors="replace").splitlines()[-max(1, min(lines, 500)) :]
    return {"status": "ok", "path": str(log_path), "lines": data}
