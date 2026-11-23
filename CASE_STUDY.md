# Case study · 300 reviews for 6,000 accounts

[Español](CASO_DE_ESTUDIO.md) · [Run the synthetic demo](README.md#run-the-synthetic-demo)

## The decision

Operations needs to fill a daily queue and explain why each account appears in it. Risk needs to decide whether to promote a new model. A model can improve the overall ranking while one of the alternatives puts more observed defaults in the first 300 places.

## What I built

I used a historical Taiwanese credit-card cohort from 2005. I separated accounts into training, selection and test sets before fitting transformations. I compared the last recorded overdue payment, a constant probability, logistic regression and calibrated gradient boosting. I froze the selection rule before looking at the final test. [Frozen selection record](reports/release/selection_frozen.json) · [Data provenance and license (Spanish)](DATA_SOURCES.md)

The production-style batch takes a CSV without labels or demographic fields. It records versioned scores with a source, date and input hash in PostgreSQL. A SQL view exposes the top 5% for human review. In the recovery test, two concurrent submissions produced one new publication and one replay. A schema mismatch blocked publication, and a separate test triggered a suspension based on quality thresholds. [PostgreSQL acceptance](reports/acceptance.json) · [Recovery evidence](reports/demo.json)

## What the test showed

The held-out set contained **6,000 accounts** and **1,327 observed defaults**. At 300 reviews, logistic regression surfaced **232** defaults, calibrated boosting **227** and the overdue-payment rule **215**. Boosting improved average precision across the full ranking and slightly improved the Brier score, so the predeclared global criterion produced `promote`. Its estimated advantage over the rule at 300 reviews was uncertain. [Metrics and intervals](reports/release/policy_report.json) · [Open interactive report](https://jorgealarcon07.github.io/jorgealarcon07/revision-de-riesgo/index.en.html)

| Review capacity | Accounts reviewed | Observed defaults surfaced by boosting | Share of all observed defaults |
|---|---:|---:|---:|
| 2% | 120 | 95 | 7.2% |
| 5% | 300 | 227 | 17.1% |
| 10% | 600 | 429 | 32.3% |

## What I learned

If the team's main goal is to find defaults within 300 reviews, that capacity should be part of the selection criterion before evaluating another cohort. The historical sample represents one population at one point in time. Measuring whether a review changes default rates or collections would require follow-up data on the actions taken. [Model card (Spanish)](model_card.md) · [English walkthrough transcript](assets/web/walkthrough.en.txt)
