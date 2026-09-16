#!/usr/bin/env python3
"""Drive the shipped website/section.js builder — annulus + Engine2.obj."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTION_JS = ROOT / "section.js"
ENGINE_OBJ = ROOT / "models" / "Engine2.obj"


def build_section(triangles=None, plane=None, stl_path=None, obj_path=None):
    """Call the shipped section.js (stdin JSON → stdout JSON)."""
    payload = {}
    if triangles is not None:
        payload["triangles"] = triangles
    if plane is not None:
        payload["plane"] = plane
    if obj_path is not None:
        payload["objPath"] = str(obj_path)
    if stl_path is not None:
        payload["stlPath"] = str(stl_path)
    proc = subprocess.run(
        ["node", str(SECTION_JS)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"exit {proc.returncode}")
    return json.loads(proc.stdout)


def annular_pipe(r_out=10.0, r_in=6.0, length=4.0, segs=64):
    """Closed pipe along Z; smallest bbox axis is Z so mid-plane is a ring."""
    tris = []
    z0, z1 = -length / 2, length / 2

    def ring(rad, z):
        return [
            [rad * math.cos(i / segs * 2 * math.pi), rad * math.sin(i / segs * 2 * math.pi), z]
            for i in range(segs)
        ]

    def quad(a, b, c, d):
        tris.append([a, b, c])
        tris.append([a, c, d])

    o0, o1 = ring(r_out, z0), ring(r_out, z1)
    i0, i1 = ring(r_in, z0), ring(r_in, z1)
    for i in range(segs):
        j = (i + 1) % segs
        quad(o0[i], o0[j], o1[j], o1[i])
        quad(i0[j], i0[i], i1[i], i1[j])
    return tris, r_out, r_in


class SectionBuilder(unittest.TestCase):
    def test_annulus_midplane_is_filled_ring_with_hole(self):
        tris, r_out, r_in = annular_pipe()
        out = build_section(triangles=tris)
        self.assertEqual(out["solidCount"], 1, out)
        self.assertGreaterEqual(out["holeCount"], 1, out)
        self.assertEqual(out["solids"][0]["holeCount"], 1, out)
        area = out["solidArea"]
        inner = math.pi * r_in * r_in
        outer = math.pi * r_out * r_out
        self.assertGreater(area, inner, f"ring area {area} should exceed inner disk {inner}")
        self.assertLess(area, outer, f"ring area {area} should be below outer disk {outer}")
        self.assertGreater(out["indexCount"], 0)

    def test_engine2_midplane_has_metal_and_air(self):
        self.assertTrue(ENGINE_OBJ.is_file(), ENGINE_OBJ)
        text = ENGINE_OBJ.read_text(encoding="utf-8", errors="replace")
        self.assertIn("\nv ", text)
        self.assertIn("\nf ", text)
        out = build_section(obj_path=ENGINE_OBJ)
        self.assertGreaterEqual(out["solidCount"], 1, out)
        self.assertGreater(out["solidArea"], 0, out)
        self.assertGreater(out["vertexCount"], 0, out)
        self.assertGreater(out["indexCount"], 0, out)
        # Longitudinal mid-plane: hatched wall islands, cavities are the empty
        # space between them (Image-1 cutaway), not always nested 2D holes.
        self.assertTrue(
            out["holeCount"] >= 1 or out["solidCount"] >= 2,
            out,
        )
        n = out["plane"]["n"]
        sx, sy, sz = out["size"]
        if abs(n[0]) > 0.5:
            face = sy * sz
        elif abs(n[1]) > 0.5:
            face = sx * sz
        else:
            face = sx * sy
        self.assertLess(out["solidArea"], 0.55 * face, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
