def recommendations(tank):
    if tank.get('alarms'): return [a.get('recommendation') for a in tank['alarms']]
    return [tank.get('recommendation','Continue monitoring.')]
