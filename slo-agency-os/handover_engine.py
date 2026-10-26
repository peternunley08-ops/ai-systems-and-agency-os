#!/usr/bin/env python3
"""
handover_engine.py  —  TIER 4: The "One-Click Contract Win" Handover Engine
===========================================================================
Given a lead slug, compiles a clean Client Success Bundle into
/outputs/clients/<slug>/ with four deployment-ready assets:

  1. index.html          production site (the Tier-3 mockup, PREVIEW chrome stripped)
  2. invoice.html        $500 setup (due on receipt) + $50/mo (starts +30 days)
  3. onboarding_email.txt welcome + asset-request email (ready to send)
  4. launch_checklist.md  internal launch steps incl. domain/hosting/monitoring

This is the on-disk equivalent of the dashboard's "⚡ Close Deal" button (which
builds the same bundle in-browser as a downloadable ZIP). Both produce identical
asset content so disk and browser stay in sync.

Configure your own agency details with env vars (otherwise clear placeholders are
left for you to fill in):
    export AGENCY_NAME="Coastline Web Studio"
    export AGENCY_EMAIL="you@studio.com"
    export AGENCY_PHONE="(805) 555-0100"

Usage:
    python handover_engine.py --slug reds-handyman
    python handover_engine.py --all
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "leads_database.csv")
MOCK_DIR = os.path.join(BASE_DIR, "mockups")
CLIENTS_DIR = os.path.join(BASE_DIR, "clients")

SETUP_FEE = 500
MRR_FEE = 50

def _load_config():
    cfg = os.path.join(BASE_DIR, "config.env")
    if not os.path.exists(cfg):
        return
    for _raw in open(cfg, encoding="utf-8"):
        _ln = _raw.strip()
        if not _ln or _ln.startswith("#") or "=" not in _ln:
            continue
        _k, _v = _ln.split("=", 1)
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _v and not _v.startswith("[") and _k not in os.environ:
            os.environ[_k] = _v


_load_config()


AGENCY_NAME = os.environ.get("AGENCY_NAME", "[Your Agency Name]")
AGENCY_EMAIL = os.environ.get("AGENCY_EMAIL", "[your@email.com]")
AGENCY_PHONE = os.environ.get("AGENCY_PHONE", "[your phone]")


def esc(t: str) -> str:
    return html.escape(t or "", quote=True)


# --------------------------------------------------------------------------- #
# Asset 1: production index.html  (strip PREVIEW chrome from the Tier-3 mockup)
# --------------------------------------------------------------------------- #
def productionize(mockup_html: str) -> str:
    """Remove demo-only chrome so the page is client-ready."""
    out = mockup_html
    # remove the diagonal PREVIEW ribbon element
    out = re.sub(r'<div class="demo-ribbon">.*?</div>', "", out, flags=re.S)
    # neutralise the demo form notice
    out = out.replace(
        "Thanks! This is a demo form - on your live site this lands straight in your inbox.",
        "Thanks - we&rsquo;ll be in touch shortly!",
    )
    # KEEP the labeled "sample testimonials" disclaimer: shipping unverified sample
    # reviews without a label would assert them as real, which is non-compliant.
    # Strip the "Website demo" footer tag so the production page isn't labeled a demo.
    out = out.replace(" &middot; Website demo", "").replace(" · Website demo", "")
    # drop any HTML comments
    out = re.sub(r"<!--.*?-->", "", out, flags=re.S)
    return out


def build_index(lead: dict) -> str:
    slug = lead["slug"]
    mock_path = os.path.join(MOCK_DIR, f"{slug}-demo.html")
    if os.path.exists(mock_path):
        with open(mock_path, encoding="utf-8") as fh:
            return productionize(fh.read())
    # Fallback: generate fresh from the Tier-3 engine if the mockup is missing.
    try:
        import generate_mockups as gm  # local module
        return productionize(gm.build_html(lead))
    except Exception as exc:  # pragma: no cover - defensive
        return (f"<!doctype html><meta charset='utf-8'>"
                f"<title>{esc(lead.get('business_name',''))}</title>"
                f"<h1>{esc(lead.get('business_name',''))}</h1>"
                f"<p>Production build unavailable: {esc(str(exc))}</p>")


# --------------------------------------------------------------------------- #
# Asset 2: invoice.html
# --------------------------------------------------------------------------- #
INVOICE_TPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Invoice {INV} - {BIZ}</title>
<style>
  :root{{--ink:#0e1726;--muted:#5a6678;--line:#e2e8f1;--accent:#2563eb;--bg:#f6f8fc}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:var(--bg);color:var(--ink);padding:32px;line-height:1.55}}
  .inv{{max-width:760px;margin:0 auto;background:#fff;border:1px solid var(--line);
    border-radius:16px;overflow:hidden;box-shadow:0 18px 50px rgba(15,23,42,.08)}}
  .top{{display:flex;justify-content:space-between;align-items:flex-start;
    padding:32px;background:linear-gradient(135deg,#1e293b,#0e1726);color:#fff}}
  .top h1{{font-size:30px;letter-spacing:-.02em}}
  .top .meta{{text-align:right;font-size:13px;opacity:.85;line-height:1.7}}
  .pill{{display:inline-block;background:#f59e0b;color:#1a1300;font-weight:800;
    font-size:12px;padding:4px 11px;border-radius:999px;margin-top:8px}}
  .parties{{display:flex;justify-content:space-between;gap:24px;padding:28px 32px;border-bottom:1px solid var(--line)}}
  .parties h3{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:7px}}
  .parties p{{font-size:14.5px;font-weight:600}}
  table{{width:100%;border-collapse:collapse}}
  thead th{{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
    color:var(--muted);padding:14px 32px;border-bottom:1px solid var(--line)}}
  tbody td{{padding:18px 32px;border-bottom:1px solid var(--line);font-size:15px}}
  td.amt,th.amt{{text-align:right;white-space:nowrap}}
  .desc small{{display:block;color:var(--muted);font-size:13px;font-weight:400;margin-top:3px}}
  .totals{{display:flex;justify-content:flex-end;padding:22px 32px}}
  .totals table{{width:auto;min-width:280px}}
  .totals td{{padding:6px 0;border:0;font-size:15px}}
  .totals .grand td{{font-size:19px;font-weight:800;border-top:2px solid var(--ink);padding-top:12px}}
  .pay{{margin:0 32px 28px;padding:20px;border:2px dashed var(--line);border-radius:12px;
    background:var(--bg);text-align:center;color:var(--muted);font-size:14px}}
  .pay b{{color:var(--ink)}}
  .terms{{padding:0 32px 32px;font-size:12.5px;color:var(--muted);line-height:1.7}}
  .foot{{padding:18px 32px;background:var(--bg);font-size:12px;color:var(--muted);text-align:center}}
</style></head>
<body>
<div class="inv">
  <div class="top">
    <div><h1>INVOICE</h1><div class="pill">DUE UPON RECEIPT</div></div>
    <div class="meta">Invoice <b>{INV}</b><br>Issued {ISSUED}<br>Due {ISSUED}</div>
  </div>
  <div class="parties">
    <div><h3>From</h3><p>{AGENCY}</p><p style="font-weight:400;color:var(--muted)">{AEMAIL}<br>{APHONE}</p></div>
    <div style="text-align:right"><h3>Bill To</h3><p>{BIZ}</p><p style="font-weight:400;color:var(--muted)">{ADDR}<br>{PHONE}</p></div>
  </div>
  <table>
    <thead><tr><th>Description</th><th class="amt">Amount</th></tr></thead>
    <tbody>
      <tr><td class="desc">Website Design &amp; Setup &mdash; one-time
        <small>Custom responsive single-page site, mobile-optimized, contact form, hosting setup.</small></td>
        <td class="amt">${SETUP}.00</td></tr>
      <tr><td class="desc">Maintenance &amp; Hosting &mdash; monthly
        <small>Hosting, updates, edits, and monitoring. First charge {MSTART}, then monthly.</small></td>
        <td class="amt">${MRR}.00 / mo</td></tr>
    </tbody>
  </table>
  <div class="totals"><table>
    <tr><td>Setup (due now)</td><td class="amt">${SETUP}.00</td></tr>
    <tr><td>Monthly (from {MSTART})</td><td class="amt">${MRR}.00</td></tr>
    <tr class="grand"><td>Due today</td><td class="amt">${SETUP}.00</td></tr>
  </table></div>
  <div class="pay"><b>Payment:</b> [ Connect your Stripe account &mdash; paste your payment link or embed
    your card block here. ]<br>Placeholder only; no live payment is collected by this template.</div>
  <div class="terms">
    <b>Agreement terms.</b> The ${SETUP}.00 setup fee is due upon receipt of this invoice. The
    ${MRR}.00/month maintenance &amp; hosting fee begins {MSTART} (30 days from issue) and recurs monthly
    until cancelled with 30 days&rsquo; notice. This is a template &mdash; review and adapt before sending.
  </div>
  <div class="foot">{AGENCY} &middot; Prepared for {BIZ}, {CITY}, CA &middot; {ISSUED}</div>
</div>
</body></html>"""


