"""Build multipage static dashboard from progress.md (dark mission-control theme).

Pages (all written to dist/):
  index.html            home: hero, goal, ticker, batch cards
  batch-<slug>.html     one per batch: full table + scoped filter + pager
  activity.html         activity log + skipped + policy ledger
"""
import re, html, datetime, os

SRC = "/Users/manishtiwari/progress.md"
OUT_DIR = "/Users/manishtiwari/oss-progress-site/dist"
os.makedirs(OUT_DIR, exist_ok=True)

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
    elif 48 <= i <= 60:
        batch = "Batch D · Docs/Misc"
    elif 61 <= i <= 78:
        batch = "Batch E · 50-project expansion"
    else:
        batch = "Batch F · Small easy-merge"
    st = status.upper()
    if st.startswith("LOST"):
        cls = "lost"
    elif "PR MERGED" in st:
        cls = "merged"
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

# policy ledger rows (non-numeric first cell)
ledger = []
m = re.search(r'## Policy ledger.*?\n(.*?)(?=\n## |\Z)', text, re.S)
if m:
    for line in m.group(1).splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip().strip("|").split("|")]
        if not cells or cells[0] in ("Repo", "#") or set(cells[0]) <= set("-: "):
            continue
        if len(cells) >= 3 and not cells[0][0].isdigit():
            ledger.append((cells[0], cells[1], cells[2]))

n_open = sum(1 for r in rows if r["cls"] == "open")
n_merged = sum(1 for r in rows if r["cls"] == "merged")
n_claimed = sum(1 for r in rows if r["cls"] == "claimed")
n_backlog = sum(1 for r in rows if r["cls"] == "backlog")
n_lost = sum(1 for r in rows if r["cls"] == "lost")
GOAL = 50

updated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def esc(s):
    return html.escape(s, quote=True)

BATCHES = [
    ("Original 10", "original-10", "Start",
     "Where the hunt started: cognee connectors, the mem0 queue, ollama docs."),
    ("Batch A · AI/ML", "ai-ml", "AI/ML",
     "Heavyweights: pytorch, mlflow, scikit-learn, tensorflow, transformers, langchain."),
    ("Batch B · Web/Dev", "web-dev", "Web/Dev",
     "Web and runtimes: svelte, vercel/ai, gradio, node, deno, vue, angular."),
    ("Batch C · Python/Infra", "python-infra", "Python/Infra",
     "Python and infra: pandas, pytest, numpy, prometheus, grafana, kubernetes."),
    ("Batch D · Docs/Misc", "docs-misc", "Docs/Misc",
     "Docs and misc: streamlit, ollama extras, openai-python, rust, go, docker docs."),
    ("Batch E · 50-project expansion", "expansion", "Expansion",
     "18 new repos to reach 50 projects: vite, eslint, expo, otel, cilium, nats."),
    ("Batch F · Small easy-merge", "easy-merge", "Easy-merge",
     "10 small repos under 5k stars, picked for merge speed, not prestige."),
]

def batch_stats(b):
    items = [r for r in rows if r["batch"] == b]
    c = {"open": 0, "claimed": 0, "backlog": 0, "lost": 0, "merged": 0}
    for r in items:
        c[r["cls"]] += 1
    return items, c

def stackbar(c, total):
    return "".join(
        f'<span class="seg {k}" style="width:{(v / total * 100):.1f}%"></span>'
        for k, v in c.items() if v
    ) if total else ""

def row_html(r):
    links = f'<a href="{esc(r["issue_url"])}">#{esc(r["num"])} ↗</a>'
    if r["claim"]:
        links += f' <a class="dim" href="{esc(r["claim"]["url"])}">claim ↗</a>'
    if r["pr"]:
        links += f' <a class="hot" href="{esc(r["pr"]["url"])}">PR ↗</a>'
    return (
        f'<tr data-status="{r["cls"]}" data-type="{esc(r["type"].lower())}">'
        f'<td class="num">{r["n"]:02d}</td>'
        f'<td class="repo">{esc(r["repo"])}</td>'
        f'<td class="issue">{esc(r["issue"])}</td>'
        f'<td><span class="tag">{esc(r["type"])}</span></td>'
        f'<td><span class="dot {r["cls"]}"></span><span class="st">{esc(r["status"])}</span></td>'
        f'<td class="links">{links}</td>'
        f'<td class="next">{esc(r["next"])}</td></tr>'
    )

