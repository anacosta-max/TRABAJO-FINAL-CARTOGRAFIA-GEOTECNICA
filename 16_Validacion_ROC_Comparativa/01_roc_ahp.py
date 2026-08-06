# -*- coding: utf-8 -*-
"""
Curva ROC / AUC para el método AHP + Combinado y para el método de Índices
(proyecto_susceptibilidad_AHP), con una MODIFICACIÓN pedida por el
profesor: el peso de clase (w_c) de las 4 variables CATEGÓRICAS
(geología, geomorfología, cobertura, uso_actual) ya NO viene de literatura
— se recalcula con Frequency Ratio sobre el inventario real de 256 puntos
(ver ahp_fr_pesos.py), para que la reclasificación se base en los datos
propios y no en criterio experto genérico. Las 6 variables CONTINUAS
(pendiente, aspecto, curvatura, flujo_acum, elevación, dist_drenajes)
siguen usando los rangos de literatura de
proyecto_susceptibilidad_AHP/data/pesos_clase_continuas.csv, sin cambios
— así se decidió explícitamente (alcance acotado a las categóricas).
El peso de variable (W_i, tanto AHP como Índices) tampoco cambia: sigue
siendo 100% juicio experto (matriz AHP / asignación directa), eso es
estructural del método y no se toca.

El proyecto original está pensado para ArcGIS Pro (usa arcpy para leer/
reclasificar rasters). Como no necesitamos el raster completo para la
validación ROC —solo el valor del índice en los 256 puntos del inventario—
este script recalcula S_n directamente en Python, punto por punto.

Como en 15_Validacion_ROC_Comparativa: al ser un método heurístico (los
pesos de VARIABLE no se ajustan por optimización contra los datos), se
calcula UNA sola curva ROC con el 100% del inventario, "a mano" (sweep
manual de umbrales), siguiendo la nota de clase: "Para los métodos
heurísticos... se debe hacer al menos una curva ROC".
"""
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from scipy import stats
from ahp_fr_pesos import calcular_pesos_clase_FR

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_FIG = os.path.join(BASE, "figuras")
DIR_TAB = os.path.join(BASE, "tablas")

DATA_AHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS"
    r"\proyecto_susceptibilidad_AHP\proyecto_susceptibilidad_AHP\data"
)
INVENTARIO_SHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\Resultados"
    r"\11_Inventario_Discriminado_Estratificado\inventario_nuevo\puntos_inventario_estratificado.shp"
)
RENOMBRAR_COLUMNAS = {"dist_drena": "dist_drenajes", "geomorfolo": "geomorfologia"}

VARIABLES = ["pendiente", "aspecto", "curvatura", "flujo_acum", "elevacion",
             "dist_drenajes", "cobertura", "uso_actual", "geologia", "geomorfologia"]


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
# 1. CARGAR PESOS DESDE proyecto_susceptibilidad_AHP/data
# ===========================================================================
def parse_fraccion(x):
    x = str(x)
    if "/" in x:
        num, den = x.split("/")
        return float(num) / float(den)
    return float(x)


df_pesos_var = pd.read_csv(f"{DATA_AHP}/pesos_variables.csv", index_col=0)
pesos_ahp = df_pesos_var["peso_ahp"].to_dict()
pesos_indices = df_pesos_var["peso_indices"].to_dict()

df_continuas = pd.read_csv(f"{DATA_AHP}/pesos_clase_continuas.csv")

# w_c de las 4 categóricas: Frequency Ratio sobre el inventario real
# (reemplaza los CSV de literatura pesos_clase_geologia/geomorfologia/
# cobertura/uso_actual.csv, por decisión del profesor)
mapas_categoricos, valores_neutrales_fr, registro_fr = calcular_pesos_clase_FR()
registro_fr.to_csv(f"{DIR_TAB}/pesos_clase_FR_categoricas.csv", index=False, encoding="utf-8-sig")
print("Pesos de clase (w_c) recalculados con Frequency Ratio (categóricas):")
print(registro_fr.to_string(index=False))
print(f"Guardado: tablas/pesos_clase_FR_categoricas.csv\n")

