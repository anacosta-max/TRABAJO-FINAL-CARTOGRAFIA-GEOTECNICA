# -*- coding: utf-8 -*-
"""
Prueba de DeLong (DeLong et al., 1988; algoritmo rápido de Sun & Xu, 2014)
para comparar estadísticamente el AUC de AHP+Combinado, Índices, WoE y
Regresión Logística (modelo completo, 100% de los datos) — los cuatro
evaluados sobre EXACTAMENTE los mismos 256 puntos del inventario, lo cual
es un requisito de la prueba (compara curvas ROC "pareadas", medidas
sobre los mismos sujetos).

Esto responde a la Actividad 3 del capítulo "Evaluación del modelo":
    "Traza las curvas ROC de los cuatro métodos... en el mismo gráfico.
    ¿Cuál tiene mayor AUC? ¿Es la diferencia estadísticamente significativa
    (prueba DeLong)?"

Nota: para la regresión se usa el modelo COMPLETO (ajustado con el 100%
de los 256 puntos), NO el de partición 80/20 de 03_ — porque DeLong exige
que las curvas se evalúen sobre el mismo conjunto de sujetos.
"""
import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
from scipy import stats

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_FIG = os.path.join(BASE, "figuras")
DIR_TAB = os.path.join(BASE, "tablas")

INVENTARIO_SHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\Resultados"
    r"\11_Inventario_Discriminado_Estratificado\inventario_nuevo\puntos_inventario_estratificado.shp"
)
RUTA_RASTER_WOE = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS"
    r"\14_WoE_Susceptibilidad\04_Mapa_Susceptibilidad_Final\susceptibilidad_WoE.tif"
)
RUTA_REGRESION = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS"
    r"\Resultados\13_Regresion_Logistica"
)
sys.path.insert(0, RUTA_REGRESION)
from config_base import cargar_datos, ajustar_modelo

VARIABLES_MODELO_FINAL = ["uso_actual", "geologia", "geomorfologia", "curvatura", "dist_drenajes"]


# ===========================================================================
# fastDeLong (Sun & Xu, 2014) — algoritmo estándar de referencia
# ===========================================================================
def _compute_midrank(x):
    J = np.argsort(x)
    Z = x[J]
    N = len(x)
    T = np.zeros(N, dtype=float)
    i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]:
            j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1
        i = j
    T2 = np.empty(N, dtype=float)
    T2[J] = T
    return T2


def _fast_delong(predictions_sorted_transposed, label_1_count):
    m = label_1_count
    n = predictions_sorted_transposed.shape[1] - m
    positive_examples = predictions_sorted_transposed[:, :m]
    negative_examples = predictions_sorted_transposed[:, m:]
    k = predictions_sorted_transposed.shape[0]

    tx = np.empty([k, m], dtype=float)
    ty = np.empty([k, n], dtype=float)
    tz = np.empty([k, m + n], dtype=float)
    for r in range(k):
        tx[r, :] = _compute_midrank(positive_examples[r, :])
        ty[r, :] = _compute_midrank(negative_examples[r, :])
        tz[r, :] = _compute_midrank(predictions_sorted_transposed[r, :])

    aucs = tz[:, :m].sum(axis=1) / m / n - float(m + 1.0) / 2.0 / n
    v01 = (tz[:, :m] - tx[:, :]) / n
    v10 = 1.0 - (tz[:, m:] - ty[:, :]) / m
    sx = np.cov(v01)
    sy = np.cov(v10)
    delongcov = sx / m + sy / n
    return aucs, delongcov


def delong_pairwise_pvalue(auc_i, auc_j, cov_ii, cov_jj, cov_ij):
    var_diff = cov_ii + cov_jj - 2 * cov_ij
    z = (auc_i - auc_j) / np.sqrt(var_diff)
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return z, p


