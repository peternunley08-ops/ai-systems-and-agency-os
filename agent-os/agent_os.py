"""
Multi-Agent Business OS — single-file build (patched).
Six agents share one typed state object, run sequentially at 6 AM,
pull live Stripe revenue, and email a digest when done.

Philosophy (matches the Lumen "AI Automation Agency" repo): the model advises,
code decides; use only authoritative data; never fabricate; everything logged.

Setup:
    pip install anthropic pydantic stripe
    export ANTHROPIC_API_KEY=sk-...
    export STRIPE_API_KEY=rk_live_...        # restricted, read-only key
    export SMTP_HOST=smtp.gmail.com SMTP_PORT=587
    export SMTP_USER=you@gmail.com SMTP_PASS=app-password
    export DIGEST_TO=you@gmail.com
    export BUSINESS_TZ=America/Los_Angeles    # optional; default UTC for the "yesterday" window
Run:
    python agent_os.py

Changes vs the original draft:
  - Ranking no longer depends on the model echoing UUIDs: tasks are scored by
    position index, with a coverage warning when the model under-returns.
  - Task domains are normalized to a fixed set on ingest; the CMO matches
    case-insensitively, so a stray "Marketing" can't silently drop the content task.
  - No customer/lead conflation: real leads come from fetch_new_leads() (an
    integration seam), not from the paying-customer count.
  - Anthropic calls retry with exponential backoff + jitter, plus a strict-JSON
    retry-once nudge; a shared authoritative-context preamble is prepended.
  - Stripe uses built-in network retries, a version-robust error class, a broad
    "never crash the ingest" safety net, week/day MRR intervals, and a
    timezone-aware business-day window.
  - send_digest guards all SMTP env vars; LLM token usage is logged in the digest.
"""
from __future__ import annotations
import asyncio, json, os, random, smtplib, uuid
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

import anthropic
import stripe
from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

MODEL = "claude-sonnet-4-6"
client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY

# Authoritative-context guardrail, prepended to every agent's system prompt.
PREAMBLE = (
    "Use ONLY the information provided in the input. Never invent revenue, customers, "
    "prices, competitors, metrics, or any fact not present; if you lack data, return an "
    "empty JSON array. Do not fabricate or overstate. Return ONLY the requested JSON.\n\n"
)

# Version-robust Stripe error base (stripe.StripeError on modern SDKs, stripe.error.* on older).
_StripeError = (getattr(stripe, "StripeError", None)
                or getattr(getattr(stripe, "error", None), "StripeError", Exception))

# Cost awareness: token usage accumulated across all LLM calls in a run.
USAGE = {"input_tokens": 0, "output_tokens": 0}

ALLOWED_DOMAINS = {"content", "leads", "sales", "ops", "dev"}
CONTENT_DOMAINS = {"content", "marketing", "cmo"}
_MRR_FACTOR = {"day": 365 / 12, "week": 52 / 12, "month": 1.0, "year": 1 / 12}


# ============================================================== STATE
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Priority(str, Enum):
    CRITICAL = "critical"; HIGH = "high"; MEDIUM = "medium"; LOW = "low"


class Task(BaseModel):
    id: str
    domain: str
    description: str
    priority: Priority = Priority.MEDIUM
    projected_impact: float = 0.0
    status: str = "pending"


class AgentLog(BaseModel):
    agent: str
    timestamp: str = Field(default_factory=_now)
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class GlobalState(BaseModel):
    run_id: str
    started_at: str = Field(default_factory=_now)
    yesterday_logs: list[AgentLog] = Field(default_factory=list)
    performance_metrics: dict[str, Any] = Field(default_factory=dict)
    inbound_leads: list[dict[str, Any]] = Field(default_factory=list)
    daily_master_schedule: list[Task] = Field(default_factory=list)
    ranked_operational_backlog: list[Task] = Field(default_factory=list)
    content_pipeline: list[dict[str, Any]] = Field(default_factory=list)
    crm_delta: list[dict[str, Any]] = Field(default_factory=list)
    market_intelligence: list[dict[str, Any]] = Field(default_factory=list)
    system_integrity: list[dict[str, Any]] = Field(default_factory=list)
    execution_log: list[AgentLog] = Field(default_factory=list)

    def commit(self, log: AgentLog) -> None:
        self.execution_log.append(log)


class StateStore:
    def __init__(self, path: str = "state_store.json") -> None:
        self.path = path

    def load_yesterday(self) -> list[AgentLog]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path) as f:
                raw = json.load(f)
            return [AgentLog(**l) for l in raw.get("execution_log", [])]
        except (ValueError, json.JSONDecodeError, OSError) as e:
            print(f"[state] could not load prior run ({e}); starting fresh.")
            return []

    def save(self, state: GlobalState) -> None:
        tmp = f"{self.path}.tmp"
        with open(tmp, "w") as f:
            f.write(state.model_dump_json(indent=2))
        os.replace(tmp, self.path)  # atomic; a crash mid-write can't corrupt the store


