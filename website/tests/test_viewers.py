#!/usr/bin/env python3
"""Drive the shipped 3D overlay — vtk.js only, CUT swaps Engine2-cut.obj."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
VIEWERS = ROOT / "viewers"
CUT_OBJ = ROOT / "models" / "Engine2-cut.obj"
FULL_OBJ = ROOT / "models" / "Engine2.obj"


def html() -> str:
    return INDEX.read_text(encoding="utf-8")


class OverlayVtkOnly(unittest.TestCase):
    def test_single_vtk_iframe(self):
        text = html()
        iframes = re.findall(r'<iframe data-src="([^"]+)"', text)
        self.assertEqual(len(iframes), 1, iframes)
        self.assertIn("viewers/vtk.html", iframes[0])
        self.assertNotIn("three.html", text)
        self.assertNotIn("babylon.html", text)
        self.assertIn("id=\"btn-cut\"", text)
        self.assertIn("Section view", text)
        self.assertIn("body.view3d #btn-cut", text)
        self.assertIn("postMessage", text)
        vtk = (VIEWERS / "vtk.html").read_text(encoding="utf-8")
        self.assertNotIn("Click a part to copy", vtk)
        self.assertNotIn('id="copied"', vtk)
        self.assertNotIn("copyPick", vtk)
        self.assertNotIn("pick-copy", text)
        self.assertIn("Raketentriebwerk.pdf", text)
        self.assertIn("engine2-data.js", vtk)
        self.assertIn("data.cut", vtk)
        self.assertIn("watchCut", vtk)
        self.assertIn("vtk", vtk.lower())
        data_js = (VIEWERS / "engine2-data.js").read_text(encoding="utf-8")
        self.assertIn("Engine2.obj", data_js)
        self.assertIn("Engine2-cut.obj", data_js)
        self.assertIn("watchCut", data_js)
        self.assertNotIn("keepHalf", data_js)
        self.assertNotIn("buildSection", data_js)
        self.assertNotIn("debugHoles", data_js)
        self.assertNotIn("?v=hires", data_js)
        self.assertNotIn("?v=hires", text)
        cut_head = CUT_OBJ.read_text(encoding="utf-8", errors="replace")[:200]
        self.assertNotIn("hires smooth", cut_head)
        self.assertLess(CUT_OBJ.stat().st_size, 800_000, CUT_OBJ.stat().st_size)
        nfaces = sum(1 for line in CUT_OBJ.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("f "))
        self.assertGreater(nfaces, 1000, nfaces)
        self.assertLess(nfaces, 8000, nfaces)

    def test_cut_obj_is_midplane_half(self):
        self.assertTrue(FULL_OBJ.is_file(), FULL_OBJ)
        self.assertTrue(CUT_OBJ.is_file(), CUT_OBJ)
        obj = CUT_OBJ.read_text(encoding="utf-8", errors="replace")
        self.assertIn("\nv ", obj)
        self.assertIn("\nf ", obj)
        ys = []
        for line in obj.splitlines():
            if line.startswith("v "):
                ys.append(float(line.split()[2]))
        self.assertTrue(ys)
        # mid-plane half: one side of Y=0, the other is the remaining solid
        self.assertTrue(max(ys) < 1.0 or min(ys) > -1.0, (min(ys), max(ys)))
        self.assertGreater(max(ys) - min(ys), 10.0)


class ViewerHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        port = "8777"
        env = os.environ.copy()
        env["PORT"] = port
        env["HOST"] = "127.0.0.1"
        cls.base = f"http://127.0.0.1:{port}"
        cls.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "server.py")],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 8
        last = None
        while time.time() < deadline:
            try:
                urllib.request.urlopen(cls.base + "/", timeout=1)
                return
            except Exception as e:
                last = e
                time.sleep(0.15)
        cls.proc.kill()
        raise RuntimeError(f"server did not start: {last}")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=2)
        except Exception:
            cls.proc.kill()

    def test_index_and_vtk(self):
        r = urllib.request.urlopen(self.base + "/", timeout=5)
        self.assertEqual(r.status, 200)
        text = html()
        srcs = re.findall(r'<iframe data-src="([^"]+)"', text)
        self.assertEqual(len(srcs), 1, srcs)
        vr = urllib.request.urlopen(self.base + "/" + srcs[0], timeout=5)
        self.assertEqual(vr.status, 200, srcs[0])
        for path in ("/models/Engine2.obj", "/models/Engine2-cut.obj"):
            pr = urllib.request.urlopen(self.base + path, timeout=5)
            self.assertEqual(pr.status, 200, path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