# ticker: newest claims first
ticker_items = [r for r in rows if r["claim"] or r["pr"]]
ticker_items.sort(key=lambda r: -r["n"])
ticker = "".join(
    f'<span class="titem"><b>{esc(r["repo"])}</b> #{esc(r["num"])} · {esc(r["status"].split(",")[0].split("—")[0].strip())}</span><span class="tsep">/</span>'
    for r in ticker_items[:14]
)

funnel = [
    ("Merged", n_merged, "merged"),
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

nav_links = (
    '<a href="index.html">Overview</a>'
    + "".join(f'<a href="batch-{slug}.html">{esc(short)}</a>' for _, slug, short, _ in BATCHES)
    + '<a href="activity.html">Activity</a>'
)

CSS = """<style>
:root{
  --bg:#0a0c10; --panel:#10141b; --panel2:#0d1117; --line:rgba(255,255,255,.09);
  --ink:#e9edf3; --muted:#98a1b1; --faint:#5d6675;
  --acc:#cdf138; --acc-ink:#141802;
  --open:#cdf138; --claimed:#7cc4ff; --backlog:#8b93a3; --lost:#ff7a72; --merged:#3ddc84;
  --r:16px; --ease:cubic-bezier(.32,.72,0,1);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15.5px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:radial-gradient(rgba(255,255,255,.055) 1px,transparent 1px);
  background-size:26px 26px;
  mask-image:radial-gradient(ellipse 90% 60% at 50% 0%,black 30%,transparent 75%);}
.wrap{max-width:1180px;margin:0 auto;padding:0 26px 90px;position:relative;z-index:1}
.mono{font-family:"JetBrains Mono",ui-monospace,monospace}
/* top nav */
.topnav{position:sticky;top:0;z-index:50;background:rgba(10,12,16,.88);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border-bottom:1px solid var(--line)}
.topnav .inner{max-width:1180px;margin:0 auto;padding:0 26px;display:flex;gap:4px;align-items:center;
  overflow-x:auto;white-space:nowrap}
.topnav a{color:var(--muted);text-decoration:none;font-size:13px;font-weight:600;
  padding:15px 13px;border-bottom:2px solid transparent;transition:color .25s var(--ease)}
.topnav a:hover{color:var(--ink)}
.topnav a.brand{color:var(--acc);font-family:"JetBrains Mono",monospace;font-size:12.5px;
  letter-spacing:.08em;margin-right:10px}
.topnav a.on{color:var(--ink);border-bottom-color:var(--acc)}
/* hero */
.hero{display:grid;grid-template-columns:1.2fr .95fr;gap:34px;padding:76px 0 34px;align-items:stretch}
.eyebrow{display:inline-block;font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--acc);border:1px solid rgba(205,241,56,.35);
  border-radius:999px;padding:5px 14px;margin:0 0 22px}
h1{font-family:"Sora",sans-serif;font-weight:800;font-size:54px;line-height:1.05;
  letter-spacing:-.02em;margin:0 0 16px}
h1 .thin{color:var(--muted);font-weight:600}
.sub{color:var(--muted);font-size:15.5px;max-width:46ch;margin:0 0 26px}
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
.btn:hover .arr{transform:translate(2px,-2px)}
.btn-ghost .arr{background:rgba(255,255,255,.08)}
.meta{margin:22px 0 0;font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--faint)}
/* goal shell */
.shell{background:rgba(255,255,255,.04);border:1px solid var(--line);
  border-radius:26px;padding:10px}
.core{background:var(--panel);border:1px solid var(--line);
  border-radius:18px;padding:28px 26px;height:100%}
.core h3{font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--muted);margin:0 0 6px;font-weight:500}
.bignum{font-family:"JetBrains Mono",monospace;font-size:64px;font-weight:700;
  line-height:1;color:var(--ink);font-variant-numeric:tabular-nums}
.bignum small{font-size:20px;color:var(--faint)}
.goalbar{height:10px;border-radius:999px;background:rgba(255,255,255,.08);margin:18px 0 8px;overflow:hidden}
.goalbar span{display:block;height:100%;width:0;border-radius:999px;background:var(--acc);
  transition:width 1.2s var(--ease)}
.goalcap{font-size:12.5px;color:var(--muted);margin:0 0 20px}
.frow{display:grid;grid-template-columns:86px 1fr 34px;gap:10px;align-items:center;margin:10px 0}
.flabel{font-family:"JetBrains Mono",monospace;font-size:11.5px;color:var(--muted)}
.fbar{height:8px;border-radius:999px;background:rgba(255,255,255,.07);overflow:hidden}
.fbar .fill{display:block;height:100%;width:0;border-radius:999px;transition:width 1.1s var(--ease)}
.fill.open{background:var(--open)} .fill.merged{background:var(--merged)} .fill.claimed{background:var(--claimed)}
.fill.backlog{background:var(--backlog)} .fill.lost{background:var(--lost)}
.fval{font-family:"JetBrains Mono",monospace;font-size:13px;text-align:right;font-variant-numeric:tabular-nums}
/* ticker */
.ticker{border-top:1px solid var(--line);border-bottom:1px solid var(--line);
  overflow:hidden;white-space:nowrap;padding:12px 0;margin:8px 0 0;
  font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--muted)}
.ticker .titem b{color:var(--ink);font-weight:500}
.tsep{color:var(--acc);margin:0 14px}
/* batch cards */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px;margin-top:52px}
.card{display:block;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);
  padding:26px 24px;text-decoration:none;color:var(--ink);
  transition:transform .35s var(--ease),border-color .35s var(--ease)}
.card:hover{transform:translateY(-4px);border-color:rgba(205,241,56,.45)}
.card h2{font-family:"Sora",sans-serif;font-size:19px;margin:0 0 6px;letter-spacing:-.01em}
.card p.desc{color:var(--muted);font-size:13.5px;margin:0 0 16px;min-height:44px}
.card .bmeta{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--faint);margin:12px 0 0}
.card .go{color:var(--acc);font-weight:700;font-size:13.5px;margin-top:14px;display:inline-block}
.stackbar{display:flex;height:8px;width:100%;border-radius:999px;overflow:hidden;
  background:rgba(255,255,255,.07)}
.seg{display:block;height:100%}
.seg.open{background:var(--open)} .seg.merged{background:var(--merged)} .seg.claimed{background:var(--claimed)}
.seg.backlog{background:var(--backlog)} .seg.lost{background:var(--lost)}
.secttl{font-family:"Sora",sans-serif;font-size:24px;margin:52px 0 4px;letter-spacing:-.01em}
.secsub{color:var(--faint);font-size:13.5px;margin:0}
/* page head (batch pages) */
.pagehead{padding:64px 0 10px}
.pagehead h1{font-size:44px}
.crumb{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--faint);margin:0 0 14px}
.crumb a{color:var(--acc);text-decoration:none}
/* sticky controls */
.controls{position:sticky;top:52px;z-index:20;display:flex;flex-wrap:wrap;gap:10px;align-items:center;
  background:rgba(10,12,16,.85);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin:26px 0 8px}
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
.result{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--faint);margin:12px 2px 0}
/* tables — aired out */
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--r);background:var(--panel2);
  margin-top:18px}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:900px}
thead th{background:#141922;font-family:"JetBrains Mono",monospace;
  font-size:10.5px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);
  text-align:left;padding:13px 16px;border-bottom:1px solid var(--line);font-weight:500}
tbody td{padding:15px 16px;border-bottom:1px solid rgba(255,255,255,.05);vertical-align:top}
tbody tr{transition:background .25s var(--ease)}
tbody tr:hover{background:rgba(255,255,255,.035)}
tbody tr:last-child td{border-bottom:none}
tr.hidden{display:none}
td.num{font-family:"JetBrains Mono",monospace;color:var(--faint);font-size:12.5px;white-space:nowrap}
td.repo{white-space:nowrap;font-weight:600;font-size:13.5px}
td.issue{max-width:360px}
td.links{white-space:nowrap;font-family:"JetBrains Mono",monospace;font-size:12px}
td.links a{color:var(--acc);text-decoration:none;margin-right:9px}
td.links a.dim{color:var(--muted)}
td.links a.hot{color:var(--claimed)}
td.links a:hover{text-decoration:underline}
td.next{color:var(--muted);font-size:13px;max-width:320px}
.tag{display:inline-block;border:1px solid var(--line);border-radius:6px;padding:2px 10px;
  font-size:11.5px;color:var(--muted);font-family:"JetBrains Mono",monospace;white-space:nowrap}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;vertical-align:1px}
.dot.open{background:var(--open)} .dot.merged{background:var(--merged)} .dot.claimed{background:var(--claimed)}
.dot.backlog{background:var(--backlog)} .dot.lost{background:var(--lost)}
.st{font-size:13px;color:var(--muted)}
/* pager */
.pager{display:flex;justify-content:space-between;gap:12px;margin:40px 0 0;flex-wrap:wrap}
.pager a{flex:1 1 220px;border:1px solid var(--line);border-radius:12px;padding:16px 20px;
  text-decoration:none;color:var(--ink);background:var(--panel);transition:border-color .3s var(--ease)}
.pager a:hover{border-color:var(--acc)}
.pager span.dir{display:block;font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--faint);
  text-transform:uppercase;letter-spacing:.12em;margin-bottom:4px}
.pager span.nm{font-weight:700;font-size:14.5px}
/* panels */
.cols{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:34px}
.panel{border:1px solid var(--line);border-radius:18px;padding:28px;background:var(--panel)}
.panel.full{grid-column:1/-1}
.panel h2{font-family:"Sora",sans-serif;font-size:18px;margin:0 0 16px}
.panel ul{margin:0;padding-left:19px;font-size:13.5px;color:var(--muted)}
.panel li{margin-bottom:10px}
.panel li::marker{color:var(--acc)}
.pol{display:grid;grid-template-columns:220px 130px 1fr;gap:0;border:1px solid var(--line);
  border-radius:12px;overflow:hidden;margin-top:6px;font-size:13px}
.pol div{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.05)}
.pol .ph{background:#141922;font-family:"JetBrains Mono",monospace;font-size:10.5px;
  text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}
.pol .pr{font-weight:600;white-space:nowrap}
.pol .pp-GREEN{color:var(--merged)} .pol .pp-RED{color:var(--lost)} .pol .pp-YELLOW{color:var(--claimed)}
.pol .pp-YELLOW-strict{color:var(--claimed)} .pol .pp-GREEN-strict{color:var(--merged)}
.pol .pp-GREEN-behavioral{color:var(--merged)} .pol .pp-RED-friction{color:var(--lost)}
footer{margin-top:48px;padding-top:22px;border-top:1px solid var(--line);
  color:var(--faint);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
  font-family:"JetBrains Mono",monospace;font-size:11.5px}
/* reveal */
.reveal{opacity:0;transform:translateY(22px);transition:opacity .8s var(--ease),transform .8s var(--ease)}
.reveal.in{opacity:1;transform:none}
@keyframes tick{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.ticktrack{display:inline-block;animation:tick 60s linear infinite}
@media(max-width:900px){
  .hero{grid-template-columns:1fr;padding-top:48px}
  h1{font-size:36px}
  .pagehead h1{font-size:30px}
  .bignum{font-size:52px}
  .cols{grid-template-columns:1fr}
  .pol{grid-template-columns:1fr}
  .pol .ph{display:none}
}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  *,*::before,*::after{animation:none!important;transition:none!important}
  .reveal{opacity:1;transform:none}
  .ticktrack{animation:none}
}
</style>"""

JS_FILTER = """<script>
(function(){
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
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
  var gf = document.getElementById('goalfill');
  if (gf) requestAnimationFrame(function(){ gf.style.width = gf.getAttribute('data-w') + '%'; });
  document.querySelectorAll('.fbar .fill').forEach(function(f){
    f.style.width = f.style.getPropertyValue('--w');
  });
  if (!reduce && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){ if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, {threshold: 0.08});
    document.querySelectorAll('.reveal').forEach(function(el){ io.observe(el); });
  } else {
    document.querySelectorAll('.reveal').forEach(function(el){ el.classList.add('in'); });
  }
  var q = document.getElementById('q'), res = document.getElementById('result'), cur = 'all';
  if (q) {
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
  }
})();
</script>"""

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ — OSS Contribution Hunt</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
""" + CSS + """
</head>
<body>
<nav class="topnav"><div class="inner">__NAV__</div></nav>
<div class="wrap">
"""

FOOT = """
<footer><span>generated from progress.md · __UPDATED__</span><span>links point to github issues · claims · prs</span></footer>
</div>
""" + JS_FILTER + """
</body>
</html>"""

def nav_on(current):
    out = '<a class="brand" href="index.html">OSS-HUNT</a><a href="index.html"' + (' class="on"' if current == "index" else '') + '>Overview</a>'
    for _, slug, short, _ in BATCHES:
        out += f'<a href="batch-{slug}.html"' + (' class="on"' if current == slug else '') + f'>{esc(short)}</a>'
    out += '<a href="activity.html"' + (' class="on"' if current == "activity" else '') + '>Activity</a>'
    return out

def page(title, current, body):
    h = HEAD.replace("__TITLE__", esc(title)).replace("__NAV__", nav_on(current))
    return h + body + FOOT.replace("__UPDATED__", esc(updated))

# ---------- index ----------
cards = []
for b, slug, short, desc in BATCHES:
    items, c = batch_stats(b)
    total = len(items)
    active = c["open"] + c["claimed"] + c["merged"]
    cards.append(
        f'<a class="card reveal" href="batch-{slug}.html"><h2>{esc(b)}</h2>'
        f'<p class="desc">{esc(desc)}</p>'
        f'<div class="stackbar">{stackbar(c, total)}</div>'
        f'<p class="bmeta">{total} issues · {active} active · {c["backlog"]} queued</p>'
        f'<span class="go">Open board →</span></a>'
    )

active_total = n_open + n_claimed + n_merged
index_body = f"""
<header class="hero">
  <div>
    <p class="eyebrow">manish-9245 · contribution hunt · live board</p>
    <h1>Sixty projects.<br><span class="thin">Eighty-eight shots on goal.</span></h1>
    <p class="sub">Tracking every claimed, open and queued issue across 60 open-source repos, big and small easy-merge. Pick a board to drill in.</p>
    <div class="ctas">
      <a class="btn btn-solid" href="batch-easy-merge.html">Hottest board <span class="arr">→</span></a>
      <a class="btn btn-ghost" href="activity.html">Activity log <span class="arr">→</span></a>
    </div>
    <p class="meta">updated {esc(updated)} · rule: code only after assignment where the repo assigns · max 5 claims/day</p>
  </div>
  <div class="shell">
    <div class="core">
      <h3>Pipeline to goal</h3>
      <div class="bignum"><span data-count="{active_total}">0</span><small> / {GOAL} projects active</small></div>
      <div class="goalbar"><span id="goalfill" data-w="{active_total / GOAL * 100:.1f}" style="width:0%"></span></div>
      <p class="goalcap">Goal: {GOAL} distinct projects with assigned / merged work. {n_claimed} claimed, {n_backlog} queued.</p>
      {funnel_html}
    </div>
  </div>
</header>
<div class="ticker" aria-hidden="true"><span class="ticktrack">{ticker} {ticker}</span></div>
<h2 class="secttl">Boards</h2>
<p class="secsub">Seven boards, one per hunt phase. Each has its own filter and full table.</p>
<div class="cards">{"".join(cards)}</div>
"""
open(os.path.join(OUT_DIR, "index.html"), "w").write(page("Overview", "index", index_body))

# ---------- batch pages ----------
for idx, (b, slug, short, desc) in enumerate(BATCHES):
    items, c = batch_stats(b)
    total = len(items)
    trs = "".join(row_html(r) for r in items)
    prev_link, next_link = "", ""
    if idx > 0:
        pb, pslug, _, _ = BATCHES[idx - 1]
        prev_link = f'<a href="batch-{pslug}.html"><span class="dir">← Previous</span><span class="nm">{esc(pb)}</span></a>'
    else:
        prev_link = '<a href="index.html"><span class="dir">← Up</span><span class="nm">Overview</span></a>'
    if idx < len(BATCHES) - 1:
        nb, nslug, _, _ = BATCHES[idx + 1]
        next_link = f'<a href="batch-{nslug}.html"><span class="dir">Next →</span><span class="nm">{esc(nb)}</span></a>'
    else:
        next_link = '<a href="activity.html"><span class="dir">Next →</span><span class="nm">Activity log</span></a>'
    body = f"""
<div class="pagehead">
  <p class="crumb"><a href="index.html">overview</a> / {esc(short.lower())}</p>
  <h1>{esc(b)}</h1>
  <p class="sub">{esc(desc)}</p>
  <p class="bmeta mono" style="color:var(--faint);font-size:12.5px">{total} issues · {c["open"] + c["claimed"] + c["merged"]} active · {c["backlog"]} queued · {c["lost"]} lost</p>
  <div class="stackbar" style="margin-top:14px">{stackbar(c, total)}</div>
</div>
<div class="controls">
  <input id="q" type="search" placeholder="Filter this board — try docs, #7645…" aria-label="Filter issues">
  <div class="fgroup" id="statusF">
    <button class="f" data-f="all" aria-pressed="true">All {total}</button>
    <button class="f" data-f="open" aria-pressed="false">PR open</button>
    <button class="f" data-f="merged" aria-pressed="false">Merged</button>
    <button class="f" data-f="backlog" aria-pressed="false">Backlog</button>
    <button class="f" data-f="lost" aria-pressed="false">Lost</button>
  </div>
</div>
<p class="result" id="result"></p>
<div class="tablewrap"><table><thead><tr><th>#</th><th>Repo</th><th>Issue</th><th>Type</th><th>Status</th><th>Links</th><th>Next action</th></tr></thead>
<tbody>{trs}</tbody></table></div>
<div class="pager">{prev_link}{next_link}</div>
"""
    open(os.path.join(OUT_DIR, f"batch-{slug}.html"), "w").write(page(b, slug, body))

# ---------- activity ----------
log_html = "".join(f"<li>{esc(x)}</li>" for x in log_items)
skip_html = "".join(f"<li>{esc(x)}</li>" for x in skip_items)
pol_rows = "".join(
    f'<div class="pr">{esc(r)}</div><div class="pp-{esc(p.replace(" ", "-"))}">{esc(p)}</div><div>{esc(e)}</div>'
    for r, p, e in ledger
)
activity_body = f"""
<div class="pagehead">
  <p class="crumb"><a href="index.html">overview</a> / activity</p>
  <h1>Activity &amp; policy</h1>
  <p class="sub">Every hunt event, every skipped repo, and the AI-policy classification for all 60 repos.</p>
</div>
<div class="cols">
  <div class="panel reveal"><h2>Activity log</h2><ul>{log_html}</ul></div>
  <div class="panel reveal"><h2>Skipped — verified unmergeable</h2><ul>{skip_html}</ul></div>
  <div class="panel full reveal"><h2>Policy ledger — RED / YELLOW / GREEN</h2>
    <p class="secsub" style="margin-bottom:14px">GREEN: disclosed AI allowed. YELLOW: no written policy. RED: drop.</p>
    <div class="pol"><div class="ph">Repo</div><div class="ph">Policy</div><div class="ph">Evidence</div>{pol_rows}</div>
  </div>
</div>
"""
open(os.path.join(OUT_DIR, "activity.html"), "w").write(page("Activity", "activity", activity_body))

print(f"wrote {OUT_DIR}: index + {len(BATCHES)} batches + activity; {len(rows)} rows, open={n_open} merged={n_merged} backlog={n_backlog} lost={n_lost}, ledger={len(ledger)}")