# ============================================================== STRIPE
def _yesterday_window() -> tuple[int, int]:
    """Epoch bounds for 'yesterday' in the business timezone (default UTC)."""
    tzname = os.environ.get("BUSINESS_TZ", "UTC")
    try:
        tz = ZoneInfo(tzname)
    except Exception:
        print(f"[stripe] unknown BUSINESS_TZ={tzname!r}; falling back to UTC.")
        tz = timezone.utc
    now = datetime.now(tz)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int((today - timedelta(days=1)).timestamp()), int(today.timestamp())


def fetch_revenue_metrics() -> dict[str, Any]:
    """Yesterday's real revenue. Stripe outage / unexpected error -> zeros, never a crash."""
    metrics: dict[str, Any] = {
        "gross_revenue": 0.0, "net_revenue": 0.0, "refunds": 0.0,
        "successful_charges": 0, "new_customers": 0, "active_mrr": 0.0,
    }
    key = os.environ.get("STRIPE_API_KEY")
    if not key:
        metrics["_stripe_error"] = "no STRIPE_API_KEY set"
        return metrics
    stripe.api_key = key
    stripe.max_network_retries = 2  # SDK-level idempotent retry/backoff
    start, end = _yesterday_window()
    try:
        for ch in stripe.Charge.list(created={"gte": start, "lt": end},
                                     limit=100).auto_paging_iter():
            if ch.paid and ch.status == "succeeded":
                metrics["gross_revenue"] += ch.amount / 100.0
                metrics["successful_charges"] += 1
                metrics["refunds"] += ch.amount_refunded / 100.0
        metrics["net_revenue"] = metrics["gross_revenue"] - metrics["refunds"]
        metrics["new_customers"] = sum(
            1 for _ in stripe.Customer.list(created={"gte": start, "lt": end},
                                            limit=100).auto_paging_iter())
        for sub in stripe.Subscription.list(status="active",
                                            limit=100).auto_paging_iter():
            for item in sub["items"]["data"]:
                price = item["price"]
                amt = (price.get("unit_amount") or 0) / 100.0
                qty = item.get("quantity", 1)
                interval = (price.get("recurring") or {}).get("interval", "month")
                metrics["active_mrr"] += amt * qty * _MRR_FACTOR.get(interval, 1.0)
    except _StripeError as e:
        metrics["_stripe_error"] = str(e)
        print(f"[stripe] degraded: {e}")
    except Exception as e:  # ingest must never crash the whole run
        metrics["_stripe_error"] = f"unexpected: {type(e).__name__}: {e}"
        print(f"[stripe] unexpected error, returning partial metrics: {e}")
    return {k: round(v, 2) if isinstance(v, float) else v for k, v in metrics.items()}


def fetch_new_leads() -> list[dict[str, Any]]:
    """Top-of-funnel leads for the SDR agent.
    // TODO(integration): wire to the real CRM / form / ad-lead source.
    Returns [] until connected — we never pass paying customers off as 'leads'."""
    return []


# ============================================================== LLM HELPERS
# Build the retryable-exception tuple defensively so an SDK-version rename can't
# break import; fall back to the APIError base if a specific class is absent.
_RETRYABLE = tuple(
    e for e in (getattr(anthropic, n, None) for n in
                ("RateLimitError", "APIConnectionError", "APITimeoutError", "InternalServerError"))
    if isinstance(e, type)
) or (anthropic.APIError,)


async def _ask(system: str, user: str, *, tries: int = 4) -> str:
    """One LLM call with exponential backoff + jitter on transient failures."""
    delay = 1.0
    for attempt in range(tries):
        try:
            resp = await client.messages.create(
                model=MODEL, max_tokens=2000, system=PREAMBLE + system,
                messages=[{"role": "user", "content": user}])
            u = getattr(resp, "usage", None)
            if u:
                USAGE["input_tokens"] += getattr(u, "input_tokens", 0) or 0
                USAGE["output_tokens"] += getattr(u, "output_tokens", 0) or 0
            return "".join(b.text for b in resp.content if b.type == "text")
        except _RETRYABLE:
            if attempt == tries - 1:
                raise
            await asyncio.sleep(delay + random.uniform(0, delay))
            delay *= 2
    return ""  # unreachable; the last attempt either returns or raises


def _extract_json(text: str) -> str | None:
    """Return the first *balanced* JSON array/object substring, or None."""
    candidates = [i for i in (text.find("["), text.find("{")) if i != -1]
    if not candidates:
        return None
    i = min(candidates)
    open_ch = text[i]
    close_ch = "]" if open_ch == "[" else "}"
    depth, in_str, esc = 0, False, False
    for j in range(i, len(text)):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    return None


