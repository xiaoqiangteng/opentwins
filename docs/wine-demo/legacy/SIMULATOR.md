# Simulator

The simulator is `wine-simulator/wine_fermentation_simulator.py`.

## Run Once

```bash
MQTT_HOST=192.168.49.2 MQTT_PORT=30511 \
python3 wine-simulator/wine_fermentation_simulator.py --config configs/wine_simulation.yaml --once
```

## Continuous Run

```bash
./scripts/run_simulator.sh --opentwins-host-ip 192.168.49.2
```

## Model

- Brix follows exponential decay.
- Progress is sugar-consumption ratio.
- Alcohol increases with progress.
- CO2 follows a peak curve during active fermentation.
- Temperature combines target temperature, fermentation heat, daily cycle, and noise.
- pH drifts slightly with progress.
- Specific gravity is approximated from Brix.
- Quality score subtracts penalties for temperature, pH, stuck fermentation, CO2, and missing data.

## Anomalies

- `temperature_high`: applied to `tank_02` after 40 simulated hours.
- `stuck_fermentation`: applied to `tank_03` after 72 simulated hours.
- Additional supported modes: `ph_abnormal`, `co2_low`, `sensor_missing`, `sensor_spike`.

CSV output is written to `wine-simulator/data/generated_csv/`.
