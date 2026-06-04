import math, random

def clamp(v, lo, hi): return max(lo, min(hi, v))

def brix_to_sg(brix):
    return 1 + brix / (258.6 - ((brix / 258.2) * 227.1))

def stage(progress):
    if progress < 0.10: return 'initial'
    if progress < 0.80: return 'active'
    if progress < 0.98: return 'late'
    return 'finished'

def simulate_point(tank, elapsed_hours):
    total_hours=float(tank.get('total_hours', 288))
    b0=float(tank['initial_brix']); bf=float(tank['final_brix']); max_alc=float(tank['max_alcohol'])
    k=math.log(max((b0-bf)/0.15, 1.01))/total_hours
    brix=bf+(b0-bf)*math.exp(-k*elapsed_hours)
    progress=clamp((b0-brix)/(b0-bf),0,1)
    heat=4.0*math.sin(math.pi*progress) if progress < 1 else 0
    daily=0.6*math.sin(2*math.pi*(elapsed_hours%24)/24.0)
    temp=float(tank['target_temp'])+heat+daily+random.uniform(-0.25,0.25)
    co2=420+7200*math.exp(-((elapsed_hours-total_hours*0.32)**2)/(2*(total_hours*0.14)**2))+random.uniform(-90,90)
    ph=float(tank['initial_ph'])-0.08*progress+random.uniform(-0.025,0.025)
    pressure=101.3+min(3.5, co2/4200)+random.uniform(-0.15,0.15)
    return {
        'temperature': round(temp,2), 'ph': round(ph,2), 'brix': round(brix,2),
        'specific_gravity': round(brix_to_sg(max(brix,0)),4), 'co2': round(max(250,co2),1),
        'pressure': round(pressure,2), 'liquid_level': round(float(tank.get('liquid_level',82.0)),1),
        'alcohol_estimation': round(max_alc*progress,2), 'fermentation_progress': round(progress*100,1),
        'fermentation_stage': stage(progress)
    }
