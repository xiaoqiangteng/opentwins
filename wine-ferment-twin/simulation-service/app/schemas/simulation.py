from typing import List, Optional
from pydantic import BaseModel, Field


class CurrentState(BaseModel):
    brix: float
    alcohol: float = 0.0
    co2: float = 420.0
    temperature: float
    ph: Optional[float] = None
    progress: Optional[float] = None


class ModelParams(BaseModel):
    initial_brix_reference: float
    final_brix: float
    optimal_temperature: float
    warning_temperature: float
    critical_temperature: float
    k_sugar: float = 0.018
    y_alcohol: float = 0.55
    y_co2: float = 260.0


class SimulationRequest(BaseModel):
    tank_id: str
    wine_type: str = "red"
    horizon_hours: int = Field(default=24, ge=1, le=240)
    step_hours: int = Field(default=1, ge=1, le=12)
    current_state: CurrentState
    model_params: ModelParams


class WhatIfRequest(SimulationRequest):
    temperature_delta: float = 0.0
    nutrient_boost: float = 0.0


class SimulationPoint(BaseModel):
    hour: float
    brix: float
    alcohol: float
    co2: float
    progress: float
    quality_score: float
    risk_code: int


class SimulationResponse(BaseModel):
    tank_id: str
    engine: str = "OpenModelica"
    model: str
    horizon_hours: int
    estimated_completion_hours: Optional[float] = None
    risk_level: str
    quality_score_end: float
    points: List[SimulationPoint]
    raw_result_file: Optional[str] = None
