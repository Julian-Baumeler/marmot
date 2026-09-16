(function (g) {
  "use strict";

  const PARTS = [
    { id: "cutFace", label: "1  Cut-plane fill", color: [0.95, 0.82, 0.12] },
    { id: "injector", label: "2  Injector tube", color: [0.90, 0.22, 0.18] },
    { id: "flange", label: "3  Injector flange / plug", color: [0.98, 0.50, 0.12] }, // unused if empty
    { id: "liner", label: "4  Inner liner", color: [0.15, 0.72, 0.88] },
    { id: "jacket", label: "5  Jacket wall", color: [0.25, 0.82, 0.38] },
    { id: "outer", label: "6  Outer wall", color: [0.78, 0.78, 0.82] },
    { id: "bulkhead", label: "7  Left bulkhead", color: [0.95, 0.45, 0.70] },
    { id: "inlet", label: "8  Inlet pipe", color: [0.72, 0.38, 0.95] },
    { id: "nozzle", label: "9  Right end / nozzle", color: [0.35, 0.48, 0.95] },
    { id: "other", label: "10  Other", color: [0.55, 0.55, 0.48] },
  ];

  function partId(cx, cy, cz) {
    const r = Math.hypot(cy, cz);
    if (cz > 36) return "inlet";
    if (cx > 150) return "nozzle";
    if (r < 9.3) return "injector";
    if (cx < 1.5) return "bulkhead";
    if (r >= 12.5 && r < 19.5) return "liner";
    if (r >= 19.5 && r < 31.5) return "jacket";
    if (r >= 31.5) return "outer";
    return "other";
  }

  function splitCutParts(positions, normals) {
    const buckets = {};
    PARTS.forEach((p) => {
      buckets[p.id] = { id: p.id, label: p.label, color: p.color, p: [], n: [] };
    });
    for (let i = 0; i < positions.length; i += 9) {
      const y0 = positions[i + 1], y1 = positions[i + 4], y2 = positions[i + 7];
      const onCut = Math.abs(y0) < 0.05 && Math.abs(y1) < 0.05 && Math.abs(y2) < 0.05;
      const cx = (positions[i] + positions[i + 3] + positions[i + 6]) / 3;
      const cy = (y0 + y1 + y2) / 3;
      const cz = (positions[i + 2] + positions[i + 5] + positions[i + 8]) / 3;
      const b = buckets[onCut ? "cutFace" : partId(cx, cy, cz)];
      for (let k = 0; k < 9; k++) {
        b.p.push(positions[i + k]);
        b.n.push(normals[i + k]);
      }
    }
    return PARTS.map((p) => ({
      id: p.id,
      label: p.label,
      color: p.color,
      positions: new Float32Array(buckets[p.id].p),
      normals: new Float32Array(buckets[p.id].n),
    })).filter((p) => p.positions.length);
  }

  function shift(arr, c) {
    for (let i = 0; i < arr.length; i += 3) {
      arr[i] -= c[0]; arr[i + 1] -= c[1]; arr[i + 2] -= c[2];
    }
  }

  function bboxOf(positions) {
    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < positions.length; i += 3) {
      const x = positions[i], y = positions[i + 1], z = positions[i + 2];
      if (x < min[0]) min[0] = x; if (y < min[1]) min[1] = y; if (z < min[2]) min[2] = z;
      if (x > max[0]) max[0] = x; if (y > max[1]) max[1] = y; if (z > max[2]) max[2] = z;
    }
    const size = [max[0] - min[0], max[1] - min[1], max[2] - min[2]];
    const center = [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2];
    return { min, max, size, center, radius: Math.max(size[0], size[1], size[2]) || 1 };
  }

  async function loadEngine2() {
    const [objText, cutText] = await Promise.all([
      fetch("../models/Engine2.obj").then((r) => {
        if (!r.ok) throw new Error("obj " + r.status);
        return r.text();
      }),
      fetch("../models/Engine2-cut.obj").then((r) => {
        if (!r.ok) throw new Error("cut obj " + r.status);
        return r.text();
      }),
    ]);
    const full = MarmotSection.readObj(objText);
    const cutMesh = MarmotSection.readObj(cutText);
    const cutParts = splitCutParts(cutMesh.positions, cutMesh.normals);
    const cut = { positions: cutMesh.positions, normals: cutMesh.normals };
    const b = bboxOf(full.positions);
    shift(full.positions, b.center);
    shift(cut.positions, b.center);
    cutParts.forEach((p) => shift(p.positions, b.center));
    const radius = b.radius;
    return {
      positions: full.positions,
      normals: full.normals,
      cut,
      cutParts,
      min: b.min,
      max: b.max,
      size: b.size,
      center: [0, 0, 0],
      radius,
      eye: [radius * 0.55, radius * 1.7, radius * 2.45],
      fov: 0.92,
      originCenter: b.center,
    };
  }

  function watchCut(cb) {
    let last = null;
    function apply(on) {
      on = !!on;
      if (on === last) return;
      last = on;
      cb(on);
    }
    function readParent() {
      try {
        if (parent && parent.document && parent.document.body.classList.contains("cut")) return true;
      } catch (e) {}
      return /[?&]cut=1\b/.test(location.search);
    }
    addEventListener("message", (e) => {
      if (e.data && e.data.type === "cut") apply(e.data.on);
    });
    apply(readParent());
    setInterval(() => apply(readParent()), 300);
  }

  g.loadEngine2 = loadEngine2;
  g.watchCut = watchCut;
})(typeof globalThis !== "undefined" ? globalThis : this);