def build_invoice(lead: dict) -> str:
    today = datetime.now()
    mstart = today + timedelta(days=30)
    inv_no = f"INV-{today:%Y%m%d}-{lead['slug'][:6].upper()}"
    return INVOICE_TPL.format(
        INV=esc(inv_no), BIZ=esc(lead.get("business_name", "")),
        CITY=esc(lead.get("city", "")), ADDR=esc(lead.get("address", "") or "—"),
        PHONE=esc(lead.get("phone", "") or "—"),
        AGENCY=esc(AGENCY_NAME), AEMAIL=esc(AGENCY_EMAIL), APHONE=esc(AGENCY_PHONE),
        ISSUED=today.strftime("%b %d, %Y"), MSTART=mstart.strftime("%b %d, %Y"),
        SETUP=SETUP_FEE, MRR=MRR_FEE,
    )


# --------------------------------------------------------------------------- #
# Asset 3 + 4: onboarding email + launch checklist
# --------------------------------------------------------------------------- #
def build_email(lead: dict) -> str:
    biz = lead.get("business_name", "your business")
    city = lead.get("city", "your area")
    return f"""Subject: Welcome aboard, {biz} — your new website is ready to launch

Hi [First Name],

Welcome to {AGENCY_NAME}! I'm excited to get {biz} online.

Your custom preview site is ready to review here:
  [ paste preview link — e.g. open clients/{lead['slug']}/index.html ]

It's built specifically for a {lead.get('niche','local service')} business in {city},
with your services, a tap-to-call button, and a contact form already wired up.

To finalize your launch, I need three quick things from you:

  1. Your logo (any format — PNG/SVG/PDF), if you have one.
  2. 3–6 photos you'd like featured (team, work, storefront, or food).
  3. Confirmation of your hours, service area, and best phone number.

Once I have those, I'll swap them in, connect your domain, and push the site live —
usually within a few business days.

To get started, the one-time setup invoice is attached (setup due on receipt; the
${MRR_FEE}/mo maintenance & hosting begins 30 days after launch). Reply to this email
with your assets and any questions and we'll take it from there.

Looking forward to getting {biz} found online.

Best,
[Your Name]
{AGENCY_NAME}
{AGENCY_EMAIL} · {AGENCY_PHONE}

—
Note: this is a ready-to-send draft. Personalize the bracketed fields and confirm the
recipient opted in / is a fair business contact before sending (CAN-SPAM for email).
"""


