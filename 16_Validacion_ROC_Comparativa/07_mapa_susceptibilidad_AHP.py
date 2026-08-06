# -*- coding: utf-8 -*-
"""
Mapa de susceptibilidad — AHP + Combinado, clasificado en 3 niveles
(Alta/Media/Baja) según el criterio del SGC que indicó el profesor:
Alta = 75% de los movimientos, Media = siguiente 23% (acumulado 98%),
Baja = el resto (acumulado 100%).

Método ("tasa de éxito acumulada"):
  1. Se calcula el índice AHP+Combinado (S_n = Σ Wᵢ·w_cᵢ) en los 128
     puntos de movimiento real.
  2. Se ordenan esos 128 valores de mayor a menor.
  3. El umbral "Alta" es el score del movimiento que está en la posición
     75% (percentil 75 desde arriba) — es decir, el valor de score tal
     que exactamente el 75% de los movimientos reales tienen un score
     igual o mayor (TPR=0.75 en la curva ROC/éxito).
  4. El umbral "Media" es el score en la posición 98% (75+23) — TPR=0.98.
  5. Con esos dos umbrales se clasifica el RÁSTER COMPLETO de la cuenca:
     Alta = score ≥ umbral_alta
     Media = umbral_media ≤ score < umbral_alta
     Baja = score < umbral_media

Como el proyecto original (proyecto_susceptibilidad_AHP) está pensado
para ArcGIS Pro (arcpy) y aún no generó el ráster final, este script
construye el ráster completo de AHP+Combinado en Python puro (rasterio),
aplicando las mismas reglas de reclasificación ya usadas en 01_roc_ahp.py,
pero ahora sobre los 10 rásters completos en vez de solo los 256 puntos.

Igual que en 01_roc_ahp.py: el w_c de las 4 CATEGÓRICAS (geología,
geomorfología, cobertura, uso_actual) viene de Frequency Ratio calculado
sobre el inventario real (ver ahp_fr_pesos.py), no de literatura — pedido
explícito del profesor para que el modelo se base en los datos propios.
Las 6 CONTINUAS siguen con los rangos de literatura, sin cambios. Los
códigos que existan en el ráster completo pero que NUNCA aparecieron en
los 256 puntos del inventario (p. ej. geomorfología 8, 14, 15, 16) reciben
el "valor neutral" de esa variable (FR_media_global/FR_máximo) en vez de
quedar sin clase — se documenta cuántas celdas caen en este caso.
"""
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from ahp_fr_pesos import calcular_pesos_clase_FR

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_FIG = os.path.join(BASE, "figuras")
DIR_TAB = os.path.join(BASE, "tablas")
DIR_MAPAS = os.path.join(BASE, "mapas")
os.makedirs(DIR_MAPAS, exist_ok=True)

DATA_AHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS"
    r"\proyecto_susceptibilidad_AHP\proyecto_susceptibilidad_AHP\data"
)
RASTER_FOLDER = r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\masked_by_pendiente_v2"
INVENTARIO_SHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\Resultados"
    r"\11_Inventario_Discriminado_Estratificado\inventario_nuevo\puntos_inventario_estratificado.shp"
)

VARIABLES = ["pendiente", "aspecto", "curvatura", "flujo_acum", "elevacion",
             "dist_drenajes", "cobertura", "uso_actual", "geologia", "geomorfologia"]
RASTERS_ARCHIVO = {
    "pendiente": "pendiente.tif", "aspecto": "aspecto.tif", "curvatura": "curvatura.tif",
    "flujo_acum": "flujo_acumulado.tif", "elevacion": "elevacion.tif", "dist_drenajes": "dist_drenajes.tif",
    "cobertura": "cobertura.tif", "uso_actual": "uso_actual.tif", "geologia": "geologia.tif",
    "geomorfologia": "geomorfologia.tif",
}

# ===========================================================================
# 1. CARGAR PESOS (mismo AHP+Combinado que 01_roc_ahp.py)
# ===========================================================================
df_pesos_var = pd.read_csv(f"{DATA_AHP}/pesos_variables.csv", index_col=0)
pesos_ahp = df_pesos_var["peso_ahp"].to_dict()

df_continuas = pd.read_csv(f"{DATA_AHP}/pesos_clase_continuas.csv")

# w_c de las 4 categóricas: Frequency Ratio sobre el inventario real
mapas_categoricos, valores_neutrales_fr, registro_fr = calcular_pesos_clase_FR()
print("Pesos de clase (w_c) usados — categóricas por Frequency Ratio:")
print(registro_fr.to_string(index=False))
print(f"Valores neutrales (códigos nunca vistos en el inventario): {valores_neutrales_fr}\n")

