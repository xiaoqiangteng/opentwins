import { AlertTriangle } from 'lucide-react';
export function AlarmPanel({ alarms }: { alarms: any[] }) {
  return <section className="panel"><h2><AlertTriangle size={16}/>Alarms</h2>{alarms.length ? alarms.map((alarm, index) => <p className="alarm" key={index}><b>{alarm.level}</b> {alarm.message}</p>) : <p className="muted">No active alarms.</p>}</section>;
}
