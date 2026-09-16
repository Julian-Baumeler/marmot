(function (global) {
  "use strict";

  function bboxOf(tris) {
    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];
    for (const t of tris) {
      for (let i = 0; i < 3; i++) {
        const p = t[i];
        for (let a = 0; a < 3; a++) {
          if (p[a] < min[a]) min[a] = p[a];
          if (p[a] > max[a]) max[a] = p[a];
        }
      }
    }
    const size = [max[0] - min[0], max[1] - min[1], max[2] - min[2]];
    const center = [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2];
    return { min, max, size, center };
  }

  function axisPlane(b, n) {
    const d = -(n[0] * b.center[0] + n[1] * b.center[1] + n[2] * b.center[2]);
    return { n: n.slice(), d, center: b.center, size: b.size, min: b.min, max: b.max };
  }

  function midPlane(tris) {
    const b = bboxOf(tris);
    let n = [1, 0, 0];
    if (b.size[1] <= b.size[0] && b.size[1] <= b.size[2]) n = [0, 1, 0];
    else if (b.size[2] <= b.size[0] && b.size[2] <= b.size[1]) n = [0, 0, 1];
    return axisPlane(b, n);
  }

  function sd(plane, p) {
    return plane.n[0] * p[0] + plane.n[1] * p[1] + plane.n[2] * p[2] + plane.d;
  }

  function lerp(a, b, t) {
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
  }

  function intersectTri(tri, plane, eps) {
    const d = [sd(plane, tri[0]), sd(plane, tri[1]), sd(plane, tri[2])];
    const hits = [];
    for (let e = 0; e < 3; e++) {
      const a = tri[e], b = tri[(e + 1) % 3];
      const da = d[e], db = d[(e + 1) % 3];
      if (Math.abs(da) <= eps && Math.abs(db) <= eps) {
        hits.push(a, b);
        continue;
      }
      if (da * db < 0) {
        const t = da / (da - db);
        hits.push(lerp(a, b, t));
      } else if (Math.abs(da) <= eps) {
        hits.push(a);
      }
    }
    if (hits.length < 2) return null;
    return [hits[0], hits[hits.length - 1]];
  }

  function weldPoint(p, eps, map, pts) {
    const q = 1 / eps;
    const k = (Math.round(p[0] * q)) + "," + (Math.round(p[1] * q)) + "," + (Math.round(p[2] * q));
    if (map.has(k)) return map.get(k);
    const id = pts.length;
    pts.push(p);
    map.set(k, id);
    return id;
  }

  function extractLoops(edges, pts, closeEps) {
    const adj = new Map();
    const add = (a, b) => {
      if (a === b) return;
      if (!adj.has(a)) adj.set(a, []);
      if (adj.get(a).indexOf(b) < 0) adj.get(a).push(b);
    };
    const ek = (a, b) => (a < b ? a + "," + b : b + "," + a);
    const seenE = new Set();
    edges.forEach(([a, b]) => {
      if (a === b) return;
      const k = ek(a, b);
      if (seenE.has(k)) return;
      seenE.add(k);
      add(a, b);
      add(b, a);
    });
    const dist2 = (i, j) => {
      const dx = pts[i][0] - pts[j][0], dy = pts[i][1] - pts[j][1], dz = pts[i][2] - pts[j][2];
      return dx * dx + dy * dy + dz * dz;
    };
    const used = new Set();
    const take = (a, b) => {
      const k = ek(a, b);
      if (used.has(k)) return false;
      used.add(k);
      return true;
    };
    const unusedNbr = (v, prev) => {
      const nbrs = adj.get(v) || [];
      for (let i = 0; i < nbrs.length; i++) {
        if (nbrs[i] !== prev && !used.has(ek(v, nbrs[i]))) return nbrs[i];
      }
      return -1;
    };
    const walk = (start, next) => {
      const chain = [start];
      let prev = start, cur = next;
      take(start, next);
      let guard = 0;
      while (cur !== start && guard++ < pts.length + 4) {
        chain.push(cur);
        const n = unusedNbr(cur, prev);
        if (n < 0) break;
        take(cur, n);
        prev = cur;
        cur = n;
      }
      if (cur === start) return chain;
      const back = unusedNbr(start, next);
      if (back >= 0) {
        const head = [];
        prev = start;
        cur = back;
        take(start, back);
        guard = 0;
        while (cur !== chain[chain.length - 1] && guard++ < pts.length + 4) {
          head.push(cur);
          const n = unusedNbr(cur, prev);
          if (n < 0) break;
          take(cur, n);
          prev = cur;
          cur = n;
        }
        head.reverse();
        return head.concat(chain);
      }
      return chain;
    };
    const loops = [];
    const opens = [];
    const lim = closeEps * closeEps;
    adj.forEach((nbrs, v) => {
      for (let i = 0; i < nbrs.length; i++) {
        if (used.has(ek(v, nbrs[i]))) continue;
        const chain = walk(v, nbrs[i]);
        if (chain.length < 2) continue;
        const a = chain[0], b = chain[chain.length - 1];
        if (a === b || dist2(a, b) <= lim) {
          if (chain[0] === chain[chain.length - 1]) chain.pop();
          if (chain.length >= 3) loops.push(chain);
        } else {
          opens.push(chain);
        }
      }
    });
    const usedC = new Set();
    const pairLim = lim * 8;
    for (let i = 0; i < opens.length; i++) {
      if (usedC.has(i)) continue;
      const A = opens[i];
      const a0 = A[0], a1 = A[A.length - 1];
      let best = -1, mode = 0, bestS = pairLim;
      for (let j = i + 1; j < opens.length; j++) {
        if (usedC.has(j)) continue;
        const B = opens[j];
        const b0 = B[0], b1 = B[B.length - 1];
        const s0 = dist2(a0, b0) + dist2(a1, b1);
        const s1 = dist2(a0, b1) + dist2(a1, b0);
        if (s0 < bestS) { bestS = s0; best = j; mode = 0; }
        if (s1 < bestS) { bestS = s1; best = j; mode = 1; }
      }
      if (best < 0) continue;
      usedC.add(i);
      usedC.add(best);
      const B = mode ? opens[best].slice().reverse() : opens[best].slice();
      const loop = A.concat(B);
      if (loop.length >= 4) loops.push(loop);
    }
    return loops;
  }

  function basis(plane) {
    const n = plane.n;
    const nlen = Math.hypot(n[0], n[1], n[2]) || 1;
    const nn = [n[0] / nlen, n[1] / nlen, n[2] / nlen];
    const tmp = Math.abs(nn[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
    const t1 = [
      tmp[1] * nn[2] - tmp[2] * nn[1],
      tmp[2] * nn[0] - tmp[0] * nn[2],
      tmp[0] * nn[1] - tmp[1] * nn[0],
    ];
    const t1l = Math.hypot(t1[0], t1[1], t1[2]) || 1;
    t1[0] /= t1l; t1[1] /= t1l; t1[2] /= t1l;
    const t2 = [
      nn[1] * t1[2] - nn[2] * t1[1],
      nn[2] * t1[0] - nn[0] * t1[2],
      nn[0] * t1[1] - nn[1] * t1[0],
    ];
    return { n: nn, t1, t2 };
  }

  function to2(p, origin, t1, t2) {
    const dx = p[0] - origin[0], dy = p[1] - origin[1], dz = p[2] - origin[2];
    return [dx * t1[0] + dy * t1[1] + dz * t1[2], dx * t2[0] + dy * t2[1] + dz * t2[2]];
  }

  function area2(poly) {
    let a = 0;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      a += poly[j][0] * poly[i][1] - poly[i][0] * poly[j][1];
    }
    return a / 2;
  }

  function pip(x, y, poly) {
    let c = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const xi = poly[i][0], yi = poly[i][1], xj = poly[j][0], yj = poly[j][1];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-30) + xi) c = !c;
    }
    return c;
  }

  function getEarcut() {
    if (typeof earcut === "function") return earcut;
    if (typeof require === "function") {
      try { return require("./vendor/earcut/earcut.min.js"); } catch (e) {}
    }
    throw new Error("earcut missing");
  }

  function triArea2(ax, ay, bx, by, cx, cy) {
    return Math.abs((bx - ax) * (cy - ay) - (cx - ax) * (by - ay)) / 2;
  }

  function buildSection(tris, plane) {
    const b = bboxOf(tris);
    const diag = Math.hypot(b.size[0], b.size[1], b.size[2]) || 1;
    const eps = Math.max(diag * 1e-5, 1e-7);
    const segs = [];
    for (const t of tris) {
      const hit = intersectTri(t, plane, eps);
      if (hit) segs.push(hit);
    }
    const map = new Map();
    const pts = [];
    const edges = [];
    for (const s of segs) {
      const a = weldPoint(s[0], eps, map, pts);
      const c = weldPoint(s[1], eps, map, pts);
      if (a !== c) edges.push([a, c]);
    }
    const loops = extractLoops(edges, pts, Math.max(eps * 40, diag * 0.03));
    const { n, t1, t2 } = basis(plane);
    const origin = plane.center || b.center;
    const pinchSplit = (pts3, pts2, eps2) => {
      const n = pts2.length;
      for (let i = 0; i < n; i++) {
        for (let j = i + 2; j < n; j++) {
          if (i === 0 && j === n - 1) continue;
          const along = Math.min(j - i, n - (j - i));
          if (along < Math.max(8, n * 0.08)) continue;
          const dx = pts2[i][0] - pts2[j][0], dy = pts2[i][1] - pts2[j][1];
          if (dx * dx + dy * dy > eps2) continue;
          return [
            { pts3: pts3.slice(i, j + 1), pts2: pts2.slice(i, j + 1) },
            { pts3: pts3.slice(j).concat(pts3.slice(0, i + 1)), pts2: pts2.slice(j).concat(pts2.slice(0, i + 1)) },
          ];
        }
      }
      return null;
    };
    const raw = loops.map((ids) => {
      const pts3 = ids.map((i) => pts[i]);
      const pts2 = pts3.map((p) => to2(p, origin, t1, t2));
      return { pts3, pts2 };
    });
    const packed = [];
    const pinchEps2 = Math.pow(Math.max(eps * 8, diag * 0.015), 2);
    const queue = raw.slice();
    while (queue.length) {
      const L = queue.pop();
      if (L.pts2.length < 3) continue;
      const split = pinchSplit(L.pts3, L.pts2, pinchEps2);
      if (split) {
        queue.push(split[0], split[1]);
        continue;
      }
      const area = Math.abs(area2(L.pts2));
      if (area > diag * diag * 1e-12) packed.push({ pts3: L.pts3, pts2: L.pts2, area });
    }
    packed.sort((a, c) => c.area - a.area);

    const usedHole = new Set();
    const groups = [];
    for (let i = 0; i < packed.length; i++) {
      if (usedHole.has(i)) continue;
      const holes = [];
      for (let j = i + 1; j < packed.length; j++) {
        if (usedHole.has(j)) continue;
        if (!pip(packed[j].pts2[0][0], packed[j].pts2[0][1], packed[i].pts2)) continue;
        let nested = false;
        for (let k = i + 1; k < j; k++) {
          if (usedHole.has(k)) continue;
          if (
            pip(packed[j].pts2[0][0], packed[j].pts2[0][1], packed[k].pts2) &&
            pip(packed[k].pts2[0][0], packed[k].pts2[0][1], packed[i].pts2)
          ) {
            nested = true;
            break;
          }
        }
        if (!nested) {
          holes.push(packed[j]);
          usedHole.add(j);
        }
      }
      groups.push({ outer: packed[i], holes });
    }

    const earcutFn = getEarcut();
    const positions = [];
    const indices = [];
    const uvs = [];
    const normals = [];
    const uvScale = 1.1;
    const solids = [];
    let holeCount = 0;
    const offset = diag * 8e-4;

    groups.forEach((g) => {
      const outerA = area2(g.outer.pts2);
      const outer3 = outerA < 0 ? g.outer.pts3.slice().reverse() : g.outer.pts3.slice();
      const outer2 = outerA < 0 ? g.outer.pts2.slice().reverse() : g.outer.pts2.slice();
      const holes3 = [];
      const holes2 = [];
      g.holes.forEach((h) => {
        const a = area2(h.pts2);
        holes3.push(a > 0 ? h.pts3.slice().reverse() : h.pts3.slice());
        holes2.push(a > 0 ? h.pts2.slice().reverse() : h.pts2.slice());
      });
      const flat = [];
      const holeIdx = [];
      outer2.forEach((q) => { flat.push(q[0], q[1]); });
      holes2.forEach((h) => {
        holeIdx.push(flat.length / 2);
        h.forEach((q) => { flat.push(q[0], q[1]); });
      });
      const trisIdx = earcutFn(flat, holeIdx, 2);
      const pts3 = outer3.concat(...holes3);
      const pts2 = outer2.concat(...holes2);
      const base = positions.length / 3;
      pts3.forEach((p, i) => {
        positions.push(p[0] - n[0] * offset, p[1] - n[1] * offset, p[2] - n[2] * offset);
        uvs.push(pts2[i][0] * uvScale, pts2[i][1] * uvScale);
        normals.push(n[0], n[1], n[2]);
      });
      const outerAbs = Math.abs(outerA) || 1;
      const boreHoles = holes2.filter((h) => Math.abs(area2(h)) > outerAbs * 0.05);
      let area = 0;
      for (let i = 0; i < trisIdx.length; i += 3) {
        const ia = trisIdx[i] * 2, ib = trisIdx[i + 1] * 2, ic = trisIdx[i + 2] * 2;
        const ax = flat[ia], ay = flat[ia + 1], bx = flat[ib], by = flat[ib + 1], cx = flat[ic], cy = flat[ic + 1];
        const ta = triArea2(ax, ay, bx, by, cx, cy);
        if (ta < 1e-10) continue;
        const mx = (ax + bx + cx) / 3, my = (ay + by + cy) / 3;
        let inBore = false;
        for (let h = 0; h < boreHoles.length; h++) {
          if (pip(mx, my, boreHoles[h])) { inBore = true; break; }
        }
        if (inBore) continue;
        indices.push(base + trisIdx[i], base + trisIdx[i + 1], base + trisIdx[i + 2]);
        area += ta;
      }
      holeCount += g.holes.length;
      solids.push({ area, holeCount: g.holes.length });
    });

    return {
      solidCount: solids.length,
      holeCount,
      solids,
      solidArea: solids.reduce((s, x) => s + x.area, 0),
      positions,
      indices,
      uvs,
      normals,
      plane,
    };
  }

  function readStl(buf) {
    const dv = new DataView(buf);
    const n = dv.getUint32(80, true);
    const tris = [];
    let o = 84;
    for (let i = 0; i < n; i++) {
      o += 12;
      const t = [];
      for (let v = 0; v < 3; v++) {
        t.push([dv.getFloat32(o, true), dv.getFloat32(o + 4, true), dv.getFloat32(o + 8, true)]);
        o += 12;
      }
      o += 2;
      tris.push(t);
    }
    return tris;
  }

  function readObj(text) {
    const vs = [null];
    const vns = [null];
    const triangles = [];
    const pos = [];
    const nrm = [];
    const lines = String(text).split(/\r?\n/);
    for (let li = 0; li < lines.length; li++) {
      const line = lines[li];
      if (!line || line.charCodeAt(0) === 35) continue;
      if (line.startsWith("v ")) {
        const a = line.split(/\s+/);
        vs.push([+a[1], +a[2], +a[3]]);
      } else if (line.startsWith("vn ")) {
        const a = line.split(/\s+/);
        vns.push([+a[1], +a[2], +a[3]]);
      } else if (line.startsWith("f ")) {
        const parts = line.trim().split(/\s+/).slice(1);
        const verts = parts.map((tok) => {
          const bits = tok.split("/");
          let vi = +bits[0];
          let ni = bits.length > 2 && bits[2] !== "" ? +bits[2] : 0;
          if (vi < 0) vi = vs.length + vi;
          if (ni < 0) ni = vns.length + ni;
          return { vi, ni };
        });
        for (let i = 1; i + 1 < verts.length; i++) {
          const a = verts[0], b = verts[i], c = verts[i + 1];
          const pa = vs[a.vi], pb = vs[b.vi], pc = vs[c.vi];
          if (!pa || !pb || !pc) continue;
          triangles.push([pa, pb, pc]);
          let na = a.ni ? vns[a.ni] : null;
          let nb = b.ni ? vns[b.ni] : null;
          let nc = c.ni ? vns[c.ni] : null;
          if (!na || !nb || !nc) {
            const ax = pb[0] - pa[0], ay = pb[1] - pa[1], az = pb[2] - pa[2];
            const bx = pc[0] - pa[0], by = pc[1] - pa[1], bz = pc[2] - pa[2];
            let nx = ay * bz - az * by, ny = az * bx - ax * bz, nz = ax * by - ay * bx;
            const len = Math.hypot(nx, ny, nz) || 1;
            na = nb = nc = [nx / len, ny / len, nz / len];
          }
          pos.push(pa[0], pa[1], pa[2], pb[0], pb[1], pb[2], pc[0], pc[1], pc[2]);
          nrm.push(na[0], na[1], na[2], nb[0], nb[1], nb[2], nc[0], nc[1], nc[2]);
        }
      }
    }
    return {
      triangles,
      positions: new Float32Array(pos),
      normals: new Float32Array(nrm),
    };
  }

  const api = { buildSection, midPlane, bboxOf, readStl, readObj };
  global.MarmotSection = api;
  if (typeof module === "object" && module.exports) {
    module.exports = api;
    if (typeof require === "function" && require.main === module) {
      const fs = require("fs");
      const chunks = [];
      process.stdin.on("data", (c) => chunks.push(c));
      process.stdin.on("end", () => {
        const raw = Buffer.concat(chunks).toString("utf8");
        const msg = JSON.parse(raw);
        let tris = msg.triangles;
        if (msg.objPath) {
          tris = readObj(fs.readFileSync(msg.objPath, "utf8")).triangles;
        } else if (msg.stlPath) {
          const buf = fs.readFileSync(msg.stlPath);
          tris = readStl(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
        }
        const plane = msg.plane || midPlane(tris);
        const out = buildSection(tris, plane);
        const slim = {
          solidCount: out.solidCount,
          holeCount: out.holeCount,
          solidArea: out.solidArea,
          solids: out.solids,
          vertexCount: out.positions.length / 3,
          indexCount: out.indices.length,
          plane: { n: out.plane.n, d: out.plane.d },
          size: out.plane.size,
        };
        process.stdout.write(JSON.stringify(slim));
      });
    }
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
