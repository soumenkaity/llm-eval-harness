# A/B comparison: `rag-7b-hybrid` (A) vs `rag-7b-no-rewrite` (B)

- **A**: qwen2.5:7b, hybrid retrieval + query rewrite (production config)
- **B**: qwen2.5:7b, hybrid retrieval without query rewrite (one LLM call fewer per question)
- 40 paired cases; significance level 0.05; non-inferiority margin 15 pp

| Metric | n | A | B | B − A (95% CI) | only A passed | only B passed | McNemar p | Verdict |
|---|---|---|---|---|---|---|---|---|
| passed | 40 | 95% | 90% | -5 pp [-12 pp, +0 pp] | 2 | 0 | 0.500 | no significant change |
| refusal | 40 | 100% | 98% | -2 pp [-8 pp, +0 pp] | 1 | 0 | 1.000 | no significant change |
| facts | 34 | 100% | 94% | -6 pp [-15 pp, +0 pp] | 2 | 0 | 0.500 | no significant change |
| correctness | 34 | 94% | 91% | -3 pp [-9 pp, +0 pp] | 1 | 0 | 1.000 | no significant change |
| faithfulness | 33 | 94% | 94% | +0 pp [-9 pp, +9 pp] | 1 | 1 | 1.000 | no significant change |

Median latency: A 24.6 s, B 22.5 s.

## Cases that changed (overall pass)

| Case | Question | A | B |
|---|---|---|---|
| q13 | Is there a limit on loan amount for the riskiest borrowers? | pass | fail |
| q16 | How do you check that my bank account is correct before sending money? | pass | fail |

**Gate: PASS**: every gated metric is shown to be within 15 pp of A.
