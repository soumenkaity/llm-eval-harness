"""Judge LLM client: structured JSON output, a response cache, and token usage for tracing.

- Structured output: the JSON schema is sent to the model server (Ollama `format`, OpenAI
  `response_format`), which constrains generation so the reply always parses.
- Cache: identical judge requests are answered from SQLite. Re-scoring a run, or re-running a
  suite after changing one case, costs nothing for the unchanged cases.
"""

import hashlib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from .suite import JudgeConfig


class JudgeError(RuntimeError):
    pass


@dataclass
class LLMResult:
    data: dict
    input_tokens: int | None
    output_tokens: int | None
    cached: bool
    latency_ms: int


class ResponseCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self._lock = threading.Lock()

    def get(self, key: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT value FROM cache WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, value: dict) -> None:
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (key, json.dumps(value)))
            self._db.commit()


class JudgeLLM:
    def __init__(self, config: JudgeConfig, cache: ResponseCache | None = None, client: httpx.Client | None = None):
        self.config = config
        self.cache = cache
        self.client = client or httpx.Client(timeout=config.timeout_s)

    def complete_json(self, messages: list[dict], schema: dict) -> LLMResult:
        c = self.config
        key = hashlib.sha256(json.dumps(
            [c.provider, c.model, c.num_ctx, c.think, messages, schema], sort_keys=True).encode()).hexdigest()
        if self.cache and (hit := self.cache.get(key)):
            return LLMResult(hit["data"], hit["input_tokens"], hit["output_tokens"], True, 0)

        start = time.perf_counter()
        last_error = None
        for _ in range(2):  # one retry: local servers occasionally return a truncated reply
            try:
                text, tin, tout = self._ollama(messages, schema) if c.provider == "ollama" else self._openai(messages, schema)
                data = json.loads(text)
                break
            except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
                last_error = e
        else:
            raise JudgeError(f"judge call failed: {type(last_error).__name__}: {last_error}")
        ms = int((time.perf_counter() - start) * 1000)
        if self.cache:
            self.cache.put(key, {"data": data, "input_tokens": tin, "output_tokens": tout})
        return LLMResult(data, tin, tout, False, ms)

    def _ollama(self, messages, schema):
        c = self.config
        body = {"model": c.model, "messages": messages, "stream": False, "format": schema,
                "options": {"temperature": 0, "num_ctx": c.num_ctx}}
        if c.think is not None:
            body["think"] = c.think
        r = self.client.post(f"{c.base_url.rstrip('/')}/api/chat", json=body)
        r.raise_for_status()
        d = r.json()
        return d["message"]["content"], d.get("prompt_eval_count"), d.get("eval_count")

    def _openai(self, messages, schema):
        c = self.config
        body = {"model": c.model, "messages": messages, "temperature": 0,
                "response_format": {"type": "json_schema", "json_schema": {"name": "verdict", "schema": schema}}}
        headers = {"Authorization": f"Bearer {c.api_key}"} if c.api_key else {}
        r = self.client.post(f"{c.base_url.rstrip('/')}/chat/completions", json=body, headers=headers)
        r.raise_for_status()
        d = r.json()
        usage = d.get("usage") or {}
        return d["choices"][0]["message"]["content"], usage.get("prompt_tokens"), usage.get("completion_tokens")
