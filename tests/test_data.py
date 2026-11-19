import numpy as np
import pytest
from pandas.testing import assert_frame_equal

from faro_risk.common import digest
from faro_risk.data import (
    AUDIT,
    BATCH,
    PAY,
    TARGET,
    canonical_batch,
    csv_bytes,
    features,
    partitions,
    profile,
    source,
    synthetic,
    validate_batch,
)


def test_split_is_exhaustive_disjoint_stable():
    df = synthetic()
    split = partitions(df)
    assert split.ID.is_unique and set(split.ID) == set(df.ID)
    assert split.groupby("split").size().to_dict() == {"train": 300, "test": 100, "validation": 100}
    assert_frame_equal(split, partitions(df.sample(frac=1, random_state=17)))
    assert df.merge(split).groupby("split")[TARGET].mean().max() - df[TARGET].mean() < 0.02


def test_outcome_and_audit_never_enter_features():
    data = synthetic()
    before = features(data)
    data[AUDIT + ["ID", TARGET]] = -12345
    assert_frame_equal(before, features(data))
    assert not set(before).intersection(["ID", TARGET, *AUDIT])


def test_zero_denominator_and_signed_balance():
    df = synthetic()
    df.loc[0, ["BILL_AMT1", "BILL_AMT2"]] = [-40, 0]
    out = features(df)
    assert out.loc[0, "bill_limit"] < 0
    assert np.isnan(out.loc[0, "paid_prior_bill"])
    assert out.loc[0, "late_months"] == int((df.loc[0, PAY] > 0).sum())


def test_raw_unknowns_kept():
    df = synthetic()
    df.loc[0, "PAY_0"] = -7
    assert profile(df)["unknown_codes"]["PAY_0"]["-7"] == 1
    assert features(df).loc[0, "PAY_0"] == -7


@pytest.mark.parametrize(
    "change",
    [
        "extra",
        "missing",
        "null_id",
        "duplicate",
        "zero_limit",
        "inf",
        "fractional",
        "text",
        "negative_payment",
    ],
)
def test_bad_batch(change):
    df = synthetic()[BATCH].copy()
    if change == "extra":
        df[TARGET] = 0
    if change == "missing":
        df.drop(columns="PAY_0", inplace=True)
    if change == "null_id":
        df.loc[0, "ID"] = np.nan
    if change == "duplicate":
        df.loc[0, "ID"] = df.ID.iloc[1]
    if change == "zero_limit":
        df.loc[0, "LIMIT_BAL"] = 0
    if change in {"inf", "fractional"}:
        df["PAY_0"] = df["PAY_0"].astype(float)
        df.loc[0, "PAY_0"] = np.inf if change == "inf" else 0.5
    if change == "text":
        df["PAY_0"] = df["PAY_0"].astype(str)
    if change == "negative_payment":
        df.loc[0, "PAY_AMT1"] = -1
    with pytest.raises(ValueError):
        validate_batch(df)


def test_canonical_fingerprint_ignores_input_order_and_numeric_representation():
    df = synthetic()[BATCH]
    first = canonical_batch(df)
    other = canonical_batch(df.iloc[::-1, ::-1].astype(float))
    assert digest(csv_bytes(first)) == digest(csv_bytes(other))


def test_bad_source_blocked_before_unpacking(tmp_path):
    path = tmp_path / "changed.zip"
    path.write_bytes(b"wrong revision")
    with pytest.raises(ValueError, match="SHA"):
        source(path)
