# Judge meta-evaluation: `qwen2.5:7b`

| Judge task | Items | Accuracy | Catch rate (bad flagged) | False alarms (good flagged) | Cohen's kappa | Judge errors |
|---|---|---|---|---|---|---|
| faithfulness | 34 | 85% | 76% | 6% | 0.71 | 0 |
| correctness | 31 | 100% | 100% | 0% | 1.00 | 0 |

## By source

| Judge task | Source | Items (good / bad) | Judge agrees |
|---|---|---|---|
| faithfulness | flip | 4 (0 / 4) | 2/4 |
| faithfulness | injected | 8 (0 / 8) | 8/8 |
| faithfulness | natural | 18 (17 / 1) | 16/18 |
| faithfulness | number_swap | 4 (0 / 4) | 3/4 |
| correctness | natural | 17 (16 / 1) | 17/17 |
| correctness | number_swap | 14 (0 / 14) | 14/14 |

## Disagreements with the label

- `rag-7b-hybrid/q01` faithfulness / number_swap [21 -> 32]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q18` faithfulness / flip [above -> below]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q34` faithfulness / natural [retrieval missed the foreclosure section; the answer applies the markup-loan '15 days' rule to an ordinary loan]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q17` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q13` faithfulness / natural [includes a derived amount (50% of Rs 15,00,000 = Rs 7,50,000) that follows directly from the context]: label good, judge bad; unsupported per judge: For personal loans, the maximum amount is Rs 15,00,000, so the riskiest borrowers can only receive up to 50% of that, which is Rs 7,50,000.
