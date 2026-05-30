# Oakridge Drawings

Pick a survey date → browse every drawing for that day → download them all
compiled (in name order) into one titled PDF.

Pulls live from `http://drawings.oakridge.smtresearch.ca/<DATE>/`.

## Run locally

```bash
pip install -r requirements.txt
DATA_DIR=./data python app.py        # http://localhost:8000
```

Or with Docker:

```bash
docker build -t oakridge-drawings .
docker run -p 8000:8000 -v oakridge_data:/data oakridge-drawings
```

## Deploy on Coolify

1. Push this folder to a Git repo (GitHub/GitLab/Gitea).
2. In Coolify: **New Resource → Application → from your repo**.
3. Build pack: **Dockerfile** (auto-detected).
4. Port: **8000** (Coolify reads `EXPOSE`; set it explicitly if asked).
5. **Persistent storage**: add a volume mounted at **`/data`** so downloaded
   images and generated PDFs survive restarts (otherwise they're re-fetched).
6. (Optional) Env vars:
   - `OAKRIDGE_HOST` — source server (default `http://drawings.oakridge.smtresearch.ca`)
   - `DATA_DIR` — cache dir inside the container (default `/data`)
7. Deploy. Coolify handles HTTPS via its proxy.

Health check is at `/healthz`.

## Notes

- First PDF for a given day takes a moment (downloads ~150 images, then
  renders). It's cached on the `/data` volume, so repeats are instant.
- Images are proxied through the app so the page works over HTTPS even though
  the source server is plain HTTP (avoids mixed-content blocking).
