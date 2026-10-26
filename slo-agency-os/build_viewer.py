#!/usr/bin/env python3
"""
build_viewer.py  —  viewer.html : ONE self-contained file to view every mockup.
Embeds all variant pages as base64 and renders the selected one via <iframe srcdoc>,
so there are no cross-file links to break. Open viewer.html alone and browse all
14 leads x 5 styles, or pop any out full-size. Run by run_pipeline.py too.
"""
from __future__ import annotations
import base64, csv, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, "leads_database.csv")
MOCK = os.path.join(BASE, "mockups")
OUT = os.path.join(BASE, "viewer.html")
VAR = [("1","editorial","Editorial"),("2","bento","Bento"),("3","brutalist","Brutalist"),
       ("4","minimalist","Minimal"),("5","darkmode","Dark Mode")]


def build():
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    leads = []
    for r in rows:
        slug = (r.get("slug") or "").strip()
        if not slug:
            continue
        variants = []
        for num, key, label in VAR:
            fp = os.path.join(MOCK, slug, f"variant-{num}-{key}.html")
            if os.path.exists(fp):
                with open(fp, "rb") as fh:
                    variants.append({"key": key, "label": label,
                                     "b64": base64.b64encode(fh.read()).decode("ascii")})
        if variants:
            leads.append({"slug": slug, "name": r.get("business_name", ""),
                          "niche": r.get("niche", ""), "city": r.get("city", ""),
                          "variants": variants})
    return {"leads": leads}


TPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SLO Mockup Viewer</title>
<style>
:root{--bg:#0b1020;--panel:#121a31;--panel2:#0f1730;--line:#243154;--ink:#e8edf9;--muted:#9aa7c7;--brand:#5b8cff;--brand2:#7c5cff;--gold:#fbbf24;--font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font);background:var(--bg);color:var(--ink);height:100vh;display:flex;flex-direction:column;overflow:hidden}
.top{display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid var(--line);background:var(--panel2)}
.top .logo{width:34px;height:34px;border-radius:9px;display:grid;place-items:center;font-weight:800;color:#fff;background:linear-gradient(135deg,var(--brand),var(--brand2))}
.top h1{font-size:16px}.top .meta{color:var(--muted);font-size:12px}
.main{flex:1;display:flex;min-height:0}
.side{width:260px;border-right:1px solid var(--line);overflow-y:auto;background:var(--panel2)}
.lead{padding:11px 14px;border-bottom:1px solid var(--line);cursor:pointer}
.lead:hover{background:rgba(91,140,255,.08)}
.lead.on{background:rgba(91,140,255,.16);border-left:3px solid var(--brand)}
.lead .nm{font-weight:700;font-size:14px}
.lead .mt{color:var(--muted);font-size:11.5px;margin-top:2px}
.stage{flex:1;display:flex;flex-direction:column;min-width:0}
.tabs{display:flex;gap:6px;flex-wrap:wrap;padding:10px 14px;border-bottom:1px solid var(--line);align-items:center}
.tab{background:var(--panel);border:1px solid var(--line);color:var(--muted);font-size:12px;font-weight:700;border-radius:8px;padding:7px 12px;cursor:pointer}
.tab.on{background:var(--brand);border-color:var(--brand);color:#fff}
.pop{margin-left:auto;background:var(--panel);border:1px solid var(--line);color:var(--ink);font-size:12px;font-weight:700;border-radius:8px;padding:7px 12px;cursor:pointer}
.pop:hover{border-color:var(--brand)}
iframe{flex:1;width:100%;border:0;background:#fff}
@media(max-width:760px){.side{width:150px}}
</style></head>
<body>
<div class="top"><div class="logo">SLO</div><div><h1>Mockup Viewer</h1><div class="meta" id="meta"></div></div></div>
<div class="main">
  <div class="side" id="side"></div>
  <div class="stage">
    <div class="tabs" id="tabs"></div>
    <iframe id="frame" title="preview"></iframe>
  </div>
</div>
<script>
const D = {{DATA}};
let li=0, vi=0;
function bytes(b){return Uint8Array.from(atob(b),function(c){return c.charCodeAt(0);});}
function decode(b){return new TextDecoder("utf-8").decode(bytes(b));}
function esc(s){return (s||"").replace(/[&<>"]/g,function(m){return ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"})[m];});}
function renderSide(){
  document.getElementById("side").innerHTML = D.leads.map(function(l,i){
    return '<div class="lead'+(i===li?' on':'')+'" onclick="setLead('+i+')"><div class="nm">'+esc(l.name)+'</div><div class="mt">'+esc(l.niche)+' &middot; '+esc(l.city)+'</div></div>';
  }).join("");
}
function renderTabs(){
  const l=D.leads[li];
  document.getElementById("tabs").innerHTML = l.variants.map(function(v,i){
    return '<button class="tab'+(i===vi?' on':'')+'" onclick="setVar('+i+')">'+esc(v.label)+'</button>';
  }).join("") + '<button class="pop" onclick="popOut()">&#8599; Open full size</button>';
}
function renderFrame(){
  const v=D.leads[li].variants[vi];
  document.getElementById("frame").srcdoc = decode(v.b64);
  document.getElementById("meta").innerHTML = esc(D.leads[li].name)+" &middot; "+esc(v.label)+" &middot; "+(li+1)+"/"+D.leads.length;
}
function setLead(i){li=i;vi=0;renderSide();renderTabs();renderFrame();}
function setVar(i){vi=i;renderTabs();renderFrame();}
function popOut(){
  const v=D.leads[li].variants[vi];
  const url=URL.createObjectURL(new Blob([decode(v.b64)],{type:"text/html"}));
  window.open(url,"_blank");
}
renderSide();renderTabs();renderFrame();
</script>
</body></html>"""


def main():
    data = build()
    out = TPL.replace("{{DATA}}", json.dumps(data, ensure_ascii=False))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(out)
    n = sum(len(l["variants"]) for l in data["leads"])
    print(f"Wrote {OUT} with {len(data['leads'])} leads ({n} embedded mockups).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
