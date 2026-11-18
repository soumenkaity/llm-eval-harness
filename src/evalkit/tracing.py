"""OpenTelemetry tracing: every target call and judge call becomes a span.

Spans always go to a local traces.jsonl inside the run folder (the HTML report draws them as a
timeline). If OTEL_EXPORTER_OTLP_ENDPOINT is set, they are also sent over OTLP/HTTP to any
OpenTelemetry backend (Jaeger, Grafana Tempo, Langfuse, Phoenix...). Install the extra first:
`uv sync --extra otlp`.

LLM attributes follow the OpenTelemetry GenAI semantic conventions (gen_ai.*).
"""

import json
import os
from pathlib import Path

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter, SpanExportResult


class JsonlSpanExporter(SpanExporter):
    def __init__(self, path: Path):
        self._file = open(path, "a", encoding="utf-8")

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        for s in spans:
            self._file.write(json.dumps(span_to_dict(s)) + "\n")
        self._file.flush()
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self._file.close()


def span_to_dict(s: ReadableSpan) -> dict:
    return {
        "trace_id": format(s.context.trace_id, "032x"),
        "span_id": format(s.context.span_id, "016x"),
        "parent_id": format(s.parent.span_id, "016x") if s.parent else None,
        "name": s.name,
        "start_ns": s.start_time,
        "end_ns": s.end_time,
        "status": s.status.status_code.name,
        "attributes": dict(s.attributes or {}),
    }


def make_provider(trace_file: Path | None, service: str = "evalkit") -> TracerProvider:
    provider = TracerProvider(resource=Resource.create({"service.name": service}))
    if trace_file:
        provider.add_span_processor(SimpleSpanProcessor(JsonlSpanExporter(trace_file)))
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    return provider


def read_traces(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
