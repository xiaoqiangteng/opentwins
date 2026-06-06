ARG OPENMODELICA_IMAGE=openmodelica/openmodelica:v1.26.7-minimal
FROM ${OPENMODELICA_IMAGE}

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY simulation-service/requirements.txt /app/requirements.txt
RUN python3 -m pip install --break-system-packages -r /app/requirements.txt \
    || python3 -m pip install -r /app/requirements.txt

COPY simulation-service/app /app/app
COPY modelica /app/modelica

RUN mkdir -p /app/runtime/results /app/runtime/mos

EXPOSE 8020
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]