# ===========================================================================
# 2. RECLASIFICAR LOS 10 RÁSTERS COMPLETOS (w_c por celda)
# ===========================================================================
print("=== Reclasificando rásters completos ===")
arrays_wc = {}
perfil_ref = None
forma_ref = None
mascara_nan_global = None

for var in VARIABLES:
    ruta = os.path.join(RASTER_FOLDER, RASTERS_ARCHIVO[var])
    with rasterio.open(ruta) as src:
        arr = src.read(1).astype(float)
        if src.nodata is not None:
            arr = np.where(arr == src.nodata, np.nan, arr)
        if perfil_ref is None:
            perfil_ref = src.profile.copy()
            forma_ref = arr.shape
            mascara_nan_global = np.isnan(arr)

    if var in df_continuas["variable"].unique():
        fila_var = df_continuas[df_continuas.variable == var]
        wc = np.full(arr.shape, np.nan)
        for _, row in fila_var.iterrows():
            mask = (arr >= row["rango_min"]) & (arr < row["rango_max"])
            wc = np.where(mask, row["peso_wc"], wc)
        if var == "aspecto":
            norte_mask = (arr >= 315) | (arr < 45)
            peso_norte = df_continuas[(df_continuas.variable == "aspecto") &
                                       (df_continuas.rango_min == 315)]["peso_wc"].values[0]
            wc = np.where(norte_mask, peso_norte, wc)
    else:
        wc = np.full(arr.shape, np.nan)
        for codigo, peso in mapas_categoricos[var].items():
            wc = np.where(arr == codigo, peso, wc)
        # códigos válidos en el ráster que nunca aparecieron en el inventario
        # (el FR no pudo calcularse para ellos) -> valor neutral de la variable
        sin_regla = np.isnan(wc) & ~np.isnan(arr)
        n_neutral = int(sin_regla.sum())
        if n_neutral > 0:
            wc = np.where(sin_regla, valores_neutrales_fr[var], wc)
            print(f"  [{var}] {n_neutral} celdas con código no observado en el inventario -> "
                  f"valor neutral ({valores_neutrales_fr[var]})")

    n_sin_clase = int(np.sum(np.isnan(wc) & ~np.isnan(arr)))
    if n_sin_clase > 0:
        print(f"  ADVERTENCIA [{var}]: {n_sin_clase} celdas válidas sin regla de reclasificación")

    arrays_wc[var] = wc
    mascara_nan_global |= np.isnan(arr)
    print(f"  {var}: OK")

# ===========================================================================
# 3. COMBINAR: S_n = Σ Wᵢ · w_cᵢ
# ===========================================================================
Sn = np.zeros(forma_ref)
for var in VARIABLES:
    Sn += pesos_ahp[var] * np.nan_to_num(arrays_wc[var], nan=0.0)
Sn = np.where(mascara_nan_global, np.nan, Sn)

print(f"\nS_n AHP+Combinado (ráster completo): min={np.nanmin(Sn):.3f}  "
      f"max={np.nanmax(Sn):.3f}  media={np.nanmean(Sn):.3f}")

perfil_out = perfil_ref.copy()
perfil_out.update(dtype="float32", nodata=np.nan, count=1)
ruta_continuo = os.path.join(DIR_MAPAS, "indice_AHP_combinado.tif")
with rasterio.open(ruta_continuo, "w", **perfil_out) as dst:
    dst.write(Sn.astype(np.float32), 1)
print(f"Guardado: mapas/indice_AHP_combinado.tif")

# ===========================================================================
# 4. UMBRALES POR TASA DE ÉXITO ACUMULADA (SGC: 75% / 23% / 2%)
# ===========================================================================
scores_export = pd.read_csv(f"{DIR_TAB}/scores_ahp_indices_256puntos.csv")
score_mov = scores_export.loc[scores_export["Y"] == 1, "score_AHP_Combinado"].values
mov_sorted = np.sort(score_mov)[::-1]
n = len(mov_sorted)

k_alta = int(np.ceil(0.75 * n))
k_media = int(np.ceil(0.98 * n))
umbral_alta = mov_sorted[k_alta - 1]
umbral_media = mov_sorted[k_media - 1]
umbral_baja_ref = mov_sorted[-1]  # TPR=100% (referencia, no se usa como corte)

