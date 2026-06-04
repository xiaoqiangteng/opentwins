import { Wrench } from 'lucide-react';
export function RecommendationPanel({ tank }: { tank: any }) {
  return <section className="panel"><h2><Wrench size={16}/>Recommendation</h2><p>{tank.recommendation}</p></section>;
}
