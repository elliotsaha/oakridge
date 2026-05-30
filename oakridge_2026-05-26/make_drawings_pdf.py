#!/usr/bin/env python3
"""
Build a titled PDF of all drawings for a given day from the Oakridge index.

Usage:
    python3 make_drawings_pdf.py 2026-05-26
    python3 make_drawings_pdf.py            # defaults to today

Downloads every .jpg listed at
    http://drawings.oakridge.smtresearch.ca/<DATE>/
and compiles them, in name order, into one PDF (cover page + one drawing
per page with a titled header bar and page numbers).

Requires: Pillow, reportlab  ->  pip install pillow reportlab
"""
import os, sys, glob, html, datetime, urllib.parse, urllib.request, ssl

BASE_HOST = "http://drawings.oakridge.smtresearch.ca"


def fetch_listing(date):
    url = f"{BASE_HOST}/{date}/"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(url, context=ctx, timeout=60) as r:
        return url, r.read().decode("utf-8", "replace")


def parse_jpgs(html_text):
    import re
    # grab hrefs ending in .jpg (case-insensitive)
    return re.findall(r'href="([^"]+\.jpg)"', html_text, flags=re.IGNORECASE)


def download_all(date, hrefs, outdir):
    os.makedirs(outdir, exist_ok=True)
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    base = f"{BASE_HOST}/{date}/"
    ok, fail = 0, []
    for h in hrefs:
        name = urllib.parse.unquote(html.unescape(h))          # display/filename
        url = base + h.replace("&amp;", "%26")                 # request URL
        dest = os.path.join(outdir, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            ok += 1; continue
        try:
            with urllib.request.urlopen(url, context=ctx, timeout=120) as r, open(dest, "wb") as f:
                f.write(r.read())
            if os.path.getsize(dest) > 0:
                ok += 1
            else:
                fail.append(name)
        except Exception as e:
            fail.append(f"{name} ({e})")
    return ok, fail


def build_pdf(date, imgdir, out_pdf):
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from PIL import Image

    imgs = sorted(glob.glob(os.path.join(imgdir, "*.jpg")),
                  key=lambda p: os.path.basename(p).lower())
    if not imgs:
        print("No images found — nothing to build."); return None

    PAGE = landscape(letter); W, H = PAGE
    c = canvas.Canvas(out_pdf, pagesize=PAGE)

    # cover
    c.setFillColorRGB(0.1, 0.12, 0.15); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 34); c.drawCentredString(W/2, H/2+40, "Oakridge Drawings")
    c.setFont("Helvetica", 20); c.drawCentredString(W/2, H/2, f"Survey Date: {date}")
    c.setFont("Helvetica", 14)
    c.drawCentredString(W/2, H/2-30, f"{len(imgs)} drawings  ·  compiled in name order")
    c.setFillColorRGB(0.6, 0.6, 0.6); c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(W/2, 0.6*inch, f"Source: drawings.oakridge.smtresearch.ca/{date}")
    c.showPage()

    M = 0.4*inch; HDR = 0.5*inch
    for i, p in enumerate(imgs, 1):
        title = os.path.basename(p).rsplit("_"+date, 1)[0]
        c.setFillColorRGB(0.12, 0.45, 0.62); c.rect(0, H-HDR, W, HDR, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1); c.setFont("Helvetica-Bold", 13)
        c.drawString(M, H-HDR+0.16*inch, title)
        c.setFont("Helvetica", 9); c.drawRightString(W-M, H-HDR+0.16*inch, f"{i} / {len(imgs)}")
        try:
            iw, ih = Image.open(p).size
        except Exception as e:
            c.setFillColorRGB(0, 0, 0); c.setFont("Helvetica", 12)
            c.drawString(M, H/2, f"[could not read image: {e}]"); c.showPage(); continue
        avail_w, avail_h = W-2*M, H-HDR-2*M
        s = min(avail_w/iw, avail_h/ih)
        dw, dh = iw*s, ih*s
        x = (W-dw)/2; y = M + (avail_h-dh)/2
        c.drawImage(ImageReader(p), x, y, dw, dh, preserveAspectRatio=True, anchor='c')
        c.showPage()
    c.save()
    return out_pdf, len(imgs)


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    workdir = f"oakridge_{date}"
    imgdir = os.path.join(workdir, "images")
    out_pdf = os.path.join(workdir, f"Oakridge_Drawings_{date}.pdf")

    print(f"Reading index for {date} ...")
    try:
        _, text = fetch_listing(date)
    except Exception as e:
        print(f"ERROR: could not load {BASE_HOST}/{date}/  ->  {e}")
        print("Check the date exists on the server.")
        sys.exit(1)
    hrefs = parse_jpgs(text)
    print(f"Found {len(hrefs)} images. Downloading to {imgdir}/ ...")
    ok, fail = download_all(date, hrefs, imgdir)
    print(f"Downloaded {ok}/{len(hrefs)}." + (f" {len(fail)} failed." if fail else ""))
    for f in fail:
        print("  FAIL", f)
    res = build_pdf(date, imgdir, out_pdf)
    if res:
        print(f"\nDone -> {res[0]}  ({res[1]} drawings + cover)")


if __name__ == "__main__":
    main()