print(f"\nUmbrales SGC (tasa de éxito acumulada, sobre {n} movimientos reales):")
print(f"  Alta  (TPR>=0.75): score >= {umbral_alta:.4f}  (TPR real = {k_alta/n:.4f})")
print(f"  Media (TPR>=0.98): {umbral_media:.4f} <= score < {umbral_alta:.4f}  (TPR real = {k_media/n:.4f})")
print(f"  Baja  (TPR=1.00): score < {umbral_media:.4f}  (umbral de referencia TPR=1: {umbral_baja_ref:.4f})")

pd.DataFrame([{
    "modelo": "AHP+Combinado", "umbral_alta_TPR75": umbral_alta, "umbral_media_TPR98": umbral_media,
    "umbral_referencia_TPR100": umbral_baja_ref, "TPR_real_alta": k_alta / n, "TPR_real_media": k_media / n,
}]).to_csv(f"{DIR_TAB}/umbrales_sgc_ahp.csv", index=False, encoding="utf-8-sig")

# ===========================================================================
# 5. CLASIFICAR EL RÁSTER COMPLETO EN 3 NIVELES
# ===========================================================================
clases = np.full(forma_ref, np.nan, dtype=np.float32)
valido = ~np.isnan(Sn)
clases[valido & (Sn >= umbral_alta)] = 3       # Alta
clases[valido & (Sn >= umbral_media) & (Sn < umbral_alta)] = 2  # Media
clases[valido & (Sn < umbral_media)] = 1       # Baja

ruta_clases = os.path.join(DIR_MAPAS, "susceptibilidad_AHP_combinado_3clases.tif")
with rasterio.open(ruta_clases, "w", **perfil_out) as dst:
    dst.write(clases, 1)
print(f"\nGuardado: mapas/susceptibilidad_AHP_combinado_3clases.tif")

nombres_clase = {1: "Baja", 2: "Media", 3: "Alta"}
n_total_validas = int(valido.sum())
distribucion = []
for c, nombre in nombres_clase.items():
    n_c = int(np.sum(clases == c))
    distribucion.append({"clase": nombre, "n_celdas": n_c, "pct_area": round(100 * n_c / n_total_validas, 2)})
tabla_distribucion = pd.DataFrame(distribucion)
tabla_distribucion.to_csv(f"{DIR_TAB}/ahp_distribucion_area_3clases.csv", index=False, encoding="utf-8-sig")
print(tabla_distribucion.to_string(index=False))

# ===========================================================================
# 6. VALIDACIÓN: dónde caen los 256 puntos del inventario en las 3 clases
# ===========================================================================
puntos = gpd.read_file(INVENTARIO_SHP)
y_real = puntos["Y"].astype(int).values
scores_todos = scores_export["score_AHP_Combinado"].values
clase_puntos = np.where(scores_todos >= umbral_alta, 3, np.where(scores_todos >= umbral_media, 2, 1))

tabla_val = pd.DataFrame({"clase": pd.Series(clase_puntos).map(nombres_clase), "Y": y_real})
resumen_val = tabla_val.groupby("clase")["Y"].agg(["count", "sum"]).reindex(["Baja", "Media", "Alta"])
resumen_val.columns = ["n_puntos_total", "n_movimientos"]
resumen_val["pct_movimientos"] = round(100 * resumen_val["n_movimientos"] / resumen_val["n_movimientos"].sum(), 1)
print("\nValidación — distribución de los 128 movimientos reales por clase:")
print(resumen_val.to_string())
resumen_val.to_csv(f"{DIR_TAB}/ahp_validacion_3clases.csv", encoding="utf-8-sig")

# ===========================================================================
# 7. FIGURA
# ===========================================================================
colores = ["#1a9850", "#fee08b", "#d73027"]  # Baja, Media, Alta
cmap = ListedColormap(colores)
norm = BoundaryNorm([0.5, 1.5, 2.5, 3.5], cmap.N)

fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(clases, cmap=cmap, norm=norm)
ax.set_title("Susceptibilidad — AHP + Combinado (3 clases, criterio SGC)\n"
              "Alta=75% mov., Media=+23% (98% acum.), Baja=resto")
ax.set_xticks([]); ax.set_yticks([])
cbar = fig.colorbar(im, ax=ax, ticks=[1, 2, 3], shrink=0.75)
cbar.ax.set_yticklabels(["Baja", "Media", "Alta"])
plt.tight_layout()
plt.savefig(f"{DIR_FIG}/mapa_susceptibilidad_AHP_3clases.png", dpi=180)
plt.close(fig)
print(f"\nGuardado: figuras/mapa_susceptibilidad_AHP_3clases.png")
