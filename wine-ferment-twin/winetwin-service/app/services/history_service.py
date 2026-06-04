import math
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.clients.influx_client import InfluxClient

def generated(tank_id, metric, hours):
    cfg={t['tank_id']:t for t in settings.sim_config.get('tanks',[])}.get(tank_id,{})
    b0=float(cfg.get('initial_brix',24)); bf=float(cfg.get('final_brix',-1)); maxa=float(cfg.get('max_alcohol',13)); target=float(cfg.get('target_temp',25)); ph0=float(cfg.get('initial_ph',3.4)); total=288.0
    pts=[]; now=datetime.now(timezone.utc); step=max(1,int(hours/48))
    for h in range(int(hours),-1,-step):
        elapsed=max(0,total-h); k=math.log(max((b0-bf)/0.15,1.01))/total; brix=bf+(b0-bf)*math.exp(-k*elapsed); progress=max(0,min(1,(b0-brix)/(b0-bf)))
        vals={'brix':brix,'temperature':target+4*math.sin(math.pi*progress)+0.5*math.sin(2*math.pi*(elapsed%24)/24),'ph':ph0-0.08*progress,'co2':420+7200*math.exp(-((elapsed-total*0.32)**2)/(2*(total*0.14)**2)),'alcohol_estimation':maxa*progress,'fermentation_progress':progress*100}
        pts.append({'timestamp':(now-timedelta(hours=h)).isoformat(),'value':round(vals.get(metric,brix),2)})
    return pts
def history(tank_id, metric='brix', hours=48):
    pts=[]
    try: pts=InfluxClient(settings.influx_url,settings.influx_token,settings.influx_org,settings.influx_bucket).query_metric(tank_id,metric,hours)
    except Exception as e: print('history fallback',e)
    return {'tank_id':tank_id,'metric':metric,'points':pts or generated(tank_id,metric,hours)}
