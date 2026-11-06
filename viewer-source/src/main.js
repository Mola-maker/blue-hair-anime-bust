import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const captureMode = new URLSearchParams(window.location.search).has('capture');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const loading = document.getElementById('loading');
const progress = document.getElementById('progress');
const loadLabel = document.getElementById('load-label');

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: true,
  preserveDrawingBuffer: captureMode,
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.domElement.setAttribute('aria-label', '蓝发少女三维骨骼胸像，可拖动旋转和缩放');
renderer.domElement.setAttribute('role', 'img');
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(32, window.innerWidth / window.innerHeight, 0.01, 100);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.075;
controls.autoRotateSpeed = 0.8;
controls.minPolarAngle = 0.15;
controls.maxPolarAngle = Math.PI * 0.88;

scene.add(new THREE.HemisphereLight(0xf5faff, 0x8397aa, 2.15));
const key = new THREE.DirectionalLight(0xffffff, 3.1);
key.position.set(3.5, 5.5, 4.5);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.left = -3;
key.shadow.camera.right = 3;
key.shadow.camera.top = 3;
key.shadow.camera.bottom = -3;
key.shadow.bias = -0.0004;
scene.add(key);
const fill = new THREE.DirectionalLight(0xcfe5ff, 1.4);
fill.position.set(-4, 2, 3);
scene.add(fill);
const rim = new THREE.DirectionalLight(0xffffff, 2.0);
rim.position.set(1, 3, -4);
scene.add(rim);

let model;
let skeleton;
let mixer;
let action;
let motionEnabled = false;
let baseDistance = 5;
let baseTarget = new THREE.Vector3();
let modelBounds;
const clock = new THREE.Clock();

function tuneMaterial(material) {
  const name = (material.name || '').toLowerCase();
  material.metalness = 0;
  if (name.includes('catchlight')) material.roughness = 0.12;
  else if (name.includes('eye_iris')) material.roughness = 0.16;
  else if (name.includes('lash')) material.roughness = 0.38;
  else if (name.includes('lip_glint')) material.roughness = 0.18;
  else if (name.includes('lip')) material.roughness = 0.28;
  else if (name.includes('skin')) material.roughness = 0.49;
  else if (name.includes('cloth_strap_edge')) material.roughness = 0.52;
  else if (name.includes('cloth_strap')) material.roughness = 0.48;
  else if (name.includes('hair')) material.roughness = 0.43;
  else material.roughness = 0.68;
  material.side = THREE.DoubleSide;
  if (material.normalScale) {
    const strength = name.includes('skin') ? 0.12 : name.includes('hair') ? 0.4 : 0.3;
    material.normalScale.set(strength, strength);
  }
  if ('clearcoat' in material && name.includes('hair')) {
    material.clearcoat = 0.1;
    material.clearcoatRoughness = 0.32;
  }
  if ('anisotropy' in material && name.includes('hair')) material.anisotropy = 0.55;
  material.needsUpdate = true;
}

function forEachMaterial(callback) {
  model?.traverse((object) => {
    if (!object.isMesh) return;
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    materials.forEach(callback);
  });
}

function modelStats(root) {
  let triangles = 0;
  let meshes = 0;
  let bones = 0;
  let skinnedMeshes = 0;
  root.traverse((object) => {
    if (object.isBone) bones += 1;
    if (object.isSkinnedMesh) skinnedMeshes += 1;
    if (!object.isMesh) return;
    meshes += 1;
    triangles += object.geometry.index
      ? object.geometry.index.count / 3
      : object.geometry.attributes.position.count / 3;
  });
  return { triangles: Math.round(triangles), meshes, bones, skinnedMeshes };
}

function addPlinth(box) {
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const height = Math.max(size.y * 0.025, 0.025);
  const radius = Math.max(size.x, size.z) * 0.55 + 0.12;
  const geometry = new THREE.CylinderGeometry(radius, radius * 1.025, height, 128);
  const material = new THREE.MeshStandardMaterial({ color: 0xf6f9fc, roughness: 0.82, metalness: 0 });
  const plinth = new THREE.Mesh(geometry, material);
  plinth.position.set(center.x, box.min.y - height * 0.5, center.z);
  plinth.castShadow = true;
  plinth.receiveShadow = true;
  scene.add(plinth);
}

function fitCamera(bounds) {
  const size = bounds.getSize(new THREE.Vector3());
  const center = bounds.getCenter(new THREE.Vector3());
  const vertical = size.y / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5)));
  const horizontal = size.x / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5)) * camera.aspect);
  baseDistance = Math.max(vertical, horizontal) * 1.5 + size.z * 0.5;
  baseTarget = center.clone();
  baseTarget.y += size.y * 0.015;
}

function setView(name = 'hero') {
  if (!modelBounds) return;
  const directions = {
    hero: new THREE.Vector3(1, 0.42, 1.25),
    front: new THREE.Vector3(0.18, 0.16, 1),
    side: new THREE.Vector3(1, 0.16, 0.12),
    back: new THREE.Vector3(0.05, 0.16, -1),
    face: new THREE.Vector3(0.52, 0.12, 1),
  };
  const direction = (directions[name] || directions.hero).normalize();
  const target = baseTarget.clone();
  let distance = baseDistance;
  if (name === 'face') {
    target.y += modelBounds.getSize(new THREE.Vector3()).y * 0.22;
    distance *= window.innerWidth < 760 ? 0.76 : 0.64;
  }
  controls.target.copy(target);
  camera.position.copy(target).addScaledVector(direction, distance);
  camera.near = Math.max(0.005, distance * 0.002);
  camera.far = distance * 20;
  camera.updateProjectionMatrix();
  controls.update();
  renderOnce();
}

