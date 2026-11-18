import json

import httpx
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from evalkit.judges import Judges, decide_correctness, decide_faithfulness
from evalkit.llm import JudgeLLM, ResponseCache
from evalkit.suite import JudgeConfig


def test_faithfulness_verdict_is_computed_from_claims():
    assert decide_faithfulness({"claims": [{"supported": True}, {"supported": True}]}) == (True, 1.0)
    assert decide_faithfulness({"claims": [{"supported": True}, {"supported": False}]}) == (False, 0.5)
    assert decide_faithfulness({"claims": []}) == (True, 1.0)


def test_correctness_ignores_missing_background_detail():
    facts = [{"status": "stated", "essential": True}, {"status": "missing", "essential": False}]
    assert decide_correctness({"facts": facts})[0] is True
    assert decide_correctness({"facts": [{"status": "missing", "essential": True}]})[0] is False
    assert decide_correctness({"facts": [{"status": "contradicted", "essential": False}]})[0] is False
    assert decide_correctness({"facts": []})[0] is False


def _fake_ollama(calls):
    def handler(request):
        body = json.loads(request.read())
        calls.append(body)
        assert body["format"]["required"] == ["claims"] and body["options"]["temperature"] == 0
        content = {"claims": [{"claim": "Rs 25,000", "evidence": "Rs 25,000.", "supported": True},
                              {"claim": "0.25% discount", "evidence": "", "supported": False}]}
        return httpx.Response(200, json={"message": {"content": json.dumps(content)},
                                         "prompt_eval_count": 321, "eval_count": 45})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_judge_call_is_traced_and_cached(tmp_path):
    calls = []
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    llm = JudgeLLM(JudgeConfig(model="judge-x"), ResponseCache(tmp_path / "c.sqlite"), _fake_ollama(calls))
    judges = Judges(llm, provider.get_tracer("t"))

    first = judges.faithfulness("Min salary?", "Rs 25,000, plus a 0.25% discount", ["Rs 25,000."], "q2")
    second = judges.faithfulness("Min salary?", "Rs 25,000, plus a 0.25% discount", ["Rs 25,000."], "q2")

    assert first.passed is False and first.score == 0.5
    assert second.cached and len(calls) == 1  # the identical request never reached the model again
    span = exporter.get_finished_spans()[0]
    assert span.name == "judge.faithfulness"
    assert span.attributes["gen_ai.request.model"] == "judge-x"
    assert span.attributes["gen_ai.usage.input_tokens"] == 321
    assert span.attributes["evalkit.case_id"] == "q2"


def test_judge_failure_is_reported_not_counted_as_pass(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={"message": {"content": "not json"}})))
    judges = Judges(JudgeLLM(JudgeConfig(), None, client), TracerProvider().get_tracer("t"))
    res = judges.correctness("q", "a", "ref")
    assert res.passed is None and "judge call failed" in res.error
