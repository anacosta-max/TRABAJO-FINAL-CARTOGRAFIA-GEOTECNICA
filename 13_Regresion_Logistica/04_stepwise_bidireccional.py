"""
Paso 4 — Stepwise bidireccional por AIC.

Combina forward y backward: se parte del modelo nulo y en cada paso se
evalúan TODAS las variables candidatas —tanto agregar una variable que no
está en el modelo, como quitar una que sí está— y se toma la acción
(agregar o quitar) que más reduce el AIC. Se detiene cuando ninguna acción
(agregar o quitar) mejora el AIC del modelo actual. A diferencia de forward
selection puro, una variable agregada en un paso temprano podría ser
retirada más adelante si deja de aportar al combinarse con otras.
"""
import pandas as pd
from scipy import stats

from config_base import cargar_datos, ajustar_modelo, TODAS_LAS_VARIABLES, DIR_TABLAS

df = cargar_datos()

incluidas = []
modelo_actual = ajustar_modelo(df, incluidas)  # modelo nulo
historial = [{
    "paso": 0, "accion": "inicio", "variable": "(ninguna)",
    "variables_en_modelo": "(ninguna)", "n_variables": 0,
    "AIC": round(modelo_actual.aic, 2), "pseudo_R2_McFadden": round(modelo_actual.prsquared, 4),
    "delta_AIC": None, "LR_estadistico": None, "LR_gl": None, "LR_p_valor": None,
}]
print(f"Paso 0 (nulo): AIC={modelo_actual.aic:.2f}  Pseudo R2={modelo_actual.prsquared:.4f}\n")

paso = 0
while True:
    mejores_candidatos = []  # (accion, variable, modelo)

    # candidatos para agregar
    for var in TODAS_LAS_VARIABLES:
        if var in incluidas:
            continue
        m = ajustar_modelo(df, incluidas + [var])
        if m is not None:
            mejores_candidatos.append(("agregar", var, m))

    # candidatos para quitar
    for var in incluidas:
        m = ajustar_modelo(df, [v for v in incluidas if v != var])
        if m is not None:
            mejores_candidatos.append(("quitar", var, m))

    if not mejores_candidatos:
        print("No hay ninguna acción (agregar/quitar) que produzca un modelo válido. Se detiene.")
        break

    accion, var_elegida, modelo_elegido = min(mejores_candidatos, key=lambda t: t[2].aic)

    if modelo_elegido.aic >= modelo_actual.aic:
        print(f"Ninguna acción mejora el AIC actual ({modelo_actual.aic:.2f}). Se detiene stepwise bidireccional.")
        break

    paso += 1
    gl = abs(int(modelo_elegido.df_model - modelo_actual.df_model))
    lr_stat = abs(2 * (modelo_elegido.llf - modelo_actual.llf))
    lr_p = stats.chi2.sf(lr_stat, gl) if gl > 0 else float("nan")

    if accion == "agregar":
        incluidas.append(var_elegida)
        simbolo = "+"
    else:
        incluidas.remove(var_elegida)
        simbolo = "-"

    historial.append({
        "paso": paso, "accion": accion, "variable": var_elegida,
        "variables_en_modelo": ", ".join(incluidas) if incluidas else "(ninguna)",
        "n_variables": len(incluidas), "AIC": round(modelo_elegido.aic, 2),
        "pseudo_R2_McFadden": round(modelo_elegido.prsquared, 4),
        "delta_AIC": round(modelo_elegido.aic - modelo_actual.aic, 2),
        "LR_estadistico": round(lr_stat, 3), "LR_gl": gl, "LR_p_valor": lr_p,
    })
    print(f"Paso {paso}: {simbolo} {var_elegida:15s}  AIC={modelo_elegido.aic:8.2f}  "
          f"(delta={modelo_elegido.aic - modelo_actual.aic:+7.2f})  "
          f"PseudoR2={modelo_elegido.prsquared:.4f}  LR p={lr_p:.4g}")

    modelo_actual = modelo_elegido

print(f"\nModelo final (stepwise bidireccional): {incluidas}")
print(f"AIC final: {modelo_actual.aic:.2f}   Pseudo R2 final: {modelo_actual.prsquared:.4f}")

tabla_historial = pd.DataFrame(historial)
tabla_historial.to_csv(f"{DIR_TABLAS}/stepwise_bidireccional_historial.csv", index=False, encoding="utf-8-sig")
print(f"\nGuardado: tablas/stepwise_bidireccional_historial.csv")

with open(f"{DIR_TABLAS}/stepwise_bidireccional_modelo_final.txt", "w", encoding="utf-8") as f:
    f.write(f"Variables seleccionadas (stepwise bidireccional, criterio AIC): {incluidas}\n\n")
    f.write(str(modelo_actual.summary()))
print(f"Guardado: tablas/stepwise_bidireccional_modelo_final.txt")
