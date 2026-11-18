import httpx

from evalkit.metrics import contains_facts, refusal_correct
from evalkit.suite import Case, TargetConfig, load_suite
from evalkit.targets import HttpTarget, extract, fill

RESPONSE = {"answer": "Minimum Rs 25,000 [1]", "answered": True,
            "sources": [{"text": "Salaried applicants ... Rs 25,000."}, {"text": "Other"}]}
CONFIG = TargetConfig(url="http://rag/ask", request={"question": "{input}"}, answer="answer",
                      answered="answered", contexts="sources[*].text")


def test_extract_paths():
    assert extract(RESPONSE, "answer") == "Minimum Rs 25,000 [1]"
    assert extract(RESPONSE, "sources[*].text") == ["Salaried applicants ... Rs 25,000.", "Other"]
    assert extract({"a": {"b": 1}}, "a.b") == 1
    assert extract(RESPONSE, "missing") is None


def test_fill_template():
    assert fill({"q": "{input}", "meta": ["{id}"]}, Case("q1", "hi")) == {"q": "hi", "meta": ["q1"]}


def test_http_target_maps_response():
    seen = {}

    def handler(request):
        seen["body"] = request.read()
        return httpx.Response(200, json=RESPONSE)

    out = HttpTarget(CONFIG, httpx.Client(transport=httpx.MockTransport(handler)))(Case("q2", "Min salary?"))
    assert b"Min salary?" in seen["body"]
    assert out.answered and out.answer.startswith("Minimum") and len(out.contexts) == 2 and out.error is None


def test_http_target_records_errors_instead_of_crashing():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503, json={"detail": "down"})))
    out = HttpTarget(CONFIG, client)(Case("q2", "Min salary?"))
    assert out.error and not out.answered


def test_deterministic_checks():
    assert contains_facts("Minimum ₹25,000 per month", [["25000", "25k"]])
    assert not contains_facts("Minimum Rs 20,000", [["25000"]])
    assert refusal_correct(answered=False, answerable=False) and not refusal_correct(True, False)


def test_example_suite_loads():
    suite = load_suite("suites/lending-policy-rag/suite.toml")
    assert len(suite.cases) == 40
    assert all(c.reference for c in suite.cases if c.answerable)
    assert sum(not c.answerable for c in suite.cases) == 6
