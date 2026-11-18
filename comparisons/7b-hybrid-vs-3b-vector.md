# A/B comparison: `rag-7b-hybrid` (A) vs `rag-3b-vector` (B)

- **A**: qwen2.5:7b, hybrid retrieval + query rewrite (production config)
- **B**: qwen2.5:3b, vector-only retrieval (cheapest config)
- 40 paired cases; significance level 0.05; non-inferiority margin 15 pp

| Metric | n | A | B | B − A (95% CI) | only A passed | only B passed | McNemar p | Verdict |
|---|---|---|---|---|---|---|---|---|
| passed | 40 | 95% | 82% | -12 pp [-25 pp, +0 pp] | 6 | 1 | 0.125 | **not shown non-inferior** |
| refusal | 40 | 100% | 92% | -8 pp [-18 pp, +0 pp] | 3 | 0 | 0.250 | **not shown non-inferior** |
| facts | 34 | 100% | 91% | -9 pp [-21 pp, +0 pp] | 3 | 0 | 0.250 | **not shown non-inferior** |
| correctness | 34 | 94% | 88% | -6 pp [-21 pp, +9 pp] | 4 | 2 | 0.688 | **not shown non-inferior** |
| faithfulness | 31 | 94% | 90% | -3 pp [-16 pp, +6 pp] | 2 | 1 | 1.000 | **not shown non-inferior** |

Median latency: A 24.6 s, B 8.8 s.

## Cases that changed (overall pass)

| Case | Question | A | B |
|---|---|---|---|
| q04 | What is the lowest credit score you accept? | pass | fail |
| q06 | I have never taken a loan or credit card before. How much can I borrow? | pass | fail |
| q08 | I earn 1.5 lakh a month. What share of my income can go to EMIs? | pass | fail |
| q13 | Is there a limit on loan amount for the riskiest borrowers? | pass | fail |
| q22 | When am I allowed to close my loan early? | pass | fail |
| q23 | How much do I pay to foreclose a fixed-rate loan? | pass | fail |
| q32 | After how many days overdue does a loan become an NPA? | fail | pass |

**Gate: FAIL** on passed, refusal, correctness, faithfulness.
