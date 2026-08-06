"""
Paso 6 — Mapa de susceptibilidad con el modelo final de regresión logística.

Aplica el modelo final (uso_actual, geologia, geomorfologia, curvatura,
dist_drenajes; ver 05_comparacion_metodos.py) a los rasters de todo el
dominio de estudio para producir:
  1. Un mapa continuo de probabilidad de movimiento (0-1), P = 1/(1+e^-Xb).
  2. Un mapa clasificado de susceptibilidad en 5 clases (quintiles de
     probabilidad, mismo criterio usado en 08_Metodos_Conocimiento para
     que los mapas sean comparables).

Limitación documentada: las variables cualitativas del modelo se
reclasifican en la cuadrícula con las MISMAS reglas de agrupación de
categorías raras que se usaron para entrenar el modelo (ver
colapsar_categorias_raras en config_base.py). Cualquier celda cuya
categoría no exista en ninguna forma en el modelo entrenado (es decir, no
es ni una categoría original vista en el entrenamiento ni cae en la
categoría "Otras"/mayoritaria por asociación) queda como NoData: el modelo
no puede extrapolar a categorías que nunca observó.
"""
import os
import numpy as np
import pandas as pd
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

from config_base import (
    cargar_datos, colapsar_categorias_raras, ajustar_modelo, RASTER_FOLDER,
    RASTERS, VARIABLES_CATEGORICAS, DIR_TABLAS, DIR_FIGURAS, CARPETA_BASE,
)

DIR_MAPAS = os.path.join(CARPETA_BASE, "mapas")
os.makedirs(DIR_MAPAS, exist_ok=True)

VARIABLES_MODELO = ["uso_actual", "geologia", "geomorfologia", "curvatura", "dist_drenajes"]

# --- 1. Reconstruir el modelo final y las reglas de agrupación de categorías ---
puntos_col, registro_agrupacion = None, None
df_entrenamiento = cargar_datos()
modelo = ajustar_modelo(df_entrenamiento, VARIABLES_MODELO)
print(f"Modelo final: AIC={modelo.aic:.2f}  Pseudo R2={modelo.prsquared:.4f}")

# reglas de agrupación (categoría original -> destino), recalculadas sobre los datos crudos
import geopandas as gpd
from config_base import INVENTARIO_SHP, RENOMBRAR_COLUMNAS, COLUMNA_PRESENCIA, TODAS_LAS_VARIABLES
puntos = gpd.read_file(INVENTARIO_SHP).rename(columns=RENOMBRAR_COLUMNAS)
df_crudo = puntos[TODAS_LAS_VARIABLES + [COLUMNA_PRESENCIA]].copy().rename(columns={COLUMNA_PRESENCIA: "inventario"})
df_crudo["inventario"] = df_crudo["inventario"].astype(int)
_, registro_agrupacion = colapsar_categorias_raras(df_crudo)

reglas_por_variable = {var: {} for var in VARIABLES_CATEGORICAS}
for _, fila in registro_agrupacion.iterrows():
    var = fila["variable"]
    origen = float(fila["categoria_original"])
    if fila["destino"] == "Otras":
        destino = 9999.0
    else:
        destino = float(str(fila["destino"]).split()[-1])
    reglas_por_variable[var][origen] = destino

# categorías válidas (tal como quedaron en el modelo entrenado) por variable categórica
categorias_validas = {var: set(df_entrenamiento[var].unique()) for var in VARIABLES_CATEGORICAS}

# --- 2. Cargar rasters de las 5 variables del modelo y alinear a la misma grilla ---
archivo_por_variable = {v: k for k, v in RASTERS.items()}
datos = {}
perfil_ref = None
for var in VARIABLES_MODELO:
    ruta = os.path.join(RASTER_FOLDER, archivo_por_variable[var])
    with rasterio.open(ruta) as src:
        arr = src.read(1).astype(float)
        if src.nodata is not None:
            arr = np.where(arr == src.nodata, np.nan, arr)
        datos[var] = arr
        if perfil_ref is None:
            perfil_ref = src.profile.copy()
            forma_ref = arr.shape

for var, arr in datos.items():
    if arr.shape != forma_ref:
        raise ValueError(f"Raster de '{var}' no coincide en tamaño con el resto: {arr.shape} vs {forma_ref}")

# --- 3. Aplicar reglas de agrupación de categorías a los rasters categóricos ---
mascara_categoria_desconocida = np.zeros(forma_ref, dtype=bool)
for var in VARIABLES_CATEGORICAS:
    if var not in datos:
        continue
    arr = datos[var].copy()
    valido = ~np.isnan(arr)
    for origen, destino in reglas_por_variable[var].items():
        arr = np.where(valido & np.isclose(arr, origen), destino, arr)
    # cualquier valor válido que, tras la agrupación, no exista en las categorías del modelo entrenado
    arr_valido = ~np.isnan(arr)
    conocida = np.isin(np.round(arr, 2), [round(c, 2) for c in categorias_validas[var]])
    desconocida = arr_valido & ~conocida
    mascara_categoria_desconocida |= desconocida
    datos[var] = arr

n_desconocidas = int(mascara_categoria_desconocida.sum())
print(f"Celdas con categoría no vista en el entrenamiento (quedan NoData): {n_desconocidas}")

