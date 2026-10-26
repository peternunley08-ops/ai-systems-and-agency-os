#!/usr/bin/env python3
"""
pitch_studio.py  —  TIER 2: Persuasive Personalization Studio
=============================================================
For every verified lead in leads_database.csv, generates a context-aware Pitch
Kit built ONLY from real CSV fields (rating, review_count, niche, city, phone):

  * Reputation Gap   - Maps authority vs. zero web-search presence
  * Cold Call Script - pattern-interrupt opener using real metrics
  * SMS Hook         - <160-char text
  * Email Sequence   - 3 short steps (hook -> value -> CTA)
  * Review Summary   - characterization of their aggregate rating

Outputs:
  /outputs/pitch/<slug>.md       human-readable kit per lead
  /outputs/pitch_assets.json     consolidated kit the dashboard Pitch Panel loads

INTEGRITY: This does NOT invent verbatim customer reviews. When the CSV has a
`review_summary_seed` (populated by find_leads.py via the Places API), it is used;
otherwise the review summary is phrased from the aggregate rating/count only.
All copy is a DRAFT for manual use. Before sending: confirm the phone, and comply
with TCPA (calls/texts), the DNC registry, and CAN-SPAM (email). No auto-sending.

Usage:
    python pitch_studio.py            # all leads
    python pitch_studio.py --slug reds-handyman
"""

from __future__ import annotations

import argparse
import csv
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "leads_database.csv")
PITCH_DIR = os.path.join(BASE_DIR, "pitch")
JSON_PATH = os.path.join(BASE_DIR, "pitch_assets.json")


def has_metrics(lead: dict) -> tuple[str, str]:
    return (lead.get("rating", "").strip(), lead.get("review_count", "").strip())


def reputation_gap(lead: dict) -> str:
    rating, reviews = has_metrics(lead)
    city = lead.get("city", "your area")
    niche = (lead.get("niche", "local service") or "local service").lower()
    if rating and reviews:
        return (f"{rating}★ across {reviews} reviews on Google Maps "
                f"— but 0% official web presence when people search "
                f"“{niche} in {city}.”")
    if reviews:
        return (f"{reviews} reviews on Maps — strong local authority, "
                f"yet no website shows up when customers look you up.")
    return (f"Clear word-of-mouth reputation in {city} — but no website "
            f"to capture the customers already searching for a {niche}.")


def call_script(lead: dict) -> str:
    biz = lead.get("business_name", "there")
    rating, reviews = has_metrics(lead)
    city = lead.get("city", "the area")
    niche = (lead.get("niche", "local service") or "local service").lower()
    if rating and reviews:
        hook = (f"I was looking for a {niche} in {city} and found {biz} — "
                f"you've got a {rating}-star rating with {reviews} reviews, which is "
                f"honestly excellent. But here's why I'm calling: you don't have a "
                f"website, so when people find that great rating, there's nowhere to "
                f"send them to see your work or book you.")
    elif reviews:
        hook = (f"I came across {biz} while looking for a {niche} in {city} — "
                f"{reviews} reviews, clearly a strong local reputation. The thing is, "
                f"you don't have a website, so a lot of those interested customers hit "
                f"a dead end online.")
    else:
        hook = (f"I was searching for a {niche} in {city} and your name keeps coming "
                f"up by word of mouth — but there's no website when people try to "
                f"look you up, so you're likely losing customers who never find you.")
    return (
        f"COLD CALL SCRIPT — {biz}\n"
        f"(Goal: book a 5-minute look at a free mockup. Keep it conversational.)\n\n"
        f"OPENER (pattern interrupt):\n"
        f"  “Hey, is this the owner? Quick question — {hook}”\n\n"
        f"PERMISSION:\n"
        f"  “I actually already built a free demo of what a site could look like "
        f"for {biz}. Mind if I send it over so you can see it — no obligation?”\n\n"
        f"OFFER:\n"
        f"  “It's a one-time $500 to set up and $50/month to host and maintain it. "
        f"Most clients make that back from the first job or two it brings in.”\n\n"
        f"CLOSE:\n"
        f"  “What's the best email or number to send the demo link to?”\n\n"
        f"IF NOT NOW: “Totally fair — can I text you the demo link so you can "
        f"look when you have a sec?”"
    )


def sms_hook(lead: dict) -> str:
    biz = lead.get("business_name", "you")
    city = lead.get("city", "")
    rating, _ = has_metrics(lead)
    cred = f"your {rating}★ rep" if rating else "your reputation"
    msg = (f"Hi, this is [Name]. Big fan of {biz}—{cred} in {city} is great, but "
           f"you've got no website. I built a free demo to show you. Want the link?")
    if len(msg) > 160:
        msg = (f"Hi, it's [Name]. {biz} has a great local rep but no website—"
               f"I built a free demo. Want the link?")
    return msg


