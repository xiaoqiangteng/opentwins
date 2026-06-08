import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, AlertTriangle, BarChart3, Boxes, Gauge, PlayCircle, RefreshCw, Play, Pause, RotateCcw } from 'lucide-react';
import { wineApi, Tank, SimulationStatus } from './api/wineApi';
import { WineWorkshopScene } from './components/three/WineWorkshopScene';
import { MetricLineChart } from './components/charts/MetricLineChart';
import { AlarmPanel } from './components/panels/AlarmPanel';
import { RecommendationPanel } from './components/panels/RecommendationPanel';
import { ModelicaSimulationPanel } from './components/panels/ModelicaSimulationPanel';
import './styles.css';

type Tab = 'overview' | 'history' | 'simulation';
const metricNames = ['temperature', 'brix', 'ph', 'co2', 'alcohol_estimation', 'fermentation_progress'];
const metricLabels: Record<string, string> = { temperature: '温度', brix: '糖度', ph: 'pH', co2: 'CO2', alcohol_estimation: '酒精度', fermentation_progress: '发酵进度' };
function riskLabel(level: string) { const m: Record<string, string> = { normal: '正常', warning: '警告', critical: '危险', offline: '离线', finished: '已完成' }; return m[level] || level; }

function Metric({ label, tank, name }: { label: string; tank: Tank; name: string }) {
  const metric = tank.metrics[name];
  return <div className="metric"><span>{label}</span><b>{metric?.value ?? '--'} <small>{metric?.unit}</small></b></div>;
}

/* ── 仿真进度条 ──────────────────────────────────────────────────────── */
function SimulationProgressBar({ status }: { status: SimulationStatus | null }) {
  if (!status) return null;
  const pct = Math.min(100, Math.max(0, status.progress_pct));
  let colorClass = 'progInitial';
  if (pct >= 98) colorClass = 'progFinished';
  else if (pct >= 80) colorClass = 'progLate';
  else if (pct >= 10) colorClass = 'progActive';

  return <div className="simProgressBar">
    <div className="simProgressTrack">
      <div className={`simProgressFill ${colorClass}`} style={{ width: `${pct}%` }} />
    </div>
    <span className="simProgressLabel">
      {pct.toFixed(0)}% &nbsp;({status.elapsed_hours.toFixed(0)}h / {status.total_hours.toFixed(0)}h)
      &nbsp;·&nbsp;{status.stage}
    </span>
  </div>;
}

/* ── 主应用 ───────────────────────────────────────────────────────────── */
function App() {
  const [tab, setTab] = useState<Tab>('overview');
  const [tanks, setTanks] = useState<Tank[]>([]);
  const [selected, setSelected] = useState('tank_01');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [simStatus, setSimStatus] = useState<SimulationStatus | null>(null);
  const [simBusy, setSimBusy] = useState(false);
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

  /* 加载仿真状态 */
  const loadSimStatus = useCallback(async () => {
    try {
      const s = await wineApi.simulationStatus();
      setSimStatus(s);
    } catch { /* standalone mode — ignore */ }
  }, []);

  useEffect(() => {
    load();
    loadSimStatus();
    const timer = setInterval(load, 5000);
    const simTimer = setInterval(loadSimStatus, 2000);
    return () => { clearInterval(timer); clearInterval(simTimer); };
  }, [loadSimStatus]);

  /* 仿真控制 */
  async function simAction(fn: () => Promise<any>, delay = 0) {
    setSimBusy(true);
    try {
      await fn();
      if (delay > 0) await new Promise(r => setTimeout(r, delay));
      await loadSimStatus();
      await load();
    } catch (err: any) {
      setError(err.message || '仿真控制失败');
    } finally {
      setSimBusy(false);
    }
  }

  const isRunning = simStatus?.running ?? false;
  const isEmbedded = simStatus?.mode !== 'standalone';

  return <main className="app">
    <header className="topbar">
      <div className="brand"><Boxes size={22}/><div><strong>葡萄酒发酵数字孪生</strong><span>{wineApi.base}</span></div></div>
      <nav>
        <button className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}><Gauge size={16}/>总览</button>
        <button className={tab === 'history' ? 'active' : ''} onClick={() => setTab('history')}><BarChart3 size={16}/>历史</button>
        <button className={tab === 'simulation' ? 'active' : ''} onClick={() => setTab('simulation')}><PlayCircle size={16}/>仿真</button>
      </nav>
      <div className="simControls">
        {isEmbedded && <>
          <button disabled={simBusy || isRunning} onClick={() => simAction(wineApi.simulationStart)} title="开始仿真">
            <Play size={16}/>{simBusy ? '…' : '开始'}
          </button>
          <button disabled={simBusy || !isRunning} onClick={() => simAction(wineApi.simulationPause)} title="暂停仿真">
            <Pause size={16}/>{simBusy ? '…' : '暂停'}
          </button>
          <button className="resetBtn" disabled={simBusy} onClick={() => simAction(wineApi.simulationReset, 1500)} title="重置仿真">
            <RotateCcw size={16}/>{simBusy ? '…' : '重置'}
          </button>
        </>}
      </div>
      <button className="icon" onClick={load} title="刷新"><RefreshCw size={18} className={loading ? 'spin' : ''}/></button>
    </header>
    {isEmbedded && <SimulationProgressBar status={simStatus} />}
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
  useEffect(() => {
    let cancelled = false;
    wineApi.history(tank.tank_id, metric)
      .then((res) => { if (!cancelled) setData(res.points || []); })
      .catch(() => { if (!cancelled) setData([]); });
    return () => { cancelled = true; };
  }, [tank.tank_id, metric]);
  return <section className="band">
    <div className="tabs">{metricNames.map((name) => <button className={metric === name ? 'active' : ''} onClick={() => setMetric(name)} key={name}>{metricLabels[name] || name}</button>)}</div>
    <MetricLineChart metric={metric} points={data}/>
  </section>;
}

function Simulation({ tank }: { tank: Tank }) {
  const [prediction, setPrediction] = useState<any>();
  const [delta, setDelta] = useState(0);
  const [simulation, setSimulation] = useState<any>();
  useEffect(() => { wineApi.prediction(tank.tank_id).then(setPrediction); }, [tank.tank_id]);
  async function run() { setSimulation(await wineApi.simulate(tank.tank_id, { temperature_delta: delta, nutrient_boost: 1 })); }
  return <section className="band simulationStack"><div className="two"><div><h2>经验公式 24小时预测</h2><p>预计完成时间: {prediction?.estimated_completion_time || '--'}</p><MetricLineChart metric="future_progress" points={prediction?.future_progress || []}/></div><div className="controlPanel"><h2>原规则参数扰动</h2><label>温度偏移量 <input type="range" min="-5" max="5" value={delta} onChange={(event) => setDelta(Number(event.target.value))}/><b>{delta} C</b></label><button onClick={run}><Activity size={16}/>运行仿真</button>{simulation && <p className="result">质量变化量: {simulation.projected_quality_delta}。 {simulation.recommendation}</p>}</div></div><ModelicaSimulationPanel tank={tank}/></section>;
}

createRoot(document.getElementById('root')!).render(<App/>);
