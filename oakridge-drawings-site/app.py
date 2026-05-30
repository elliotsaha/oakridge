#!/usr/bin/env python3
"""
Oakridge Drawings — web front-end.

Pick a survey date, browse every drawing for that day, and download them all
compiled (in name order) into a single titled PDF.

Backed by the public index at http://drawings.oakridge.smtresearch.ca/<DATE>/
"""
import os
import re
import html
import ssl
import urllib.parse
import urllib.request

from flask import Flask, render_template, abort, send_file, Response

BASE_HOST = os.environ.get(
    "OAKRIDGE_HOST", "http://drawings.oakridge.smtresearch.ca"
).rstrip("/")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

app = Flask(__name__)

# SSL context that tolerates the source server's cert quirks
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


# --------------------------------------------------------------------------- #
#  Source-server helpers
# --------------------------------------------------------------------------- #
def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "oakridge-drawings/1.0"})
    return urllib.request.urlopen(req, context=_CTX, timeout=timeout)


def list_dates():
    """Available survey dates on the source server, newest first."""
    try:
        with _get(f"{BASE_HOST}/") as r:
            text = r.read().decode("utf-8", "replace")
    except Exception:
        return []
    dates = sorted(set(re.findall(r'href="(\d{4}-\d{2}-\d{2})/"', text)), reverse=True)
    return dates


def list_images(date):
    """List of dicts {href, name, title} for every jpg on the given day."""
    with _get(f"{BASE_HOST}/{date}/") as r:
        text = r.read().decode("utf-8", "replace")
    hrefs = re.findall(r'href="([^"]+\.jpg)"', text, flags=re.IGNORECASE)
    items = []
    for h in hrefs:
        name = urllib.parse.unquote(html.unescape(h))
        title = name.rsplit("_" + date, 1)[0] if ("_" + date) in name else \
            name.rsplit(".jpg", 1)[0]
        items.append({"href": h, "name": name, "title": title})
    items.sort(key=lambda it: it["name"].lower())
    return items


def image_bytes(date, name):
    """Fetch one image, caching to disk. Returns (bytes, content_type)."""
    safe = name.replace("/", "_")
    cache_dir = os.path.join(DATA_DIR, date, "images")
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, safe)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            return f.read(), "image/jpeg"
    # name is already decoded; re-encode for the request (& -> %26, space -> %20)
    url = f"{BASE_HOST}/{date}/{urllib.parse.quote(name)}"
    with _get(url, timeout=120) as r:
        data = r.read()
    if data:
        with open(path, "wb") as f:
            f.write(data)
    return data, "image/jpeg"


# --------------------------------------------------------------------------- #
#  PDF builder
# --------------------------------------------------------------------------- #
def build_pdf(date):
    """Build (or reuse cached) PDF for a date. Returns the file path."""
    out_dir = os.path.join(DATA_DIR, date)
    os.makedirs(out_dir, exist_ok=True)
    out_pdf = os.path.join(out_dir, f"Oakridge_Drawings_{date}.pdf")

    items = list_images(date)
    if not items:
        return None

    # rebuild if missing or older than the cached image set
    if os.path.exists(out_pdf) and os.path.getsize(out_pdf) > 0:
        return out_pdf

    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from PIL import Image

    # ensure all images are on disk
    paths = []
    for it in items:
        data, _ = image_bytes(date, it["name"])
        if not data:
            continue
        paths.append((it["title"], os.path.join(DATA_DIR, date, "images",
                                                 it["name"].replace("/", "_"))))

    PAGE = landscape(letter)
    W, H = PAGE
    c = canvas.Canvas(out_pdf, pagesize=PAGE)

    # cover
    c.setFillColorRGB(0.1, 0.12, 0.15)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(W / 2, H / 2 + 40, "Oakridge Drawings")
    c.setFont("Helvetica", 20)
    c.drawCentredString(W / 2, H / 2, f"Survey Date: {date}")
    c.setFont("Helvetica", 14)
    c.drawCentredString(W / 2, H / 2 - 30,
                        f"{len(paths)} drawings  ·  compiled in name order")
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(W / 2, 0.6 * inch,
                        f"Source: {BASE_HOST.split('//')[-1]}/{date}")
    c.showPage()

    M = 0.4 * inch
    HDR = 0.5 * inch
    for i, (title, p) in enumerate(paths, 1):
        c.setFillColorRGB(0.12, 0.45, 0.62)
        c.rect(0, H - HDR, W, HDR, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(M, H - HDR + 0.16 * inch, title)
        c.setFont("Helvetica", 9)
        c.drawRightString(W - M, H - HDR + 0.16 * inch, f"{i} / {len(paths)}")
        try:
            iw, ih = Image.open(p).size
        except Exception:
            c.showPage()
            continue
        avail_w, avail_h = W - 2 * M, H - HDR - 2 * M
        s = min(avail_w / iw, avail_h / ih)
        dw, dh = iw * s, ih * s
        x = (W - dw) / 2
        y = M + (avail_h - dh) / 2
        c.drawImage(ImageReader(p), x, y, dw, dh,
                    preserveAspectRatio=True, anchor="c")
        c.showPage()
    c.save()
    return out_pdf


# --------------------------------------------------------------------------- #
#  Routes
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return render_template("index.html", dates=list_dates(), host=BASE_HOST)


@app.route("/d/<date>")
def gallery(date):
    if not DATE_RE.match(date):
        abort(404)
    try:
        items = list_images(date)
    except Exception:
        items = None
    if not items:
        return render_template("empty.html", date=date), 404
    return render_template("gallery.html", date=date, items=items)


@app.route("/img/<date>/<path:name>")
def img(date, name):
    if not DATE_RE.match(date):
        abort(404)
    try:
        data, ctype = image_bytes(date, name)
    except Exception:
        abort(502)
    if not data:
        abort(404)
    return Response(data, mimetype=ctype,
                    headers={"Cache-Control": "public, max-age=86400"})


@app.route("/pdf/<date>")
def pdf(date):
    if not DATE_RE.match(date):
        abort(404)
    path = build_pdf(date)
    if not path or not os.path.exists(path):
        return render_template("empty.html", date=date), 404
    return send_file(path, mimetype="application/pdf", as_attachment=True,
                     download_name=f"Oakridge_Drawings_{date}.pdf")


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
