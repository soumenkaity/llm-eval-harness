# Judge meta-evaluation: `qwen2.5:3b`

| Judge task | Items | Accuracy | Catch rate (bad flagged) | False alarms (good flagged) | Cohen's kappa | Judge errors |
|---|---|---|---|---|---|---|
| faithfulness | 90 | 61% | 31% | 9% | 0.22 | 2 |
| correctness | 86 | 87% | 76% | 2% | 0.74 | 0 |

## By source

| Judge task | Source | Items (good / bad) | Judge agrees |
|---|---|---|---|
| faithfulness | flip | 10 (0 / 10) | 3/10 |
| faithfulness | injected | 22 (0 / 22) | 2/22 |
| faithfulness | natural | 46 (45 / 1) | 41/46 |
| faithfulness | number_swap | 12 (0 / 12) | 9/12 |
| correctness | natural | 46 (45 / 1) | 44/46 |
| correctness | number_swap | 40 (0 / 40) | 31/40 |

## Disagreements with the label

- `rag-7b-hybrid/q02` faithfulness / flip [minimum -> maximum]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q03` faithfulness / injected [added: Customers who hold a Northwind salary account also get a 0.25% interest rate discount.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q05` correctness / natural: label good, judge bad; judge: My CIBIL score is 670 (contradicted)
- `rag-7b-hybrid/q06` faithfulness / natural: label good, judge bad; unsupported per judge: You can borrow up to Rs 1,00,000 as a new credit applicant with no credit history.
- `rag-7b-hybrid/q08` faithfulness / natural: label good, judge bad; unsupported per judge: The fixed obligation to income ratio (FOIR) including the proposed EMI must not exceed 50% of net monthly income.
- `rag-7b-hybrid/q08` correctness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q09` faithfulness / injected [added: Women applicants get this waived under the Udyam scheme.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q10` faithfulness / injected [added: A one-time documentation fee of Rs 750 also applies.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q12` faithfulness / injected [added: A gold-backed top-up loan is also available for this.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q13` correctness / number_swap [50 -> 75]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q13` faithfulness / injected [added: Senior citizens above 60 are given priority processing.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q15` correctness / number_swap [3 -> 5]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q15` faithfulness / injected [added: Requests can also be submitted at any Northwind branch on Saturdays.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q16` faithfulness / injected [added: Women applicants get this waived under the Udyam scheme.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q19` faithfulness / injected [added: A gold-backed top-up loan is also available for this.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q20` correctness / number_swap [1,999 -> 2,999]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q20` faithfulness / number_swap [1,999 -> 2,999]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q21` correctness / number_swap [500 -> 750]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q21` faithfulness / injected [added: Women applicants get this waived under the Udyam scheme.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q22` faithfulness / injected [added: Requests can also be submitted at any Northwind branch on Saturdays.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q24` faithfulness / injected [added: Senior citizens above 60 are given priority processing.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q25` faithfulness / injected [added: A gold-backed top-up loan is also available for this.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q26` faithfulness / number_swap [3 -> 5]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q27` faithfulness / injected [added: A one-time documentation fee of Rs 750 also applies.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q28` faithfulness / injected [added: Existing customers with a clean repayment record can have this limit raised by 10%.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q29` faithfulness / flip [before -> after]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q30` faithfulness / injected [added: Senior citizens above 60 are given priority processing.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q31` faithfulness / injected [added: A gold-backed top-up loan is also available for this.]: label bad, judge good; judge found every claim supported
- `rag-7b-hybrid/q33` correctness / number_swap [30 -> 45]: label bad, judge good; judge found every fact stated
- `rag-7b-hybrid/q34` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q34` faithfulness / natural [retrieval missed the foreclosure section; the answer applies the markup-loan '15 days' rule to an ordinary loan]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q34` correctness / natural [retrieval missed the foreclosure section; the answer applies the markup-loan '15 days' rule to an ordinary loan]: label bad, judge good; judge: 4% of the outstanding principal (missing)
- `rag-7b-no-rewrite/q01` faithfulness / injected [added: Requests can also be submitted at any Northwind branch on Saturdays.]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q08` faithfulness / number_swap [1,00,000 -> 1,50,000]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q17` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-7b-no-rewrite/q22` correctness / number_swap [6 -> 9]: label bad, judge good; judge found every fact stated
- `rag-7b-no-rewrite/q31` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q13` correctness / number_swap [50 -> 75]: label bad, judge good; judge found every fact stated
- `rag-3b-vector/q32` faithfulness / injected [added: The branch manager can approve exceptions to this rule.]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q05` faithfulness / natural: label good, judge bad; unsupported per judge: My CIBIL score is 670.
- `rag-3b-vector/q31` faithfulness / flip [up to -> at least]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q20` correctness / number_swap [1,999 -> 2,999]: label bad, judge good; judge found every fact stated
- `rag-3b-vector/q20` faithfulness / injected [added: Customers who hold a Northwind salary account also get a 0.25% interest rate discount.]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q19` faithfulness / flip [never -> always]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q01` faithfulness / injected [added: Requests can also be submitted at any Northwind branch on Saturdays.]: label bad, judge good; judge found every claim supported
- `rag-3b-vector/q34` faithfulness / natural [borderline for correctness: gives the 4% cost but omits the 6-EMI condition]: label good, judge bad; unsupported per judge: Part-prepayment is limited to 25% of the outstanding principal once per financial year and carries no charge. | A borrower may receive at most one moratorium during the loan tenure. | Interest continues to accrue during the moratorium and is added to the outstanding principal. | Borrowers facing genuine financial hardship, such as job loss or medical emergency, may request a moratorium of up to 3 months. | The answer to the question is yes, you can close your loan early.
