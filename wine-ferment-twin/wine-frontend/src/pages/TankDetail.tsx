import { Tank } from '../api/wineApi';
import { AlarmPanel } from '../components/panels/AlarmPanel';
import { RecommendationPanel } from '../components/panels/RecommendationPanel';

function Metric({ label, tank, name }: { label: string; tank: Tank; name: string }) {
  const metric = tank.metrics[name];
  return <div className="metric"><span>{label}</span><b>{metric?.value ?? '--'} <small>{metric?.unit}</small></b></div>;
}

export default function TankDetail({ tank }: { tank: Tank }) {
  return <>
    <div className="tankHead"><div><span>{tank.thing_id}</span><h1>{tank.name}</h1></div><b className={`risk ${tank.risk_level}`}>{tank.risk_level}</b></div>
    <div className="metrics">
      <Metric label="Temp" tank={tank} name="temperature"/><Metric label="Brix" tank={tank} name="brix"/>
      <Metric label="pH" tank={tank} name="ph"/><Metric label="CO2" tank={tank} name="co2"/>
      <Metric label="Alcohol" tank={tank} name="alcohol_estimation"/><Metric label="Progress" tank={tank} name="fermentation_progress"/>
    </div>
    <RecommendationPanel tank={tank}/><AlarmPanel alarms={tank.alarms}/>
  </>;
}

