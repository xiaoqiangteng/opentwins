import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import { Tank, wineApi } from '../api/wineApi';
import { MetricLineChart } from '../components/charts/MetricLineChart';

export default function SimulationPanel({ tank }: { tank: Tank }) {
  const [prediction, setPrediction] = useState<any>();
  const [delta, setDelta] = useState(0);
  const [simulation, setSimulation] = useState<any>();
  useEffect(() => { wineApi.prediction(tank.tank_id).then(setPrediction); }, [tank.tank_id]);
  async function run() { setSimulation(await wineApi.simulate(tank.tank_id, { temperature_delta: delta, nutrient_boost: 1 })); }
  return <section className="band two"><div><h2>24h Prediction</h2><p>Estimated completion: {prediction?.estimated_completion_time || '--'}</p><MetricLineChart metric="future_progress" points={prediction?.future_progress || []}/></div><div className="controlPanel"><h2>Parameter Perturbation</h2><label>Temperature delta <input type="range" min="-5" max="5" value={delta} onChange={(event) => setDelta(Number(event.target.value))}/><b>{delta} C</b></label><button onClick={run}><Activity size={16}/>Run Simulation</button>{simulation && <p className="result">Quality delta: {simulation.projected_quality_delta}. {simulation.recommendation}</p>}</div></section>;
}