def build_checklist(lead: dict) -> str:
    biz = lead.get("business_name", "")
    base = re.sub(r"[^a-z0-9]", "", (lead.get("business_name", "") or "").lower())[:18]
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""# Launch Checklist — {biz}

_Generated {today} · stage: Closed/Won · {lead.get('city','')}, CA_

## 1. Domain
- [ ] Check availability and register a domain for the client:
  - `{base}slo.com`
  - `{base}.com`
  - `{base}{re.sub(r'[^a-z0-9]','', lead.get('city','').lower())}.com`
- [ ] Confirm preferred domain with client; point DNS to host.

## 2. Hosting & Deploy
- [ ] Connect hosting platform / storage bucket (Netlify, Cloudflare Pages, S3, etc.).
- [ ] Deploy `clients/{lead['slug']}/index.html` as the site root.
- [ ] Enable HTTPS / SSL and verify mobile rendering.

## 3. Content Swap
- [ ] Replace sample testimonials with the client's real Google/Yelp reviews.
- [ ] Insert client logo + supplied photos into the hero and gallery.
- [ ] Confirm phone, hours, and service area are correct.

## 4. Billing
- [ ] Send `invoice.html` — ${SETUP_FEE} setup (due on receipt).
- [ ] Schedule ${MRR_FEE}/mo maintenance to begin 30 days post-launch.

## 5. Monitoring
- [ ] Set up an uptime/status check (e.g., a daily ping).
- [ ] Add the site to Google Business Profile + submit sitemap.
- [ ] Calendar a 2-week check-in with the client.
"""


# --------------------------------------------------------------------------- #
# Bundle writer
# --------------------------------------------------------------------------- #
def load_leads() -> list[dict]:
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"ERROR: {CSV_PATH} not found. Run find_leads.py first.")
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_bundle(lead: dict) -> str:
    slug = (lead.get("slug") or "").strip()
    out_dir = os.path.join(CLIENTS_DIR, slug)
    os.makedirs(out_dir, exist_ok=True)
    files = {
        "index.html": build_index(lead),
        "invoice.html": build_invoice(lead),
        "onboarding_email.txt": build_email(lead),
        "launch_checklist.md": build_checklist(lead),
    }
    for name, content in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            fh.write(content)
    return out_dir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate a client handover bundle.")
    ap.add_argument("--slug", help="Lead slug to close.")
    ap.add_argument("--all", action="store_true", help="Build bundles for all leads.")
    args = ap.parse_args(argv)

    leads = load_leads()
    if args.slug:
        leads = [l for l in leads if l.get("slug") == args.slug]
        if not leads:
            raise SystemExit(f"ERROR: slug '{args.slug}' not found in CSV.")
    elif not args.all:
        raise SystemExit("Specify --slug <slug> or --all.")

    for lead in leads:
        out = build_bundle(lead)
        print(f"  bundle -> {out}  ({lead.get('business_name','')})")
    print(f"\nDone. {len(leads)} client bundle(s) written under {CLIENTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
