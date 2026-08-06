"""
CÓDIGO 3 (variante): MATRIZ DE CORRELACIÓN — INVENTARIO ESTRATIFICADO (v2)
================================================================
Misma lógica que 03_correlacion_variables.py, pero usando el inventario
generado en `11_Inventario_Discriminado_Estratificado` (128 movimientos +
128 puntos "NO" con disimilitud moderada y muestreo espacialmente
estratificado) en vez de la muestra balanceada original o la v1 (extrema).

Se guarda en subcarpetas separadas (tablas_estratificado/, figuras_estratificado/).

Salidas:
  - tablas_estratificado/matriz_correlacion_pearson.csv
  - tablas_estratificado/matriz_correlacion_spearman.csv
  - tablas_estratificado/correlacion_con_inventario.csv
  - tablas_estratificado/pares_alta_correlacion.csv
  - figuras_estratificado/matriz_correlacion_pearson.png
  - figuras_estratificado/matriz_correlacion_spearman.png
"""

import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings("ignore")

# -------------------------------------------------------------------------
# Configuración de rutas
# -------------------------------------------------------------------------
INVENTARIO_ESTRATIFICADO_SHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\Resultados"
    r"\11_Inventario_Discriminado_Estratificado\inventario_nuevo\puntos_inventario_estratificado.shp"
)

CARPETA_SALIDA = os.path.dirname(os.path.abspath(__file__))
DIR_TABLAS = os.path.join(CARPETA_SALIDA, "tablas_estratificado")
DIR_FIGURAS = os.path.join(CARPETA_SALIDA, "figuras_estratificado")
os.makedirs(DIR_TABLAS, exist_ok=True)
os.makedirs(DIR_FIGURAS, exist_ok=True)

VARIABLES_CATEGORICAS = ["cobertura", "uso_actual", "geologia", "geomorfologia"]
VARIABLES_NUMERICAS = ["pendiente", "aspecto", "curvatura", "flujo_acum", "elevacion", "dist_drenajes"]
TODAS_LAS_VARIABLES = VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS

RENOMBRAR_COLUMNAS = {"dist_drena": "dist_drenajes", "geomorfolo": "geomorfologia"}
COLUMNA_PRESENCIA = "Y"
UMBRAL_MULTICOLINEALIDAD = 0.7

print("=" * 60)
print("CÓDIGO 3 (INVENTARIO ESTRATIFICADO v2): CORRELACIÓN DE VARIABLES")
print("=" * 60)

# -------------------------------------------------------------------------
# Carga del inventario estratificado
# -------------------------------------------------------------------------
puntos = gpd.read_file(INVENTARIO_ESTRATIFICADO_SHP).rename(columns=RENOMBRAR_COLUMNAS)
df = puntos[TODAS_LAS_VARIABLES + [COLUMNA_PRESENCIA]].copy()
df = df.rename(columns={COLUMNA_PRESENCIA: "inventario"})

print(f"Movimientos ('sí'): {(df['inventario']==1).sum()}")
print(f"NO estratificados ('no'): {(df['inventario']==0).sum()}")
print(f"Muestra total: {df.shape}")

# -------------------------------------------------------------------------
# Matrices de correlación
# -------------------------------------------------------------------------
print("\n" + "=" * 50)
print("CALCULANDO CORRELACIONES")
print("=" * 50)

corr_pearson = df.corr(method="pearson")
corr_spearman = df.corr(method="spearman")

corr_pearson.to_csv(os.path.join(DIR_TABLAS, "matriz_correlacion_pearson.csv"))
corr_spearman.to_csv(os.path.join(DIR_TABLAS, "matriz_correlacion_spearman.csv"))

corr_inventario = pd.DataFrame({
    "variable": [v for v in TODAS_LAS_VARIABLES],
    "pearson_r": [corr_pearson.loc[v, "inventario"] for v in TODAS_LAS_VARIABLES],
    "spearman_r": [corr_spearman.loc[v, "inventario"] for v in TODAS_LAS_VARIABLES],
})
corr_inventario["abs_spearman"] = corr_inventario["spearman_r"].abs()
corr_inventario = corr_inventario.sort_values("abs_spearman", ascending=False).drop(columns="abs_spearman")
corr_inventario.to_csv(os.path.join(DIR_TABLAS, "correlacion_con_inventario.csv"), index=False)

print("\nCorrelación de cada variable con el inventario (movimiento=1 / NO estratificado=0):")
print(f"{'Variable':<16}{'Pearson r':<12}{'Spearman r':<12}")
for _, row in corr_inventario.iterrows():
    print(f"{row['variable']:<16}{row['pearson_r']:<12.3f}{row['spearman_r']:<12.3f}")

# -------------------------------------------------------------------------
# Multicolinealidad entre predictoras
# -------------------------------------------------------------------------
print("\n" + "=" * 50)
print(f"PARES DE VARIABLES CON |r| >= {UMBRAL_MULTICOLINEALIDAD} (Spearman)")
print("=" * 50)

pares = []
predictoras = TODAS_LAS_VARIABLES
for i, v1 in enumerate(predictoras):
    for v2 in predictoras[i + 1:]:
        r = corr_spearman.loc[v1, v2]
        if abs(r) >= UMBRAL_MULTICOLINEALIDAD:
            pares.append({"variable_1": v1, "variable_2": v2, "spearman_r": round(r, 3)})

df_pares = pd.DataFrame(pares).sort_values("spearman_r", key=abs, ascending=False) if pares else pd.DataFrame(
    columns=["variable_1", "variable_2", "spearman_r"])
df_pares.to_csv(os.path.join(DIR_TABLAS, "pares_alta_correlacion.csv"), index=False)

if len(df_pares) == 0:
    print(f"Ningún par de variables predictoras supera |r| = {UMBRAL_MULTICOLINEALIDAD}.")
else:
    for _, row in df_pares.iterrows():
        print(f"  {row['variable_1']:<16} <-> {row['variable_2']:<16}  r = {row['spearman_r']}")

# -------------------------------------------------------------------------
# Heatmaps
# -------------------------------------------------------------------------
print("\n" + "=" * 50)
print("GENERANDO HEATMAPS")
print("=" * 50)

for nombre, matriz in [("pearson", corr_pearson), ("spearman", corr_spearman)]:
    plt.figure(figsize=(11, 9))
    sns.heatmap(matriz, annot=True, fmt=".2f", cmap="coolwarm", center=0,
                square=True, linewidths=0.5, cbar_kws={"shrink": 0.8})
    plt.title(f"Matriz de correlación ({nombre.capitalize()}) — inventario estratificado v2 (128/128)")
    plt.tight_layout()
    plt.savefig(os.path.join(DIR_FIGURAS, f"matriz_correlacion_{nombre}.png"), dpi=200)
    plt.close()

print(f"Guardado en: {DIR_TABLAS}")
print(f"Figuras en:  {DIR_FIGURAS}")

print("\n" + "=" * 60)
print("RESUMEN FINAL - CÓDIGO 3 (INVENTARIO ESTRATIFICADO v2)")
print("=" * 60)
print(f"Variables analizadas: {len(TODAS_LAS_VARIABLES)}")
print(f"Observaciones: {len(df)} (128 con movimiento + 128 NO estratificados)")
print(f"Pares con multicolinealidad (|r|>={UMBRAL_MULTICOLINEALIDAD}): {len(df_pares)}")
print("=" * 60)