def _parse_json(text: str, fallback):
    blob = _extract_json(text)
    if blob is None:
        return fallback
    try:
        return json.loads(blob)
    except (ValueError, json.JSONDecodeError):
        return fallback


async def _ask_json(system: str, user: str, fallback):
    """Strict-JSON contract: parse, and on failure retry once with a nudge, then fall back."""
    parsed = _parse_json(await _ask(system, user), None)
    if parsed is not None:
        return parsed
    nudged = user + ("\n\nYour previous reply was not valid JSON. Return ONLY valid JSON "
                     "matching the requested shape — no prose, no markdown fences.")
    return _parse_json(await _ask(system, nudged), fallback)


# ============================================================== AGENTS
async def ceo_agent(state: GlobalState) -> GlobalState:
    logs = "\n".join(f"- {l.agent}: {l.summary}" for l in state.yesterday_logs) or "No prior logs."
    rows = await _ask_json(
        "You are a COO. Audit yesterday, name friction, produce a master task table "
        "across content, leads, sales, ops, dev. Return ONLY a JSON array: "
        '[{"domain","description","priority"}]. domain must be one of '
        "content|leads|sales|ops|dev. priority: critical|high|medium|low.",
        f"Yesterday:\n{logs}\n\nMetrics: {state.performance_metrics}", [])
    for t in rows if isinstance(rows, list) else []:
        if not isinstance(t, dict):
            continue
        domain = (t.get("domain") or "ops").strip().lower()
        if domain not in ALLOWED_DOMAINS:
            domain = "ops"
        try:
            priority = Priority((t.get("priority") or "medium").strip().lower())
        except (ValueError, AttributeError):
            priority = Priority.MEDIUM
        state.daily_master_schedule.append(Task(
            id=str(uuid.uuid4())[:8], domain=domain,
            description=str(t.get("description", "")), priority=priority))
    state.commit(AgentLog(agent="CEO",
        summary=f"Routed {len(state.daily_master_schedule)} tasks."))
    return state


async def data_analyst_agent(state: GlobalState) -> GlobalState:
    items = list(enumerate(state.daily_master_schedule))
    payload = [{"i": i, "domain": t.domain, "description": t.description,
                "priority": t.priority.value} for i, t in items]
    rows = await _ask_json(
        "You are a revenue analyst. Score each task's projected_impact (0-100) by "
        'expected revenue and urgency. Return ONLY JSON: [{"i","projected_impact"}].',
        f"Tasks: {json.dumps(payload)}\nMetrics: {state.performance_metrics}", [])
    scores: dict[int, float] = {}
    for s in rows if isinstance(rows, list) else []:
        if isinstance(s, dict) and "i" in s:
            try:
                scores[int(s["i"])] = float(s.get("projected_impact", 0))
            except (ValueError, TypeError):
                continue
    for i, t in items:
        t.projected_impact = scores.get(i, 0.0)
    state.ranked_operational_backlog = sorted(
        state.daily_master_schedule, key=lambda t: t.projected_impact, reverse=True)
    top = state.ranked_operational_backlog[0].projected_impact if state.ranked_operational_backlog else 0
    coverage = f" ({len(scores)}/{len(items)} scored)" if items else ""
    note = " WARN partial scoring" if items and len(scores) < len(items) else ""
    state.commit(AgentLog(agent="DataAnalyst",
        summary=f"Ranked backlog; top impact={top}{coverage}.{note}"))
    return state


async def cmo_agent(state: GlobalState) -> GlobalState:
    top = next((t for t in state.ranked_operational_backlog
                if t.domain.lower() in CONTENT_DOMAINS), None)
    if not top:
        state.commit(AgentLog(agent="CMO", summary="No content task queued."))
        return state
    rows = await _ask_json(
        "You are a CMO. Build a multi-channel content matrix: hook, script outline, "
        'channels, CTA. Return ONLY JSON: [{"channel","hook","script","cta"}].',
        f"Content task: {top.description}", [])
    matrix = rows if isinstance(rows, list) else [rows]
    state.content_pipeline.extend(matrix)
    state.commit(AgentLog(agent="CMO", summary=f"Produced {len(matrix)} content assets."))
    return state


async def sales_agent(state: GlobalState) -> GlobalState:
    if not state.inbound_leads:
        state.commit(AgentLog(agent="SalesRep", summary="No inbound leads to process."))
        return state
    rows = await _ask_json(
        "You are an SDR. Qualify the day's leads, assign a 0-100 score, draft a "
        'personalized follow-up. Return ONLY JSON: [{"lead","score","followup"}].',
        f"New leads: {json.dumps(state.inbound_leads)}\nRecent CRM: {state.crm_delta[-3:]}", [])
    deltas = rows if isinstance(rows, list) else [rows]
    state.crm_delta.extend(deltas)
    state.commit(AgentLog(agent="SalesRep", summary=f"Processed {len(deltas)} lead actions."))
    return state


