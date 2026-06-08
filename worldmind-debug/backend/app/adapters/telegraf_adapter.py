from __future__ import annotations

import subprocess
from typing import Dict

from app.config import Settings


class TelegrafAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def status(self) -> Dict[str, str]:
        proc = subprocess.run(
            [
                "kubectl",
                "get",
                "pods",
                "-n",
                self.settings.kubernetes_namespace,
                "-l",
                "app.kubernetes.io/name=telegraf",
                "--no-headers",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode != 0:
            return {"status": "skipped", "message": "kubectl 不可用或集群未响应，跳过 Telegraf 检查"}
        output = proc.stdout.strip()
        if not output:
            return {"status": "skipped", "message": "未找到 Telegraf pod"}
        if "Running" in output:
            return {"status": "ok", "message": output}
        return {"status": "warning", "message": output}