print("Pesos de variable (AHP vs. Índices) — sin cambios, siguen siendo literatura/AHP:")
print(df_pesos_var[["peso_ahp", "peso_indices"]].to_string())

# ===========================================================================
# 2. CARGAR LOS 256 PUNTOS DEL INVENTARIO Y RECLASIFICAR CADA VARIABLE
#    (misma lógica exacta que ahp_susceptibilidad.py, a nivel de punto)
# ===========================================================================
puntos = gpd.read_file(INVENTARIO_SHP).rename(columns=RENOMBRAR_COLUMNAS)
y_real = puntos["Y"].astype(int).values
print(f"\nPuntos: {len(puntos)} (movimiento={int(y_real.sum())}, NO={int((y_real == 0).sum())})")

wc_por_variable = {}  # {variable: array de w_c por punto}

for _, fila in df_continuas.groupby("variable"):
    var = fila["variable"].iloc[0]
    valores = puntos[var].values.astype(float)
    wc = np.full(len(valores), np.nan)
    for _, row in fila.iterrows():
        mask = (valores >= row["rango_min"]) & (valores < row["rango_max"])
        wc = np.where(mask, row["peso_wc"], wc)
    if var == "aspecto":
        norte_mask = (valores >= 315) | (valores < 45)
        peso_norte = df_continuas[(df_continuas.variable == "aspecto") &
                                   (df_continuas.rango_min == 315)]["peso_wc"].values[0]
        wc = np.where(norte_mask, peso_norte, wc)
    n_sin_clase = int(np.isnan(wc).sum())
    if n_sin_clase > 0:
        print(f"  ADVERTENCIA [{var}]: {n_sin_clase} puntos sin regla de reclasificación (valor fuera de rango)")
    wc_por_variable[var] = wc

for var, mapeo in mapas_categoricos.items():
    valores = puntos[var].values
    wc = np.full(len(valores), np.nan)
    for codigo, peso in mapeo.items():
        wc = np.where(valores == codigo, peso, wc)
    n_sin_clase = int(np.isnan(wc).sum())
    if n_sin_clase > 0:
        print(f"  ADVERTENCIA [{var}]: {n_sin_clase} puntos sin regla de reclasificación "
              f"(código no está en la tabla de pesos): "
              f"{sorted(set(valores[np.isnan(wc)]))}")
    wc_por_variable[var] = wc

# ===========================================================================
# 3. COMBINAR: S_n = sum(W_i * w_c_i) — para AHP y para Índices
# ===========================================================================
def calcular_Sn(pesos_variable):
    Sn = np.zeros(len(puntos))
    for var in VARIABLES:
        Sn += pesos_variable[var] * np.nan_to_num(wc_por_variable[var], nan=0.0)
    return Sn


score_ahp = calcular_Sn(pesos_ahp)
score_indices = calcular_Sn(pesos_indices)

print(f"\nS_n AHP+Combinado:  min={score_ahp.min():.3f}  max={score_ahp.max():.3f}  media={score_ahp.mean():.3f}")
print(f"S_n Índices:        min={score_indices.min():.3f}  max={score_indices.max():.3f}  media={score_indices.mean():.3f}")

# Validación cruzada: t-test (mismo criterio que ahp_susceptibilidad.py) —
# para verificar que el recálculo en Python coincide con el reportado en el README
t_ahp, p_ahp = stats.ttest_ind(score_ahp[y_real == 1], score_ahp[y_real == 0])
print(f"\nT-test AHP+Combinado (con w_c por Frequency Ratio en las categóricas): "
      f"media_mov={score_ahp[y_real==1].mean():.3f}  media_est={score_ahp[y_real==0].mean():.3f}  "
      f"t={t_ahp:.3f}  p={p_ahp:.4g}  "
      f"(antes, con w_c 100% literatura: media_mov=0.548, media_est=0.536, t=1.076, p=0.2828, NO significativo)")

