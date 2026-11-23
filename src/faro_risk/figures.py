"""Render reliability diagrams from the saved evaluation without scoring the holdout."""

import matplotlib as mpl
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from .report_language import labels


def calibration(report, output, language="es"):
    text = labels(language)
    with mpl.rc_context({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}):
        fig = Figure(figsize=(8.6, 3.8), dpi=150, layout="constrained", facecolor="white")
        FigureCanvasAgg(fig)
        curve, counts = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1.2, 1]})
        curve.plot([0, 1], [0, 1], "--", color="#8e9e99", lw=1, label=text["py_ideal"])
        for name, label, color, marker in [
            ("logistic", text["py_figure_logistic"], "#ad632e", "s"),
            ("boost", text["py_figure_boost"], "#086a62", "o"),
        ]:
            nonempty = [b for b in report["metrics"][name]["calibration"] if b["n"]]
            curve.plot(
                [b["predicted"] for b in nonempty],
                [b["observed"] for b in nonempty],
                marker=marker,
                lw=1.4,
                ms=4,
                color=color,
                label=label,
            )
            for b in nonempty:
                if b["n"] < 10:
                    curve.annotate(
                        f"n = {b['n']}",
                        (b["predicted"], b["observed"]),
                        xytext=(-30, 8),
                        textcoords="offset points",
                        fontsize=8,
                        color=color,
                    )
        curve.set(
            xlim=(0, 1),
            ylim=(0, 1),
            xlabel=text["py_figure_predicted"],
            ylabel=text["py_figure_observed"],
            title=text["py_figure_validation"],
        )
        curve.legend(loc="upper left", fontsize=8, frameon=False)
        bins = report["metrics"][report["decision"]["active"]]["calibration"]
        counts.bar(
            [(b["bin"] + 0.5) / 10 for b in bins],
            [b["n"] for b in bins],
            width=0.083,
            color="#54877b",
        )
        counts.set(
            xlim=(0, 1),
            xlabel=text["py_figure_band"],
            ylabel=text["py_accounts"],
            title=text["py_figure_active"],
        )
        for ax in [curve, counts]:
            ax.grid(axis="y", alpha=0.14)
            ax.set_axisbelow(True)
        fig.savefig(output, format="png")
