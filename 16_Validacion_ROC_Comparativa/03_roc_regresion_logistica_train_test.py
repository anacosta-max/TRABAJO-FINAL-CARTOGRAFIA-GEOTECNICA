# -*- coding: utf-8 -*-
"""
Curva ROC / AUC para el modelo final de Regresión Logística
(13_Regresion_Logistica), con partición 80/20 tal como piden las notas de
clase para métodos estadísticos/de datos:

    "Para regresión logística, mínimo hacer la partición de 80-20..."
    "Podemos tener el área bajo la curva con los valores de entrenamiento
    o el área bajo la curva con los datos de validación. El mejor modelo
    es el que tenga el área bajo la curva más grande."
    "La curva de éxito es la de validación. La curva de predicción es la
    de entrenamiento."

Metodología:
  1. Partición estratificada 80/20 del inventario de 256 puntos (preserva
     la proporción de movimiento/NO en ambos subconjuntos).
  2. Se agrupan las categorías raras (<5 obs) SOLO con los conteos del
     80% de entrenamiento (para no filtrar información del 20% de prueba
     hacia el preprocesamiento) y se aplica la misma agrupación al 20%.
  3. Se reajustan los COEFICIENTES del modelo final ya seleccionado
     (uso_actual + geologia + geomorfologia + curvatura + dist_drenajes;
     la selección de variables ya se hizo con AIC sobre el 100% de los
     datos en 13_Regresion_Logistica/02-05, aquí solo se re-estima con el
     80%) usando SOLO el 80% de entrenamiento.
  4. Se calculan las probabilidades predichas y la curva ROC tanto sobre
     el propio 80% de entrenamiento (curva de predicción) como sobre el
     20% de prueba nunca visto por el modelo (curva de éxito/validación).
"""
import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_curve, auc

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_FIG = os.path.join(BASE, "figuras")
DIR_TAB = os.path.join(BASE, "tablas")

RUTA_REGRESION = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS"
    r"\Resultados\13_Regresion_Logistica"
)
sys.path.insert(0, RUTA_REGRESION)
from config_base import (
    INVENTARIO_SHP, RENOMBRAR_COLUMNAS, COLUMNA_PRESENCIA, TODAS_LAS_VARIABLES,
    VARIABLES_CATEGORICAS, MIN_OBS_CATEGORIA, CODIGO_OTRAS,
    construir_formula, ajustar_modelo,
)

VARIABLES_MODELO_FINAL = ["uso_actual", "geologia", "geomorfologia", "curvatura", "dist_drenajes"]
SEMILLA = 42

# ===========================================================================
# 1. CARGAR DATOS CRUDOS (sin agrupar categorías todavía)
# ===========================================================================
puntos = gpd.read_file(INVENTARIO_SHP).rename(columns=RENOMBRAR_COLUMNAS)
df = puntos[TODAS_LAS_VARIABLES + [COLUMNA_PRESENCIA]].copy().rename(columns={COLUMNA_PRESENCIA: "inventario"})
df["inventario"] = df["inventario"].astype(int)

print(f"Inventario completo: {len(df)} puntos ({df['inventario'].sum()} movimiento, "
      f"{(df['inventario'] == 0).sum()} NO)")

# ===========================================================================
# 2. PARTICIÓN ESTRATIFICADA 80/20
# ===========================================================================
df_train, df_test = train_test_split(
    df, test_size=0.20, stratify=df["inventario"], random_state=SEMILLA
)
print(f"\nEntrenamiento (80%): {len(df_train)} puntos "
      f"({df_train['inventario'].sum()} movimiento, {(df_train['inventario'] == 0).sum()} NO)")
print(f"Prueba/validación (20%): {len(df_test)} puntos "
      f"({df_test['inventario'].sum()} movimiento, {(df_test['inventario'] == 0).sum()} NO)")

# ===========================================================================
# 3. AGRUPAR CATEGORÍAS RARAS — SOLO CON EL 80% DE ENTRENAMIENTO,
#    y aplicar la MISMA agrupación al 20% de prueba (sin recalcularla ahí)
# ===========================================================================
def construir_mapeo_categorias(df_train, variables_categoricas, min_obs=MIN_OBS_CATEGORIA):
    mapeos = {}
    registro = []
    for var in variables_categoricas:
        conteos = df_train[var].value_counts()
        raras = conteos[conteos < min_obs].index.tolist()
        mapeo = {c: c for c in conteos.index}
        if raras:
            n_otras = int(conteos.loc[raras].sum())
            destino = CODIGO_OTRAS if n_otras >= min_obs else conteos.drop(index=raras).idxmax()
            for c in raras:
                mapeo[c] = destino
                registro.append({"variable": var, "categoria_original": c,
                                  "n_obs_train": int(conteos[c]), "destino": destino})
        mapeos[var] = mapeo
    return mapeos, pd.DataFrame(registro)


def aplicar_mapeo_categorias(df, mapeos, variables_a_verificar):
    """Aplica el mapeo aprendido en train. Las filas cuyo valor en alguna
    variable REALMENTE USADA POR EL MODELO no existe de ninguna forma en
    train (ni como categoría propia ni agrupada) no se pueden predecir de
    forma válida (el modelo no tiene coeficiente para ese nivel) y se
    marcan para excluir de la evaluación, en vez de forzarlas a un valor
    arbitrario."""
    df = df.copy()
    fila_predecible = np.ones(len(df), dtype=bool)
    categorias_no_vistas = []
    for var, mapeo in mapeos.items():
        no_vistas = ~df[var].isin(mapeo.keys())
        if no_vistas.any() and var in variables_a_verificar:
            categorias_no_vistas.append((var, df.loc[no_vistas, var].unique().tolist()))
            fila_predecible &= ~no_vistas
        df[var] = df[var].where(~no_vistas, list(mapeo.values())[0])  # valor de relleno; la fila se excluye igual
        df[var] = df[var].map(lambda c: mapeo.get(c, c))
    return df, fila_predecible, categorias_no_vistas


