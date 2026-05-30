# oakridge-drawings

Tools for the Oakridge drawing index at
`http://drawings.oakridge.smtresearch.ca/<DATE>/`.

## `oakridge-drawings-site/` — the web app (deploy this)

A small Flask app: pick a survey day from a **calendar**, browse every drawing
in a zoom/pan **viewer**, and download them all compiled into one titled
**PDF** (in name order). Images are proxied so it works over HTTPS.

See [`oakridge-drawings-site/README.md`](oakridge-drawings-site/README.md) for
full details.

### Deploy on Coolify

- New Resource → Application → from this repo
- Build pack: **Dockerfile** (root `Dockerfile` builds the app — no base
  directory config needed)
- Port: **8000**
- Add a persistent volume mounted at **`/data`** (caches images + PDFs)

## `oakridge_2026-05-26/make_drawings_pdf.py` — standalone CLI

Same PDF compile, no server:

```bash
python3 make_drawings_pdf.py 2026-05-26   # any date; omit for today
```
# oakridge
