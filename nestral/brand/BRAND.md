# Nestral — Brand Guidelines
*v1.1 · 2026-06-23 · universal positioning*

> The AI chief-of-staff for **everything you run**.

---

## 1. Essence

**Concept:** *Dawn over the operations tower.* Nestral is the calm, intelligent vantage point
above the chaos of running many brands. The product's defining moment is the **morning brief** —
so the brand lives at dawn: the quiet, focused hour before the noise, when one clear briefing tells
you exactly what to do.

- **One-liner:** Everything you run, in one nest.
- **What it is:** One AI brain across everything you connect → one morning brief, ranked by what needs you today.
- **Mission:** Give any operator the leverage of a team they don't have.
- **Feeling:** Calm authority. In control. Quietly premium. The opposite of dashboard clutter.

## 2. Audience

**Universal positioning, with a flagship wedge.** Nestral is for anyone running more than their
attention can hold and checking more than one dashboard a day:
- **Flagship / beachhead:** the solo operator running **3–10 DTC/Shopify stores** (the sharpest,
  most under-served pain — and where we start, dogfooded on a real portfolio).
- **Then:** agencies & freelancers watching client accounts, solo founders with many moving parts,
  people juggling side-projects (stores, newsletters, apps, rentals).

Go-to-market lands the beachhead first (portfolio commerce), then widens. The brand reads universal;
the *messaging by channel* can narrow to whichever audience we're targeting.

## 3. Voice & personality

Operator-to-operator. Plain, confident, a little dry. We respect the reader's time and intelligence.

- **Do:** lead with the point; use real numbers; short sentences; concrete nouns; admit limits honestly.
- **Don't:** hype words ("revolutionary", "unleash", "supercharge"), exclamation marks, emoji spam,
  vague AI-magic claims, fake urgency.
- **Tone test:** would a smart, busy operator nod — or roll their eyes? Write for the nod.

**Examples**
- ✅ "Five stores. Five logins. No team." ✅ "Signal. Not another dashboard." ✅ "Start tomorrow already knowing."
- ❌ "Supercharge your e-commerce empire with AI!" ❌ "The #1 revolutionary growth platform."

## 4. Name

**Nestral** — *nest* (where all your brands live, gathered and protected) + the steady "-tral" of
*central / neutral*. A coined word: ownable, calm, and not boxed into birds if we grow beyond DTC.
- Pronounced **NES-trəl**. Always capitalized "Nestral" (never NestRAL, Nest-ral, or all-caps in body).
- Domain: **nestral.ai** (verified available 2026-06-23 — register before launch).
- Tagline options: *“Run every brand from one nest.”* · *“One brief. Every brand.”* · *“Your portfolio, at dawn.”*

## 5. Logo

The **nest mark**: two woven arcs (the nest) cradling **three eggs** — the center egg lighter, = *today's
focus*. It doubles as a radar/observatory motif (oversight). Files in `brand/logo/`:

| File | Use |
|---|---|
| `mark.svg` | Full-color mark, transparent bg |
| `mark-mono.svg` | Single-color (`currentColor`) for one-ink contexts |
| `lockup.svg` | Mark + "Nestral" wordmark (for dark backgrounds) |
| `favicon.svg` | Mark on dark rounded square (browser tab) |
| `icon.svg` | App icon — mark on a dawn-gradient square |

- **Clearspace:** keep at least the height of one egg around the mark.
- **Min size:** mark 20px; lockup 110px wide.
- **Wordmark type:** Hanken Grotesk 800, letter-spacing -1.
- **Don't:** recolor eggs off-palette, add shadows/bevels, stretch, rotate, or put the dark lockup on a busy/light photo without a scrim.

## 6. Color

Dark-first. Deep ink base, a single warm **dawn** accent, functional signal colors.

| Token | Hex | Use |
|---|---|---|
| `--ink-900` | `#0B0E12` | Page base |
| `--ink-800` / `--ink-700` | `#11161D` / `#161D26` | Surfaces / cards |
| hairline | `rgba(255,255,255,.07)` | Borders, dividers |
| `--dawn-400` | `#FFB55C` | **Primary accent** (light) |
| `--dawn-500` / `--dawn-600` | `#FF9A3D` / `#F2792B` | Accent mid / deep, gradients |
| `--tx` / `--tx-dim` / `--tx-faint` | `#ECEFF4` / `#9AA7B5` / `#62707F` | Text scale |
| `--sig-crit` | `#FF5D5D` | 🔴 Critical (needs you) |
| `--sig-watch` | `#FFC24B` | 🟡 Watch |
| `--sig-good` | `#46D39A` | 🟢 Healthy |

- One accent, used with restraint. The **dawn horizon glow** (radial gradient at the bottom) is the
  signature background — never gradient *text*.
- Signal colors are **functional only** (status), never decoration.
- **Dual theme (versatility):** Nestral is dark-first but ships a full **light theme** too — toggle on
  the site and cockpit, remembered per device, defaults to the OS preference. Light = warm paper
  `#F5F1E8`, ink text, deepened accent `#E2670F`. Critically, the serif (Instrument) stays **display-only**;
  body is always grotesk — so warm paper never pairs with a serif *body* (the "cream + serif" combo is
  the #1 AI-slop tell; we avoid it deliberately). See `[data-theme="light"]` in `tokens.css`.

## 7. Typography

Three families, clear roles. Deliberately none of the AI-default fonts (no Inter, Roboto, Space Grotesk, Fraunces).

- **Display — Instrument Serif** (`--f-display`): hero & section headlines, pull quotes. High-contrast,
  editorial, used big with an *italic* accent word in dawn-300.
- **UI/body — Hanken Grotesk** (`--f-ui`): everything functional — nav, body, buttons, subheads. 400–800.
- **Data/mono — Spline Sans Mono** (`--f-mono`): **all numbers/metrics**, eyebrows, labels, code. This
  mono-numerals choice is a signature — it makes the product feel like an instrument panel.

Scale: hero `clamp(44–78px)` serif · section `clamp(32–52px)` serif · body 15–17px Hanken ·
eyebrow 12px mono, letter-spacing .22em, uppercase, dawn-400.

## 8. Motion

Calm and purposeful. One orchestrated page-load (staggered `rise` reveal, `animation-delay` ladder),
subtle hover lifts (`translateY(-2–3px)`), hairline-to-brighter border on hover. Always honor
`prefers-reduced-motion`. No bouncing, no parallax soup.

## 9. Imagery & texture

- **Atmosphere over stock photos:** the dawn glow + a very low-opacity (≈3%) fractal-noise **grain**
  overlay give depth without imagery.
- **Show the product:** the hero/marketing visual is a styled **morning brief**, not an abstract.
  Show, don't tell.
- Icons: simple mono glyphs (◈ ⚡ ❝ ⇄ 🔒 ◐) in a dawn-tinted rounded square.

## 10. Applications

- **Landing** — `site/index.html` (deploy to nestral.ai). OG image template `site/assets/og.html` → render to `og.png` (1200×630).
- **Cockpit** — `public/index.html` (the product dashboard; served by the app).
- **Brief (text/email/Telegram)** — markdown, leads with the 🪺 line + portfolio totals, then "Needs you today", then per brand. Keep the mono/severity-dot language consistent with the UI.

## 11. Asset index
```
brand/
  BRAND.md            this file
  tokens.css          design tokens (colors, type, radii, motion)
  logo/ mark · mark-mono · lockup · favicon · icon  (.svg)
site/
  index.html          marketing site
  assets/ favicon.svg · og.html
public/index.html     product cockpit
```
