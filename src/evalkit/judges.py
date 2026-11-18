"""LLM-as-judge metrics.

Two design choices that make a judge more reliable:

1. Reason in small steps, then decide in code. The judge never outputs a bare "pass/fail". It lists
   each claim (or reference fact) with evidence, and the verdict is computed from that list by a
   fixed rule. A one-word verdict is the least reliable thing to ask a model for, and the list
   shows a person *why* an answer failed.
2. Validate the judge before trusting it (see metaeval.py). A judge is a model too, and its error
   rate must be measured against known labels.
"""

from dataclasses import dataclass, field

from opentelemetry.trace import Tracer

from .llm import JudgeError, JudgeLLM

FAITHFULNESS_SYSTEM = """You check answers from a customer-support assistant for hallucinations. You are given the CONTEXT that the assistant retrieved and its ANSWER. Decide, claim by claim, whether the CONTEXT supports the ANSWER.

Rules:
- Break the ANSWER into its factual claims: every number, amount, percentage, time limit, condition, name and yes/no statement.
- For each claim, copy the sentence from the CONTEXT that supports it into "evidence", or write "" if there is none.
- supported = true only if the evidence states the claim or it follows directly from it. A claim that adds a condition, exception, number or benefit that the CONTEXT does not state is not supported, even if it sounds plausible.
- A number that differs from the CONTEXT is not supported. A reversed condition (at least / at most, before / after, minimum / maximum) is not supported.
- Ignore citation markers like [2] and polite phrases.
- Use only the CONTEXT, never your own knowledge."""

# Bump when a prompt changes: results from different versions are not comparable. A v2 faithfulness
# prompt was tried and rejected because meta-evaluation showed it was worse (meta-eval/prompts/).
PROMPT_VERSIONS = {"faithfulness": 1, "correctness": 1}

FAITHFULNESS_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence": {"type": "string"},
                    "supported": {"type": "boolean"},
                },
                "required": ["claim", "evidence", "supported"],
            },
        }
    },
    "required": ["claims"],
}

CORRECTNESS_SYSTEM = """You grade answers from a customer-support assistant against a REFERENCE answer written by an expert.

Rules:
- List each fact in the REFERENCE. For each one, write what the ANSWER says about it, and a status:
  "stated": the ANSWER says the same thing, in any wording or number format (Rs 25,000 = 25000 = 25k; 1 lakh = 1,00,000),
  "missing": the ANSWER does not mention it,
  "contradicted": the ANSWER gives a different number, condition, or yes/no.
- essential = true if the fact is needed to answer the QUESTION; false if it is extra background detail.
- Extra information in the ANSWER that is not in the REFERENCE does not affect this grade.
- Use only the REFERENCE, never your own knowledge."""

CORRECTNESS_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string"},
                    "answer_says": {"type": "string"},
                    "status": {"type": "string", "enum": ["stated", "missing", "contradicted"]},
                    "essential": {"type": "boolean"},
                },
                "required": ["fact", "answer_says", "status", "essential"],
            },
        }
    },
    "required": ["facts"],
}


@dataclass
class JudgeResult:
    passed: bool | None  # None = the judge itself failed (counted separately, never as a pass)
    score: float | None
    details: dict = field(default_factory=dict)
    error: str | None = None
    cached: bool = False

    def to_dict(self) -> dict:
        return {"passed": self.passed, "score": self.score, "details": self.details,
                "error": self.error, "cached": self.cached}


def decide_faithfulness(data: dict) -> tuple[bool, float]:
    claims = data.get("claims") or []
    if not claims:
        return True, 1.0
    supported = sum(bool(c.get("supported")) for c in claims)
    return supported == len(claims), supported / len(claims)


def decide_correctness(data: dict) -> tuple[bool, float]:
    facts = data.get("facts") or []
    if not facts:
        return False, 0.0  # a judge that found no facts to check has not checked anything
    bad = [f for f in facts if f.get("status") == "contradicted" or (f.get("status") == "missing" and f.get("essential"))]
    return not bad, sum(f.get("status") == "stated" for f in facts) / len(facts)


def numbered(contexts: list[str]) -> str:
    return "\n\n".join(f"[{i}] {c}" for i, c in enumerate(contexts, start=1)) or "(no context retrieved)"


class Judges:
    def __init__(self, llm: JudgeLLM, tracer: Tracer):
        self.llm = llm
        self.tracer = tracer

    def faithfulness(self, question: str, answer: str, contexts: list[str], case_id: str = "") -> JudgeResult:
        user = f"CONTEXT:\n{numbered(contexts)}\n\nQUESTION: {question}\n\nANSWER: {answer}"
        return self._run("faithfulness", FAITHFULNESS_SYSTEM, user, FAITHFULNESS_SCHEMA, decide_faithfulness, case_id)

    def correctness(self, question: str, answer: str, reference: str, case_id: str = "") -> JudgeResult:
        user = f"QUESTION: {question}\n\nREFERENCE: {reference}\n\nANSWER: {answer}"
        return self._run("correctness", CORRECTNESS_SYSTEM, user, CORRECTNESS_SCHEMA, decide_correctness, case_id)

    def _run(self, name, system, user, schema, decide, case_id) -> JudgeResult:
        cfg = self.llm.config
        with self.tracer.start_as_current_span(f"judge.{name}") as span:
            span.set_attributes({
                "evalkit.case_id": case_id,
                "gen_ai.operation.name": "chat",
                "gen_ai.provider.name": cfg.provider,
                "gen_ai.request.model": cfg.model,
                "gen_ai.request.temperature": 0,
            })
            try:
                res = self.llm.complete_json([{"role": "system", "content": system}, {"role": "user", "content": user}], schema)
            except JudgeError as e:
                span.set_attribute("error.type", "JudgeError")
                return JudgeResult(None, None, error=str(e))
            passed, score = decide(res.data)
            span.set_attributes({
                "gen_ai.usage.input_tokens": res.input_tokens or 0,
                "gen_ai.usage.output_tokens": res.output_tokens or 0,
                "evalkit.cache_hit": res.cached,
                "evalkit.judge.passed": passed,
            })
            return JudgeResult(passed, score, res.data, cached=res.cached)
