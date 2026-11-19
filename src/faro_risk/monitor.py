import numpy as np
from scipy.stats import ks_2samp

from .data import RAW, validate_batch

WATCH = ["LIMIT_BAL", "PAY_0", "BILL_AMT1", "PAY_AMT1"]


def reference(frame):
    # An empirical distribution stored as unique values and cumulative frequencies.
    result = {}
    for col in WATCH:
        values, counts = np.unique(frame[col].dropna(), return_counts=True)
        result[col] = {"values": values.tolist(), "counts": counts.tolist()}
    return result


def inspect(frame, scores, baseline):
    validate_batch(frame)
    scores = np.asarray(scores, dtype=float)
    if (
        len(scores) != len(frame)
        or not np.isfinite(scores).all()
        or ((scores < 0) | (scores > 1)).any()
    ):
        raise ValueError("Probabilidades fuera de contrato")
    missing = frame[RAW].isna().mean()
    alerts = [f"missing:{c}" for c in RAW if missing[c] > 0.05]
    shift = {}
    for col in WATCH:
        train = np.repeat(baseline[col]["values"], baseline[col]["counts"])
        obs = frame[col].dropna().to_numpy(dtype=float)
        if obs.size:
            distance = float(ks_2samp(train, obs, method="asymp").statistic)
            shift[col] = distance
            if distance > 0.20:
                alerts.append(f"shift:{col}")
    return {
        "state": "suspend" if alerts else "publish",
        "alerts": alerts,
        "ks": shift,
        "missing_fraction": missing.to_dict(),
        "n": len(frame),
        "score_range": [float(scores.min()), float(scores.max())],
    }


def delayed_labels(ids, probabilities, labels, days):
    # Validate full one-to-one linkage before measuring matured outcomes.
    if len(set(ids)) != len(ids) or len(probabilities) != len(ids) or days < 0:
        raise ValueError("Claves de etiqueta incompatibles")
    if days < 30:
        return {"simulated": True, "days": days, "state": "awaiting_labels", "available": 0}
    if set(ids) != set(labels):
        raise ValueError("Claves de etiqueta incompatibles")
    y = np.array([labels[i] for i in ids])
    if not np.isin(y, [0, 1]).all():
        raise ValueError("Etiqueta no binaria")
    return {
        "simulated": True,
        "days": days,
        "state": "mature",
        "available": len(y),
        "brier": float(np.mean((np.asarray(probabilities) - y) ** 2)),
    }
