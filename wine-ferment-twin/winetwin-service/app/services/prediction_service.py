from app.services.twin_service import get_tank

# 温度阈值参数（与 modelica_prediction_service.py 保持一致）
TANK_PARAMS = {
    "tank_01": {
        "wine_type": "red",
        "optimal_temperature": 25.0,
        "warning_temperature": 30.0,
        "critical_temperature": 33.0,
        "too_cold_threshold": 18.0,
    },
    "tank_02": {
        "wine_type": "red",
        "optimal_temperature": 26.0,
        "warning_temperature": 30.0,
        "critical_temperature": 33.0,
        "too_cold_threshold": 18.0,
    },
    "tank_03": {
        "wine_type": "white",
        "optimal_temperature": 14.0,
        "warning_temperature": 18.0,
        "critical_temperature": 22.0,
        "too_cold_threshold": 8.0,
    },
}

DEFAULT_PARAMS = {
    "wine_type": "red",
    "optimal_temperature": 25.0,
    "warning_temperature": 30.0,
    "critical_temperature": 33.0,
    "too_cold_threshold": 18.0,
}


def _current_temperature(tank_id: str) -> float | None:
    """从孪生体获取当前温度，获取失败则使用默认值。"""
    tank = get_tank(tank_id)
    if tank and tank.get("metrics", {}).get("temperature", {}).get("value") is not None:
        return float(tank["metrics"]["temperature"]["value"])
    # 降级：使用默认温度
    return DEFAULT_PARAMS["optimal_temperature"]


def _compute_quality_gain(current_temp: float, new_temp: float, params: dict, nutrient: float) -> float:
    """基于偏移后温度所在区间计算质量增益。"""
    optimal = params["optimal_temperature"]
    warning = params["warning_temperature"]
    critical = params["critical_temperature"]
    too_cold = params["too_cold_threshold"]

    # 温度区间判定
    if new_temp >= critical:
        # 超过危险阈值：严重扣分，距离阈值越远扣分越多
        overshoot = new_temp - critical
        temp_gain = -6.0 - overshoot * 0.8
    elif new_temp >= warning:
        # 超过警告阈值：中度扣分
        overshoot = new_temp - warning
        temp_gain = -2.0 - overshoot * 1.2
    elif new_temp < too_cold:
        # 过冷：严重扣分
        undershoot = too_cold - new_temp
        temp_gain = -6.0 - undershoot * 0.8
    elif new_temp < optimal - 2:
        # 偏低于最适区间：轻微扣分，但好于过热/过冷
        undershoot = optimal - 2 - new_temp
        temp_gain = -0.5 - undershoot * 0.6
    else:
        # 在最适区间内（optimal-2 ~ warning）：正增益
        # 越接近 optimal 增益越高
        dist_from_optimal = abs(new_temp - optimal)
        temp_gain = 3.0 - dist_from_optimal * 0.4

    # 叠加营养增益
    nutrient_gain = nutrient * 2.0

    gain = temp_gain + nutrient_gain
    return round(max(-8, min(8, gain)), 1)


def prediction(tank_id):
    from app.services.history_service import generated
    from datetime import datetime, timedelta, timezone
    pts = generated(tank_id, 'fermentation_progress', 24); cur = pts[-1]['value'] if pts else 50; hours_left = max(0, round((98 - cur) / 2.4, 1))
    return {'tank_id': tank_id, 'horizon_hours': 24, 'estimated_completion_time': (datetime.now(timezone.utc) + timedelta(hours=hours_left)).isoformat(), 'current_progress': cur, 'future_progress': pts[-24:] if len(pts) > 24 else pts, 'message': '预测基于发酵进度趋势，可替换为校准模型提升精度。'}


def simulate(tank_id, payload):
    temp_delta = float(payload.get('temperature_delta', 0) if isinstance(payload, dict) else 0)
    nutrient = float(payload.get('nutrient_boost', 0) if isinstance(payload, dict) else 0)

    # 获取罐体参数
    short_id = tank_id.split(':')[-1] if ':' in tank_id else tank_id
    params = TANK_PARAMS.get(short_id, DEFAULT_PARAMS)

    # 获取当前温度，计算偏移后温度
    current_temp = _current_temperature(tank_id)
    new_temp = current_temp + temp_delta

    # 基于温度区间计算质量增益
    gain = _compute_quality_gain(current_temp, new_temp, params, nutrient)

    # 根据增益生成推荐语
    if gain <= -4:
        recommendation = '偏移后温度将超出安全范围，强烈建议不要执行此调整。'
    elif gain < 0:
        recommendation = '偏移后温度不利于发酵品质，请在验证传感器读数和酒窖操作规程约束后再执行调整。'
    elif gain <= 2:
        recommendation = '偏移后温度在可接受范围内，建议继续观察发酵状态。'
    else:
        recommendation = '偏移后温度接近最适区间，有利于提升发酵品质。'

    return {
        'tank_id': tank_id,
        'input': payload,
        'current_temperature': round(current_temp, 1),
        'projected_temperature': round(new_temp, 1),
        'projected_quality_delta': gain,
        'recommendation': recommendation,
    }
