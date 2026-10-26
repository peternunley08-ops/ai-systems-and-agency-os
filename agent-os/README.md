# Agent OS — Multi-Agent Business OS

A single-file, six-agent business automation. Six async agents share one typed
(`pydantic`) state object, run **sequentially**, pull **live Stripe revenue**, and email a
digest when done. Built to the same discipline as the Lumen Systems agency repo:
**the model advises, code decides; use only authoritative data; never fabricate; everything logged.**

- Entry point: `agent_os.py` (`python agent_os.py`)
- State: `state_store.json` (atomic writes; last run's `execution_log` becomes the next run's "yesterday")
- Deps: `anthropic`, `pydantic`, `stripe` (Python 3.9+ for `zoneinfo`; tested on 3.12)

## Pipeline
`StripeIngest → CEO → DataAnalyst → CMO → SalesRep → Researcher → Developer → digest email`

Each agent: load authoritative context → one LLM call (strict JSON) → **code decides** → log.
The Developer agent **quarantines** every proposed patch as `pending_review` — it never auto-deploys.

## Setup
```bash
pip install anthropic pydantic stripe
export ANTHROPIC_API_KEY=sk-...
export STRIPE_API_KEY=rk_live_...          # restricted, READ-ONLY key
export SMTP_HOST=smtp.gmail.com SMTP_PORT=587
export SMTP_USER=you@gmail.com SMTP_PASS=app-password
export DIGEST_TO=you@gmail.com
export BUSINESS_TZ=America/Los_Angeles      # optional; default UTC for the "yesterday" window
python agent_os.py
```

## Schedule it for 6 AM
- **Windows (Task Scheduler):** create a daily 06:00 task running
  `python C:\Users\peter\iCloudDrive\Desktop\agent-os\agent_os.py` with the env vars set for that task.
- **cron (Linux/macOS):** `0 6 * * *  cd /path/agent-os && /usr/bin/python agent_os.py`

## Integration seams (wire these to go live)
- `fetch_new_leads()` → real CRM / form / ad-lead source. Returns `[]` until connected.
  The SDR agent only acts on real leads — paying customers are **never** relabeled as leads.

## What was fixed vs the original draft
| Severity | Fix |
|---|---|
| High | Ranking no longer depends on the model echoing UUIDs — tasks are scored by **position index**, with a coverage warning when the model under-returns (previously the backlog could silently collapse to insertion order with all impacts `0`). |
| Medium | Task domains normalized to a fixed set on ingest; the CMO matches case-insensitively (a stray `"Marketing"` can't silently drop the content task). |
| Medium | No customer/lead conflation — leads come from `fetch_new_leads()`, not the paying-customer count. |
| Medium | Anthropic calls retry with **exponential backoff + jitter** + a strict-JSON retry-once nudge; shared authoritative-context preamble; token usage logged in the digest. |
| Medium | `send_digest` guards **all** SMTP env vars (no `KeyError` on a half-configured env). |
| Low | Stripe: built-in network retries, version-robust error class, broad "never crash the ingest" net, week/day MRR intervals, timezone-aware business-day window. |
| Low | Balanced-bracket JSON extraction; atomic state writes; UTC-consistent digest subject; Developer triages this run's errors too. |

> The contract still holds: no secrets in source, restricted read-only Stripe key, STARTTLS email,
> LLM output never executed, patches quarantined for human review.
