"""Refit the frozen specifications, check validation predictions without using test outcomes."""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from faro_risk.common import digest, file_hash, put, read
from faro_risk.data import TARGET, csv_bytes, features, partitions, source
from faro_risk.models import fit_candidates


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--release", type=Path, default=Path("reports/release"))
    p.add_argument("--out", type=Path, default=Path("local/reproduced.json"))
    args = p.parse_args()
    freeze = read(args.release / "selection_frozen.json")
    data = source(args.zip)
    splits = partitions(data)
    saved = pd.read_csv(args.release / "splits.csv")
    if not splits.equals(saved):
        raise RuntimeError("Split no reproducido")
    indexed = data.set_index("ID")
    train = indexed.loc[saved.loc[saved.split == "train", "ID"]]
    valid = indexed.loc[saved.loc[saved.split == "validation", "ID"]]
    x, y = features(train), train[TARGET]
    vx, vy = features(valid), valid[TARGET]
    if digest(csv_bytes(x)) != freeze["train_feature_sha256"]:
        raise RuntimeError("Features de entrenamiento divergentes")
    with threadpool_limits(1):
        models, new = fit_candidates(x, y, vx, vy, lambda row: None)
        delta = {}
        for key, m in models.items():
            path = args.release / "model" / f"{key}.joblib"
            if file_hash(path) != freeze["model_hashes"][key]:
                raise ValueError("Huella de modelo incompatible")
            pinned = joblib.load(path)
            delta[key] = float(np.max(np.abs(m.predict_proba(vx) - pinned.predict_proba(vx))))
    if max(delta.values()) > 1e-12 or any(
        new[k]["param"] != freeze[k]["param"] for k in ["reference", "candidate"]
    ):
        raise RuntimeError("Ajuste no reproducido")
    put(
        args.out,
        {
            "train": len(train),
            "validation": len(valid),
            "split_identical": True,
            "train_features_identical": True,
            "selected_parameters_identical": True,
            "max_absolute_validation_probability_difference": delta,
            "tolerance": 1e-12,
            "test_outcomes_used_for_refit_or_comparison": False,
        },
    )


if __name__ == "__main__":
    main()
