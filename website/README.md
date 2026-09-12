# Website (rocketengine.ch / Triebwerkstests)

Presentation companion for the Marmot engine tests: slides in `index.html`, figures, posters, and clip metadata.

Test videos (`media/*.mp4`) are **not stored in git**. In production, `server.py` streams them from S3 when the bucket env vars are set. See [media/README.md](media/README.md).

## Run locally

```bash
cd website
python3 -m pip install -r requirements.txt   # only needed for S3 video
python3 server.py                            # http://127.0.0.1:8765/
```

`PORT` / `HOST` override the bind address. Without S3 credentials, `/media/*.mp4` 404s unless you place real files in `media/`.

## Deploy (Railway)

Keep this folder as the service root so `Dockerfile`, `Procfile`, and `server.py` stay together.

1. Railway → service → **Settings → Root Directory** → `website`
2. Deploy uses the `Dockerfile` (or the `Procfile` `web:` process)
3. For videos, set `AWS_S3_BUCKET_NAME` (or `BUCKET`) plus the usual AWS key / endpoint / region vars

`.dockerignore` skips `media/*.mp4` so large clips are not baked into the image.