# --- 4. Construir el dataframe de predicción (una fila por celda válida) ---
mascara_valida = np.ones(forma_ref, dtype=bool)
for var in VARIABLES_MODELO:
    mascara_valida &= ~np.isnan(datos[var])
mascara_valida &= ~mascara_categoria_desconocida

filas, columnas = np.where(mascara_valida)
df_pred = pd.DataFrame({var: datos[var][filas, columnas] for var in VARIABLES_MODELO})

print(f"Celdas válidas para predecir: {len(df_pred)} de {forma_ref[0] * forma_ref[1]} totales")

# --- 5. Predecir probabilidad con el modelo final ---
prob = modelo.predict(df_pred)

mapa_prob = np.full(forma_ref, np.nan, dtype=np.float32)
mapa_prob[filas, columnas] = prob.values

perfil_prob = perfil_ref.copy()
perfil_prob.update(dtype="float32", nodata=np.nan, count=1)
ruta_prob = os.path.join(DIR_MAPAS, "probabilidad_regresion_logistica.tif")
with rasterio.open(ruta_prob, "w", **perfil_prob) as dst:
    dst.write(mapa_prob, 1)
print(f"Guardado: mapas/probabilidad_regresion_logistica.tif")

# --- 6. Clasificar en 5 clases de susceptibilidad (quintiles) ---
valores_validos = mapa_prob[~np.isnan(mapa_prob)]
quintiles = np.nanpercentile(valores_validos, [20, 40, 60, 80])
clases = np.full(forma_ref, np.nan, dtype=np.float32)
valido = ~np.isnan(mapa_prob)
clases[valido] = np.digitize(mapa_prob[valido], quintiles) + 1  # 1=Muy baja ... 5=Muy alta

ruta_clases = os.path.join(DIR_MAPAS, "susceptibilidad_regresion_logistica.tif")
with rasterio.open(ruta_clases, "w", **perfil_prob) as dst:
    dst.write(clases, 1)
print(f"Guardado: mapas/susceptibilidad_regresion_logistica.tif")

nombres_clase = {1: "Muy baja", 2: "Baja", 3: "Media", 4: "Alta", 5: "Muy alta"}
tabla_umbrales = pd.DataFrame({
    "clase": list(nombres_clase.values()),
    "probabilidad_min": [0] + list(quintiles),
    "probabilidad_max": list(quintiles) + [1],
})
tabla_umbrales.to_csv(f"{DIR_TABLAS}/umbrales_clases_susceptibilidad.csv", index=False, encoding="utf-8-sig")
print(f"Guardado: tablas/umbrales_clases_susceptibilidad.csv")

# --- 7. Distribución de área por clase ---
n_total_validas = int(valido.sum())
distribucion = []
for c, nombre in nombres_clase.items():
    n = int(np.sum(clases == c))
    distribucion.append({"clase": nombre, "n_celdas": n, "pct_area": round(100 * n / n_total_validas, 2)})
tabla_distribucion = pd.DataFrame(distribucion)
tabla_distribucion.to_csv(f"{DIR_TABLAS}/distribucion_area_clases_susceptibilidad.csv", index=False, encoding="utf-8-sig")
print(tabla_distribucion.to_string(index=False))
print(f"Guardado: tablas/distribucion_area_clases_susceptibilidad.csv")

# --- 8. Figura del mapa clasificado ---
colores = ["#1a9850", "#91cf60", "#fee08b", "#fc8d59", "#d73027"]
cmap = ListedColormap(colores)
norm = BoundaryNorm([0.5, 1.5, 2.5, 3.5, 4.5, 5.5], cmap.N)

fig, ax = plt.subplots(figsize=(9, 8))
im = ax.imshow(clases, cmap=cmap, norm=norm)
ax.set_title("Susceptibilidad a movimientos en masa — Regresión logística\n"
              "(uso_actual + geologia + geomorfologia + curvatura + dist_drenajes)")
ax.set_xticks([])
ax.set_yticks([])
cbar = fig.colorbar(im, ax=ax, ticks=[1, 2, 3, 4, 5], shrink=0.75)
cbar.ax.set_yticklabels(list(nombres_clase.values()))
plt.tight_layout()
plt.savefig(f"{DIR_FIGURAS}/mapa_susceptibilidad_regresion_logistica.png", dpi=180)
plt.close(fig)
print(f"Guardado: figuras/mapa_susceptibilidad_regresion_logistica.png")

# --- 9. Validación rápida: dónde caen los puntos de movimiento conocidos ---
puntos_mov = df_entrenamiento[df_entrenamiento["inventario"] == 1][VARIABLES_MODELO]
prob_en_movimientos = modelo.predict(puntos_mov)
clases_en_movimientos = np.digitize(prob_en_movimientos, quintiles) + 1
tabla_val = pd.Series(clases_en_movimientos).map(nombres_clase).value_counts().reindex(
    list(nombres_clase.values()), fill_value=0)
tabla_val_pct = (100 * tabla_val / tabla_val.sum()).round(1)
print("\nValidación: distribución de clase de susceptibilidad en los puntos de movimiento conocidos:")
print(pd.DataFrame({"n_puntos": tabla_val, "pct": tabla_val_pct}).to_string())
pd.DataFrame({"n_puntos": tabla_val, "pct": tabla_val_pct}).to_csv(
    f"{DIR_TABLAS}/validacion_movimientos_en_clases.csv", encoding="utf-8-sig")
print(f"Guardado: tablas/validacion_movimientos_en_clases.csv")
