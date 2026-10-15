"""Build single-file static dashboard from progress.md (dark mission-control theme)."""
import re, html, datetime

SRC = "/Users/manishtiwari/progress.md"
OUT = "/Users/manishtiwari/oss-progress-site/index.html"

text = open(SRC).read()

def md_link(cell):
    m = re.search(r'\[([^\]]*)\]\((https?://[^)]+)\)', cell)
    if m:
        return {"label": m.group(1), "url": m.group(2)}
    return None

def issue_num(issue_cell):
    m = re.search(r'#(\d+)', issue_cell)
    return m.group(1) if m else ""

rows = []
for line in text.splitlines():
    s = line.strip()
    if not s.startswith("|"):
        continue
    cells = [c.strip() for c in s.strip().strip("|").split("|")]
    if not cells or cells[0] == "#" or not cells[0].isdigit():
        continue
    if len(cells) == 8:
        n, repo, issue, typ, status, claim_c, pr_c, nxt = cells
    elif len(cells) == 7:
        n, repo, issue, typ, status, claim_c, nxt = cells
        pr_c = "—"
    else:
        continue
    num = issue_num(issue)
    issue_url = f"https://github.com/{repo}/issues/{num}" if num else ""
    claim = md_link(claim_c)
    pr = md_link(pr_c)
    i = int(n)
    if i <= 10:
        batch = "Original 10"
    elif 11 <= i <= 22:
        batch = "Batch A · AI/ML"
    elif 23 <= i <= 33:
        batch = "Batch B · Web/Dev"
    elif 34 <= i <= 47:
        batch = "Batch C · Python/Infra"
    else:
        batch = "Batch D · Docs/Misc"
    st = status.upper()
    if st.startswith("LOST"):
        cls = "lost"
    elif "PR OPEN" in st or "PR DRAFT" in st:
        cls = "open"
    elif st.startswith("CLAIMED"):
        cls = "claimed"
    else:
        cls = "backlog"
    rows.append({
        "n": i, "repo": repo, "issue": issue, "type": typ,
        "status": status, "cls": cls, "claim": claim, "pr": pr,
        "next": nxt, "batch": batch,
        "issue_url": issue_url, "num": num,
    })

rows.sort(key=lambda r: r["n"])

def section(name):
    m = re.search(r'## ' + re.escape(name) + r'\n(.*?)(?=\n## |\Z)', text, re.S)
    return m.group(1).strip() if m else ""

log_sec = section("Log")
skip_sec = section("Deliberately skipped")
log_items = [l.strip()[2:].strip() for l in log_sec.splitlines() if l.strip().startswith("- ")]
skip_items = [l.strip()[2:].strip() for l in skip_sec.splitlines() if l.strip().startswith("- ")]

n_open = sum(1 for r in rows if r["cls"] == "open")
n_claimed = sum(1 for r in rows if r["cls"] == "claimed")
n_backlog = sum(1 for r in rows if r["cls"] == "backlog")
n_lost = sum(1 for r in rows if r["cls"] == "lost")
GOAL = 10

updated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def esc(s):
    return html.escape(s, quote=True)

batches = ["Original 10", "Batch A · AI/ML", "Batch B · Web/Dev",
           "Batch C · Python/Infra", "Batch D · Docs/Misc"]

