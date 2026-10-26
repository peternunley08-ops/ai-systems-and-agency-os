#!/usr/bin/env python3
"""
generate_mockups.py  —  TIER 3 (UPGRADED): Dynamic Layout Engine & Anti-Template Matrix
=======================================================================================
Each lead is routed through a multi-variable Design Router so no two pages share
the generic "standard corporate" template.

DESIGN ROUTER
-------------
1. Industry Archetype  (palette + typography + vibe):
     * Artisanal / Craftsman   -> Food Trucks, bakers, boutique creators
         editorial, asymmetrical, warm cream bg, serif + mono, amber accents
     * Heavy-Duty Professional -> Handymen, Plumbers, Roofers, Landscapers
         ultra-clean, high-trust, navy/slate, heavy display sans, safety-orange CTA
     * Lifestyle / Caregiver   -> Pet Groomers, Salons, Wellness
         soft minimalist, oatmeal/sage/terracotta, modern serif, generous whitespace
2. Layout variants (cycled deterministically per slug so same-niche leads differ):
     * Hero:     A asymmetric split | B brutalist statement + float grid | C off-center minimal + full-bleed
     * Services: bento grid (flagship) | hover accordion list | alternating Z-pattern
3. Premium elements on every page:
     * Glassy floating nav (backdrop-filter blur, solidifies on scroll)
     * Mobile "Conversion Utility" bar pinned to bottom (one-tap call + hours)
     * Pure-CSS micro-interactions (magnetic buttons, translate/shadow, animated underlines)

CONSTRAINTS (enforced)
----------------------
  * ZERO external CDNs / fonts / scripts. Spec'd display faces (Playfair Display,
    Oswald, Fraunces, etc.) are listed FIRST in each font stack so they render when
    locally installed, then fall back to robust system fonts. Nothing is fetched.
  * Real aggregate rating / review count injected when present in the CSV.
  * Testimonials are CLEARLY-LABELED SAMPLE placeholders — no verbatim third-party
    review text is republished. Demo "hours" are illustrative site chrome, not data.

The HTML/CSS/JS shell lives in mockup_template.html (kept separate so this file
stays readable and writeable). Usage:
    python generate_mockups.py                 # build all leads
    python generate_mockups.py --slug reds-handyman
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import sys
from datetime import datetime

import i18n_seo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "leads_database.csv")
OUT_DIR = os.path.join(BASE_DIR, "mockups")
TEMPLATE_FILE = os.path.join(BASE_DIR, "mockup_template.html")

# --------------------------------------------------------------------------- #
# Inline SVG icons (24x24, stroke=currentColor). No external assets.
# --------------------------------------------------------------------------- #
ICONS = {
    "wrench": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2-2 2.5-2.5z"/>',
    "paint": '<path d="M19 3H5a2 2 0 0 0-2 2v6h18V5a2 2 0 0 0-2-2zM3 11v2a2 2 0 0 0 2 2h6v3a2 2 0 0 0 2 2 2 2 0 0 0 2-2v-5H3z"/>',
    "hammer": '<path d="M14 6l4 4-7 7-4-4zM14 6l3-3 4 4-3 3M3 21l4-4"/>',
    "home": '<path d="M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10"/>',
    "fence": '<path d="M4 9l2-2 2 2v11H4zM10 9l2-2 2 2v11h-4zM16 9l2-2 2 2v11h-4zM2 13h20M2 17h20"/>',
    "check": '<path d="M20 6L9 17l-5-5"/>',
    "scissors": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4L8.1 15.9M14.5 14.5L20 20M8.1 8.1L12 12"/>',
    "paw": '<circle cx="7" cy="9" r="2"/><circle cx="12" cy="6" r="2"/><circle cx="17" cy="9" r="2"/><path d="M12 12c-3 0-5 2.2-5 4.5S9 20 12 20s5-1.2 5-3.5S15 12 12 12z"/>',
    "bath": '<path d="M4 12h16v3a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4zM6 12V6a2 2 0 0 1 2-2 2 2 0 0 1 2 2"/>',
    "truck": '<path d="M3 6h11v9H3zM14 9h4l3 3v3h-7zM7 18a1.5 1.5 0 1 0 0 .01M18 18a1.5 1.5 0 1 0 0 .01"/>',
    "calendar": '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/>',
    "phone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2 4.2 2 2 0 0 1 4 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.2-1.2a2 2 0 0 1 2.1-.5c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    "star": '<path d="M12 2l3 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.9 21l1.2-6.8-5-4.9 6.9-1z"/>',
    "leaf": '<path d="M11 20A7 7 0 0 1 4 13c0-6 8-9 16-9 0 8-3 16-9 16zM4 20c4-2 6-5 8-9"/>',
    "spark": '<path d="M12 2v6M12 16v6M2 12h6M16 12h6M5 5l4 4M15 15l4 4M19 5l-4 4M9 15l-4 4"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "map": '<path d="M9 3L3 6v15l6-3 6 3 6-3V3l-6 3-6-3zM9 3v15M15 6v15"/>',
    "utensils": '<path d="M4 3v7a2 2 0 0 0 2 2 2 2 0 0 0 2-2V3M6 12v9M16 3c-1.5 0-3 1.8-3 4.5S14.5 12 16 12v9"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
}


def icon(name: str, size: int = 26) -> str:
    body = ICONS.get(name, ICONS["check"])
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
            f'width="{size}" height="{size}" aria-hidden="true">{body}</svg>')


# --------------------------------------------------------------------------- #
# Archetypes: palette, fonts, geometry
# --------------------------------------------------------------------------- #
ARCHETYPES = {
    "artisanal": {
        "BG": "#f7f1e6", "SURFACE": "#fffaf2", "SURFACE2": "#f1e7d4",
        "INK": "#241f18", "MUTED": "#7c6f59", "LINE": "#e6d9c1",
        "C1": "#c8761f", "C2": "#7c3a14", "DARK": "#2a2118", "ACCENT_TEXT": "#fff",
        "RADIUS": "12px", "RADIUS_LG": "26px", "BDW": "1px",
        "SHADOW": "0 16px 40px rgba(64,38,8,.14)",
        "F_DISPLAY": '"Playfair Display","DM Serif Display",Georgia,"Times New Roman",serif',
        "F_BODY": 'Georgia,"Iowan Old Style","Palatino Linotype",serif',
        "F_MONO": '"Space Mono","DM Mono","SFMono-Regular",ui-monospace,"Courier New",monospace',
    },
    "heavy": {
        "BG": "#eef1f6", "SURFACE": "#ffffff", "SURFACE2": "#e2e8f1",
        "INK": "#0e1726", "MUTED": "#566076", "LINE": "#cdd7e3",
        "C1": "#ff6a00", "C2": "#0e1726", "DARK": "#0e1726", "ACCENT_TEXT": "#fff",
        "RADIUS": "8px", "RADIUS_LG": "10px", "BDW": "2px",
        "SHADOW": "0 10px 26px rgba(14,23,38,.16)",
        "F_DISPLAY": '"Oswald","Syncopate","Syne","Arial Narrow",system-ui,sans-serif',
        "F_BODY": '"Plus Jakarta Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif',
        "F_MONO": 'ui-monospace,"SFMono-Regular","Courier New",monospace',
    },
    "lifestyle": {
        "BG": "#f3efe8", "SURFACE": "#fbf9f4", "SURFACE2": "#ece4d6",
        "INK": "#3a3d2e", "MUTED": "#7d7a64", "LINE": "rgba(58,61,46,.16)",
        "C1": "#c0805a", "C2": "#8a9a6f", "DARK": "#3a3d2e", "ACCENT_TEXT": "#fff",
        "RADIUS": "24px", "RADIUS_LG": "32px", "BDW": "1px",
        "SHADOW": "0 18px 44px rgba(58,61,46,.12)",
        "F_DISPLAY": '"Fraunces","Bricolage Grotesque",Georgia,"Iowan Old Style",serif',
        "F_BODY": '"Plus Jakarta Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif',
        "F_MONO": 'ui-monospace,"SFMono-Regular","Courier New",monospace',
    },
}

NICHE_TO_ARCH = {
    "food truck": "artisanal", "bakery": "artisanal", "coffee": "artisanal",
    "handyman": "heavy", "plumber": "heavy", "roofer": "heavy",
    "landscaping": "heavy", "auto repair": "heavy", "painter": "heavy",
    "pet groomer": "lifestyle", "salon": "lifestyle", "wellness": "lifestyle",
    "house cleaning": "lifestyle",
}

HERO_BY_ARCH = {"artisanal": ["A", "B"], "heavy": ["B", "A"], "lifestyle": ["C", "A"]}
SVC_BY_ARCH = {"artisanal": ["z", "accordion"], "heavy": ["bento", "z"], "lifestyle": ["bento", "accordion"]}

# --------------------------------------------------------------------------- #
# Per-niche content
# --------------------------------------------------------------------------- #
NICHE_CONTENT = {
    "food truck": {
        "tag": "Street food worth chasing.",
        "sub": "Fresh, made-to-order favorites served hot from our truck — now bookable online for your next event.",
        "cta": "Book the Truck", "hours": "Wed-Sun 11a-8p",
        "svc": [
            ("utensils", "The Menu", "Every taco, plate, and special - see it before you arrive."),
            ("calendar", "Event Catering", "Weddings, parties, and corporate lunches, fully staffed."),
            ("map", "Find the Truck", "A live weekly schedule so regulars always track you down."),
            ("truck", "Private Bookings", "Reserve the truck for your event in two taps."),
            ("phone", "Order Ahead", "Skip the line with call-ahead pickup."),
            ("star", "Crowd Favorites", "The dishes people line up for, front and center."),
        ],
        "rev": ["Best on the Central Coast", "Catered our wedding", "A weekly ritual"],
    },
    "handyman": {
        "tag": "Your punch list, handled.",
        "sub": "Licensed, dependable home repair across the Central Coast. Free estimates, clean work, done right the first time.",
        "cta": "Get a Free Estimate", "hours": "Mon-Sat 7a-6p",
        "svc": [
            ("wrench", "Repairs & Maintenance", "From leaky faucets to sticking doors - one call fixes it."),
            ("paint", "Drywall & Painting", "Patch, texture, and paint that blends in seamlessly."),
            ("hammer", "Carpentry", "Trim, shelving, decking, and custom built-ins."),
            ("home", "Fixture Install", "Lights, fans, faucets, TVs, and hardware mounted safely."),
            ("fence", "Fencing & Gates", "Repairs and new installs built for the coast."),
            ("check", "Free Estimates", "Transparent written quotes before any work begins."),
        ],
        "rev": ["Saved my weekend", "Honest and on time", "My go-to for everything"],
    },
    "pet groomer": {
        "tag": "Grooming that comes to you.",
        "sub": "Cage-free, one-on-one mobile grooming at your doorstep - less stress for your pet, no drive for you.",
        "cta": "Book a Groom", "hours": "Tue-Sat 9a-5p",
        "svc": [
            ("scissors", "Full Groom", "Breed-specific cut, style, and finishing touches."),
            ("bath", "Bath & Brush", "Deep clean, conditioned coat, nails, and ears."),
            ("paw", "Nail & Paw Care", "Trims and grinding without the wrestling match."),
            ("spark", "De-Shedding", "Knock out loose undercoat, keep your home fur-free."),
            ("truck", "Mobile Service", "The salon comes to your driveway, fully equipped."),
            ("calendar", "Easy Rebooking", "Set a recurring schedule so they stay fresh."),
        ],
        "rev": ["My dog actually enjoys it", "So convenient", "Gentle with seniors"],
    },
    "landscaping": {
        "tag": "Curb appeal, season after season.",
        "sub": "Design, build, and maintenance for drought-smart Central Coast yards that look great and save water.",
        "cta": "Request a Quote", "hours": "Mon-Fri 7a-5p",
        "svc": [
            ("leaf", "Garden Design", "Drought-tolerant, native-forward designs built to last."),
            ("spark", "Hardscapes", "Pavers, walkways, retaining walls, and patios."),
            ("home", "Irrigation", "Efficient systems that cut your water bill."),
            ("check", "Maintenance", "Reliable weekly and biweekly care plans."),
            ("shield", "Cleanups", "Seasonal refresh, hauling, and storm prep."),
            ("phone", "Free Walk-throughs", "On-site estimates with clear pricing."),
        ],
        "rev": ["Transformed our yard", "Reliable crew", "Water bill dropped"],
    },
}

DEFAULT_CONTENT = {
    "tag": "Local service you can count on.",
    "sub": "Professional, dependable service across San Luis Obispo County - now easy to find and book online.",
    "cta": "Get in Touch", "hours": "Mon-Sat 8a-6p",
    "svc": [
        ("check", "Quality Work", "Done right, on time, every time."),
        ("phone", "Easy Booking", "Reach us in one tap from any device."),
        ("star", "5-Star Service", "The reputation your customers already give you."),
        ("clock", "Fast Response", "Quick quotes and prompt scheduling."),
        ("shield", "Licensed & Trusted", "Local, insured, and accountable."),
        ("map", "Serving the Coast", "Proudly local to SLO County."),
    ],
    "rev": ["Highly recommend", "Great experience", "Will use again"],
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

# --- V8 fresh-batch niches (tree service, house cleaning) ---
NICHE_TO_ARCH["tree service"] = "heavy"
NICHE_CONTENT["tree service"] = {
    "tag": "Your trees, in expert hands.",
    "sub": "Licensed, insured tree care across the Central Coast - trimming, removals, and 24/7 storm response, done safely and clean.",
    "cta": "Get a Free Estimate", "hours": "Mon-Sat 7a-5p",
    "svc": [
        ("leaf", "Tree Trimming", "Shaping and crown thinning that keeps trees healthy and safe."),
        ("hammer", "Tree Removal", "Safe, efficient removal of hazardous or unwanted trees."),
        ("shield", "Stump Grinding", "Grind stumps below grade and reclaim your yard."),
        ("spark", "Emergency & Storm", "24/7 response for fallen limbs and storm damage."),
        ("home", "Lot & Brush Clearing", "Defensible-space and brush clearing for fire safety."),
        ("check", "Free Estimates", "Honest, written quotes before any work begins."),
    ],
    "rev": ["Saved our oak", "Fast storm cleanup", "Fair and professional"],
}
NICHE_CONTENT["house cleaning"] = {
    "tag": "A spotless home, every time.",
    "sub": "Reliable, detail-obsessed home cleaning across the Central Coast - recurring, deep, and move-out cleans by a team you can trust.",
    "cta": "Get a Free Quote", "hours": "Mon-Sat 8a-5p",
    "svc": [
        ("spark", "Recurring Cleaning", "Weekly, biweekly, or monthly visits that keep it effortless."),
        ("bath", "Deep Cleaning", "Top-to-bottom detail: baseboards, fixtures, the works."),
        ("home", "Move In / Move Out", "Get the deposit back or start fresh in a spotless space."),
        ("shield", "Trusted & Insured", "Background-checked, insured, and consistent."),
        ("calendar", "Easy Scheduling", "Book and reschedule in a tap; no contracts."),
        ("check", "Satisfaction Promise", "Not happy with a spot? We make it right."),
    ],
    "rev": ["My house has never been cleaner", "Reliable and trustworthy", "Worth every penny"],
}


def esc(t: str) -> str:
    return html.escape(t or "", quote=True)


def vhash(slug: str) -> int:
    return int(hashlib.md5(slug.encode("utf-8")).hexdigest(), 16)


def pick(slug: str, opts: list, salt: int = 0):
    return opts[(vhash(slug) + salt) % len(opts)]


def arch_of(niche: str) -> str:
    return NICHE_TO_ARCH.get((niche or "").strip().lower(), "heavy")


def content_of(niche: str) -> dict:
    return NICHE_CONTENT.get((niche or "").strip().lower(), DEFAULT_CONTENT)


def monogram(name: str) -> str:
    words = [w for w in (name or "").replace("'", "").split() if w]
    if not words:
        return "*"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def tel_of(phone: str) -> str:
    return "".join(ch for ch in (phone or "") if ch.isdigit() or ch == "+")


def cta_button(ctx: dict, label: str, cls: str) -> str:
    if ctx["phone"]:
        return f'<a class="{cls}" href="tel:{ctx["tel"]}">{esc(label)} &middot; {esc(ctx["phone"])}</a>'
    return f'<a class="{cls}" href="#contact">{esc(label)}</a>'


# --------------------------------------------------------------------------- #
# Fragment builders
# --------------------------------------------------------------------------- #
def stats_strip(ctx: dict) -> str:
    chips = []
    if ctx["rating"]:
        chips.append(f'<div class="stat"><b>{esc(ctx["rating"])}<i class="st">&#9733;</i></b><span>Avg rating</span></div>')
    if ctx["reviews"]:
        chips.append(f'<div class="stat"><b>{esc(ctx["reviews"])}</b><span>Reviews</span></div>')
    chips.append(f'<div class="stat"><b>{esc(ctx["city"])}</b><span>Serving</span></div>')
    chips.append('<div class="stat"><b>Same-day</b><span>Quotes</span></div>')
    return '<div class="wrap"><div class="stats">' + "".join(chips) + "</div></div>"


def hero_badge(ctx: dict) -> str:
    if ctx["rating"]:
        return (f'<div class="badge"><span class="st">&#9733;</span> {esc(ctx["rating"])} '
                f'<small>&middot; {esc(ctx["reviews"] or "loved")} reviews</small></div>')
    return '<div class="badge"><span class="st">&#9733;</span> Local &amp; Trusted</div>'


def media_panel(ctx: dict) -> str:
    return (f'<div class="media">'
            f'<span class="mono-art">{esc(ctx["mono"])}</span>'
            f'<span class="media-tag">{esc(ctx["niche"])}</span>'
            f'{hero_badge(ctx)}</div>')


def hero_A(ctx: dict) -> str:  # asymmetric split
    return f"""<section class="hero hero-a">
  <div class="wrap hero-a-grid">
    <div class="hero-copy">
      <span class="eyebrow"><span class="mono">{esc(ctx["niche"])}</span> &middot; {esc(ctx["city"])}</span>
      <h1>{esc(ctx["tag"])}</h1>
      <p class="lede">{esc(ctx["sub"])}</p>
      <div class="cta-row">{ctx["cta_hero"]}<a class="btn btn-ghost mag" href="#services">See services <span class="ico">{icon("arrow",18)}</span></a></div>
    </div>
    {media_panel(ctx)}
  </div>
