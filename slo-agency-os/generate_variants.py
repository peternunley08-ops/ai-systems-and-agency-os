#!/usr/bin/env python3
"""
generate_variants.py  —  TIER 3 (V6/V7): 5-Variant Dynamic Design Factory
=========================================================================
For every lead in leads_database.csv, writes FIVE standalone, self-contained
mockups, each a genuinely distinct CSS architecture:

  mockups/<slug>/variant-1-editorial.html    warm cream, serif, asymmetric
  mockups/<slug>/variant-2-bento.html        white, bento grid, cobalt accent
  mockups/<slug>/variant-3-brutalist.html    high-contrast, thick borders, safety orange
  mockups/<slug>/variant-4-minimalist.html   sage/oatmeal, airy, deep slate
  mockups/<slug>/variant-5-darkmode.html     obsidian, glassmorphic, neon

Shared across all five (so they stay consistent + cheap to maintain):
  * content (tagline, services, sample testimonials) from generate_mockups
  * JSON-LD LocalBusiness structured data (i18n_seo.jsonld)
  * a live EN/ES toggle (i18n_seo.i18n_map) — works on any layout because it
    matches visible text by string
  * glassy sticky nav + mobile sticky tap-to-call bar
Zero external CDNs. Run:  python generate_variants.py   (or --slug <slug>)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime

import generate_mockups as gm
import i18n_seo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "leads_database.csv")
OUT_DIR = os.path.join(BASE_DIR, "mockups")
YEAR = datetime.now().year
REV_BODIES = i18n_seo._REV_BODIES_EN

esc = gm.esc
icon = gm.icon

VARIANTS = [
    ("1", "editorial", "Editorial"),
    ("2", "bento", "Bento"),
    ("3", "brutalist", "Brutalist"),
    ("4", "minimalist", "Minimal"),
    ("5", "darkmode", "Dark Mode"),
]


# --------------------------------------------------------------------------- #
# Small shared fragments (same DOM, styled differently by each variant CSS)
# --------------------------------------------------------------------------- #
def cta_primary(ctx, cls="btn primary"):
    if ctx["phone"]:
        return f'<a class="{cls}" href="tel:{ctx["tel"]}">{esc(ctx["cta"])} &middot; {esc(ctx["phone"])}</a>'
    return f'<a class="{cls}" href="#contact">{esc(ctx["cta"])}</a>'


def badge(ctx):
    if ctx["rating"]:
        return (f'<span class="badge"><b>&#9733; {esc(ctx["rating"])}</b> '
                f'{esc(ctx["reviews"] or "")} reviews</span>')
    return '<span class="badge"><b>&#9733;</b> Local &amp; Trusted</span>'


def call_bar(ctx):
    if ctx["phone"]:
        link = f'<a class="cbar-call" href="tel:{ctx["tel"]}">{icon("phone",18)} Call {esc(ctx["phone"])}</a>'
    else:
        link = f'<a class="cbar-call" href="#contact">{icon("phone",18)} Contact us</a>'
    return f'<div class="cbar"><span class="cbar-h">{icon("clock",16)} {esc(ctx["hours"])}</span>{link}</div>'


def nav(ctx):
    return (
        '<header><div class="wrap nav">'
        f'<a class="brand" href="#top"><span class="logo">{esc(ctx["mono"])}</span>{esc(ctx["name"])}</a>'
        '<nav class="links"><a href="#services">Services</a><a href="#reviews">Reviews</a>'
        '<a href="#contact">Contact</a></nav>'
        '<button class="lang" data-langbtn onclick="toggleLang()">ES</button>'
        '</div></header>'
    )


def services_items(ctx):
    return "".join(
        f'<article class="svc"><span class="svc-ic">{icon(i)}</span>'
        f'<h3>{esc(t)}</h3><p>{esc(d)}</p></article>'
        for i, t, d in ctx["svc"])


def review_items(ctx):
    return "".join(
        f'<figure class="rev"><div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>'
        f'<blockquote>&ldquo;{esc(b)}&rdquo;</blockquote>'
        f'<figcaption>{esc(rt)} &middot; Sample testimonial</figcaption></figure>'
        for b, rt in zip(REV_BODIES, ctx["rev"]))


def sections(ctx):
    return f"""
<section id="services" class="sec"><div class="wrap">
  <div class="sec-h"><span class="kick">What we do</span>
    <h2>Everything {esc(ctx['city'])} relies on us for</h2>
    <p>Clear services, honest pricing, and a booking experience your customers will actually enjoy.</p></div>
  <div class="svc-grid">{services_items(ctx)}</div>
</div></section>
<section id="reviews" class="sec alt"><div class="wrap">
  <div class="sec-h"><span class="kick">What our customers say</span>
    <h2>Loved by neighbors across {esc(ctx['city'])}</h2>
    <p>Your reputation is your best marketing - we put it where everyone can see it.</p></div>
  <div class="revs">{review_items(ctx)}</div>
  <p class="rev-note" style="text-align:center;max-width:640px;margin:22px auto 0;font-size:13px;opacity:.62;line-height:1.5">Sample testimonials shown to illustrate the layout &mdash; {esc(ctx['name'])}&rsquo;s real Google &amp; Yelp reviews replace these before launch.</p>
