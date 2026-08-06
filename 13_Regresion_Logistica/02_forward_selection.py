"""
Paso 2 — Forward selection (selección hacia adelante) por AIC.

Se parte del modelo nulo (solo intercepto) y en cada paso se agrega, de
entre las variables aún no incluidas, la que produce el modelo con menor
AIC. Cada variable —numérica o categórica— entra completa (todas las
dummies de una categórica se mueven juntas, ver config_base.py). El
proceso se detiene cuando ninguna variable candidata mejora (reduce) el
AIC del modelo actual. En cada paso se registra AIC, pseudo R² de McFadden
y el resultado de la prueba de razón de verosimilitud (LR test) de la
variable que entra, para poder ver cómo cambia el ajuste al combinar
variables (tal como pidió el profesor).
"""
import pandas as pd
from scipy import stats

from config_base import cargar_datos, ajustar_modelo, TODAS_LAS_VARIABLES, DIR_TABLAS

df = cargar_datos()

incluidas = []
restantes = list(TODAS_LAS_VARIABLES)
modelo_actual = ajustar_modelo(df, incluidas)  # modelo nulo
historial = [{
    "paso": 0, "accion": "inicio", "variable": "(ninguna)",
    "variables_en_modelo": "(ninguna)", "n_variables": 0,
    "AIC": round(modelo_actual.aic, 2), "pseudo_R2_McFadden": round(modelo_actual.prsquared, 4),
    "delta_AIC": None, "LR_estadistico": None, "LR_gl": None, "LR_p_valor": None,
}]

print(f"Paso 0 (nulo): AIC={modelo_actual.aic:.2f}  Pseudo R2={modelo_actual.prsquared:.4f}\n")

paso = 0
while restantes:
    candidatos = []
    for var in restantes:
        modelo_candidato = ajustar_modelo(df, incluidas + [var])
        if modelo_candidato is None:
            continue
        candidatos.append((var, modelo_candidato))

    if not candidatos:
        print("Ninguna variable restante produce un modelo válido (identificable). Se detiene.")
        break

    # mejor candidato = menor AIC
    var_elegida, modelo_elegido = min(candidatos, key=lambda t: t[1].aic)

    if modelo_elegido.aic >= modelo_actual.aic:
        print(f"Ninguna variable candidata mejora el AIC actual ({modelo_actual.aic:.2f}). Se detiene forward selection.")
        break

    paso += 1
    gl = int(modelo_elegido.df_model - modelo_actual.df_model)
    lr_stat = 2 * (modelo_elegido.llf - modelo_actual.llf)
    lr_p = stats.chi2.sf(lr_stat, gl) if gl > 0 else float("nan")

    incluidas.append(var_elegida)
    restantes.remove(var_elegida)

    historial.append({
        "paso": paso, "accion": "agregar", "variable": var_elegida,
        "variables_en_modelo": ", ".join(incluidas), "n_variables": len(incluidas),
        "AIC": round(modelo_elegido.aic, 2), "pseudo_R2_McFadden": round(modelo_elegido.prsquared, 4),
        "delta_AIC": round(modelo_elegido.aic - modelo_actual.aic, 2),
        "LR_estadistico": round(lr_stat, 3), "LR_gl": gl, "LR_p_valor": lr_p,
    })
    print(f"Paso {paso}: + {var_elegida:15s}  AIC={modelo_elegido.aic:8.2f}  "
          f"(delta={modelo_elegido.aic - modelo_actual.aic:+7.2f})  "
          f"PseudoR2={modelo_elegido.prsquared:.4f}  LR p={lr_p:.4g}")

    modelo_actual = modelo_elegido

print(f"\nModelo final (forward selection): {incluidas}")
print(f"AIC final: {modelo_actual.aic:.2f}   Pseudo R2 final: {modelo_actual.prsquared:.4f}")

tabla_historial = pd.DataFrame(historial)
tabla_historial.to_csv(f"{DIR_TABLAS}/forward_selection_historial.csv", index=False, encoding="utf-8-sig")
print(f"\nGuardado: tablas/forward_selection_historial.csv")

with open(f"{DIR_TABLAS}/forward_selection_modelo_final.txt", "w", encoding="utf-8") as f:
    f.write(f"Variables seleccionadas (forward selection, criterio AIC): {incluidas}\n\n")
    f.write(str(modelo_actual.summary()))
print(f"Guardado: tablas/forward_selection_modelo_final.txt")
