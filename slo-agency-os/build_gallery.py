#!/usr/bin/env python3
"""
build_gallery.py  —  gallery.html: open the FULL page for every lead x every style.
Reads leads_database.csv, links to each lead's 5 standalone variant pages
(mockups/<slug>/variant-N.html) opening in a new tab. Self-contained, no CDNs.
Run:  python build_gallery.py   (also run by run_pipeline.py)
"""
from __future__ import annotations
import csv, html as _h, os

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, "leads_database.csv")
OUT = os.path.join(BASE, "gallery.html")
MOCK = "mockups"
VARIANTS = [("1", "editorial", "Editorial"), ("2", "bento", "Bento"),
            ("3", "brutalist", "Brutalist"), ("4", "minimalist", "Minimal"),
            ("5", "darkmode", "Dark Mode")]


def esc(s): return _h.escape(s or "", quote=True)


def build_cards():
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    cards = []
    for r in rows:
        slug = (r.get("slug") or "").strip()
        if not slug:
            continue
        links, paths = [], []
        for num, key, label in VARIANTS:
            p = f"{MOCK}/{slug}/variant-{num}-{key}.html"
            if os.path.exists(os.path.join(BASE, p)):
                links.append(f'<a class="pill" href="{p}" target="_blank" rel="noopener">{esc(label)}</a>')
                paths.append(p)
        if not links:
            continue
        meta = " &middot; ".join(x for x in [esc(r.get("niche", "")), esc(r.get("city", ""))] if x)
        rating = (r.get("rating") or "").strip()
        reviews = (r.get("review_count") or "").strip()
        if rating:
            badge = f'<span class="rate">&#9733; {esc(rating)}' + (f" &middot; {esc(reviews)}" if reviews else "") + '</span>'
        elif reviews:
            badge = f'<span class="rate">{esc(reviews)} reviews</span>'
        else:
            badge = ''
        openall = "[" + ",".join(f'"{p}"' for p in paths) + "]"
        cards.append(
            '<article class="card">'
            f'<div class="ch"><div><h2>{esc(r.get("business_name",""))}</h2>'
            f'<div class="meta">{meta}</div></div>{badge}</div>'
            f'<div class="pills">{"".join(links)}</div>'
            f'<button class="all" onclick=\'openAll({openall})\'>Open all 5 &#8599;</button>'
            '</article>')
    return cards


TPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SLO Mockup Gallery</title>
<style>
:root{--bg:#0b1020;--panel:#121a31;--panel2:#0f1730;--line:#243154;--ink:#e8edf9;--muted:#9aa7c7;--brand:#5b8cff;--brand2:#7c5cff;--gold:#fbbf24;--font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font);background:radial-gradient(900px 500px at 88% -10%,rgba(124,92,255,.18),transparent 60%),radial-gradient(800px 500px at -10% 0%,rgba(91,140,255,.16),transparent 55%),var(--bg);color:var(--ink);min-height:100vh;padding:26px}
.wrap{max-width:1120px;margin:0 auto}
h1{font-size:24px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:14px;margin:5px 0 22px}
.sub a{color:var(--brand);font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:16px}
.card{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 12px 30px rgba(0,0,0,.35)}
.ch{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;margin-bottom:13px}
.card h2{font-size:17px}
.meta{color:var(--muted);font-size:12.5px;margin-top:3px}
.rate{color:var(--gold);font-size:12.5px;font-weight:700;white-space:nowrap}
.pills{display:flex;flex-wrap:wrap;gap:7px}
.pill{background:var(--panel2);border:1px solid var(--line);color:var(--ink);border-radius:999px;padding:7px 13px;font-size:12.5px;font-weight:700}
.pill:hover{border-color:var(--brand);color:var(--brand)}
.all{margin-top:12px;width:100%;background:linear-gradient(135deg,var(--brand),var(--brand2));border:0;color:#fff;font-weight:800;border-radius:10px;padding:10px;cursor:pointer;font-size:13px}
.all:hover{filter:brightness(1.07)}
</style></head>
<body><div class="wrap">
<h1>SLO Mockup Gallery</h1>
<div class="sub">Every lead &times; 5 styles &mdash; click a style to open the full page in a new tab. <a href="lead-command-center.html">&rarr; Command Center</a></div>
<div class="grid">__CARDS__</div>
</div>
<script>
function openAll(paths){paths.forEach(function(p,i){setTimeout(function(){window.open(p,'_blank');},i*250);});}
</script>
</body></html>"""


def main():
    cards = build_cards()
    out = TPL.replace("__CARDS__", "".join(cards))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"Wrote {OUT} with {len(cards)} leads ({len(cards)*5} full-page links).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
