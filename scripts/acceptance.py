"""Exercise public CLI entry points and compare the SQL queue with observed test outcomes."""

import argparse
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from psycopg.errors import InsufficientPrivilege

from faro_risk import batch
from faro_risk.common import AS_OF, REAL, SIM, file_hash, put, read
from faro_risk.data import TARGET, source


def run():
    p = argparse.ArgumentParser()
    p.add_argument("--zip", required=True, type=Path)
    p.add_argument("--out", type=Path, default=Path("local/acceptance"))
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    def command(*parts):
        subprocess.run([sys.executable, *map(str, parts)], check=True)

    def cli(*parts):
        command("-m", "faro_risk.cli", *parts)

    testtemp = Path(tempfile.mkdtemp(dir=args.out))
    command("-m", "pytest", "-q", "--basetemp", testtemp, "--junitxml", args.out / "tests.xml")
    release = Path("reports/release")
    cli("validate")
    cli("demo", "--out", args.out / "demo")
    cli("export-holdout", "--zip", args.zip, "--out", args.out / "holdout.csv")
    cli("audit-import", "--zip", args.zip)
    cli("audit-import", "--zip", args.zip)

    def score(output):
        cli(
            "score",
            "--csv",
            args.out / "holdout.csv",
            "--namespace",
            REAL,
            "--as-of",
            AS_OF,
            "--out",
            args.out / output,
        )

    with ThreadPoolExecutor(2) as workers:
        list(workers.map(score, ["run-a.json", "run-b.json"]))
    # Compare every stored score to a fresh inference in reverse input order.
    frame = batch.read_batch(args.out / "holdout.csv")
    _, snapshot, rows, _ = batch.prepare(frame.iloc[::-1], release / "model")
    expected = dict((i, s) for i, s, _ in rows)
    with batch.fetch_connection() as conn:
        persisted = conn.execute(
            "SELECT account_id,score FROM faro_risk.score WHERE namespace=%s AND as_of=%s",
            (REAL, AS_OF),
        ).fetchall()
        blocked = conn.execute(
            "SELECT count(*) FROM faro_risk.snapshot WHERE namespace=%s AND as_of IN ('2026-02-28','2026-03-31')",
            (SIM,),
        ).fetchone()[0]
        version = conn.execute("SHOW server_version").fetchone()[0]
        conn.execute(Path("scripts/access.sql").read_text(encoding="utf8"))
        with conn.transaction():
            conn.execute("SET LOCAL ROLE faro_risk_reader")
            reader_rows = conn.execute(
                "SELECT count(*) FROM faro_risk.review_queue WHERE namespace=%s", (REAL,)
            ).fetchone()[0]
            try:
                with conn.transaction():
                    conn.execute(
                        "SELECT account_id FROM faro_risk_audit.historical_accounts LIMIT 1"
                    )
            except InsufficientPrivilege:
                private_denied = True
            else:
                raise RuntimeError("El lector obtuvo acceso a las variables privadas")
        with conn.transaction():
            conn.execute("SET LOCAL ROLE faro_risk_auditor")
            audit_count = conn.execute(
                "SELECT count(*) FROM faro_risk_audit.historical_accounts"
            ).fetchone()[0]
    delta = max(abs(expected[i] - s) for i, s in persisted)
    cli("queue", "--namespace", REAL, "--as-of", AS_OF, "--out", args.out / "queue.csv")
    queue = pd.read_csv(args.out / "queue.csv")
    y = source(args.zip).set_index("ID")[TARGET]
    report = read(release / "policy_report.json")
    active = report["decision"]["active"]
    policy = report["metrics"][active]["capacity"]["5"]
    hits = int(y.loc[queue.account_id].sum())
    statuses = sorted(read(args.out / f"run-{i}.json")["status"] for i in "ab")
    if not (
        statuses == ["published", "replay"]
        and delta <= 1e-12
        and hits == policy["hits"]
        and len(queue) == policy["k"]
        and len(persisted) == len(expected)
        and blocked == 0
        and reader_rows == len(queue)
        and audit_count == 30_000
        and list(queue.account_id)
        == [i for i, _, _ in sorted(rows, key=lambda r: (-r[1], r[2]))[: len(queue)]]
        and np.array_equal(queue.position, np.arange(1, len(queue) + 1))
    ):
        raise RuntimeError("Snapshot, concurrencia o cola divergente")
    put(
        args.out / "acceptance.json",
        {
            "postgresql": version,
            "access_check": {
                "reader_queue_rows": reader_rows,
                "reader_denied_audit": private_denied,
                "auditor_private_accounts": audit_count,
            },
            "namespace": REAL,
            "as_of": AS_OF,
            "feature_snapshot_id": snapshot,
            "rows": len(persisted),
            "queue": len(queue),
            "hits": hits,
            "concurrent_submissions": statuses,
            "max_absolute_score_replay_difference": delta,
            "tolerance": 1e-12,
            "blocked_snapshots_persisted": blocked,
            "sql_rank_matches_python": True,
            "queue_csv_sha256": file_hash(args.out / "queue.csv"),
            "first_queue_record": queue.iloc[0].to_dict(),
        },
    )


if __name__ == "__main__":
    run()
