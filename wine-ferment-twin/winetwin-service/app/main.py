import requests
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.schemas.wine import ApiResponse
from app.services import twin_service
from app.services.history_service import history
from app.services.prediction_service import prediction, simulate
from app.services import modelica_prediction_service
from app.clients import modelica_client

app=FastAPI(title='WineTwin Service',version='1.0.0',description='Business API for WineFermentTwin demo on OpenTwins.')
origins=['*'] if settings.cors_allow_origins=='*' else [x.strip() for x in settings.cors_allow_origins.split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

# ── 仿真引擎（嵌入式模式）─────────────────────────────────────────────────
_engine=None
def _get_engine():
    global _engine
    if _engine is None and settings.simulation_mode:
        from app.services.simulation_engine import engine
        _engine=engine
    return _engine
@app.get('/health')
def health(): return {'status':'ok','ditto_base_url':settings.ditto_base_url,'influx_url':settings.influx_url,'use_modelica':settings.use_modelica,'modelica_service_url':settings.modelica_service_url}
@app.post('/api/wine/init',response_model=ApiResponse)
def init(): return ApiResponse(data={'message':'Run scripts/init_wine_twins.sh for full idempotent initialization.'})
@app.get('/api/wine/overview',response_model=ApiResponse)
def overview(): return ApiResponse(data=twin_service.overview())
@app.get('/api/wine/tanks',response_model=ApiResponse)
def tanks(): return ApiResponse(data=twin_service.list_tanks())
@app.get('/api/wine/tanks/{tank_id}',response_model=ApiResponse)
def tank(tank_id:str):
    t=twin_service.get_tank(tank_id)
    if not t: raise HTTPException(404,'tank not found')
    return ApiResponse(data=t)
@app.get('/api/wine/tanks/{tank_id}/history',response_model=ApiResponse)
def tank_history(tank_id:str, metric:str=Query('brix'), hours:int=Query(48,ge=1,le=720)): return ApiResponse(data=history(tank_id,metric,hours))
@app.get('/api/wine/tanks/{tank_id}/alarms',response_model=ApiResponse)
def alarms(tank_id:str):
    t=twin_service.get_tank(tank_id)
    if not t: raise HTTPException(404,'tank not found')
    return ApiResponse(data={'tank_id':tank_id,'alarms':t['alarms']})
@app.get('/api/wine/tanks/{tank_id}/prediction',response_model=ApiResponse)
def pred(tank_id:str): return ApiResponse(data=prediction(tank_id))
@app.post('/api/wine/tanks/{tank_id}/simulate',response_model=ApiResponse)
def sim(tank_id:str, payload:dict=Body(default={})): return ApiResponse(data=simulate(tank_id,payload))
@app.get('/api/wine/modelica/health')
def modelica_health():
    try:
        return modelica_client.health()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f'Modelica service unavailable: {e}')
@app.get('/api/wine/tanks/{tank_id}/modelica-prediction')
def tank_modelica_prediction(tank_id:str, horizon:int=Query(24,ge=1,le=240)):
    if not settings.use_modelica:
        raise HTTPException(status_code=503, detail='OpenModelica integration is disabled')
    twin_id=tank_id if ':' in tank_id else f'wine:{tank_id}'
    twin=twin_service.get_raw_twin(twin_id)
    if not twin: raise HTTPException(404,'tank not found')
    try:
        return modelica_prediction_service.modelica_prediction(twin_id,twin,horizon)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f'Modelica simulation failed: {e}')
@app.post('/api/wine/tanks/{tank_id}/modelica-simulate')
def tank_modelica_simulate(tank_id:str, body:dict=Body(default={})):
    if not settings.use_modelica:
        raise HTTPException(status_code=503, detail='OpenModelica integration is disabled')
    twin_id=tank_id if ':' in tank_id else f'wine:{tank_id}'
    twin=twin_service.get_raw_twin(twin_id)
    if not twin: raise HTTPException(404,'tank not found')
    try:
        return modelica_prediction_service.modelica_what_if(twin_id,twin,body)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f'Modelica what-if failed: {e}')
@app.get('/api/wine/rules',response_model=ApiResponse)
def rules(): return ApiResponse(data=settings.alarm_rules)

# ── 仿真控制 API ──────────────────────────────────────────────────────────
@app.get('/api/wine/simulation/status')
def simulation_status():
    eng=_get_engine()
    if eng is None: return {'mode':'standalone','elapsed_hours':0,'total_hours':288,'progress_pct':0,'running':False,'stage':'独立进程模式'}
    return eng.status()

@app.post('/api/wine/simulation/start')
def simulation_start():
    eng=_get_engine()
    if eng is None: raise HTTPException(503,'仿真引擎未启动（当前为独立进程模式）')
    return eng.start()

@app.post('/api/wine/simulation/pause')
def simulation_pause():
    eng=_get_engine()
    if eng is None: raise HTTPException(503,'仿真引擎未启动（当前为独立进程模式）')
    return eng.pause()

@app.post('/api/wine/simulation/reset')
def simulation_reset():
    eng=_get_engine()
    if eng is None: raise HTTPException(503,'仿真引擎未启动（当前为独立进程模式）')
    return eng.reset()
