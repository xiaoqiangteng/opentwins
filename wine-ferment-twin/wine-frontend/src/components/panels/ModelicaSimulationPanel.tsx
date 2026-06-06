import { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { Activity, Cpu, Thermometer } from 'lucide-react';
import { ModelicaResult, Tank, wineApi } from '../../api/wineApi';

const riskLabels: Record<string, string> = { normal: '正常', warning: '警告', critical: '危险', finished: '已完成', offline: '离线' };

function Completion({ value }: { value?: number | null }) {
  if (value == null) return <span>超过当前预测窗口</span>;
  return <span>{value.toFixed(1)} 小时</span>;
}

function ModelicaChart({ baseline, whatIf }: { baseline?: ModelicaResult; whatIf?: ModelicaResult }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !baseline?.points?.length) return;
    const chart = echarts.init(ref.current);
    const hours = baseline.points.map((point) => `${point.hour}h`);
    chart.setOption({
      grid: { left: 46, right: 18, top: 34, bottom: 42 },
      legend: { top: 4 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: hours, axisLabel: { hideOverlap: true } },
      yAxis: { type: 'value', scale: true },
      series: [
        { name: 'Brix 基线', type: 'line', smooth: true, showSymbol: false, data: baseline.points.map((point) => point.brix), lineStyle: { width: 3, color: '#23614f' } },
        { name: 'Alcohol 基线', type: 'line', smooth: true, showSymbol: false, data: baseline.points.map((point) => point.alcohol), lineStyle: { width: 3, color: '#7a4f9d' } },
        { name: 'Progress 基线', type: 'line', smooth: true, showSymbol: false, data: baseline.points.map((point) => point.progress), lineStyle: { width: 3, color: '#2d6fb7' } },
        { name: 'Quality 基线', type: 'line', smooth: true, showSymbol: false, data: baseline.points.map((point) => point.quality_score), lineStyle: { width: 3, color: '#b36a00' } },
        ...(whatIf?.points?.length ? [{
          name: 'Quality what-if',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: whatIf.points.map((point) => point.quality_score),
          lineStyle: { width: 3, type: 'dashed', color: '#c62828' },
        }] : []),
      ],
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => { observer.disconnect(); chart.dispose(); };
  }, [baseline, whatIf]);
  return <div className="chart modelicaChart" ref={ref}/>;
}

export function ModelicaSimulationPanel({ tank }: { tank: Tank }) {
  const [health, setHealth] = useState<any>();
  const [baseline, setBaseline] = useState<ModelicaResult>();
  const [whatIf, setWhatIf] = useState<ModelicaResult>();
  const [delta, setDelta] = useState(-5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function loadBaseline() {
    setLoading(true);
    try {
      const [serviceHealth, prediction] = await Promise.all([
        wineApi.modelicaHealth(),
        wineApi.modelicaPrediction(tank.tank_id, 24),
      ]);
      setHealth(serviceHealth);
      setBaseline(prediction);
      setWhatIf(undefined);
      setError('');
    } catch (err: any) {
      setError(err.message || 'OpenModelica service unavailable');
    } finally {
      setLoading(false);
    }
  }

  async function runWhatIf() {
    setLoading(true);
    try {
      setWhatIf(await wineApi.modelicaSimulate(tank.tank_id, { temperature_delta: delta, nutrient_boost: 0, horizon_hours: 24 }));
      setError('');
    } catch (err: any) {
      setError(err.message || 'OpenModelica what-if failed');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadBaseline(); }, [tank.tank_id]);

  const qualityDelta = baseline && whatIf ? whatIf.quality_score_end - baseline.quality_score_end : undefined;

  return <section className="modelicaPanel">
    <div className="modelicaHeader">
      <h2><Cpu size={16}/>OpenModelica 机理仿真</h2>
      <button onClick={loadBaseline} disabled={loading}><Activity size={16}/>{loading ? '运行中' : '刷新基线'}</button>
    </div>
    {error && <p className="modelicaError">{error}</p>}
    <div className="modelicaStats">
      <div><span>模型状态</span><b>{health?.status === 'ok' ? '可用' : '未知'}</b></div>
      <div><span>风险等级</span><b className={`risk ${baseline?.risk_level || 'normal'}`}>{riskLabels[baseline?.risk_level || 'normal'] || baseline?.risk_level}</b></div>
      <div><span>预计完成</span><b><Completion value={baseline?.estimated_completion_hours}/></b></div>
      <div><span>末端质量分</span><b>{baseline?.quality_score_end?.toFixed(1) ?? '--'}</b></div>
    </div>
    <ModelicaChart baseline={baseline} whatIf={whatIf}/>
    <div className="whatIfBar">
      <label><Thermometer size={16}/>温度扰动
        <input type="range" min="-5" max="5" value={delta} onChange={(event) => setDelta(Number(event.target.value))}/>
        <b>{delta > 0 ? '+' : ''}{delta} C</b>
      </label>
      <button onClick={runWhatIf} disabled={loading}><Activity size={16}/>运行 OpenModelica What-if</button>
    </div>
    {whatIf && <p className="result">what-if 末端质量分 {whatIf.quality_score_end.toFixed(1)}，相对基线 {qualityDelta! >= 0 ? '+' : ''}{qualityDelta!.toFixed(1)}；风险等级 {riskLabels[whatIf.risk_level] || whatIf.risk_level}。</p>}
  </section>;
}
