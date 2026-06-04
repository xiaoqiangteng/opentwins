from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.schemas.wine import ApiResponse
from app.services import twin_service
from app.services.history_service import history
from app.services.prediction_service import prediction, simulate
app=FastAPI(title='WineTwin Service',version='1.0.0',description='Business API for WineFermentTwin demo on OpenTwins.')
origins=['*'] if settings.cors_allow_origins=='*' else [x.strip() for x in settings.cors_allow_origins.split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
@app.get('/health')
def health(): return {'status':'ok','ditto_base_url':settings.ditto_base_url,'influx_url':settings.influx_url}
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
@app.get('/api/wine/rules',response_model=ApiResponse)
def rules(): return ApiResponse(data=settings.alarm_rules)