batch_sections = []
for b in batches:
    items = [r for r in rows if r["batch"] == b]
    c = {"open": 0, "claimed": 0, "backlog": 0, "lost": 0}
    for r in items:
        c[r["cls"]] += 1
    total = len(items)
    segs = "".join(
        f'<span class="seg {k}" style="width:{(v / total * 100):.1f}%"></span>'
        for k, v in c.items() if v
    )
    trs = []
    for r in items:
        links = f'<a href="{esc(r["issue_url"])}">#{esc(r["num"])} ↗</a>'
        if r["claim"]:
            links += f' <a class="dim" href="{esc(r["claim"]["url"])}">claim ↗</a>'
        if r["pr"]:
            links += f' <a class="hot" href="{esc(r["pr"]["url"])}">PR ↗</a>'
        trs.append(
            f'<tr data-status="{r["cls"]}" data-type="{esc(r["type"].lower())}">'
            f'<td class="num">{r["n"]:02d}</td>'
            f'<td class="repo">{esc(r["repo"])}</td>'
            f'<td class="issue">{esc(r["issue"])}</td>'
            f'<td><span class="tag">{esc(r["type"])}</span></td>'
            f'<td><span class="dot {r["cls"]}"></span><span class="st">{esc(r["status"])}</span></td>'
            f'<td class="links">{links}</td>'
            f'<td class="next">{esc(r["next"])}</td></tr>'
        )
    batch_sections.append(
        f'<section class="batch reveal" id="batch-{esc(str(batches.index(b)))}">'
        f'<div class="batchhead"><div><h2>{esc(b)}</h2>'
        f'<p class="bmeta">{total} issues · {c["open"] + c["claimed"]} active · {c["backlog"]} queued</p></div>'
        f'<div class="stackbar">{segs}</div></div>'
        f'<div class="tablewrap"><table><thead><tr><th>#</th><th>Repo</th><th>Issue</th><th>Type</th><th>Status</th><th>Links</th><th>Next action</th></tr></thead>'
        f'<tbody>{"".join(trs)}</tbody></table></div></section>'
    )

# ticker: newest claims first
ticker_items = [r for r in rows if r["claim"] or r["pr"]]
ticker_items.sort(key=lambda r: -r["n"])
ticker = "".join(
    f'<span class="titem"><b>{esc(r["repo"])}</b> #{esc(r["num"])} · {esc(r["status"].split(",")[0].split("—")[0].strip())}</span><span class="tsep">/</span>'
    for r in ticker_items[:14]
)

funnel = [
    ("PRs open", n_open, "open"),
    ("Claimed", n_claimed, "claimed"),
    ("Backlog", n_backlog, "backlog"),
    ("Lost", n_lost, "lost"),
]
maxv = max(v for _, v, _ in funnel) or 1
funnel_html = "".join(
    f'<div class="frow"><span class="flabel">{label}</span>'
    f'<span class="fbar"><span class="fill {cls}" style="--w:{(v / maxv * 100):.1f}%"></span></span>'
    f'<span class="fval" data-count="{v}">0</span></div>'
    for label, v, cls in funnel
)

page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OSS Contribution Hunt — Progress</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0a0c10; --panel:#10141b; --panel2:#0d1117; --line:rgba(255,255,255,.09);
  --ink:#e9edf3; --muted:#98a1b1; --faint:#5d6675;
  --acc:#cdf138; --acc-ink:#141802;
  --open:#cdf138; --claimed:#7cc4ff; --backlog:#8b93a3; --lost:#ff7a72;
  --r:14px; --ease:cubic-bezier(.32,.72,0,1);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:radial-gradient(rgba(255,255,255,.055) 1px,transparent 1px);
  background-size:26px 26px;
  mask-image:radial-gradient(ellipse 90% 60% at 50% 0%,black 30%,transparent 75%);}
.wrap{max-width:1180px;margin:0 auto;padding:0 22px 80px;position:relative;z-index:1}
.mono{font-family:"JetBrains Mono",ui-monospace,monospace}
.disp{font-family:"Sora",-apple-system,sans-serif}
/* hero */
.hero{display:grid;grid-template-columns:1.25fr .9fr;gap:28px;padding:88px 0 30px;align-items:stretch}
.eyebrow{display:inline-block;font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--acc);border:1px solid rgba(205,241,56,.35);
  border-radius:999px;padding:5px 14px;margin:0 0 20px}
h1{font-family:"Sora",sans-serif;font-weight:800;font-size:52px;line-height:1.04;
  letter-spacing:-.02em;margin:0 0 14px}
h1 .thin{color:var(--muted);font-weight:600}
.sub{color:var(--muted);font-size:15px;max-width:46ch;margin:0 0 24px}
.ctas{display:flex;gap:12px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:10px;border-radius:999px;
  padding:12px 22px;font-weight:700;font-size:14px;text-decoration:none;
  transition:transform .35s var(--ease),background .35s var(--ease),color .35s var(--ease);white-space:nowrap}
.btn:active{transform:scale(.97)}
.btn-solid{background:var(--acc);color:var(--acc-ink)}
.btn-solid:hover{transform:translateY(-2px)}
.btn-ghost{border:1px solid var(--line);color:var(--ink)}
.btn-ghost:hover{border-color:var(--acc);color:var(--acc)}
.btn .arr{display:inline-flex;width:26px;height:26px;border-radius:50%;
  background:rgba(0,0,0,.14);align-items:center;justify-content:center;font-size:14px;
  transition:transform .35s var(--ease)}
