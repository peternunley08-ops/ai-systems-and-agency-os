# AI Systems & Agency OS — Portfolio Monorepo

[![CI Verification](https://github.com/peternunley/ai-systems-and-agency-os/actions/workflows/ci.yml/badge.svg)](./.github/workflows/ci.yml)
[![Nestral Live Cockpit](https://img.shields.io/badge/Nestral-Live_Portfolio_Cockpit-FF9A3D?style=for-the-badge)](./nestral/public/index.html)
[![SLO Agency OS Gallery](https://img.shields.io/badge/SLO_Agency_OS-70_Live_Mockups-5b8cff?style=for-the-badge)](./slo-agency-os/gallery.html)
[![Agent OS Simulator](https://img.shields.io/badge/Agent_OS-6--Agent_Pipeline_Simulator-38bdf8?style=for-the-badge)](./agent-os/index.html)

Three production-grade AI operations and agency automation systems built around one core engineering philosophy: **the model advises, deterministic code decides; authoritative data only; zero silent failures; human-gated execution.**

---

## 🚀 Live Interactive Previews (Zero Install / GitHub Pages)

| System | Interactive Web App | Architecture & Overview | Stack |
| :--- | :--- | :--- | :--- |
| **1. 🪺 Nestral** | [**Launch Live Cockpit →**](./nestral/public/index.html)<br>[**View Marketing Site (`nestral.ai`) →**](./nestral/site/index.html) | Multi-brand AI chief-of-staff that connects Shopify & Stripe workspaces into one calm daily morning brief ranked by *what needs you today*, plus deterministic natural-language Q&A. | Node.js 18+ (Zero Dependencies), Vanilla JS, CSS Design Tokens |
| **2. 🌊 SLO Agency OS** | [**Launch Mockup Gallery (70 Variants) →**](./slo-agency-os/gallery.html)<br>[**Launch Lead Command Center →**](./slo-agency-os/lead-command-center.html) | End-to-end local web agency pipeline for San Luis Obispo County: 3-stage Google Places lead verification, 5-variant HTML mockup generator (`Editorial`, `Bento`, `Brutalist`, `Minimalist`, `Dark Mode`), bilingual EN/ES JSON-LD SEO, and pitch studio. | Python 3.12, Official Google Places API, Self-Contained HTML/CSS |
| **3. 🤖 Agent OS** | [**Launch 6-Agent Pipeline Simulator →**](./agent-os/index.html) | Single-file 6-agent sequential business OS (`StripeIngest → CEO → DataAnalyst → CMO → SalesRep → Researcher → Developer → 6 AM Digest`) sharing a typed `pydantic` `GlobalState` with quarantined `pending_review` SRE patches. | Python 3.12, `pydantic`, `anthropic`, `stripe`, Atomic JSON State |

---

## 📂 Repository Structure

```text
ai-systems-and-agency-os/
├── index.html                  # Interactive portfolio hub linking all live systems
├── README.md                   # Architecture & quickstart documentation
├── .github/workflows/ci.yml    # Automated Node 22 + Python 3.12 CI verification
│
├── nestral/                    # 🪺 Nestral — AI Chief-of-Staff for Multi-Brand Operators
│   ├── index.js                # Zero-dependency CLI (brief | ask | serve | watch)
│   ├── src/                    # Connector registry, Shopify/Stripe clients, brief & ask engines
│   ├── public/index.html       # Interactive Cockpit (works both with local server & standalone)
│   ├── site/index.html         # Marketing landing page for nestral.ai
│   └── brand/                  # Design system tokens (tokens.css), SVG logos, BRAND.md
│
├── slo-agency-os/              # 🌊 SLO Agency OS — Central Coast Web Agency Pipeline
│   ├── run_pipeline.py         # Full orchestrator (leads → mockups → variants → pitch → gallery)
│   ├── find_leads.py           # Tier 1 official Places API discovery + 3-stage verification
│   ├── generate_variants.py    # Tier 3 multi-style HTML generator (5 styles per lead)
│   ├── pitch_studio.py         # Tier 2 outreach scripts & review copy generator
│   ├── i18n_seo.py             # Bilingual EN/ES + LocalBusiness JSON-LD schema engine
│   ├── gallery.html            # Live 14-lead × 5-style interactive gallery (70 mockups)
│   ├── lead-command-center.html# Full agency Kanban CRM & pitch command center
│   └── mockups/                # 70+ generated responsive HTML mockups
│
└── agent-os/                   # 🤖 Agent OS — 6-Agent Sequential Business OS
    ├── agent_os.py             # 466-line sequential multi-agent state machine
    ├── index.html              # Interactive 6-Agent Pipeline Simulator & State Inspector
    └── README.md               # Engineering changelog & deployment guide
```

---

## ⚡ Quickstart & Local Verification

### 1. Nestral (Zero-Dependency Node 18+ CLI & Cockpit)
```bash
cd nestral
node index.js brief                 # Generate today's ranked portfolio morning brief
node index.js ask "best week?"      # Query the deterministic portfolio Q&A engine
node index.js serve                 # Start local cockpit server at http://localhost:7711
```

### 2. SLO Agency OS (Python 3.12 Web Agency Pipeline)
```bash
cd slo-agency-os
pip install -r requirements.txt
python3 run_pipeline.py             # Rebuild mockups, 5x style variants, pitch copy & gallery
```

### 3. Agent OS (6-Agent Sequential Business OS)
```bash
cd agent-os
pip install anthropic pydantic stripe
python3 -m py_compile agent_os.py   # Verify syntax & type contracts
```
