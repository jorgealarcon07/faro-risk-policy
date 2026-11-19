# Operación, recuperación y mantenimiento

## Publicar una cola

Desde la raíz, instale el lock y ejecute `faro-risk validate`. Use una release local de confianza. La huella comprueba integridad frente al manifiesto conocido. El formato joblib puede ejecutar código al cargar un archivo. Preserve conjuntamente el commit y los artefactos de la release.

El contrato de entrada es un CSV con ID entero positivo único, LIMIT_BAL, seis columnas PAY, seis BILL_AMT y seis PAY_AMT históricas. La CLI admite los namespaces `uci_tw_credit_2005` con corte 2005-09-30 y `credit_simulated_v1` con fecha ISO de simulación. Un lote debe contener una sola población. Campos extra como target o SEX bloquean el lote. Las claves, tipos, signos y valores infinitos se comprueban antes de escribir. Un lote menor de 20 cuentas genera cero revisiones. [Diccionario de campos](ARQUITECTURA.md)

```sh
faro-risk score --csv data/fixtures/synthetic.csv --namespace credit_simulated_v1 --as-of 2026-01-31 --out local/result.json
faro-risk queue --namespace credit_simulated_v1 --as-of 2026-01-31 --out local/queue.csv
```

La primera columna del orden es score descendente y la segunda es SHA-256 hexadecimal de `faro-v1:<ID>` ascendente. El contrato `risk_score` añade namespace, fecha, versión, clase y huella de contenido. El CSV de la vista incorpora el ordinal de revisión `position`. Cada importe y fecha pertenece a su namespace. El CLI escribe logs JSON por etapa sin DSN ni registros privados por cuenta. [Esquemas y lock](../contracts.lock.json)

## Interpretar estados

| Señal | Acción |
|---|---|
| `published`, salida 0 | Consultar conteos y la vista PostgreSQL. Registrar el run y la huella. |
| `replay`, salida 0 | Un envío idéntico ya quedó confirmado. La vista conserva las mismas posiciones. |
| `suspended`, salida 3 | Revisar el JSON del monitor. Comprobar origen, moneda, unidades y nulos antes de una nueva entrega. |
| Entrada incompatible o colisión, salida 2 | Comparar archivo, fecha y contrato con el productor. Reenviar una corrección solo para una fecha que aún no tenga publicación. |
| Error de conexión | Revisar `PGHOST`, puerto y credenciales en el entorno. Si la conexión se perdió después del commit, repetir exactamente el mismo comando. |
| Fallo en `study` | Preservar registro y carpeta parcial para diagnóstico. Usar un directorio de release nuevo tras corregir el problema. Abrir un estudio nuevo sobre la misma cohorte solo reproduce evidencia histórica. |

La referencia es la distribución empírica del entrenamiento en LIMIT_BAL, PAY_0, BILL_AMT1 y PAY_AMT1. El monitor suspende con distancia KS superior a 0,20 o más del 5 % de faltantes en cualquier predictor de origen. Un score fuera de [0,1] o no finito bloquea por contrato. Las reglas se fijaron como controles del laboratorio. El ensayo de cambio multiplica por doce el límite en una copia y vuelve a inferir. El cambio de distribución por sí solo no mide pérdida predictiva. La simulación mantiene etiquetas pendientes el día 7 y permite calcular Brier el día 30. [Monitor ejecutado](../reports/release/monitor.json)

## Auditar accesos y conservar evidencia

La importación privada se realiza por separado mediante `faro-risk audit-import --zip local/uci.zip`, con un usuario autorizado. Verifica de nuevo el ZIP. Un replay compara la cohorte entrante con la tabla histórica. Tras inicializar el scoring y la tabla privada, el administrador de la base dedicada aplica `psql -v ON_ERROR_STOP=1 -f scripts/access.sql`. El script crea grupos NOLOGIN y asigna permisos concretos. Asigne el grupo lector o auditor a un login según su función. La consulta a la vista solo requiere el grupo lector. La aplicación de scoring necesita sus permisos de escritura propios. [SQL de accesos](../scripts/access.sql)

Los datos de auditoría por cuenta y las etiquetas quedan fuera de los CSV de cola y del repositorio. PostgreSQL conserva la proyección privada en `faro_risk_audit.historical_accounts`. Los reportes exportados muestran agregados con umbral de 100 cuentas. El dueño de la base y el administrador conservan facultades administrativas. [Prueba con permisos efectivos](../reports/acceptance.json)

Para reproducir una publicación conserve release, versiones, split, CSV, SHA del original y copia de la base. Para recuperar una base dedicada use copia consistente con `pg_dump -Fc` y restaure con `pg_restore` en una base nueva, con sus roles preparados. Una actualización incompatible del esquema o del significado del score requiere nueva versión y migración explícita. En este prototipo los snapshots publicados son inmutables. Una corrección histórica que deba reemplazarlos exige diseñar y revisar una migración versionada. Se puede validar el reemplazo en una base nueva.

`faro-risk clean --confirm --out local/demo` retira únicamente los tres archivos conocidos de una carpeta con el identificador de la demo. Los clústeres del verificador nativo quedan detenidos bajo `.runtime/` para inspección. El lock fija el entorno probado. Para actualizar dependencias, ensayar en un entorno nuevo, ejecutar suite, recarga de modelos, refit y aceptación antes de mover la versión activa.

## Evidencia y límites del despliegue

El pipeline nativo y el cliente real de PostgreSQL se ejecutaron en Windows. GitHub Actions instala el lock, valida huellas, corre pytest con PostgreSQL de servicio y ejecuta el piloto sintético. El Dockerfile usa un usuario de aplicación sin privilegios y Compose mantiene la base dentro de la red del proyecto. La construcción de imágenes y el workflow remoto están pendientes. [CI](../.github/workflows/ci.yml) · [Compose](../compose.yaml)