.btn-solid .arr{background:rgba(0,0,0,.16)}
.btn:hover .arr{transform:translate(2px,-2px)}
.btn-ghost .arr{background:rgba(255,255,255,.08)}
.meta{margin:22px 0 0;font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--faint)}
/* goal shell (double-bezel) */
.shell{background:rgba(255,255,255,.04);border:1px solid var(--line);
  border-radius:26px;padding:10px}
.core{background:var(--panel);border:1px solid var(--line);
  border-radius:18px;padding:26px 24px;height:100%}
.core h3{font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--muted);margin:0 0 6px;font-weight:500}
.bignum{font-family:"JetBrains Mono",monospace;font-size:64px;font-weight:700;
  line-height:1;color:var(--ink);font-variant-numeric:tabular-nums}
.bignum small{font-size:20px;color:var(--faint)}
.goalbar{height:10px;border-radius:999px;background:rgba(255,255,255,.08);margin:18px 0 8px;overflow:hidden}
.goalbar span{display:block;height:100%;width:0;border-radius:999px;background:var(--acc);
  transition:width 1.2s var(--ease)}
.goalcap{font-size:12.5px;color:var(--muted);margin:0 0 20px}
.frow{display:grid;grid-template-columns:86px 1fr 34px;gap:10px;align-items:center;margin:9px 0}
.flabel{font-family:"JetBrains Mono",monospace;font-size:11.5px;color:var(--muted)}
.fbar{height:8px;border-radius:999px;background:rgba(255,255,255,.07);overflow:hidden}
.fbar .fill{display:block;height:100%;width:0;border-radius:999px;transition:width 1.1s var(--ease)}
.fill.open{background:var(--open)} .fill.claimed{background:var(--claimed)}
.fill.backlog{background:var(--backlog)} .fill.lost{background:var(--lost)}
.fval{font-family:"JetBrains Mono",monospace;font-size:13px;text-align:right;font-variant-numeric:tabular-nums}
/* ticker */
.ticker{border-top:1px solid var(--line);border-bottom:1px solid var(--line);
  overflow:hidden;white-space:nowrap;padding:11px 0;margin:6px 0 0;
  font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--muted)}
.ticker .titem b{color:var(--ink);font-weight:500}
.tsep{color:var(--acc);margin:0 14px}
/* sticky controls */
.controls{position:sticky;top:12px;z-index:20;display:flex;flex-wrap:wrap;gap:10px;align-items:center;
  background:rgba(10,12,16,.82);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin:26px 0 6px}
.controls input[type=search]{flex:1 1 200px;background:var(--panel);border:1px solid var(--line);
  border-radius:9px;padding:9px 13px;font-size:13.5px;color:var(--ink);font-family:inherit}
.controls input[type=search]::placeholder{color:var(--faint)}
.controls input[type=search]:focus{outline:none;border-color:var(--acc)}
.fgroup{display:flex;gap:6px;flex-wrap:wrap}
button.f{border:1px solid var(--line);background:transparent;color:var(--muted);border-radius:999px;
  padding:7px 15px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;
  transition:all .3s var(--ease)}
button.f:hover{color:var(--ink);border-color:var(--muted)}
button.f[aria-pressed=true]{background:var(--acc);border-color:var(--acc);color:var(--acc-ink)}
.result{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--faint);margin:10px 2px 0}
/* batches */
.batch{margin-top:44px}
.batchhead{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:14px;flex-wrap:wrap}
.batch h2{font-family:"Sora",sans-serif;font-size:23px;margin:0;letter-spacing:-.01em}
.bmeta{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--faint);margin:5px 0 0}
.stackbar{display:flex;height:8px;width:min(320px,100%);border-radius:999px;overflow:hidden;
  background:rgba(255,255,255,.07)}
.seg{display:block;height:100%}
.seg.open{background:var(--open)} .seg.claimed{background:var(--claimed)}
.seg.backlog{background:var(--backlog)} .seg.lost{background:var(--lost)}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--r);background:var(--panel2)}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:880px}
thead th{position:sticky;top:0;background:#141922;font-family:"JetBrains Mono",monospace;
  font-size:10.5px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);
  text-align:left;padding:11px 12px;border-bottom:1px solid var(--line);font-weight:500}
