from __future__ import annotations

import subprocess
from typing import List


class DockerAdapter:
    def ps(self) -> List[str]:
        proc = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "docker ps 执行失败")
        return [line for line in proc.stdout.splitlines() if line.strip()]
