import numpy as np
import pytest
from sklearn.metrics import average_precision_score

from faro_risk.common import tie_keys
from faro_risk.data import AUDIT, BATCH, TARGET, features, synthetic
from faro_risk.metrics import audit, bins, decision, evaluate, paired, queue_metrics, ranking
from faro_risk.models import estimator
from faro_risk.monitor import delayed_labels, inspect, reference


def test_no_cross_fold_preprocessing():
    df = synthetic()
    x = features(df)
    model = estimator("logistic", 0.1, x.columns)
    model.fit(x.iloc[:300], df[TARGET].iloc[:300])
    model.predict_proba(x.iloc[300:])
    imp = model.named_steps["prepare"].named_transformers_["numbers"].steps[0][1]
    assert imp.statistics_[0] == np.median(x.LIMIT_BAL.iloc[:300])


def test_ranking_is_stable_in_ties_and_small_batches():
    ids = np.array([31, 7, 23, 9, 82, 10])
    scores = np.ones(len(ids))
    order = ranking(scores, tie_keys(ids))
    assert list(ids[order]) == list(ids[::-1][ranking(scores, tie_keys(ids[::-1]))])
    assert queue_metrics(np.zeros(6), order, 5) == {
        "k": 0,
        "hits": 0,
        "precision": None,
        "recall": None,
    }


def test_paired_identical_scores_zero_difference():
    probs = np.tile([0.2, 0.5, 0.3, 0.8], 25)
    y = np.tile([0, 0, 1, 1], 25)
    preds = dict(boost=probs, logistic=probs, rule=probs)
    res = paired(y, preds, np.arange(100), 30)
    assert res["valid"] == 30 and res["ap_boost_minus_logistic"] == [0, 0]
    assert res["capacity"]["boost"]["5"]["lift_vs_rule"] == [1, 1]
    assert evaluate(y, preds, np.arange(100))["boost"]["ap"] == average_precision_score(y, probs)


@pytest.mark.parametrize(
    ("eligible", "lo", "brier", "expected"),
    [
        (False, 0.1, 0.1, "hold"),
        (True, 0, 0.1, "hold"),
        (True, 0.1, 0.21, "hold"),
        (True, 0.1, 0.1, "promote"),
    ],
)
def test_gates(eligible, lo, brier, expected):
    metrics = {"logistic": {"ap": 0.5, "brier": 0.2}, "boost": {"ap": 0.6, "brier": brier}}
    assert decision(eligible, metrics, {"ap_boost_minus_logistic": [lo, 0.2]})["status"] == expected


def test_calibration_includes_endpoints_and_empty_bins():
    values = bins(np.array([0, 1]), np.array([0.0, 1.0]))
    assert values[0]["n"] == values[9]["n"] == 1 and values[4]["predicted"] is None


def test_small_group_suppression():
    df = synthetic()
    df.loc[0, "EDUCATION"] = 99
    scores = np.full(len(df), 0.3)
    groups = audit(df[AUDIT], df[TARGET].to_numpy(), scores, np.zeros(len(df), dtype=bool))
    rare = next(r for r in groups if r["field"] == "EDUCATION" and r["group"] == "99")
    assert rare == {"field": "EDUCATION", "group": "99", "n": 1, "suppressed": True}


def test_drift_missing_and_score_limits():
    df = synthetic()[BATCH].copy()
    ref = reference(df)
    p = np.full(len(df), 0.3)
    assert inspect(df, p, ref)["state"] == "publish"
    df["LIMIT_BAL"] *= 10
    df.loc[:100, "PAY_2"] = np.nan
    result = inspect(df, p, ref)
    assert set(result["alerts"]) == {"missing:PAY_2", "shift:LIMIT_BAL"}
    with pytest.raises(ValueError):
        inspect(df, p + 1, ref)


def test_unmatured_labels_do_not_become_negatives():
    args = ([1, 2], [0.1, 0.8], {2: 1, 1: 0})
    assert "brier" not in delayed_labels(*args, 7)
    assert delayed_labels(*args, 30)["brier"] == pytest.approx(0.025)
    with pytest.raises(ValueError):
        delayed_labels([1, 2], [0.1, 0.8], {2: 1}, 30)
