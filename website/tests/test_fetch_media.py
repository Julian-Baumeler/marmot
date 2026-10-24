#!/usr/bin/env python3
"""The image fetch list is exactly the clips the pages request."""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fetch_media  # noqa: E402


def referenced_mp4s() -> set[str]:
    found: set[str] = set()
    for name in ("index.html", "slides.html"):
        text = (ROOT / name).read_text(encoding="utf-8")
        found |= set(re.findall(r"media/([A-Za-z0-9._-]+\.mp4)", text))
    return found


class FetchList(unittest.TestCase):
    def test_covers_every_page_clip(self):
        self.assertEqual(referenced_mp4s(), set(fetch_media.FILES))

    def test_pointer_and_tiny_file_are_not_mp4(self):
        with tempfile.TemporaryDirectory() as tmp:
            pointer = os.path.join(tmp, "pointer.mp4")
            tiny = os.path.join(tmp, "tiny.mp4")
            real = os.path.join(tmp, "real.mp4")
            Path(pointer).write_bytes(
                b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 10\n"
                + b"\0" * 1100
            )
            Path(tiny).write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\0" * 8)
            Path(real).write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\0" * 1200)
            self.assertFalse(fetch_media.is_real_mp4(pointer))
            self.assertFalse(fetch_media.is_real_mp4(tiny))
            self.assertTrue(fetch_media.is_real_mp4(real))
            self.assertFalse(fetch_media.is_real_mp4(os.path.join(tmp, "missing.mp4")))


if __name__ == "__main__":
    unittest.main()
