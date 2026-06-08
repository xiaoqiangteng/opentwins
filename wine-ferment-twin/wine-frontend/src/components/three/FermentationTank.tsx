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
  const isSelected = selected;

  // ── 主体 ────────────────────────────────────────────────────────────
  const bodyMaterial = new THREE.MeshStandardMaterial({
    color: statusColor,
    metalness: 0.35,
    roughness: 0.28,
    emissive: isSelected ? statusColor : 0x000000,
    emissiveIntensity: isSelected ? 0.15 : 0,
  });
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.75, 2.4, 48), bodyMaterial);
  body.position.y = 1.35;

  const cap = new THREE.Mesh(
    new THREE.SphereGeometry(0.75, 32, 12, 0, Math.PI * 2, 0, Math.PI / 2),
    bodyMaterial,
  );
  cap.position.y = 2.55;

  // ── 支腿 ────────────────────────────────────────────────────────────
  const legMaterial = new THREE.MeshStandardMaterial({ color: 0x4d5a56 });
  [-0.45, 0.45].forEach((x) => [-0.45, 0.45].forEach((z) => {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.8, 12), legMaterial);
    leg.position.set(x, 0.4, z);
    group.add(leg);
  }));

  // ── 装饰环 ──────────────────────────────────────────────────────────
  const ringColor = isSelected ? 0xffd740 : 0xffffff;
  const ringMaterial = new THREE.MeshStandardMaterial({
    color: ringColor,
    emissive: isSelected ? 0xffd740 : 0x000000,
    emissiveIntensity: isSelected ? 0.4 : 0,
  });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.77, isSelected ? 0.035 : 0.025, 12, 64), ringMaterial);
  ring.position.y = 2.02;
  ring.rotation.x = Math.PI / 2;

  // 底部装饰环
  const bottomRing = new THREE.Mesh(
    new THREE.TorusGeometry(0.77, isSelected ? 0.035 : 0.025, 12, 64),
    ringMaterial,
  );
  bottomRing.position.y = 0.15;
  bottomRing.rotation.x = Math.PI / 2;

  // ── 选中光圈（底部发光圆环） ──────────────────────────────────────
  if (isSelected) {
    const glowRing = new THREE.Mesh(
      new THREE.RingGeometry(0.85, 1.15, 64),
      new THREE.MeshBasicMaterial({
        color: statusColor,
        transparent: true,
        opacity: 0.35,
        side: THREE.DoubleSide,
      }),
    );
    glowRing.rotation.x = -Math.PI / 2;
    glowRing.position.y = 0.02;
    group.add(glowRing);
  }

  // ── 选中粒子光环 ──────────────────────────────────────────────────
  if (isSelected) {
    const particleCount = 60;
    const particleGeom = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      const angle = (i / particleCount) * Math.PI * 2;
      const r = 0.95 + (Math.random() - 0.5) * 0.15;
      positions[i * 3] = Math.cos(angle) * r;
      positions[i * 3 + 1] = 1.35 + (Math.random() - 0.5) * 2.0;
      positions[i * 3 + 2] = Math.sin(angle) * r;
    }
    particleGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    // 生成圆形粒子纹理
    const pCanvas = document.createElement('canvas');
    pCanvas.width = 32;
    pCanvas.height = 32;
    const pCtx = pCanvas.getContext('2d')!;
    const gradient = pCtx.createRadialGradient(16, 16, 0, 16, 16, 16);
    gradient.addColorStop(0, 'rgba(255,255,255,1)');
    gradient.addColorStop(0.4, 'rgba(255,255,255,0.6)');
    gradient.addColorStop(1, 'rgba(255,255,255,0)');
    pCtx.fillStyle = gradient;
    pCtx.fillRect(0, 0, 32, 32);
    const pTexture = new THREE.CanvasTexture(pCanvas);

    const particleMat = new THREE.PointsMaterial({
      size: 0.06,
      map: pTexture,
      color: statusColor,
      transparent: true,
      opacity: 0.7,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const particles = new THREE.Points(particleGeom, particleMat);
    particles.name = 'selectionParticles';
    group.add(particles);
  }

  // ── 标签 ──────────────────────────────────────────────────────────
  const labelColor = isSelected ? '#ffd740' : `#${statusColor.toString(16).padStart(6, '0')}`;
  const label = makeLabel(`${tank.tank_id}  ${riskLabels[tank.risk_level] || tank.risk_level}`, labelColor);
  label.position.y = 3.55;

  group.add(body, cap, ring, bottomRing, label);
  group.userData.id = tank.tank_id;
  return group;
}

export function FermentationTank() {
  return null;
}