tbody td{padding:11px 12px;border-bottom:1px solid rgba(255,255,255,.05);vertical-align:top}
tbody tr{transition:background .25s var(--ease)}
tbody tr:hover{background:rgba(255,255,255,.035)}
tbody tr:last-child td{border-bottom:none}
tr.hidden{display:none}
td.num{font-family:"JetBrains Mono",monospace;color:var(--faint);font-size:12.5px;white-space:nowrap}
td.repo{white-space:nowrap;font-weight:600;font-size:13px}
td.issue{max-width:340px}
td.links{white-space:nowrap;font-family:"JetBrains Mono",monospace;font-size:12px}
td.links a{color:var(--acc);text-decoration:none;margin-right:9px}
td.links a.dim{color:var(--muted)}
td.links a.hot{color:var(--claimed)}
td.links a:hover{text-decoration:underline}
td.next{color:var(--muted);font-size:12.5px;max-width:300px}
.tag{display:inline-block;border:1px solid var(--line);border-radius:6px;padding:1px 9px;
  font-size:11.5px;color:var(--muted);font-family:"JetBrains Mono",monospace;white-space:nowrap}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;vertical-align:1px}
.dot.open{background:var(--open)} .dot.claimed{background:var(--claimed)}
.dot.backlog{background:var(--backlog)} .dot.lost{background:var(--lost)}
.st{font-size:12.5px;color:var(--muted)}
/* bottom panels */
.cols{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:48px}
.panel{border:1px solid var(--line);border-radius:18px;padding:24px;background:var(--panel)}
.panel h2{font-family:"Sora",sans-serif;font-size:17px;margin:0 0 14px}
.panel ul{margin:0;padding-left:19px;font-size:13px;color:var(--muted)}
.panel li{margin-bottom:9px}
.panel li::marker{color:var(--acc)}
footer{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);
  color:var(--faint);font-size:12.5px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
  font-family:"JetBrains Mono",monospace;font-size:11.5px}
/* reveal */
.reveal{opacity:0;transform:translateY(22px);transition:opacity .8s var(--ease),transform .8s var(--ease)}
.reveal.in{opacity:1;transform:none}
/* ticker motion */
@keyframes tick{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.ticktrack{display:inline-block;animation:tick 60s linear infinite}
/* responsive */
@media(max-width:900px){
  .hero{grid-template-columns:1fr;padding-top:56px}
  h1{font-size:36px}
  .bignum{font-size:52px}
  .cols{grid-template-columns:1fr}
  .batchhead{flex-direction:column;align-items:flex-start}
  .stackbar{width:100%}
}
/* reduced motion */
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  *,*::before,*::after{animation:none!important;transition:none!important}
  .reveal{opacity:1;transform:none}
  .ticktrack{animation:none}
}
</style>
</head>
<body>
<div class="wrap">

  <header class="hero">
    <div>
      <p class="eyebrow">manish-9245 · contribution hunt · live board</p>
      <h1>Ten merges.<br><span class="thin">Sixty shots on goal.</span></h1>
      <p class="sub">Tracking every claimed, open and queued issue across 30+ major open-source repos — one board, updated from progress.md.</p>
      <div class="ctas">
        <a class="btn btn-solid" href="#board">Browse the board <span class="arr">↓</span></a>
        <a class="btn btn-ghost" href="https://github.com/manish-9245/oss-progress">Source on GitHub <span class="arr">↗</span></a>
      </div>
      <p class="meta">updated __UPDATED__ · rule: code only after assignment where the repo assigns</p>
    </div>
    <div class="shell">
      <div class="core">
        <h3>Pipeline to goal</h3>
        <div class="bignum"><span data-count="__PROPEN__">0</span><small> / __GOAL__ PRs open</small></div>
        <div class="goalbar"><span id="goalfill" style="width:0%"></span></div>
        <p class="goalcap">Goal: __GOAL__ issues assigned / merged. __CLAIMED__ claimed and being worked, __BACKLOG__ queued.</p>
        __FUNNEL__
      </div>
    </div>
  </header>

  <div class="ticker" aria-hidden="true"><span class="ticktrack">__TICKER__ __TICKER__</span></div>

  <div id="board" class="controls">
    <input id="q" type="search" placeholder="Filter — try grafana, docs, #7546…" aria-label="Filter issues">
    <div class="fgroup" id="statusF">
      <button class="f" data-f="all" aria-pressed="true">All 60</button>
      <button class="f" data-f="open" aria-pressed="false">PR open</button>
      <button class="f" data-f="claimed" aria-pressed="false">Claimed</button>
      <button class="f" data-f="backlog" aria-pressed="false">Backlog</button>
      <button class="f" data-f="lost" aria-pressed="false">Lost</button>
    </div>
  </div>
  <p class="result" id="result"></p>

  __TABLES__

  <div class="cols">
    <div class="panel reveal"><h2>Activity log</h2><ul>__LOG__</ul></div>
    <div class="panel reveal"><h2>Skipped — verified unmergeable</h2><ul>__SKIP__</ul></div>
  </div>

  <footer><span>generated from progress.md · __UPDATED__</span><span>links point to github issues · claims · prs</span></footer>
