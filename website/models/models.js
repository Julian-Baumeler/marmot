import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";

const MODELS = [
  { file: "models/RocketEngine_100N_1to1.stl", label: "100 N · 1:1" },
  { file: "models/RocketEngine_100N_10Bar_Feed.stl", label: "100 N · 10 bar feed" },
  { file: "models/RocketEngine_550N_1to1.stl", label: "550 N · 1:1" },
  { file: "models/raketentriebwerk_rotationskoerper.stl", label: "Rotationskörper" },
  { file: "models/rocket_engine_section.obj", label: "Section" },
  { file: "models/rocket_engine_complete_section.obj", label: "Complete section" },
  { file: "models/Motor_Board_base.stl", label: "Motor board" },
  { file: "models/Engine.f3d", label: "Engine.f3d", fusion: true, preview: "models/Engine-preview.png" },
  { file: "models/Engine2.f3d", label: "Engine2.f3d", fusion: true, preview: "models/Engine2-preview.png" },
];

const viewers = [];
let raf = 0;
let built = false;

function fit(mesh, camera, controlsRadius) {
  const box = new THREE.Box3().setFromObject(mesh);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  mesh.position.sub(center);
  const r = Math.max(size.x, size.y, size.z) || 1;
  camera.position.set(r * 0.9, r * 0.55, r * 1.35);
  camera.near = r / 100;
  camera.far = r * 20;
  camera.lookAt(0, 0, 0);
  camera.updateProjectionMatrix();
  return r;
}

function makeViewer(canvas, object) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setClearColor(0x111111, 1);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 1000);
  scene.add(new THREE.AmbientLight(0xffffff, 0.45));
  const key = new THREE.DirectionalLight(0xffffff, 1.1);
  key.position.set(2, 3, 4);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x8899aa, 0.4);
  fill.position.set(-3, 1, 1);
  scene.add(fill);
  const mat = new THREE.MeshStandardMaterial({
    color: 0xc9cdd3,
    metalness: 0.72,
    roughness: 0.32,
  });
  object.traverse((n) => {
    if (n.isMesh) {
      n.material = mat;
      n.castShadow = false;
    }
  });
  scene.add(object);
  fit(object, camera);
  const resize = () => {
    const w = canvas.clientWidth || 320;
    const h = canvas.clientHeight || 240;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  resize();
  viewers.push({ renderer, scene, camera, object, resize });
}

function tick() {
  raf = requestAnimationFrame(tick);
  for (const v of viewers) {
    v.object.rotation.y += 0.004;
    v.renderer.render(v.scene, v.camera);
  }
}

async function loadOne(item, canvas) {
  const url = item.file;
  if (url.endsWith(".stl")) {
    const geo = await new STLLoader().loadAsync(url);
    geo.computeVertexNormals();
    makeViewer(canvas, new THREE.Mesh(geo));
  } else {
    const obj = await new OBJLoader().loadAsync(url);
    obj.traverse((n) => {
      if (n.isMesh && n.geometry) n.geometry.computeVertexNormals();
    });
    makeViewer(canvas, obj);
  }
}

export async function buildModels() {
  if (built) {
    if (!raf) tick();
    return;
  }
  const grid = document.getElementById("model-grid");
  grid.innerHTML = "";
  for (const item of MODELS) {
    const card = document.createElement("div");
    card.className = "model-card";
    const cap = document.createElement("p");
    cap.textContent = item.label;
    if (item.fusion) {
      const img = document.createElement("img");
      img.src = item.preview;
      img.alt = item.label;
      img.style.cssText = "width:100%;height:220px;object-fit:contain;background:#111;display:block";
      const note = document.createElement("p");
      note.className = "model-note";
      note.textContent = "Fusion archive — parametric .f3d, not a mesh";
      card.append(img, cap, note);
    } else {
      const canvas = document.createElement("canvas");
      card.append(canvas, cap);
      try {
        await loadOne(item, canvas);
      } catch (e) {
        const note = document.createElement("p");
        note.className = "model-note";
        note.textContent = "Could not load";
        canvas.replaceWith(note);
      }
    }
    grid.appendChild(card);
  }
  built = true;
  window.addEventListener("resize", () => viewers.forEach((v) => v.resize()));
  tick();
}

export function stopModels() {
  cancelAnimationFrame(raf);
  raf = 0;
}

window.buildModels = buildModels;
window.stopModels = stopModels;
