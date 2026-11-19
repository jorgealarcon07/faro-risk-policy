import datetime as dt
import os
import shutil
import uuid
from pathlib import Path

import pandas as pd
import pytest

from faro_risk import batch
from faro_risk.cli import main, validate, validate_contract
from faro_risk.common import SIM, read

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "reports/release"


def test_release_and_model_checksum(tmp_path):
    validate(ROOT, RELEASE)
    folder = tmp_path / "model"
    shutil.copytree(RELEASE / "model", folder)
    with (folder / (read(folder / "release.json")["active"] + ".joblib")).open("ab") as f:
        f.write(b"different")
    with pytest.raises(ValueError, match="Huella"):
        batch.load_release(folder)


@pytest.fixture
def db():
    if not os.getenv("PGDATABASE"):
        pytest.skip("Set PGDATABASE to a dedicated PostgreSQL database")
    with batch.fetch_connection() as conn:
        batch.initialize(conn)
        yield conn


@pytest.mark.postgres
def test_atomic_publication_recovery_and_conflicts(db):
    # One outer transaction contains a private test date; every change is rolled back.
    folder = RELEASE / "model"
    _, _, ref = batch.load_release(folder)
    frame = batch.demo_batch(ref)
    date = str(dt.date(2100, 1, 1) + dt.timedelta(days=uuid.uuid4().int % 90000))
    with db.transaction(force_rollback=True):
        with pytest.raises(RuntimeError), db.transaction():
            batch.publish(db, frame, folder, SIM, date)
            raise RuntimeError("interrupted before commit")
        assert batch.queue(db, SIM, date) == []
        first = batch.publish(db, frame, folder, SIM, date)
        assert (
            first["status"] == "published"
            and batch.publish(db, frame.iloc[::-1], folder, SIM, date)["status"] == "replay"
        )
        rows = batch.queue(db, SIM, date)
        assert len(rows) == 25 and rows[0]["score"] >= rows[-1]["score"]
        for row in rows:
            validate_contract(ROOT, "risk_score", {k: v for k, v in row.items() if k != "position"})
        frame.loc[0, "PAY_AMT2"] += 1
        with pytest.raises(ValueError, match="Colisión"):
            batch.publish(db, frame, folder, SIM, date)
        assert batch.queue(db, SIM, date) == rows


@pytest.mark.postgres
def test_demo_cli_e2e_and_clean(db, tmp_path):
    out = tmp_path / "example"
    assert main(["demo", "--out", str(out)]) == 0
    demo = read(out / "demo.json")
    assert demo["queue_rows"] == 25 and demo["repeat"] == "replay"
    assert demo["shift"]["status"] == "suspended" and demo["schema_blocked"]
    assert pd.read_csv(out / "queue.csv").position.tolist() == list(range(1, 26))
    (out / "user-file").write_text("keep", encoding="utf8")
    assert main(["clean", "--confirm", "--out", str(out)]) == 0
    assert (out / "user-file").is_file()


@pytest.mark.postgres
def test_schema_rejected_from_cli_before_write(db, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("ID,target\n1,0\n", encoding="utf8")
    out = tmp_path / "result.json"
    assert (
        main(
            [
                "score",
                "--csv",
                str(bad),
                "--out",
                str(out),
                "--namespace",
                SIM,
                "--as-of",
                "2088-12-31",
            ]
        )
        == 2
    )
    assert not out.exists() and batch.queue(db, SIM, "2088-12-31") == []
