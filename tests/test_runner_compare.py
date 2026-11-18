import json

from opentelemetry.sdk.trace import TracerProvider

from evalkit.cli import main
from evalkit.compare import compare_runs
from evalkit.judges import JudgeResult
from evalkit.report import write_report
from evalkit.runner import score_case, summarize, write_jsonl
from evalkit.suite import Case
from evalkit.targets import Output

ANSWERABLE = Case("q1", "Min salary?", True, "Rs 25,000.", [["25000"]])
OUT_OF_SCOPE = Case("u1", "Home loan rate?", False)


class FakeJudges:
    def __init__(self, correct=True, faithful=True):
        self.correct, self.faithful = correct, faithful

    def correctness(self, *a):
        return JudgeResult(self.correct, 1.0, {"facts": []})

    def faithfulness(self, *a):
        return JudgeResult(self.faithful, 1.0, {"claims": []})


def test_refusing_an_answerable_question_fails_without_a_judge_call():
    r = score_case(ANSWERABLE, Output("", False), FakeJudges())
    assert r["passed"] is False and r["judges"]["correctness"]["passed"] is False
    assert r["judges"]["faithfulness"] is None


def test_out_of_scope_must_be_refused():
    assert score_case(OUT_OF_SCOPE, Output("Not in policy", False), FakeJudges())["passed"] is True
    assert score_case(OUT_OF_SCOPE, Output("It is 8.5%", True, ["ctx"]), FakeJudges())["passed"] is False


def test_unfaithful_answer_fails_overall_even_if_correct():
    r = score_case(ANSWERABLE, Output("Rs 25,000 plus a bonus", True, ["ctx"]), FakeJudges(faithful=False))
    assert r["checks"]["facts"] is True and r["passed"] is False


def _write_run(path, name, passes):
    path.mkdir()
    results = [score_case(Case(f"q{i}", f"Q{i}?", True, "ref", [["x"]]),
                          Output("x" if ok else "y", True, ["ctx"], latency_ms=1000), FakeJudges(ok, True))
               for i, ok in enumerate(passes)]
    write_jsonl(path / "results.jsonl", results)
    write_jsonl(path / "outputs.jsonl", [{"id": r["id"], "output": r["output"]} for r in results])
    meta = {"name": name, "suite": "s", "judge": {"model": "j"}, "summary": summarize(results)}
    (path / "run.json").write_text(json.dumps(meta), encoding="utf-8")


def test_compare_flags_only_significant_regressions(tmp_path):
    _write_run(tmp_path / "a", "a", [True] * 20)
    _write_run(tmp_path / "b", "b", [True] * 12 + [False] * 8)  # 8 lost, 0 gained: p = 0.008
    _write_run(tmp_path / "c", "c", [True] * 18 + [False] * 2)  # 2 lost: could be noise
    assert "passed" in compare_runs(tmp_path / "a", tmp_path / "b", ["passed"])["regressions"]
    assert compare_runs(tmp_path / "a", tmp_path / "c", ["passed"])["regressions"] == []
    assert main(["compare", str(tmp_path / "a"), str(tmp_path / "b"), "--fail-on-regression"]) == 1
    assert main(["compare", str(tmp_path / "a"), str(tmp_path / "c"), "--fail-on-regression"]) == 0


def test_report_renders(tmp_path):
    _write_run(tmp_path / "a", "a", [True, False])
    html = write_report(tmp_path / "a").read_text(encoding="utf-8")
    assert "<table>" in html and "Overall pass" in html


def test_margin_gate_requires_proof_of_non_inferiority(tmp_path):
    _write_run(tmp_path / "a", "a", [True] * 20)
    _write_run(tmp_path / "c", "c", [True] * 18 + [False] * 2)  # not significant, but CI reaches about -20 pp
    assert compare_runs(tmp_path / "a", tmp_path / "c", ["passed"], margin=0.05)["regressions"] == ["passed"]
    assert compare_runs(tmp_path / "a", tmp_path / "c", ["passed"], margin=0.30)["regressions"] == []
