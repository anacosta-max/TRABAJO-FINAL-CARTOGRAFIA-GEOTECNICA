# Validación ROC/AUC — AHP+Combinado, WoE y Regresión Logística

Versión actualizada de `15_Validacion_ROC_Comparativa`, usando la fuente
de AHP corregida y completa (`proyecto_susceptibilidad_AHP`). Carpeta
nueva para no mezclar con los resultados anteriores.

## Cómo replicar (en orden)

```
ahp_fr_pesos.py                            # módulo: pesos de clase FR (L_r/A_r) de las 4 categóricas
01_roc_ahp.py                              # AHP+Combinado e Índices — ROC, 1 curva, sin partición
02_roc_woe.py                              # WoE — ROC, 1 curva, sin partición
03_roc_regresion_logistica_train_test.py   # Regresión logística, partición 80/20
07_mapa_susceptibilidad_AHP.py             # ráster completo de AHP+Combinado (no existía) + mapa 3 clases SGC
08_mapa_susceptibilidad_WoE.py             # reclasifica el ráster de WoE ya existente en 3 clases SGC
09_mapa_susceptibilidad_Regresion.py       # reclasifica el ráster de Regresión ya existente en 3 clases SGC
10_comparacion_mapas.py                    # figura comparativa de los 3 mapas + tabla de % área
05_metricas_adicionales.py                 # distancia a clasificación perfecta + escala de Swets (1988)
06_prueba_delong.py                        # prueba de DeLong pareada (3 modelos, mismos 256 puntos)
04_generar_informe.py                      # Informe_Validacion_ROC.docx (comparación de los 3 modelos)
12_informe_AHP_metodologia.py              # Informe_AHP_Combinado_Metodologia.docx (solo AHP, detalle del cambio de pesos)
```

## Pesos de clase (w_c) de AHP+Combinado: de literatura a Frequency Ratio

El profesor pidió basar la reclasificación de AHP+Combinado en los datos
propios de la cuenca (no en literatura), para que el modelo no rindiera
tan mal. Se aplicó **solo a las 4 variables categóricas** (geología,
geomorfología, cobertura, uso_actual); las 6 continuas y el peso de
variable (W_i, matriz AHP) no se tocaron.

**Fórmula usada — la oficial del capítulo del curso** (`ahp_fr_pesos.py`):

```
w_n = L_r / A_r
L_r = % de los 128 movimientos reales que contiene la clase n
A_r = % del ÁREA TOTAL de la cuenca que representa la clase n (ráster completo)
```

(Nota: una primera versión de este cálculo usó por error "% de puntos
estables" en vez de "% de área" en el denominador — se corrigió tras
detectar la discrepancia con la fórmula del libro.)

## Resultado — hallazgo principal

| Modelo | Curva | AUC | Swets (1988) |
|---|---|---|---|
| AHP + Combinado (w_c por FR) | Única | **0.667** | Aceptable, cerca de "moderado" |
| WoE | Única | **0.819** | Moderado |
| Regresión Logística | Entrenamiento (80%) | **0.898** | Moderado |
| Regresión Logística | Validación (20%) | **0.729** | Moderado |

Antes del cambio (w_c 100% literatura): AHP+Combinado AUC=0.542, t-test
NO significativo (p=0.283). Después (w_c por FR en las 4 categóricas):
AUC=0.667, t-test SÍ significativo (t=4.921, p=1.6×10⁻⁶). La prueba de
DeLong confirma que WoE y Regresión Logística siguen superando a
AHP+Combinado de forma estadísticamente significativa (p<0.05 en las 3
comparaciones pareadas), aunque la brecha se cerró bastante.

Índices (mismos w_c que AHP+Combinado, W_i asignado directamente) se
sigue calculando en segundo plano (AUC=0.673) pero se excluyó de las
gráficas/informes por decisión del usuario — es casi redundante con
AHP+Combinado.

**Recomendación:** si el objetivo es un mapa de susceptibilidad con buena
capacidad predictiva, usar WoE o Regresión Logística. AHP+Combinado
mejoró bastante con FR pero sigue siendo el más débil de los 3.

## Mapas de susceptibilidad — criterio SGC (3 clases)

Scripts `07_` a `10_` construyen el mapa de susceptibilidad de cada
método clasificado en 3 niveles según el criterio del SGC que indicó el
profesor: **Alta = 75% de los movimientos reales, Media = +23% (acumulado
98%), Baja = el resto**. El umbral de cada clase se lee de la curva de
éxito: se ordenan los 128 movimientos por su score y se toma el score en
la posición del percentil correspondiente.

| Modelo | % área en "Alta" (75% de los movimientos) |
|---|---|
| AHP + Combinado (w_c por FR) | **63.7%** — mejoró desde 69.5% (literatura), pero sigue siendo mucha área |
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

Salidas: `mapas/*.tif` (índice continuo + clasificado, 3 modelos),
`figuras/mapa_susceptibilidad_*_3clases.png` y
`figuras/comparacion_3_mapas_susceptibilidad.png`.

## Informes Word

- **`Informe_Validacion_ROC.docx`** — comparación de los 3 modelos: ROC/AUC,
  distancia a clasificación perfecta, escala de Swets, prueba de DeLong,
  y los mapas SGC de 3 clases.
- **`Informe_AHP_Combinado_Metodologia.docx`** — documento dedicado solo a
  AHP+Combinado: fórmula L_r/A_r explicada, tabla completa de pesos
  literatura vs. FR para las 4 categóricas (con % área y % movimientos de
  cada clase), y resultados antes/después del cambio.
