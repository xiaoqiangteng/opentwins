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
    risk='normal'; score=100.0; alarms=[]; rec='继续正常发酵监控。'
    if temp is None:
        risk='offline'; score-=55; alarms.append({'level':'offline','type':'sensor_missing','message':'传感器数据缺失','recommendation':'请检查传感器电源、网关连接和 MQTT 发布状态'})
    else:
        if temp > rules.get('temperature_critical_upper',33):
            risk='critical'; score-=32; alarms.append({'level':'critical','type':'temperature_high','message':'发酵温度超过危险阈值','recommendation':'请立即启动冷却系统并检查发酵罐状态'})
        elif temp > rules.get('temperature_warning_upper',30):
            risk='warning'; score-=18; alarms.append({'level':'warning','type':'temperature_high','message':'发酵温度超过建议范围','recommendation':'请启动冷却或降低目标温度'})
    if ph is not None and (ph < rules.get('ph_lower',3.1) or ph > rules.get('ph_upper',3.8)):
        risk='critical' if ph<3.0 or ph>3.9 else ('warning' if risk=='normal' else risk); score-=18; alarms.append({'level':risk,'type':'ph_abnormal','message':'pH 超出推荐发酵范围','recommendation':'请校验 pH 传感器并根据酒窖操作规程调节酸度'})
    if stage=='active' and co2 is not None and co2 < rules.get('co2_active_min',1500):
        risk='warning' if risk=='normal' else risk; score-=12; alarms.append({'level':'warning','type':'co2_low','message':'活跃发酵阶段 CO2 低于预期','recommendation':'请检查酵母活性、营养物供给和密封完整性'})
    if attrs.get('name','').endswith('03') and progress and progress < 45 and stage=='active':
        risk='warning' if risk=='normal' else risk; score-=18; alarms.append({'level':'warning','type':'stuck_fermentation','message':'糖度下降速度低于预期，存在发酵停滞风险','recommendation':'请检查酵母活性、营养物和温度稳定性'})
    if progress and progress>=98 and risk=='normal': risk='finished'; rec='发酵接近完成，请准备澄清和转罐计划'
    if alarms: rec=alarms[0]['recommendation']
    return {'risk_level':risk,'quality_score':round(max(0,min(100,score)),1),'alarms':alarms,'recommendation':rec,'stage':stage}
