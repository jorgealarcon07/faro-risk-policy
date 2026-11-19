# Lote sintético para la demo

`synthetic.csv` contiene 500 cuentas ficticias. Lo genera `demo_batch` con semilla 2026. Cuatro variables reproducen marginales empíricas de entrenamiento mediante muestreos independientes. Las demás se generan con distribuciones fijadas en código. El lote carece de etiqueta, demografía o vínculo con una persona del estudio. Namespace `credit_simulated_v1`, corte simulado 2026-01-31. Sirve para verificar la entrega de 25 revisiones por SQL y la recuperación por replay.

Distribuciones derivadas de I-Cheng Yeh, *Default of Credit Card Clients*, UCI, CC BY 4.0. [Procedencia y cambios](../../DATA_SOURCES.md) · [Ejecución del caso](../../reports/demo.json)
