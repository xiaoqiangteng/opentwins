from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ditto, grafana, health, influxdb, logs, mqtt, trace

app = FastAPI(title="WorldMind Debug Console API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(mqtt.router)
app.include_router(ditto.router)
app.include_router(influxdb.router)
app.include_router(grafana.router)
app.include_router(trace.router)
app.include_router(logs.router)


@app.get("/")
def root():
    return {"service": "worldmind-debug-api", "docs": "/docs", "health": "/api/debug/health"}
