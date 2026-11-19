import datetime as dt
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import psycopg
from psycopg.rows import dict_row
from threadpoolctl import threadpool_limits

from .common import AS_OF, REAL, SEED, SIM, digest, file_hash, read, tie_keys
from .data import BATCH, canonical_batch, csv_bytes, features, synthetic
from .monitor import inspect

SQL = Path(__file__).with_name("sql") / "v1.sql"


def initialize(conn):
    with conn.transaction():
        conn.execute(SQL.read_text(encoding="utf-8"))


def load_release(folder):
    from importlib.metadata import version

    folder = Path(folder)
    manifest = read(folder / "release.json")
    name = manifest["active"]
    if name not in {"logistic", "boost"} or version("scikit-learn") != manifest["sklearn"]:
        raise ValueError("Familia o versión sklearn incompatible")
    file = folder / f"{name}.joblib"
    if (
        file_hash(file) != manifest["sha256"]
        or file_hash(folder / "reference.json") != manifest["reference_sha256"]
    ):
        raise ValueError("Huella de modelo o referencia incompatible")
    return joblib.load(file), manifest, read(folder / "reference.json")


def demo_batch(ref, n=500):
    frame = synthetic(n)[BATCH].copy()
    rng = np.random.default_rng(SEED)
    for c, dist in ref.items():
        counts = np.asarray(dist["counts"])
        frame[c] = rng.choice(dist["values"], n, p=counts / counts.sum())
    return frame


def prepare(frame, folder):
    canonical = canonical_batch(frame)
    model, release, ref = load_release(folder)
    with threadpool_limits(1):
        probabilities = model.predict_proba(features(canonical))[:, 1]
    report = inspect(canonical, probabilities, ref)
    ids = canonical.ID.astype("int64").tolist()
    rows = list(zip(ids, probabilities.tolist(), tie_keys(ids).tolist(), strict=True))
    return release, digest(csv_bytes(canonical)), rows, report


def publish(conn, frame, folder, namespace, as_of):
    day = dt.date.fromisoformat(as_of)
    if namespace not in (REAL, SIM) or (namespace == REAL and as_of != AS_OF):
        raise ValueError("Namespace o corte incompatible")
    release, snapshot, rows, monitor = prepare(frame, folder)
    result = {
        "namespace": namespace,
        "as_of": as_of,
        "data_kind": "real_public" if namespace == REAL else "synthetic",
        "model_version": release["model_version"],
        "feature_snapshot_id": snapshot,
        "monitor": monitor,
        "rows": len(rows),
        "run_id": release["run_id"],
    }
    if monitor["state"] != "publish":
        return dict(result, status="suspended")
    with conn.transaction():
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"{namespace}/{as_of}",)
        )
        old = conn.execute(
            "SELECT feature_snapshot_id,model_version FROM faro_risk.snapshot WHERE namespace=%s AND as_of=%s",
            (namespace, day),
        ).fetchone()
        if old:
            if tuple(old) != (snapshot, release["model_version"]):
                raise ValueError("Colisión de snapshot inmutable")
            return dict(result, status="replay")
        conn.execute(
            """INSERT INTO faro_risk.snapshot(namespace,as_of,feature_snapshot_id,model_version,
                     data_kind,run_id,accounts) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (
                namespace,
                day,
                snapshot,
                release["model_version"],
                result["data_kind"],
                release["run_id"],
                len(rows),
            ),
        )
        with conn.cursor().copy(
            "COPY faro_risk.score(namespace,as_of,account_id,score,tie_key) FROM STDIN"
        ) as cp:
            for account, value, tie in rows:
                cp.write_row((namespace, day, account, value, tie))
    return dict(result, status="published")


def queue(conn, namespace, as_of):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT namespace, as_of::text,account_id,score,model_version,feature_snapshot_id,data_kind,position
                    FROM faro_risk.review_queue WHERE namespace=%s AND as_of=%s ORDER BY position""",
            (namespace, as_of),
        )
        return cur.fetchall()


def fetch_connection():
    return psycopg.connect(connect_timeout=6, autocommit=True, application_name="faro_risk")


def read_batch(path):
    return pd.read_csv(path)
