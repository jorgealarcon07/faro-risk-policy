from html import escape
from pathlib import Path

from .common import file_hash, put, read

NAMES = {
    "logistic": "Regresión logística",
    "boost": "Boosting calibrado",
    "rule": "Regla de mora",
    "constant": "Prevalencia constante",
}


def fmt(value, mode="decimal"):
    if value is None:
        return "—"
    if mode == "pct":
        return f"{100 * value:.1f} %".replace(".", ",")
    return f"{value:.4f}".replace(".", ",")


def ci(bounds, mode="decimal"):
    return " – ".join(fmt(x, mode) for x in bounds)


def table(headers, rows):
    heads = "".join(f'<th scope="col">{escape(str(c))}</th>' for c in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(x))}</td>" for x in row) + "</tr>" for row in rows
    )
    return f'<div class="scroll"><table><thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></div>'


def render(folder):
    folder = Path(folder)
    report = read(folder / "policy_report.json")
    follow = read(folder / "monitor.json")
    metrics, boot, verdict = report["metrics"], report["bootstrap"], report["decision"]
    active = verdict["active"]
    main = metrics[active]["capacity"]["5"]
    rule = metrics["rule"]["capacity"]["5"]
    order = ["rule", "logistic", "boost", "constant"]
    comparison = table(
        ["Método", "AP", "ROC-AUC", "Brier", "Log loss", "Impagos en cola (5 %)"],
        [
            [
                NAMES[n],
                fmt(metrics[n]["ap"]),
                fmt(metrics[n]["roc_auc"]),
                fmt(metrics[n].get("brier")),
                fmt(metrics[n].get("log_loss")),
                metrics[n]["capacity"]["5"]["hits"],
            ]
            for n in order
        ],
    )
    capacity = table(
        [
            "Capacidad",
            "Revisiones",
            "Impagos",
            "Precisión (IC 95 %)",
            "Captura (IC 95 %)",
            "Lift / regla",
        ],
        [
            [
                f"{p} %",
                row["k"],
                row["hits"],
                fmt(row["precision"], "pct")
                + " · "
                + ci(boot["capacity"][active][p]["precision"], "pct"),
                fmt(row["recall"], "pct")
                + " · "
                + ci(boot["capacity"][active][p]["recall"], "pct"),
                fmt(row["lift_vs_rule"]),
            ]
            for p in ["2", "5", "10"]
            if (row := metrics[active]["capacity"][p])
        ],
    )
    calibration = table(
        ["Intervalo de score", "Cuentas", "Predicción media", "Impago observado"],
        [
            [
                f"{b['bin'] / 10:.1f} – {(b['bin'] + 1) / 10:.1f}",
                b["n"],
                fmt(b["predicted"], "pct"),
                fmt(b["observed"], "pct"),
            ]
            for b in metrics[active]["calibration"]
        ],
    )
    audit = table(
        ["Variable", "Grupo", "Cuentas", "Selección", "Captura", "Brecha media¹ (IC 95 %)"],
        [
            [
                row["field"],
                row["group"],
                row["n"],
                fmt(row.get("selection"), "pct"),
                fmt(row.get("recall"), "pct"),
                "Suprimido"
                if row["suppressed"]
                else fmt(row["calibration_gap"], "pct")
                + " · "
                + ci(row["calibration_gap_ci"], "pct"),
            ]
            for row in report["audit"]
        ],
    )
    gates = {
        "validation_eligible": "Elegible en validación",
        "higher_ap": "AP mayor que logística",
        "ap_lower_bound_positive": "Límite inferior de la diferencia de AP superior a cero",
        "brier_no_worse": "Brier igual o menor que logística",
    }
    gate_table = table(
        ["Condición predefinida", "Resultado"],
        [[label, "Cumple" if verdict["checks"][k] else "Falla"] for k, label in gates.items()],
    )
    manifest = read(folder / "manifest.json")
    put(
        folder / "decision_record.json",
        {
            **verdict,
            "run_id": manifest["run_id"],
            "as_of": manifest["as_of"],
            "reason": [
                label
                for key, label in gates.items()
                if verdict["checks"][key] == (active == "boost")
            ],
            "accounts": report["n"],
            "positives": report["positives"],
            "capacity_pct": 5,
            "hits_at_capacity": main["hits"],
            "review_slots": main["k"],
            "delta_ap_ci95": boot["ap_boost_minus_logistic"],
            "scenario_assumptions": report["scenario"],
            "evidence": {
                name: file_hash(folder / name)
                for name in ["selection_frozen.json", "policy_report.json", "manifest.json"]
            },
        },
    )
    values = {
        "main": NAMES[active],
        "verdict": "Promover el candidato" if active == "boost" else "Mantener la logística",
        "hits": main["hits"],
        "k": main["k"],
        "n": report["n"],
        "pos": report["positives"],
        "rule": rule["hits"],
        "lr_hits": metrics["logistic"]["capacity"]["5"]["hits"],
        "lift_ci": ci(boot["capacity"][active]["5"]["lift_vs_rule"]),
        "delta": fmt(metrics["boost"]["ap"] - metrics["logistic"]["ap"]),
        "ci": ci(boot["ap_boost_minus_logistic"]),
        "recall": fmt(main["recall"], "pct"),
        "comparison": comparison,
        "capacity": capacity,
        "calibration": calibration,
        "audit": audit,
        "gates": gate_table,
        "alert": escape(", ".join(follow["synthetic_limit_shift"]["alerts"])),
        "case_amount": f"{report['scenario']['default_selected_balance_times_lgd']:,.0f}".replace(
            ",", "."
        ),
    }
    from string import Template

    template = (Path(__file__).with_name("templates") / "report.html").read_text(encoding="utf-8")
    (folder / "policy_report.html").write_text(
        Template(template).substitute(values), encoding="utf-8"
    )
