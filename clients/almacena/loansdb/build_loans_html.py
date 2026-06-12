"""Render the self-contained interactive loan-book dashboard -> loans.html.

Reads the reconstruction from loan_book.build() and embeds it as JSON in a
single static HTML file (vanilla JS + CSS, no CDN, opens by double-click).
Compact, non-scrolling: header + KPIs + MoM matrix are fixed; only the loan
table pane scrolls internally. Everything is flagged DERIVED / 2026 / USD.

    uv run python clients/almacena/loansdb/build_loans_html.py
"""

from __future__ import annotations

import json
from pathlib import Path

import loan_book

OUT = Path(__file__).resolve().parent / "loans.html"

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Almacena — Lender Loan Book</title>
<style>
  :root{--ink:#0d2b2b;--teal:#013E3F;--accent:#009091;--coral:#E67D5A;
        --up:#1a8f6f;--down:#cf5b43;--line:#e3e8e8;--muted:#7d8c8c;--bg:#eef2f2;}
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%}
  body{font:13px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);
       background:var(--bg);display:flex;flex-direction:column;height:100vh;overflow:hidden}
  header{background:var(--teal);color:#fff;padding:10px 18px;display:flex;align-items:center;gap:14px;flex:0 0 auto}
  header h1{font-size:16px;font-weight:600;letter-spacing:.2px}
  .badge{background:var(--coral);color:#fff;font-size:10px;font-weight:700;letter-spacing:.5px;
         padding:3px 8px;border-radius:4px}
  .sub{color:#bcd;font-size:11px;margin-left:auto;text-align:right}
  .tabs{display:flex;gap:6px;padding:10px 18px 0;flex:0 0 auto}
  .tab{padding:6px 16px;border:1px solid var(--line);background:#fff;border-radius:6px 6px 0 0;
       cursor:pointer;font-weight:600;color:var(--muted)}
  .tab.on{color:var(--teal);border-bottom-color:#fff;box-shadow:0 -2px 0 var(--accent) inset}
  main{flex:1 1 auto;display:grid;grid-template-columns:minmax(420px,1fr) 1.6fr;gap:12px;
       padding:12px 18px 14px;min-height:0}
  .col{display:flex;flex-direction:column;gap:12px;min-height:0}
  .card{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 14px}
  .kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
  .kpi .lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}
  .kpi .val{font-size:18px;font-weight:700;color:var(--teal);margin-top:2px}
  .kpi .d{font-size:11px;font-weight:600;margin-top:1px}
  .up{color:var(--up)} .down{color:var(--down)} .flat{color:var(--muted)}
  h2{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:8px}
  table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
  th,td{padding:5px 7px;text-align:right;white-space:nowrap}
  th:first-child,td:first-child,th.l,td.l{text-align:left}
  thead th{font-size:10px;color:var(--muted);text-transform:uppercase;border-bottom:1px solid var(--line);
           cursor:pointer;position:sticky;top:0;background:#fff}
  .matrix td{border-bottom:1px solid #f0f3f3}
  .matrix td.sel{background:#eaf5f4;font-weight:700}
  .matrix .mlab{color:var(--muted);font-size:11px}
  .matrix .delta{font-size:10px;display:block}
  .changes{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  .chg{background:#f7faf9;border:1px solid var(--line);border-radius:6px;padding:8px 10px}
  .chg .n{font-size:16px;font-weight:700}
  .filters{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px}
  select,input{font:inherit;padding:4px 6px;border:1px solid var(--line);border-radius:5px;background:#fff}
  .tablewrap{flex:1 1 auto;overflow:auto;border:1px solid var(--line);border-radius:8px;background:#fff}
  .pill{font-size:9px;font-weight:700;padding:1px 5px;border-radius:8px}
  .pill.new{background:#e3f3ef;color:var(--up)} .pill.mat{background:#fbe9e3;color:var(--down)}
  tbody tr:hover{background:#f6fafa}
  .foot{flex:0 0 auto;padding:4px 18px 8px;color:var(--muted);font-size:10px}
</style></head>
<body>
<header>
  <h1>Almacena — Lender Loan Book</h1>
  <span class="badge">DERIVED</span>
  <span class="sub">__SUB__</span>
</header>
<div class="tabs" id="tabs"></div>
<main>
  <div class="col">
    <div class="card"><h2>Selected month — <span id="mlabel"></span></h2><div class="kpis" id="kpis"></div></div>
    <div class="card"><h2>Month-over-month book (USD)</h2><table class="matrix" id="matrix"></table></div>
    <div class="card"><h2>What changed this month</h2><div class="changes" id="changes"></div></div>
  </div>
  <div class="col">
    <div class="filters">
      <label>Lender <select id="fLender"><option value="">All</option></select></label>
      <label>Status <select id="fStatus">
        <option value="">All</option><option value="new">New this month</option>
        <option value="maturing">Maturing this month</option></select></label>
      <label>Rate <select id="fRate"><option value="">All</option>
        <option value="lo">&lt; 9%</option><option value="mid">9–10%</option><option value="hi">&ge; 10%</option></select></label>
      <label>Sort <select id="fSort">
        <option value="principal">Principal</option><option value="available">Available</option>
        <option value="accrued">Accrued interest</option><option value="rate">Rate</option>
        <option value="repay">Repayment</option></select></label>
      <span id="tcount" style="margin-left:auto;color:var(--muted)"></span>
    </div>
    <div class="tablewrap"><table id="loans"></table></div>
  </div>
</main>
<div class="foot" id="foot"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
let sel=D.months.length-1;
const usd=v=>'$'+Math.round(v).toLocaleString('en-US');
const usdM=v=>Math.abs(v)>=1e6?'$'+(v/1e6).toFixed(2)+'M':(Math.abs(v)>=1e3?'$'+Math.round(v/1e3)+'k':'$'+Math.round(v));
const pct=v=>(v*100).toFixed(2)+'%';
const arrow=d=>d>0?'\\u25B2':(d<0?'\\u25BC':'\\u2013');
const cls=(d,goodUp=true)=>d===0?'flat':((d>0)===goodUp?'up':'down');
const KPI=[['available','Available Funds',usdM,true],['cost','Cost of Funds',usdM,false],
  ['blended_rate','Blended Rate',pct,false],['n_loans','Active Loans',v=>v,true],
  ['n_lenders','Lenders',v=>v,true],['principal','Total Principal',usdM,true]];

function tabs(){document.getElementById('tabs').innerHTML=D.months.map((m,i)=>
  `<div class="tab ${i===sel?'on':''}" onclick="pick(${i})">${m.label}</div>`).join('');}
function kpis(){const m=D.months[sel];document.getElementById('mlabel').textContent=m.label;
  document.getElementById('kpis').innerHTML=KPI.map(([k,lbl,fmt,gu])=>{
    const d=m.mom?m.mom[k]:null;const dd=d==null?'':`<div class="d ${cls(d,gu)}">${arrow(d)} ${k==='blended_rate'?(d*100).toFixed(2)+'pp':(typeof m[k]==='number'&&Math.abs(m[k])>1000?usd(Math.abs(d)):Math.abs(d))}</div>`;
    return `<div class="kpi"><div class="lbl">${lbl}</div><div class="val">${fmt(m[k])}</div>${dd}</div>`;}).join('');}
function matrix(){let h='<thead><tr><th class="l">KPI</th>'+D.months.map((m,i)=>
  `<th class="${i===sel?'sel':''}">${m.label.split(' ')[0]}</th>`).join('')+'</tr></thead><tbody>';
  KPI.forEach(([k,lbl,fmt,gu])=>{h+=`<tr><td class="l mlab">${lbl}</td>`+D.months.map((m,i)=>{
    const d=m.mom?m.mom[k]:null;const dl=d==null||d===0?'':`<span class="delta ${cls(d,gu)}">${arrow(d)}</span>`;
    return `<td class="${i===sel?'sel':''}">${fmt(m[k])}${dl}</td>`;}).join('')+'</tr>';});
  document.getElementById('matrix').innerHTML=h+'</tbody>';}
function changes(){const m=D.months[sel];document.getElementById('changes').innerHTML=
  `<div class="chg"><div class="lbl" style="color:var(--up)">NEW THIS MONTH</div><div class="n">${m.n_new}</div><div>${usd(m.new_principal)} principal</div></div>
   <div class="chg"><div class="lbl" style="color:var(--down)">MATURING THIS MONTH</div><div class="n">${m.n_maturing}</div><div>${usd(m.maturing_principal)} principal</div></div>`;}
function rateBand(r){return r<0.09?'lo':(r<0.10?'mid':'hi');}
function table(){const m=D.months[sel];
  const fL=fLender.value,fS=fStatus.value,fR=fRate.value,sk=fSort.value;
  let rows=m.loans.filter(r=>(!fL||r.lender===fL)&&(!fS||r[fS])&&(!fR||rateBand(r.rate)===fR));
  rows.sort((a,b)=>sk==='repay'?a.repay.localeCompare(b.repay):(b[sk]-a[sk]));
  const COL=[['lender','Lender','l'],['ref','Ref','l'],['repay','Repays','l'],
    ['principal','Principal',''],['rate','Rate',''],['days_active','Days',''],
    ['available','Available',''],['accrued','Accrued','']];
  let h='<thead><tr>'+COL.map(c=>`<th class="${c[2]}">${c[1]}</th>`).join('')+'</tr></thead><tbody>';
  rows.forEach(r=>{const tag=r.new?'<span class="pill new">NEW</span> ':(r.maturing?'<span class="pill mat">MAT</span> ':'');
    h+=`<tr><td class="l">${tag}${r.lender}</td><td class="l">${r.ref||''}</td><td class="l">${r.repay}</td>
    <td>${usd(r.principal)}</td><td>${pct(r.rate)}</td><td>${r.days_active}</td>
    <td>${usd(r.available)}</td><td>${usd(r.accrued)}</td></tr>`;});
  document.getElementById('loans').innerHTML=h+'</tbody>';
  document.getElementById('tcount').textContent=rows.length+' loans · '+usd(rows.reduce((s,r)=>s+r.available,0))+' available';}
function lenders(){const set=[...new Set(D.months.flatMap(m=>m.loans.map(r=>r.lender)))].sort();
  fLender.innerHTML='<option value="">All</option>'+set.map(l=>`<option>${l}</option>`).join('');}
function pick(i){sel=i;render();}
function render(){tabs();kpis();matrix();changes();table();}
['fLender','fStatus','fRate','fSort'].forEach(id=>document.getElementById(id).onchange=table);
document.getElementById('foot').textContent=D.derived_note+'  ·  Source: '+D.source_file+'  ·  '+D.scope+'  ·  '+D.currency;
lenders();render();
</script>
</body></html>
"""


def main() -> int:
    data = loan_book.build()
    sub = f"{data['currency']} · {data['scope']} · reconstructed from {data['source_file']}"
    html = (TEMPLATE
            .replace("__SUB__", sub)
            .replace("__DATA__", json.dumps(data)))
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(Path.cwd())}  ({len(html):,} bytes, "
          f"{len(data['months'])} months)")
    return 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