async def researcher_agent(state: GlobalState) -> GlobalState:
    rows = await _ask_json(
        "You are a market analyst. Surface 3 actionable micro-opportunities from "
        'competitor and trend movement. Return ONLY JSON: [{"signal","opportunity","action"}].',
        f"Known intel: {state.market_intelligence[-3:]}", [])
    notes = rows if isinstance(rows, list) else [rows]
    state.market_intelligence.extend(notes)
    state.commit(AgentLog(agent="Researcher", summary=f"Logged {len(notes)} opportunities."))
    return state


async def developer_agent(state: GlobalState) -> GlobalState:
    # Triage both yesterday's errors and any error logged earlier in *this* run.
    errors = [l for l in (state.yesterday_logs + state.execution_log)
              if "error" in l.summary.lower()]
    rows = await _ask_json(
        "You are an SRE. Triage error logs, propose patches. Output is QUARANTINED for "
        'human review — never auto-deploy. Return ONLY JSON: [{"issue","diagnosis","patch","risk"}].',
        f"Error logs: {[e.summary for e in errors]}", [])
    fixes = rows if isinstance(rows, list) else [rows]
    for f in fixes:
        if isinstance(f, dict):
            f["status"] = "pending_review"
    state.system_integrity.extend(f for f in fixes if isinstance(f, dict))
    state.commit(AgentLog(agent="Developer",
        summary=f"Quarantined {len(state.system_integrity)} patches for review."))
    return state


# ============================================================== DIGEST EMAIL
def send_digest(state: GlobalState) -> None:
    required = ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "DIGEST_TO")
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"[digest] missing env {missing}; skipping email.")
        return
    host = os.environ["SMTP_HOST"]
    to = os.environ["DIGEST_TO"]
    m = state.performance_metrics
    lines = [
        f"Agent OS run {state.run_id} — {state.started_at}",
        "",
        f"Net revenue (yest):  ${m.get('net_revenue', 0)}",
        f"Gross / refunds:     ${m.get('gross_revenue', 0)} / ${m.get('refunds', 0)}",
        f"Active MRR:          ${m.get('active_mrr', 0)}",
        f"New customers:       {m.get('new_customers', 0)}",
        f"LLM tokens (in/out): {USAGE['input_tokens']} / {USAGE['output_tokens']}",
        "",
        "Top 3 priorities:",
    ]
    for t in state.ranked_operational_backlog[:3]:
        lines.append(f"  [{t.projected_impact:>5}] {t.domain}: {t.description}")
    lines += ["", "Stage log:"]
    lines += [f"  {l.agent}: {l.summary}" for l in state.execution_log]
    if m.get("_stripe_error"):
        lines += ["", f"! Stripe degraded: {m['_stripe_error']}"]

    msg = MIMEText("\n".join(lines))
    msg["Subject"] = f"Agent OS digest — {datetime.now(timezone.utc):%Y-%m-%d}"
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = to
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587))) as s:
            s.starttls()
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            s.send_message(msg)
        print(f"[digest] sent to {to}")
    except Exception as e:
        print(f"[digest] failed: {e}")


# ============================================================== ORCHESTRATION
PIPELINE = [ceo_agent, data_analyst_agent, cmo_agent,
            sales_agent, researcher_agent, developer_agent]


async def run_pipeline() -> GlobalState:
    USAGE["input_tokens"] = USAGE["output_tokens"] = 0
    store = StateStore()
    try:
        metrics = await asyncio.to_thread(fetch_revenue_metrics)
    except Exception as e:  # belt-and-suspenders: the ingest itself must not abort the run
        metrics = {"gross_revenue": 0.0, "net_revenue": 0.0, "refunds": 0.0,
                   "successful_charges": 0, "new_customers": 0, "active_mrr": 0.0,
                   "_stripe_error": f"ingest crashed: {e}"}
    leads = await asyncio.to_thread(fetch_new_leads)
    state = GlobalState(
        run_id=str(uuid.uuid4())[:8],
        yesterday_logs=store.load_yesterday(),
        performance_metrics=metrics,
        inbound_leads=leads)
    state.commit(AgentLog(agent="StripeIngest",
        summary=f"net=${metrics.get('net_revenue', 0)} mrr=${metrics.get('active_mrr', 0)} "
                f"new_cust={metrics.get('new_customers', 0)}"))
    for agent in PIPELINE:
        try:
            state = await agent(state)
        except Exception as e:
            state.commit(AgentLog(agent=agent.__name__, summary=f"error: {e}"))
        store.save(state)
    send_digest(state)
    return state


if __name__ == "__main__":
    final = asyncio.run(run_pipeline())
    print(f"Run {final.run_id} complete. {len(final.execution_log)} stages logged.")
