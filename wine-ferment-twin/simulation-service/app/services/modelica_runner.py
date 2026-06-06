import subprocess
import threading
import uuid
from pathlib import Path

from app.core.config import settings
from app.schemas.simulation import SimulationRequest


ROOT = settings.model_root
MODEL_FILE = ROOT / "modelica" / "WineFermentation.mo"
RUNTIME = settings.runtime_dir
MOS_DIR = RUNTIME / "mos"
RESULT_DIR = RUNTIME / "results"
OMC_LOCK = threading.Lock()


def _clean_number(value):
    return str(float(value))


def build_mos(req: SimulationRequest, temperature_delta: float = 0.0, nutrient_boost: float = 0.0) -> Path:
    MOS_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = f"{req.tank_id}_{uuid.uuid4().hex[:8]}"
    result_file = RESULT_DIR / f"{run_id}_res.csv"
    temperature_set = req.current_state.temperature + temperature_delta
    intervals = max(1, int(req.horizon_hours / req.step_hours))
    mp = req.model_params
    cs = req.current_state
    k_sugar = mp.k_sugar * (1.0 + max(nutrient_boost, 0.0) * 0.08)
    mos = f"""loadFile("{MODEL_FILE.as_posix()}");
simulate(
  WineFermentation.ContinuationFermentation,
  startTime=0,
  stopTime={int(req.horizon_hours)},
  numberOfIntervals={intervals},
  outputFormat="csv",
  simflags="-override=initialBrixReference={_clean_number(mp.initial_brix_reference)},finalBrix={_clean_number(mp.final_brix)},brixStart={_clean_number(cs.brix)},alcoholStart={_clean_number(cs.alcohol)},co2Start={_clean_number(cs.co2)},temperatureSet={_clean_number(temperature_set)},optimalTemperature={_clean_number(mp.optimal_temperature)},warningTemperature={_clean_number(mp.warning_temperature)},criticalTemperature={_clean_number(mp.critical_temperature)},kSugar={_clean_number(k_sugar)},yAlcohol={_clean_number(mp.y_alcohol)},yCO2={_clean_number(mp.y_co2)} -r={result_file.as_posix()}");
getErrorString();
"""
    path = MOS_DIR / f"{run_id}.mos"
    path.write_text(mos, encoding="utf-8")
    return path


def run_omc(mos_file: Path) -> str:
    with OMC_LOCK:
        proc = subprocess.run(
            [settings.omc_bin, str(mos_file)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=settings.max_timeout_seconds,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"OpenModelica failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc.stdout + "\n" + proc.stderr


def run_demo() -> Path:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    demo_script = ROOT / "modelica" / "scripts" / "run_hello_wine.mos"
    run_omc(demo_script)
    candidates = [
        ROOT / "WineFermentation.HelloWine_res.csv",
        ROOT / "WineFermentation.HelloWine_res.mat",
    ]
    result = None
    for src in candidates:
        if src.exists():
            dst = RESULT_DIR / src.name
            src.replace(dst)
            result = dst
    if result is None:
        raise RuntimeError("No HelloWine result file generated")
    return result
