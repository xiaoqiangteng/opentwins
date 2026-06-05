import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, AlertTriangle, BarChart3, Boxes, Gauge, PlayCircle, RefreshCw } from 'lucide-react';
import { wineApi, Tank } from './api/wineApi';
import { WineWorkshopScene } from './components/three/WineWorkshopScene';
import { MetricLineChart } from './components/charts/MetricLineChart';
import { AlarmPanel } from './components/panels/AlarmPanel';
import { RecommendationPanel } from './components/panels/RecommendationPanel';
import './styles.css';

type Tab = 'overview' | 'history' | 'simulation';
const metricNames = ['temperature', 'brix', 'ph', 'co2', 'alcohol_estimation', 'fermentation_progress'];
const metricLabels: Record<string, string> = { temperature: '温度', brix: '糖度', ph: 'pH', co2: 'CO2', alcohol_estimation: '酒精度', fermentation_progress: '发酵进度' };
function riskLabel(level: string) { const m: Record<string, string> = { normal: '正常', warning: '警告', critical: '危险', offline: '离线', finished: '已完成' }; return m[level] || level; }

function Metric({ label, tank, name }: { label: string; tank: Tank; name: string }) {
  const metric = tank.metrics[name];
  return <div className="metric"><span>{label}</span><b>{metric?.value ?? '--'} <small>{metric?.unit}</small></b></div>;
}

function App() {
  const [tab, setTab] = useState<Tab>('overview');
  const [tanks, setTanks] = useState<Tank[]>([]);
  const [selected, setSelected] = useState('tank_01');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const tank = useMemo(() => tanks.find((item) => item.tank_id === selected) || tanks[0], [tanks, selected]);

  async function load() {
    setLoading(true);
    try {
      const data = await wineApi.tanks();
      setTanks(data);
      setError('');
      if (data.length && !data.some((item) => item.tank_id === selected)) setSelected(data[0].tank_id);
    } catch (err: any) {
      setError(err.message || 'API connection failed');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, []);

  return <main className="app">
    <header className="topbar">
      <div className="brand"><Boxes size={22}/><div><strong>葡萄酒发酵数字孪生</strong><span>{wineApi.base}</span></div></div>
      <nav>
        <button className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}><Gauge size={16}/>总览</button>
        <button className={tab === 'history' ? 'active' : ''} onClick={() => setTab('history')}><BarChart3 size={16}/>历史</button>
        <button className={tab === 'simulation' ? 'active' : ''} onClick={() => setTab('simulation')}><PlayCircle size={16}/>仿真</button>
      </nav>
      <button className="icon" onClick={load} title="刷新"><RefreshCw size={18} className={loading ? 'spin' : ''}/></button>
    </header>
    {error && <div className="error"><AlertTriangle size={16}/>{error}</div>}
    <section className="workspace">
      <div className="scenePane"><WineWorkshopScene tanks={tanks} selected={selected} onSelect={setSelected}/></div>
      <aside className="sidePane">{tank && <>
        <div className="tankHead"><div><span>{tank.thing_id}</span><h1>{tank.name}</h1></div><b className={`risk ${tank.risk_level}`}>{riskLabel(tank.risk_level)}</b></div>
        <div className="metrics">
          <Metric label="温度" tank={tank} name="temperature"/><Metric label="糖度" tank={tank} name="brix"/>
          <Metric label="pH" tank={tank} name="ph"/><Metric label="CO2" tank={tank} name="co2"/>
          <Metric label="酒精度" tank={tank} name="alcohol_estimation"/><Metric label="进度" tank={tank} name="fermentation_progress"/>
        </div>
        <RecommendationPanel tank={tank}/><AlarmPanel alarms={tank.alarms}/>
      </>}</aside>
    </section>
    {tab === 'history' && tank && <History tank={tank}/>} {tab === 'simulation' && tank && <Simulation tank={tank}/>} 
    <footer>OpenTwins 数字孪生状态每5秒自动刷新。当前选中: {selected}</footer>
  </main>;
}

function History({ tank }: { tank: Tank }) {
  const [metric, setMetric] = useState('brix');
  const [data, setData] = useState<any[]>([]);
  useEffect(() => { wineApi.history(tank.tank_id, metric).then((res) => setData(res.points || [])).catch(() => setData([])); }, [tank.tank_id, metric]);
  return <section className="band"><div className="tabs">{metricNames.map((name) => <button className={metric === name ? 'active' : ''} onClick={() => setMetric(name)} key={name}>{metricLabels[name] || name}</button>)}</div><MetricLineChart metric={metric} points={data}/></section>;
}

function Simulation({ tank }: { tank: Tank }) {
  const [prediction, setPrediction] = useState<any>();
  const [delta, setDelta] = useState(0);
  const [simulation, setSimulation] = useState<any>();
  useEffect(() => { wineApi.prediction(tank.tank_id).then(setPrediction); }, [tank.tank_id]);
  async function run() { setSimulation(await wineApi.simulate(tank.tank_id, { temperature_delta: delta, nutrient_boost: 1 })); }
  return <section className="band two"><div><h2>24小时预测</h2><p>预计完成时间: {prediction?.estimated_completion_time || '--'}</p><MetricLineChart metric="future_progress" points={prediction?.future_progress || []}/></div><div className="controlPanel"><h2>参数扰动</h2><label>温度偏移量 <input type="range" min="-5" max="5" value={delta} onChange={(event) => setDelta(Number(event.target.value))}/><b>{delta} C</b></label><button onClick={run}><Activity size={16}/>运行仿真</button>{simulation && <p className="result">质量变化量: {simulation.projected_quality_delta}。 {simulation.recommendation}</p>}</div></section>;
}

createRoot(document.getElementById('root')!).render(<App/>);
