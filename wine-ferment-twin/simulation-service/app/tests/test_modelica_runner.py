from app.schemas.simulation import CurrentState, ModelParams, SimulationRequest
from app.services.modelica_runner import build_mos


def test_build_mos_contains_overrides(tmp_path, monkeypatch):
    req = SimulationRequest(
        tank_id="tank_01",
        wine_type="red",
        current_state=CurrentState(brix=16.2, alcohol=4.3, co2=3200.0, temperature=25.4),
        model_params=ModelParams(
            initial_brix_reference=24.5,
            final_brix=-1.0,
            optimal_temperature=25.0,
            warning_temperature=30.0,
            critical_temperature=33.0,
        ),
    )
    path = build_mos(req)
    text = path.read_text(encoding="utf-8")
    assert "WineFermentation.ContinuationFermentation" in text
    assert "brixStart=16.2" in text