</section>"""


def hero_B(ctx: dict) -> str:  # brutalist statement + floating action grid
    cells = [
        ("phone", "Call / Text", ctx["phone"] or "Tap to contact"),
        ("clock", "Hours", ctx["hours"]),
        ("map", "Service area", ctx["city"] + " + Central Coast"),
        ("star", "Reputation", (ctx["rating"] + " star rated") if ctx["rating"] else "Locally loved"),
    ]
    grid = "".join(
        f'<div class="fcell"><span class="fic">{icon(i,22)}</span><div><b>{esc(t)}</b><span>{esc(v)}</span></div></div>'
        for i, t, v in cells)
    return f"""<section class="hero hero-b">
  <div class="wrap hero-b-inner">
    <span class="eyebrow"><span class="mono">{esc(ctx["niche"])}</span> &middot; {esc(ctx["city"])}, CA</span>
    <h1 class="brutal">{esc(ctx["tag"])}</h1>
    <p class="lede center">{esc(ctx["sub"])}</p>
    <div class="cta-row center">{ctx["cta_hero"]}<a class="btn btn-ghost mag" href="#services">Explore services</a></div>
    <div class="float-grid">{grid}</div>
  </div>
</section>"""


def hero_C(ctx: dict) -> str:  # off-center minimal + full-bleed strip
    feats = ctx["content"]["svc"][:4]
    strip = "".join(
        f'<div class="fb-item"><span class="fb-ic">{icon(i,24)}</span><b>{esc(t)}</b></div>'
        for i, t, _ in feats)
    return f"""<section class="hero hero-c">
  <div class="wrap hero-c-inner">
    <span class="eyebrow"><span class="mono">{esc(ctx["niche"])}</span> &middot; {esc(ctx["city"])}</span>
    <h1>{esc(ctx["tag"])}</h1>
    <p class="lede">{esc(ctx["sub"])}</p>
    <div class="cta-row">{ctx["cta_hero"]}<a class="btn btn-ghost mag" href="#contact">Book now</a></div>
  </div>
  <div class="fullbleed"><div class="wrap fb-grid">{strip}{hero_badge(ctx)}</div></div>
