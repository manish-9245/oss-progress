"""Build single-file static site from progress.md."""
import re, json, html, datetime

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
    # batch
    i = int(n)
    if i <= 10:
        batch = "Original 10"
    elif 11 <= i <= 22:
        batch = "Batch A — AI/ML"
    elif 23 <= i <= 33:
        batch = "Batch B — Web/Dev"
    elif 34 <= i <= 47:
        batch = "Batch C — Python/Infra"
    else:
        batch = "Batch D — Docs/Misc"
    # status class
    st = status.upper()
    if st.startswith("LOST"):
        cls = "lost"
    elif "PR OPEN" in st:
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

def count(cls=None, substr=None):
    out = 0
    for r in rows:
        if cls and r["cls"] != cls:
            continue
        if substr and substr not in r["status"]:
            continue
        out += 1
    return out

stats = {
    "targets": len(rows),
    "pr_open": sum(1 for r in rows if "PR OPEN" in r["status"]) + 1,  # +1: ollama PR counted via PR cell? verify
    "claimed": count("claimed"),
    "backlog": count("backlog"),
    "lost": count("lost"),
}
# Correct pr_open: rows with PR link that looks like /pull/
stats["pr_open"] = sum(1 for r in rows if r["pr"] and "/pull/" in r["pr"]["url"])
stats["merged"] = 0

# log + skipped sections
def section(name):
    m = re.search(r'## ' + re.escape(name) + r'\n(.*?)(?=\n## |\Z)', text, re.S)
    return m.group(1).strip() if m else ""

log_sec = section("Log")
skip_sec = section("Deliberately skipped")
log_items = [l.strip()[2:].strip() for l in log_sec.splitlines() if l.strip().startswith("- ")]
skip_items = [l.strip()[2:].strip() for l in skip_sec.splitlines() if l.strip().startswith("- ")]

updated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
data_json = json.dumps(rows)

def esc(s):
    return html.escape(s, quote=True)

# Build static table HTML server-side so site works with JS disabled; JS only filters.
batches = ["Original 10", "Batch A — AI/ML", "Batch B — Web/Dev", "Batch C — Python/Infra", "Batch D — Docs/Misc"]
tables_html = []
for b in batches:
    items = [r for r in rows if r["batch"] == b]
    trs = []
    for r in items:
        links = f'<a href="{esc(r["issue_url"])}">issue</a>'
        if r["claim"]:
            links += f' · <a href="{esc(r["claim"]["url"])}">claim</a>'
        if r["pr"]:
            links += f' · <a href="{esc(r["pr"]["url"])}">PR</a>'
        trs.append(
            f'<tr data-status="{r["cls"]}" data-type="{esc(r["type"].lower())}" data-batch="{esc(b)}">'
            f'<td class="num">{r["n"]}</td>'
            f'<td class="repo">{esc(r["repo"])}</td>'
            f'<td class="issue">{esc(r["issue"])}</td>'
            f'<td><span class="tag">{esc(r["type"])}</span></td>'
            f'<td><span class="pill {r["cls"]}">{esc(r["status"])}</span></td>'
            f'<td class="links">{links}</td>'
            f'<td class="next">{esc(r["next"])}</td></tr>'
        )
    tables_html.append(f'<section class="batch" data-batch-section="{esc(b)}"><h2>{esc(b)}</h2>'
                       f'<div class="tablewrap"><table><thead><tr><th>#</th><th>Repo</th><th>Issue</th><th>Type</th><th>Status</th><th>Links</th><th>Next action</th></tr></thead>'
                       f'<tbody>{"".join(trs)}</tbody></table></div></section>')