def email_sequence(lead: dict) -> str:
    biz = lead.get("business_name", "your business")
    city = lead.get("city", "your area")
    niche = (lead.get("niche", "local service") or "local service").lower()
    rating, reviews = has_metrics(lead)
    cred = (f"a {rating}-star rating with {reviews} reviews" if rating and reviews
            else "a strong local reputation")
    return (
        f"EMAIL 1 — The hook (day 0)\n"
        f"Subject: a quick demo site for {biz}\n\n"
        f"Hi [First Name],\n"
        f"I found {biz} while looking for a {niche} in {city} — you've got {cred}, "
        f"which is fantastic. But you don't have a website, so customers who find you "
        f"online have nowhere to go. I built a free demo to show what that could look "
        f"like: [demo link]. Worth a 2-minute look?\n— [Name]\n\n"
        f"EMAIL 2 — The value (day 3)\n"
        f"Subject: re: a quick demo site for {biz}\n\n"
        f"Hi [First Name], following up with the demo: [demo link]. It's mobile-first "
        f"with a tap-to-call button and a contact form, so leads reach you instantly. "
        f"Setup is a one-time $500, then $50/month for hosting + maintenance.\n— [Name]\n\n"
        f"EMAIL 3 — The close (day 7)\n"
        f"Subject: should I take the {biz} demo down?\n\n"
        f"Hi [First Name], I'll keep the demo up a few more days: [demo link]. If you'd "
        f"like it live (or want changes first), just reply and I'll handle the rest.\n— [Name]\n"
    )


def review_summary(lead: dict) -> str:
    seed = (lead.get("review_summary_seed", "") or "").strip()
    biz = lead.get("business_name", "this business")
    rating, reviews = has_metrics(lead)
    niche = (lead.get("niche", "local service") or "local service").lower()
    city = lead.get("city", "the area")
    if seed:
        return (f"From recent customer feedback, {biz} is praised for: {seed}. "
                f"Use these themes as personalization hooks (paraphrase — don't "
                f"quote verbatim).")
    if rating and reviews:
        return (f"With a {rating}-star average across {reviews} reviews, {biz} is among "
                f"the better-rated {niche}s in {city}. That hard-won reputation is the "
                f"single strongest selling point — a website simply makes it visible "
                f"to the people already searching. (No verbatim reviews were available to "
                f"this engine; pull the top 3 from their Maps listing to personalize.)")
    return (f"{biz} appears to run largely on word-of-mouth in {city}. Aggregate review "
            f"data wasn't captured for this lead — pull their latest Maps/Yelp "
            f"reviews to craft a personalization hook before outreach.")


COMPLIANCE = (
    "\n---\nDRAFT FOR MANUAL USE. Confirm the phone number before contacting. "
    "Cold calls/texts are governed by TCPA & the DNC registry; cold email by "
    "CAN-SPAM (include a real address + opt-out). Do not auto-send.\n"
)


def why_us(lead: dict) -> str:
    biz = lead.get("business_name", "your business")
    return (
        "WHY US — positioning (honest edges, no competitor named):\n"
        f"  - You see it first: a finished, working demo for {biz} before you pay a cent.\n"
        "  - Live in days, not weeks.\n"
        "  - Flat $500 setup + $50/month — no hourly “coding time” bills, no surprises.\n"
        "  - Mobile-first with tap-to-call + a contact form, so leads reach you instantly.\n"
        "  - Plain English, zero tech stress — hosting, updates, and edits handled for you."
    )


def build_kit(lead: dict) -> dict:
    return {
        "business_name": lead.get("business_name", ""),
        "niche": lead.get("niche", ""),
        "city": lead.get("city", ""),
        "reputation_gap": reputation_gap(lead),
        "why_us": why_us(lead),
        "call_script": call_script(lead),
        "sms_hook": sms_hook(lead),
        "email_sequence": email_sequence(lead),
        "review_summary": review_summary(lead),
    }


def kit_to_md(kit: dict) -> str:
    return (
        f"# Pitch Kit — {kit['business_name']}\n"
        f"_{kit['niche']} · {kit['city']}, CA_\n\n"
        f"## Reputation Gap\n{kit['reputation_gap']}\n\n"
        f"## Why Us (positioning)\n{kit['why_us']}\n\n"
        f"## Review Summary (personalization hook)\n{kit['review_summary']}\n\n"
        f"## Cold Call Script\n```\n{kit['call_script']}\n```\n\n"
        f"## SMS Hook (<160 chars)\n```\n{kit['sms_hook']}\n```\n\n"
        f"## Email Sequence\n```\n{kit['email_sequence']}\n```\n"
        f"{COMPLIANCE}"
    )


def load_leads() -> list[dict]:
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"ERROR: {CSV_PATH} not found. Run find_leads.py first.")
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate per-lead pitch kits (Tier 2).")
    ap.add_argument("--slug", help="Only build this slug.")
    args = ap.parse_args(argv)

    leads = load_leads()
    os.makedirs(PITCH_DIR, exist_ok=True)
    bundle = {}
    built = 0
    for lead in leads:
        slug = (lead.get("slug") or "").strip()
        if not slug or (args.slug and slug != args.slug):
            continue
        kit = build_kit(lead)
        bundle[slug] = kit
        with open(os.path.join(PITCH_DIR, f"{slug}.md"), "w", encoding="utf-8") as fh:
            fh.write(kit_to_md(kit))
        built += 1
        print(f"  pitch  pitch/{slug}.md  ({kit['business_name']})")

    # Merge into consolidated JSON (preserve kits not rebuilt this run).
    existing = {}
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, encoding="utf-8") as fh:
                existing = json.load(fh).get("leads", {})
        except (OSError, json.JSONDecodeError):
            existing = {}
    existing.update(bundle)
    with open(JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump({"leads": existing}, fh, ensure_ascii=False, indent=2)

    print(f"\nDone. {built} pitch kit(s) -> {PITCH_DIR}; consolidated -> {JSON_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
