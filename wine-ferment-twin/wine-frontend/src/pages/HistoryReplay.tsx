import { useEffect, useState } from 'react';
import { Tank, wineApi } from '../api/wineApi';
import { MetricLineChart } from '../components/charts/MetricLineChart';

const metricNames = ['temperature', 'brix', 'ph', 'co2', 'alcohol_estimation', 'fermentation_progress'];

export default function HistoryReplay({ tank }: { tank: Tank }) {
  const [metric, setMetric] = useState('brix');
  const [data, setData] = useState<any[]>([]);
  useEffect(() => {
    wineApi.history(tank.tank_id, metric).then((res) => setData(res.points || [])).catch(() => setData([]));
  }, [tank.tank_id, metric]);
  return <section className="band"><div className="tabs">{metricNames.map((name) => <button className={metric === name ? 'active' : ''} onClick={() => setMetric(name)} key={name}>{name}</button>)}</div><MetricLineChart metric={metric} points={data}/></section>;
}