page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OSS Contribution Hunt — Progress</title>
<style>
:root{--ink:#1a1f26;--muted:#5b6472;--line:#e2e6eb;--bg:#ffffff;--panel:#f4f6f8;--accent:#0e6b5e;--amber:#8a5a00;--red:#b42318;--blue:#175cd3;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;}
.wrap{max-width:1120px;margin:0 auto;padding:32px 20px 64px}
header.top{border:1px solid var(--line);border-radius:12px;padding:28px;background:var(--panel);}
.overline{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 8px}
h1{font-family:Georgia,"Times New Roman",serif;font-size:34px;line-height:1.2;margin:0 0 8px;font-weight:700}
.sub{color:var(--muted);margin:0 0 4px}
.rule{font-size:13px;color:var(--muted);margin:8px 0 0}
.stats{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:18px 0 6px}
.stat{border:1px solid var(--line);border-radius:10px;padding:12px 14px;background:#fff}
.stat .v{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}
.stat .k{font-size:12px;color:var(--muted)}
.controls{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}
.controls input[type=search]{flex:1 1 220px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;font-size:14px}
.fgroup{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
button.f{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 12px;font-size:13px;cursor:pointer}
button.f[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}
.result{font-size:13px;color:var(--muted);margin:4px 0 0}
.batch{margin-top:28px}
.batch h2{font-size:19px;margin:0 0 10px;padding-top:8px;border-top:2px solid var(--ink)}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:860px;background:#fff}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
thead th{background:var(--panel);font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
tr.hidden{display:none}
td.num{font-variant-numeric:tabular-nums;color:var(--muted);white-space:nowrap}
td.repo{white-space:nowrap;font-weight:600}
td.links{white-space:nowrap}
td.next{color:var(--muted)}
a{color:var(--blue);text-decoration:none}
a:hover{text-decoration:underline}
.tag{display:inline-block;border:1px solid var(--line);border-radius:6px;padding:1px 8px;font-size:12px;background:#fff}
.pill{display:inline-block;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600;white-space:nowrap}
.pill.open{background:#e0f2ec;color:#0b5c52}
.pill.claimed{background:#e8effd;color:#174a94}
.pill.backlog{background:#f2f0e6;color:var(--amber)}
.pill.lost{background:#fbe9e7;color:var(--red)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:28px}
.panel{border:1px solid var(--line);border-radius:10px;padding:18px;background:#fff}
.panel h2{font-size:17px;margin:0 0 10px}
.panel ul{margin:0;padding-left:20px;font-size:13.5px;color:#333}
.panel li{margin-bottom:8px}
footer{margin-top:32px;color:var(--muted);font-size:13px}
@media(max-width:800px){.stats{grid-template-columns:repeat(3,1fr)}.cols{grid-template-columns:1fr}h1{font-size:27px}}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
<p class="overline">manish-9245 · Open source contribution hunt</p>
<h1>Goal: 10 issues assigned / merged on popular repos</h1>
<p class="sub">Started 2026-10-13/14 (UTC) · Updated __UPDATED__ · Source: progress.md (60 targets)</p>
<p class="rule">Rule: code only after assignment where the repo assigns; mem0 / ollama-docs / flask-docs move claim &rarr; PR directly.</p>
<div class="stats">
<div class="stat"><div class="v">__TARGETS__</div><div class="k">targets tracked</div></div>
<div class="stat"><div class="v">__PROPEN__</div><div class="k">PRs open</div></div>
<div class="stat"><div class="v">__CLAIMED__</div><div class="k">claimed</div></div>
<div class="stat"><div class="v">__BACKLOG__</div><div class="k">backlog</div></div>
<div class="stat"><div class="v">__LOST__</div><div class="k">lost</div></div>
<div class="stat"><div class="v">0</div><div class="k">merged</div></div>
</div>
</header>
<div class="controls">
<input id="q" type="search" placeholder="Filter by repo, issue, text… (#7546, grafana, docs)" aria-label="Filter issues">
<div class="fgroup" id="statusF">
<button class="f" data-f="all" aria-pressed="true">All</button>
<button class="f" data-f="open" aria-pressed="false">PR open</button>
<button class="f" data-f="claimed" aria-pressed="false">Claimed</button>
<button class="f" data-f="backlog" aria-pressed="false">Backlog</button>
<button class="f" data-f="lost" aria-pressed="false">Lost</button>
</div>
</div>
<p class="result" id="result"></p>
__TABLES__
<div class="cols">
<div class="panel"><h2>Activity log</h2><ul>__LOG__</ul></div>
<div class="panel"><h2>Deliberately skipped</h2><ul>__SKIP__</ul></div>
</div>
<footer>Static page generated from progress.md · __UPDATED__ · Links point to GitHub issues, claim comments and PRs.</footer>
</div>
<script>
var q=document.getElementById('q'),res=document.getElementById('result'),cur='all';
var rows=Array.prototype.slice.call(document.querySelectorAll('tbody tr'));
function apply(){
  var term=(q.value||'').toLowerCase(),shown=0;
  rows.forEach(function(tr){
    var okS=(cur==='all'||tr.getAttribute('data-status')===cur);
    var okT=!term||tr.textContent.toLowerCase().indexOf(term)>-1;
    var show=okS&&okT;tr.classList.toggle('hidden',!show);if(show)shown++;
  });
  document.querySelectorAll('[data-batch-section]').forEach(function(sec){
    var any=Array.prototype.some.call(sec.querySelectorAll('tbody tr'),function(tr){return !tr.classList.contains('hidden')});
    sec.style.display=any?'':'none';
  });
  res.textContent=shown+' of '+rows.length+' shown';
}
q.addEventListener('input',apply);
document.getElementById('statusF').addEventListener('click',function(e){
  var b=e.target.closest('button.f');if(!b)return;cur=b.getAttribute('data-f');
  this.querySelectorAll('button.f').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});
  apply();
});
apply();
</script>
</body>
</html>
"""

page = page.replace("__UPDATED__", esc(updated))
page = page.replace("__TARGETS__", str(stats["targets"]))
page = page.replace("__PROPEN__", str(stats["pr_open"]))
page = page.replace("__CLAIMED__", str(stats["claimed"]))
page = page.replace("__BACKLOG__", str(stats["backlog"]))
page = page.replace("__LOST__", str(stats["lost"]))
page = page.replace("__TABLES__", "\n".join(tables_html))
page = page.replace("__LOG__", "".join(f"<li>{esc(x)}</li>" for x in log_items))
page = page.replace("__SKIP__", "".join(f"<li>{esc(x)}</li>" for x in skip_items))

open(OUT, "w").write(page)
print(f"wrote {OUT} with {len(rows)} rows, pr_open={stats['pr_open']}, claimed={stats['claimed']}, backlog={stats['backlog']}, lost={stats['lost']}")
