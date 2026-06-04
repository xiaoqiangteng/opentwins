# Deployment

## Current Server

- Project path: `/home/teng/programmings/git/opentwins/wine-ferment-twin`
- Demo host IP: `10.168.1.102`
- OpenTwins NodePort IP: `192.168.49.2`

## Start

```bash
cd /home/teng/programmings/git/opentwins/wine-ferment-twin
./scripts/deploy_demo.sh --host-ip 10.168.1.102 --opentwins-host-ip 192.168.49.2
```

The script checks OpenTwins, installs Python dependencies, initializes Wine Twin objects, starts WineTwin Service, starts the Vite frontend, and starts the simulator.

## URLs

- Frontend: `http://10.168.1.102:5173`
- WineTwin API docs: `http://10.168.1.102:8010/docs`
- Health: `http://10.168.1.102:8010/health`
- Grafana/OpenTwins: `http://192.168.49.2:30718`
- Ditto API: `http://192.168.49.2:30525`
- InfluxDB: `http://192.168.49.2:30716`
- Mosquitto MQTT: `192.168.49.2:30511`

## Stop

```bash
cd /home/teng/programmings/git/opentwins/wine-ferment-twin
./scripts/stop_demo.sh
```

## Notes

The current server lacks `python3.8-venv`, so `deploy_demo.sh` falls back to `python3 -m pip install --user`. Backend and simulator are started with `setsid -f` so they survive SSH session exit.

If another machine cannot open the frontend, open firewall/security-group ports `5173`, `8010`, `30718`, `30525`, `30526`, `30511`, and `30716`.
