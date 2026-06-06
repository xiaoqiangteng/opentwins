from app.clients import modelica_client


TANK_PARAMS = {
    "tank_01": {
        "wine_type": "red",
        "initial_brix_reference": 24.5,
        "final_brix": -1.0,
        "optimal_temperature": 25.0,
        "warning_temperature": 30.0,
        "critical_temperature": 33.0,
    },
    "tank_02": {
        "wine_type": "red",
        "initial_brix_reference": 25.0,
        "final_brix": -0.8,
        "optimal_temperature": 26.0,
        "warning_temperature": 30.0,
        "critical_temperature": 33.0,
    },
    "tank_03": {
        "wine_type": "white",
        "initial_brix_reference": 22.5,
        "final_brix": -1.0,
        "optimal_temperature": 14.0,
        "warning_temperature": 18.0,
        "critical_temperature": 22.0,
    },
}


def feature_value(features: dict, name: str, default=None):
    try:
        value = features[name]["properties"]["value"]
        return default if value is None else value
    except Exception:
        return default


def build_request_from_twin(tank_id: str, twin: dict, horizon_hours: int = 24):
    short_id = tank_id.split(":")[-1]
    params = TANK_PARAMS.get(short_id, TANK_PARAMS["tank_01"])
    twin = twin or {}
    features = twin.get("features") or {}
    attrs = twin.get("attributes") or {}
    current_state = {
        "brix": float(feature_value(features, "brix", params["initial_brix_reference"])),
        "alcohol": float(feature_value(features, "alcohol_estimation", 0.0)),
        "co2": float(feature_value(features, "co2", 420.0)),
        "temperature": float(feature_value(features, "temperature", params["optimal_temperature"])),
        "ph": feature_value(features, "ph", None),
        "progress": feature_value(features, "fermentation_progress", None),
    }
    return {
        "tank_id": short_id,
        "wine_type": attrs.get("wine_type") or params["wine_type"],
        "horizon_hours": horizon_hours,
        "step_hours": 1,
        "current_state": current_state,
        "model_params": {
            "initial_brix_reference": params["initial_brix_reference"],
            "final_brix": params["final_brix"],
            "optimal_temperature": params["optimal_temperature"],
            "warning_temperature": params["warning_temperature"],
            "critical_temperature": params["critical_temperature"],
        },
    }


def modelica_prediction(tank_id: str, twin: dict, horizon_hours: int = 24):
    payload = build_request_from_twin(tank_id, twin, horizon_hours)
    return modelica_client.simulate(payload)


def modelica_what_if(tank_id: str, twin: dict, body: dict):
    payload = build_request_from_twin(tank_id, twin, int(body.get("horizon_hours", 24)))
    payload["temperature_delta"] = float(body.get("temperature_delta", 0.0))
    payload["nutrient_boost"] = float(body.get("nutrient_boost", 0.0))
    return modelica_client.what_if(payload)
