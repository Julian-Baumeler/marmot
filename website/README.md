# Website (rocketengine.ch / Triebwerkstests)

Presentation companion for the Marmot engine tests: slides in `index.html`, figures, posters, and clip metadata.

Deck figures always use `object-fit: contain` with a dark letterbox so photos are never cropped. Browsers also honor EXIF via `image-orientation: from-image`; figure files themselves are stored with normal pixel orientation.

Test videos (`media/*.mp4`) are stored with Git LFS. The Docker image downloads the clips the pages play; `server.py` streams any missing clip from S3 when the bucket env vars are set. See [media/README.md](media/README.md).

## Run locally

```bash
cd website
python3 -m pip install -r requirements.txt   # only needed for S3 video
python3 server.py                            # http://127.0.0.1:8765/
```

`PORT` / `HOST` override the bind address. `python3 fetch_media.py` downloads the clips into `media/`. Without those files or S3 credentials, `/media/*.mp4` 404s.

## Präsentationsmodus (JPSM)

`/?mode=präsi` öffnen, oder **Präsi** in der Seitenleiste / Taste **P**. Die erste Folie ist die Leitfrage. Das Inhaltsverzeichnis folgt den Themen: Einleitung, Ventile (M), Schubmessen (P), Brennkammer (J), Tests (ALLE), Schluss. Ohne Präsi-Modus bleibt die Titelfolie die Startseite.

Figures fill the remaining slide (`object-fit: contain`, dark letterbox, no crop). Portrait photos sit in a tall column so they stay large.

## Deploy (Railway)

Keep this folder as the service root so `Dockerfile`, `Procfile`, and `server.py` stay together.

1. Railway → service → **Settings → Root Directory** → `website`
2. Deploy uses the `Dockerfile` (`railway.toml`). That build runs `fetch_media.py`, which downloads the clips referenced by `index.html` and `slides.html` from GitHub into the image. No bucket, volume, or other Railway setting is required.
3. Optional: `AWS_S3_BUCKET_NAME` (or `BUCKET`) plus the usual AWS key / endpoint / region vars still supply a clip when the local file is missing.

`.dockerignore` still skips `media/*.mp4` so Git LFS pointer stubs are not copied over the downloaded files.
