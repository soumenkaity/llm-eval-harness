"""Run a suite in two phases, each traced:

1. record: call the target system once per case and save its outputs (outputs.jsonl).
2. score:  run the deterministic checks and the LLM judges on the saved outputs (results.jsonl).

Keeping them separate means a run can be re-scored with a different judge, or a fixed judge prompt,
without calling the target again. It also keeps one model loaded at a time on a small GPU.
"""

import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from opentelemetry.trace import Tracer

from .judges import PROMPT_VERSIONS, JudgeResult, Judges
from .metrics import contains_facts, refusal_correct
from .stats import bootstrap_ci, percentile
from .suite import Case, Suite
from .targets import Output

METRICS = ("passed", "refusal", "facts", "correctness", "faithfulness")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def record(suite: Suite, run_dir: Path, target: Callable[[Case], Output], tracer: Tracer,
           label: str = "", limit: int | None = None, log=print) -> list[dict]:
    run_dir.mkdir(parents=True, exist_ok=True)
    cases = suite.cases[:limit] if limit else suite.cases
    rows = []
    with tracer.start_as_current_span("evalkit.record") as root:
        root.set_attributes({"evalkit.suite": suite.name, "evalkit.cases": len(cases)})
        for case in cases:
            with tracer.start_as_current_span("target.call") as span:
                out = target(case)
                span.set_attributes({"evalkit.case_id": case.id, "http.url": suite.target.url,
                                     "evalkit.answered": out.answered, "evalkit.latency_ms": out.latency_ms})
                if out.error:
                    span.set_attribute("error.type", out.error.split(":")[0])
            rows.append({"id": case.id, "output": out.to_dict()})
            log(f"  {case.id} {out.latency_ms:>7} ms  {'ERROR ' + out.error if out.error else out.answer[:90]!r}")
    write_jsonl(run_dir / "outputs.jsonl", rows)
    meta = {"name": run_dir.name, "label": label, "suite": suite.name, "target_url": suite.target.url,
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cases": len(rows)}
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return rows


def score_case(case: Case, out: Output, judges: Judges | None) -> dict:
    checks = {"refusal": refusal_correct(out.answered, case.answerable),
              "facts": contains_facts(out.answer, case.must_include) and out.answered
              if case.answerable and case.must_include else None}
    verdicts: dict[str, JudgeResult | None] = {"correctness": None, "faithfulness": None}
    if judges:
        if case.answerable and case.reference:
            verdicts["correctness"] = (
                judges.correctness(case.input, out.answer, case.reference, case.id) if out.answered
                else JudgeResult(False, 0.0, {"note": "refused an answerable question"}))
        if out.answered and out.contexts:
            verdicts["faithfulness"] = judges.faithfulness(case.input, out.answer, out.contexts, case.id)

    # Overall pass: refuse what you should, and when answering, be correct and grounded.
    parts = [checks["refusal"]]
    if case.answerable and out.answered:
        correct = verdicts["correctness"].passed if verdicts["correctness"] else checks["facts"]
        parts += [correct, verdicts["faithfulness"].passed if verdicts["faithfulness"] else True]
    passed = None if None in parts else all(parts)
    return {
        "id": case.id, "input": case.input, "answerable": case.answerable, "tags": case.tags,
        "reference": case.reference, "output": out.to_dict(), "checks": checks,
        "judges": {k: v.to_dict() if v else None for k, v in verdicts.items()}, "passed": passed,
    }


def score(suite: Suite, run_dir: Path, judges: Judges | None, tracer: Tracer, log=print) -> dict:
    outputs = {r["id"]: Output(**r["output"]) for r in read_jsonl(run_dir / "outputs.jsonl")}
    cases = [c for c in suite.cases if c.id in outputs]
    results = []
    start = time.perf_counter()
    with tracer.start_as_current_span("evalkit.score") as root:
        root.set_attributes({"evalkit.suite": suite.name, "evalkit.cases": len(cases),
                             "evalkit.judge_model": judges.llm.config.model if judges else "none"})
        for case in cases:
            with tracer.start_as_current_span("case") as span:
                span.set_attribute("evalkit.case_id", case.id)
                r = score_case(case, outputs[case.id], judges)
                span.set_attribute("evalkit.passed", str(r["passed"]))
            results.append(r)
            j = r["judges"]
            log(f"  {case.id} pass={r['passed']!s:5} facts={r['checks']['facts']!s:5} "
                f"correct={_p(j['correctness'])} faithful={_p(j['faithfulness'])}")
    write_jsonl(run_dir / "results.jsonl", results)
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    meta["judge"] = ({**{k: v for k, v in asdict(judges.llm.config).items() if k != "api_key"},
                      "prompt_versions": PROMPT_VERSIONS} if judges else None)
    meta["scored_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta["scoring_seconds"] = round(time.perf_counter() - start, 1)
    meta["summary"] = summarize(results)
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def _p(j: dict | None) -> str:
    return "-" if j is None else ("ERR" if j["passed"] is None else str(j["passed"]))


def metric_values(r: dict, metric: str) -> bool | None:
    """The pass/fail value of one metric for one case, or None if it doesn't apply (or the judge failed)."""
    if metric == "passed":
        return r["passed"]
    if metric in r["checks"]:
        return r["checks"][metric]
    j = r["judges"].get(metric)
    return j["passed"] if j else None


def summarize(results: list[dict]) -> dict:
    metrics = {}
    for m in METRICS:
        vals = [metric_values(r, m) for r in results]
        applicable = [v for v in vals if v is not None]
        errors = sum(1 for r in results if (r["judges"].get(m) or {}).get("error"))
        if not applicable:
            continue
        lo, hi = bootstrap_ci([float(v) for v in applicable])
        metrics[m] = {"n": len(applicable), "passed": sum(applicable), "rate": sum(applicable) / len(applicable),
                      "ci": [lo, hi], "judge_errors": errors}
    lat = [r["output"]["latency_ms"] for r in results]
    # Judge calls actually made (a refused answerable question is failed without asking the judge)
    judged = [j for r in results for j in r["judges"].values()
              if j and ("claims" in j["details"] or "facts" in j["details"])]
    return {
        "cases": len(results),
        "metrics": metrics,
        "latency_ms": {"p50": percentile(lat, 0.5), "p95": percentile(lat, 0.95)},
        "target_errors": sum(1 for r in results if r["output"]["error"]),
        "judge_calls": len(judged),
        "judge_cache_hits": sum(1 for j in judged if j["cached"]),
    }
