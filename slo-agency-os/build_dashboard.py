#!/usr/bin/env python3
"""
build_dashboard.py  —  TIER 4: Command Center + One-Click Handover
Reads leads_database.csv (+ pitch_assets.json + Tier-3 mockups) and emits a
self-contained cockpit at ./lead-command-center.html: KPI scorecard, kanban
pipeline, Pitch Panel (call script / SMS / email / review summary with copy),
one-click mockup launch, and a "Close Deal & Generate Handover Assets" button
that builds clients/<slug>/{index,invoice,onboarding_email,launch_checklist}
in-browser and downloads it as a ZIP (pure vanilla JS, no libraries), then moves
the lead to Closed/Won. All inline; zero external CDNs. Persists via localStorage.
    export AGENCY_NAME / AGENCY_EMAIL / AGENCY_PHONE   # used in the in-browser invoice
"""
from __future__ import annotations

import base64
import csv
import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "leads_database.csv")
OUT_PATH = os.path.join(BASE_DIR, "lead-command-center.html")
MOCKDIR = "mockups"
PITCH_JSON = os.path.join(BASE_DIR, "pitch_assets.json")

SETUP_FEE = 500
MRR_PER_WON = 50

def _load_config():
    cfg = os.path.join(BASE_DIR, "config.env")
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


AGENCY = {
    "name": os.environ.get("AGENCY_NAME", "[Your Agency Name]"),
    "email": os.environ.get("AGENCY_EMAIL", "[your@email.com]"),
    "phone": os.environ.get("AGENCY_PHONE", "[your phone]"),
}


def productionize(mockup_html: str) -> str:
    out = re.sub(r'<div class="demo-ribbon">.*?</div>', "", mockup_html, flags=re.S)
    out = out.replace(
        "Thanks! This is a demo form - on your live site this lands straight in your inbox.",
        "Thanks - we'll be in touch shortly!",
    )
    # KEEP the labeled "sample testimonials" disclaimer (compliance: never present
    # unverified sample reviews as real). Strip any "Website demo" footer tag.
    out = out.replace(" &middot; Website demo", "").replace(" · Website demo", "")
    out = re.sub(r"<!--.*?-->", "", out, flags=re.S)
    return out


def load_pitch() -> dict:
    if not os.path.exists(PITCH_JSON):
        return {}
    try:
        with open(PITCH_JSON, encoding="utf-8") as fh:
            return json.load(fh).get("leads", {})
    except (OSError, json.JSONDecodeError):
        return {}


def _variant_list(slug):
    labels = {"editorial":"Editorial","bento":"Bento","brutalist":"Brutalist","minimalist":"Minimal","darkmode":"Dark Mode"}
    order = ["1-editorial","2-bento","3-brutalist","4-minimalist","5-darkmode"]
    out = []
    for stem in order:
        key = stem.split("-",1)[1]
        fp = os.path.join(BASE_DIR, MOCKDIR, slug, f"variant-{stem}.html")
        if os.path.exists(fp):
            with open(fp, encoding="utf-8") as fh:
                raw = fh.read()
            out.append({"key": key, "label": labels[key],
                        "path": f"{MOCKDIR}/{slug}/variant-{stem}.html",
                        "b64": base64.b64encode(productionize(raw).encode("utf-8")).decode("ascii")})
    return out


def load_leads() -> list[dict]:
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"ERROR: {CSV_PATH} not found. Run find_leads.py first.")
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    pitch = load_pitch()
    leads = []
    for r in rows:
        slug = (r.get("slug") or "").strip()
        if not slug:
            continue
        mock_file = os.path.join(BASE_DIR, MOCKDIR, f"{slug}-demo.html")
        has_mock = os.path.exists(mock_file)
        prod_b64 = ""
        if has_mock:
            with open(mock_file, encoding="utf-8") as fh:
                prod_b64 = base64.b64encode(
                    productionize(fh.read()).encode("utf-8")).decode("ascii")
        leads.append({
            "name": r.get("business_name", ""), "niche": r.get("niche", ""),
            "city": r.get("city", ""), "phone": r.get("phone", ""),
            "address": r.get("address", ""), "rating": r.get("rating", ""),
            "reviews": r.get("review_count", ""), "website_status": r.get("website_status", ""),
            "source": r.get("source_url", ""), "confidence": r.get("confidence", ""),
            "slug": slug, "notes": r.get("notes", ""),
            "mockup": f"{MOCKDIR}/{slug}-demo.html", "has_mockup": has_mock,
            "stage": "Mockup Generated" if has_mock else (r.get("stage") or "New Identified"),
            "production_b64": "", "variants": _variant_list(slug), "pitch": pitch.get(slug, {}),
        })
    return leads


