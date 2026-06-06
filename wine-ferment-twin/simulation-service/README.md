# OpenModelica Simulation Service

FastAPI service for running the WineFermentTwin Modelica continuation model.

Endpoints:

- `GET /health`
- `POST /api/modelica/demo`
- `POST /api/modelica/simulate`
- `POST /api/modelica/what-if`

The service is designed to run inside the `openmodelica/openmodelica` Docker image so `omc` is available in `PATH`.
