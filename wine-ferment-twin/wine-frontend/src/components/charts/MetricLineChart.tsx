import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

export function MetricLineChart({ metric, points }: { metric: string; points: { timestamp: string; value: number }[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;

    // 复用或初始化图表实例，避免切换时销毁重建导致闪烁
    if (!chartRef.current || chartRef.current.isDisposed()) {
      chartRef.current = echarts.init(ref.current);
    }
    const chart = chartRef.current;

    // 数据为空时显示空坐标轴
    const hasData = points && points.length > 0;
    const xData = hasData ? points.map((point) => new Date(point.timestamp).toLocaleTimeString()) : [];
    const yData = hasData ? points.map((point) => point.value) : [];

    chart.setOption({
      grid: { left: 42, right: 16, top: 24, bottom: 42 },
      xAxis: { type: 'category', data: xData, axisLabel: { hideOverlap: true } },
      yAxis: { type: 'value', scale: true },
      tooltip: { trigger: 'axis' },
      series: [{
        name: metric,
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 3, color: '#2f6f62' },
        areaStyle: { color: 'rgba(47,111,98,.12)' },
        data: yData,
      }],
    }, !hasData /* notMerge=true when empty: clear old axis data */);

    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => { observer.disconnect(); };
  }, [metric, points]);

  // 组件卸载时销毁图表
  useEffect(() => {
    return () => {
      if (chartRef.current && !chartRef.current.isDisposed()) {
        chartRef.current.dispose();
        chartRef.current = null;
      }
    };
  }, []);

  return <div className="chart" ref={ref}/>;
}
