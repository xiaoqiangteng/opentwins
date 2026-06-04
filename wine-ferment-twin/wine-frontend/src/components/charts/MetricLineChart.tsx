import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

export function MetricLineChart({ metric, points }: { metric: string; points: { timestamp: string; value: number }[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: { left: 42, right: 16, top: 24, bottom: 42 },
      xAxis: { type: 'category', data: points.map((point) => new Date(point.timestamp).toLocaleTimeString()), axisLabel: { hideOverlap: true } },
      yAxis: { type: 'value', scale: true },
      tooltip: { trigger: 'axis' },
      series: [{ name: metric, type: 'line', smooth: true, showSymbol: false, lineStyle: { width: 3, color: '#2f6f62' }, areaStyle: { color: 'rgba(47,111,98,.12)' }, data: points.map((point) => point.value) }],
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => { observer.disconnect(); chart.dispose(); };
  }, [metric, points]);
  return <div className="chart" ref={ref}/>;
}
