# SLO Agency OS — Central Coast Web Agency Pipeline

[![Live Mockup Gallery](https://img.shields.io/badge/Live_Demo-SLO_Mockup_Gallery_(70_Variants)-5b8cff?style=for-the-badge)](./gallery.html)
[![Lead Command Center](https://img.shields.io/badge/Live_Dashboard-Lead_Command_Center-7c5cff?style=for-the-badge)](./lead-command-center.html)

An end-to-end Python automation pipeline for discovering local Central Coast (San Luis Obispo County) businesses without modern websites, generating 5 tailored multi-style HTML mockups per lead (`Editorial`, `Bento`, `Brutalist`, `Minimalist`, `Dark Mode`), drafting localized EN/ES pitch assets, and compiling an interactive Lead Command Center and Mockup Gallery.

---

## Live Interactive Demos
- **[SLO Mockup Gallery (`gallery.html`)](./gallery.html)** — Browse 14 local leads × 5 live design variants (70+ self-contained responsive HTML mockups).
- **[SLO Lead Command Center (`lead-command-center.html`)](./lead-command-center.html)** — Full Kanban CRM board, pitch scripts, SMS/email templates, and embedded mockup previews.

---

## 1. Folder layout (keep it flat)

The scripts resolve every path relative to **their own location**, so the simplest,
most reliable structure is to keep all the project files together in one folder:

```
slo-agency-os/
├── requirements.txt
├── config.env.example     # template for API keys + agency details
├── find_leads.py          # Tier 1 discovery + 3-stage verification
├── generate_mockups.py    # Tier 3 — 1 demo per lead
├── generate_variants.py   # Tier 3 — 5 styles per lead
├── pitch_studio.py        # Tier 2 — call/SMS/email/review copy
├── build_dashboard.py     # Tier 4 — lead-command-center.html
├── build_gallery.py       # gallery.html (links to every mockup)
├── build_viewer.py        # viewer.html (all mockups embedded in one file)
├── handover_engine.py     # Tier 4 — clients/<slug>/ bundle
├── run_pipeline.py        # runs the whole loop in order
├── i18n_seo.py            # JSON-LD + EN/ES helpers
├── leads_database.csv     # the lead database
├── mockups/               # generated HTML mockups (5 variants per lead)
└── gallery.html  lead-command-center.html
```

## 2. Virtual environment (one-time)

From the project folder:

```bash
python -m venv .venv
# activate it:
#   Windows PowerShell:  .venv\Scripts\Activate.ps1
#   Windows CMD:         .venv\Scripts\activate.bat
#   Mac/Linux:           source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

That's it — the only dependency is `requests`. No Playwright, no browser binaries,
no Gemini key needed.

## 3. Add your key (no brackets!)

Copy `config.env.example` to `config.env` and set:

```ini
GOOGLE_PLACES_API_KEY=AIzaSyYourRealKey      # NO [ ] brackets, NO quotes
SERPAPI_KEY=your_serpapi_key                 # optional (enables verification Stages 2-3)
AGENCY_NAME=Central Coast Web Studio
AGENCY_EMAIL=you@example.com
AGENCY_PHONE=(805) 555-0123
```

A value still wrapped in `[ ]` is treated as unset.

## 4. Run it

```bash
# discover new leads (needs the Places key + internet)
python find_leads.py --niche "Plumber" --city "Paso Robles"

# rebuild every asset from the database (no key needed)
python run_pipeline.py
```

`run_pipeline.py` chains: `find_leads` (if key present) → `generate_mockups` →
`generate_variants` → `pitch_studio` → `build_dashboard` → `build_gallery` → `build_viewer`.

## 5. Compliance reminders (built into the engine)

- Only the official Google Places API is used — no Maps/Yelp HTML scraping.
- Ratings/reviews in schema are emitted only when real; no fabricated values.
- Outreach copy + invoices are drafts for **manual** human use — confirm phones and
  follow TCPA (calls/texts) and CAN-SPAM (email) before sending.
