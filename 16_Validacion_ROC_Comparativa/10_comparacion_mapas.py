# -*- coding: utf-8 -*-
"""
Figura comparativa de los 3 mapas de susceptibilidad clasificados (SGC:
Alta=75%, Media=+23%, Baja=resto de movimientos) + tabla resumen de
% de área por clase y validación, y una sección nueva en el informe Word.
"""
import os
import numpy as np
import pandas as pd
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_FIG = os.path.join(BASE, "figuras")
DIR_TAB = os.path.join(BASE, "tablas")
DIR_MAPAS = os.path.join(BASE, "mapas")

rasters = {
    "AHP + Combinado": f"{DIR_MAPAS}/susceptibilidad_AHP_combinado_3clases.tif",
    "WoE": f"{DIR_MAPAS}/susceptibilidad_WoE_3clases.tif",
    "Regresión Logística": f"{DIR_MAPAS}/susceptibilidad_Regresion_3clases.tif",
}

colores = ["#1a9850", "#fee08b", "#d73027"]
cmap = ListedColormap(colores)
norm = BoundaryNorm([0.5, 1.5, 2.5, 3.5], cmap.N)

fig, axes = plt.subplots(1, 3, figsize=(15, 7))
for ax, (nombre, ruta) in zip(axes, rasters.items()):
    with rasterio.open(ruta) as src:
        arr = src.read(1)
    im = ax.imshow(arr, cmap=cmap, norm=norm)
    ax.set_title(nombre, fontsize=12)
    ax.set_xticks([]); ax.set_yticks([])

cbar = fig.colorbar(im, ax=axes, ticks=[1, 2, 3], shrink=0.6, orientation="horizontal", pad=0.03)
cbar.ax.set_xticklabels(["Baja", "Media", "Alta"])
fig.suptitle("Comparación de mapas de susceptibilidad (criterio SGC: Alta=75% de los movimientos, "
              "Media=+23% acumulado 98%, Baja=resto)", fontsize=12, y=0.98)
plt.savefig(f"{DIR_FIG}/comparacion_3_mapas_susceptibilidad.png", dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Guardado: figuras/comparacion_3_mapas_susceptibilidad.png")

# ===========================================================================
# Tabla resumen: % área de la clase "Alta" por método (el indicador clave
# de qué tanto concentra el riesgo cada modelo)
# ===========================================================================
filas = []
for nombre, archivo in [("AHP + Combinado", "ahp_distribucion_area_3clases.csv"),
                         ("WoE", "woe_distribucion_area_3clases.csv"),
                         ("Regresión Logística", "regresion_distribucion_area_3clases.csv")]:
    df = pd.read_csv(f"{DIR_TAB}/{archivo}").set_index("clase")
    filas.append({
        "modelo": nombre,
        "pct_area_Baja": df.loc["Baja", "pct_area"],
        "pct_area_Media": df.loc["Media", "pct_area"],
        "pct_area_Alta": df.loc["Alta", "pct_area"],
    })
resumen = pd.DataFrame(filas)
resumen.to_csv(f"{DIR_TAB}/resumen_area_3clases_todos_modelos.csv", index=False, encoding="utf-8-sig")
print("\nResumen: % de área de la cuenca por clase, según cada modelo")
print(resumen.to_string(index=False))
print("\n(Recordatorio: en los 3 modelos, la clase 'Alta' SIEMPRE contiene el 75% de los\n"
      "movimientos reales por construcción — la diferencia entre modelos es CUÁNTA ÁREA\n"
      "necesita cada uno para capturar ese 75%. Menos área = modelo más concentrado/útil.)")
