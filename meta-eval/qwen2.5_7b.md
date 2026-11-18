# Judge meta-evaluation: `qwen2.5:7b`

| Judge task | Items | Accuracy | Catch rate (bad flagged) | False alarms (good flagged) | Cohen's kappa | Judge errors |
|---|---|---|---|---|---|---|
| faithfulness | 92 | 88% | 83% | 7% | 0.76 | 0 |
| correctness | 86 | 94% | 90% | 2% | 0.88 | 0 |

## By source

| Judge task | Source | Items (good / bad) | Judge agrees |
|---|---|---|---|
| faithfulness | flip | 11 (0 / 11) | 7/11 |
| faithfulness | injected | 22 (0 / 22) | 22/22 |
| faithfulness | natural | 47 (46 / 1) | 43/47 |
| faithfulness | number_swap | 12 (0 / 12) | 9/12 |
| correctness | natural | 46 (45 / 1) | 45/46 |
| correctness | number_swap | 40 (0 / 40) | 36/40 |

## Disagreements with the label

- `rag-7b-hybrid/q01` faithfulness / number_swap [21 -> 32]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q06` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q08` correctness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q08` faithfulness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q12` correctness / number_swap [1.5 -> 2.25]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q18` faithfulness / flip [above -> below]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q25` correctness / number_swap [15 -> 23]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q34` faithfulness / natural: label good, judge bad; unsupported per judge: Yes, you can close your loan early.
- `rag-7b-hybrid/q34` correctness / natural: label good, judge bad; judge: What is the cost for early closure? (contradicted)
- `rag-7b-no-rewrite/q34` faithfulness / natural [retrieval missed the foreclosure section; the answer applies the markup-loan '15 days' rule to an ordinary loan]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q08` correctness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every fact stated
- `rag-7b-no-rewrite/q08` faithfulness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q17` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q31` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q13` faithfulness / natural [includes a derived amount (50% of Rs 15,00,000 = Rs 7,50,000) that follows directly from the context]: label good, judge bad; unsupported per judge: For personal loans, the maximum amount is Rs 15,00,000, so the riskiest borrowers can only receive up to 50% of that, which is Rs 7,50,000.
- `rag-3b-vector/q34` faithfulness / natural [borderline for correctness: gives the 4% cost but omits the 6-EMI condition]: label good, judge bad; unsupported per judge: Yes, you can close your loan early.
