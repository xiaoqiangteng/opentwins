import requests

from app.core.config import settings


def health():
    response = requests.get(f"{settings.modelica_service_url}/health", timeout=settings.modelica_timeout_seconds)
    response.raise_for_status()
    return response.json()


def simulate(payload: dict) -> dict:
    response = requests.post(
        f"{settings.modelica_service_url}/api/modelica/simulate",
        json=payload,
        timeout=settings.modelica_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def what_if(payload: dict) -> dict:
    response = requests.post(
        f"{settings.modelica_service_url}/api/modelica/what-if",
        json=payload,
        timeout=settings.modelica_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()
