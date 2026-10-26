#!/usr/bin/env python3
"""
run_pipeline.py  —  one-command orchestrator for the SLO lead engine.

Order: find_leads.py (discovery) -> generate_mockups.py -> pitch_studio.py -> build_dashboard.py
Reads config.env for keys/agency details. WITHOUT a Google Places key it skips live
discovery and simply rebuilds the mockups/pitch/dashboard from the existing CSV, so
a daily run is always safe. Everything is logged to pipeline_log.txt.

Usage:
    python run_pipeline.py                         # rotating niche x all cities (daily)
    python run_pipeline.py --all                   # full niche x city sweep
    python run_pipeline.py --niche "Food Trucks" --city Atascadero
"""
from __future__ import annotations

import argparse
import datetime
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "pipeline_log.txt")
CSV = os.path.join(BASE, "leads_database.csv")

NICHES = ["Food Trucks", "Handyman", "Pet Groomer", "Landscaping",
          "Roofer", "Plumber", "Tree Service"]
CITIES = ["Paso Robles", "Atascadero", "San Luis Obispo", "Morro Bay",
          "Los Osos", "Pismo Beach", "Arroyo Grande"]


def log(msg: str) -> None:
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def load_config() -> None:
    cfg = os.path.join(BASE, "config.env")
    if not os.path.exists(cfg):
        return
    for raw in open(cfg, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if v and not v.startswith("["):   # ignore placeholder values
            os.environ[k] = v


def count_leads() -> int:
    if not os.path.exists(CSV):
        return 0
    with open(CSV, encoding="utf-8") as fh:
        return max(0, sum(1 for _ in fh) - 1)


def run(cmd: list[str]) -> bool:
    log("RUN: " + " ".join(cmd[1:]))
    try:
        r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1800)
        for ln in (r.stdout or "").splitlines():
            if ln.strip():
                log("    " + ln.strip())
        if r.returncode != 0:
            log(f"    ! exit {r.returncode}: {(r.stderr or '').strip()[:400]}")
        return r.returncode == 0
    except Exception as exc:  # noqa: BLE001
        log(f"    ! failed: {exc}")
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the full SLO lead pipeline.")
    ap.add_argument("--all", action="store_true", help="Full niche x city sweep.")
    ap.add_argument("--niche", action="append", help="Niche (repeatable).")
    ap.add_argument("--city", action="append", help="City (repeatable).")
    args = ap.parse_args(argv)

    load_config()
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")  # children print UTF-8 accented names on cp1252 consoles
    py = sys.executable
    before = count_leads()
    log("===== pipeline start =====")

    if os.environ.get("GOOGLE_PLACES_API_KEY", "").strip():
        if args.all:
            run([py, "find_leads.py", "--all"])
        else:
            niches = args.niche or [NICHES[datetime.date.today().toordinal() % len(NICHES)]]
            cities = args.city or CITIES
            cmd = [py, "find_leads.py", "--limit", "20"]
            for n in niches:
                cmd += ["--niche", n]
            for c in cities:
                cmd += ["--city", c]
            log(f"Discovery focus today: {', '.join(niches)} across {len(cities)} cities")
            run(cmd)
    else:
        log("No GOOGLE_PLACES_API_KEY in config.env -> skipping live discovery; "
            "rebuilding assets from existing leads_database.csv.")

    run([py, "generate_mockups.py"])
    run([py, "generate_variants.py"])
    run([py, "pitch_studio.py"])
    run([py, "build_dashboard.py"])
    run([py, "build_gallery.py"])
    run([py, "build_viewer.py"])

    after = count_leads()
    log(f"SUMMARY: {after} leads total ({after - before:+d} today). "
        f"Dashboard: lead-command-center.html")
    log("===== pipeline done =====")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