</section>"""


HERO_FN = {"A": hero_A, "B": hero_B, "C": hero_C}


def services_bento(ctx: dict) -> str:
    cards = []
    for idx, (i, t, d) in enumerate(ctx["content"]["svc"]):
        cls = "b-card mag-card"
        if idx == 0:
            cls += " b-flag"
        elif idx == 1:
            cls += " b-wide"
        cards.append(f'<article class="{cls}"><span class="svc-ic">{icon(i)}</span>'
                     f'<h3>{esc(t)}</h3><p>{esc(d)}</p></article>')
    return f'<div class="bento">{"".join(cards)}</div>'


def services_accordion(ctx: dict) -> str:
    rows = []
    for n, (i, t, d) in enumerate(ctx["content"]["svc"], 1):
        rows.append(
            f'<div class="acc-row" tabindex="0">'
            f'<div class="acc-head"><span class="acc-no mono">{n:02d}</span>'
            f'<span class="acc-ic">{icon(i,22)}</span><h3>{esc(t)}</h3>'
            f'<span class="acc-plus">{icon("arrow",20)}</span></div>'
            f'<div class="acc-desc"><p>{esc(d)}</p></div></div>')
    return f'<div class="acc">{"".join(rows)}</div>'


def services_zpattern(ctx: dict) -> str:
    rows = []
    for n, (i, t, d) in enumerate(ctx["content"]["svc"]):
        rev = " z-rev" if n % 2 else ""
        rows.append(
            f'<div class="z-row{rev}">'
            f'<div class="z-media"><span class="z-no mono">{n+1:02d}</span>{icon(i,40)}</div>'
            f'<div class="z-copy"><h3>{esc(t)}</h3><p>{esc(d)}</p>'
            f'<a class="z-link mag" href="#contact">Ask about this {icon("arrow",16)}</a></div></div>')
    return f'<div class="zwrap">{"".join(rows)}</div>'


SVC_FN = {"bento": services_bento, "accordion": services_accordion, "z": services_zpattern}


def reviews_block(ctx: dict) -> str:
    titles = ctx["content"]["rev"]
    bodies = [
        "Showed up exactly when they said, did beautiful work, and the price matched the quote. Couldn't ask for more.",
        "Friendly, professional, and clearly knows their craft. I've already recommended them to two neighbors.",
        "Easy to book, great communication, and the results speak for themselves. This is who I'll call from now on.",
    ]
    cards = "".join(
        f'<figure class="rev mag-card"><div class="rstars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>'
        f'<blockquote>&ldquo;{esc(bodies[k])}&rdquo;</blockquote>'
        f'<figcaption>{esc(titles[k])} &middot; Sample testimonial</figcaption></figure>'
        for k in range(3))
    note = (f'<p class="rev-note">Sample layout &mdash; once you approve, {esc(ctx["name"])}&rsquo;s '
            f'real 5-star Google &amp; Yelp reviews drop straight into these cards.</p>')
    return f'<div class="revs">{cards}</div>{note}'


def conversion_bar(ctx: dict) -> str:
    call = (f'<a class="cv-call" href="tel:{ctx["tel"]}">{icon("phone",20)} Call {esc(ctx["phone"])}</a>'
            if ctx["phone"] else
            f'<a class="cv-call" href="#contact">{icon("phone",20)} Contact us</a>')
    return (f'<div class="convbar">'
            f'<div class="cv-hours">{icon("clock",18)} {esc(ctx["hours"])}</div>{call}</div>')


# --------------------------------------------------------------------------- #
# Page assembly
# --------------------------------------------------------------------------- #
_TEMPLATE_CACHE = None


def load_template() -> str:
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        if not os.path.exists(TEMPLATE_FILE):
            sys.exit(f"ERROR: template not found at {TEMPLATE_FILE}")
        with open(TEMPLATE_FILE, encoding="utf-8") as fh:
            _TEMPLATE_CACHE = fh.read()
    return _TEMPLATE_CACHE


def variants_for(slug: str, niche: str) -> tuple[str, str, str]:
    arch = arch_of(niche)
    return arch, pick(slug, HERO_BY_ARCH[arch], 0), pick(slug, SVC_BY_ARCH[arch], 7)


def build_html(lead: dict, hero_v: str | None = None, svc_v: str | None = None) -> str:
    niche = lead.get("niche", "") or "Local Service"
    arch = arch_of(niche)
    pal = ARCHETYPES[arch]
    content = content_of(niche)
    slug = lead.get("slug", "") or "lead"

    ctx = {
        "name": lead.get("business_name", "") or "Your Business",
        "city": lead.get("city", "") or "San Luis Obispo County",
        "niche": niche,
        "phone": (lead.get("phone", "") or "").strip(),
        "rating": (lead.get("rating", "") or "").strip(),
        "reviews": (lead.get("review_count", "") or "").strip(),
        "mono": monogram(lead.get("business_name", "")),
        "content": content, "arch": arch,
    }
    ctx["tag"] = content["tag"]
    ctx["sub"] = content["sub"]
    ctx["hours"] = content["hours"]
    ctx["tel"] = tel_of(ctx["phone"])
    ctx["cta_hero"] = cta_button(ctx, content["cta"], "btn btn-primary mag")

    _, h_def, s_def = variants_for(slug, niche)
    hero_v = hero_v or h_def
    svc_v = svc_v or s_def
    hero_html = HERO_FN[hero_v](ctx)
    svc_html = SVC_FN[svc_v](ctx)

    repl = {
        "{{ARCH}}": arch, "{{HEROV}}": hero_v, "{{SVCV}}": svc_v,
        "{{JSONLD}}": i18n_seo.jsonld(lead, content.get("svc")),
        "{{I18N_ES}}": json.dumps(i18n_seo.i18n_map(ctx, content), ensure_ascii=False),
        "{{NAME}}": esc(ctx["name"]), "{{CITY}}": esc(ctx["city"]),
        "{{NICHE}}": esc(niche), "{{MONO}}": esc(ctx["mono"]),
        "{{CTA_NAV}}": cta_button(ctx, "Call now", "btn btn-nav mag"),
        "{{CTA_LABEL}}": esc(content["cta"]),
        "{{HERO}}": hero_html, "{{STATS}}": stats_strip(ctx),
        "{{SERVICES}}": svc_html, "{{REVIEWS}}": reviews_block(ctx),
        "{{CONVBAR}}": conversion_bar(ctx), "{{YEAR}}": str(datetime.now().year),
        "{{BG}}": pal["BG"], "{{SURFACE}}": pal["SURFACE"], "{{SURFACE2}}": pal["SURFACE2"],
        "{{INK}}": pal["INK"], "{{MUTED}}": pal["MUTED"], "{{LINE}}": pal["LINE"],
        "{{C1}}": pal["C1"], "{{C2}}": pal["C2"], "{{DARK}}": pal["DARK"],
        "{{ACCENT_TEXT}}": pal["ACCENT_TEXT"], "{{RADIUS}}": pal["RADIUS"],
        "{{RADIUS_LG}}": pal["RADIUS_LG"], "{{BDW}}": pal["BDW"], "{{SHADOW}}": pal["SHADOW"],
        "{{F_DISPLAY}}": pal["F_DISPLAY"], "{{F_BODY}}": pal["F_BODY"], "{{F_MONO}}": pal["F_MONO"],
    }
    out = load_template()
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def load_leads(path: str) -> list[dict]:
    if not os.path.exists(path):
        sys.exit(f"ERROR: {path} not found. Run find_leads.py first.")
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate per-lead demo websites (Design Router).")
    ap.add_argument("--slug", help="Only build this slug.")
    args = ap.parse_args(argv)

    leads = load_leads(CSV_PATH)
    os.makedirs(OUT_DIR, exist_ok=True)
    built = 0
    arch_seen: dict = {}
    for lead in leads:
        slug = (lead.get("slug") or "").strip()
        if not slug or (args.slug and slug != args.slug):
            continue
        niche = lead.get("niche", "")
        arch = arch_of(niche)
        # Round-robin variant cycling per archetype so same-niche leads never
        # share a layout. Hero and services use offset indices to avoid lockstep.
        idx = arch_seen.get(arch, 0)
        arch_seen[arch] = idx + 1
        heroes, svcs = HERO_BY_ARCH[arch], SVC_BY_ARCH[arch]
        hv = heroes[idx % len(heroes)]
        sv = svcs[(idx + 1) % len(svcs)]
        out_path = os.path.join(OUT_DIR, f"{slug}-demo.html")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(build_html(lead, hero_v=hv, svc_v=sv))
        built += 1
        print(f"  built  {slug}-demo.html   arch={arch:<9} hero={hv}  services={sv}  ({lead.get('business_name','')})")
    print(f"\nDone. {built} mockup(s) -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
