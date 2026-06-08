import math
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.clients.influx_client import InfluxClient


def _get_engine_info():
    """获取仿真引擎的当前轮次信息（started_at 和 elapsed_hours）。"""
    try:
        from app.services.simulation_engine import engine
        return engine.status()
    except Exception:
        return None


def generated(tank_id, metric, hours, started_at=None, elapsed_hours=None):
    """生成模拟历史数据。

    时间戳使用真实墙钟时间：每个仿真小时对应的真实时间取决于仿真速度。
    例如 speed=3600, interval=5s 时，每步推进 5 仿真小时，耗时 5 真实秒。

    Args:
        tank_id: 罐体 ID
        metric: 指标名称
        hours: 请求的历史时长（小时）
        started_at: 当前仿真轮次的起始时间（ISO 字符串或 datetime）
        elapsed_hours: 当前仿真已运行的小时数，如果提供则只生成 0→elapsed 范围的数据
    """
    cfg = {t['tank_id']: t for t in settings.sim_config.get('tanks', [])}.get(tank_id, {})
    b0 = float(cfg.get('initial_brix', 24))
    bf = float(cfg.get('final_brix', -1))
    maxa = float(cfg.get('max_alcohol', 13))
    target = float(cfg.get('target_temp', 25))
    ph0 = float(cfg.get('initial_ph', 3.4))
    total = 288.0
    # 从 tank 配置读取动力学参数（与 simulation_engine 保持一致）
    fermentation_k_mult = float(cfg.get('fermentation_k_mult', 1.0))
    heat_amplitude = float(cfg.get('heat_amplitude', 4.0))
    daily_temp_amplitude = float(cfg.get('daily_temp_amplitude', 0.6))
    co2_peak = float(cfg.get('co2_peak', 7200))
    co2_peak_pos = float(cfg.get('co2_peak_pos', 0.32))
    co2_peak_width = float(cfg.get('co2_peak_width', 0.14))
    ph_drop_rate = float(cfg.get('ph_drop_rate', 0.08))

    # 仿真速度参数
    sim_speed = float(settings.sim_config.get('simulation', {}).get('speed', 3600))
    sim_interval = float(settings.sim_config.get('simulation', {}).get('interval_seconds', 5))
    # 每步推进的仿真小时数
    step_sim_hours = sim_interval * sim_speed / 3600.0

    # 如果有 elapsed_hours，只展示当前轮次已运行的部分
    effective_hours = min(hours, elapsed_hours) if elapsed_hours is not None else hours

    # 确定时间基准（真实墙钟时间）
    if started_at is not None:
        if isinstance(started_at, str):
            base_time = datetime.fromisoformat(started_at)
        else:
            base_time = started_at
        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=timezone.utc)
    else:
        base_time = datetime.now(timezone.utc)

    pts = []
    step = max(1, int(effective_hours / 48)) if effective_hours > 0 else 1
    for h_offset in range(0, int(effective_hours) + 1, step):
        elapsed = h_offset
        k = math.log(max((b0 - bf) / 0.15, 1.01)) / total * fermentation_k_mult
        brix = bf + (b0 - bf) * math.exp(-k * elapsed)
        progress = max(0, min(1, (b0 - brix) / (b0 - bf)))
        vals = {
            'brix': brix,
            'temperature': target + heat_amplitude * math.sin(math.pi * progress) + daily_temp_amplitude * math.sin(2 * math.pi * (elapsed % 24) / 24),
            'ph': ph0 - ph_drop_rate * progress,
            'co2': 420 + co2_peak * math.exp(-((elapsed - total * co2_peak_pos) ** 2) / (2 * (total * co2_peak_width) ** 2)),
            'alcohol_estimation': maxa * progress,
            'fermentation_progress': progress * 100,
        }
        # 计算真实墙钟时间：sim_hour H 是在 started_at + H/step_sim_hours * interval 秒时发布的
        real_seconds = (h_offset / step_sim_hours) * sim_interval if step_sim_hours > 0 else 0
        pts.append({
            'timestamp': (base_time + timedelta(seconds=real_seconds)).isoformat(),
            'value': round(vals.get(metric, brix), 2),
        })
    return pts


def history(tank_id, metric='brix', hours=48):
    pts = []

    # 获取仿真引擎轮次信息
    engine_info = _get_engine_info()
    started_at = engine_info.get('started_at') if engine_info else None
    elapsed_hours = engine_info.get('elapsed_hours') if engine_info else None

    try:
        client = InfluxClient(settings.influx_url, settings.influx_token, settings.influx_org, settings.influx_bucket)
        if started_at:
            # 只查询当前轮次起始时间之后的数据
            pts = client.query_metric(tank_id, metric, hours, start_time=started_at)
        else:
            pts = client.query_metric(tank_id, metric, hours)
    except Exception as e:
        print('history fallback', e)

    # 如果 InfluxDB 没有数据，使用 generated() 回退
    if not pts:
        pts = generated(tank_id, metric, hours, started_at=started_at, elapsed_hours=elapsed_hours)

    return {'tank_id': tank_id, 'metric': metric, 'points': pts}