</div></section>
<section id="contact" class="sec"><div class="wrap cgrid">
  <div class="cinfo"><span class="kick">Get in touch</span><h2>Ready when you are</h2>
    <p>Send a request and {esc(ctx['name'])} will get right back to you. No phone tag, no hold music.</p>
    <div class="ci">{icon('phone',20)}<span>Call or text for a fast quote</span></div>
    <div class="ci">{icon('map',20)}<span>Serving {esc(ctx['city'])} &amp; the Central Coast</span></div>
    <div class="ci">{icon('clock',20)}<span>{esc(ctx['city'])} &middot; same-day estimates</span></div>
  </div>
  <form onsubmit="return hs(event)">
    <div class="fmsg" id="fmsg">Thanks - we&rsquo;ll be in touch shortly!</div>
    <label>Your name</label><input required placeholder="Jane Doe">
    <label>Phone or email</label><input required placeholder="(805) 555-0123">
    <label>What do you need?</label>
    <select><option>Request a quote</option><option>Book a service</option><option>Ask a question</option><option>Catering / event</option></select>
    <label>Details</label><textarea placeholder="Tell us a little about the job..."></textarea>
    <button class="btn primary" type="submit">{esc(ctx['cta'])}</button>
  </form>
</div></section>
<footer><div class="wrap foot">
  <span class="brand2"><span class="logo">{esc(ctx['mono'])}</span>{esc(ctx['name'])}</span>
  <span>&copy; {YEAR} {esc(ctx['name'])} &middot; {esc(ctx['city'])}, CA</span>
