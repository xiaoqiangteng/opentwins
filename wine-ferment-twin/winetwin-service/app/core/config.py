import os
from pathlib import Path
import yaml
BASE_DIR = Path(__file__).resolve().parents[3]
CONFIG_DIR = BASE_DIR / 'configs'
def _load_yaml(name, default):
    p=CONFIG_DIR/name
    if not p.exists(): return default
    with p.open(encoding='utf-8') as f: return yaml.safe_load(f) or default
class Settings:
    host=os.getenv('WINE_SERVICE_HOST','0.0.0.0')
    port=int(os.getenv('WINE_SERVICE_PORT','8010'))
    ditto_base_url=os.getenv('DITTO_BASE_URL','http://127.0.0.1:30525').rstrip('/')
    ditto_username=os.getenv('DITTO_USERNAME','ditto')
    ditto_password=os.getenv('DITTO_PASSWORD','ditto')
    extended_api_url=os.getenv('EXTENDED_API_URL','http://127.0.0.1:30526').rstrip('/')
    influx_url=os.getenv('INFLUX_URL','http://127.0.0.1:30716').rstrip('/')
    influx_token=os.getenv('INFLUX_TOKEN','')
    influx_org=os.getenv('INFLUX_ORG','opentwins')
    influx_bucket=os.getenv('INFLUX_BUCKET','opentwins')
    mongo_uri=os.getenv('MONGO_URI','mongodb://127.0.0.1:30717')
    cors_allow_origins=os.getenv('CORS_ALLOW_ORIGINS','*')
    use_modelica=os.getenv('USE_MODELICA','true').lower() in ('1','true','yes','on')
    modelica_service_url=os.getenv('MODELICA_SERVICE_URL','http://127.0.0.1:8020').rstrip('/')
    modelica_timeout_seconds=int(os.getenv('MODELICA_TIMEOUT_SECONDS','30'))
    model_default_horizon_hours=int(os.getenv('MODEL_DEFAULT_HORIZON_HOURS','24'))
    alarm_rules=_load_yaml('alarm_rules.yaml',{})
    sim_config=_load_yaml('wine_simulation.yaml',{})
    simulation_mode=os.getenv('SIMULATION_MODE','embedded').lower() in ('1','true','yes','on','embedded')
    mqtt_host=os.getenv('MQTT_HOST','')
    mqtt_port=int(os.getenv('MQTT_PORT','0')) or None
    simulator_config_path=os.getenv('SIMULATOR_CONFIG_PATH',str(BASE_DIR/'configs'/'wine_simulation.yaml'))
settings=Settings()
