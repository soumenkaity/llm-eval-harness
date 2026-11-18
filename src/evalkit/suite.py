"""A suite = a dataset of test cases + the target system to call + how to judge the answers.

Suites are TOML files, so adding a new system to evaluate needs no code:

    name = "lending-policy-rag"
    dataset = "cases.jsonl"

    [target]
    url = "http://localhost:8000/ask"
    request = { question = "{input}" }
    answer = "answer"                 # where the answer is in the JSON response
    answered = "answered"             # optional: false means the system refused
    contexts = "sources[*].text"      # optional: retrieved passages, needed for faithfulness

    [judge]
    provider = "ollama"
    model = "qwen2.5:7b"
"""

import json
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Case:
    id: str
    input: str
    answerable: bool = True
    reference: str | None = None  # a correct answer, written by a person, for the correctness judge
    must_include: list[list[str]] = field(default_factory=list)  # exact facts; each inner list = alternatives
    tags: list[str] = field(default_factory=list)


@dataclass
class TargetConfig:
    url: str
    request: dict
    answer: str
    answered: str | None = None
    contexts: str | None = None
    timeout_s: float = 600


@dataclass
class JudgeConfig:
    provider: str = "ollama"  # "ollama" or "openai" (any OpenAI-compatible API)
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    api_key: str | None = None
    num_ctx: int = 4096
    think: bool | None = None  # for reasoning models in Ollama; None = don't send
    timeout_s: float = 600


@dataclass
class Suite:
    name: str
    cases: list[Case]
    target: TargetConfig
    judge: JudgeConfig
    path: Path


def load_cases(path: Path) -> list[Case]:
    cases = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(Case(**json.loads(line)))
        except (TypeError, json.JSONDecodeError) as e:
            raise ValueError(f"{path}:{n}: invalid case: {e}") from e
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate case ids")
    return cases


def load_suite(path: str | Path) -> Suite:
    path = Path(path)
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    judge = JudgeConfig(**raw.get("judge", {}))
    # Environment variables override the file, so CI or a teammate can switch judges without edits.
    judge.provider = os.environ.get("JUDGE_PROVIDER", judge.provider)
    judge.model = os.environ.get("JUDGE_MODEL", judge.model)
    judge.base_url = os.environ.get("JUDGE_BASE_URL", judge.base_url)
    judge.api_key = os.environ.get("JUDGE_API_KEY", judge.api_key)
    if "JUDGE_THINK" in os.environ:  # reasoning models (e.g. qwen3): "false" turns thinking off
        judge.think = os.environ["JUDGE_THINK"].lower() in ("1", "true", "yes")
    return Suite(
        name=raw["name"],
        cases=load_cases(path.parent / raw["dataset"]),
        target=TargetConfig(**raw["target"]),
        judge=judge,
        path=path,
    )
