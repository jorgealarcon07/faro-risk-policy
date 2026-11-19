# Caso de estudio · 300 revisiones para 6.000 cuentas

**Decisión.** Una jefa de operaciones debe repartir una cola diaria y explicar por qué una cuenta entró. El responsable de riesgo, por su parte, necesita decidir si promueve una nueva versión. Ambas decisiones comparten datos, pero sus métricas pueden favorecer modelos distintos. [Informe de la decisión](reports/release/policy_report.html)

## Del dato a la cola

Validé la versión del XLS de UCI, separé las cuentas antes de ajustar transformaciones y conservé sus particiones. Tomé el último atraso como regla operativa, la prevalencia como referencia probabilística y una regresión logística como modelo de comparación. Entrené un único tipo de candidato no lineal. La validación seleccionó una de dos configuraciones y el protocolo dejó fijado qué mejora exigirle antes de consultar test. [Selección previa](reports/release/selection_frozen.json)

El batch recibe un CSV sin etiquetas ni demografía, genera probabilidades y ejecuta controles de calidad. La transacción publica los scores con fecha, fuente, versión y huella de entrada. PostgreSQL expone el primer 5 % por una vista. El responsable puede reproducir cualquier posición a partir del snapshot. [Primera cuenta, concurrencia y consistencia SQL](reports/acceptance.json)

## Qué ocurrió

En 6.000 cuentas hubo 1.327 impagos. El boosting encontró 227 en 300 posiciones, precisión de 75,7 % y captura de 17,1 %. Con las mismas 300 revisiones la logística encontró 232 y la regla 215. La diferencia global de AP frente a logística tuvo un límite inferior positivo y el Brier mejoró, por lo que se registró `promote`. A capacidad fija, el IC del lift frente a la regla incluye 1. Estas cifras describen concentración de impagos históricos. El dataset carece de un tratamiento y un resultado contrafactual con los que estimar cobros adicionales. [Métricas e intervalos](reports/release/policy_report.json)

| Capacidad | Revisiones | Impagos observados | Captura de todos los impagos |
|---|---:|---:|---:|
| 2 % | 120 | 95 | 7,2 % |
| 5 % | 300 | 227 | 17,1 % |
| 10 % | 600 | 429 | 32,3 % |

El estudio tardó 22,42 s sobre CPU en la máquina registrada. El máximo RSS muestreado del proceso fue 280,3 MiB. La entrada fue el ZIP ya descargado. Instalación, PostgreSQL y captura de medios quedan fuera de esa medición. [Recursos](reports/release/resources.json)

## Qué cambiaría una decisión real

Si operaciones solo valora los primeros 300 puestos, debería definir ese objetivo antes de una evaluación prospectiva. Elegir de nuevo el modelo que ganó en ese corte del test reutilizaría información de evaluación. Otra cohorte permitiría confirmar estabilidad y calibración. Datos de las acciones y sus resultados permitirían estudiar si revisar una cuenta cambia lo que ocurre.

El ensayo operativo reveló una necesidad distinta. Enviar dos veces el mismo lote debe producir una sola publicación incluso cuando las solicitudes llegan juntas. Los dos envíos concurrentes produjeron una publicación y un replay. Cambiar los límites en la demo activó la suspensión. El esquema incompatible falló antes de persistir scores. [Prueba de recuperación](reports/demo.json) · [Resultados SQL](reports/acceptance.json)

## Material para el portafolio

[Video narrado en inglés](assets/web/walkthrough.mp4) · [Transcripción](assets/web/walkthrough.en.txt) · [Captura de la decisión](assets/web/decision.png) · [Capacidad y calibración](assets/web/capacidad.png) · [Auditoría](assets/web/auditoria.png) · [Modelo y límites de uso](model_card.md).
