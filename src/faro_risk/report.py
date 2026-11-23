from base64 import b64encode
from html import escape
from io import BytesIO
from pathlib import Path
from string import Template

from .common import file_hash, put, read
from .report_language import REPORT_FILES, labels, localize


def promotion_labels(text):
    return {
        "validation_eligible": text["py_validation"],
        "higher_ap": text["py_higher_ap"],
        "ap_lower_bound_positive": text["py_lower_bound"],
        "brier_no_worse": text["py_brier"],
    }


def table(headers, rows):
    heads = "".join(f'<th scope="col">{escape(str(c))}</th>' for c in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(x))}</td>" for x in row) + "</tr>" for row in rows
    )
    return f'<div class="scroll"><table><thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></div>'


def render(folder):
    """Write the decision record and both presentation views."""
    folder = Path(folder)
    report = read(folder / "policy_report.json")
    verdict = report["decision"]
    active = verdict["active"]
    main = report["metrics"][active]["capacity"]["5"]
    boot = report["bootstrap"]
    gates = promotion_labels(labels("es"))
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
    render_pages(folder, save_figure=True)


def render_pages(folder, *, languages=REPORT_FILES, save_figure=False):
    """Render both locales from the same saved evaluation and monitoring data."""
    from .figures import calibration as plot_calibration

    folder = Path(folder)
    report = read(folder / "policy_report.json")
    follow = read(folder / "monitor.json")
    template = (Path(__file__).with_name("templates") / "report.html").read_text(encoding="utf-8")
    for language in languages:
        buffer = BytesIO()
        plot_calibration(report, buffer, language)
        figure = buffer.getvalue()
        if save_figure and language == "es":
            (folder / "calibration.png").write_bytes(figure)
        copy = localize(template, language)
        content = Template(copy).substitute(page_values(report, follow, figure, language))
        (folder / REPORT_FILES[language]).write_text(content, encoding="utf-8", newline="\n")


def page_values(report, follow, figure, language):
    text = labels(language)

    def rounded(value, digits):
        number = f"{value:,.{digits}f}"
        return number.translate(str.maketrans(".,", ",.")) if language == "es" else number

    def percent(value, digits=0):
        gap = " " if language == "es" else ""
        return f"{rounded(value, digits)}{gap}%"

    def fmt(value, mode="decimal"):
        if value is None:
            return "—"
        return percent(100 * value, 1) if mode == "pct" else rounded(value, 4)

    def ci(bounds, mode="decimal"):
        return " – ".join(fmt(x, mode) for x in bounds)

    metrics, boot, verdict = report["metrics"], report["bootstrap"], report["decision"]
    active = verdict["active"]
    main = metrics[active]["capacity"]["5"]
    rule = metrics["rule"]["capacity"]["5"]
    names = {name: text[f"py_{name}"] for name in ("logistic", "boost", "rule", "constant")}
    order = ["rule", "logistic", "boost", "constant"]
    comparison = table(
        [text["py_method"], "AP", "ROC-AUC", "Brier", "Log loss", text["py_queued"]],
        [
            [
                names[n],
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
            text["py_capacity"],
            text["py_reviews"],
            text["py_defaults"],
            text["py_precision"],
            text["py_capture"],
            text["py_lift"],
        ],
        [
            [
                percent(float(p)),
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
        [text["py_score_band"], text["py_accounts"], text["py_prediction"], text["py_observed"]],
        [
            [
                f"{rounded(b['bin'] / 10, 1)} – {rounded((b['bin'] + 1) / 10, 1)}",
                b["n"],
                fmt(b["predicted"], "pct"),
                fmt(b["observed"], "pct"),
            ]
            for b in metrics[active]["calibration"]
        ],
    )
    audit = table(
        [
            text["py_variable"],
            text["py_group"],
            text["py_accounts"],
            text["py_selection"],
            text["py_simple_capture"],
            text["py_gap"],
        ],
        [
            [
                text.get(f"py_field_{row['field'].lower()}", row["field"]),
                row["group"],
                row["n"],
                fmt(row.get("selection"), "pct"),
                fmt(row.get("recall"), "pct"),
                text["py_suppressed"]
                if row["suppressed"]
                else fmt(row["calibration_gap"], "pct")
                + " · "
                + ci(row["calibration_gap_ci"], "pct"),
            ]
            for row in report["audit"]
        ],
    )
    gates = promotion_labels(text)
    gate_table = table(
        [text["py_condition"], text["py_result"]],
        [
            [label, text["py_pass"] if verdict["checks"][k] else text["py_fail"]]
            for k, label in gates.items()
        ],
    )
    values = {
        "main": names[active],
        "verdict": text["py_promote"] if active == "boost" else text["py_retain"],
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
        "figure": b64encode(figure).decode("ascii"),
        "audit": audit,
        "gates": gate_table,
        "alert": escape(
            ", ".join(
                text.get(f"py_alert_{code}", code)
                for code in follow["synthetic_limit_shift"]["alerts"]
            )
        ),
        "case_amount": rounded(report["scenario"]["default_selected_balance_times_lgd"], 1),
    }
    return values
