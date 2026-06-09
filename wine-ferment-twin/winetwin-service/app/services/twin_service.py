from app.core.config import settings
from app.clients.ditto_client import DittoClient
from app.services.rules import metric, unit, evaluate

def tank_ids(): return ['tank_01','tank_02','tank_03']
def thing_id(tank_id): return 'wine:'+tank_id
def default_attrs(tank_id):
    return {'name':'Fermentation Tank '+tank_id[-2:],'type':'FermentationTank','wine_type':'white' if tank_id=='tank_03' else 'red','_parents':['wine:workshop_01']}
def default_features(tank_id):
    temp=14.0 if tank_id=='tank_03' else (31.0 if tank_id=='tank_02' else 25.0); progress=30.0 if tank_id=='tank_03' else 45.0
    return {'temperature':{'properties':{'value':temp,'unit':'C'}},'ph':{'properties':{'value':3.42,'unit':''}},'brix':{'properties':{'value':18.5 if tank_id=='tank_03' else 17.0,'unit':'Bx'}},'specific_gravity':{'properties':{'value':1.07,'unit':''}},'co2':{'properties':{'value':900 if tank_id=='tank_03' else 6000,'unit':'ppm'}},'pressure':{'properties':{'value':102.1,'unit':'kPa'}},'liquid_level':{'properties':{'value':80,'unit':'%'}},'alcohol_estimation':{'properties':{'value':5.1,'unit':'%vol'}},'fermentation_progress':{'properties':{'value':progress,'unit':'%'}},'fermentation_stage':{'properties':{'value':'active'}},'quality_score':{'properties':{'value':86}},'risk_level':{'properties':{'value':'normal'}},'recommendation':{'properties':{'value':'Continue monitoring.'}}}
def normalize(tank_id, thing):
    attrs=(thing or {}).get('attributes') or default_attrs(tank_id); features=(thing or {}).get('features') or default_features(tank_id); ev=evaluate(attrs,features,settings.alarm_rules)
    metrics={}
    for k in ['temperature','ph','brix','specific_gravity','co2','pressure','liquid_level','alcohol_estimation','fermentation_progress','quality_score']:
        metrics[k]={'value': metric(features,k,ev['quality_score'] if k=='quality_score' else None), 'unit': unit(features,k,'')}
    updated_at=None
    for f in features.values(): updated_at=(f.get('properties') or {}).get('observed_at') or updated_at
    return {'tank_id':tank_id,'thing_id':thing_id(tank_id),'name':attrs.get('name',tank_id),'wine_type':attrs.get('wine_type','red'),'stage':ev['stage'],'risk_level':ev['risk_level'],'metrics':metrics,'alarms':ev['alarms'],'recommendation':ev['recommendation'],'updated_at':updated_at}
def list_tanks():
    client=DittoClient(settings.ditto_base_url,settings.ditto_username,settings.ditto_password); things={}
    try:
        for t in client.list_things([thing_id(i) for i in tank_ids()]): things[t.get('thingId')]=t
    except Exception as e: print('ditto unavailable, using fallback',e)
    return [normalize(i,things.get(thing_id(i))) for i in tank_ids()]
def get_tank(tank_id):
    if tank_id not in tank_ids(): return None
    try: thing=DittoClient(settings.ditto_base_url,settings.ditto_username,settings.ditto_password).get_thing(thing_id(tank_id))
    except Exception: thing=None
    return normalize(tank_id,thing)
def get_raw_twin(tank_id):
    short_id=tank_id.split(':')[-1]
    if short_id not in tank_ids(): return None
    try:
        thing=DittoClient(settings.ditto_base_url,settings.ditto_username,settings.ditto_password).get_thing(thing_id(short_id))
        if thing is not None: return thing
    except Exception as e:
        print('ditto raw read failed',tank_id,e)
    return {'thingId':thing_id(short_id),'attributes':default_attrs(short_id),'features':default_features(short_id)}
def overview():
    tanks=list_tanks(); alarms=sum(len(t['alarms']) for t in tanks); avg=sum((t['metrics']['quality_score']['value'] or 0) for t in tanks)/len(tanks)
    return {'winery':{'thing_id':'wine:winery_01','name':'Winery 01'},'workshop':{'thing_id':'wine:workshop_01','name':'Fermentation Workshop 01'},'tank_count':len(tanks),'alarm_count':alarms,'average_quality_score':round(avg,1),'tanks':tanks}
