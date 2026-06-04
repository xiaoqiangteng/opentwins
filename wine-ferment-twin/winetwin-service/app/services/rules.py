def rule_key(wine_type): return 'white_wine' if wine_type=='white' else 'red_wine'
def metric(features, name, default=None):
    try: return features[name]['properties'].get('value', default)
    except Exception: return default
def unit(features, name, default=''):
    try: return features[name]['properties'].get('unit', default)
    except Exception: return default
def stage_from_progress(progress):
    p=(progress or 0)/100.0
    if p<0.10: return 'initial'
    if p<0.80: return 'active'
    if p<0.98: return 'late'
    return 'finished'
def evaluate(attrs, features, alarm_rules):
    wine_type=attrs.get('wine_type','red'); rules=alarm_rules.get(rule_key(wine_type),{})
    temp=metric(features,'temperature'); ph=metric(features,'ph'); co2=metric(features,'co2'); progress=metric(features,'fermentation_progress',0)
    stage=metric(features,'fermentation_stage') or stage_from_progress(progress)
    risk='normal'; score=100.0; alarms=[]; rec='Continue normal fermentation monitoring.'
    if temp is None:
        risk='offline'; score-=55; alarms.append({'level':'offline','type':'sensor_missing','message':'Sensor data is missing.','recommendation':'Check sensor power, gateway and MQTT publishing.'})
    else:
        if temp > rules.get('temperature_critical_upper',33):
            risk='critical'; score-=32; alarms.append({'level':'critical','type':'temperature_high','message':'Fermentation temperature is above critical range.','recommendation':'Activate cooling immediately and inspect tank.'})
        elif temp > rules.get('temperature_warning_upper',30):
            risk='warning'; score-=18; alarms.append({'level':'warning','type':'temperature_high','message':'Fermentation temperature is above recommended range.','recommendation':'Activate cooling or reduce target temperature.'})
    if ph is not None and (ph < rules.get('ph_lower',3.1) or ph > rules.get('ph_upper',3.8)):
        risk='critical' if ph<3.0 or ph>3.9 else ('warning' if risk=='normal' else risk); score-=18; alarms.append({'level':risk,'type':'ph_abnormal','message':'pH is outside the recommended fermentation range.','recommendation':'Verify pH sensor and adjust acidity according to cellar SOP.'})
    if stage=='active' and co2 is not None and co2 < rules.get('co2_active_min',1500):
        risk='warning' if risk=='normal' else risk; score-=12; alarms.append({'level':'warning','type':'co2_low','message':'CO2 is lower than expected in active fermentation.','recommendation':'Check yeast activity, nutrients and seal integrity.'})
    if attrs.get('name','').endswith('03') and progress and progress < 45 and stage=='active':
        risk='warning' if risk=='normal' else risk; score-=18; alarms.append({'level':'warning','type':'stuck_fermentation','message':'Brix decline is slower than expected; stuck fermentation risk detected.','recommendation':'Check yeast viability, nutrients and temperature stability.'})
    if progress and progress>=98 and risk=='normal': risk='finished'; rec='Fermentation is near completion; prepare clarification and transfer plan.'
    if alarms: rec=alarms[0]['recommendation']
    return {'risk_level':risk,'quality_score':round(max(0,min(100,score)),1),'alarms':alarms,'recommendation':rec,'stage':stage}
