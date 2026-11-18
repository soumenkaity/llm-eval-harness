"""Command line.

    evalkit run      SUITE --name RUN [--label TEXT] [--no-judge]   record outputs, then score them
    evalkit score    SUITE RUN_DIR                                  (re)score saved outputs
    evalkit compare  RUN_A RUN_B [--fail-on-regression] [--margin M] paired A/B comparison, CI gate
    evalkit meta-eval SUITE --labels FILE --run RUN_DIR ...          measure how accurate the judge is
    evalkit report   RUN_DIR                                        rebuild report.html
"""

import argparse
import json
import sys
from pathlib import Path

from .suite import load_suite


def _judges(suite, cache_dir: Path, tracer):
    from .judges import Judges
    from .llm import JudgeLLM, ResponseCache

    return Judges(JudgeLLM(suite.judge, ResponseCache(cache_dir / "judge-cache.sqlite")), tracer)


def cmd_run(a) -> int:
    from .runner import record, score
    from .targets import HttpTarget
    from .tracing import make_provider

    suite = load_suite(a.suite)
    run_dir = Path(a.runs) / a.name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "traces.jsonl").unlink(missing_ok=True)
    provider = make_provider(run_dir / "traces.jsonl")
    tracer = provider.get_tracer("evalkit")
    print(f"Recording {suite.name} -> {run_dir}")
    record(suite, run_dir, HttpTarget(suite.target), tracer, label=a.label, limit=a.limit)
    if not a.no_judge:
        from .report import write_report

        print(f"Scoring with judge {suite.judge.provider}:{suite.judge.model}")
        score(suite, run_dir, _judges(suite, Path(a.runs), tracer), tracer)
        write_report(run_dir)
    provider.shutdown()
    return 0


def cmd_score(a) -> int:
    from .report import write_report
    from .runner import score
    from .tracing import make_provider

    suite = load_suite(a.suite)
    run_dir = Path(a.run_dir)
    provider = make_provider(run_dir / "traces.jsonl")
    tracer = provider.get_tracer("evalkit")
    judges = None if a.no_judge else _judges(suite, run_dir.parent, tracer)
    print(f"Scoring {run_dir} with judge {suite.judge.model if judges else '(none)'}")
    meta = score(suite, run_dir, judges, tracer)
    write_report(run_dir)
    provider.shutdown()
    for m, s in meta["summary"]["metrics"].items():
        print(f"  {m:13s} {s['passed']}/{s['n']} = {s['rate']:.0%}  95% CI [{s['ci'][0]:.0%}, {s['ci'][1]:.0%}]")
    return 0


def cmd_compare(a) -> int:
    from .compare import compare_runs, to_markdown

    result = compare_runs(Path(a.run_a), Path(a.run_b), gate_metrics=a.gate, margin=a.margin)
    md = to_markdown(result)
    print(md)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    if a.fail_on_regression and result["regressions"]:
        print(f"FAIL: gate failed on {', '.join(result['regressions'])}", file=sys.stderr)
        return 1
    return 0


def cmd_meta_eval(a) -> int:
    from .metaeval import build_items, run_meta_eval, to_markdown
    from .tracing import make_provider

    suite = load_suite(a.suite)
    items = build_items(suite, [Path(r) for r in a.run], Path(a.labels))
    if a.sample:
        from .metaeval import stratified_sample

        items = stratified_sample(items, a.sample)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    provider = make_provider(out / f"traces-{suite.judge.model.replace(':', '_')}.jsonl")
    tracer = provider.get_tracer("evalkit")
    judges = _judges(suite, Path(a.cache_dir), tracer)
    print(f"Meta-evaluating judge {suite.judge.model} on {len(items)} labelled items")
    result = run_meta_eval(items, judges)
    provider.shutdown()
    name = suite.judge.model.replace(":", "_")
    (out / f"{name}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md = to_markdown(result)
    (out / f"{name}.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def cmd_report(a) -> int:
    from .report import write_report

    print(write_report(Path(a.run_dir)))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="evalkit", description="Evaluate LLM applications.")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="call the target for every case, then score")
    r.add_argument("suite")
    r.add_argument("--name", required=True, help="run folder name, e.g. rag-7b-hybrid")
    r.add_argument("--label", default="", help="what is being tested, e.g. 'qwen2.5:7b, hybrid retrieval'")
    r.add_argument("--runs", default="runs")
    r.add_argument("--limit", type=int)
    r.add_argument("--no-judge", action="store_true", help="record outputs only; score later")
    r.set_defaults(fn=cmd_run)

    s = sub.add_parser("score", help="score (or re-score) saved outputs")
    s.add_argument("suite")
    s.add_argument("run_dir")
    s.add_argument("--no-judge", action="store_true", help="deterministic checks only")
    s.set_defaults(fn=cmd_score)

    c = sub.add_parser("compare", help="paired comparison of two scored runs")
    c.add_argument("run_a", help="baseline")
    c.add_argument("run_b", help="candidate")
    c.add_argument("--gate", nargs="+", default=["passed", "correctness", "faithfulness", "refusal"],
                   help="metrics that fail the gate when they regress significantly")
    c.add_argument("--fail-on-regression", action="store_true", help="exit 1 when the gate fails")
    c.add_argument("--margin", type=float, help="non-inferiority margin as a fraction (0.15 = 15 pp): also fail "
                   "when the 95%% CI cannot rule out a drop bigger than this")
    c.add_argument("--out", help="also write the markdown report here")
    c.set_defaults(fn=cmd_compare)

    m = sub.add_parser("meta-eval", help="measure judge accuracy on labelled answers")
    m.add_argument("suite")
    m.add_argument("--labels", required=True)
    m.add_argument("--run", action="append", required=True, help="run folder(s) providing the answers")
    m.add_argument("--out", default="meta-eval")
    m.add_argument("--cache-dir", default="runs")
    m.add_argument("--sample", type=int, help="judge a stratified sample of this many items (slow judges)")
    m.set_defaults(fn=cmd_meta_eval)

    rp = sub.add_parser("report", help="rebuild the HTML report of a run")
    rp.add_argument("run_dir")
    rp.set_defaults(fn=cmd_report)

    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy code page
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
