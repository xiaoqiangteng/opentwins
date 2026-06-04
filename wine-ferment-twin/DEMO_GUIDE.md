# Demo Guide

1. Start the demo:

   ```bash
   ./scripts/deploy_demo.sh --host-ip 10.168.1.102 --opentwins-host-ip 192.168.49.2
   ```

2. Open `http://10.168.1.102:5173`.

3. Show the ThreeJS workshop scene with three fermentation tanks.

4. Explain colors:
   - `normal`: green
   - `warning`: yellow
   - `critical`: red
   - `offline`: gray
   - `finished`: blue

5. Click `tank_01` to show normal fermentation metrics.

6. Click `tank_02`; after the accelerated simulator passes about 40 simulated hours, it triggers high-temperature warning/critical alarms and cooling recommendations.

7. Click `tank_03`; after the simulator passes about 72 simulated hours, it demonstrates stuck-fermentation risk.

8. Open the History tab to view Brix, Alcohol, Temperature, pH, and CO2 trend curves.

9. Open the Simulation tab to view completion prediction and parameter perturbation output.

10. Open `http://10.168.1.102:8010/docs` to show REST APIs.

11. Open Grafana/OpenTwins at `http://192.168.49.2:30718` to show `wine:winery_01`, `wine:workshop_01`, and `wine:tank_01..03`.
