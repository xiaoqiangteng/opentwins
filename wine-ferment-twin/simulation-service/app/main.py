import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException

from app.core.config import settings
from app.schemas.simulation import SimulationRequest, SimulationResponse, WhatIfRequest
from app.services.modelica_runner import RESULT_DIR, build_mos, run_demo, run_omc
from app.services.result_parser import parse_csv
from app.services.risk_evaluator import estimated_completion, risk_label


app = FastAPI(title="OpenModelica Simulation Service", version="1.0.0")


@app.get("/health")
def health():
    try:
        out = subprocess.run([settings.omc_bin, "--version"], capture_output=True, text=True, timeout=20)
        if out.returncode != 0:
            return {"status": "error", "omc": out.stderr.strip() or out.stdout.strip()}
        return {"status": "ok", "omc": out.stdout.strip() or out.stderr.strip()}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.post("/api/modelica/demo")
def demo():
    try:
        result = run_demo()
        return {"engine": "OpenModelica", "model": "WineFermentation.HelloWine", "raw_result_file": str(result)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _latest_result(tank_id: str) -> Path:
    csv_files = sorted(RESULT_DIR.glob(f"{tank_id}_*_res.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not csv_files:
        raise RuntimeError("No OpenModelica CSV result generated")
    return csv_files[0]


def _response(req: SimulationRequest, csv_path: Path) -> SimulationResponse:
    points = parse_csv(csv_path)
    last = points[-1]
    return SimulationResponse(
        tank_id=req.tank_id,
        model="WineFermentation.ContinuationFermentation",
        horizon_hours=req.horizon_hours,
        estimated_completion_hours=estimated_completion(points),
        risk_level=risk_label(last["risk_code"]),
        quality_score_end=last["quality_score"],
        points=points,
        raw_result_file=str(csv_path),
    )


@app.post("/api/modelica/simulate", response_model=SimulationResponse)
def simulate(req: SimulationRequest):
    try:
        mos = build_mos(req)
        run_omc(mos)
        return _response(req, _latest_result(req.tank_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/modelica/what-if", response_model=SimulationResponse)
def what_if(req: WhatIfRequest):
    try:
        mos = build_mos(req, temperature_delta=req.temperature_delta, nutrient_boost=req.nutrient_boost)
        run_omc(mos)
        return _response(req, _latest_result(req.tank_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
