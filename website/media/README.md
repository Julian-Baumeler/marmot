# Media (test videos)

The site expects `/media/01-yg-1.mp4` … `/media/07-mf-7.mp4`.

Those files are **not in git**. Broken macOS absolute-path symlinks (`/Users/julian/Downloads/...`) were removed.

- **Production:** `server.py` serves the objects from S3 when `AWS_S3_BUCKET_NAME` / `BUCKET` is set.
- **Local:** copy the `.mp4` files into this folder, or point the same S3 env vars at the bucket.

Do not commit machine-specific symlinks.
