import random

def apply_anomaly(tank, point, elapsed_hours):
    a=tank.get('anomaly')
    if a == 'temperature_high' and elapsed_hours >= 40:
        point['temperature']=round(point['temperature']+4.8+min(2.0,(elapsed_hours-40)/48),2)
    elif a == 'stuck_fermentation' and elapsed_hours >= 72:
        base=float(tank['initial_brix'])
        point['brix']=round(max(point['brix'], base-5.2-(elapsed_hours-72)*0.015),2)
        progress=max(0.0,min(100.0,(base-point['brix'])/(base-float(tank['final_brix']))*100))
        point['fermentation_progress']=round(progress,1)
        point['alcohol_estimation']=round(float(tank['max_alcohol'])*progress/100,2)
    elif a == 'ph_abnormal' and elapsed_hours >= 96:
        point['ph']=round(point['ph']+0.45,2)
    elif a == 'co2_low' and 36 <= elapsed_hours <= 120:
        point['co2']=round(point['co2']*0.18,1)
    elif a == 'sensor_missing' and random.random()<0.12:
        point['temperature']=None
    elif a == 'sensor_spike' and random.random()<0.08:
        point['temperature']=round(point['temperature']+random.choice([-8,8]),2)
    return point
