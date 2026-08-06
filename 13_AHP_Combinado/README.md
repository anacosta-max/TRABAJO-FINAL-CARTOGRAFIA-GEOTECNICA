# AHP + Combinado — Resultados finales

Carpeta con los resultados del método heurístico **AHP + Combinado** usado en el
artículo (caracterización de modelos de susceptibilidad a movimientos en masa,
cuenca de la quebrada El Circio, Abejorral, Antioquia). Es un extracto
autocontenido de `16_Validacion_ROC_Comparativa/`, que originalmente reúne los
tres métodos (AHP+Combinado, WoE, Regresión Logística); esta carpeta deja solo
lo específico de AHP+Combinado para subir aparte.

## Qué es AHP + Combinado

`S_n = Σ Wᵢ · w_cᵢ`, donde:
- **W_i** (peso por variable): matriz de comparación pareada de Saaty (AHP) +
  eigenvector — ver [`tablas/matriz_ahp.csv`](tablas/matriz_ahp.csv) y
  [`tablas/pesos_variables.csv`](tablas/pesos_variables.csv). Es 100% juicio
  experto, no cambió en este proceso. CR = 0.0199 (consistente, ver
  [`tablas/consistencia_ahp.csv`](tablas/consistencia_ahp.csv)).
- **w_c** (peso por clase dentro de cada variable):
  - 4 variables categóricas (geología, geomorfología, cobertura, uso_actual):
    recalculado con **Frequency Ratio** `w_n = L_r / A_r` (L_r = % de los 128
    movimientos reales en la clase; A_r = % del área total de la cuenca que
    ocupa la clase), normalizado por el w_n máximo de cada variable — ver
    [`ahp_fr_pesos.py`](ahp_fr_pesos.py).
  - 6 variables continuas: rangos de literatura (sin cambios, fuera del
    alcance de este ajuste).

## Contenido

| Archivo | Descripción |
|---|---|
| `ahp_fr_pesos.py` | Calcula los pesos `w_c` (Frequency Ratio, L_r/A_r) de las 4 variables categóricas. |
| `01_roc_ahp.py` | Calcula el score AHP+Combinado en los 256 puntos del inventario y su curva ROC "a mano" (barrido manual de umbrales + AUC trapezoidal). |
| `07_mapa_susceptibilidad_AHP.py` | Construye el mapa raster completo de susceptibilidad (10 variables reclasificadas) y lo clasifica en 3 niveles según criterio SGC (Alta=75% de movimientos, Media=+23%, Baja=resto). |
| `12_informe_AHP_metodologia.py` | Genera `Informe_AHP_Combinado_Metodologia.docx`. |
| `Informe_AHP_Combinado_Metodologia.docx` | Informe con la metodología completa del recálculo de pesos y su efecto en el AUC. |
| `figuras/roc_ahp.png` | Curva ROC de AHP+Combinado. |
| `figuras/mapa_susceptibilidad_AHP_3clases.png` | Mapa de susceptibilidad clasificado en 3 niveles (criterio SGC). |
| `mapas/indice_AHP_combinado.tif` | Ráster continuo del índice de susceptibilidad AHP+Combinado (score S_n). |
| `mapas/susceptibilidad_AHP_combinado_3clases.tif` | Ráster clasificado en 3 niveles (Alta/Media/Baja). |
| `tablas/matriz_ahp.csv` | **Matriz de comparación por pares de Saaty (10×10)**, el insumo original del AHP: para cada par de variables, cuántas veces más importante es una que la otra según juicio experto (escala 1–9 y sus recíprocos). |
| `tablas/consistencia_ahp.csv` | λmax, CI, CR de la matriz (CR=0.0199 < 0.10 → consistente). |
| `tablas/pesos_variables.csv` | Peso final **W_i** de cada una de las 10 variables, obtenido del eigenvector de la matriz de Saaty (columna `peso_ahp`); incluye también los pesos del método de Índices (`peso_indices`, no usado en el artículo, se deja de referencia). |
| `tablas/pesos_clase_FR_categoricas.csv` | Pesos `w_c` (FR) de las 4 variables categóricas, con % área (A_r) y % movimientos (L_r) por clase. |
| `tablas/scores_ahp_indices_256puntos.csv` | Score AHP+Combinado (e Índices) calculado en los 256 puntos del inventario. |
| `tablas/roc_ahp+combinado_puntos_umbral.csv` | Puntos de la curva ROC (TPR, FPR por umbral). |
| `tablas/ahp+combinado_matriz_confusion_resumen.csv` | Matriz de confusión y exactitud en el umbral de referencia (mediana). |
| `tablas/umbrales_sgc_ahp.csv` | Umbrales de score para las 3 clases SGC (Alta≥0.4485, Media 0.3487–0.4485). |
| `tablas/ahp_distribucion_area_3clases.csv` | % de área de la cuenca en cada clase (Baja=7.8%, Media=28.5%, Alta=63.7%). |
| `tablas/ahp_validacion_3clases.csv` | Validación de la clasificación de 3 niveles contra el inventario. |

## Resultado clave

**AUC = 0.667** (Swets 1988: "aceptable", mejor que el azar). Es el modelo con
menor desempeño de los tres evaluados en el artículo (WoE=0.819, Regresión
Logística=0.869), pero mejoró respecto a los pesos de literatura pura gracias
al recálculo de `w_c` con Frequency Ratio (ver informe adjunto para el
detalle antes/después).

## Dependencias externas (no incluidas aquí, por tamaño)

Los scripts asumen la siguiente estructura de carpetas del proyecto completo
(rutas absolutas dentro de `MODELOS/`), necesaria solo si se quiere
**re-ejecutar** el pipeline, no para consultar los resultados ya generados:
- `masked_by_pendiente_v2/` — los 10 rásters de variables condicionantes recortados a la cuenca.
- `Resultados/11_Inventario_Discriminado_Estratificado/inventario_nuevo/` — shapefile del inventario de 256 puntos (128 movimientos + 128 estables).
- `proyecto_susceptibilidad_AHP/proyecto_susceptibilidad_AHP/data/pesos_clase_continuas.csv` — pesos w_c de literatura para las 6 variables continuas (los W_i y la matriz de Saaty sí están incluidos en `tablas/`, ver arriba).

## Contexto comparativo (no incluido aquí)

Las curvas ROC comparadas entre los 3 métodos, la prueba de DeLong, y los
mapas de WoE/Regresión Logística están en `16_Validacion_ROC_Comparativa/`
(carpeta original de la que se extrajo este contenido).
