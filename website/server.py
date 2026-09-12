#!/usr/bin/env python3
"""Threading HTTP server with byte-range support. Local files, or S3 for /media/*.mp4."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http import HTTPStatus
import os
import re
import sys
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")

S3_BUCKET = os.environ.get("AWS_S3_BUCKET_NAME") or os.environ.get("BUCKET")
S3_ENDPOINT = os.environ.get("AWS_ENDPOINT_URL") or os.environ.get("AWS_S3_ENDPOINT")
S3_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
S3_SECRET = os.environ.get("AWS_SECRET_ACCESS_KEY")
S3_REGION = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or "ams"
_s3 = None


def s3():
    global _s3
    if _s3 is None:
        import boto3
        kwargs = {"region_name": S3_REGION}
        if S3_ENDPOINT:
            kwargs["endpoint_url"] = S3_ENDPOINT
        if S3_KEY and S3_SECRET:
            kwargs["aws_access_key_id"] = S3_KEY
            kwargs["aws_secret_access_key"] = S3_SECRET
        _s3 = boto3.client("s3", **kwargs)
    return _s3


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".mp4": "video/mp4",
        ".jpg": "image/jpeg",
        ".html": "text/html; charset=utf-8",
    }

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        if self.path.split("?", 1)[0].endswith(".mp4"):
            self.send_header("Cache-Control", "public, max-age=86400")
        super().end_headers()

    def _parse_range(self, size):
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        status = HTTPStatus.OK
        if rng:
            m = RANGE_RE.match(rng.strip())
            if not m:
                return None
            a, b = m.group(1), m.group(2)
            if a and b:
                start, end = int(a), int(b)
            elif a:
                start, end = int(a), size - 1
            elif b:
                start, end = max(size - int(b), 0), size - 1
            if start >= size or start > end:
                return "unsat"
            end = min(end, size - 1)
            status = HTTPStatus.PARTIAL_CONTENT
        return start, end, status

    def do_GET(self):
        path = urlparse(self.path).path
        if S3_BUCKET and path.startswith("/media/") and path.endswith(".mp4"):
            key = unquote(path.lstrip("/"))
            try:
                head = s3().head_object(Bucket=S3_BUCKET, Key=key)
            except Exception:
                self.send_error(HTTPStatus.NOT_FOUND, "File not found")
                return
            size = int(head["ContentLength"])
            parsed = self._parse_range(size)
            if parsed is None:
                self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return
            if parsed == "unsat":
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            start, end, status = parsed
            length = end - start + 1
            kwargs = {"Bucket": S3_BUCKET, "Key": key}
            if status == HTTPStatus.PARTIAL_CONTENT:
                kwargs["Range"] = f"bytes={start}-{end}"
            obj = s3().get_object(**kwargs)
            self.send_response(status)
            self.send_header("Content-type", "video/mp4")
            self.send_header("Content-Length", str(length))
            if status == HTTPStatus.PARTIAL_CONTENT:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            body = obj["Body"]
            remaining = length
            while remaining > 0:
                chunk = body.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)
            return
        super().do_GET()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        if path.endswith("/"):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            fs = os.fstat(f.fileno())
            size = fs.st_size
            ctype = self.guess_type(path)
            parsed = self._parse_range(size)
            if parsed is None:
                f.close()
                self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return None
            if parsed == "unsat":
                f.close()
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            start, end, status = parsed
            length = end - start + 1 if size else 0
            f.seek(start)
            self._range_len = length
            self.send_response(status)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(length))
            if status == HTTPStatus.PARTIAL_CONTENT:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except Exception:
            f.close()
            raise

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_range_len", None)
        if remaining is None:
            super().copyfile(source, outputfile)
            return
        while remaining > 0:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else "8765"))
    host = os.environ.get("HOST", "0.0.0.0")
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"http://{host}:{port}/ s3={bool(S3_BUCKET)}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstop", flush=True)
