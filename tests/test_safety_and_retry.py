from pathlib import Path

import jsonschema
import pytest

from faro_risk import batch
from faro_risk.cli import demo, validate_contract
from faro_risk.common import SIM, read

ROOT = Path(__file__).resolve().parents[1]


def test_retry_marker_survives_failure(monkeypatch, tmp_path):
    def stop():
        raise RuntimeError("unavailable")

    monkeypatch.setattr(batch, "fetch_connection", stop)
    for _ in range(2):
        with pytest.raises(RuntimeError, match="unavailable"):
            demo(ROOT / "reports/release/model", tmp_path, ROOT)
        assert read(tmp_path / "demo.json")["status"] == "started"


def test_existing_demo_directory_is_protected(tmp_path):
    (tmp_path / "demo.json").write_text('{"product":"other"}', encoding="utf8")
    with pytest.raises(ValueError, match="carpeta"):
        demo(ROOT / "reports/release/model", tmp_path, ROOT)


@pytest.mark.parametrize("bad", [{"data_kind": "real_public"}, {"score": 1.01}, {"target": 0}])
def test_public_score_contract(bad):
    row = {
        "namespace": SIM,
        "data_kind": "synthetic",
        "score": 0.4,
        "as_of": "2026-01-31",
        "account_id": 1,
        "feature_snapshot_id": "0" * 64,
        "model_version": "fixture",
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(ROOT, "risk_score", row | bad)
