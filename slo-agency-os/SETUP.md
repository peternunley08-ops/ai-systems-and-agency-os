# SLO Agency OS — Setup

## 1. Folder layout (keep it flat)

The scripts resolve every path relative to **their own location**, so the simplest,
most reliable structure is to keep all the project files together in one folder:

```
slo-agency-os/
├── .clinerules            # Cline rules + V8.5 prompt
├── .gitignore
├── requirements.txt
├── config.env             # your API key + agency details (NEVER commit)
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
├── mockups/   pitch/   clients/        # generated output (auto-created)
└── viewer.html  gallery.html  lead-command-center.html   # generated
```

> If you prefer the scripts in root with everything else under an `outputs/` subfolder,
> tell me and I'll adjust the path constants in each script — but the flat layout above
> works as-is with no code changes.

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

Open `config.env` and set:

```
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

`run_pipeline.py` chains: find_leads (if key present) → generate_mockups →
generate_variants → pitch_studio → build_dashboard → build_gallery → build_viewer.

## 5. Compliance reminders (built into the engine)

- Only the official Google Places API is used — no Maps/Yelp HTML scraping.
- Ratings/reviews in schema are emitted only when real; no fabricated values.
- Outreach copy + invoices are drafts for **manual** human use — confirm phones and
  follow TCPA (calls/texts) and CAN-SPAM (email) before sending.
