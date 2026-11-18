"""The system under test, called as a black box over HTTP, the way a real client would call it."""

import time
from dataclasses import asdict, dataclass, field

import httpx

from .suite import Case, TargetConfig


@dataclass
class Output:
    answer: str
    answered: bool
    contexts: list[str] = field(default_factory=list)
    latency_ms: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def extract(data, path: str | None):
    """Read a value from parsed JSON with a small path syntax: "answer", "a.b", "sources[*].text"."""
    if not path:
        return None
    values, many = [data], False
    for part in path.split("."):
        star = part.endswith("[*]")
        key = part[:-3] if star else part
        nxt = []
        for v in values:
            v = v.get(key) if isinstance(v, dict) else None
            if v is None:
                continue
            if star:
                many = True
                nxt.extend(v)
            else:
                nxt.append(v)
        values = nxt
    if many:
        return values
    return values[0] if values else None


def fill(template, case: Case):
    """Put the case input into the request template, e.g. {"question": "{input}"}."""
    if isinstance(template, str):
        return template.replace("{input}", case.input).replace("{id}", case.id)
    if isinstance(template, dict):
        return {k: fill(v, case) for k, v in template.items()}
    if isinstance(template, list):
        return [fill(v, case) for v in template]
    return template


class HttpTarget:
    def __init__(self, config: TargetConfig, client: httpx.Client | None = None):
        self.config = config
        self.client = client or httpx.Client(timeout=config.timeout_s)

    def __call__(self, case: Case) -> Output:
        start = time.perf_counter()
        try:
            resp = self.client.post(self.config.url, json=fill(self.config.request, case))
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            ms = int((time.perf_counter() - start) * 1000)
            return Output(answer="", answered=False, latency_ms=ms, error=f"{type(e).__name__}: {e}")
        ms = int((time.perf_counter() - start) * 1000)
        answer = extract(data, self.config.answer) or ""
        answered = extract(data, self.config.answered)
        contexts = extract(data, self.config.contexts) or []
        return Output(
            answer=str(answer),
            answered=bool(answer) if answered is None else bool(answered),
            contexts=[str(c) for c in contexts],
            latency_ms=ms,
        )
