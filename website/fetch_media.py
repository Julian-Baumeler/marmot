#!/usr/bin/env python3
"""Put real hotfire MP4s into the image.

Railway clones this repo without Git LFS, and `.dockerignore` /
`.railwayignore` omit `media/*.mp4`, so the deployed tree has no video
bytes and `server.py` returns 404. The objects are public on GitHub's
media CDN (the same bytes as the LFS pointers). Download the clips that
`index.html` and `slides.html` actually reference.

A file already on disk is kept when it is a real MP4, so a local checkout
with `git lfs pull` is not replaced.
"""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

REPO = "Julian-Baumeler/marmot"
# Every media/*.mp4 referenced by index.html or slides.html.
FILES = (
    "02-yg-2.mp4",
    "04-mg-4.mp4",
    "05-mf-5.mp4",
    "06-mf-6.mp4",
    "06-mf-6a.mp4",
    "06-mf-6b.mp4",
    "06-mf-6c.mp4",
    "07-mf-7.mp4",
)
LFS_PREFIX = b"version https://git-lfs.github.com/spec/v1"
HERE = os.path.dirname(os.path.abspath(__file__))


def is_real_mp4(path: str) -> bool:
    """True for a playable MP4, false for a missing file or an LFS pointer."""
    try:
        if os.path.getsize(path) < 1024:
            return False
        with open(path, "rb") as fh:
            head = fh.read(64)
    except OSError:
        return False
    if head.startswith(LFS_PREFIX):
        return False
    return b"ftyp" in head


def media_url(ref: str, name: str) -> str:
    return (
        "https://media.githubusercontent.com/media/"
        f"{REPO}/{ref}/website/media/{name}"
    )


def download(url: str, dest: str) -> None:
    tmp = dest + ".partial"
    req = urllib.request.Request(url, headers={"User-Agent": "marmot-fetch-media"})
    try:
        resp = urllib.request.urlopen(req, timeout=300)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"download failed {url}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"download failed {url}: {exc.reason}") from exc
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    expected = resp.headers.get("Content-Length")
    written = 0
    try:
        with resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                written += len(chunk)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    if expected is not None and written != int(expected):
        os.remove(tmp)
        raise SystemExit(f"{url} truncated: got {written} of {expected} bytes")
    os.replace(tmp, dest)
    if not is_real_mp4(dest):
        raise SystemExit(f"{dest} is not an MP4 after download ({written} bytes)")


def fetch(ref: str, dest_dir: str) -> None:
    ref = (ref or "").strip() or "master"
    for name in FILES:
        dest = os.path.join(dest_dir, name)
        if is_real_mp4(dest):
            print(f"keep {name} ({os.path.getsize(dest)} bytes)", flush=True)
            continue
        url = media_url(ref, name)
        print(f"fetch {name} from {ref}", flush=True)
        download(url, dest)
        print(f"ok {name} {os.path.getsize(dest)} bytes", flush=True)


def main(argv: list[str]) -> None:
    ref = "master"
    dest_dir = os.path.join(HERE, "media")
    args = argv[1:]
    if args and args[0] == "--dest":
        if len(args) < 2:
            raise SystemExit("usage: fetch_media.py [--dest DIR] [GIT_REF]")
        dest_dir = args[1]
        args = args[2:]
    if args:
        ref = args[0]
    fetch(ref, dest_dir)


if __name__ == "__main__":
    main(sys.argv)