</div></footer>
{call_bar(ctx)}
"""


_JS_BODY = r"""
function _walk(n,f){for(var c=n.firstChild;c;c=c.nextSibling){if(c.nodeType===3)f(c);else if(c.nodeType===1&&c.tagName!=='SCRIPT'&&c.tagName!=='STYLE')_walk(c,f);}}
function setLang(l){_walk(document.body,function(t){if(l==='es'){var k=t.nodeValue.trim();if(k&&I18N_ES[k]!=null){if(t.__en==null)t.__en=t.nodeValue;t.nodeValue=t.nodeValue.replace(k,I18N_ES[k]);}}else if(t.__en!=null)t.nodeValue=t.__en;});document.querySelectorAll('input[placeholder],textarea[placeholder]').forEach(function(e){if(l==='es'){if(e.__ph==null)e.__ph=e.placeholder;if(I18N_ES[e.placeholder]!=null)e.placeholder=I18N_ES[e.placeholder];}else if(e.__ph!=null)e.placeholder=e.__ph;});document.documentElement.setAttribute('data-lang',l);document.querySelectorAll('[data-langbtn]').forEach(function(b){b.textContent=l==='es'?'EN':'ES';});}
function toggleLang(){setLang(document.documentElement.getAttribute('data-lang')==='es'?'en':'es');}
function hs(e){e.preventDefault();var m=document.getElementById('fmsg');if(m)m.style.display='block';e.target.querySelectorAll('input,textarea').forEach(function(el){el.value='';});return false;}
(function(){var h=document.querySelector('header');function on(){if(h)h.classList.toggle('scrolled',window.scrollY>24);}on();window.addEventListener('scroll',on,{passive:true});})();
"""


def script(es_json):
    return "<script>\nconst I18N_ES = " + es_json + ";\n" + _JS_BODY + "\n</script>"


def frame(ctx, css, body, body_class):
    return (
        '<!doctype html><html lang="en" data-lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{esc(ctx["name"])} | {esc(ctx["niche"])} in {esc(ctx["city"])}</title>'
        f'<meta name="description" content="{esc(ctx["name"])} - {esc(ctx["niche"])} serving {esc(ctx["city"])}.">'
        f'\n{ctx["_jsonld"]}\n<style>{css}</style></head>'
        f'<body class="{body_class}">{body}{script(ctx["_es"])}</body></html>'
    )


BASE = """
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
.wrap{max-width:1140px;margin:0 auto;padding:0 22px}
a{text-decoration:none;color:inherit}
img{max-width:100%}
.demo-ribbon{position:fixed;top:14px;right:-44px;transform:rotate(45deg);z-index:120;font-size:11px;font-weight:800;letter-spacing:.12em;padding:6px 56px}
.svc-grid{display:grid;gap:18px}
.revs{display:grid;gap:18px}
.cgrid{display:grid;gap:34px}
.ci{display:flex;align-items:center;gap:11px;margin-top:12px;font-weight:600}
form{display:flex;flex-direction:column}
label{font-size:13px;font-weight:700;margin:12px 0 5px}
input,select,textarea{width:100%;padding:12px 14px;font:inherit;font-size:15px}
textarea{min-height:96px;resize:vertical}
.fmsg{display:none;padding:11px 14px;margin-bottom:10px;font-weight:600}
.cbar{position:fixed;left:0;right:0;bottom:0;z-index:110;display:none;align-items:center;justify-content:space-between;gap:10px;padding:10px 16px}
@media(max-width:880px){.cbar{display:flex}.links{display:none}}
"""
print("generate_variants.py chunk1 written")


# =========================== VARIANT 1: EDITORIAL ============================ #
CSS_EDITORIAL = BASE + """
body{font-family:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif;color:#1A1A1A;background:#FDFBF7;line-height:1.65}
h1,h2,h3,.brand,.mono-art,.brand2{font-family:"Fraunces","Playfair Display",Georgia,serif;font-weight:800;letter-spacing:-.01em;line-height:1.08}
header{position:fixed;inset:0 0 auto 0;z-index:100;transition:.25s}
header.scrolled{background:rgba(253,251,247,.7);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-bottom:1px solid #ece4d6}
.nav{display:flex;align-items:center;justify-content:space-between;height:72px}
.brand{display:flex;align-items:center;gap:11px;font-size:19px}
.logo{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;color:#fff;background:#C2513B;font-size:15px}
.links{display:flex;gap:24px}.links a{color:#7a6f63;font-weight:600;font-size:15px}.links a:hover{color:#1A1A1A}
.lang{background:#fff;border:1px solid #e6dccd;border-radius:999px;padding:8px 13px;font-weight:700;font-size:13px;cursor:pointer}
.btn{display:inline-flex;align-items:center;gap:8px;border-radius:999px;font-weight:700;font-size:15px;padding:14px 24px;cursor:pointer;border:0;transition:.18s}
.btn.primary{background:#C2513B;color:#fff}.btn.primary:hover{transform:translateY(-2px)}
.btn.ghost{background:transparent;border:1.5px solid #d9cbb8;color:#1A1A1A}
.hero{padding:128px 0 60px}
.hero-in{display:grid;grid-template-columns:1.1fr .9fr;gap:48px;align-items:center}
.eyebrow{font-family:"Space Mono",monospace;text-transform:uppercase;letter-spacing:.1em;font-size:12.5px;color:#C2513B}
.hero h1{font-size:clamp(40px,6.5vw,68px);max-width:14ch;margin:16px 0}
.lede{font-size:20px;color:#5a5048;max-width:48ch;margin-bottom:26px}
.cta-row{display:flex;gap:14px;flex-wrap:wrap}
.hart{position:relative;aspect-ratio:4/5;border-radius:18px;background:linear-gradient(160deg,#C2513B,#7c2f20);display:grid;place-items:center;box-shadow:0 30px 60px rgba(124,47,32,.25)}
.mono-art{font-size:clamp(90px,16vw,150px);color:rgba(255,255,255,.92)}
.badge{position:absolute;bottom:-16px;left:24px;background:#fff;border-radius:999px;padding:10px 16px;font-size:13px;font-weight:700;box-shadow:0 10px 24px rgba(0,0,0,.12)}.badge b{color:#C2513B}
.sec{padding:78px 0}.sec.alt{background:#f4ece0}
.sec-h{max-width:60ch;margin:0 auto 44px;text-align:center}
.kick{font-family:"Space Mono",monospace;text-transform:uppercase;letter-spacing:.12em;font-size:12.5px;color:#C2513B}
.sec-h h2{font-size:clamp(28px,4vw,42px);margin-top:10px}.sec-h p{color:#6a6058;margin-top:12px;font-size:17px}
.svc-grid{grid-template-columns:repeat(3,1fr)}
.svc{padding:26px;border-bottom:2px solid #C2513B;background:#fffdf9}
.svc-ic{display:inline-grid;place-items:center;width:50px;height:50px;border-radius:12px;color:#C2513B;background:#f4e7dd;margin-bottom:14px}
.svc h3{font-size:20px;margin-bottom:6px}.svc p{color:#6a6058;font-size:15px}
.revs{grid-template-columns:repeat(3,1fr)}
.rev{padding:28px;background:#fffdf9;border-radius:16px;box-shadow:0 14px 30px rgba(120,70,40,.07)}
.stars{color:#C2513B;letter-spacing:2px;margin-bottom:10px}.rev blockquote{font-size:16px;font-style:italic}.rev figcaption{margin-top:14px;font-weight:700;font-size:13px;color:#8a7d70}
.cgrid{grid-template-columns:1fr 1fr;align-items:start}
.cinfo h2{font-size:clamp(28px,4vw,40px);margin:8px 0 12px}.cinfo p{color:#6a6058;font-size:17px;margin-bottom:6px}
.ci svg{color:#C2513B}
form{background:#fffdf9;border:1px solid #ece0d0;border-radius:18px;padding:26px}
input,select,textarea{border:1.5px solid #e6dccd;border-radius:11px;background:#fff}
input:focus,select:focus,textarea:focus{outline:none;border-color:#C2513B}
.fmsg{background:#f6ece2;border:1px solid #e0cdb8;border-radius:11px;color:#7c2f20}
button.primary[type=submit]{width:100%;justify-content:center;margin-top:10px}
footer{background:#241c16;color:#cbb8a6;padding:40px 0 96px}
.foot{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.brand2{display:flex;align-items:center;gap:10px;color:#fff}.foot .logo{background:#C2513B}
.cbar{background:rgba(253,251,247,.94);backdrop-filter:blur(12px);border-top:1px solid #e6dccd}
.cbar-h{font-size:13px;font-weight:700;color:#6a6058;display:flex;align-items:center;gap:6px}
.cbar-call{display:inline-flex;align-items:center;gap:7px;background:#C2513B;color:#fff;font-weight:800;padding:10px 16px;border-radius:999px}
@media(max-width:880px){.hero-in,.cgrid{grid-template-columns:1fr}.svc-grid,.revs{grid-template-columns:1fr}.hart{order:-1;aspect-ratio:16/10}}
"""

def build_editorial(ctx):
    hero = (f'<section class="hero" id="top"><div class="wrap hero-in">'
            f'<div class="hcopy"><span class="eyebrow">{esc(ctx["niche"])} &middot; {esc(ctx["city"])}</span>'
            f'<h1>{esc(ctx["tag"])}</h1><p class="lede">{esc(ctx["sub"])}</p>'
            f'<div class="cta-row">{cta_primary(ctx)}<a class="btn ghost" href="#services">See services</a></div></div>'
            f'<aside class="hart"><span class="mono-art">{esc(ctx["mono"])}</span>{badge(ctx)}</aside>'
            f'</div></section>')
    return frame(ctx, CSS_EDITORIAL, nav(ctx) + hero + sections(ctx), "v-editorial")


# ============================ VARIANT 2: BENTO ============================== #
CSS_BENTO = BASE + """
body{font-family:"Plus Jakarta Sans","Inter",system-ui,-apple-system,sans-serif;color:#0f172a;background:#fff;line-height:1.6}
h1,h2,h3{font-weight:800;letter-spacing:-.02em;line-height:1.1}
header{position:fixed;inset:0 0 auto 0;z-index:100;transition:.25s}
header.scrolled{background:rgba(255,255,255,.65);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-bottom:1px solid #E5E7EB}
.nav{display:flex;align-items:center;justify-content:space-between;height:70px}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:18px}
.logo{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;color:#fff;background:#1E40AF;font-weight:800}
.links{display:flex;gap:24px}.links a{color:#64748b;font-weight:600;font-size:15px}.links a:hover{color:#0f172a}
.lang{background:#f1f5f9;border:1px solid #E5E7EB;border-radius:999px;padding:8px 13px;font-weight:700;font-size:13px;cursor:pointer}
.btn{display:inline-flex;align-items:center;gap:8px;border-radius:12px;font-weight:700;font-size:15px;padding:13px 22px;cursor:pointer;border:0;transition:.18s}
.btn.primary{background:#1E40AF;color:#fff}.btn.primary:hover{background:#1b3a9c}
.btn.ghost{background:#fff;border:1px solid #E5E7EB;color:#0f172a}
.hero{padding:104px 0 40px}
.bento{display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:minmax(120px,auto);gap:16px}
.cell{border:1px solid #E5E7EB;border-radius:24px;padding:24px;display:flex;flex-direction:column;justify-content:center}
.cell.big{grid-column:span 2;grid-row:span 2;justify-content:center}
.cell.accent{background:#1E40AF;color:#fff}
.cell.stat b{font-size:30px;font-weight:800}.cell b{font-size:22px;font-weight:800}.cell span{color:#64748b;font-size:13px;font-weight:600;margin-top:3px}.cell.accent span{color:#c7d2fe}
.eyebrow{color:#1E40AF;font-weight:800;font-size:12.5px;text-transform:uppercase;letter-spacing:.08em}
.cell.big h1{font-size:clamp(30px,4.6vw,50px);margin:12px 0}.cell.big .lede{color:#475569;font-size:18px;margin-bottom:20px}
.cta-row{display:flex;gap:12px;flex-wrap:wrap}
.sec{padding:70px 0}.sec.alt{background:#f8fafc}
.sec-h{max-width:60ch;margin:0 auto 40px;text-align:center}
.kick{color:#1E40AF;font-weight:800;font-size:12.5px;text-transform:uppercase;letter-spacing:.08em}
.sec-h h2{font-size:clamp(26px,4vw,40px);margin-top:8px}.sec-h p{color:#64748b;margin-top:10px;font-size:17px}
.svc-grid{grid-template-columns:repeat(4,1fr);grid-auto-flow:dense}
.svc{border:1px solid #E5E7EB;border-radius:20px;padding:24px}
.svc:nth-child(1){grid-column:span 2}.svc:nth-child(6){grid-column:span 2}
.svc-ic{display:inline-grid;place-items:center;width:48px;height:48px;border-radius:14px;color:#1E40AF;background:#eff3ff;margin-bottom:13px}
.svc h3{font-size:18px;margin-bottom:5px}.svc p{color:#64748b;font-size:14.5px}
.revs{grid-template-columns:repeat(3,1fr)}
.rev{border:1px solid #E5E7EB;border-radius:20px;padding:24px}
.stars{color:#1E40AF;letter-spacing:2px;margin-bottom:10px}.rev blockquote{font-size:15px}.rev figcaption{margin-top:13px;font-weight:700;font-size:13px;color:#64748b}
.cgrid{grid-template-columns:1fr 1fr;align-items:start}
.cinfo h2{font-size:clamp(26px,4vw,38px);margin:8px 0 12px}.cinfo p{color:#64748b;font-size:17px;margin-bottom:6px}
.ci svg{color:#1E40AF}
form{border:1px solid #E5E7EB;border-radius:24px;padding:26px}
input,select,textarea{border:1px solid #E5E7EB;border-radius:12px;background:#fff}
input:focus,select:focus,textarea:focus{outline:none;border-color:#1E40AF}
.fmsg{background:#eff3ff;border:1px solid #c7d2fe;border-radius:12px;color:#1E40AF}
button.primary[type=submit]{width:100%;justify-content:center;margin-top:10px}
footer{background:#0f172a;color:#94a3b8;padding:40px 0 96px}
.foot{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.brand2{display:flex;align-items:center;gap:10px;color:#fff;font-weight:800}.foot .logo{background:#1E40AF}
.cbar{background:rgba(255,255,255,.7);backdrop-filter:blur(12px);border-top:1px solid #E5E7EB}
.cbar-h{font-size:13px;font-weight:700;color:#64748b;display:flex;align-items:center;gap:6px}
.cbar-call{display:inline-flex;align-items:center;gap:7px;background:#1E40AF;color:#fff;font-weight:800;padding:10px 16px;border-radius:12px}
@media(max-width:880px){.bento,.svc-grid{grid-template-columns:1fr 1fr}.cell.big{grid-column:span 2}.svc:nth-child(1),.svc:nth-child(6){grid-column:span 2}.cgrid{grid-template-columns:1fr}.revs{grid-template-columns:1fr}}
"""

def build_bento(ctx):
    hero = (f'<section class="hero" id="top"><div class="wrap bento">'
            f'<div class="cell big"><span class="eyebrow">{esc(ctx["niche"])} &middot; {esc(ctx["city"])}</span>'
            f'<h1>{esc(ctx["tag"])}</h1><p class="lede">{esc(ctx["sub"])}</p>'
            f'<div class="cta-row">{cta_primary(ctx)}<a class="btn ghost" href="#services">See services</a></div></div>'
            f'<div class="cell stat"><b>{esc(ctx["rating"]) or "&#9733;"}</b><span>Avg rating</span></div>'
            f'<div class="cell stat"><b>{esc(ctx["reviews"]) or "&mdash;"}</b><span>Reviews</span></div>'
            f'<div class="cell accent"><b>{esc(ctx["city"])}</b><span>Serving</span></div>'
            f'<div class="cell"><b>{esc(ctx["hours"])}</b><span>Open hours</span></div>'
            f'</div></section>')
    return frame(ctx, CSS_BENTO, nav(ctx) + hero + sections(ctx), "v-bento")


# ========================== VARIANT 3: BRUTALIST ============================ #
CSS_BRUTALIST = BASE + """
body{font-family:"Plus Jakarta Sans",system-ui,-apple-system,sans-serif;color:#000;background:#F3F4F6;line-height:1.55}
h1,h2,h3,.brand,.kick,.eyebrow{font-family:"Oswald","Syne","Arial Narrow",system-ui,sans-serif;text-transform:uppercase;font-weight:700;letter-spacing:.01em;line-height:1}
header{position:fixed;inset:0 0 auto 0;z-index:100}
header.scrolled{background:rgba(243,244,246,.8);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-bottom:2.5px solid #000}
.nav{display:flex;align-items:center;justify-content:space-between;height:70px}
.brand{display:flex;align-items:center;gap:10px;font-size:20px}
.logo{width:40px;height:40px;display:grid;place-items:center;color:#000;background:#FF5500;border:2.5px solid #000;font-weight:800}
.links{display:flex;gap:22px}.links a{color:#000;font-weight:700;font-size:15px}.links a:hover{background:#FF5500}
.lang{background:#fff;border:2.5px solid #000;padding:7px 12px;font-weight:800;font-size:13px;cursor:pointer}
.btn{display:inline-flex;align-items:center;gap:8px;font-weight:800;font-size:15px;padding:13px 22px;cursor:pointer;border:2.5px solid #000;transition:none}
.btn.primary{background:#FF5500;color:#000}.btn.primary:hover{background:#000;color:#FF5500}
.btn.ghost{background:#fff;color:#000}.btn.ghost:hover{background:#000;color:#fff}
.hero{padding:128px 0 56px}
.eyebrow{font-size:14px;letter-spacing:.12em;background:#000;color:#fff;padding:5px 10px;display:inline-block}
.hero h1{font-size:clamp(44px,9vw,104px);max-width:15ch;margin:18px 0}
.lede{font-size:20px;max-width:54ch;margin-bottom:24px;font-weight:500}
.cta-row{display:flex;gap:14px;flex-wrap:wrap}
.hstats{display:flex;gap:0;margin-top:40px;border:2.5px solid #000;width:fit-content;max-width:100%;flex-wrap:wrap}
.hstats div{padding:16px 26px;border-right:2.5px solid #000}.hstats div:last-child{border-right:0}
.hstats b{font-family:"Oswald",sans-serif;font-size:28px;display:block}.hstats span{font-size:12px;font-weight:700;text-transform:uppercase}
.sec{padding:72px 0;border-top:2.5px solid #000}.sec.alt{background:#fff}
.sec-h{margin:0 0 40px;max-width:60ch}
.kick{font-size:14px;letter-spacing:.12em;color:#FF5500}
.sec-h h2{font-size:clamp(30px,5vw,52px);margin-top:8px}.sec-h p{font-size:17px;margin-top:10px;font-weight:500}
.svc-grid{grid-template-columns:repeat(3,1fr);gap:0;border:2.5px solid #000}
.svc{padding:26px;border-right:2.5px solid #000;border-top:2.5px solid #000;background:#fff}
.svc:nth-child(-n+3){border-top:0}.svc:nth-child(3n){border-right:0}
.svc-ic{display:inline-grid;place-items:center;width:50px;height:50px;color:#000;background:#FF5500;border:2.5px solid #000;margin-bottom:14px}
.svc h3{font-size:21px;margin-bottom:6px}.svc p{font-size:15px;font-weight:500}
.revs{grid-template-columns:repeat(3,1fr)}
.rev{padding:24px;background:#fff;border:2.5px solid #000}
.stars{color:#FF5500;letter-spacing:2px;margin-bottom:10px}.rev blockquote{font-size:15px;font-weight:500}.rev figcaption{margin-top:13px;font-weight:800;font-size:12px;text-transform:uppercase}
.cgrid{grid-template-columns:1fr 1fr;align-items:start}
.cinfo h2{font-size:clamp(28px,4.5vw,46px);margin:6px 0 12px}.cinfo p{font-size:17px;font-weight:500;margin-bottom:6px}
.ci svg{color:#FF5500}
form{border:2.5px solid #000;padding:26px;background:#fff}
input,select,textarea{border:2.5px solid #000;background:#fff;border-radius:0}
input:focus,select:focus,textarea:focus{outline:3px solid #FF5500;outline-offset:-2px}
.fmsg{background:#FF5500;border:2.5px solid #000;color:#000;font-weight:800}
button.primary[type=submit]{width:100%;justify-content:center;margin-top:10px}
footer{background:#000;color:#fff;padding:40px 0 96px;border-top:2.5px solid #FF5500}
.foot{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.brand2{display:flex;align-items:center;gap:10px;color:#fff;font-family:"Oswald",sans-serif;text-transform:uppercase;font-weight:700}.foot .logo{background:#FF5500}
.cbar{background:#fff;border-top:2.5px solid #000}
.cbar-h{font-size:12px;font-weight:800;text-transform:uppercase;display:flex;align-items:center;gap:6px}
.cbar-call{display:inline-flex;align-items:center;gap:7px;background:#FF5500;color:#000;font-weight:800;padding:10px 16px;border:2.5px solid #000}
@media(max-width:880px){.svc-grid,.revs,.cgrid{grid-template-columns:1fr}.svc{border-right:0}}
"""

def build_brutalist(ctx):
    hero = (f'<section class="hero" id="top"><div class="wrap">'
            f'<span class="eyebrow">{esc(ctx["niche"])} // {esc(ctx["city"])}</span>'
            f'<h1>{esc(ctx["tag"])}</h1><p class="lede">{esc(ctx["sub"])}</p>'
            f'<div class="cta-row">{cta_primary(ctx)}<a class="btn ghost" href="#services">See services</a></div>'
            f'<div class="hstats"><div><b>{esc(ctx["rating"]) or "&#9733;"}</b><span>Avg rating</span></div>'
            f'<div><b>{esc(ctx["reviews"]) or "&mdash;"}</b><span>Reviews</span></div>'
            f'<div><b>{esc(ctx["city"])}</b><span>Serving</span></div></div>'
            f'</div></section>')
    return frame(ctx, CSS_BRUTALIST, nav(ctx) + hero + sections(ctx), "v-brutalist")


# ========================= VARIANT 4: MINIMALIST ============================ #
CSS_MINIMAL = BASE + """
body{font-family:"Bricolage Grotesque","Plus Jakarta Sans",system-ui,-apple-system,sans-serif;color:#33403a;background:#F4F1EA;line-height:1.7}
h1,h2,h3{font-weight:700;letter-spacing:-.01em;line-height:1.12;color:#2b352f}
header{position:fixed;inset:0 0 auto 0;z-index:100;transition:.25s}
header.scrolled{background:rgba(244,241,234,.7);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px)}
.nav{display:flex;align-items:center;justify-content:space-between;height:74px}
.brand{display:flex;align-items:center;gap:11px;font-weight:700;font-size:18px}
.logo{width:38px;height:38px;border-radius:50%;display:grid;place-items:center;color:#fff;background:#8AA37B;font-weight:700}
.links{display:flex;gap:26px}.links a{color:#6b7770;font-weight:600;font-size:15px}.links a:hover{color:#2b352f}
.lang{background:transparent;border:1px solid #c9d2c4;border-radius:999px;padding:8px 14px;font-weight:600;font-size:13px;cursor:pointer;color:#33403a}
.btn{display:inline-flex;align-items:center;gap:8px;border-radius:999px;font-weight:600;font-size:15px;padding:14px 26px;cursor:pointer;border:0;transition:.2s}
.btn.primary{background:#8AA37B;color:#fff}.btn.primary:hover{background:#76906a}
.btn.ghost{background:transparent;border:1px solid #c9d2c4;color:#33403a}
.hero{padding:clamp(8rem,16vw,12rem) 0 clamp(4rem,8vw,7rem);text-align:center}
.eyebrow{color:#8a9485;font-weight:600;font-size:14px;letter-spacing:.06em}
.hero h1{font-size:clamp(36px,6vw,62px);max-width:18ch;margin:18px auto}
.lede{font-size:20px;color:#5d6862;max-width:50ch;margin:0 auto 28px}
.cta-row{display:flex;gap:14px;flex-wrap:wrap;justify-content:center}
.sec{padding:clamp(4rem,10vw,9rem) 0}.sec.alt{background:#EAEFE9}
.sec-h{max-width:56ch;margin:0 auto 52px;text-align:center}
.kick{color:#8a9485;font-weight:600;font-size:14px;letter-spacing:.06em}
.sec-h h2{font-size:clamp(28px,4vw,42px);margin-top:10px}.sec-h p{color:#5d6862;margin-top:12px;font-size:17px}
.svc-grid{grid-template-columns:repeat(3,1fr);gap:clamp(1.5rem,4vw,3rem)}
.svc{padding:6px}
.svc-ic{display:inline-grid;place-items:center;width:52px;height:52px;border-radius:50%;color:#76906a;background:#dfe7da;margin-bottom:16px}
.svc h3{font-size:19px;margin-bottom:7px}.svc p{color:#5d6862;font-size:15px}
.revs{grid-template-columns:repeat(3,1fr);gap:clamp(1.5rem,4vw,3rem)}
.rev{padding:6px}.stars{color:#b08968;letter-spacing:2px;margin-bottom:10px}.rev blockquote{font-size:16px}.rev figcaption{margin-top:14px;font-weight:600;font-size:13px;color:#8a9485}
.cgrid{grid-template-columns:1fr 1fr;gap:clamp(2rem,6vw,5rem);align-items:start}
.cinfo h2{font-size:clamp(28px,4vw,40px);margin:8px 0 12px}.cinfo p{color:#5d6862;font-size:17px;margin-bottom:6px}
.ci svg{color:#8AA37B}
form{padding:0}
input,select,textarea{border:0;border-bottom:1px solid #c9d2c4;border-radius:0;background:transparent;padding:12px 2px}
input:focus,select:focus,textarea:focus{outline:none;border-color:#8AA37B}
.fmsg{background:#dfe7da;border-radius:14px;color:#3a5a3a}
button.primary[type=submit]{width:100%;justify-content:center;margin-top:18px}
footer{background:#2b352f;color:#b9c4ba;padding:42px 0 96px}
.foot{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.brand2{display:flex;align-items:center;gap:10px;color:#fff;font-weight:700}.foot .logo{background:#8AA37B}
.cbar{background:rgba(244,241,234,.94);backdrop-filter:blur(12px);border-top:1px solid #d6ddd1}
.cbar-h{font-size:13px;font-weight:600;color:#5d6862;display:flex;align-items:center;gap:6px}
.cbar-call{display:inline-flex;align-items:center;gap:7px;background:#8AA37B;color:#fff;font-weight:700;padding:10px 16px;border-radius:999px}
@media(max-width:880px){.svc-grid,.revs,.cgrid{grid-template-columns:1fr}}
"""

def build_minimalist(ctx):
    hero = (f'<section class="hero" id="top"><div class="wrap">'
            f'<span class="eyebrow">{esc(ctx["niche"])} &middot; {esc(ctx["city"])}</span>'
            f'<h1>{esc(ctx["tag"])}</h1><p class="lede">{esc(ctx["sub"])}</p>'
            f'<div class="cta-row">{cta_primary(ctx)}<a class="btn ghost" href="#services">See services</a></div>'
            f'</div></section>')
    return frame(ctx, CSS_MINIMAL, nav(ctx) + hero + sections(ctx), "v-minimal")


# ========================== VARIANT 5: DARK MODE ============================ #
CSS_DARK = BASE + """
body{font-family:"Space Grotesk","Syncopate",system-ui,-apple-system,sans-serif;color:#e6edf6;background:#080C14;line-height:1.6}
h1,h2,h3{font-weight:700;letter-spacing:-.01em;line-height:1.1}
.glass{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
header{position:fixed;inset:0 0 auto 0;z-index:100;transition:.25s}
header.scrolled{background:rgba(8,12,20,.6);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,.08)}
.nav{display:flex;align-items:center;justify-content:space-between;height:72px}
.brand{display:flex;align-items:center;gap:11px;font-weight:700;font-size:18px}
.logo{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;color:#06121a;background:linear-gradient(135deg,#6ee7ff,#a78bfa);font-weight:800}
.links{display:flex;gap:24px}.links a{color:#9aa6bd;font-weight:600;font-size:15px}.links a:hover{color:#fff}
.lang{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);color:#e6edf6;border-radius:999px;padding:8px 13px;font-weight:700;font-size:13px;cursor:pointer}
.btn{display:inline-flex;align-items:center;gap:8px;border-radius:12px;font-weight:700;font-size:15px;padding:14px 24px;cursor:pointer;border:0;transition:.18s}
.btn.primary{background:linear-gradient(135deg,#6ee7ff,#a78bfa);color:#06121a}.btn.primary:hover{filter:brightness(1.08)}
.btn.ghost{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.16);color:#e6edf6}
.hero{padding:140px 0 70px;position:relative;overflow:hidden;text-align:center}
.hero::after{content:"";position:absolute;width:600px;height:600px;left:50%;top:-280px;transform:translateX(-50%);border-radius:50%;background:radial-gradient(circle,rgba(110,231,255,.18),transparent 60%);z-index:0}
.hero .wrap{position:relative;z-index:1}
.hcard{max-width:760px;margin:0 auto;border-radius:24px;padding:48px 40px}
.eyebrow{color:#6ee7ff;font-weight:700;font-size:12.5px;text-transform:uppercase;letter-spacing:.14em}
.hero h1{font-size:clamp(36px,6vw,62px);margin:16px 0;background:linear-gradient(135deg,#fff,#a78bfa);-webkit-background-clip:text;background-clip:text;color:transparent}
.lede{font-size:19px;color:#9aa6bd;max-width:50ch;margin:0 auto 26px}
.cta-row{display:flex;gap:14px;flex-wrap:wrap;justify-content:center}
.sec{padding:78px 0}
.sec-h{max-width:60ch;margin:0 auto 44px;text-align:center}
.kick{color:#6ee7ff;font-weight:700;font-size:12.5px;text-transform:uppercase;letter-spacing:.12em}
.sec-h h2{font-size:clamp(28px,4vw,42px);margin-top:10px}.sec-h p{color:#9aa6bd;margin-top:12px;font-size:17px}
.svc-grid{grid-template-columns:repeat(3,1fr)}
.svc{border-radius:18px;padding:26px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08)}
.svc:hover{border-color:rgba(110,231,255,.5)}
.svc-ic{display:inline-grid;place-items:center;width:50px;height:50px;border-radius:13px;color:#6ee7ff;background:rgba(110,231,255,.1);margin-bottom:14px}
.svc h3{font-size:19px;margin-bottom:6px}.svc p{color:#9aa6bd;font-size:15px}
.revs{grid-template-columns:repeat(3,1fr)}
.rev{border-radius:18px;padding:26px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08)}
.stars{color:#a78bfa;letter-spacing:2px;margin-bottom:10px}.rev blockquote{font-size:15px;color:#dbe3ef}.rev figcaption{margin-top:14px;font-weight:700;font-size:13px;color:#9aa6bd}
.cgrid{grid-template-columns:1fr 1fr;align-items:start}
.cinfo h2{font-size:clamp(28px,4vw,40px);margin:8px 0 12px}.cinfo p{color:#9aa6bd;font-size:17px;margin-bottom:6px}
.ci svg{color:#6ee7ff}
form{border-radius:20px;padding:26px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08)}
input,select,textarea{border:1px solid rgba(255,255,255,.14);border-radius:12px;background:rgba(255,255,255,.04);color:#e6edf6}
input::placeholder,textarea::placeholder{color:#6b778c}
input:focus,select:focus,textarea:focus{outline:none;border-color:#6ee7ff}
.fmsg{background:rgba(110,231,255,.1);border:1px solid rgba(110,231,255,.3);border-radius:12px;color:#6ee7ff}
button.primary[type=submit]{width:100%;justify-content:center;margin-top:10px}
footer{background:#05080e;color:#7e8aa1;padding:40px 0 96px;border-top:1px solid rgba(255,255,255,.06)}
.foot{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.brand2{display:flex;align-items:center;gap:10px;color:#fff;font-weight:700}
.cbar{background:rgba(8,12,20,.7);backdrop-filter:blur(12px);border-top:1px solid rgba(255,255,255,.1)}
.cbar-h{font-size:13px;font-weight:700;color:#9aa6bd;display:flex;align-items:center;gap:6px}
.cbar-call{display:inline-flex;align-items:center;gap:7px;background:linear-gradient(135deg,#6ee7ff,#a78bfa);color:#06121a;font-weight:800;padding:10px 16px;border-radius:999px}
@media(max-width:880px){.svc-grid,.revs,.cgrid{grid-template-columns:1fr}.hcard{padding:34px 22px}}
"""

def build_darkmode(ctx):
    hero = (f'<section class="hero" id="top"><div class="wrap"><div class="hcard glass">'
            f'<span class="eyebrow">{esc(ctx["niche"])} &middot; {esc(ctx["city"])}</span>'
            f'<h1>{esc(ctx["tag"])}</h1><p class="lede">{esc(ctx["sub"])}</p>'
            f'<div class="cta-row">{cta_primary(ctx)}<a class="btn ghost" href="#services">See services</a></div>'
            f'</div></div></section>')
    return frame(ctx, CSS_DARK, nav(ctx) + hero + sections(ctx), "v-dark")


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
BUILDERS = {
    "editorial": build_editorial, "bento": build_bento, "brutalist": build_brutalist,
    "minimalist": build_minimalist, "darkmode": build_darkmode,
}


def build_ctx(lead: dict) -> dict:
    niche = lead.get("niche", "") or "Local Service"
    content = gm.content_of(niche)
    ctx = {
        "name": lead.get("business_name", "") or "Your Business",
        "city": lead.get("city", "") or "San Luis Obispo County",
        "niche": niche,
        "phone": (lead.get("phone", "") or "").strip(),
        "rating": (lead.get("rating", "") or "").strip(),
        "reviews": (lead.get("review_count", "") or "").strip(),
        "mono": gm.monogram(lead.get("business_name", "")),
        "hours": content["hours"],
        "tag": content["tag"], "sub": content["sub"], "cta": content["cta"],
        "svc": content["svc"], "rev": content["rev"],
    }
    ctx["tel"] = gm.tel_of(ctx["phone"])
    ctx["_jsonld"] = i18n_seo.jsonld(lead, content.get("svc"))
    ctx["_es"] = json.dumps(i18n_seo.i18n_map(ctx, content), ensure_ascii=False)
    return ctx


def load_leads(path: str) -> list[dict]:
    if not os.path.exists(path):
        sys.exit(f"ERROR: {path} not found. Run find_leads.py first.")
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate 5 design variants per lead.")
    ap.add_argument("--slug", help="Only build this slug.")
    args = ap.parse_args(argv)
    leads = load_leads(CSV_PATH)
    built = 0
    for lead in leads:
        slug = (lead.get("slug") or "").strip()
        if not slug or (args.slug and slug != args.slug):
            continue
        ctx = build_ctx(lead)
        d = os.path.join(OUT_DIR, slug)
        os.makedirs(d, exist_ok=True)
        for num, key, _label in VARIANTS:
            with open(os.path.join(d, f"variant-{num}-{key}.html"), "w", encoding="utf-8") as fh:
                fh.write(BUILDERS[key](ctx))
        built += 1
        print(f"  built  mockups/{slug}/  (5 variants)  {lead.get('business_name','')}")
    print(f"\nDone. {built} lead(s) x 5 variants = {built*5} files -> {OUT_DIR}/<slug>/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
