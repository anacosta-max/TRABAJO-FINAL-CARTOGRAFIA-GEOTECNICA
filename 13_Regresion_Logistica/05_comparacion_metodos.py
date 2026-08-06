"""
Paso 5 — Comparación de los 3 métodos de selección por pasos y modelo final.

Compara las variables seleccionadas, el número de pasos, el AIC y el
pseudo R² final de forward selection, backward elimination y stepwise
bidireccional. Si (como ocurrió aquí) los tres métodos convergen al mismo
subconjunto de variables, eso se reporta como evidencia de que el modelo
encontrado es un óptimo robusto por AIC y no un artefacto del orden de
búsqueda de un solo método. Con el modelo final se calculan además los
odds ratios (exp(coef)), la curva ROC y el AUC.
"""
import ast
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc

from config_base import cargar_datos, ajustar_modelo, construir_formula, DIR_TABLAS, DIR_FIGURAS

df = cargar_datos()

metodos = {
    "Forward selection": "forward_selection_historial.csv",
    "Backward elimination": "backward_elimination_historial.csv",
    "Stepwise bidireccional": "stepwise_bidireccional_historial.csv",
}

filas = []
variables_por_metodo = {}
for nombre, archivo in metodos.items():
    hist = pd.read_csv(f"{DIR_TABLAS}/{archivo}")
    ultima = hist.iloc[-1]
    variables_finales = [] if ultima["variables_en_modelo"] in ("(ninguna)", None) or pd.isna(ultima["variables_en_modelo"]) \
        else [v.strip() for v in str(ultima["variables_en_modelo"]).split(",")]
    variables_por_metodo[nombre] = variables_finales
    filas.append({
        "metodo": nombre,
        "n_pasos": int(hist["paso"].max()),
        "variables_seleccionadas": ", ".join(variables_finales) if variables_finales else "(ninguna)",
        "n_variables": len(variables_finales),
        "AIC_final": ultima["AIC"],
        "pseudo_R2_McFadden_final": ultima["pseudo_R2_McFadden"],
    })

tabla_comparacion = pd.DataFrame(filas)
tabla_comparacion.to_csv(f"{DIR_TABLAS}/comparacion_3_metodos.csv", index=False, encoding="utf-8-sig")
print("=== Comparación de los 3 métodos de selección por pasos ===")
print(tabla_comparacion.to_string(index=False))

conjuntos = [frozenset(v) for v in variables_por_metodo.values()]
coinciden = len(set(conjuntos)) == 1
print(f"\n¿Los 3 métodos seleccionan exactamente las mismas variables? {'Sí' if coinciden else 'No'}")
print(f"Guardado: tablas/comparacion_3_metodos.csv")

# --- Modelo final: el mejor AIC entre los 3 (si difieren) o el consenso (si coinciden) ---
mejor_metodo = tabla_comparacion.loc[tabla_comparacion["AIC_final"].astype(float).idxmin(), "metodo"]
variables_finales = variables_por_metodo[mejor_metodo]
modelo_final = ajustar_modelo(df, variables_finales)

print(f"\n=== Modelo final elegido: {mejor_metodo} ===")
print(f"Variables: {variables_finales}")
print(f"Fórmula: {construir_formula(variables_finales)}")
print(f"AIC={modelo_final.aic:.2f}  Pseudo R2={modelo_final.prsquared:.4f}  "
      f"LLR p-value={modelo_final.llr_pvalue:.4g}")

# --- Tabla de coeficientes con odds ratios ---
tabla_coef = pd.DataFrame({
    "coeficiente": modelo_final.params,
    "error_estandar": modelo_final.bse,
    "z": modelo_final.tvalues,
    "p_valor": modelo_final.pvalues,
    "odds_ratio": np.exp(modelo_final.params),
    "OR_IC95_inf": np.exp(modelo_final.conf_int()[0]),
    "OR_IC95_sup": np.exp(modelo_final.conf_int()[1]),
})
tabla_coef["significativo_p<0.05"] = tabla_coef["p_valor"] < 0.05
tabla_coef.index.name = "termino"
tabla_coef.to_csv(f"{DIR_TABLAS}/modelo_final_coeficientes.csv", encoding="utf-8-sig")
print(f"\nGuardado: tablas/modelo_final_coeficientes.csv")
print(tabla_coef.round(4).to_string())

with open(f"{DIR_TABLAS}/modelo_final_resumen.txt", "w", encoding="utf-8") as f:
    f.write(f"Metodo: {mejor_metodo}\n")
    f.write(f"Variables: {variables_finales}\n")
    f.write(f"Formula: {construir_formula(variables_finales)}\n\n")
    f.write(str(modelo_final.summary()))
print(f"Guardado: tablas/modelo_final_resumen.txt")

# --- ROC y AUC (sobre la misma muestra de ajuste, sin partición externa: n=256 es limitado) ---
y_real = df["inventario"].values
y_prob = modelo_final.predict()
fpr, tpr, _ = roc_curve(y_real, y_prob)
valor_auc = auc(fpr, tpr)

fig, ax = plt.subplots(figsize=(6, 6))
ax.plot(fpr, tpr, color="#1F4E79", lw=2, label=f"Modelo final (AUC = {valor_auc:.3f})")
ax.plot([0, 1], [0, 1], color="gray", lw=1, linestyle="--", label="Clasificador aleatorio (AUC = 0.5)")
ax.set_xlabel("Tasa de falsos positivos (1 - especificidad)")
ax.set_ylabel("Tasa de verdaderos positivos (sensibilidad)")
ax.set_title("Curva ROC — modelo de regresión logística final")
ax.legend(loc="lower right")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{DIR_FIGURAS}/roc_modelo_final.png", dpi=180)
plt.close(fig)

print(f"\nAUC del modelo final: {valor_auc:.4f}")
print(f"Guardado: figuras/roc_modelo_final.png")

with open(f"{DIR_TABLAS}/modelo_final_auc.txt", "w", encoding="utf-8") as f:
    f.write(f"AUC (curva ROC, sobre la muestra de ajuste, n={len(y_real)}): {valor_auc:.4f}\n")
print(f"Guardado: tablas/modelo_final_auc.txt")
