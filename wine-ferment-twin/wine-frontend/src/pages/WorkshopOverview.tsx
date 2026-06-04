import { Tank } from '../api/wineApi';
import { WineWorkshopScene } from '../components/three/WineWorkshopScene';

export default function WorkshopOverview({ tanks, selected, onSelect }: { tanks: Tank[]; selected: string; onSelect: (id: string) => void }) {
  return <WineWorkshopScene tanks={tanks} selected={selected} onSelect={onSelect}/>;
}

