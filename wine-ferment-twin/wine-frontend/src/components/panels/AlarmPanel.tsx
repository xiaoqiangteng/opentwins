import { AlertTriangle } from 'lucide-react';
const levelLabels: Record<string, string> = { critical: '危险', warning: '警告', offline: '离线' };
export function AlarmPanel({ alarms }: { alarms: any[] }) {
  return <section className="panel"><h2><AlertTriangle size={16}/>告警</h2>{alarms.length ? alarms.map((alarm, index) => <p className="alarm" key={index}><b>{levelLabels[alarm.level] || alarm.level}</b> {alarm.message}</p>) : <p className="muted">暂无活跃告警</p>}</section>;
}
