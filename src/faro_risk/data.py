from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .common import SEED, SHA, file_hash

AUDIT = ["SEX", "EDUCATION", "MARRIAGE", "AGE"]
PAY = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
BILL = [f"BILL_AMT{i}" for i in range(1, 7)]
PAID = [f"PAY_AMT{i}" for i in range(1, 7)]
RAW = ["LIMIT_BAL", *PAY, *BILL, *PAID]
BATCH = ["ID", *RAW]
TARGET = "default payment next month"
COLUMNS = ["ID", "LIMIT_BAL", *AUDIT, *PAY, *BILL, *PAID, TARGET]
STATUS_CODES = {-1, *range(1, 10)}


def source(path):
    if file_hash(path) != SHA:
        raise ValueError("ZIP UCI con SHA-256 incompatible")
    with ZipFile(path) as z:
        with z.open("default of credit card clients.xls") as xls:
            df = pd.read_excel(BytesIO(xls.read()), sheet_name="Data", header=1, engine="xlrd")
    if list(df) != COLUMNS or len(df) != 30_000:
        raise ValueError("Hoja UCI incompatible")
    validate_batch(df[BATCH])
    if set(df[TARGET]) != {0, 1} or df[AUDIT].isna().any().any():
        raise ValueError("Etiqueta o auditoría de origen inválida")
    return df


def validate_batch(df):
    if set(df) != set(BATCH) or len(df.columns) != len(BATCH) or df.empty:
        raise ValueError("Contrato de entrada incompatible: se requieren ID y 19 campos históricos")
    for col in BATCH:
        if not pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_bool_dtype(df[col]):
            raise ValueError(f"Tipo incompatible en {col}")
        present = df[col].dropna().to_numpy(dtype=float)
        if not np.isfinite(present).all() or (present != np.trunc(present)).any():
            raise ValueError(f"Se requieren enteros finitos en {col}")
    if df.ID.isna().any() or df.ID.duplicated().any() or (df.ID <= 0).any():
        raise ValueError("ID ausente, no positivo o repetido")
    if (df.LIMIT_BAL.dropna() <= 0).any() or (df[PAID] < 0).any().any():
        raise ValueError("Límite o pago fuera de dominio")
    if df[RAW].isna().all(axis=1).any():
        raise ValueError("Cuenta sin historial utilizable")


def features(df):
    x = df[RAW].astype(float).copy()
    x["late_months"] = x[PAY].gt(0).sum(axis=1).where(x[PAY].notna().any(axis=1))
    x["unmapped_statuses"] = ((~x[PAY].isin(STATUS_CODES)) & x[PAY].notna()).sum(axis=1)
    x["bill_limit"] = x[BILL[0]].div(x.LIMIT_BAL.replace(0, np.nan))
    x["paid_prior_bill"] = x[PAID[0]].div(x[BILL[1]].replace(0, np.nan))
    return x


def partitions(df):
    ids = df.set_index("ID")[TARGET].sort_index()
    train, rest = train_test_split(ids.index, stratify=ids, test_size=0.4, random_state=SEED)
    valid, test = train_test_split(rest, stratify=ids.loc[rest], test_size=0.5, random_state=SEED)
    return pd.concat([pd.DataFrame({"ID": sorted(group), "split": name}) for name, group in
                      [("train", train), ("validation", valid), ("test", test)]], ignore_index=True)


def profile(df):
    domains = {**dict.fromkeys(PAY, STATUS_CODES), "SEX": {1, 2},
               "EDUCATION": {1, 2, 3, 4}, "MARRIAGE": {1, 2, 3}}
    return {"rows": len(df), "missing": df.isna().sum().to_dict(),
            "unique_ids": df.ID.nunique(), "negative_bill_cells": int((df[BILL] < 0).sum().sum()),
            "unknown_codes": {c: {str(k): int(n) for k, n in df[c].value_counts().items()
                                  if k not in known} for c, known in domains.items()},
            "range": {c: [int(df[c].min()), int(df[c].max())] for c in RAW + AUDIT}}


def synthetic(n=500):
    rng = np.random.default_rng(SEED)
    df = pd.DataFrame({"ID": np.arange(1, n+1), "LIMIT_BAL": rng.integers(1, 60, n)*1000})
    for c in PAY:
        df[c] = rng.choice([-2, -1, 0, 1, 2, 3], n)
    for c in BILL:
        df[c] = rng.integers(-1000, 75_000, n)
    for c in PAID:
        df[c] = rng.integers(0, 5000, n)
    for c, high in zip(AUDIT, [3, 5, 4, 78], strict=True):
        df[c] = rng.integers(21 if c=="AGE" else 1, high, n)
    df[TARGET] = (rng.random(n) < (0.13 + 0.34 * (df.PAY_0 >= 2))).astype(int)
    return df[COLUMNS]


def canonical_batch(df):
    validate_batch(df)
    return df[BATCH].sort_values("ID").astype("Int64").reset_index(drop=True)


def csv_bytes(df):
    return df.to_csv(index=False, lineterminator="\n").encode()


def download(path):
    import urllib.request

    from .common import digest

    url = "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip"
    with urllib.request.urlopen(url, timeout=60) as response:
        content = response.read(6_000_001)
    if digest(content) != SHA:
        raise ValueError("Descarga UCI no verificada")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
