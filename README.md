# evalkit: an evaluation harness for LLM applications

`evalkit` tests an LLM application the way a backend gets tested: a fixed suite of cases, metrics
with confidence intervals, A/B comparisons with significance tests, a CI gate that blocks
regressions, and an OpenTelemetry trace of every call. Scoring uses **LLM-as-judge**. The judges are
not taken on trust: each one is **meta-evaluated** against hand-labelled and deliberately corrupted
answers before its scores are used.

Here it evaluates my [lending-policy RAG assistant](https://github.com/soumenkaity/lending-policy-rag),
but nothing in the harness is specific to it. A new system needs one TOML file and a JSONL dataset.

Everything runs locally and for free with [Ollama](https://ollama.com) on a 4 GB laptop GPU. Any
OpenAI-compatible API can be used as the judge instead.

## What it answers

| Question | Command | Output |
|---|---|---|
| How good is this version of my app? | `evalkit run` then `evalkit score` | pass rates with 95% CIs, an HTML report, traces |
| Is version B worse than version A? | `evalkit compare A B` | paired diff with CI, McNemar test, changed cases |
| Should this change ship? | `evalkit compare A B --margin 0.15 --fail-on-regression` | exit code for CI |
| Can I trust the judge? | `evalkit meta-eval` | judge accuracy, catch rate, false alarms, Cohen's kappa |

## Architecture

```
 suite.toml + cases.jsonl
        │
        ▼
 ┌─ record ──────────────┐      ┌─ score ───────────────────────────────────────┐
 │ POST each case to the │      │ deterministic checks: refusal, required facts │
 │ target (HTTP/JSON)    │ ───► │ LLM judges: correctness, faithfulness         │ ───► results.jsonl
 │ → outputs.jsonl       │      │   (JSON-schema output, SQLite response cache) │      run.json (summary + CIs)
 └───────────────────────┘      └───────────────────────────────────────────────┘      report.html
        │                                        │
        └──────── OpenTelemetry spans ───────────┴──► traces.jsonl  (or any OTLP backend)

 compare A B  ──► paired bootstrap CI + exact McNemar per metric ──► markdown report, CI gate
 meta-eval    ──► judges vs labelled + synthetic-bad answers     ──► judge accuracy report
```

**Two phases, recorded then scored.** The target is called once and its answers are saved. Scoring
runs on the saved answers, so a run can be re-scored with another judge or a fixed prompt without
calling the app again. On a small GPU it also means only one model is loaded at a time.

## The metrics

| Metric | How | Applies to |
|---|---|---|
| `refusal` | the app refused exactly when it should have (deterministic) | every case |
| `facts` | the answer contains the required numbers or phrases, after normalising "₹" and Indian digit grouping (deterministic) | answerable cases |
| `correctness` | LLM judge: the answer agrees with a reference answer written by a person | answerable cases |
| `faithfulness` | LLM judge: every claim in the answer is supported by the passages the app retrieved (catches hallucination) | answered cases with retrieved context |
| `passed` | the case is refused correctly, or answered correctly *and* faithfully | every case |

### How the judges are built

The judge never outputs a bare pass or fail, which is the least reliable thing to ask a model for.
It fills in a JSON schema (Ollama's `format`, or OpenAI's `response_format`):

- **Faithfulness**: list every claim in the answer. For each claim, copy the supporting sentence from
  the context and mark it supported or not.
- **Correctness**: list every fact in the reference answer. For each fact, say what the answer says
  about it and mark it `stated`, `missing` or `contradicted`, and essential or not.

**The verdict is computed in code from that list.** An answer is faithful only if every claim is
supported. It is correct unless a fact is contradicted, or an essential fact is missing. The list
also shows a person *why* a case failed. The HTML report shows it next to each case.

Judge calls use temperature 0 and are cached in SQLite, keyed by a hash of the full request.
Re-scoring is therefore free and repeatable. Every result records the judge model and
`PROMPT_VERSIONS`, because scores from different prompts are not comparable.

## Step 1: validate the judge (meta-evaluation)

An LLM judge is a classifier, so it is measured like one: on answers whose true label is known.

- **Natural items**: real answers from the recorded runs, labelled by me
  ([`labels.jsonl`](suites/lending-policy-rag/meta/labels.jsonl)). Borderline answers are left unlabelled.
- **Synthetic bad items**: good answers corrupted in known ways, so they are bad by construction:
  - `number_swap`: a number the reference depends on is changed (Rs 1,00,000 to Rs 1,50,000). The
    new value is chosen so that it appears nowhere in the retrieved context.
  - `flip`: a condition is reversed (up to to at least, above to below).
  - `injected`: a plausible policy claim that no document contains is appended. A test checks that
    the claim really is absent from the documents.

This gives 178 items: 92 for faithfulness and 86 for correctness.

**Three local judges, same stratified sample of 65 items:**

| Judge | Faithfulness: accuracy / catch rate / false alarms / κ | Correctness: accuracy / catch rate / false alarms / κ | Time per call |
|---|---|---|---|
| qwen2.5:3b | 62% / **24%** / 0% / 0.24 | 87% / 73% / 0% / 0.74 | 10 s |
| qwen3:4b (thinking off) | 79% / 88% / **29%** / 0.59 | 97% / 100% / 6% / 0.94 | 29 s |
| **qwen2.5:7b** | **85% / 76% / 6% / 0.71** | **100% / 100% / 0% / 1.00** | 34 s |

**The chosen judge, qwen2.5:7b, on all 178 items** ([full report](meta-eval/qwen2.5_7b.md)):

| Judge task | Items | Accuracy | Catch rate | False alarms | Cohen's κ |
|---|---|---|---|---|---|
| faithfulness | 92 | 88% | 83% | 7% | 0.76 |
| correctness | 86 | 94% | 90% | 2% | 0.88 |

The breakdown by corruption type shows *what* the judge misses. It caught 22 of 22 injected claims,
but only 7 of 11 reversed conditions ("up to" to "at least" slips past) and 9 of 12 swapped numbers.
These are the subtle errors a real model makes, so the judge's catch rate is a bound on how much
hallucination the eval can see.

What these numbers changed:

- **A small judge is not a cheap judge.** The 3B model passed three quarters of the hallucinated
  answers. Its scores would have looked great and meant nothing.
- **qwen3:4b catches more but cries wolf.** It flagged 29% of good answers. Most often it treated the
  user's own words ("I lost my job") as claims the answer had to support.
- **A prompt "fix" that made things worse.** After reading the 7B judge's misses, I wrote a stricter
  v2 faithfulness prompt. On the same items, its catch rate *fell* from 76% to 47% and κ from 0.71
  to 0.47. It was reverted, and both prompts are kept in [`meta-eval/prompts/`](meta-eval/prompts/).
  Without a meta-eval, that change would have shipped on intuition. The v1 numbers above were also
  measured on the items I read while tuning, so they are somewhat optimistic. A held-out split is
  the right fix (see next steps).

## Step 2: evaluate three versions of the RAG app

40 cases: 34 answerable questions, each with a hand-written reference answer, and 6 questions that
the policies do not cover and that must be refused. Three configurations of the app were recorded:

| Run | Configuration | passed | refusal | correctness | faithfulness | median latency |
|---|---|---|---|---|---|---|
| A `rag-7b-hybrid` | qwen2.5:7b, hybrid retrieval + query rewrite (production) | **95%** [88, 100] | 100% | 94% | 94% | 24.6 s |
| B `rag-7b-no-rewrite` | same, without the query-rewrite LLM call | 90% [80, 97] | 98% | 91% | 94% | 22.5 s |
| C `rag-3b-vector` | qwen2.5:3b, vector-only retrieval (cheapest) | 82% [70, 93] | 92% | 88% | 90% | 8.8 s |

Square brackets are 95% bootstrap confidence intervals. Each run folder has an HTML report with
every answer, the judge's claim-by-claim reasoning and a trace timeline.

Reading the failures one by one matters as much as the totals. Both of run A's failures are judge
errors on inspection. For q32 it marked "after 91 days overdue" as contradicting "more than 90
days". For q34 it flagged a correct answer. Run C refused three questions it should have answered,
because vector-only retrieval missed the right section.

## Step 3: compare and gate

`evalkit compare` pairs the cases, so every question is compared with itself. It reports the paired
bootstrap CI of B − A and an exact McNemar test on the cases where the runs disagree
([A vs B](comparisons/7b-hybrid-vs-no-rewrite.md), [A vs C](comparisons/7b-hybrid-vs-3b-vector.md)):

| Comparison | passed: B − A [95% CI] | McNemar p | Significance gate | Non-inferiority gate (15 pp) |
|---|---|---|---|---|
| A vs B: drop the query rewrite | −5 pp [−12, 0] | 0.50 | pass | **pass** |
| A vs C: 3B model, vector only | −12 pp [−25, 0] | 0.13 | pass ⚠ | **fail** |

**The most useful result of the project:** the classic gate ("fail on a statistically significant
regression") let config C through, although it was 12 points worse. With 40 cases, a 12-point drop
is not significant. "No significant regression" is not the same as "no regression".

So the gate now supports **non-inferiority**. With `--margin 0.15`, the candidate passes only if the
lower end of its 95% CI is above −15 pp, meaning the data rules out a drop bigger than 15 points.
The burden of proof moves to the change. The CI workflow checks all three outcomes on the committed
runs. In honesty, the 15 pp margin was picked after seeing these runs. A margin should be chosen in
advance, from what the business can tolerate. With 40 cases, the CI cannot prove anything tighter
than about ±10 pp.

## Tracing

Every target call, judge call and case is an OpenTelemetry span. Model calls carry the
[GenAI semantic convention](https://opentelemetry.io/docs/specs/semconv/gen-ai/) attributes
(`gen_ai.request.model`, `gen_ai.usage.input_tokens`, ...) and `evalkit.cache_hit`. Spans are written
to `traces.jsonl` in each run folder. Set `OTEL_EXPORTER_OTLP_ENDPOINT` to send them to Jaeger,
Grafana Tempo, Phoenix or Langfuse instead:

```bash
uv sync --extra otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 uv run evalkit score ...
```

## Running it

Requirements: [uv](https://docs.astral.sh/uv/) and Ollama with `ollama pull qwen2.5:7b`.

```bash
uv sync
uv run pytest                                    # 27 tests, no LLM needed

# Comparisons and the gate work on the committed runs; no model needed
uv run evalkit compare runs/rag-7b-hybrid runs/rag-3b-vector --margin 0.15 --fail-on-regression
uv run evalkit report runs/rag-7b-hybrid         # rebuild report.html

# Full loop: start the lending-policy-rag API on :8000 first
uv run evalkit run   suites/lending-policy-rag/suite.toml --name my-run --label "what changed"
uv run evalkit score suites/lending-policy-rag/suite.toml runs/my-run

# Judge validation (178 judge calls, about 1.5 to 2 h for the 7B on a 4 GB GPU; --sample 65 for a quick look)
uv run evalkit meta-eval suites/lending-policy-rag/suite.toml \
    --labels suites/lending-policy-rag/meta/labels.jsonl \
    --run runs/rag-7b-hybrid --run runs/rag-7b-no-rewrite --run runs/rag-3b-vector
```

The judge comes from `suite.toml` and can be overridden without editing files:
`JUDGE_MODEL`, `JUDGE_PROVIDER=openai`, `JUDGE_BASE_URL`, `JUDGE_API_KEY`, and `JUDGE_THINK=false` for
reasoning models (see [`.env.example`](.env.example)). The committed `runs/judge-cache.sqlite` makes
re-scoring the committed runs instant.

### Adding a system to evaluate

```toml
# suites/my-app/suite.toml
name = "my-app"
dataset = "cases.jsonl"

[target]
url = "http://localhost:8080/chat"
request = { message = "{input}" }    # JSON body; {input} is the case's input
answer = "reply.text"                 # where the answer is in the response
answered = "answered"                 # optional: false = the app refused
contexts = "sources[*].text"          # optional: retrieved passages, enables faithfulness

[judge]
provider = "ollama"
model = "qwen2.5:7b"
```

```json
{"id": "q01", "input": "...", "answerable": true, "reference": "...", "must_include": [["25,000", "25000"]], "tags": ["fees"]}
```

## Layout

```
src/evalkit/
  suite.py      suite + case loading, env overrides
  targets.py    HTTP target, JSON path extraction
  metrics.py    deterministic checks
  llm.py        judge client (Ollama / OpenAI-compatible), JSON schema output, SQLite cache
  judges.py     faithfulness and correctness judges, verdict rules, prompt versions
  runner.py     record and score phases, summaries
  stats.py      bootstrap CIs, paired bootstrap, exact McNemar, Cohen's kappa
  compare.py    A/B comparison, significance and non-inferiority gates
  metaeval.py   synthetic corruptions, stratified sampling, judge accuracy
  tracing.py    OpenTelemetry setup, JSONL span exporter
  report.py     self-contained HTML report
suites/lending-policy-rag/   40 cases + hand labels for meta-evaluation
runs/                        three recorded and scored runs (outputs, results, traces, reports)
meta-eval/                   judge reports, including the rejected v2 prompt
comparisons/                 A/B reports
```

## Limitations

- **40 cases is small.** Only large differences can be detected. Most real suites need hundreds
  of cases, and the CIs above show why.
- **The labels are mine,** made by one person, and two answers were too borderline to label. Real
  labelling needs two annotators and their agreement measured.
- **Synthetic errors are easier than natural ones.** Only one natural answer was truly bad, so the
  catch rate is mostly measured on corruptions.
- **Self-preference.** The 7B judge grades answers from the same model family. A judge from a
  different family would be safer.
- **The judge's errors land in the scores.** Run A's two failures are judge mistakes, so per-case
  results need human review, not only the totals.

## Next steps

- A held-out split of labelled items, so that prompt iteration does not overfit the meta-eval.
- A pairwise judge ("which answer is better?") that runs twice with the positions swapped, to cancel
  position bias.
- Trajectory evaluation for agents (right tools, right order), applied to my
  [health-claims agent](https://github.com/soumenkaity/health-claims-agent).
- Generating the candidate run inside CI from the pull request, instead of gating committed runs.
