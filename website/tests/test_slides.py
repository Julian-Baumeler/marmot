#!/usr/bin/env python3
"""JPSM /slides deck: seven slides, Ventile from Mateusz, fat titles elsewhere."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLIDES = ROOT / "slides.html"
SERVER = ROOT / "server.py"


class SlidesDeck(unittest.TestCase):
    def test_seven_jpsm_titles_and_ventile_photos(self):
        text = SLIDES.read_text(encoding="utf-8")
        for title in ("Leitfrage", "Einleitung", "Ventile", "Schubmessen", "Brennkammer", "Tests", "Schluss"):
            self.assertIn(title, text)
        self.assertIn("Mateusz Wnuk", text)
        self.assertIn("Elektronische Kugelhähne", text)
        self.assertIn("figures/emb-034.png", text)
        self.assertIn("figures/emb-036.png", text)
        self.assertIn("figures/emb-038.png", text)
        self.assertEqual(text.count('class="slide'), 7)
        self.assertIn('id="btn-full"', text)
        self.assertIn("requestFullscreen", text)
        self.assertIn('id="btn-exit"', text)
        self.assertIn('href="/"', text)
        for name in ("emb-034.png", "emb-036.png", "emb-038.png"):
            self.assertTrue((ROOT / "figures" / name).is_file(), name)

    def test_server_rewrites_slides_path(self):
        src = SERVER.read_text(encoding="utf-8")
        self.assertIn("/slides", src)
        self.assertIn("slides.html", src)