</div>
<script>
(function(){
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // count-up
  document.querySelectorAll('[data-count]').forEach(function(el){
    var target = parseInt(el.getAttribute('data-count'), 10) || 0;
    if (reduce) { el.textContent = target; return; }
    var t0 = null, dur = 1100;
    function step(ts){
      if (!t0) t0 = ts;
      var p = Math.min((ts - t0) / dur, 1);
      el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
  // goal + funnel widths
  requestAnimationFrame(function(){
    document.getElementById('goalfill').style.width = (__PROPEN__ / __GOAL__ * 100) + '%';
    document.querySelectorAll('.fbar .fill').forEach(function(f){
      f.style.width = f.style.getPropertyValue('--w');
    });
  });
  // reveal on scroll
  if (!reduce && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){ if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, {threshold: 0.08});
    document.querySelectorAll('.reveal').forEach(function(el){ io.observe(el); });
  } else {
    document.querySelectorAll('.reveal').forEach(function(el){ el.classList.add('in'); });
  }
  // filters
  var q = document.getElementById('q'), res = document.getElementById('result'), cur = 'all';
  var rows = Array.prototype.slice.call(document.querySelectorAll('tbody tr'));
  function apply(){
    var term = (q.value || '').toLowerCase(), shown = 0;
    rows.forEach(function(tr){
      var okS = (cur === 'all' || tr.getAttribute('data-status') === cur);
      var okT = !term || tr.textContent.toLowerCase().indexOf(term) > -1;
      var show = okS && okT;
      tr.classList.toggle('hidden', !show);
      if (show) shown++;
    });
    document.querySelectorAll('.batch').forEach(function(sec){
      var any = Array.prototype.some.call(sec.querySelectorAll('tbody tr'), function(tr){
        return !tr.classList.contains('hidden');
      });
      sec.style.display = any ? '' : 'none';
    });
    res.textContent = shown + ' of ' + rows.length + ' shown';
  }
  q.addEventListener('input', apply);
  document.getElementById('statusF').addEventListener('click', function(e){
    var b = e.target.closest('button.f'); if (!b) return;
    cur = b.getAttribute('data-f');
    this.querySelectorAll('button.f').forEach(function(x){ x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
    apply();
  });
  apply();
})();
</script>
</body>
</html>
"""

page = page.replace("__UPDATED__", esc(updated))
page = page.replace("__PROPEN__", str(n_open))
page = page.replace("__GOAL__", str(GOAL))
page = page.replace("__CLAIMED__", str(n_claimed))
page = page.replace("__BACKLOG__", str(n_backlog))
page = page.replace("__FUNNEL__", funnel_html)
page = page.replace("__TICKER__", ticker)
page = page.replace("__TABLES__", "\n".join(batch_sections))
page = page.replace("__LOG__", "".join(f"<li>{esc(x)}</li>" for x in log_items))
page = page.replace("__SKIP__", "".join(f"<li>{esc(x)}</li>" for x in skip_items))

open(OUT, "w").write(page)
print(f"wrote {OUT}: {len(rows)} rows, open={n_open} claimed={n_claimed} backlog={n_backlog} lost={n_lost}")