mapeos, registro_agrupacion = construir_mapeo_categorias(df_train, VARIABLES_CATEGORICAS)
registro_agrupacion.to_csv(f"{DIR_TAB}/categorias_agrupadas_train.csv", index=False, encoding="utf-8-sig")
print(f"\nCategorías agrupadas usando SOLO el 80% de entrenamiento:")
print(registro_agrupacion.to_string(index=False) if len(registro_agrupacion) else "  (ninguna)")

variables_categoricas_del_modelo = [v for v in VARIABLES_MODELO_FINAL if v in VARIABLES_CATEGORICAS]
df_train_c, _, _ = aplicar_mapeo_categorias(df_train, mapeos, variables_categoricas_del_modelo)
df_test_c, predecible_test, no_vistas_test = aplicar_mapeo_categorias(df_test, mapeos, variables_categoricas_del_modelo)

n_excluidos = int((~predecible_test).sum())
if n_excluidos > 0:
    print(f"\nADVERTENCIA — {n_excluidos} punto(s) del 20% de prueba tienen una categoría (en una "
          f"variable usada por el modelo final) nunca vista en el 80% de entrenamiento: {no_vistas_test}. "
          f"Se EXCLUYEN de la evaluación (el modelo no tiene coeficiente para predecirlos de forma válida).")
    df_test_c = df_test_c.loc[predecible_test].copy()
else:
    print("\nTodas las categorías del 20% de prueba (en variables usadas por el modelo) "
          "ya existían en el 80% de entrenamiento.")

# ===========================================================================
# 4. REAJUSTAR EL MODELO FINAL SOLO CON EL 80% DE ENTRENAMIENTO
# ===========================================================================
modelo_train = ajustar_modelo(df_train_c, VARIABLES_MODELO_FINAL)
if modelo_train is None:
    raise RuntimeError("El modelo no convergió de forma sana con el 80% de entrenamiento.")

print(f"\nModelo reajustado con el 80% de entrenamiento:")
print(f"  Fórmula: {construir_formula(VARIABLES_MODELO_FINAL)}")
print(f"  AIC={modelo_train.aic:.2f}  Pseudo R2={modelo_train.prsquared:.4f}")

with open(f"{DIR_TAB}/regresion_modelo_train_resumen.txt", "w", encoding="utf-8") as f:
    f.write(f"Modelo final reajustado SOLO con el 80 por ciento de entrenamiento (n={len(df_train_c)})\n\n")
    f.write(str(modelo_train.summary()))

# ===========================================================================
# 5. PROBABILIDADES PREDICHAS EN TRAIN Y EN TEST, CURVAS ROC
# ===========================================================================
prob_train = modelo_train.predict(df_train_c)
prob_test = modelo_train.predict(df_test_c)

y_train = df_train_c["inventario"].values
y_test = df_test_c["inventario"].values

fpr_train, tpr_train, _ = roc_curve(y_train, prob_train)
auc_train = auc(fpr_train, tpr_train)

fpr_test, tpr_test, _ = roc_curve(y_test, prob_test)
auc_test = auc(fpr_test, tpr_test)

print(f"\nAUC entrenamiento (curva de predicción): {auc_train:.4f}  (n={len(y_train)})")
print(f"AUC prueba/validación (curva de éxito):    {auc_test:.4f}  (n={len(y_test)})")
print(f"Diferencia (train - test): {auc_train - auc_test:+.4f}")

pd.DataFrame([
    {"conjunto": "Entrenamiento (curva de predicción)", "n": len(y_train), "AUC": auc_train},
    {"conjunto": "Prueba/validación (curva de éxito)", "n": len(y_test), "AUC": auc_test},
]).to_csv(f"{DIR_TAB}/regresion_auc_train_test.csv", index=False, encoding="utf-8-sig")

# ===========================================================================
# 6. FIGURA — LAS DOS CURVAS JUNTAS
# ===========================================================================
fig, ax = plt.subplots(figsize=(6.5, 6.5))
ax.plot(fpr_train, tpr_train, color="#1F4E79", lw=2,
        label=f"Entrenamiento / curva de predicción (AUC = {auc_train:.3f}, n={len(y_train)})")
ax.plot(fpr_test, tpr_test, color="#C0392B", lw=2,
        label=f"Prueba (20%) / curva de éxito (AUC = {auc_test:.3f}, n={len(y_test)})")
ax.plot([0, 1], [0, 1], color="gray", lw=1, linestyle="--", label="Predicción aleatoria (AUC = 0.5)")
ax.set_xlabel("FPR = 1 - especificidad")
ax.set_ylabel("TPR (sensibilidad)")
ax.set_title("Curva ROC — Regresión Logística\nPartición 80/20 (entrenamiento vs. validación)")
ax.legend(loc="lower right", fontsize=9)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{DIR_FIG}/roc_regresion_logistica_train_test.png", dpi=180)
plt.close(fig)
print(f"\nGuardado: figuras/roc_regresion_logistica_train_test.png")
print(f"Guardado: tablas/regresion_auc_train_test.csv")
print(f"Guardado: tablas/regresion_modelo_train_resumen.txt")
print(f"Guardado: tablas/categorias_agrupadas_train.csv")