function renderOnce() {
  controls.update();
  renderer.render(scene, camera);
  window.__RENDER_STATS__ = {
    drawCalls: renderer.info.render.calls,
    triangles: renderer.info.render.triangles,
  };
}

function animate() {
  if (captureMode) return;
  requestAnimationFrame(animate);
  const delta = clock.getDelta();
  if (motionEnabled && mixer) mixer.update(delta);
  controls.update();
  renderer.render(scene, camera);
}

function setButtonState(id, active) {
  document.getElementById(id).classList.toggle('active', active);
}

const loader = new GLTFLoader();
loader.load(
  './model.glb',
  (gltf) => {
    model = gltf.scene;
    model.traverse((object) => {
      if (!object.isMesh) return;
      object.castShadow = true;
      object.receiveShadow = true;
      object.frustumCulled = !object.isSkinnedMesh;
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.forEach(tuneMaterial);
    });
    scene.add(model);
    modelBounds = new THREE.Box3().setFromObject(model);
    addPlinth(modelBounds);
    fitCamera(modelBounds);
    skeleton = new THREE.SkeletonHelper(model);
    skeleton.visible = false;
    skeleton.material.depthTest = false;
    skeleton.material.transparent = true;
    skeleton.material.opacity = 0.92;
    skeleton.renderOrder = 20;
    scene.add(skeleton);
    if (gltf.animations.length) {
      mixer = new THREE.AnimationMixer(model);
      action = mixer.clipAction(gltf.animations[0]);
      action.setLoop(THREE.LoopRepeat, Infinity);
      action.play();
      mixer.setTime(0);
    }
    const stats = modelStats(model);
    window.__MODEL_STATS__ = {
      ...stats,
      textured: true,
      format: 'GLB',
      animations: gltf.animations.length,
    };
    document.getElementById('stats').innerHTML = `<strong>${stats.triangles.toLocaleString('zh-CN')} 三角面 · ${stats.bones} 骨骼</strong>冷白蓝服装 · 深蓝肩带 · 蒙皮动画`;
    progress.style.width = '100%';
    loadLabel.textContent = '模型已就绪';
    setView('hero');
    window.__SCENE_READY__ = true;
    if (captureMode) {
      loading.classList.add('done');
      loading.style.display = 'none';
      renderOnce();
    } else {
      clock.start();
      animate();
      requestAnimationFrame(() => loading.classList.add('done'));
    }
  },
  (event) => {
    if (event.lengthComputable && event.total > 0) {
      const percent = Math.min(96, Math.round((event.loaded / event.total) * 100));
      progress.style.width = `${percent}%`;
      loadLabel.textContent = `读取模型与彩色贴图… ${percent}%`;
    } else {
      progress.style.width = '68%';
      loadLabel.textContent = '正在解压几何与贴图…';
    }
  },
  (error) => {
    console.error('Model loading failed', error);
    loadLabel.textContent = '模型读取失败，请刷新后重试。';
    loadLabel.classList.add('error');
  },
);

for (const button of document.querySelectorAll('[data-view]')) {
  button.addEventListener('click', () => setView(button.dataset.view));
}
document.getElementById('rotate').addEventListener('click', (event) => {
  controls.autoRotate = !controls.autoRotate;
  event.currentTarget.classList.toggle('active', controls.autoRotate);
  renderOnce();
});
document.getElementById('wire').addEventListener('click', (event) => {
  const active = !event.currentTarget.classList.contains('active');
  setButtonState('wire', active);
  forEachMaterial((material) => {
    material.wireframe = active;
    material.needsUpdate = true;
  });
  renderOnce();
});
document.getElementById('bones').addEventListener('click', (event) => {
  if (!skeleton) return;
  skeleton.visible = !skeleton.visible;
  event.currentTarget.classList.toggle('active', skeleton.visible);
  renderOnce();
});
document.getElementById('motion').addEventListener('click', (event) => {
  if (!mixer || !action) return;
  motionEnabled = !motionEnabled;
  event.currentTarget.classList.toggle('active', motionEnabled);
  if (motionEnabled) action.reset().play();
  if (captureMode) {
    mixer.setTime(motionEnabled ? 1 : 0);
    renderOnce();
  }
  clock.getDelta();
});
document.getElementById('reset').addEventListener('click', () => {
  controls.autoRotate = false;
  motionEnabled = false;
  forEachMaterial((material) => {
    material.wireframe = false;
    material.needsUpdate = true;
  });
  if (skeleton) skeleton.visible = false;
  if (mixer) mixer.setTime(0);
  ['rotate', 'wire', 'bones', 'motion'].forEach((id) => setButtonState(id, false));
  setView('hero');
});

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  if (modelBounds) {
    fitCamera(modelBounds);
    setView('hero');
  }
  renderOnce();
});
controls.addEventListener('change', () => {
  if (captureMode) renderer.render(scene, camera);
});
if (reducedMotion) controls.autoRotate = false;
renderOnce();
