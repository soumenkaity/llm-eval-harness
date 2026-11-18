# Judge meta-evaluation: `qwen3:4b`

| Judge task | Items | Accuracy | Catch rate (bad flagged) | False alarms (good flagged) | Cohen's kappa | Judge errors |
|---|---|---|---|---|---|---|
| faithfulness | 92 | 82% | 85% | 22% | 0.63 | 0 |
| correctness | 86 | 93% | 95% | 9% | 0.86 | 0 |

## By source

| Judge task | Source | Items (good / bad) | Judge agrees |
|---|---|---|---|
| faithfulness | flip | 11 (0 / 11) | 7/11 |
| faithfulness | injected | 22 (0 / 22) | 22/22 |
| faithfulness | natural | 47 (46 / 1) | 36/47 |
| faithfulness | number_swap | 12 (0 / 12) | 10/12 |
| correctness | natural | 46 (45 / 1) | 42/46 |
| correctness | number_swap | 40 (0 / 40) | 38/40 |

## Disagreements with the label

- `rag-7b-hybrid/q05` faithfulness / natural: label good, judge bad; unsupported per judge: My CIBIL score is 670 | Can I still get a loan?
- `rag-7b-hybrid/q06` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q08` correctness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q08` faithfulness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q13` correctness / natural: label good, judge bad; judge: Yes. Grade E (highest-risk) borrowers are capped at 50% of the product's maximum loan amount. (contradicted)
- `rag-7b-hybrid/q15` faithfulness / natural: label good, judge bad; unsupported per judge: Until what time can I complete my request to get same-day disbursement?
- `rag-7b-hybrid/q15` correctness / natural: label good, judge bad; judge: Before the 3:01 PM IST cut-off (contradicted)
- `rag-7b-hybrid/q25` faithfulness / natural: label good, judge bad; unsupported per judge: Yes | if you repay a markup loan early | the markup is reduced to only cover the days actually used | but it is subject to a minimum of 15 days
- `rag-7b-hybrid/q31` faithfulness / natural: label good, judge bad; unsupported per judge: I lost my job | Can I pause my EMIs for a while | Yes
- `rag-7b-hybrid/q34` correctness / natural: label good, judge bad; judge: Foreclosure costs 4% of the outstanding principal. (contradicted)
- `rag-7b-hybrid/q34` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q34` faithfulness / natural [retrieval missed the foreclosure section; the answer applies the markup-loan '15 days' rule to an ordinary loan]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q08` faithfulness / natural: label good, judge bad; unsupported per judge: I earn 1.5 lakh a month | the maximum share of my income that can go to EMIs is 60%
- `rag-7b-no-rewrite/q08` correctness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every fact stated
- `rag-7b-no-rewrite/q08` faithfulness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q17` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q22` faithfulness / natural: label good, judge bad; unsupported per judge: part-prepayment is limited to 2.5% of the outstanding principal once per financial year
- `rag-7b-no-rewrite/q22` correctness / natural: label good, judge bad; judge: part-prepayment is limited to 25% of the outstanding principal once per financial year (contradicted)
- `rag-7b-no-rewrite/q31` faithfulness / natural: label good, judge bad; unsupported per judge: I lost my job | Can I pause my EMIs for a while
- `rag-3b-vector/q13` faithfulness / natural [includes a derived amount (50% of Rs 15,00,000 = Rs 7,50,000) that follows directly from the context]: label good, judge bad; unsupported per judge: For personal loans, the maximum amount is Rs 15,00,000 | so the riskiest borrowers can only receive up to 50% of that, which is Rs 7,50,000
- `rag-3b-vector/q31` faithfulness / natural [answer copies the policy text, starting with a stray [3]]: label good, judge bad; unsupported per judge: I lost my job | Can I pause my EMIs for a while
- `rag-3b-vector/q19` faithfulness / flip [never -> always]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q34` faithfulness / natural [borderline for correctness: gives the 4% cost but omits the 6-EMI condition]: label good, judge bad; unsupported per judge: Yes, you can close your loan early | it will cost you a 4% charge of the outstanding principal
