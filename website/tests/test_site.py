#!/usr/bin/env python3
"""Drive the shipped website files — orientation, size, unused figures, HTTP."""
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
FIG = ROOT / "figures"


def html() -> str:
    return INDEX.read_text(encoding="utf-8")


def referenced_paths(text: str) -> set[str]:
    found = set(re.findall(r'(?:src|poster)=["\']([^"\']+)["\']', text))
    found |= set(re.findall(r'href=["\']([^"\']+\.pdf)["\']', text))
    return {u.split("?")[0] for u in found if u and not u.startswith(("http", "about:"))}


class TankOrientation(unittest.TestCase):
    def test_wood_is_in_the_bottom_third(self):
        text = html()
        m = re.search(r'<img[^>]+src=["\'](figures/[^"\']+)["\'][^>]*alt="Drucktank"', text)
        self.assertIsNotNone(m, "Drucktank img missing")
        path = ROOT / m.group(1)
        self.assertTrue(path.is_file(), path)
        from PIL import Image

        im = Image.open(path).convert("RGB")
        w, h = im.size
        pix = im.load()

        def wood_frac(y0, y1):
            n = hits = 0
            for y in range(y0, y1):
                for x in range(0, w, 3):
                    r, g, b = pix[x, y]
                    n += 1
                    if 90 < r < 210 and 50 < g < 170 and b < 120 and r > g + 10 and g > b:
                        hits += 1
            return hits / n if n else 0.0

        top = wood_frac(0, h // 3)
        bot = wood_frac(2 * h // 3, h)
        self.assertGreater(bot, top, f"wood top={top:.4f} bot={bot:.4f} — tank still inverted")
        self.assertGreater(bot, 0.03, f"too little wood at bottom ({bot:.4f})")


class Simplicity(unittest.TestCase):
    def test_fewer_sections_and_lines_than_the_dump(self):
        text = html()
        lines = text.count("\n") + 1
        sections = text.count("<section")
        self.assertLess(sections, 19, sections)
        self.assertLess(lines, 643, lines)

    def test_no_unused_figure_files(self):
        used = referenced_paths(html())
        leftover = []
        if FIG.is_dir():
            for p in sorted(FIG.iterdir()):
                if p.is_file() and f"figures/{p.name}" not in used:
                    leftover.append(p.name)
        self.assertEqual(leftover, [], f"unused figures: {leftover}")

    def test_hero_is_mf6_and_plain_script(self):
        text = html()
        self.assertIn("media/06-mf-6.mp4", text)
        self.assertIn("<script>", text)
        self.assertNotIn('type="module"', text)
        self.assertIn('id="btn-menu"', text)
        self.assertIn("transform:translateX(-105%)", text.replace(" ", ""))


class HttpSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        port = "8769"
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

    def test_index_and_tank(self):
        text = html()
        r = urllib.request.urlopen(self.base + "/", timeout=5)
        body = r.read()
        self.assertEqual(r.status, 200)
        self.assertIn(b"<title>Raketentriebwerk", body)
        self.assertIn(b"media/06-mf-6.mp4", body)
        self.assertIn(b"figures/emb-051.png", body)
        tank = urllib.request.urlopen(self.base + "/figures/emb-051.png", timeout=5)
        self.assertEqual(tank.status, 200)
        self.assertGreater(int(tank.headers.get("Content-Length") or 0), 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
