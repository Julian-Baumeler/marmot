"""Reverse proxy for /fixit/* -> the Fixit Silo-Karte service.

The Silo-Karte is built for base path "/", so absolute paths in its HTML/JS
(/assets/, /api/, /favicon.svg, /fixit-logo.svg, Vite's preload base) are
rewritten to /fixit/... so the browser only ever talks to this host.
"""
from __future__ import annotations

import gzip
import os
import re
import urllib.error
import urllib.request

PREFIX = "/fixit"
UPSTREAM = os.environ.get(
    "FIXIT_UPSTREAM", "https://fixit-silo-karte-production.up.railway.app"
).rstrip("/")
TIMEOUT = float(os.environ.get("FIXIT_TIMEOUT", "30"))

FORWARD_REQ = (
    "accept",
    "accept-language",
    "content-type",
    "x-edit-pin",
    "if-none-match",
    "if-modified-since",
    "range",
    "user-agent",
)
FORWARD_RESP = (
    "content-type",
    "cache-control",
    "etag",
    "last-modified",
    "content-range",
    "accept-ranges",
)

_HTML_ATTR = re.compile(r'((?:src|href)=["\'])/(?!/|fixit/)')
_JS_ABS = re.compile(r'([`"\'])/(api/|assets/|favicon\.svg|fixit-logo\.svg)')
_JS_PRELOAD = re.compile(r"return`/`\+")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def matches(path: str) -> bool:
    return path == PREFIX or path.startswith(PREFIX + "/")


def rewrite(body: bytes, ctype: str) -> bytes:
    ct = ctype.split(";")[0].strip().lower()
    if ct == "text/html":
        t = body.decode("utf-8", "replace")
        return _HTML_ATTR.sub(r"\1" + PREFIX + "/", t).encode("utf-8")
    if ct in ("text/javascript", "application/javascript"):
        t = body.decode("utf-8", "replace")
        t = _JS_ABS.sub(lambda m: m.group(1) + PREFIX + "/" + m.group(2), t)
        t = _JS_PRELOAD.sub("return`" + PREFIX + "/`+", t)
        return t.encode("utf-8")
    if ct == "text/css":
        t = body.decode("utf-8", "replace")
        return re.sub(r"url\((['\"]?)/(?!/)", r"url(\1" + PREFIX + "/", t).encode("utf-8")
    return body


def handle(h, method: str) -> None:
    """h is a BaseHTTPRequestHandler. Proxies one request."""
    raw = h.path
    path, _, query = raw.partition("?")
    if path == PREFIX:
        # Serve the app at /fixit too; assets are absolute so no redirect needed.
        path = PREFIX + "/"
    sub = path[len(PREFIX):] or "/"
    url = UPSTREAM + sub + (("?" + query) if query else "")

    body = None
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        n = int(h.headers.get("Content-Length") or 0)
        body = h.rfile.read(n) if n > 0 else b""

    req = urllib.request.Request(url, data=body, method=method)
    for k in FORWARD_REQ:
        v = h.headers.get(k)
        if v:
            req.add_header(k, v)
    req.add_header("Accept-Encoding", "identity")
    fwd = h.headers.get("X-Forwarded-For")
    client = h.client_address[0] if h.client_address else ""
    req.add_header("X-Forwarded-For", f"{fwd}, {client}" if fwd else client)
    req.add_header("X-Forwarded-Prefix", PREFIX)

    try:
        resp = _opener.open(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        resp = e
    except Exception as e:  # upstream down / timeout
        h.send_response(502)
        msg = f"fixit upstream error: {type(e).__name__}\n".encode()
        h.send_header("Content-Type", "text/plain; charset=utf-8")
        h.send_header("Content-Length", str(len(msg)))
        h.end_headers()
        if method != "HEAD":
            h.wfile.write(msg)
        return

    status = resp.status if hasattr(resp, "status") else resp.code
    data = resp.read() if method != "HEAD" else b""
    ctype = resp.headers.get("Content-Type", "")
    data = rewrite(data, ctype) if data else data

    gz = False
    if (
        data
        and len(data) > 1024
        and "gzip" in (h.headers.get("Accept-Encoding") or "")
        and ctype.split(";")[0].strip().lower()
        in ("text/html", "text/javascript", "application/javascript", "text/css", "application/json", "image/svg+xml")
    ):
        data = gzip.compress(data, 6)
        gz = True

    h.send_response(status)
    for k in FORWARD_RESP:
        v = resp.headers.get(k)
        if v:
            h.send_header(k, v)
    loc = resp.headers.get("Location")
    if loc:
        if loc.startswith(UPSTREAM):
            loc = loc[len(UPSTREAM):] or "/"
        if loc.startswith("/") and not loc.startswith("//"):
            loc = PREFIX + loc
        h.send_header("Location", loc)
    if gz:
        h.send_header("Content-Encoding", "gzip")
        h.send_header("Vary", "Accept-Encoding")
    if method == "HEAD":
        cl = resp.headers.get("Content-Length")
        if cl:
            h.send_header("Content-Length", cl)
    else:
        h.send_header("Content-Length", str(len(data)))
    h._fixit_proxied = True
    h.end_headers()
    if method != "HEAD" and data:
        h.wfile.write(data)
