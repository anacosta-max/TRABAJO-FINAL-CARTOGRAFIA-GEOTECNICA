# Validación ROC/AUC — Comparación de los 3 modelos

Comparación conjunta de los tres métodos de susceptibilidad (AHP+Combinado,
WoE, Regresión Logística): curvas ROC, prueba de DeLong, mapas SGC de 3
clases y el informe final.

> **Nota:** los resultados específicos de AHP+Combinado (matriz de Saaty,
> pesos por Frequency Ratio, ráster de índice, mapa de 3 clases, informe de
> metodología) viven en la carpeta hermana **[`13_AHP_Combinado/`](../13_AHP_Combinado)**,
> para no duplicar contenido entre carpetas. Esta carpeta se enfoca en lo que
> es genuinamente comparativo entre los 3 modelos.

## Cómo replicar (en orden)

```
02_roc_woe.py                              # WoE — ROC, 1 curva, sin partición
03_roc_regresion_logistica_train_test.py   # Regresión logística, partición 80/20
08_mapa_susceptibilidad_WoE.py             # reclasifica el ráster de WoE ya existente en 3 clases SGC
09_mapa_susceptibilidad_Regresion.py       # reclasifica el ráster de Regresión ya existente en 3 clases SGC
10_comparacion_mapas.py                    # figura comparativa de los 3 mapas + tabla de % área
05_metricas_adicionales.py                 # distancia a clasificación perfecta + escala de Swets (1988)
06_prueba_delong.py                        # prueba de DeLong pareada (3 modelos, mismos 256 puntos)
04_generar_informe.py                      # Informe_Validacion_ROC.docx (comparación de los 3 modelos)
```

Estos scripts leen como insumo los resultados de AHP+Combinado (score en
los 256 puntos, ráster de susceptibilidad) desde `13_AHP_Combinado/tablas/` y
`13_AHP_Combinado/mapas/` — no desde esta carpeta.

## Resultado — hallazgo principal

| Modelo | Curva | AUC | Swets (1988) |
|---|---|---|---|
| AHP + Combinado (w_c por FR) | Única | **0.667** | Aceptable, cerca de "moderado" |
| WoE | Única | **0.819** | Moderado |
| Regresión Logística | Entrenamiento (80%) | **0.898** | Moderado |
| Regresión Logística | Validación (20%) | **0.729** | Moderado |

La prueba de DeLong confirma que WoE y Regresión Logística superan a
AHP+Combinado de forma estadísticamente significativa (p<0.05 en las 3
comparaciones pareadas). Detalle del recálculo de pesos de AHP+Combinado
(que subió su AUC de 0.542 a 0.667) en `13_AHP_Combinado/`.

**Recomendación:** si el objetivo es un mapa de susceptibilidad con buena
capacidad predictiva, usar WoE o Regresión Logística. AHP+Combinado
mejoró bastante con FR pero sigue siendo el más débil de los 3.

## Mapas de susceptibilidad — criterio SGC (3 clases)

Scripts `08_`/`09_`/`10_` construyen y comparan el mapa de susceptibilidad
de cada método clasificado en 3 niveles según el criterio del SGC que
indicó el profesor: **Alta = 75% de los movimientos reales, Media = +23%
(acumulado 98%), Baja = el resto**. El umbral de cada clase se lee de la
curva de éxito: se ordenan los 128 movimientos por su score y se toma el
score en la posición del percentil correspondiente.

| Modelo | % área en "Alta" (75% de los movimientos) |
|---|---|
| AHP + Combinado (w_c por FR) | **63.7%** (ver `13_AHP_Combinado/`) |
| WoE | **42.2%** — el más concentrado de los 3 |
| Regresión Logística | **48.2%** |

Por construcción, la clase "Alta" de los 3 mapas contiene el mismo 75% de
movimientos — lo que cambia es cuánta área necesita cada modelo para
lograrlo. Regresión Logística (mayor AUC, 0.869) necesita más área que
WoE para el mismo 75%: el AUC mide qué tan bien el modelo ORDENA los
puntos en general, no qué tan concentrada queda la probabilidad en el
mapa — con 3 de sus 5 variables categóricas, la regresión asigna
probabilidades casi idénticas a polígonos completos de geología/
geomorfología/uso_actual, generando bloques grandes de "Alta".

Salidas: `mapas/*.tif` (WoE y Regresión; el de AHP+Combinado está en
`13_AHP_Combinado/mapas/`), `figuras/mapa_susceptibilidad_*_3clases.png` y
`figuras/comparacion_3_mapas_susceptibilidad.png` (mosaico de los 3).

## Informe Word

**`Informe_Validacion_ROC.docx`** — comparación de los 3 modelos: ROC/AUC,
distancia a clasificación perfecta, escala de Swets, prueba de DeLong, y
los mapas SGC de 3 clases. El informe dedicado solo a la metodología de
AHP+Combinado (`Informe_AHP_Combinado_Metodologia.docx`) está en
`13_AHP_Combinado/`.
