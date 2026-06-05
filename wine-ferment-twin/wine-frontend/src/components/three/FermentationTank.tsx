import * as THREE from 'three';
import { Tank } from '../../api/wineApi';

export const colorMap: Record<string, number> = {
  normal: 0x2e7d32,
  warning: 0xf9a825,
  critical: 0xc62828,
  offline: 0x9e9e9e,
  finished: 0x1565c0,
};

function makeLabel(text: string, accent: string) {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 160;
  const ctx = canvas.getContext('2d')!;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = 'rgba(255,255,255,0.92)';
  ctx.strokeStyle = accent;
  ctx.lineWidth = 8;
  ctx.beginPath();
  ctx.roundRect(18, 18, 476, 124, 24);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = '#17211e';
  ctx.font = '700 42px Inter, Arial, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 256, 78);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(1.9, 0.6, 1);
  return sprite;
}

const riskLabels: Record<string, string> = { normal: '正常', warning: '警告', critical: '危险', offline: '离线', finished: '已完成' };

export function createFermentationTank(tank: Tank, selected: boolean) {
  const group = new THREE.Group();
  const statusColor = colorMap[tank.risk_level] || colorMap.normal;
  const material = new THREE.MeshStandardMaterial({ color: statusColor, metalness: 0.35, roughness: 0.28 });
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.75, 2.4, 48), material);
  body.position.y = 1.35;
  const cap = new THREE.Mesh(new THREE.SphereGeometry(0.75, 32, 12, 0, Math.PI * 2, 0, Math.PI / 2), material);
  cap.position.y = 2.55;
  const legMaterial = new THREE.MeshStandardMaterial({ color: 0x4d5a56 });
  [-0.45, 0.45].forEach((x) => [-0.45, 0.45].forEach((z) => {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.8, 12), legMaterial);
    leg.position.set(x, 0.4, z);
    group.add(leg);
  }));
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(0.77, 0.025, 12, 64),
    new THREE.MeshStandardMaterial({ color: selected ? 0x111111 : 0xffffff }),
  );
  ring.position.y = 2.02;
  ring.rotation.x = Math.PI / 2;
  const label = makeLabel(`${tank.tank_id}  ${riskLabels[tank.risk_level] || tank.risk_level}`, selected ? '#111111' : `#${statusColor.toString(16).padStart(6, '0')}`);
  label.position.y = 3.55;
  group.add(body, cap, ring, label);
  group.userData.id = tank.tank_id;
  return group;
}

export function FermentationTank() {
  return null;
}

