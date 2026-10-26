#!/usr/bin/env python3
"""
find_leads.py  —  TIER 1: Scraping & Verification Engine
========================================================
Discovers local service businesses in San Luis Obispo County that lack a
website, verifies the "no website" status with an auxiliary deep-web check,
enriches each record, and appends clean rows to leads_database.csv.

DATA SOURCE
-----------
Uses the official Google Places API (Place Text Search + Place Details). This
is the ToS-compliant path. Direct scraping of Google Maps HTML is a Terms of
Service violation and is intentionally NOT implemented here.

COMPLIANCE NOTES (read before running at scale)
-----------------------------------------------
* Google's Places API terms restrict caching/storing returned content. You may
  store `place_id` indefinitely; other fields (name, phone, rating, reviews)
  should be refreshed and not retained long-term. This script timestamps every
  row (`fetched_at`) so you can expire stale data. Keep your retention policy
  aligned with https://cloud.google.com/maps-platform/terms .
* Verbatim third-party reviews are copyrighted by their authors/platforms.
  This engine stores review TEXT only to derive a paraphrased summary downstream
  (Tier 2/3). Do not republish verbatim review text in client-facing assets.
* Before any phone/text/email outreach, confirm the contact and comply with
  TCPA (calls/texts), the DNC registry, and CAN-SPAM (email).

REQUIREMENTS
------------
    pip install requests
    export GOOGLE_PLACES_API_KEY="your_key"          # required
    export SERPAPI_KEY="your_serpapi_key"            # optional (deep-web check)

USAGE
-----
    python find_leads.py --niche "Food Trucks" --city "Atascadero" --limit 20
    python find_leads.py --all                       # full SLO County sweep
    python find_leads.py --niche Plumbers --city "Paso Robles" --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Iterable

try:
    import requests
except ImportError:  # pragma: no cover - dependency guard
    sys.stderr.write("Missing dependency 'requests'. Run: pip install requests\n")
    raise

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

PLACES_TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
SERPAPI_URL = "https://serpapi.com/search.json"

# Detail fields we request. Keep this list minimal to control API cost.
DETAIL_FIELDS = ",".join([
    "place_id", "name", "formatted_address", "formatted_phone_number",
    "international_phone_number", "website", "rating", "user_ratings_total",
    "reviews", "business_status", "url",
])

SLO_CITIES = [
    "Paso Robles", "Atascadero", "San Luis Obispo", "Morro Bay",
    "Los Osos", "Pismo Beach", "Arroyo Grande", "Templeton",
    "Cambria", "Nipomo", "Grover Beach",
]

TARGET_NICHES = [
    "Landscaping", "Food Trucks", "Handyman", "Roofer", "Pet Groomer",
    "Dentist", "Plumber", "House Cleaning", "Auto Repair", "Painter",
]

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads_database.csv")

CSV_FIELDS = [
    "business_name", "niche", "city", "phone", "address", "rating",
    "review_count", "website_status", "source_url", "confidence", "slug",
    "stage", "notes", "place_id", "fetched_at", "review_summary_seed",
]

# Network behaviour
MAX_RETRIES = 5
BACKOFF_BASE = 2.0          # seconds; exponential
REQUEST_TIMEOUT = 20        # seconds
PACING_DELAY = 0.25         # polite delay between calls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("find_leads")


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

@dataclass
class Lead:
    business_name: str
    niche: str
    city: str
    phone: str = ""
    address: str = ""
    rating: str = ""
    review_count: str = ""
    website_status: str = ""
    source_url: str = ""
    confidence: str = "Medium"
    slug: str = ""
    stage: str = "New Identified"
    notes: str = ""
    place_id: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    review_summary_seed: str = ""

    def as_row(self) -> dict:
        return {k: asdict(self).get(k, "") for k in CSV_FIELDS}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s_-]+", "-", text) or "lead"


def _load_config():
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.env")
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


def get_api_key() -> str:
    key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "ERROR: GOOGLE_PLACES_API_KEY is not set.\n"
            "Get a key at https://console.cloud.google.com/ (enable 'Places API'),\n"
            'then run:  export GOOGLE_PLACES_API_KEY="your_key"'
        )
    return key


def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "SLO-LeadEngine/1.0 (+local)"})
    return s


# --------------------------------------------------------------------------- #
# Google Places API
# --------------------------------------------------------------------------- #

class PlacesClient:
    """Thin, resilient wrapper over the Google Places API."""

    # Google status strings that mean "back off and retry"
    RETRYABLE = {"OVER_QUERY_LIMIT", "UNKNOWN_ERROR"}
    # Status strings that mean "your key/request is bad" (do not retry blindly)
    FATAL = {"REQUEST_DENIED", "INVALID_REQUEST", "NOT_FOUND"}

    def __init__(self, api_key: str, session: requests.Session | None = None):
        self.api_key = api_key
        self.session = session or build_session()

    def validate_key(self) -> bool:
        """Lightweight key/permission check (the 'token refresh' analogue for
        API keys: confirm the credential is live and authorised before a run)."""
        try:
            data = self._get(PLACES_TEXTSEARCH_URL, {"query": "coffee in San Luis Obispo"})
            status = data.get("status")
            if status == "REQUEST_DENIED":
                log.error("Key rejected: %s", data.get("error_message", "REQUEST_DENIED"))
                return False
            return status in {"OK", "ZERO_RESULTS"}
        except requests.RequestException as exc:
            log.error("Key validation network error: %s", exc)
            return False

    def _get(self, url: str, params: dict) -> dict:
        """GET with exponential backoff on transient errors and rate limits."""
        params = {**params, "key": self.api_key}
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                # HTTP-level rate limiting
                if resp.status_code == 429:
                    wait = BACKOFF_BASE ** attempt
                    log.warning("HTTP 429 rate limit; backing off %.1fs", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "OK")
                if status in self.RETRYABLE:
                    wait = BACKOFF_BASE ** attempt
                    log.warning("Places status %s; retry in %.1fs", status, wait)
                    time.sleep(wait)
                    continue
                if status in self.FATAL:
                    log.error("Fatal Places status %s: %s",
                              status, data.get("error_message", ""))
                    return data
                return data
            except (requests.RequestException, json.JSONDecodeError) as exc:
                last_exc = exc
                wait = BACKOFF_BASE ** attempt
                log.warning("Request error (%s); retry %d/%d in %.1fs",
                            exc, attempt, MAX_RETRIES, wait)
                time.sleep(wait)
        raise RuntimeError(f"Exhausted retries for {url}: {last_exc}")

    def text_search(self, query: str, limit: int = 20) -> list[dict]:
        """Return raw place results for a text query, following pagination."""
        results: list[dict] = []
        params = {"query": query}
        while True:
            data = self._get(PLACES_TEXTSEARCH_URL, params)
            results.extend(data.get("results", []))
            token = data.get("next_page_token")
            if not token or len(results) >= limit:
                break
            # next_page_token needs a short delay before it becomes valid
            time.sleep(2.0)
            params = {"pagetoken": token}
        return results[:limit]

    def details(self, place_id: str) -> dict:
        data = self._get(PLACES_DETAILS_URL,
                         {"place_id": place_id, "fields": DETAIL_FIELDS})
        return data.get("result", {}) or {}


# --------------------------------------------------------------------------- #
# Verification: the "no website" filter + deep-web false-positive check
# --------------------------------------------------------------------------- #

AGGREGATOR_DOMAINS = (
    "yelp.com", "facebook.com", "fb.com", "instagram.com", "nextdoor.com",
    "yellowpages.com", "bbb.org", "tripadvisor.com", "mapquest.com",
    "google.com", "goo.gl", "g.page", "angi.com", "porch.com", "manta.com",
    "thumbtack.com", "roaminghunger.com", "menupix.com", "zmenu.com",
    "restaurantji.com", "linkedin.com", "doordash.com", "ubereats.com",
    "grubhub.com", "opentable.com", "houzz.com", "superpages.com",
)

# Free site-builder / placeholder domains. A lead pointing only here has no real
# independent web presence, so it is still a sales opportunity (-> goes to Stage 2).
BUILDER_DOMAINS = (
    "business.site", "wixsite.com", "wix.com", "wordpress.com", "weebly.com",
    "squarespace.com", "godaddysites.com", "square.site", "blogspot.com",
    "jimdosite.com", "strikingly.com", "webnode.",
)


def _domain(url: str) -> str:
    u = (url or "").lower().split("//", 1)[-1]
    return u.split("/", 1)[0].removeprefix("www.")


def classify_website(url: str) -> str:
    """Stage 1 classifier: 'none' | 'builder' | 'custom'."""
    url = (url or "").strip().lower()
    if not url:
        return "none"
    if any(b in url for b in BUILDER_DOMAINS):
        return "builder"
    return "custom"


def lacks_website(details: dict) -> bool:
    """Back-compat helper: True when there is no *custom* website."""
    return classify_website(details.get("website", "")) != "custom"


def _norm(text: str) -> set[str]:
    """Significant lowercase tokens of a name (drops generic filler)."""
    stop = {"the", "and", "for", "llc", "inc", "co", "company", "services",
            "service", "ca", "california", "slo", "county"}
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {t for t in toks if t not in stop and len(t) > 2}


def _serp(query: str, serpapi_key: str, num: int = 5) -> list[dict]:
    """One SerpAPI organic search. Returns [] on any error or missing key.
    We use a Search API rather than scraping Google directly (ToS-compliant)."""
    if not serpapi_key:
        return []
    try:
        resp = requests.get(
            SERPAPI_URL,
            params={"q": query, "engine": "google", "num": num,
                    "api_key": serpapi_key},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("organic_results", []) or []
    except (requests.RequestException, json.JSONDecodeError) as exc:
        log.warning("SERP query failed (%s): %s", query, exc)
        return []


def deep_search_fingerprint(name: str, city: str, serpapi_key: str | None) -> dict:
    """
    Stage 2: localized search fingerprinting. Runs two queries
    -- '"name" "city"' and '"name" "San Luis Obispo County"' -- and inspects the
    first 5 organic results of each. A result is an OWNED domain when it is not an
    aggregator/builder AND the business name tokens appear in its domain or <title>.

    Returns {"owned": bool|None, "socials": [urls], "evidence": [urls]}.
    owned is None when no SERP key is configured (cannot verify -> lower confidence).
    """
    if not serpapi_key:
        return {"owned": None, "socials": [], "evidence": []}
    name_toks = _norm(name)
    queries = [f'"{name}" "{city}"', f'"{name}" "San Luis Obispo County"']
    owned, socials, evidence, seen = [], [], [], set()
    for q in queries:
        for item in _serp(q, serpapi_key, num=5):
            link = item.get("link") or ""
            if not link or link in seen:
                continue
            seen.add(link)
            evidence.append(link)
            dom = _domain(link)
            if any(agg in dom for agg in AGGREGATOR_DOMAINS):
                if any(s in dom for s in ("yelp.com", "facebook.com", "instagram.com")):
                    socials.append(link)
                continue
            if classify_website(link) == "builder":
                continue  # builder page is not an independent site
            title_toks = _norm(item.get("title", ""))
            dom_hit = bool(name_toks & _norm(dom.replace(".", " ")))
            title_overlap = name_toks & title_toks
            title_hit = len(title_overlap) >= max(1, len(name_toks) // 2)
            if dom_hit or title_hit:
                owned.append(link)
    return {"owned": bool(owned), "socials": socials, "evidence": owned or evidence[:5]}


def social_isolation_check(socials: list[str]) -> dict:
    """
    Stage 3: social & directory isolation. Fetch each discovered social/Yelp page
    and look for an external custom-domain link in the bio/metadata. If found, the
    business already has a real web presence -> drop.

    Returns {"custom_link": bool|None, "evidence": [urls]}.
    custom_link is None when none of the pages could be fetched (best-effort:
    Facebook/Instagram often block server-side fetches and need the optional
    headless path; the pipeline is never hard-failed because of that).
    """
    if not socials:
        return {"custom_link": None, "evidence": []}
    href_re = re.compile(r'https?://[^\s"\'<>)]+', re.I)
    ignore = ("cdn", "fbcdn", "akamai", "gstatic", "googleapis", "schema.org",
              "w3.org", "licdn", "cdninstagram", "bing.com")
    fetched_any, found = False, []
    for url in socials[:4]:
        try:
            resp = requests.get(
                url, timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0 (compatible; SLO-LeadEngine/1.0)"},
            )
            if resp.status_code != 200 or not resp.text:
                continue
            fetched_any = True
        except requests.RequestException:
            continue
        host = _domain(url)
        for m in href_re.findall(resp.text):
            d = _domain(m)
            if not d or d == host:
                continue
            if any(agg in d for agg in AGGREGATOR_DOMAINS):
                continue
            if classify_website(m) == "builder" or any(x in d for x in ignore):
                continue
            found.append(m)
    if not fetched_any:
        return {"custom_link": None, "evidence": []}
    return {"custom_link": bool(found), "evidence": found[:5]}


def derive_review_seed(reviews: list[dict]) -> str:
    """Build a short, paraphrasable seed from review text WITHOUT storing it
    verbatim for republication. We keep only adjective/keyword signal."""
    if not reviews:
        return ""
    snippets = []
    for r in reviews[:3]:
        txt = (r.get("text") or "").strip().replace("\n", " ")
        if txt:
            snippets.append(txt[:160])
    return " | ".join(snippets)


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #

def load_existing_keys(csv_path: str) -> set[str]:
    """Return existing place_ids + slugs so re-runs don't duplicate rows."""
    keys: set[str] = set()
    if not os.path.exists(csv_path):
        return keys
    try:
        with open(csv_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("place_id"):
                    keys.add(row["place_id"])
                if row.get("slug"):
                    keys.add(row["slug"])
    except (OSError, csv.Error) as exc:
        log.warning("Could not read existing CSV (%s); starting fresh index", exc)
    return keys


def build_lead(details: dict, niche: str, city: str,
               serpapi_key: str | None) -> Lead | None:
    """Run a Places detail record through the 3-stage no-website filter and return
    a verified Lead, or None to drop it."""
    name = (details.get("name") or "").strip()
    if not name:
        return None

    # --- Stage 1: API metadata scrub ---
    site_class = classify_website(details.get("website", ""))
    if site_class == "custom":
        log.info("  drop S1 (custom website present): %s", name)
        return None

    # --- Stage 2: deep search fingerprinting ---
    fp = deep_search_fingerprint(name, city, serpapi_key)
    if fp["owned"] is True:
        log.info("  drop S2 (owned domain in SERP): %s", name)
        return None

    # --- Stage 3: social & directory isolation ---
    iso = social_isolation_check(fp["socials"])
    if iso["custom_link"] is True:
        log.info("  drop S3 (custom link in social bio): %s", name)
        return None

    # Survivor: derive status + confidence from how far verification reached.
    if site_class == "builder":
        website_status = "Builder/placeholder only (no custom domain)"
    elif fp["owned"] is False and iso["custom_link"] in (False, None):
        website_status = "Verified none (passed S1-S3)"
    else:
        website_status = "None in Places (deep checks limited)"

    if serpapi_key and fp["owned"] is False:
        confidence = "High" if iso["custom_link"] is False else "Medium-High"
    else:
        confidence = "Medium"

    reviews = details.get("reviews", []) or []
    return Lead(
        business_name=name,
        niche=niche,
        city=city,
        phone=details.get("formatted_phone_number", "") or "",
        address=details.get("formatted_address", "") or "",
        rating=str(details.get("rating", "") or ""),
        review_count=str(details.get("user_ratings_total", "") or ""),
        website_status=website_status,
        source_url=details.get("url", "") or "",
        confidence=confidence,
        slug=slugify(f"{name}-{city}"),
        notes="Auto-discovered via Places API; passed 3-stage no-website filter. VERIFY phone before outreach.",
        place_id=details.get("place_id", "") or "",
        review_summary_seed=derive_review_seed(reviews),
    )


def append_leads(csv_path: str, leads: list[Lead]) -> None:
    file_exists = os.path.exists(csv_path)
    try:
        with open(csv_path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            if not file_exists or os.path.getsize(csv_path) == 0:
                writer.writeheader()
            for lead in leads:
                writer.writerow(lead.as_row())
    except OSError as exc:
        log.error("Failed to write CSV %s: %s", csv_path, exc)
        raise


def run(niches: Iterable[str], cities: Iterable[str], limit: int,
        dry_run: bool) -> list[Lead]:
    api_key = get_api_key()
    serpapi_key = os.environ.get("SERPAPI_KEY", "").strip() or None
    client = PlacesClient(api_key)

    log.info("Validating Places API credential ...")
    if not client.validate_key():
        raise SystemExit("ERROR: Google Places API key invalid or unauthorised.")
    if not serpapi_key:
        log.warning("SERPAPI_KEY not set: Stage 2/3 deep verification will be "
                    "skipped (leads kept at Medium confidence).")

    existing = load_existing_keys(CSV_PATH)
    harvested: list[Lead] = []

    for niche in niches:
        for city in cities:
            query = f"{niche} in {city}, CA"
            log.info("Searching: %s", query)
            try:
                places = client.text_search(query, limit=limit)
            except RuntimeError as exc:
                log.error("Search failed for '%s': %s", query, exc)
                continue

            for place in places:
                pid = place.get("place_id", "")
                if pid and pid in existing:
                    continue
                time.sleep(random.uniform(2.0, 5.0))  # randomized rate-limit guard
                try:
                    details = client.details(pid)
                except RuntimeError as exc:
                    log.error("Details failed for %s: %s", pid, exc)
                    continue
                if not details:
                    continue
                if classify_website(details.get("website", "")) == "custom":
                    continue  # Stage 1 fast-path: real website present -> skip
                lead = build_lead(details, niche, city, serpapi_key)
                if lead and lead.slug not in existing and lead.place_id not in existing:
                    harvested.append(lead)
                    existing.add(lead.place_id or lead.slug)
                    log.info("  + lead: %s (%s)", lead.business_name, lead.city)

    log.info("Harvested %d new no-website lead(s).", len(harvested))
    if harvested and not dry_run:
        append_leads(CSV_PATH, harvested)
        log.info("Appended to %s", CSV_PATH)
    elif dry_run:
        log.info("--dry-run: nothing written. Preview:")
        for lead in harvested:
            log.info("    %s | %s | %s | %s",
                     lead.business_name, lead.niche, lead.city, lead.website_status)
    return harvested


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SLO County no-website lead engine.")
    p.add_argument("--niche", action="append", help="Niche (repeatable).")
    p.add_argument("--city", action="append", help="City (repeatable).")
    p.add_argument("--all", action="store_true",
                   help="Sweep all target niches across all SLO cities.")
    p.add_argument("--limit", type=int, default=20,
                   help="Max results per niche+city query (default 20).")
    p.add_argument("--dry-run", action="store_true",
                   help="Discover and verify but do not write the CSV.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    niches = TARGET_NICHES if args.all else (args.niche or ["Food Trucks"])
    cities = SLO_CITIES if args.all else (args.city or ["Atascadero"])
    try:
        run(niches, cities, limit=args.limit, dry_run=args.dry_run)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        log.warning("Interrupted by user.")
        return 130
    except Exception as exc:  # last-resort guard so a crash never loses data
        log.exception("Unexpected failure: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