# ===========================================================================
# 4. CURVA ROC "A MANO" PARA CADA MÉTODO
# ===========================================================================
resultados = {}
for nombre, score in [("AHP+Combinado", score_ahp), ("Indices", score_indices)]:
    tabla_roc, auc_manual = curva_roc_manual(y_real, score)
    tabla_roc.to_csv(f"{DIR_TAB}/roc_{nombre.lower()}_puntos_umbral.csv", index=False, encoding="utf-8-sig")

    from sklearn.metrics import roc_curve, auc as auc_sklearn
    fpr_skl, tpr_skl, _ = roc_curve(y_real, score)
    auc_skl = auc_sklearn(fpr_skl, tpr_skl)

    umbral_ref = float(np.median(score))
    pred_ref = (score >= umbral_ref).astype(int)
    TP = int(((pred_ref == 1) & (y_real == 1)).sum())
    FP = int(((pred_ref == 1) & (y_real == 0)).sum())
    TN = int(((pred_ref == 0) & (y_real == 0)).sum())
    FN = int(((pred_ref == 0) & (y_real == 1)).sum())
    exactitud = (TP + TN) / len(y_real)
    precision = TP / (TP + FP) if (TP + FP) > 0 else np.nan
    recall_sens = TP / (TP + FN) if (TP + FN) > 0 else np.nan
    especificidad = TN / (TN + FP) if (TN + FP) > 0 else np.nan

    print(f"\n=== {nombre} ===")
    print(f"AUC (a mano, trapecio): {auc_manual:.4f}  |  AUC (sklearn, verificación): {auc_skl:.4f}")
    print(f"Umbral de referencia (mediana={umbral_ref:.3f}): TP={TP} FP={FP} TN={TN} FN={FN}")
    print(f"Exactitud={exactitud:.4f}  Precisión={precision:.4f}  Sensibilidad={recall_sens:.4f}  "
          f"Especificidad={especificidad:.4f}")

    pd.DataFrame([{
        "modelo": nombre, "umbral_referencia": umbral_ref, "TP": TP, "FP": FP, "TN": TN, "FN": FN,
        "exactitud": exactitud, "precision": precision, "recall_sensibilidad": recall_sens,
        "especificidad": especificidad, "AUC": auc_manual,
    }]).to_csv(f"{DIR_TAB}/{nombre.lower()}_matriz_confusion_resumen.csv", index=False, encoding="utf-8-sig")

    resultados[nombre] = {"tabla_roc": tabla_roc, "auc": auc_manual, "score": score}

# guardar los scores punto a punto también (útil para 04_/05_/06_)
puntos_export = pd.DataFrame({
    "Y": y_real, "score_AHP_Combinado": score_ahp, "score_Indices": score_indices,
})
puntos_export.to_csv(f"{DIR_TAB}/scores_ahp_indices_256puntos.csv", index=False, encoding="utf-8-sig")

# ===========================================================================
# 5. FIGURA — solo AHP+Combinado (Índices se sigue calculando arriba como
#    referencia/verificación, pero por decisión del usuario ya NO se
#    incluye en las gráficas ni en el informe comparativo: es casi
#    redundante con AHP+Combinado, mismo w_c, W_i muy similar)
# ===========================================================================
fig, ax = plt.subplots(figsize=(6.5, 6.5))
ax.plot(resultados["AHP+Combinado"]["tabla_roc"]["FPR"], resultados["AHP+Combinado"]["tabla_roc"]["TPR"],
        color="#1F4E79", lw=2, label=f"AHP + Combinado (AUC = {resultados['AHP+Combinado']['auc']:.3f})")
ax.plot([0, 1], [0, 1], color="gray", lw=1, linestyle="--", label="Predicción aleatoria (AUC = 0.5)")
ax.set_xlabel("FPR = 1 - especificidad")
ax.set_ylabel("TPR (sensibilidad)")
ax.set_title("Curva ROC — AHP + Combinado\n(1 curva, sin partición)")
ax.legend(loc="lower right")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{DIR_FIG}/roc_ahp.png", dpi=180)
plt.close(fig)
print(f"\nGuardado: figuras/roc_ahp.png (solo AHP+Combinado)")
print(f"Guardado: tablas/roc_ahp+combinado_puntos_umbral.csv, roc_indices_puntos_umbral.csv (Índices queda solo en tablas, no en gráficas)")
print(f"Guardado: tablas/scores_ahp_indices_256puntos.csv")
