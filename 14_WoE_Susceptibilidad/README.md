# WoE (Weight of Evidence) — Resultados

Resultados del método bivariado **Peso de la Evidencia (WoE)** aplicado a
las 10 variables condicionantes, para el modelo de susceptibilidad a
movimientos en masa de la cuenca de la quebrada El Circio.

## Qué es WoE

Para cada clase de cada variable, se calcula:

```
W+ = ln[ Npix1 / (Npix1 + Npix3) ] − ln[ Npix2 / (Npix2 + Npix4) ]
Contraste C = W+ − W−
```

donde Npix1 = celdas con movimiento en la clase, Npix2 = celdas con
movimiento fuera de la clase, Npix3 = celdas sin movimiento en la clase,
Npix4 = celdas sin movimiento fuera de la clase (conteo sobre el dominio
completo del ráster, no solo sobre los puntos del inventario). El mapa
final se obtiene sumando el W+ de la clase correspondiente de cada
variable, celda a celda.

## Contenido

| Carpeta/archivo | Descripción |
|---|---|
| `01_Inventario_MenM_Extraido/` | Inventario de movimientos (shapefile) y su versión rasterizada, usados para calcular los pesos. |
| `02_Pesos_WoE/pesos_woe_por_variable.csv` | W+, W− y Contraste (C) de cada clase de cada variable. |
| `02_Pesos_WoE/pesos_woe_con_significancia.csv` | Igual, con la significancia estadística de cada contraste (prueba de Studentized Contrast). |
| `03_Rasters_Reclasificados_WoE/` | Cada una de las 10 variables reclasificada: cada celda con el W+ de su clase. |
| `04_Mapa_Susceptibilidad_Final/susceptibilidad_WoE.tif` | Mapa final: suma de los W+ de las 10 variables (índice continuo). |

## Resultado clave

**AUC = 0.819** (Swets 1988: "moderado"). Es el segundo mejor de los tres
modelos evaluados en el artículo, después de Regresión Logística
(AUC=0.869) y por delante de AHP+Combinado (AUC=0.667) — ver comparación
completa en [`../16_Validacion_ROC_Comparativa/`](../16_Validacion_ROC_Comparativa)
y el mapa clasificado en 3 niveles SGC en esa misma carpeta
(`mapas/susceptibilidad_WoE_3clases.tif`).
