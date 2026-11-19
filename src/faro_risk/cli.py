import argparse
import json
import sys
from pathlib import Path

import jsonschema
import pandas as pd
import psycopg

from . import batch
from .common import REAL, SIM, file_hash, log, put, read
from .data import BATCH, download, source
from .report import render

DEMO_DATE = "2026-01-31"
DEMO_FILES = ["synthetic.csv", "queue.csv", "demo.json"]


def validate_contract(root, name, data):
    schemas = root / "contracts" / "v1"
    lock = read(root / "contracts.lock.json")
    path = schemas / f"{name}.json"
    if file_hash(path) != lock["sha256"][path.name]:
        raise ValueError("Contrato con huella incompatible")
    jsonschema.validate(
        data, read(path), format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )


def validate(root, release):
    manifest = read(release / "manifest.json")
    validate_contract(root, "run_manifest", manifest)
    for name, expected in manifest["outputs"].items():
        target = (release / name).resolve()
        if not target.is_relative_to(release.resolve()) or file_hash(target) != expected:
            raise ValueError("Artefacto con huella incompatible")
    validate_contract(root, "decision_record", read(release / "policy_report.json")["decision"])
    batch.load_release(release / "model")
    log("validated", files=len(manifest["outputs"]), run_id=manifest["run_id"])


def demo(model_dir, out, root):
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()) and not (out / "demo.json").exists():
        raise ValueError("Use una carpeta de demo nueva o previamente completada")
    _, _, ref = batch.load_release(model_dir)
    fixture = batch.demo_batch(ref)
    fixture.to_csv(out / "synthetic.csv", index=False)
    with batch.fetch_connection() as conn:
        batch.initialize(conn)
        initial = batch.publish(conn, fixture, model_dir, SIM, DEMO_DATE)
        repeat = batch.publish(conn, fixture.iloc[::-1], model_dir, SIM, DEMO_DATE)
        queue = batch.queue(conn, SIM, DEMO_DATE)
        changed = fixture.copy()
        changed["LIMIT_BAL"] *= 12
        shifted = batch.publish(conn, changed, model_dir, SIM, "2026-02-28")
        try:
            batch.publish(
                conn, fixture.rename(columns={"PAY_0": "new_status"}), model_dir, SIM, "2026-03-31"
            )
        except ValueError as exc:
            blocked = str(exc)
        else:
            raise RuntimeError("El contrato incompatible se publicó")
        if (
            initial["status"] not in {"published", "replay"}
            or repeat["status"] != "replay"
            or len(queue) != len(fixture) * 5 // 100
            or shifted["status"] != "suspended"
        ):
            raise RuntimeError("Falló la verificación de la demo")
        for row in queue:
            validate_contract(root, "risk_score", {k: v for k, v in row.items() if k != "position"})
        pd.DataFrame(queue).to_csv(out / "queue.csv", index=False)
        result = {
            "product": "faro-risk-policy",
            "data_kind": "synthetic",
            "initial": initial,
            "repeat": repeat["status"],
            "queue_rows": len(queue),
            "first_account": queue[0],
            "shift": shifted,
            "schema_blocked": blocked,
        }
        put(out / "demo.json", result)
    log("demo_complete", rows=len(fixture), queue=len(queue), shift=shifted["status"])


def main(argv=None):
    p = argparse.ArgumentParser(prog="faro-risk")
    p.add_argument(
        "--root", type=Path, default=Path.cwd(), help="repository root with versioned contracts"
    )
    subs = p.add_subparsers(dest="cmd", required=True)

    def directory(c, name, default):
        c.add_argument("--" + name, type=Path, default=Path(default))

    c = subs.add_parser("download")
    directory(c, "zip", "local/uci.zip")
    c = subs.add_parser("study")
    directory(c, "zip", "local/uci.zip")
    directory(c, "release", "local/release")
    directory(c, "work", "local/study")
    c = subs.add_parser("export-holdout")
    directory(c, "zip", "local/uci.zip")
    directory(c, "release", "reports/release")
    directory(c, "out", "local/holdout.csv")
    for cmd in ["demo", "validate", "report", "score", "queue", "clean"]:
        c = subs.add_parser(cmd)
        if cmd in {"demo", "score", "report", "validate"}:
            directory(c, "release", "reports/release")
        if cmd in {"demo", "clean"}:
            directory(c, "out", "local/demo")
        if cmd == "clean":
            c.add_argument("--confirm", action="store_true", required=True)
        if cmd in {"score", "queue"}:
            c.add_argument("--namespace", choices=[REAL, SIM], required=True)
            c.add_argument("--as-of", required=True)
            c.add_argument("--out", type=Path, required=True)
        if cmd == "score":
            c.add_argument("--csv", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.cmd == "download":
            download(args.zip)
        elif args.cmd == "study":
            from .study import study

            study(args.zip, args.release, args.work)
            render(args.release)
        elif args.cmd == "export-holdout":
            split = args.release / "splits.csv"
            if file_hash(split) != read(args.release / "selection_frozen.json")["split_sha256"]:
                raise ValueError("Split alterado")
            ids = pd.read_csv(split).query("split=='test'")["ID"]
            frame = source(args.zip).set_index("ID", drop=False).loc[ids, BATCH]
            args.out.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(args.out, index=False)
        elif args.cmd == "demo":
            demo(args.release / "model", args.out, args.root)
        elif args.cmd == "validate":
            validate(args.root, args.release)
        elif args.cmd == "report":
            render(args.release)
        elif args.cmd == "clean":
            if read(args.out / "demo.json").get("product") != "faro-risk-policy":
                raise ValueError("Directorio de demo incompatible")
            for name in DEMO_FILES:
                (args.out / name).unlink(missing_ok=True)
        else:
            with batch.fetch_connection() as conn:
                if args.cmd == "queue":
                    rows = batch.queue(conn, args.namespace, args.as_of)
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    pd.DataFrame(
                        rows,
                        columns=[
                            "namespace",
                            "as_of",
                            "account_id",
                            "score",
                            "model_version",
                            "feature_snapshot_id",
                            "data_kind",
                            "position",
                        ],
                    ).to_csv(args.out, index=False)
                    log("queue_exported", rows=len(rows))
                else:
                    batch.initialize(conn)
                    outcome = batch.publish(
                        conn,
                        batch.read_batch(args.csv),
                        args.release / "model",
                        args.namespace,
                        args.as_of,
                    )
                    put(args.out, outcome)
                    log("batch", status=outcome["status"], rows=outcome["rows"])
                    if outcome["status"] == "suspended":
                        return 3
    except psycopg.Error as exc:
        log("database_error", error=type(exc).__name__, sqlstate=exc.sqlstate)
        return 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError, jsonschema.ValidationError) as exc:
        log("error", message=str(exc))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
