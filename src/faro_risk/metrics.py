import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from .common import CAPS, SEED, tie_keys
from .data import AUDIT


def ranking(scores, ties):
    return np.lexsort((ties, -np.asarray(scores, dtype=float)))


def queue_metrics(y, order, pct):
    k = len(y) * pct // 100
    hits = int(y[order[:k]].sum())
    positives = int(y.sum())
    return {"k": k, "hits": hits, "precision": hits/k if k else None,
            "recall": hits/positives if positives else None}


def bins(y, scores):
    bucket = np.minimum((np.asarray(scores)*10).astype(int), 9)
    return [{"bin": i, "n": int((bucket==i).sum()),
             "predicted": float(scores[bucket==i].mean()) if (bucket==i).any() else None,
             "observed": float(y[bucket==i].mean()) if (bucket==i).any() else None}
            for i in range(10)]


def evaluate(y, preds, ids):
    ties = tie_keys(ids)
    result = {}
    for name, scores in preds.items():
        scores = np.asarray(scores)
        order = ranking(scores, ties)
        measures = {"ap": average_precision_score(y, scores), "roc_auc": roc_auc_score(y, scores),
                    "capacity": {str(p): queue_metrics(y, order, p) for p in CAPS}}
        if name != "rule":
            measures.update(brier=brier_score_loss(y, scores), log_loss=log_loss(y, scores),
                            calibration=bins(y, scores))
        result[name] = measures
    for measures in result.values():
        for p, row in measures["capacity"].items():
            baseline = result["rule"]["capacity"][p]["hits"]
            row["lift_vs_rule"] = row["hits"]/baseline if baseline else None
    return result


def interval(sample):
    a = np.asarray([v for v in sample if v is not None])
    return np.quantile(a, [0.025, 0.975]).tolist() if len(a) else [None, None]


def paired(y, preds, ids, repetitions=1000):
    rng = np.random.default_rng(SEED)
    ties = tie_keys(ids)
    ranks = {name: np.argsort(ranking(scores, ties)) for name, scores in preds.items()}
    ap_diff, brier_diff = [], []
    draws = {name: {str(p): {m: [] for m in ("precision","recall","lift_vs_rule")}
                    for p in CAPS} for name in preds}
    for _ in range(repetitions):
        idx = rng.integers(0, len(y), len(y))
        labels = y[idx]
        if np.unique(labels).size < 2:
            continue
        candidate, reference = preds["boost"][idx], preds["logistic"][idx]
        ap_diff.append(average_precision_score(labels, candidate) -
                       average_precision_score(labels, reference))
        brier_diff.append(np.mean((labels-candidate)**2 - (labels-reference)**2))
        hits = {}
        for name, rank in ranks.items():
            ordered = labels[np.argsort(rank[idx])].cumsum()
            hits[name] = {p: int(ordered[k-1]) if (k:=len(idx)*p//100) else 0 for p in CAPS}
        for name, by_pct in draws.items():
            for p in CAPS:
                h, k, base = hits[name][p], len(idx)*p//100, hits["rule"][p]
                entry = by_pct[str(p)]
                entry["precision"].append(h/k if k else None)
                entry["recall"].append(h/int(labels.sum()))
                entry["lift_vs_rule"].append(h/base if base else None)
    return {"requested": repetitions, "valid": len(ap_diff), "seed": SEED,
            "method": "paired account resampling, percentile 95%, queue rebuilt each draw",
            "ap_boost_minus_logistic": interval(ap_diff),
            "brier_boost_minus_logistic": interval(brier_diff),
            "capacity": {n: {p: {m: interval(a) for m,a in d.items()} for p,d in pct.items()}
                         for n,pct in draws.items()}}


def decision(eligible, measures, boot):
    candidate, reference = measures["boost"], measures["logistic"]
    lo = boot["ap_boost_minus_logistic"][0]
    gates = {"validation_eligible": bool(eligible), "higher_ap": candidate["ap"] > reference["ap"],
             "ap_lower_bound_positive": lo is not None and lo > 0,
             "brier_no_worse": candidate["brier"] <= reference["brier"]}
    promote = all(gates.values())
    return {"status": "promote" if promote else "hold", "active": "boost" if promote else "logistic",
            "checks": gates, "review_role": "responsable de riesgo simulado"}


def wilson(hits, total):
    if not total:
        return None
    z = norm.ppf(.975)
    p = hits/total
    den = 1 + z*z/total
    midpoint = p + z*z/(2*total)
    radius = z*np.sqrt(p*(1-p)/total + z*z/(4*total*total))
    return [max(0., (midpoint-radius)/den), min(1., (midpoint+radius)/den)]


def audit(df, y, scores, selected, minimum=100):
    rows = []
    for col in AUDIT:
        groups = (pd.cut(df[col], [0,29,39,49,59,np.inf], labels=["≤29","30–39","40–49","50–59","60+"])
                  if col == "AGE" else df[col])
        for value in sorted(groups.dropna().unique()):
            mask = np.asarray(groups==value)
            n = int(mask.sum())
            row = {"field": col, "group": str(value), "n": n, "suppressed": n < minimum}
            if n >= minimum:
                labels, prob, reviewed = y[mask], scores[mask], selected[mask]
                gap = prob-labels
                err = norm.ppf(.975)*gap.std(ddof=1)/np.sqrt(n)
                positives = int(labels.sum())
                hits = int(labels[reviewed].sum())
                count = int(reviewed.sum())
                row.update(selected=count, positives=positives, hits=hits, selection=count/n,
                           selection_ci=wilson(count,n), recall=hits/positives if positives else None,
                           recall_ci=wilson(hits,positives), mean_score=prob.mean(), observed=labels.mean(),
                           calibration_gap=gap.mean(), calibration_gap_ci=[gap.mean()-err,gap.mean()+err])
            rows.append(row)
    return rows
