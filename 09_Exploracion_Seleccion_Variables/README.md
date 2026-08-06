# Exploración y selección de variables — inventario estratificado

Análisis estadístico de las 10 variables condicionantes (poder discriminativo,
correlación) sobre el **inventario final de 256 puntos** usado en los tres
modelos de susceptibilidad (128 movimientos reales + 128 puntos "NO" por
disimilitud ambiental moderada + muestreo espacialmente estratificado en 18
estratos). Es la única variante que se subió a este repo — el proyecto local
también tiene versiones sobre el inventario original (NO aleatorio) y una
versión intermedia ("discriminado v1", disimilitud extrema), que no se
incluyen aquí por no ser las que finalmente se usaron en los modelos.

## Contenido

| Archivo | Descripción |
|---|---|
| `02_analisis_seleccion_variables_estratificado.py` | Estadística comparativa por variable (t-test/Mann-Whitney/chi², AUC, información mutua, F-score) + ranking de poder discriminativo. |
| `03_correlacion_variables_estratificado.py` | Matriz de correlación Pearson/Spearman entre las 10 variables + correlación con el inventario, para descartar multicolinealidad. |
| `figuras_estratificado/analisis_<variable>.png` | KDE + boxplot + histograma + ROC de cada variable numérica, comparando puntos con y sin movimiento. |
| `figuras_estratificado/analisis_categorico_<variable>.png` | Distribución por clase de cada variable categórica. |
| `figuras_estratificado/matriz_correlacion_pearson.png` / `..._spearman.png` | Mapas de calor de correlación. |
| `tablas_estratificado/ranking_variables.csv` | Ranking de las 10 variables por AUC/significancia — insumo para decidir cuáles entran a los modelos. |
| `tablas_estratificado/estadisticas_numericas.csv` / `estadisticas_categoricas.csv` | Estadística descriptiva por variable. |
| `tablas_estratificado/informacion_mutua_f_score.csv` | Rankings alternativos (no siempre coinciden con el de AUC). |
| `tablas_estratificado/matriz_correlacion_pearson.csv` / `..._spearman.csv` / `pares_alta_correlacion.csv` | Matrices de correlación en detalle. |
| `tablas_estratificado/correlacion_con_inventario.csv` | Correlación de cada variable con la variable dependiente (Y). |

## Resultado clave

Ningún par de variables predictoras supera |r|=0.7 (umbral típico de alerta
de multicolinealidad) — no hay razón estadística para descartar ninguna de
las 10 variables por redundancia.

**Confirmación de consistencia (la señal más importante):** `flujo_acum`
(p=0.646) y `dist_drenajes` (p=0.481) — las dos variables que NO se usaron
para construir el inventario de puntos "NO" — siguen sin ser
estadísticamente significativas. Esto respalda que esas dos variables
genuinamente no discriminan movimiento/estabilidad en esta cuenca,
independientemente del método de muestreo de ausencias (se confirmó
comparando contra otras dos versiones del inventario, ver el README completo
del proyecto local para el detalle comparativo).

**Un hallazgo relevante que contrasta con el modelo heurístico AHP:**
`pendiente` —la variable de mayor peso en la matriz de Saaty de
[`../13_AHP_Combinado`](../13_AHP_Combinado), por literatura general de
movimientos en masa— no discrimina fuertemente en esta cuenca específica
(consistente con que nunca entra al modelo final de
[`../13_Regresion_Logistica`](../13_Regresion_Logistica), que sí se ajusta a
los datos locales vía AIC).
