import os
from pathlib import Path


class Settings:
    model_root = Path(os.getenv("MODEL_ROOT", "/app")).resolve()
    runtime_dir = Path(os.getenv("MODELICA_RUNTIME_DIR", str(model_root / "runtime"))).resolve()
    omc_bin = os.getenv("OMC_BIN", "omc")
    max_timeout_seconds = int(os.getenv("MODELICA_TIMEOUT_SECONDS", "120"))


settings = Settings()
