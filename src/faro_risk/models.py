import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .common import SEED
from .data import PAY

GRID = {"logistic": [0.01, 0.1, 1.0], "boost": [7, 15]}
FOLDS = 5


def folds():
    return StratifiedKFold(FOLDS, shuffle=True, random_state=SEED)


def estimator(kind, param, columns):
    categorical = make_pipeline(
        SimpleImputer(strategy="constant", fill_value=-999),
        OneHotEncoder(handle_unknown="ignore", sparse_output=False),
    )
    numeric = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler())
    transform = ColumnTransformer(
        [("status", categorical, PAY), ("numbers", numeric, [c for c in columns if c not in PAY])]
    )
    if kind == "logistic":
        model = LogisticRegression(C=param, max_iter=1000, random_state=SEED)
    else:
        model = HistGradientBoostingClassifier(
            max_leaf_nodes=param,
            max_iter=80,
            learning_rate=0.08,
            l2_regularization=2.0,
            early_stopping=False,
            random_state=SEED,
        )
    return Pipeline([("prepare", transform), ("model", model)])


def fit_candidates(x, y, valid_x, valid_y, record):
    metrics, fitted = [], {}
    for kind, grid in GRID.items():
        for param in grid:
            base = estimator(kind, param, x.columns)
            cv = cross_val_score(
                base, x, y, cv=folds(), scoring="average_precision", error_score="raise", n_jobs=1
            )
            model = (
                CalibratedClassifierCV(base, method="sigmoid", cv=folds(), ensemble=False, n_jobs=1)
                if kind == "boost"
                else base
            )
            model.fit(x, y)
            pred = model.predict_proba(valid_x)[:, 1]
            row = {
                "kind": kind,
                "param": param,
                "fold_ap": cv.tolist(),
                "cv_ap": float(np.mean(cv)),
                "validation_ap": average_precision_score(valid_y, pred),
                "validation_brier": brier_score_loss(valid_y, pred),
            }
            row["run_id"] = record(row)
            metrics.append(row)
            fitted[kind, param] = model
    reference = max(
        (r for r in metrics if r["kind"] == "logistic"), key=lambda r: r["validation_ap"]
    )
    choices = [r for r in metrics if r["kind"] == "boost"]
    eligible = [
        r
        for r in choices
        if r["validation_brier"] <= reference["validation_brier"]
        and r["validation_ap"] > reference["validation_ap"]
    ]
    candidate = max(eligible or choices, key=lambda r: r["validation_ap"])
    return (
        {r["kind"]: fitted[r["kind"], r["param"]] for r in (reference, candidate)},
        {
            "eligible": bool(eligible),
            "reference": reference,
            "candidate": candidate,
            "grid": metrics,
            "seed": SEED,
            "primary_capacity_pct": 5,
            "bootstrap": 1000,
            "test_gate": "validation eligible and AP delta CI95 lower > 0 and Brier <= LR",
        },
    )
