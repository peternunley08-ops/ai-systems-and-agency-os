# 🪺 Nestral

**The AI chief-of-staff for everything you run.**
Connect the tools you already use → one calm morning brief, ranked by *what needs you today*.
One workspace or a hundred. See [`CONCEPT.md`](./CONCEPT.md) for the strategy and [`brand/BRAND.md`](./brand/BRAND.md) for the identity.

A "workspace" is anything you connect — a store, a Stripe account, a client. Portfolio commerce is
the flagship, but the engine is source-agnostic.

---

## Run it (zero install)

Zero dependencies — just Node 18+.

```powershell
node index.js brief            # build today's brief → prints it + saves briefs/<date>.md
node index.js brief --send     # …and deliver it to your configured channels (Telegram/webhook)
node index.js ask "best week?" # ask your portfolio a question
node index.js serve            # launch the cockpit at http://localhost:7711
node index.js watch [--now]    # daemon: deliver the brief automatically every day at schedule.time
```

Or double-click **`Start Nestral.cmd`**. It runs out-of-the-box on **safe demo data** (a simulated
portfolio incl. a Stripe workspace) so you can see the product immediately — no credentials needed.

## Make it real

Everything is configurable **from the cockpit** — click **⚙ Connect** (top-right) to add workspaces
and set up delivery, no file editing. Or edit `nestral.config.json` (copy from the example).

**Add a workspace**
- **Shopify** — custom app (Admin → Settings → Apps → Develop apps), scopes `read_orders` +
  `read_products`, copy the Admin API token.
- **Stripe** — a read-only restricted key.
- Leave the token blank/`mock` to keep a workspace on demo data.

**Deliver the brief** — in Connect, enable **Telegram**, paste a bot token (@BotFather) + your chat id,
set the time, Save. Then run `node index.js watch` (or schedule it via Windows Task Scheduler) and the
brief lands every morning. Webhook delivery is also supported (point it at a Zapier/Make/Apps-Script
that emails — the Northstar Apps Script pattern fits).

> Tokens stay on your machine in `nestral.config.json` (git-ignored). Nestral talks directly to each
> platform with read-only scopes. Never sold, never used to train models.

## What the brief watches

Per workspace, then ranked across the portfolio:
- 📉 **Momentum** — 7-day revenue down ≥30% vs prior week (or up ≥50%)
- 🚫 **Gone quiet** — no activity in 7+ days
- 📦 **Backlog** — orders awaiting fulfillment
- 💳 **Pending payments** to capture/cancel
- 🪫 **Stock risk** — out-of-stock / low-stock variants
- 🔌 **Broken connection** — bad/expired token

## Features

- **Connectors** — Shopify + Stripe today; add a file in `src/connectors.js` and it joins the brief.
- **Ask your portfolio** — deterministic Q&A over the live snapshot (`ask` CLI + cockpit bar + `/api/ask`). LLM-upgradeable.
- **History** — every run appends to `data/history.jsonl`; the cockpit shows a 7-day trend sparkline.
- **Delivery + scheduler** — Telegram/webhook, daily via `watch`.
- **Light + dark** — full theme, toggle remembered per device.

## Roadmap

- Ad accounts (Meta/TikTok) → spend & ROAS in the brief. Inbox + project sources. Actions (drafted, human-approved). Hosted multi-tenant SaaS.

## Layout

```
index.js                  CLI (brief [--send] | ask | serve | watch)
src/nestral.js            config load/save + parallel gather
src/connectors.js         connector registry (shopify, stripe) — "connect anything"
src/shopify.js            Shopify Admin client + realistic mock mode
src/brief.js              the brain — snapshot → ranked "needs you today"
src/ask.js                deterministic "ask your portfolio" engine
src/deliver.js            Telegram + webhook delivery
src/history.js            daily totals persistence (data/history.jsonl)
src/server.js             cockpit server + JSON API (brief/history/ask/config)
public/index.html         the cockpit UI (ask bar, sparkline, Connect drawer, light/dark)
nestral.config.example.json   workspace + delivery template
brand/                    BRAND.md, tokens.css, logo/ (mark, lockup, favicon, icon)
site/                     marketing site for nestral.ai (index.html + assets/)
```
