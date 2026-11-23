"""Localized labels for the offline report."""

import re
from html import escape

COPY = {
    "text_title": ("Faro · Política de revisión de cuentas", "Faro · Account review policy"),
    "text_brand": ("FARO / OPERACIONES DE RIESGO", "FARO / RISK OPERATIONS"),
    "text_heading": (
        "¿Qué cuentas entran en revisión?",
        "Which accounts should the risk team review?",
    ),
    "text_intro": (
        "Una mesa de riesgo tiene capacidad para revisar el 5 % del lote. Este ensayo "
        "mide cuántos impagos históricos concentra esa decisión en una cohorte de "
        "tarjetas de Taiwán.",
        "A risk team can review 5% of the batch. This evaluation measures how many "
        "observed defaults would enter that queue in a historical Taiwanese credit card "
        "cohort.",
    ),
    "text_sections": ("Secciones", "Sections"),
    "text_decision": ("Decisión", "Decision"),
    "text_models": ("Modelos", "Models"),
    "text_capacity": ("Capacidad", "Capacity"),
    "text_audit": ("Auditoría", "Audit"),
    "text_monitoring": ("Seguimiento", "Monitoring"),
    "text_active": ("La política activa usa", "The active policy uses"),
    "text_rule": (
        ". A igual capacidad, la regla que prioriza el último atraso encontró",
        ". At the same capacity, the rule based on the most recent payment delay surfaced",
    ),
    "text_observed": ("impagos observados.", "observed defaults."),
    "text_reviewable": ("cuentas revisables de $n", "accounts reviewed out of $n"),
    "text_hits": ("impagos dentro de la cola", "observed defaults in the queue"),
    "text_share": ("de los $pos impagos del lote", "of the $pos observed defaults in the batch"),
    "text_ap": (
        "La diferencia de precisión promedio (AP) entre boosting y logística fue",
        "The difference in average precision (AP) between boosting and logistic regression was",
    ),
    "text_ap_ci": (", con IC 95 % pareado de", ", with a paired 95% confidence interval of"),
    "text_frozen": (
        ". El criterio de promoción se congeló antes de evaluar el test.",
        ". The promotion criterion was fixed before evaluation on the test set.",
    ),
    "text_lr": (
        "En las primeras $k revisiones, la logística encontró",
        "Among the top $k accounts, logistic regression surfaced",
    ),
    "text_lift": (
        "impagos. El intervalo del lift de la política activa frente a la regla fue",
        "observed defaults. The confidence interval for the active policy's lift over the "
        "baseline rule was",
    ),
    "text_metric_goal": (
        "(1 indica empate). La concentración en esta cola y la calidad global del "
        "ranking responden a preguntas distintas.",
        "(1 indicates a tie). Queue concentration and overall ranking quality "
        "answer different questions.",
    ),
    "text_show_gates": ("Ver condiciones de promoción", "View promotion criteria"),
    "text_compare": ("Comparación sobre las mismas cuentas", "Comparison on the same accounts"),
    "text_compare_note": (
        "AP y ROC-AUC evalúan el orden. Brier y log loss evalúan probabilidades y "
        "favorecen valores pequeños. La regla de mora entrega un orden sin "
        "probabilidad asociada.",
        "AP and ROC-AUC evaluate ranking. Brier score and log loss evaluate "
        "predicted probabilities, with lower values preferred. The "
        "overdue-payment rule produces a ranking.",
    ),
    "text_capacity_heading": ("Rendimiento por capacidad", "Performance by review capacity"),
    "text_bootstrap": (
        "Precisión es la fracción de revisiones con impago. Captura es la fracción "
        "de todos los impagos presentes en la cola. Los intervalos remuestrean "
        "cuentas y reconstruyen la cola en 1.000 réplicas pareadas.",
        "Precision is the share of reviewed accounts that defaulted. Capture is the "
        "share of all defaults in the queue. The intervals resample accounts and "
        "rebuild the queue in 1,000 paired replicates.",
    ),
    "text_show_calibration": ("Ver calibración por banda", "View calibration by score band"),
    "text_figure_alt": (
        "Fiabilidad de logística y boosting y tamaño de cada banda. Valores del "
        "modelo activo en la tabla.",
        "Calibration of logistic regression and boosting, with counts per score "
        "band. The table shows values for the active model.",
    ),
    "text_money_scenario": ("Escenario monetario en TWD", "Illustrative balance scenario (TWD)"),
    "text_money_note": (
        "Sumar el saldo de septiembre truncado en cero de las cuentas revisadas con "
        "impago y aplicar un LGD supuesto del 50 % produce $case_amount TWD. La "
        "fuente carece de exposición al impago, costo real y efecto de revisar la "
        "cuenta. Esta cifra describe un escenario retrospectivo.",
        "Adding the nonnegative September balances for reviewed accounts that "
        "defaulted and applying an assumed 50% loss given default yields "
        "$case_amount TWD. The source lacks exposure at default, actual costs and "
        "the effect of review. This is a retrospective scenario.",
    ),
    "text_audit_heading": ("Auditoría por grupo", "Audit by group"),
    "text_audit_note": (
        "Sexo, educación, estado civil y edad quedaron fuera del modelo. El informe "
        "suprime tasas en grupos de menos de 100 cuentas. Los grupos se solapan "
        "entre variables.",
        "The model excluded sex, education, marital status and age. The report "
        "suppresses rates for groups with fewer than 100 accounts. Groups overlap "
        "across variables.",
    ),
    "text_show_audit": ("Inspeccionar grupos y tamaños", "Inspect groups and sample sizes"),
    "text_residual": (
        "¹ Predicción media menos frecuencia observada. Intervalo normal de la media "
        "del residual. El JSON incluye intervalos de Wilson para selección y captura.",
        "¹ Mean prediction minus observed default rate, with a normal interval for "
        "the mean residual. The JSON includes Wilson intervals for selection and "
        "capture.",
    ),
    "text_monitor_heading": ("Publicar o suspender un lote", "Publish or suspend a batch"),
    "text_monitor_first": (
        "El lote histórico pasó el monitor. Al multiplicar por 12 los límites en "
        "una copia de ensayo se activó",
        "The historical batch passed monitoring. Multiplying the credit limits "
        "by 12 in a test copy triggered",
    ),
    "text_monitor_second": (
        ". En el escenario de demora, el día 7 las etiquetas están pendientes y "
        "el día 30 pueden evaluarse.",
        ". In the delayed-label scenario, outcomes are pending on day 7 and can "
        "be evaluated on day 30.",
    ),
    "text_limits": (
        "La evaluación usa octubre de 2005 como horizonte de impago. Una cohorte "
        "histórica no permite estimar el efecto de una intervención ni validar la "
        "política para Colombia.",
        "October 2005 is the default window. Estimating the effect of an intervention "
        "or validating the policy for Colombia would require new evidence.",
    ),
    "text_metrics": ("Métricas e intervalos", "Metrics and confidence intervals"),
    "text_frozen_selection": ("Selección congelada", "Frozen model selection"),
    "text_manifest": ("Manifiesto", "Manifest"),
    "text_monitor": ("Monitor", "Monitoring data"),
    "text_attribution": (
        "Datos de I-Cheng Yeh · UCI Machine Learning Repository · CC BY 4.0.",
        "Data from I-Cheng Yeh · UCI Machine Learning Repository · CC BY 4.0.",
    ),
    "text_source": ("Fuente original", "Original data source"),
    "py_logistic": ("Regresión logística", "Logistic regression"),
    "py_boost": ("Boosting calibrado", "Calibrated gradient boosting"),
    "py_rule": ("Regla de mora", "Overdue-payment rule"),
    "py_constant": ("Prevalencia constante", "Constant prevalence"),
    "py_method": ("Método", "Method"),
    "py_queued": ("Impagos en cola (5 %)", "Defaults in queue (5%)"),
    "py_capacity": ("Capacidad", "Capacity"),
    "py_reviews": ("Revisiones", "Reviews"),
    "py_defaults": ("Impagos", "Observed defaults"),
    "py_precision": ("Precisión (IC 95 %)", "Precision (95% CI)"),
    "py_capture": ("Captura (IC 95 %)", "Capture (95% CI)"),
    "py_lift": ("Lift / regla", "Lift over baseline rule"),
    "py_score_band": ("Intervalo de score", "Score band"),
    "py_accounts": ("Cuentas", "Accounts"),
    "py_prediction": ("Predicción media", "Mean prediction"),
    "py_observed": ("Impago observado", "Observed default rate"),
    "py_variable": ("Variable", "Variable"),
    "py_group": ("Grupo", "Group"),
    "py_selection": ("Selección", "Selection"),
    "py_simple_capture": ("Captura", "Capture"),
    "py_gap": ("Brecha media¹ (IC 95 %)", "Mean gap¹ (95% CI)"),
    "py_suppressed": ("Suprimido", "Suppressed"),
    "py_validation": ("Elegible en validación", "Eligible on the validation set"),
    "py_higher_ap": ("AP mayor que logística", "Higher AP than logistic regression"),
    "py_lower_bound": (
        "Límite inferior de la diferencia de AP superior a cero",
        "Lower confidence bound for the AP gain above zero",
    ),
    "py_brier": (
        "Brier igual o menor que logística",
        "Brier score at most that of logistic regression",
    ),
    "py_condition": ("Condición predefinida", "Prespecified condition"),
    "py_result": ("Resultado", "Result"),
    "py_pass": ("Cumple", "Pass"),
    "py_fail": ("Falla", "Fail"),
    "py_promote": ("Promover el candidato", "Promote the candidate"),
    "py_retain": ("Mantener la logística", "Keep logistic regression"),
    "py_ideal": ("Calibración ideal", "Perfect calibration"),
    "py_figure_logistic": ("Logística", "Logistic regression"),
    "py_figure_boost": ("Boosting", "Gradient boosting"),
    "py_figure_predicted": ("Probabilidad media estimada", "Mean predicted probability"),
    "py_figure_observed": ("Fracción con impago", "Observed default rate"),
    "py_figure_validation": ("Calibración en test", "Holdout calibration"),
    "py_figure_band": ("Banda del score", "Score band"),
    "py_figure_active": ("Soporte del modelo activo", "Active model counts"),
    "py_field_sex": ("Sexo (SEX)", "Sex (SEX)"),
    "py_field_marriage": ("Estado civil (MARRIAGE)", "Marital status (MARRIAGE)"),
    "py_field_education": ("Educación (EDUCATION)", "Education (EDUCATION)"),
    "py_field_age": ("Edad (AGE)", "Age (AGE)"),
    "py_alert_shift:LIMIT_BAL": (
        "shift:LIMIT_BAL",
        "a credit limit distribution shift (shift:LIMIT_BAL)",
    ),
}


REPORT_FILES = {"es": "policy_report.html", "en": "policy_report.en.html"}


def labels(language):
    if language not in REPORT_FILES:
        raise ValueError(f"Unsupported report language: {language}")
    column = 0 if language == "es" else 1
    return {key: pair[column] for key, pair in COPY.items()}


def localize(template, language):
    copy = labels(language)
    alternate = "en" if language == "es" else "es"
    html = {
        **{key: escape(value) for key, value in copy.items()},
        "lang": language,
        "other_lang": alternate,
        "other_file": REPORT_FILES[alternate],
        "other_label": "English" if alternate == "en" else "Español",
    }

    return re.sub(r"@@([a-z_]+)@@", lambda match: html[match[1]], template)
