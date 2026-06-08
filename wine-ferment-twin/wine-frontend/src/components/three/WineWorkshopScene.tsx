import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { Tank } from '../../api/wineApi';
import { createFermentationTank } from './FermentationTank';

export function WineWorkshopScene({ tanks, selected, onSelect }: { tanks: Tank[]; selected: string; onSelect: (id: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const root = ref.current;
    root.innerHTML = '';
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf4f7f2);
    const camera = new THREE.PerspectiveCamera(45, root.clientWidth / root.clientHeight, 0.1, 100);
    camera.position.set(7, 6, 9);
    camera.lookAt(0, 1.35, 0);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(root.clientWidth, root.clientHeight);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    root.appendChild(renderer.domElement);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8c9a8c, 1.2));
    const directional = new THREE.DirectionalLight(0xffffff, 1.5);
    directional.position.set(5, 8, 3);
    scene.add(directional);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(12, 8), new THREE.MeshStandardMaterial({ color: 0xdfe7dc, roughness: 0.8 }));
    floor.rotation.x = -Math.PI / 2;
    scene.add(floor);
    const backWall = new THREE.Mesh(new THREE.PlaneGeometry(12, 3.4), new THREE.MeshStandardMaterial({ color: 0xe8eee5, roughness: 0.9 }));
    backWall.position.set(0, 1.7, -3.2);
    scene.add(backWall);
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const tankMeshes: THREE.Object3D[] = [];
    const tankData = tanks.length ? tanks : ([
      { tank_id: 'tank_01', thing_id: 'wine:tank_01', name: 'Fermentation Tank 01', wine_type: 'red', stage: 'active', risk_level: 'normal', metrics: {}, alarms: [], recommendation: 'Continue monitoring.' },
      { tank_id: 'tank_02', thing_id: 'wine:tank_02', name: 'Fermentation Tank 02', wine_type: 'red', stage: 'active', risk_level: 'warning', metrics: {}, alarms: [], recommendation: 'Activate cooling or reduce target temperature.' },
      { tank_id: 'tank_03', thing_id: 'wine:tank_03', name: 'Fermentation Tank 03', wine_type: 'white', stage: 'active', risk_level: 'warning', metrics: {}, alarms: [], recommendation: 'Check yeast activity and nutrients.' },
    ] as Tank[]);

    tankData.forEach((tank, index) => {
      const group = createFermentationTank(tank, selected === tank.tank_id);
      group.position.x = (index - 1) * 3.1;
      scene.add(group);
      tankMeshes.push(group);
    });

    function click(event: MouseEvent) {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const hit = raycaster.intersectObjects(tankMeshes, true)[0];
      if (!hit) return;
      let object: any = hit.object;
      while (object && !object.userData.id) object = object.parent;
      if (object?.userData.id) onSelect(object.userData.id);
    }

    renderer.domElement.addEventListener('click', click);
    let frame = 0;
    function animate() {
      frame = requestAnimationFrame(animate);
      scene.rotation.y = Math.sin(Date.now() / 6000) * 0.03;

      // 选中 tank 的粒子环绕旋转动画
      const time = Date.now() / 1000;
      scene.traverse((obj) => {
        if (obj.name === 'selectionParticles' && obj instanceof THREE.Points) {
          obj.rotation.y = time * 0.5;
          // 粒子上下浮动
          const positions = obj.geometry.attributes.position;
          for (let i = 0; i < positions.count; i++) {
            const y = positions.getY(i);
            positions.setY(i, y + Math.sin(time * 2 + i * 0.3) * 0.002);
          }
          positions.needsUpdate = true;
        }
      });

      renderer.render(scene, camera);
    }
    animate();
    const observer = new ResizeObserver(() => {
      camera.aspect = root.clientWidth / root.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(root.clientWidth, root.clientHeight);
    });
    observer.observe(root);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      renderer.domElement.removeEventListener('click', click);
      renderer.dispose();
      root.innerHTML = '';
    };
  }, [tanks, selected, onSelect]);
  return <div className="three" ref={ref}/>;
}
