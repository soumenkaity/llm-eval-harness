"""A/B comparison of two scored runs on the same suite: is B really better or worse than A?

For each metric we pair the cases (same question in both runs) and report:
- the change in pass rate, with a paired bootstrap 95% confidence interval,
- an exact McNemar test (p-value) on the cases where A and B disagree,
- a verdict: a regression or improvement only when p < alpha; otherwise "no significant change".

`evalkit compare --fail-on-regression` exits 1 when a gated metric fails, so it can block a merge in CI.
There are two gate rules:

- default: fail on a *significant* regression (McNemar p < alpha). With few cases this is lenient:
  a real 10-point drop is often "not significant", so it passes.
- `--margin 0.15` (non-inferiority): fail unless the data rules out a drop bigger than the margin,
  i.e. the lower end of the 95% CI of B - A must be above -margin. The candidate has to prove it is
  not much worse, which is the safer default for a release gate.
"""

import json
from pathlib import Path

from .runner import METRICS, metric_values, read_jsonl
from .stats import mcnemar_exact, paired_bootstrap, percentile


def load_run(run_dir: Path) -> tuple[dict, dict[str, dict]]:
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    results = {r["id"]: r for r in read_jsonl(run_dir / "results.jsonl")}
    return meta, results


def compare_runs(a_dir: Path, b_dir: Path, gate_metrics=("passed",), alpha: float = 0.05,
                 margin: float | None = None) -> dict:
    meta_a, res_a = load_run(a_dir)
    meta_b, res_b = load_run(b_dir)
    ids = [i for i in res_a if i in res_b]
    warnings = []
    if meta_a.get("suite") != meta_b.get("suite"):
        warnings.append("The runs come from different suites.")
    if len(ids) < max(len(res_a), len(res_b)):
        warnings.append(f"Only {len(ids)} cases appear in both runs; the others are ignored.")
    judge = lambda m: (m.get("judge") or {}).get("model")  # noqa: E731
    if judge(meta_a) != judge(meta_b):
        warnings.append(f"The runs were scored by different judges ({judge(meta_a)} vs {judge(meta_b)}), "
                        "so judge metrics are not comparable. Re-score one of them.")

    rows = []
    for m in METRICS:
        pairs = [(metric_values(res_a[i], m), metric_values(res_b[i], m)) for i in ids]
        pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
        if not pairs:
            continue
        a = [x for x, _ in pairs]
        b = [y for _, y in pairs]
        mc = mcnemar_exact(a, b)
        boot = paired_bootstrap([float(x) for x in a], [float(y) for y in b])
        rate_a, rate_b = sum(a) / len(a), sum(b) / len(b)
        if mc["p_value"] < alpha and rate_b < rate_a:
            verdict = "regression"
        elif mc["p_value"] < alpha and rate_b > rate_a:
            verdict = "improvement"
        else:
            verdict = "no significant change"
        if margin is not None and verdict != "regression" and boot["ci"][0] < -margin:
            verdict = "not shown non-inferior"
        rows.append({"metric": m, "n": len(pairs), "a": rate_a, "b": rate_b, "diff": boot["diff"],
                     "ci": list(boot["ci"]), "a_only": mc["a_only"], "b_only": mc["b_only"],
                     "p_value": mc["p_value"], "verdict": verdict})

    lat_a = [res_a[i]["output"]["latency_ms"] for i in ids]
    lat_b = [res_b[i]["output"]["latency_ms"] for i in ids]
    flips = [{"id": i, "input": res_a[i]["input"], "a": res_a[i]["passed"], "b": res_b[i]["passed"],
              "a_answer": res_a[i]["output"]["answer"], "b_answer": res_b[i]["output"]["answer"]}
             for i in ids if res_a[i]["passed"] is not None and res_b[i]["passed"] is not None
             and res_a[i]["passed"] != res_b[i]["passed"]]
    return {
        "a": {"name": meta_a["name"], "label": meta_a.get("label", "")},
        "b": {"name": meta_b["name"], "label": meta_b.get("label", "")},
        "cases": len(ids), "alpha": alpha, "margin": margin, "rows": rows, "warnings": warnings, "flips": flips,
        "latency_p50_ms": {"a": percentile(lat_a, 0.5), "b": percentile(lat_b, 0.5)},
        "regressions": [r["metric"] for r in rows if r["verdict"] in ("regression", "not shown non-inferior")
                        and r["metric"] in gate_metrics],
    }


def to_markdown(c: dict) -> str:
    pct = lambda x: f"{100 * x:.0f}%"  # noqa: E731
    pp = lambda x: f"{100 * x:+.0f} pp"  # noqa: E731
    out = [f"# A/B comparison: `{c['a']['name']}` (A) vs `{c['b']['name']}` (B)", ""]
    out += [f"- **A**: {c['a']['label'] or c['a']['name']}", f"- **B**: {c['b']['label'] or c['b']['name']}",
            f"- {c['cases']} paired cases; significance level {c['alpha']}"
            + (f"; non-inferiority margin {100 * c['margin']:.0f} pp" if c.get("margin") is not None else ""), ""]
    for w in c["warnings"]:
        out.append(f"> **Warning:** {w}\n")
    out += ["| Metric | n | A | B | B − A (95% CI) | only A passed | only B passed | McNemar p | Verdict |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in c["rows"]:
        verdict = {"regression": "**regression**", "improvement": "**improvement**",
                   "not shown non-inferior": "**not shown non-inferior**"}.get(r["verdict"], r["verdict"])
        out.append(f"| {r['metric']} | {r['n']} | {pct(r['a'])} | {pct(r['b'])} | {pp(r['diff'])} "
                   f"[{pp(r['ci'][0])}, {pp(r['ci'][1])}] | {r['a_only']} | {r['b_only']} | {r['p_value']:.3f} | {verdict} |")
    lat = c["latency_p50_ms"]
    out += ["", f"Median latency: A {lat['a'] / 1000:.1f} s, B {lat['b'] / 1000:.1f} s.", ""]
    if c["flips"]:
        out += ["## Cases that changed (overall pass)", "", "| Case | Question | A | B |", "|---|---|---|---|"]
        for f in c["flips"]:
            out.append(f"| {f['id']} | {f['input']} | {'pass' if f['a'] else 'fail'} | {'pass' if f['b'] else 'fail'} |")
        out.append("")
    if c["regressions"]:
        out.append(f"**Gate: FAIL** on {', '.join(c['regressions'])}.")
    elif c.get("margin") is not None:
        out.append(f"**Gate: PASS**: every gated metric is shown to be within {100 * c['margin']:.0f} pp of A.")
    else:
        out.append("**Gate: PASS**: no significant regression in the gated metrics.")
    return "\n".join(out) + "\n"
