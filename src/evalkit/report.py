"""Self-contained HTML report for one scored run: metrics with confidence intervals, a per-case
timeline built from the OpenTelemetry spans, and every judge's reasoning."""

import json
from collections import defaultdict
from html import escape
from pathlib import Path

from .runner import read_jsonl
from .tracing import read_traces

CSS = """
:root{--bg:#fbfbfa;--fg:#1d1d1b;--muted:#6b6b66;--card:#fff;--line:#e4e3de;--good:#1f7a4d;--bad:#b42318;
--t:#3e63dd;--j1:#c2770c;--j2:#7c4dbd;--chip:#f1f0ec}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--muted:#a3a29b;--card:#1f1f1d;--line:#34332f;
--good:#4cc38a;--bad:#ff7b72;--t:#7b9bff;--j1:#f0a43c;--j2:#b392f0;--chip:#2a2a27}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 8px}
.muted{color:var(--muted)}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-top:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.card b{display:block;font-size:24px}.card small{color:var(--muted)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}th{font-size:12px;color:var(--muted)}
.ok{color:var(--good);font-weight:600}.no{color:var(--bad);font-weight:600}.na{color:var(--muted)}
details summary{cursor:pointer;color:var(--muted)}ul{margin:4px 0;padding-left:18px}
.bar{display:flex;height:12px;min-width:2px;border-radius:3px;overflow:hidden}.bar span{display:block;height:100%}
.legend span{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 12px}
.wrap{overflow-x:auto}label{user-select:none}
"""


def _mark(v) -> str:
    if v is None:
        return '<span class="na">–</span>'
    return '<span class="ok">pass</span>' if v else '<span class="no">fail</span>'


def _judge_html(name: str, j: dict | None) -> str:
    if not j:
        return ""
    d = j.get("details") or {}
    if j.get("error"):
        return f"<p><b>{name}</b>: judge error: {escape(j['error'])}</p>"
    if "note" in d:
        return f"<p><b>{name}</b>: {escape(d['note'])}</p>"
    items = []
    for c in d.get("claims", []):
        items.append(f"<li>{_mark(c.get('supported'))} {escape(c.get('claim', ''))}"
                     f"<br><span class='muted'>evidence: {escape(c.get('evidence') or '(none)')}</span></li>")
    for f in d.get("facts", []):
        st = f.get("status")
        cls = "ok" if st == "stated" else "no" if st == "contradicted" or f.get("essential") else "na"
        items.append(f"<li><span class='{cls}'>{st}</span> {escape(f.get('fact', ''))}"
                     f"{'' if f.get('essential') else ' <span class=muted>(not essential)</span>'}"
                     f"<br><span class='muted'>answer says: {escape(f.get('answer_says', ''))}</span></li>")
    return f"<p><b>{name}</b></p><ul>{''.join(items)}</ul>"


def write_report(run_dir: Path) -> Path:
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    results = read_jsonl(run_dir / "results.jsonl")
    summary = meta.get("summary", {})

    # Per-case span durations from the trace file (latest span per case and name wins).
    spans = defaultdict(dict)
    for s in read_traces(run_dir / "traces.jsonl"):
        cid = s["attributes"].get("evalkit.case_id")
        if cid and s["name"] in ("target.call", "judge.correctness", "judge.faithfulness"):
            spans[cid][s["name"]] = (s["end_ns"] - s["start_ns"]) / 1e9
    longest = max((sum(v.values()) for v in spans.values()), default=1) or 1

    cards = []
    names = {"passed": "Overall pass", "refusal": "Refusal correct", "facts": "Exact facts",
             "correctness": "Correct (judge)", "faithfulness": "Faithful (judge)"}
    for m, s in summary.get("metrics", {}).items():
        cards.append(f"<div class='card'><small>{names.get(m, m)}</small><b>{s['rate']:.0%}</b>"
                     f"<small>{s['passed']}/{s['n']} · 95% CI {s['ci'][0]:.0%}–{s['ci'][1]:.0%}</small></div>")
    lat = summary.get("latency_ms", {})
    if lat:
        cards.append(f"<div class='card'><small>Target latency p50 / p95</small><b>{lat['p50'] / 1000:.1f} s</b>"
                     f"<small>p95 {lat['p95'] / 1000:.1f} s</small></div>")

    rows = []
    for r in results:
        o, j = r["output"], r["judges"]
        sp = spans.get(r["id"], {})
        bar = "".join(f"<span style='width:{100 * sp.get(k, 0) / longest:.1f}%;background:var({c})' "
                      f"title='{k} {sp.get(k, 0):.1f}s'></span>"
                      for k, c in (("target.call", "--t"), ("judge.correctness", "--j1"), ("judge.faithfulness", "--j2")))
        reasoning = _judge_html("Correctness", j.get("correctness")) + _judge_html("Faithfulness", j.get("faithfulness"))
        ctx = "".join(f"<li>{escape(c)}</li>" for c in o.get("contexts", []))
        rows.append(
            f"<tr data-pass='{r['passed']}'><td>{r['id']}</td><td>{escape(r['input'])}"
            f"<details><summary>answer &amp; reasoning</summary><p>{escape(o['answer'] or o.get('error') or '')}</p>"
            f"{'<p><b>Reference</b>: ' + escape(r['reference']) + '</p>' if r.get('reference') else ''}"
            f"{reasoning}<details><summary>retrieved context</summary><ol>{ctx}</ol></details></details></td>"
            f"<td>{_mark(r['checks']['refusal'])}</td><td>{_mark(r['checks']['facts'])}</td>"
            f"<td>{_mark((j.get('correctness') or {}).get('passed') if j.get('correctness') else None)}</td>"
            f"<td>{_mark((j.get('faithfulness') or {}).get('passed') if j.get('faithfulness') else None)}</td>"
            f"<td>{_mark(r['passed'])}</td><td style='width:160px'><div class='bar'>{bar}</div>"
            f"<small class='muted'>{sum(sp.values()):.0f} s</small></td></tr>")

    judge = meta.get("judge") or {}
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Eval: {escape(meta['name'])}</title>
<style>{CSS}</style></head><body><main>
<h1>{escape(meta['name'])}</h1>
<div class="muted">{escape(meta.get('label', ''))}<br>Suite <b>{escape(meta['suite'])}</b> · {summary.get('cases', len(results))} cases ·
judge <b>{escape(judge.get('provider', 'none'))}:{escape(judge.get('model', '-'))}</b> · recorded {meta.get('recorded_at', '')} ·
scored {meta.get('scored_at', '')} · judge calls {summary.get('judge_calls', 0)} ({summary.get('judge_cache_hits', 0)} from cache)</div>
<div class="cards">{''.join(cards)}</div>
<h2>Cases</h2>
<p class="legend muted">Time per case from the trace:<span style="background:var(--t)"></span>target
<span style="background:var(--j1)"></span>correctness judge<span style="background:var(--j2)"></span>faithfulness judge
&nbsp; · &nbsp;<label><input type="checkbox" id="fails"> failures only</label></p>
<div class="wrap"><table><thead><tr><th>ID</th><th>Question</th><th>Refusal</th><th>Facts</th><th>Correct</th>
<th>Faithful</th><th>Overall</th><th>Time</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
</main><script>
document.getElementById('fails').addEventListener('change',e=>{{for(const tr of document.querySelectorAll('tbody tr'))
tr.style.display=e.target.checked&&tr.dataset.pass==='True'?'none':''}});
</script></body></html>"""
    path = run_dir / "report.html"
    path.write_text(html, encoding="utf-8")
    return path
