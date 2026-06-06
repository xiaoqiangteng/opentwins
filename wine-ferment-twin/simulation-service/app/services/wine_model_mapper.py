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


def params_for_tank(tank_id: str):
    return TANK_PARAMS.get(tank_id.split(":")[-1], TANK_PARAMS["tank_01"])
