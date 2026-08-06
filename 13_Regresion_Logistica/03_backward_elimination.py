"""
Paso 3 — Backward elimination (eliminación hacia atrás) por AIC.

Clásicamente se parte del modelo completo (todas las variables) y se va
quitando, en cada paso, la variable menos aportante (mayor p-valor / cuyo
retiro más reduce el AIC), hasta que quitar otra variable ya no mejora el
AIC. En este dataset el modelo con las 10 variables NO es identificable
(ver 01_modelo_completo.py: "cobertura" y "uso_actual" están casi
anidadas, la matriz de diseño queda con rango deficiente). Por eso el
"paso 0" real no es el modelo con las 10 variables, sino el mejor modelo
de 9 variables que sí converge (se prueba quitando cada variable del
conjunto de 10, una a la vez, y se toma el de menor AIC como punto de
partida). De ahí en adelante el algoritmo es la eliminación hacia atrás
estándar.
"""
import pandas as pd
from scipy import stats

from config_base import cargar_datos, ajustar_modelo, TODAS_LAS_VARIABLES, DIR_TABLAS

df = cargar_datos()

historial = []
paso = 0

# --- Paso 0: el modelo con las 10 variables no es identificable; se busca
# el mejor punto de partida entre los modelos de 9 variables ---
incluidas = list(TODAS_LAS_VARIABLES)
modelo_actual = ajustar_modelo(df, incluidas)
if modelo_actual is None:
    print("Modelo con las 10 variables: no identificable (rango deficiente). "
          "Buscando el mejor punto de partida de 9 variables...\n")
    candidatos_inicio = []
    for var in incluidas:
        m = ajustar_modelo(df, [v for v in incluidas if v != var])
        if m is not None:
            candidatos_inicio.append((var, m))
    var_quitada, modelo_actual = min(candidatos_inicio, key=lambda t: t[1].aic)
    incluidas.remove(var_quitada)
    paso = 1
    historial.append({
        "paso": paso, "accion": "quitar (punto de partida, modelo de 10 no identificable)",
        "variable": var_quitada, "variables_en_modelo": ", ".join(incluidas),
        "n_variables": len(incluidas), "AIC": round(modelo_actual.aic, 2),
        "pseudo_R2_McFadden": round(modelo_actual.prsquared, 4),
        "delta_AIC": None, "LR_estadistico": None, "LR_gl": None, "LR_p_valor": None,
    })
    print(f"Paso {paso}: - {var_quitada:15s}  AIC={modelo_actual.aic:8.2f}  "
          f"PseudoR2={modelo_actual.prsquared:.4f}  (mejor de los 10 posibles arranques de 9 variables)\n")
else:
    historial.append({
        "paso": 0, "accion": "inicio (modelo completo)", "variable": "(ninguna)",
        "variables_en_modelo": ", ".join(incluidas), "n_variables": len(incluidas),
        "AIC": round(modelo_actual.aic, 2), "pseudo_R2_McFadden": round(modelo_actual.prsquared, 4),
        "delta_AIC": None, "LR_estadistico": None, "LR_gl": None, "LR_p_valor": None,
    })

# --- Eliminación hacia atrás estándar ---
while len(incluidas) > 0:
    candidatos = []
    for var in incluidas:
        modelo_candidato = ajustar_modelo(df, [v for v in incluidas if v != var])
        if modelo_candidato is None:
            continue
        candidatos.append((var, modelo_candidato))

    if not candidatos:
        print("Ninguna eliminación produce un modelo válido. Se detiene.")
        break

    var_quitada, modelo_candidato = min(candidatos, key=lambda t: t[1].aic)

    if modelo_candidato.aic >= modelo_actual.aic:
        print(f"Quitar cualquier variable empeora o no mejora el AIC actual ({modelo_actual.aic:.2f}). "
              f"Se detiene backward elimination.")
        break

    paso += 1
    gl = int(modelo_actual.df_model - modelo_candidato.df_model)
    lr_stat = 2 * (modelo_actual.llf - modelo_candidato.llf)
    lr_p = stats.chi2.sf(lr_stat, gl) if gl > 0 else float("nan")

    incluidas.remove(var_quitada)
    historial.append({
        "paso": paso, "accion": "quitar", "variable": var_quitada,
        "variables_en_modelo": ", ".join(incluidas) if incluidas else "(ninguna)",
        "n_variables": len(incluidas), "AIC": round(modelo_candidato.aic, 2),
        "pseudo_R2_McFadden": round(modelo_candidato.prsquared, 4),
        "delta_AIC": round(modelo_candidato.aic - modelo_actual.aic, 2),
        "LR_estadistico": round(lr_stat, 3), "LR_gl": gl, "LR_p_valor": lr_p,
    })
    print(f"Paso {paso}: - {var_quitada:15s}  AIC={modelo_candidato.aic:8.2f}  "
          f"(delta={modelo_candidato.aic - modelo_actual.aic:+7.2f})  "
          f"PseudoR2={modelo_candidato.prsquared:.4f}  LR p={lr_p:.4g}")

    modelo_actual = modelo_candidato

print(f"\nModelo final (backward elimination): {incluidas}")
print(f"AIC final: {modelo_actual.aic:.2f}   Pseudo R2 final: {modelo_actual.prsquared:.4f}")

tabla_historial = pd.DataFrame(historial)
tabla_historial.to_csv(f"{DIR_TABLAS}/backward_elimination_historial.csv", index=False, encoding="utf-8-sig")
print(f"\nGuardado: tablas/backward_elimination_historial.csv")

with open(f"{DIR_TABLAS}/backward_elimination_modelo_final.txt", "w", encoding="utf-8") as f:
    f.write(f"Variables seleccionadas (backward elimination, criterio AIC): {incluidas}\n\n")
    f.write(str(modelo_actual.summary()))
print(f"Guardado: tablas/backward_elimination_modelo_final.txt")
