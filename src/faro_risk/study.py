import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from importlib import metadata
from pathlib import Path

import joblib
import numpy as np
import psutil
from threadpoolctl import threadpool_limits

from .common import AS_OF, REAL, SEED, SHA, digest, file_hash, log, put, tie_keys
from .data import AUDIT, BATCH, BILL, TARGET, csv_bytes, features, partitions, profile, source
from .metrics import audit, decision, evaluate, paired, ranking
from .models import fit_candidates
from .monitor import delayed_labels, inspect, reference


def experiment_tracker(work):
    os.environ.setdefault("MLFLOW_ENABLE_TELEMETRY", "false")
    from mlflow import MlflowClient

    uri = "sqlite:///" + (work / "tracking.sqlite").resolve().as_posix()
    client = MlflowClient(tracking_uri=uri)
    name = "faro-risk-policy-v1"
    experiment = client.get_experiment_by_name(name)
    eid = (
        experiment.experiment_id
        if experiment
        else client.create_experiment(
            name, artifact_location=(work / "artifacts").resolve().as_uri()
        )
    )
    return client, eid


def study(archive, out, work):
    # Never replace the scientific release of an earlier run.
    out, work = Path(out), Path(work)
    out.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    process = psutil.Process()
    rss = [process.memory_info().rss]
    stop = threading.Event()

    def sample_memory():
        while not stop.wait(0.1):
            rss[0] = max(rss[0], process.memory_info().rss)

    sampler = threading.Thread(target=sample_memory, daemon=True)
    sampler.start()
    try:
        with threadpool_limits(1):
            _run(archive, out, work)
    finally:
        stop.set()
        sampler.join()
    put(
        out / "resources.json",
        {
            "seconds": time.perf_counter() - start,
            "peak_rss_mib_sampled": rss[0] / 2**20,
            "sample_interval_seconds": 0.1,
            "process": "study only",
            "threads_per_pool": 1,
            "logical_cpus_host": psutil.cpu_count(),
            "host_memory_gib": psutil.virtual_memory().total / 2**30,
            "platform": platform.system(),
            "machine": platform.machine(),
        },
    )
    log("study_complete", release=str(out))


