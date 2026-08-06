# -*- coding: utf-8 -*-
"""
Mapa de susceptibilidad — WoE (Peso de la Evidencia), clasificado en 3
niveles (Alta/Media/Baja) según el criterio del SGC: Alta = 75% de los
movimientos, Media = siguiente 23% (acumulado 98%), Baja = el resto
(acumulado 100%). Mismo método que 07_mapa_susceptibilidad_AHP.py, ver
ese script para la explicación completa del criterio de "tasa de éxito
acumulada".

Aquí solo se RECLASIFICA el ráster continuo ya calculado
(susceptibilidad_WoE.tif, 14_WoE_Susceptibilidad) — no hay que reconstruir
nada desde cero.
"""
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_FIG = os.path.join(BASE, "figuras")
DIR_TAB = os.path.join(BASE, "tablas")
DIR_MAPAS = os.path.join(BASE, "mapas")
os.makedirs(DIR_MAPAS, exist_ok=True)

INVENTARIO_SHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\Resultados"
    r"\11_Inventario_Discriminado_Estratificado\inventario_nuevo\puntos_inventario_estratificado.shp"
)
RUTA_RASTER_WOE = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS"
    r"\14_WoE_Susceptibilidad\04_Mapa_Susceptibilidad_Final\susceptibilidad_WoE.tif"
)

# ===========================================================================
# 1. EXTRAER EL SCORE WoE EN LOS 256 PUNTOS (para calcular umbrales)
# ===========================================================================
puntos = gpd.read_file(INVENTARIO_SHP)
y_real = puntos["Y"].astype(int).values
coords = [(geom.x, geom.y) for geom in puntos.geometry]

with rasterio.open(RUTA_RASTER_WOE) as src:
    scores_256 = np.array([v[0] for v in src.sample(coords)], dtype=float)
    perfil_ref = src.profile.copy()
    Sn = src.read(1).astype(float)
    if src.nodata is not None and not np.isnan(src.nodata):
        Sn = np.where(Sn == src.nodata, np.nan, Sn)

score_mov = scores_256[y_real == 1]
mov_sorted = np.sort(score_mov)[::-1]
n = len(mov_sorted)

k_alta = int(np.ceil(0.75 * n))
k_media = int(np.ceil(0.98 * n))
umbral_alta = mov_sorted[k_alta - 1]
umbral_media = mov_sorted[k_media - 1]
umbral_baja_ref = mov_sorted[-1]

print(f"Umbrales SGC (tasa de éxito acumulada, sobre {n} movimientos reales) — WoE:")
print(f"  Alta  (TPR>=0.75): score >= {umbral_alta:.4f}  (TPR real = {k_alta/n:.4f})")
print(f"  Media (TPR>=0.98): {umbral_media:.4f} <= score < {umbral_alta:.4f}  (TPR real = {k_media/n:.4f})")
print(f"  Baja  (TPR=1.00): score < {umbral_media:.4f}  (umbral de referencia TPR=1: {umbral_baja_ref:.4f})")

pd.DataFrame([{
    "modelo": "WoE", "umbral_alta_TPR75": umbral_alta, "umbral_media_TPR98": umbral_media,
    "umbral_referencia_TPR100": umbral_baja_ref, "TPR_real_alta": k_alta / n, "TPR_real_media": k_media / n,
}]).to_csv(f"{DIR_TAB}/umbrales_sgc_woe.csv", index=False, encoding="utf-8-sig")

# ===========================================================================
# 2. CLASIFICAR EL RÁSTER COMPLETO EN 3 NIVELES
# ===========================================================================
clases = np.full(Sn.shape, np.nan, dtype=np.float32)
valido = ~np.isnan(Sn)
clases[valido & (Sn >= umbral_alta)] = 3
clases[valido & (Sn >= umbral_media) & (Sn < umbral_alta)] = 2
clases[valido & (Sn < umbral_media)] = 1

perfil_out = perfil_ref.copy()
perfil_out.update(dtype="float32", nodata=np.nan, count=1)
ruta_clases = os.path.join(DIR_MAPAS, "susceptibilidad_WoE_3clases.tif")
with rasterio.open(ruta_clases, "w", **perfil_out) as dst:
    dst.write(clases, 1)
print(f"\nGuardado: mapas/susceptibilidad_WoE_3clases.tif")

nombres_clase = {1: "Baja", 2: "Media", 3: "Alta"}
n_total_validas = int(valido.sum())
distribucion = []
for c, nombre in nombres_clase.items():
    n_c = int(np.sum(clases == c))
    distribucion.append({"clase": nombre, "n_celdas": n_c, "pct_area": round(100 * n_c / n_total_validas, 2)})
tabla_distribucion = pd.DataFrame(distribucion)
tabla_distribucion.to_csv(f"{DIR_TAB}/woe_distribucion_area_3clases.csv", index=False, encoding="utf-8-sig")
print(tabla_distribucion.to_string(index=False))

# ===========================================================================
# 3. VALIDACIÓN
# ===========================================================================
clase_puntos = np.where(scores_256 >= umbral_alta, 3, np.where(scores_256 >= umbral_media, 2, 1))
tabla_val = pd.DataFrame({"clase": pd.Series(clase_puntos).map(nombres_clase), "Y": y_real})
resumen_val = tabla_val.groupby("clase")["Y"].agg(["count", "sum"]).reindex(["Baja", "Media", "Alta"])
resumen_val.columns = ["n_puntos_total", "n_movimientos"]
resumen_val["pct_movimientos"] = round(100 * resumen_val["n_movimientos"] / resumen_val["n_movimientos"].sum(), 1)
print("\nValidación — distribución de los 128 movimientos reales por clase:")
print(resumen_val.to_string())
resumen_val.to_csv(f"{DIR_TAB}/woe_validacion_3clases.csv", encoding="utf-8-sig")

# ===========================================================================
# 4. FIGURA
# ===========================================================================
colores = ["#1a9850", "#fee08b", "#d73027"]
cmap = ListedColormap(colores)
norm = BoundaryNorm([0.5, 1.5, 2.5, 3.5], cmap.N)

fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(clases, cmap=cmap, norm=norm)
ax.set_title("Susceptibilidad — WoE (3 clases, criterio SGC)\n"
              "Alta=75% mov., Media=+23% (98% acum.), Baja=resto")
ax.set_xticks([]); ax.set_yticks([])
cbar = fig.colorbar(im, ax=ax, ticks=[1, 2, 3], shrink=0.75)
cbar.ax.set_yticklabels(["Baja", "Media", "Alta"])
plt.tight_layout()
plt.savefig(f"{DIR_FIG}/mapa_susceptibilidad_WoE_3clases.png", dpi=180)
plt.close(fig)
print(f"\nGuardado: figuras/mapa_susceptibilidad_WoE_3clases.png")
