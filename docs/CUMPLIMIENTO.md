# Verificación de la entrega · 19 de noviembre de 2026

| Práctica | Evidencia comprobable |
|---|---|
| Estándar anterior al código | Primer commit `9f36ad4`. [Estándar](../ESTANDARES_INGENIERIA.md) |
| Arquitectura y contrato | Fronteras de entrenamiento, inferencia, auditoría y consumo. [Arquitectura](ARQUITECTURA.md) · [Esquemas](../contracts/v1) |
| Fuente y calidad | SHA del ZIP validado. 30.000 cuentas con ID único, perfil de faltantes, categorías adicionales y saldos negativos. [Perfil](../reports/release/profile.json) · [Licencia](../DATA_SOURCES.md) |
| Prevención de fuga | Atributos permitidos por lista, splits persistidos, prueba de invariancia ante cambios de target y demografía, mediana ajustada solo en train. [Pruebas](../tests/test_data.py) · [Split](../reports/release/splits.csv) |
| Validación y trazabilidad | Cinco folds internos, una selección congelada previa a test, 1.000 réplicas pareadas, un run padre y cinco hijos finalizados. [Selección](../reports/release/selection_frozen.json) · [Exportación MLflow](../reports/release/tracking.json) |
| Reproducibilidad | Reajuste de los cinco candidatos con train/validación. Mismos parámetros elegidos, huella de features e IDs idénticos y diferencia máxima de probabilidades 0 en los dos modelos congelados. [Refit](../reports/refit.json) |
| Métrica de negocio | 300 posiciones en PostgreSQL, 227 positivos verificados tras la unión posterior con etiquetas. [Evaluación](../reports/release/policy_report.json) · [Cola](../reports/queue.csv) |
| Persistencia y seguridad | Rollback antes del commit, replay con orden alterado, colisión, doble envío concurrente, lectura autorizada de cola y rechazo real del acceso lector a la tabla privada. [Aceptación](../reports/acceptance.json) |
| Operación | CLI con códigos de salida y diagnóstico JSON, bloqueos ante esquema incompatible y shift, reporte de etiquetas demoradas, reintento tras fallo de demo. [Caso adverso](../reports/demo.json) · [Runbook](RUNBOOK.md) |
| Pruebas, CI y entorno | 35 casos de pytest con PostgreSQL nativo, incluidos tests unitarios e integraciones y demo CLI. [JUnit](../reports/tests.xml) · [Workflow](../.github/workflows/ci.yml) · [Lock](../requirements.lock) |
| Comunicación | HTML sin servicio, tabla de probabilidades, auditoría, imágenes y video narrado. [Comprobación móvil/escritorio](../reports/browser.json) · [Material](../assets/web) |
| Recursos y mantenimiento | 22,42 s y pico RSS muestreado de 280,3 MiB en el estudio científico. CPU con un hilo por pool. Reejecución, actualización y restauración documentadas. [Medición](../reports/release/resources.json) |

El manifiesto identifica el commit científico anterior a abrir test. Los commits posteriores incorporan comprobaciones operativas, permisos y presentación. El diseño científico y la selección de modelo se conservaron. La ruta nativa fue la comprobación de ejecución. Docker Compose y GitHub Actions quedaron configurados y su ejecución en esos entornos sigue pendiente. Una validación temporal o geográfica requiere datos adicionales.