def _run(archive, out, work):
    data = source(archive)
    put(out / "profile.json", profile(data))
    split = partitions(data)
    split.to_csv(out / "splits.csv", index=False, lineterminator="\n")
    indexed = data.set_index("ID", drop=False)

    def subset(name):
        return indexed.loc[split.loc[split.split == name, "ID"]]

    train, valid = subset("train"), subset("validation")
    x_train, x_valid = features(train), features(valid)
    client, eid = experiment_tracker(work)
    parent = client.create_run(eid, run_name="historical-policy")
    run_id = parent.info.run_id

    def record(row):
        child = client.create_run(
            eid, run_name=f"{row['kind']}-{row['param']}", tags={"mlflow.parentRunId": run_id}
        )
        cid = child.info.run_id
        client.log_param(cid, "configuration", row["param"])
        client.log_param(cid, "family", row["kind"])
        for m in ("cv_ap", "validation_ap", "validation_brier"):
            client.log_metric(cid, m, row[m])
        client.set_terminated(cid)
        log("validation", family=row["kind"], parameter=row["param"])
        return cid

    try:
        models, freeze = fit_candidates(x_train, train[TARGET], x_valid, valid[TARGET], record)
        model_dir = out / "model"
        model_dir.mkdir()
        for name, model in models.items():
            joblib.dump(model, model_dir / f"{name}.joblib", compress=3)
        hashes = {k: file_hash(model_dir / f"{k}.joblib") for k in models}
        baseline = reference(train)
        put(model_dir / "reference.json", baseline)
        freeze.update(
            model_hashes=hashes,
            split_sha256=file_hash(out / "splits.csv"),
            training_prevalence=float(train[TARGET].mean()),
            feature_names=x_train.columns.tolist(),
            train_feature_sha256=digest(csv_bytes(x_train)),
            train_n=len(train),
            validation_n=len(valid),
        )
        put(out / "selection_frozen.json", freeze)
        client.log_artifact(run_id, str(out / "selection_frozen.json"))
        log("selection_frozen", sha256=file_hash(out / "selection_frozen.json"))
        test = subset("test")
        y = test[TARGET].to_numpy()
        ids = test.ID.to_numpy()
        x_test = features(test)
        pred = {k: v.predict_proba(x_test)[:, 1] for k, v in models.items()}
        pred.update(
            constant=np.full(len(test), freeze["training_prevalence"]),
            rule=test.PAY_0.to_numpy(dtype=float),
        )
        metrics = evaluate(y, pred, ids)
        uncertainty = paired(y, pred, ids)
        verdict = decision(freeze["eligible"], metrics, uncertainty)
        active = verdict["active"]
        selected = np.zeros(len(ids), dtype=bool)
        selected[ranking(pred[active], tie_keys(ids))[: len(ids) * 5 // 100]] = True
        batch = test[BATCH].reset_index(drop=True)
        batch.to_csv(work / "holdout_features.csv", index=False)
        labels = dict(zip(ids, y, strict=True))
        shifted = batch.copy()
        shifted["LIMIT_BAL"] *= 12
        shifted_scores = models[active].predict_proba(features(shifted))[:, 1]
        follow_up = {
            "observed_batch": inspect(batch, pred[active], baseline),
            "synthetic_limit_shift": inspect(shifted, shifted_scores, baseline),
            "simulated_label_delay": [
                delayed_labels(ids, pred[active], labels, d) for d in (7, 30)
            ],
        }
        put(out / "monitor.json", follow_up)
        report = {
            "n": len(test),
            "positives": int(y.sum()),
            "decision": verdict,
            "metrics": metrics,
            "bootstrap": uncertainty,
            "audit_minimum": 100,
            "audit": audit(test[AUDIT], y, pred[active], selected),
            "scenario": {
                "currency": "TWD",
                "lgd_assumption": 0.5,
                "balance_proxy": "max(BILL_AMT1,0)",
                "selected_balance": float(test.loc[selected, BILL[0]].clip(lower=0).sum()),
                "default_selected_balance_times_lgd": float(
                    test.loc[selected & (y == 1), BILL[0]].clip(lower=0).sum() * 0.5
                ),
            },
        }
        put(out / "policy_report.json", report)
        # Only the active, checksum-pinned local model is used by the batch command.
        release = {
            "active": active,
            "sha256": hashes[active],
            "reference_sha256": file_hash(model_dir / "reference.json"),
            "model_version": f"{active}-{hashes[active][:16]}",
            "run_id": run_id,
            "schema_version": "1.0",
            "sklearn": metadata.version("scikit-learn"),
        }
        put(model_dir / "release.json", release)
        git = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent,
                check=False,
            )
            if shutil.which("git")
            else None
        )
        versions = {
            k: metadata.version(k)
            for k in [
                "numpy",
                "pandas",
                "scikit-learn",
                "scipy",
                "mlflow-skinny",
                "psycopg",
                "joblib",
                "xlrd",
                "threadpoolctl",
            ]
        }
        manifest = {
            "run_id": run_id,
            "git_sha": git.stdout.strip() if git and git.returncode == 0 else None,
            "contract_version": "1.0",
            "source_namespace": REAL,
            "data_kind": "real_public",
            "dataset_sha256": SHA,
            "seed": SEED,
            "as_of": AS_OF,
            "rows": len(data),
            "timezone": "unavailable",
            "python": sys.version.split()[0],
            "versions": versions,
            "outputs": {
                p.relative_to(out).as_posix(): file_hash(p)
                for p in sorted(out.rglob("*"))
                if p.is_file()
            },
        }
        put(out / "manifest.json", manifest)
        for key, value in {
            "seed": SEED,
            "data": SHA,
            "capacity_pct": 5,
            "decision": verdict["status"],
        }.items():
            client.log_param(run_id, key, value)
        for name, stats in metrics.items():
            client.log_metric(run_id, f"{name}_ap", stats["ap"])
        for path in [
            out / "manifest.json",
            out / "policy_report.json",
            out / "monitor.json",
            model_dir / "release.json",
            model_dir / f"{active}.joblib",
        ]:
            client.log_artifact(run_id, str(path))
        client.set_terminated(run_id)
        put(
            out / "tracking.json",
            {
                "experiment_id": eid,
                "parent": run_id,
                "status": client.get_run(run_id).info.status,
                "metrics": client.get_run(run_id).data.metrics,
                "params": client.get_run(run_id).data.params,
                "artifacts": [a.path for a in client.list_artifacts(run_id)],
                "children": [r["run_id"] for r in freeze["grid"]],
            },
        )
    except Exception:
        client.set_terminated(run_id, status="FAILED")
        raise
