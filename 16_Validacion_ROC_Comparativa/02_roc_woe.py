# -*- coding: utf-8 -*-
"""
Curva ROC / AUC para el método WoE — Peso de la Evidencia
(14_WoE_Susceptibilidad, sin cambios respecto a la versión anterior), UNA
sola curva, sin partición 80/20 — mismo criterio que en AHP+Combinado e
Índices (ver 01_roc_ahp.py): "Para los métodos heurísticos (por ejemplo
peso de la evidencia y asignación de pesos), se debe hacer al menos una
curva ROC."

Se extrae el raster ya calculado (susceptibilidad_WoE.tif) en los 256
puntos del inventario oficial (mismo inventario que usa AHP en 01_).
"""
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt

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


def curva_roc_manual(y_real, score):
    umbrales = np.sort(np.unique(score))[::-1]
    umbrales = np.concatenate(([umbrales[0] + 1e-9], umbrales, [umbrales[-1] - 1e-9]))
    P = (y_real == 1).sum()
    N = (y_real == 0).sum()
    filas = []
    for u in umbrales:
        pred = (score >= u).astype(int)
        TP = int(((pred == 1) & (y_real == 1)).sum())
        FP = int(((pred == 1) & (y_real == 0)).sum())
        TN = int(((pred == 0) & (y_real == 0)).sum())
        FN = int(((pred == 0) & (y_real == 1)).sum())
        TPR = TP / P if P > 0 else 0.0
        FPR = FP / N if N > 0 else 0.0
        filas.append({"umbral": u, "TP": TP, "FP": FP, "TN": TN, "FN": FN, "TPR": TPR, "FPR": FPR})
    tabla = pd.DataFrame(filas).sort_values("FPR").reset_index(drop=True)
    auc_manual = np.trapezoid(tabla["TPR"], tabla["FPR"])
    return tabla, auc_manual


# ===========================================================================
# 1. CARGAR PUNTOS Y EXTRAER EL VALOR DEL RASTER WoE EN CADA UNO
# ===========================================================================
puntos = gpd.read_file(INVENTARIO_SHP)
y_real = puntos["Y"].astype(int).values
coords = [(geom.x, geom.y) for geom in puntos.geometry]

with rasterio.open(RUTA_RASTER_WOE) as src:
    valores = np.array([v[0] for v in src.sample(coords)], dtype=float)
    nodata = src.nodata
    if nodata is not None and not np.isnan(nodata):
        valores = np.where(valores == nodata, np.nan, valores)

n_nulos = int(np.isnan(valores).sum())
print(f"Puntos: {len(puntos)}  |  celdas NoData en el raster WoE: {n_nulos}")
if n_nulos > 0:
    print(f"  ADVERTENCIA: se excluyen {n_nulos} puntos por caer en NoData del raster WoE")
valido = ~np.isnan(valores)
y_real_v = y_real[valido]
score_v = valores[valido]

print(f"Puntos usados en la validación: {len(score_v)}  "
      f"(movimiento={int(y_real_v.sum())}, NO={int((y_real_v == 0).sum())})")
print(f"Índice WoE: min={score_v.min():.3f}  max={score_v.max():.3f}  media={score_v.mean():.3f}")

# ===========================================================================
# 2. CURVA ROC "A MANO" + VERIFICACIÓN CON SKLEARN
# ===========================================================================
tabla_roc, auc_manual = curva_roc_manual(y_real_v, score_v)
tabla_roc.to_csv(f"{DIR_TAB}/roc_woe_puntos_umbral.csv", index=False, encoding="utf-8-sig")
print(f"\nAUC (regla del trapecio, a mano): {auc_manual:.4f}")

from sklearn.metrics import roc_curve, auc as auc_sklearn
fpr_skl, tpr_skl, _ = roc_curve(y_real_v, score_v)
auc_skl = auc_sklearn(fpr_skl, tpr_skl)
print(f"AUC (sklearn.roc_curve, verificación): {auc_skl:.4f}")

# ===========================================================================
# 3. MATRIZ DE CONFUSIÓN A UN UMBRAL DE REFERENCIA (mediana)
# ===========================================================================
umbral_ref = float(np.median(score_v))
pred_ref = (score_v >= umbral_ref).astype(int)
TP = int(((pred_ref == 1) & (y_real_v == 1)).sum())
FP = int(((pred_ref == 1) & (y_real_v == 0)).sum())
TN = int(((pred_ref == 0) & (y_real_v == 0)).sum())
FN = int(((pred_ref == 0) & (y_real_v == 1)).sum())
exactitud = (TP + TN) / len(y_real_v)
precision = TP / (TP + FP) if (TP + FP) > 0 else np.nan
recall_sens = TP / (TP + FN) if (TP + FN) > 0 else np.nan
especificidad = TN / (TN + FP) if (TN + FP) > 0 else np.nan

print(f"\nMatriz de confusión al umbral de referencia (mediana={umbral_ref:.3f}):")
print(f"  TP={TP}  FP={FP}  TN={TN}  FN={FN}")
print(f"  Exactitud={exactitud:.4f}  Precisión={precision:.4f}  "
      f"Recall/Sensibilidad={recall_sens:.4f}  Especificidad={especificidad:.4f}")

pd.DataFrame([{
    "modelo": "WoE", "n_puntos_validos": len(score_v), "umbral_referencia": umbral_ref,
    "TP": TP, "FP": FP, "TN": TN, "FN": FN, "exactitud": exactitud, "precision": precision,
    "recall_sensibilidad": recall_sens, "especificidad": especificidad, "AUC": auc_manual,
}]).to_csv(f"{DIR_TAB}/woe_matriz_confusion_resumen.csv", index=False, encoding="utf-8-sig")

# ===========================================================================
# 4. FIGURA
# ===========================================================================
fig, ax = plt.subplots(figsize=(6, 6))
ax.plot(tabla_roc["FPR"], tabla_roc["TPR"], color="#C0392B", lw=2,
        label=f"WoE — 1 curva, sin partición (AUC = {auc_manual:.3f})")
ax.plot([0, 1], [0, 1], color="gray", lw=1, linestyle="--", label="Predicción aleatoria (AUC = 0.5)")
ax.set_xlabel("FPR = 1 - especificidad")
ax.set_ylabel("TPR (sensibilidad)")
ax.set_title("Curva ROC — Método WoE (Peso de la Evidencia)")
ax.legend(loc="lower right")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{DIR_FIG}/roc_woe.png", dpi=180)
plt.close(fig)
print(f"\nGuardado: figuras/roc_woe.png")
print(f"Guardado: tablas/roc_woe_puntos_umbral.csv")
print(f"Guardado: tablas/woe_matriz_confusion_resumen.csv")
