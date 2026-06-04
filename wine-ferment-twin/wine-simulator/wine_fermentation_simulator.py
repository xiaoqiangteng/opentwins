#!/usr/bin/env python3
import argparse, csv, os, sys, time, yaml
from datetime import datetime, timezone
from pathlib import Path
from fermentation_model import simulate_point
from anomaly_injector import apply_anomaly
from mqtt_client import DittoMqttPublisher

UNITS={'temperature':'C','ph':'','brix':'Bx','specific_gravity':'','co2':'ppm','pressure':'kPa','liquid_level':'%','alcohol_estimation':'%vol','fermentation_progress':'%'}

def risk_and_score(tank, p):
    wt=tank.get('wine_type','red'); temp=p.get('temperature'); ph=p.get('ph'); co2=p.get('co2'); brix=p.get('brix')
    warn=30 if wt=='red' else 18; crit=33 if wt=='red' else 22; phlo=3.1 if wt=='red' else 3.0; phhi=3.8 if wt=='red' else 3.7
    score=100.0; risk='normal'; rec='Continue normal fermentation monitoring.'
    if temp is None: return 'offline', 45.0, 'Check sensor power, wiring and gateway connectivity.'
    if temp>crit or ph<3.0 or ph>3.9: risk='critical'; score-=32; rec='Stop automatic escalation, inspect tank and activate corrective control.'
    elif temp>warn: risk='warning'; score-=18; rec='Activate cooling or reduce target temperature.'
    if ph<phlo or ph>phhi: risk='critical' if risk!='offline' else risk; score-=18; rec='Check acidity and validate pH sensor calibration.'
    if tank.get('anomaly')=='stuck_fermentation' and p['fermentation_progress']<40 and p['fermentation_stage']=='active': risk='warning'; score-=22; rec='Check yeast activity, nutrients, oxygen exposure and temperature profile.'
    if p['fermentation_stage']=='active' and co2 < (1500 if wt=='red' else 1200): risk='warning'; score-=12; rec='CO2 is lower than expected for active fermentation; check yeast vitality.'
    if p['fermentation_progress']>=98 and risk=='normal': risk='finished'; rec='Fermentation is near completion; prepare clarification and transfer plan.'
    return risk, round(max(0,min(100,score)),1), rec

def as_features(point, risk, score, rec):
    now=datetime.now(timezone.utc).isoformat()
    out={}
    for k,v in point.items():
        props={'value':v,'observed_at':now}
        if k in UNITS: props['unit']=UNITS[k]
        out[k]={'properties':props}
    out['quality_score']={'properties':{'value':score,'observed_at':now}}
    out['risk_level']={'properties':{'value':risk,'observed_at':now}}
    out['recommendation']={'properties':{'value':rec,'observed_at':now}}
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',required=True); ap.add_argument('--once',action='store_true'); args=ap.parse_args()
    cfg=yaml.safe_load(Path(args.config).read_text())
    sim=cfg['simulation']; mqtt_cfg=cfg['mqtt']; namespace=cfg.get('ditto',{}).get('namespace','wine')
    host=os.getenv('MQTT_HOST', mqtt_cfg.get('host','127.0.0.1')); port=int(os.getenv('MQTT_PORT', mqtt_cfg.get('port',30511)))
    pub=DittoMqttPublisher(host, port, os.getenv('MQTT_USERNAME', mqtt_cfg.get('username')), os.getenv('MQTT_PASSWORD', mqtt_cfg.get('password')), mqtt_cfg.get('qos',1), sim.get('mqtt_topic_prefix','opentwins'))
    csv_dir=Path('wine-simulator/data/generated_csv'); csv_dir.mkdir(parents=True, exist_ok=True)
    csv_file=csv_dir/('wine_simulation_%s.csv'%datetime.now().strftime('%Y%m%d_%H%M%S'))
    f=csv_file.open('w',newline='') if sim.get('save_csv',True) else None
    writer=None
    if f:
        writer=csv.DictWriter(f, fieldnames=['timestamp','tank_id','thing_id','temperature','ph','brix','specific_gravity','co2','pressure','liquid_level','alcohol_estimation','fermentation_progress','fermentation_stage','quality_score','risk_level','recommendation'])
        writer.writeheader()
    for t in cfg['tanks']: t['total_hours']=float(sim.get('total_days',12))*24
    try:
        pub.connect(); elapsed=0.0; speed=float(sim.get('speed',3600)); interval=float(sim.get('interval_seconds',5))
        while True:
            for tank in cfg['tanks']:
                p=apply_anomaly(tank, simulate_point(tank, elapsed), elapsed)
                risk,score,rec=risk_and_score(tank,p); features=as_features(p,risk,score,rec)
                pub.publish_features(namespace, tank['tank_id'], tank['thing_id'], tank.get('parent_id','wine:workshop_01'), features)
                row={'timestamp':datetime.now(timezone.utc).isoformat(),'tank_id':tank['tank_id'],'thing_id':tank['thing_id'],**p,'quality_score':score,'risk_level':risk,'recommendation':rec}
                if writer: writer.writerow(row); f.flush()
                print(f"sent {tank['thing_id']} t={elapsed:.1f}h risk={risk} brix={p.get('brix')} temp={p.get('temperature')}")
            if args.once: break
            elapsed += interval*speed/3600.0; time.sleep(interval)
    finally:
        try: pub.close()
        except Exception: pass
        if f: f.close(); print(f'csv saved: {csv_file}')
if __name__=='__main__': main()