def delong_roc_test(y_real, scores_dict):
    orden = np.argsort(-y_real, kind="stable")  # positivos (1) primero
    y_ordenado = y_real[orden]
    nombres = list(scores_dict.keys())
    preds = np.vstack([scores_dict[n][orden] for n in nombres])
    m = int((y_ordenado == 1).sum())

    aucs, cov = _fast_delong(preds, m)

    filas = []
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            z, p = delong_pairwise_pvalue(aucs[i], aucs[j], cov[i, i], cov[j, j], cov[i, j])
            filas.append({
                "modelo_A": nombres[i], "AUC_A": aucs[i],
                "modelo_B": nombres[j], "AUC_B": aucs[j],
                "diferencia_AUC": aucs[i] - aucs[j], "z": z, "p_valor": p,
                "significativo_p<0.05": p < 0.05,
            })
    return dict(zip(nombres, aucs)), pd.DataFrame(filas)


# ===========================================================================
# 1. CARGAR LOS 256 PUNTOS Y LOS 4 SCORES (mismo sujeto, mismo orden)
# ===========================================================================
scores_ahp = pd.read_csv(f"{DIR_TAB}/scores_ahp_indices_256puntos.csv")
y_real = scores_ahp["Y"].astype(int).values
score_ahp_comb = scores_ahp["score_AHP_Combinado"].values.astype(float)
# Nota: Índices también está disponible en scores_ahp["score_Indices"], pero
# por decisión del usuario se excluye de esta comparación (casi redundante
# con AHP+Combinado — mismo w_c, W_i muy similar).

puntos = gpd.read_file(INVENTARIO_SHP)
coords = [(geom.x, geom.y) for geom in puntos.geometry]
with rasterio.open(RUTA_RASTER_WOE) as src:
    score_woe = np.array([v[0] for v in src.sample(coords)], dtype=float)

# Modelo de regresión COMPLETO (100% de los datos, mismos 256 puntos)
df_completo = cargar_datos()
modelo_completo = ajustar_modelo(df_completo, VARIABLES_MODELO_FINAL)
score_regresion = modelo_completo.predict(df_completo).values

scores_dict = {
    "AHP+Combinado": score_ahp_comb,
    "WoE": score_woe, "Regresión Logística (completo)": score_regresion,
}

# ===========================================================================
# 2. PRUEBA DE DELONG PAREADA (los 4 modelos, mismos 256 sujetos)
# ===========================================================================
aucs, tabla_pvalores = delong_roc_test(y_real, scores_dict)

from sklearn.metrics import roc_auc_score
print("AUC (DeLong) vs. AUC (sklearn, verificación cruzada):")
for nombre, auc_val in aucs.items():
    print(f"  {nombre}: DeLong={auc_val:.4f}  sklearn={roc_auc_score(y_real, scores_dict[nombre]):.4f}")

print("\nComparación pareada (prueba de DeLong):")
print(tabla_pvalores.round(4).to_string(index=False))

tabla_pvalores.to_csv(f"{DIR_TAB}/delong_comparacion_pareada.csv", index=False, encoding="utf-8-sig")
print(f"\nGuardado: tablas/delong_comparacion_pareada.csv")

# ===========================================================================
# 3. FIGURA — LOS 3 MODELOS JUNTOS (Actividad 3 del capítulo)
# ===========================================================================
from sklearn.metrics import roc_curve

fig, ax = plt.subplots(figsize=(7.5, 7.5))
colores = {"AHP+Combinado": "#1F4E79", "WoE": "#C0392B",
           "Regresión Logística (completo)": "#1E7B34"}
for nombre, score in scores_dict.items():
    fpr, tpr, _ = roc_curve(y_real, score)
    ax.plot(fpr, tpr, color=colores[nombre], lw=2, label=f"{nombre} (AUC = {aucs[nombre]:.3f})")
ax.plot([0, 1], [0, 1], color="gray", lw=1, linestyle="--", label="Predicción aleatoria (AUC = 0.5)")
ax.set_xlabel("FPR = 1 - especificidad")
ax.set_ylabel("TPR (sensibilidad)")
ax.set_title("Comparación de los 3 modelos — mismos 256 puntos\n(Actividad 3, capítulo Evaluación del modelo)")
ax.legend(loc="lower right", fontsize=9)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{DIR_FIG}/roc_comparacion_3_modelos_delong.png", dpi=180)
plt.close(fig)
print(f"Guardado: figuras/roc_comparacion_3_modelos_delong.png")
