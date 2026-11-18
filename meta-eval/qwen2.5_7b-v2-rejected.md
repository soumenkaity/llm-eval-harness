# Judge meta-evaluation: `qwen2.5:7b`

| Judge task | Items | Accuracy | Catch rate (bad flagged) | False alarms (good flagged) | Cohen's kappa | Judge errors |
|---|---|---|---|---|---|---|
| faithfulness | 92 | 74% | 52% | 4% | 0.48 | 0 |
| correctness | 86 | 94% | 90% | 2% | 0.88 | 0 |

## By source

| Judge task | Source | Items (good / bad) | Judge agrees |
|---|---|---|---|
| faithfulness | flip | 11 (0 / 11) | 5/11 |
| faithfulness | injected | 22 (0 / 22) | 14/22 |
| faithfulness | natural | 47 (46 / 1) | 44/47 |
| faithfulness | number_swap | 12 (0 / 12) | 5/12 |
| correctness | natural | 46 (45 / 1) | 45/46 |
| correctness | number_swap | 40 (0 / 40) | 36/40 |

## Disagreements with the label

- `rag-7b-hybrid/q01` faithfulness / number_swap [21 -> 32]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q02` faithfulness / flip [minimum -> maximum]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q06` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q08` correctness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q08` faithfulness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q09` faithfulness / injected [added: Women applicants get this waived under the Udyam scheme.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q10` faithfulness / injected [added: A one-time documentation fee of Rs 750 also applies.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q11` faithfulness / number_swap [80 -> 82]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q12` correctness / number_swap [1.5 -> 2.25]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q12` faithfulness / injected [added: A gold-backed top-up loan is also available for this.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q13` faithfulness / injected [added: Senior citizens above 60 are given priority processing.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q17` faithfulness / number_swap [3 -> 5]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q18` faithfulness / flip [above -> below]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q20` faithfulness / number_swap [1,999 -> 2,999]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q24` faithfulness / injected [added: Senior citizens above 60 are given priority processing.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q25` correctness / number_swap [15 -> 23]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q25` faithfulness / injected [added: A gold-backed top-up loan is also available for this.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q29` faithfulness / flip [before -> after]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q30` faithfulness / injected [added: Senior citizens above 60 are given priority processing.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q34` faithfulness / natural: label good, judge bad; unsupported per judge: Yes, you can close your loan early.
- `rag-7b-hybrid/q34` correctness / natural: label good, judge bad; judge: What is the cost for early closure? (contradicted)
- `rag-7b-no-rewrite/q34` faithfulness / natural [retrieval missed the foreclosure section; the answer applies the markup-loan '15 days' rule to an ordinary loan]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q01` faithfulness / injected [added: Requests can also be submitted at any Northwind branch on Saturdays.]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q08` correctness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every fact stated
- `rag-7b-no-rewrite/q08` faithfulness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q31` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q13` faithfulness / flip [maximum -> minimum]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q05` faithfulness / number_swap [670 -> 1005]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q34` faithfulness / natural [borderline for correctness: gives the 4% cost but omits the 6-EMI condition]: label good, judge bad; unsupported per judge: Yes, you can close your loan early.
