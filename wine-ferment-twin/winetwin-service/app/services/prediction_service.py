from datetime import datetime, timedelta, timezone
from app.services.history_service import generated

def prediction(tank_id):
    pts=generated(tank_id,'fermentation_progress',24); cur=pts[-1]['value'] if pts else 50; hours_left=max(0,round((98-cur)/2.4,1))
    return {'tank_id':tank_id,'horizon_hours':24,'estimated_completion_time':(datetime.now(timezone.utc)+timedelta(hours=hours_left)).isoformat(),'current_progress':cur,'future_progress':pts[-24:] if len(pts)>24 else pts,'message':'Prediction uses fermentation progress trend and can be replaced by a calibrated model.'}
def simulate(tank_id,payload):
    temp_delta=float(payload.get('temperature_delta',0) if isinstance(payload,dict) else 0); nutrient=float(payload.get('nutrient_boost',0) if isinstance(payload,dict) else 0); gain=max(-8,min(8,-temp_delta*0.6+nutrient*2.0))
    return {'tank_id':tank_id,'input':payload,'projected_quality_delta':round(gain,1),'recommendation':'Apply adjustment only after validating sensor readings and cellar SOP constraints.'}
