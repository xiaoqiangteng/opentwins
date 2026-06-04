# Test Report

Date: 2026-06-04

## Environment

- Server project path: `/home/teng/programmings/git/opentwins/wine-ferment-twin`
- Python: 3.8.10
- Node: 20.20.2
- npm: 11.14.1
- OpenTwins NodePort IP: `192.168.49.2`
- Demo host IP: `10.168.1.102`

## Passed

- OpenTwins services:
  - Ditto API `192.168.49.2:30525`: OK with Basic Auth.
  - InfluxDB `192.168.49.2:30716`: OK.
  - Grafana `192.168.49.2:30718`: OK.
  - Mosquitto `192.168.49.2:30511`: OK.
- Twin initialization:
  - `wine:winery_01`: created and verified.
  - `wine:workshop_01`: created and verified.
  - `wine:tank_01`, `wine:tank_02`, `wine:tank_03`: created and verified with required Features.
- MQTT to Ditto:
  - Simulator publishes to `telemetry/wine/<tank_id>`.
  - Ditto Features update with fresh `observed_at`.
- Frontend:
  - `npm run build`: passed.
  - Vite dev server listens on `0.0.0.0:5173`.
  - `http://10.168.1.102:5173/`: returns Vite React page.
- Backend:
  - WineTwin Service listens on `0.0.0.0:8010`.
  - `/health`: 200.
  - `/api/wine/tanks`: 200.
  - `/api/wine/tanks/{id}/history`: 200, verified against real InfluxDB `mqtt_consumer` time-series rows.
  - `/api/wine/tanks/{id}/alarms`: 200.
  - `/api/wine/tanks/{id}/prediction`: 200.
  - `/api/wine/tanks/{id}/simulate`: 200.

## Current Runtime Snapshot

Example backend output after simulator runs:

```text
tank_01 normal
tank_02 critical Activate cooling immediately and inspect tank.
tank_03 normal
```

## Known Limitations

- Extended API root returns 404 on this deployment; Type registration is skipped, but Ditto Twin creation/update works through Ditto REST API.
- `deploy_demo.sh` reads the InfluxDB token from the existing OpenTwins `values.yaml` when `INFLUX_TOKEN` is not supplied.
- Browser visual screenshot verification was not completed because the in-app Browser was unavailable and neither local nor server Chrome/Chromium/Playwright/Puppeteer was installed. Build, HTTP, API, and WebGL source integration were verified.