def main() -> int:
    payload = {
        "leads": load_leads(),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "setup_fee": SETUP_FEE, "mrr_per_won": MRR_PER_WON, "agency": AGENCY,
    }
    html = TEMPLATE.replace("{{PAYLOAD}}", json.dumps(payload, ensure_ascii=False))
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(html)
    n = sum(len(l.get("variants", [])) for l in payload["leads"])
    print(f"Wrote {OUT_PATH} with {len(payload['leads'])} leads ({n} variant pages embedded).")
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SLO Lead Command Center</title>
<style>
  :root{
    --bg:#0b1020;--panel:#121a31;--panel2:#0f1730;--line:#243154;--ink:#e8edf9;
    --muted:#9aa7c7;--brand:#5b8cff;--brand2:#7c5cff;--good:#22c55e;--warn:#f59e0b;--gold:#fbbf24;
    --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    --radius:14px;--shadow:0 12px 34px rgba(0,0,0,.4);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:var(--font);background:
     radial-gradient(900px 500px at 88% -10%,rgba(124,92,255,.18),transparent 60%),
     radial-gradient(800px 500px at -10% 0%,rgba(91,140,255,.16),transparent 55%),var(--bg);
     color:var(--ink);min-height:100vh}
  .wrap{max-width:1320px;margin:0 auto;padding:22px}
  a{color:var(--brand);text-decoration:none}
  code{font-family:var(--mono);font-size:12px}
  .top{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;margin-bottom:18px}
  .title{display:flex;align-items:center;gap:13px}
  .logo{width:44px;height:44px;border-radius:12px;display:grid;place-items:center;font-weight:800;
    color:#fff;background:linear-gradient(135deg,var(--brand),var(--brand2));box-shadow:var(--shadow)}
  h1{font-size:21px;letter-spacing:-.01em}
  .sub{color:var(--muted);font-size:13px;margin-top:2px}
  .gen{color:var(--muted);font-size:12px;text-align:right}
  .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:22px}
  .kpi{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);
    border-radius:var(--radius);padding:18px 20px;box-shadow:var(--shadow);position:relative;overflow:hidden}
  .kpi::after{content:"";position:absolute;right:-30px;top:-30px;width:90px;height:90px;border-radius:50%;
    background:radial-gradient(circle,rgba(91,140,255,.25),transparent 70%)}
  .kpi .lbl{color:var(--muted);font-size:12.5px;font-weight:600;text-transform:uppercase;letter-spacing:.06em}
  .kpi .val{font-size:30px;font-weight:800;margin-top:7px;letter-spacing:-.02em}
  .kpi .hint{color:var(--muted);font-size:12px;margin-top:3px}
  .kpi.green .val{color:var(--good)}.kpi.blue .val{color:var(--brand)}.kpi.purple .val{color:var(--brand2)}.kpi.gold .val{color:var(--gold)}
  .board{display:grid;grid-template-columns:repeat(5,minmax(225px,1fr));gap:14px;align-items:start;overflow-x:auto;padding-bottom:10px}
  .col{background:rgba(255,255,255,.02);border:1px solid var(--line);border-radius:var(--radius);min-height:120px}
  .col.drag{border-color:var(--brand);background:rgba(91,140,255,.08)}
  .col-h{display:flex;align-items:center;justify-content:space-between;padding:13px 14px;border-bottom:1px solid var(--line)}
  .col-h .nm{font-weight:700;font-size:13.5px}
  .col-h .ct{background:var(--panel);border:1px solid var(--line);color:var(--muted);font-size:12px;font-weight:700;border-radius:999px;padding:2px 9px}
  .col-body{padding:12px;display:flex;flex-direction:column;gap:10px;min-height:60px}
  .card{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);
    border-radius:12px;padding:13px;cursor:grab;box-shadow:0 4px 14px rgba(0,0,0,.25);transition:transform .12s,border-color .12s}
  .card:hover{transform:translateY(-2px);border-color:var(--brand)}
  .card .cn{font-weight:700;font-size:14.5px}
  .card .cm{color:var(--muted);font-size:12.5px;margin-top:3px;display:flex;gap:7px;flex-wrap:wrap;align-items:center}
  .pill{font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:999px;border:1px solid var(--line)}
  .pill.niche{color:var(--brand);border-color:rgba(91,140,255,.4)}
  .pill.hi{color:var(--good);border-color:rgba(34,197,94,.4)}
  .pill.med{color:var(--warn);border-color:rgba(245,158,11,.4)}
  .pill.low{color:var(--muted)}
  .cmeta{display:flex;align-items:center;gap:6px;margin-top:9px;color:var(--muted);font-size:12px}
  .star{color:var(--gold)}
  .card .deal{margin-top:11px;width:100%;border:0;border-radius:9px;cursor:pointer;font-weight:800;font-size:12px;
    padding:9px;color:#1a1300;background:linear-gradient(135deg,#fbbf24,#f59e0b);box-shadow:0 3px 10px rgba(245,158,11,.3)}
  .card .deal:hover{filter:brightness(1.07)}
  .card .deal.won{background:linear-gradient(135deg,#22c55e,#16a34a);color:#04230f}
  .scrim{position:fixed;inset:0;background:rgba(2,6,20,.6);opacity:0;pointer-events:none;transition:opacity .2s;z-index:40}
  .scrim.open{opacity:1;pointer-events:auto}
  .drawer{position:fixed;top:0;right:0;height:100%;width:480px;max-width:94vw;background:var(--panel);
    border-left:1px solid var(--line);box-shadow:var(--shadow);transform:translateX(100%);transition:transform .25s;z-index:41;display:flex;flex-direction:column}
  .drawer.open{transform:translateX(0)}
  .dh{padding:20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
  .dh h2{font-size:19px}.dh .dsub{color:var(--muted);font-size:13px;margin-top:4px}
  .x{background:none;border:0;color:var(--muted);font-size:24px;cursor:pointer;line-height:1}
  .db{padding:18px 20px;overflow-y:auto;flex:1}
  .row{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid var(--line);font-size:14px}
  .row .k{color:var(--muted)}.row .v{text-align:right;font-weight:600;max-width:62%}
  .btnrow{display:flex;gap:10px;margin:16px 0}
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border-radius:11px;font-weight:700;font-size:14px;
    padding:12px 16px;cursor:pointer;border:1px solid var(--line);background:var(--panel2);color:var(--ink);flex:1}
  .btn.primary{background:linear-gradient(135deg,var(--brand),var(--brand2));border:0;color:#fff}
  .btn.disabled{opacity:.45;pointer-events:none}
  .deal-big{width:100%;border:0;border-radius:12px;cursor:pointer;font-weight:800;font-size:15px;padding:15px;margin:4px 0 6px;
    color:#1a1300;background:linear-gradient(135deg,#fbbf24,#f59e0b);box-shadow:0 6px 18px rgba(245,158,11,.34)}
  .deal-big:hover{filter:brightness(1.07)}
  .deal-big.won{background:linear-gradient(135deg,#22c55e,#16a34a);color:#04230f}
  label.fl{display:block;color:var(--muted);font-size:12.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin:16px 0 7px}
  select,textarea{width:100%;background:var(--panel2);border:1px solid var(--line);color:var(--ink);border-radius:11px;padding:11px 13px;font:inherit;font-size:14px}
  textarea{min-height:90px;resize:vertical}select:focus,textarea:focus{outline:none;border-color:var(--brand)}
  .saved{color:var(--good);font-size:12px;margin-top:7px;height:14px;opacity:0;transition:opacity .2s}.saved.show{opacity:1}
  .pitch h3{font-size:13px;margin:18px 0 6px;color:var(--brand2);text-transform:uppercase;letter-spacing:.05em}
  .gap{background:rgba(124,92,255,.1);border:1px solid rgba(124,92,255,.35);border-radius:10px;padding:12px;font-size:13.5px;line-height:1.5}
  .pblock{position:relative;background:var(--panel2);border:1px solid var(--line);border-radius:10px;margin-top:8px}
  .pblock pre{white-space:pre-wrap;word-break:break-word;font-family:var(--mono);font-size:12px;line-height:1.5;padding:12px;color:#d7e0f5;max-height:230px;overflow:auto}
  .copy{position:absolute;top:8px;right:8px;background:var(--panel);border:1px solid var(--line);color:var(--muted);font-size:11px;font-weight:700;border-radius:7px;padding:4px 9px;cursor:pointer}
  .copy:hover{color:var(--ink);border-color:var(--brand)}
  .legend{color:var(--muted);font-size:12px;margin:14px 2px 0;line-height:1.7}
  .footer{color:var(--muted);font-size:12px;margin-top:18px;line-height:1.7}
  .vtabs{display:flex;gap:6px;flex-wrap:wrap;margin:14px 0 10px}
  .vtab{background:var(--panel2);border:1px solid var(--line);color:var(--muted);font-size:12px;font-weight:700;border-radius:8px;padding:7px 11px;cursor:pointer}
  .vtab.on{background:var(--brand);border-color:var(--brand);color:#fff}
  .vframe{width:100%;height:440px;border:1px solid var(--line);border-radius:12px;background:#fff}
  .toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(20px);background:var(--panel);
    border:1px solid var(--good);color:var(--ink);padding:13px 20px;border-radius:12px;box-shadow:var(--shadow);
    font-size:14px;font-weight:600;opacity:0;pointer-events:none;transition:opacity .25s,transform .25s;z-index:60;max-width:90vw}
  .toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
  @media(max-width:1100px){.kpis{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="title"><div class="logo">SLO</div>
      <div><h1>Lead Command Center</h1><div class="sub">SLO County &middot; no-website prospects &middot; $500 setup + $50/mo</div></div>
    </div>
    <div class="gen" id="gen"></div>
  </div>
  <div class="kpis" id="kpis"></div>
  <div class="board" id="board"></div>
  <div class="footer" id="foot"></div>
</div>
<div class="scrim" id="scrim" onclick="closeDrawer()"></div>
<aside class="drawer" id="drawer" aria-hidden="true"></aside>
<div class="toast" id="toast"></div>
<script>
const DATA = {{PAYLOAD}};
const STAGES = ["New Identified","Mockup Generated","Outreach Initiated","Negotiating","Closed/Won"];
const KEY = "slo_crm_v2";
const $ = (id)=>document.getElementById(id);
let STATE = (function(){try{return JSON.parse(localStorage.getItem(KEY))||{};}catch(e){return {};}})();
function saveState(){try{localStorage.setItem(KEY, JSON.stringify(STATE));}catch(e){}}
function stageOf(l){return (STATE[l.slug]&&STATE[l.slug].stage)||l.stage||"New Identified";}
function notesOf(l){return (STATE[l.slug]&&STATE[l.slug].notes!=null)?STATE[l.slug].notes:(l.notes||"");}
function setField(slug,k,v){STATE[slug]=Object.assign({},STATE[slug],{[k]:v});saveState();}
function money(n){return "$"+n.toLocaleString("en-US");}
function confClass(c){c=(c||"").toLowerCase();if(c.indexOf("high")>=0)return"hi";if(c.indexOf("low")>=0)return"low";return"med";}
function escapeHtml(s){return (s||"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));}
function selVariant(l){var s=STATE[l.slug]&&STATE[l.slug].variant;return s||((l.variants&&l.variants[0])?l.variants[0].key:'editorial');}
function setVariant(slug,key){setField(slug,'variant',key);var l=DATA.leads.find(function(x){return x.slug===slug;});var v=(l.variants||[]).find(function(x){return x.key===key;});var f=document.getElementById('vframe');if(f&&v)f.src=v.path;document.querySelectorAll('.vtab').forEach(function(b){b.classList.toggle('on',b.getAttribute('data-vk')===key);});}
function renderKPIs(){
  const total=DATA.leads.length;
  const won=DATA.leads.filter(l=>stageOf(l)==="Closed/Won").length;
  const pending=DATA.leads.filter(l=>stageOf(l)!=="Closed/Won").length;
  const cards=[
    ["blue","Leads scoped",total,pending+" still in pipeline"],
    ["purple","Est. pipeline value",money(pending*DATA.setup_fee),money(DATA.setup_fee)+" &times; "+pending+" pending"],
    ["green","MRR (won)",money(won*DATA.mrr_per_won),money(won*DATA.mrr_per_won*12)+" / yr recurring"],
    ["gold","Closed / won",won,won?"&#9889; deals closed":"None yet"],
  ];
  $("kpis").innerHTML=cards.map(c=>`<div class="kpi ${c[0]}"><div class="lbl">${c[1]}</div><div class="val">${c[2]}</div><div class="hint">${c[3]}</div></div>`).join("");
}
function cardHTML(l){
  const won=stageOf(l)==="Closed/Won";
  const rating=l.rating?`<span class="cmeta"><span class="star">&#9733;</span> ${l.rating}${l.reviews?(" &middot; "+l.reviews+" reviews"):""}</span>`:(l.reviews?`<span class="cmeta">${l.reviews} reviews</span>`:"");
  return `<div class="card" draggable="true" data-slug="${l.slug}" onclick="openDrawer('${l.slug}')">
    <div class="cn">${escapeHtml(l.name)}</div>
    <div class="cm"><span class="pill niche">${escapeHtml(l.niche||"")}</span><span class="pill ${confClass(l.confidence)}">${escapeHtml(l.confidence||"")}</span><span>${escapeHtml(l.city||"")}</span></div>
    ${rating}
    <button class="deal ${won?'won':''}" onclick="closeDeal('${l.slug}',event)">${won?'&#10003; Re-download bundle':'&#9889; Close Deal &amp; Generate Assets'}</button>
  </div>`;
}
function renderBoard(){
  $("board").innerHTML=STAGES.map(st=>{
    const items=DATA.leads.filter(l=>stageOf(l)===st);
    return `<div class="col" data-stage="${st}" ondragover="onOver(event)" ondragleave="onLeave(event)" ondrop="onDrop(event)">
      <div class="col-h"><span class="nm">${st}</span><span class="ct">${items.length}</span></div>
      <div class="col-body">${items.map(cardHTML).join("")||'<div style="color:var(--muted);font-size:12px;padding:6px">&mdash;</div>'}</div>
    </div>`;
  }).join("");
  bindDrag();
}
let dragSlug=null;
function bindDrag(){document.querySelectorAll(".card").forEach(c=>{c.addEventListener("dragstart",e=>{dragSlug=c.dataset.slug;e.dataTransfer.effectAllowed="move";});c.addEventListener("dragend",()=>{dragSlug=null;});});}
function onOver(e){e.preventDefault();e.currentTarget.classList.add("drag");}
function onLeave(e){e.currentTarget.classList.remove("drag");}
function onDrop(e){e.preventDefault();e.currentTarget.classList.remove("drag");if(!dragSlug)return;setField(dragSlug,"stage",e.currentTarget.dataset.stage);renderBoard();renderKPIs();}
function pblock(label,text){if(!text)return"";return `<h3>${label}</h3><div class="pblock"><button class="copy" onclick="copyText(this)">Copy</button><pre>${escapeHtml(text)}</pre></div>`;}
function openDrawer(slug){
  const l=DATA.leads.find(x=>x.slug===slug);if(!l)return;
  const won=stageOf(l)==="Closed/Won";
  const selV=selVariant(l);const vlist=l.variants||[];
  const vsel=vlist.find(function(v){return v.key===selV;})||vlist[0];
  const vtabs=vlist.map(function(v){return '<button class="vtab '+(v.key===selV?'on':'')+'" data-vk="'+v.key+'" onclick="setVariant(\''+l.slug+'\',\''+v.key+'\')">'+v.label+'</button>';}).join("");
  const vframe=vsel?('<label class="fl">Style preview &mdash; pick the look to pitch</label><div class="vtabs">'+vtabs+'</div><iframe class="vframe" id="vframe" src="'+vsel.path+'" title="preview"></iframe>'):"";
  const mock=vsel?`<a class="btn primary" href="${vsel.path}" target="_blank" rel="noopener">&#9658; Open full page</a>`:(l.has_mockup?`<a class="btn primary" href="${l.mockup}" target="_blank" rel="noopener">&#9658; Launch mockup</a>`:`<span class="btn disabled">No mockup</span>`);
  const src=l.source?`<a class="btn" href="${l.source}" target="_blank" rel="noopener">View source</a>`:"";
  const rows=[["Phone",l.phone||'<span style="color:var(--warn)">verify before calling</span>'],["Address",l.address||"&mdash;"],["Rating",l.rating?(l.rating+" &#9733;"):"&mdash;"],["Reviews",l.reviews||"&mdash;"],["Website",l.website_status||"&mdash;"],["Confidence",l.confidence||"&mdash;"]]
    .map(r=>`<div class="row"><span class="k">${r[0]}</span><span class="v">${r[1]}</span></div>`).join("");
  const stageOpts=STAGES.map(s=>`<option ${stageOf(l)===s?"selected":""}>${s}</option>`).join("");
  const p=l.pitch||{};
  const pitch=(p.call_script||p.email_sequence)?`<div class="pitch">
      <h3>Reputation gap</h3><div class="gap">${escapeHtml(p.reputation_gap||"")}</div>
      ${pblock("Why us (positioning)",p.why_us)}${pblock("Review summary",p.review_summary)}${pblock("Cold call script",p.call_script)}${pblock("SMS hook",p.sms_hook)}${pblock("Email sequence",p.email_sequence)}
    </div>`:`<p class="legend">No pitch kit found. Run <code>python pitch_studio.py</code> to generate one.</p>`;
  $("drawer").innerHTML=`
    <div class="dh"><div><h2>${escapeHtml(l.name)}</h2><div class="dsub">${escapeHtml(l.niche)} &middot; ${escapeHtml(l.city)}, CA</div></div><button class="x" onclick="closeDrawer()">&times;</button></div>
    <div class="db">
      <button class="deal-big ${won?'won':''}" onclick="closeDeal('${l.slug}',event)">${won?'&#10003; Won &mdash; re-download handover bundle':'&#9889; Close Deal &amp; Generate Handover Assets'}</button>
      <div class="btnrow">${mock}${src}</div>${vframe}
      ${rows}
      <label class="fl">Pipeline stage</label>
      <select onchange="setField('${l.slug}','stage',this.value);renderBoard();renderKPIs();">${stageOpts}</select>
      <label class="fl">Notes</label>
      <textarea id="nt" oninput="onNotes('${l.slug}',this.value)">${escapeHtml(notesOf(l))}</textarea>
      <div class="saved" id="sv">Saved &#10003;</div>
      ${pitch}
      <p class="legend"><strong>Reminder:</strong> confirm the phone before any call/text/email. Calls &amp; texts &rarr; TCPA + DNC; email &rarr; CAN-SPAM. Outreach copy is a draft for manual use.</p>
    </div>`;
  $("drawer").classList.add("open");$("drawer").setAttribute("aria-hidden","false");$("scrim").classList.add("open");
}
function closeDrawer(){$("drawer").classList.remove("open");$("scrim").classList.remove("open");$("drawer").setAttribute("aria-hidden","true");}
let noteTimer=null;
function onNotes(slug,val){setField(slug,"notes",val);const sv=$("sv");if(sv){sv.classList.add("show");clearTimeout(noteTimer);noteTimer=setTimeout(()=>sv.classList.remove("show"),1200);}}
function copyText(btn){const t=btn.parentNode.querySelector("pre").innerText;copyToClipboard(t);btn.textContent="Copied!";setTimeout(()=>btn.textContent="Copy",1200);}
function copyToClipboard(t){if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).catch(()=>fallbackCopy(t));}else{fallbackCopy(t);}}
function fallbackCopy(t){const a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();try{document.execCommand("copy");}catch(e){}a.remove();}
let toastT=null;
function toast(msg){const t=$("toast");t.innerHTML=msg;t.classList.add("show");clearTimeout(toastT);toastT=setTimeout(()=>t.classList.remove("show"),3200);}
const MON=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function fmtDate(d){return MON[d.getMonth()]+" "+d.getDate()+", "+d.getFullYear();}
function invoiceHTML(l){
  const today=new Date();const ms=new Date(today.getTime()+30*864e5);
  const inv="INV-"+today.getFullYear()+String(today.getMonth()+1).padStart(2,"0")+String(today.getDate()).padStart(2,"0")+"-"+l.slug.slice(0,6).toUpperCase();
  const A=DATA.agency,F=DATA.setup_fee,M=DATA.mrr_per_won;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Invoice ${inv} - ${escapeHtml(l.name)}</title><style>
:root{--ink:#0e1726;--muted:#5a6678;--line:#e2e8f1;--bg:#f6f8fc}*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink);padding:32px;line-height:1.55}
.inv{max-width:760px;margin:0 auto;background:#fff;border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 18px 50px rgba(15,23,42,.08)}
.top{display:flex;justify-content:space-between;padding:32px;background:linear-gradient(135deg,#1e293b,#0e1726);color:#fff}
.top h1{font-size:30px}.pill{display:inline-block;background:#f59e0b;color:#1a1300;font-weight:800;font-size:12px;padding:4px 11px;border-radius:999px;margin-top:8px}
.meta{text-align:right;font-size:13px;opacity:.85;line-height:1.7}.parties{display:flex;justify-content:space-between;gap:24px;padding:28px 32px;border-bottom:1px solid var(--line)}
.parties h3{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:7px}.parties p{font-size:14.5px;font-weight:600}
table{width:100%;border-collapse:collapse}thead th{text-align:left;font-size:11px;text-transform:uppercase;color:var(--muted);padding:14px 32px;border-bottom:1px solid var(--line)}
tbody td{padding:18px 32px;border-bottom:1px solid var(--line);font-size:15px}td.amt,th.amt{text-align:right}.desc small{display:block;color:var(--muted);font-size:13px;font-weight:400;margin-top:3px}
.totals{display:flex;justify-content:flex-end;padding:22px 32px}.totals table{width:auto;min-width:280px}.totals td{padding:6px 0;border:0}
.grand td{font-size:19px;font-weight:800;border-top:2px solid var(--ink);padding-top:12px}
.pay{margin:0 32px 28px;padding:20px;border:2px dashed var(--line);border-radius:12px;background:var(--bg);text-align:center;color:var(--muted);font-size:14px}
.terms{padding:0 32px 32px;font-size:12.5px;color:var(--muted);line-height:1.7}.foot{padding:18px 32px;background:var(--bg);font-size:12px;color:var(--muted);text-align:center}
</style></head><body><div class="inv">
<div class="top"><div><h1>INVOICE</h1><div class="pill">DUE UPON RECEIPT</div></div><div class="meta">Invoice <b>${inv}</b><br>Issued ${fmtDate(today)}<br>Due ${fmtDate(today)}</div></div>
<div class="parties"><div><h3>From</h3><p>${escapeHtml(A.name)}</p><p style="font-weight:400;color:var(--muted)">${escapeHtml(A.email)}<br>${escapeHtml(A.phone)}</p></div>
<div style="text-align:right"><h3>Bill To</h3><p>${escapeHtml(l.name)}</p><p style="font-weight:400;color:var(--muted)">${escapeHtml(l.address||"")}<br>${escapeHtml(l.phone||"")}</p></div></div>
<table><thead><tr><th>Description</th><th class="amt">Amount</th></tr></thead><tbody>
<tr><td class="desc">Website Design &amp; Setup &mdash; one-time<small>Custom responsive single-page site, mobile-optimized, contact form, hosting setup.</small></td><td class="amt">$${F}.00</td></tr>
<tr><td class="desc">Maintenance &amp; Hosting &mdash; monthly<small>Hosting, updates, edits, monitoring. First charge ${fmtDate(ms)}, then monthly.</small></td><td class="amt">$${M}.00 / mo</td></tr>
</tbody></table><div class="totals"><table><tr><td>Setup (due now)</td><td class="amt">$${F}.00</td></tr><tr><td>Monthly (from ${fmtDate(ms)})</td><td class="amt">$${M}.00</td></tr><tr class="grand"><td>Due today</td><td class="amt">$${F}.00</td></tr></table></div>
<div class="pay"><b>Payment:</b> [ Connect your Stripe account &mdash; paste your payment link / card embed here. ]<br>Placeholder only; no live payment is collected by this template.</div>
<div class="terms"><b>Agreement terms.</b> The $${F}.00 setup fee is due upon receipt. The $${M}.00/month maintenance &amp; hosting fee begins ${fmtDate(ms)} (30 days from issue) and recurs monthly until cancelled with 30 days' notice. Template &mdash; review before sending.</div>
<div class="foot">${escapeHtml(A.name)} &middot; Prepared for ${escapeHtml(l.name)}, ${escapeHtml(l.city)}, CA &middot; ${fmtDate(today)}</div></div></body></html>`;
}
function onboardingEmail(l){
  const A=DATA.agency,M=DATA.mrr_per_won;
  return `Subject: Welcome aboard, ${l.name} - your new website is ready to launch\n\nHi [First Name],\n\nWelcome to ${A.name}! I'm excited to get ${l.name} online.\n\nYour custom preview site is ready to review here:\n  [ paste preview link - e.g. open clients/${l.slug}/index.html ]\n\nIt's built specifically for a ${l.niche||"local service"} business in ${l.city||"your area"}, with your services, a tap-to-call button, and a contact form already wired up.\n\nTo finalize your launch, I need three quick things:\n  1. Your logo (PNG/SVG/PDF), if you have one.\n  2. 3-6 photos to feature (team, work, storefront, or food).\n  3. Confirmation of your hours, service area, and best phone number.\n\nOnce I have those, I'll swap them in, connect your domain, and push the site live - usually within a few business days.\n\nThe one-time setup invoice is attached (setup due on receipt; the $${M}/mo maintenance & hosting begins 30 days after launch). Reply with your assets and any questions.\n\nLooking forward to getting ${l.name} found online.\n\nBest,\n[Your Name]\n${A.name}\n${A.email} - ${A.phone}\n\n-\nReady-to-send draft. Personalize bracketed fields and confirm the contact opted in / is a fair business contact before sending (CAN-SPAM).\n`;
}
function launchChecklist(l){
  const base=(l.name||"").toLowerCase().replace(/[^a-z0-9]/g,"").slice(0,18);
  const cityb=(l.city||"").toLowerCase().replace(/[^a-z0-9]/g,"");
  const F=DATA.setup_fee,M=DATA.mrr_per_won;
  return `# Launch Checklist - ${l.name}\n\n_Generated ${fmtDate(new Date())} - stage: Closed/Won - ${l.city||""}, CA_\n\n## 1. Domain\n- [ ] Register a domain for the client:\n  - \`${base}slo.com\`\n  - \`${base}.com\`\n  - \`${base}${cityb}.com\`\n- [ ] Confirm preferred domain; point DNS to host.\n\n## 2. Hosting & Deploy\n- [ ] Connect hosting platform / storage bucket (Netlify, Cloudflare Pages, S3).\n- [ ] Deploy clients/${l.slug}/index.html as the site root.\n- [ ] Enable HTTPS/SSL; verify mobile rendering.\n\n## 3. Content Swap\n- [ ] Replace sample testimonials with the client's real Google/Yelp reviews.\n- [ ] Insert client logo + supplied photos.\n- [ ] Confirm phone, hours, and service area.\n\n## 4. Billing\n- [ ] Send invoice.html - $${F} setup (due on receipt).\n- [ ] Schedule $${M}/mo maintenance to begin 30 days post-launch.\n\n## 5. Monitoring\n- [ ] Set up an uptime/status check.\n- [ ] Add to Google Business Profile; submit sitemap.\n- [ ] Calendar a 2-week client check-in.\n`;
}
const CRCT=(function(){const t=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=(c&1)?(0xEDB88320^(c>>>1)):(c>>>1);t[n]=c>>>0;}return t;})();
function crc32(u8){let c=0xFFFFFFFF;for(let i=0;i<u8.length;i++)c=CRCT[(c^u8[i])&0xFF]^(c>>>8);return (c^0xFFFFFFFF)>>>0;}
function b64ToBytes(b64){const bin=atob(b64);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return u;}
function makeZip(files){
  const enc=new TextEncoder();const chunks=[];const central=[];let offset=0;const now=new Date();
  const dt=((now.getHours()<<11)|(now.getMinutes()<<5)|(now.getSeconds()>>1))&0xFFFF;
  const dd=(((now.getFullYear()-1980)<<9)|((now.getMonth()+1)<<5)|now.getDate())&0xFFFF;
  const u16=v=>[v&0xFF,(v>>>8)&0xFF];const u32=v=>[v&0xFF,(v>>>8)&0xFF,(v>>>16)&0xFF,(v>>>24)&0xFF];
  files.forEach(f=>{
    const nameB=enc.encode(f.name);const data=f.data;const crc=crc32(data);const sz=data.length;
    const lfh=[].concat(u32(0x04034b50),u16(20),u16(0),u16(0),u16(dt),u16(dd),u32(crc),u32(sz),u32(sz),u16(nameB.length),u16(0));
    chunks.push(new Uint8Array(lfh),nameB,data);
    const cdh=[].concat(u32(0x02014b50),u16(20),u16(20),u16(0),u16(0),u16(dt),u16(dd),u32(crc),u32(sz),u32(sz),u16(nameB.length),u16(0),u16(0),u16(0),u16(0),u32(0),u32(offset));
    central.push(new Uint8Array(cdh),nameB);
    offset+=30+nameB.length+sz;
  });
  let cdSize=0;central.forEach(c=>cdSize+=c.length);
  const eocd=[].concat(u32(0x06054b50),u16(0),u16(0),u16(files.length),u16(files.length),u32(cdSize),u32(offset),u16(0));
  const all=chunks.concat(central,[new Uint8Array(eocd)]);
  let total=0;all.forEach(c=>total+=c.length);
  const out=new Uint8Array(total);let p=0;all.forEach(c=>{out.set(c,p);p+=c.length;});
  return out;
}
function downloadBytes(bytes,fname){
  const blob=new Blob([bytes],{type:"application/zip"});const url=URL.createObjectURL(blob);
  const a=document.createElement("a");a.href=url;a.download=fname;document.body.appendChild(a);a.click();
  setTimeout(()=>{a.remove();URL.revokeObjectURL(url);},500);
}
function closeDeal(slug,ev){
  if(ev)ev.stopPropagation();
  const l=DATA.leads.find(x=>x.slug===slug);if(!l)return;
  const enc=new TextEncoder();const base="clients/"+slug+"/";const files=[];
  var _sv=selVariant(l);var _v=(l.variants||[]).find(function(x){return x.key===_sv;})||(l.variants||[])[0];
  var _idx=(_v&&_v.b64)?b64ToBytes(_v.b64):(l.production_b64?b64ToBytes(l.production_b64):null);
  if(!_idx){toast("Cannot close &mdash; no mockup for "+escapeHtml(l.name)+". Generate a mockup first.");return;}
  files.push({name:base+"index.html",data:_idx});
  files.push({name:base+"invoice.html",data:enc.encode(invoiceHTML(l))});
  files.push({name:base+"onboarding_email.txt",data:enc.encode(onboardingEmail(l))});
  files.push({name:base+"launch_checklist.md",data:enc.encode(launchChecklist(l))});
  try{downloadBytes(makeZip(files),slug+"-handover.zip");}
  catch(e){toast("Bundle error: "+e.message);return;}
  setField(slug,"stage","Closed/Won");renderBoard();renderKPIs();
  if($("drawer").classList.contains("open"))openDrawer(slug);
  toast("&#9889; Handover bundle downloaded ("+files.length+" files) &middot; "+escapeHtml(l.name)+" &rarr; Closed/Won");
}
$("gen").innerHTML="Generated "+DATA.generated_at+"<br>"+DATA.leads.length+" leads &middot; data: leads_database.csv";
$("foot").innerHTML="Pipeline value = "+money(DATA.setup_fee)+" &times; pending leads. MRR = "+money(DATA.mrr_per_won)+" &times; closed/won. "+
  "Drag cards or use the stage selector; changes persist in this browser. The &#9889; button bundles clients/&lt;slug&gt;/ (index, invoice, email, checklist) into a downloadable ZIP. Mockups open from the local mockups/ folder.";
renderKPIs();renderBoard();
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeDrawer();});
</script>
</body>
</html>"""


if __name__ == "__main__":
    raise SystemExit(main())
