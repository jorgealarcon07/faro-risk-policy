# Model card · boost-f3559198b5ca4841

**Propósito.** Ordenar para revisión humana simulada cuentas existentes en el cierre de septiembre de 2005. La etiqueta es el impago registrado el mes siguiente. Fecha de corte analítica 2005-09-30, sin instante puntual ni zona horaria verificable. Unidad de decisión por cuenta y snapshot. [Artefacto activo](reports/release/model/release.json)

**Población.** 30.000 cuentas de tarjeta de Taiwán en UCI. Split estratificado por cuenta, semilla 2026, con 18.000 cuentas para ajustar, 6.000 para elegir y 6.000 para test. 1.327 positivos en test. Una sola cohorte impide medir deterioro temporal o deriva geográfica. La etiqueta y los identificadores de persona quedan fuera de la matriz predictora. [Particiones](reports/release/splits.csv) · [Fuente y licencia](DATA_SOURCES.md)

**Ajuste.** HistGradientBoostingClassifier con 15 hojas como máximo, 80 iteraciones, tasa 0,08 y regularización L2 de 2. Sigmoide aprendida con predicciones out-of-fold dentro de entrenamiento y estimador final reajustado sobre ese entrenamiento. Comparador logístico con C = 0,1. Prevalencia natural. Preprocesamiento dentro de los folds. Las cinco configuraciones y sus AP por fold se conservan en la selección congelada. [Selección y huellas](reports/release/selection_frozen.json)

| Modelo | AP | ROC-AUC | Brier | Impagos / 300 |
|---|---:|---:|---:|---:|
| Probabilidad constante | 0,2212 | 0,5000 | 0,1723 | 75 |
| Último atraso | 0,4580 | 0,7115 | — | 215 |
| Regresión logística | 0,5427 | 0,7769 | 0,1346 | 232 |
| Boosting calibrado | 0,5615 | 0,7881 | 0,1323 | 227 |

**Decisión.** Promoción en el laboratorio según el criterio anterior al test. Diferencia de AP frente a logística +0,01886, con IC pareado 95 % [0,00452, 0,03224]. El Brier disminuyó 0,00222. La capacidad del 5 % deja fuera a 1.100 impagos históricos del lote. El IC del lift respecto a la regla de mora [0,9864, 1,1408] incluye el empate. [Evaluación completa](reports/release/policy_report.json)

**Auditoría.** SEX, EDUCATION, MARRIAGE y AGE se reservan a la auditoría. Entre 30 y 39 años entraron 91 de 2.265 cuentas (4,02 %) y entre 40 y 49 años, 83 de 1.270 (6,54 %). Se suprimen tasas de subgrupos con menos de 100 cuentas. Se reportan Wilson para proporciones y un intervalo normal para el residual medio de calibración. Los intervalos son descriptivos por grupo, sin ajuste por comparaciones múltiples. Otras variables pueden actuar como proxies. La evidencia resulta insuficiente para certificar equidad.

**Uso permitido en el proyecto.** Evaluación educativa delegada a una mesa de revisión ficticia, scoring batch y ensayos de fallos. Quedan fuera aprobación o rechazo de crédito, fijación de precios, cobros automatizados y decisiones sobre personas reales. Las probabilidades, el saldo y un LGD hipotético carecen de validación para estimar ahorro, efecto causal o pérdida regulatoria. Ante cambios de población o de la definición del resultado se necesita evaluación externa. [Runbook](docs/RUNBOOK.md)
