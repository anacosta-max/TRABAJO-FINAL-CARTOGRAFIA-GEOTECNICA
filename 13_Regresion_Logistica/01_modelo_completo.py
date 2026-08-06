"""
Paso 1 — Modelo completo (saturado): las 10 variables condicionantes.

Intenta ajustar el modelo de regresión logística con las 10 variables a la
vez (equivalente al "modelo completo" del que parte backward elimination
en el capítulo del libro). Se documenta aquí, con evidencia, un problema de
identificabilidad real de estos datos: "cobertura" y "uso_actual" están
casi perfectamente anidadas en la muestra, así que el modelo con las 10
variables no tiene una matriz de diseño de rango completo (no es
identificable). Por eso se reportan, como referencia, los dos mejores
modelos posibles con 9 variables (uno sin "cobertura", otro sin
"uso_actual"): son el punto de partida real para backward elimination.
"""
import numpy as np
import pandas as pd

from config_base import (
    cargar_datos, colapsar_categorias_raras, construir_formula, ajustar_modelo,
    TODAS_LAS_VARIABLES, VARIABLES_CATEGORICAS, DIR_TABLAS,
)
import geopandas as gpd
from config_base import INVENTARIO_SHP, RENOMBRAR_COLUMNAS, COLUMNA_PRESENCIA

# --- 0. Datos crudos (antes de agrupar categorías raras), para documentar la agrupación ---
puntos = gpd.read_file(INVENTARIO_SHP).rename(columns=RENOMBRAR_COLUMNAS)
df_crudo = puntos[TODAS_LAS_VARIABLES + [COLUMNA_PRESENCIA]].copy().rename(columns={COLUMNA_PRESENCIA: "inventario"})
df_crudo["inventario"] = df_crudo["inventario"].astype(int)
df_colapsado, registro_agrupacion = colapsar_categorias_raras(df_crudo)
registro_agrupacion.to_csv(f"{DIR_TABLAS}/categorias_agrupadas.csv", index=False, encoding="utf-8-sig")
print("Categorías cualitativas agrupadas por tener pocas observaciones:")
print(registro_agrupacion.to_string(index=False))
print(f"Guardado: tablas/categorias_agrupadas.csv\n")

df = cargar_datos()
print(f"Muestra: {df.shape[0]} puntos ({int(df['inventario'].sum())} movimiento, "
      f"{int((df['inventario'] == 0).sum())} NO), {df.shape[1] - 1} variables candidatas.\n")

# --- 1. Intento del modelo completo (10 variables) ---
print("=== Intento: modelo con las 10 variables ===")
modelo_completo = ajustar_modelo(df, TODAS_LAS_VARIABLES)
if modelo_completo is None:
    print("No es identificable: la matriz de diseño tiene rango deficiente.\n")
else:
    print("(inesperado) el modelo completo sí convergió de forma sana.\n")

# --- 2. Diagnóstico: tabla de contingencia cobertura x uso_actual ---
tabla_cruzada = pd.crosstab(df["cobertura"], df["uso_actual"])
tabla_cruzada.to_csv(f"{DIR_TABLAS}/diagnostico_cobertura_uso_actual.csv", encoding="utf-8-sig")
print("Tabla de contingencia cobertura x uso_actual (evidencia de anidamiento casi perfecto):")
print(tabla_cruzada.to_string())
print(f"Guardado: tablas/diagnostico_cobertura_uso_actual.csv\n")

# --- 3. Modelos de referencia con 9 variables (excluyendo una de las dos colineales) ---
filas_referencia = []
resumenes = {}
for excluida in ["uso_actual", "cobertura"]:
    variables_9 = [v for v in TODAS_LAS_VARIABLES if v != excluida]
    modelo = ajustar_modelo(df, variables_9)
    nombre = f"Sin {excluida}"
    if modelo is not None:
        filas_referencia.append({
            "modelo_referencia": nombre,
            "variable_excluida": excluida,
            "n_variables": len(variables_9),
            "n_parametros": int(modelo.df_model) + 1,
            "log_verosimilitud": round(modelo.llf, 3),
            "AIC": round(modelo.aic, 2),
            "pseudo_R2_McFadden": round(modelo.prsquared, 4),
            "LLR_p_value": modelo.llr_pvalue,
        })
        resumenes[nombre] = modelo
    else:
        filas_referencia.append({
            "modelo_referencia": nombre, "variable_excluida": excluida,
            "n_variables": len(variables_9), "n_parametros": None,
            "log_verosimilitud": None, "AIC": None, "pseudo_R2_McFadden": None, "LLR_p_value": None,
        })

# modelo nulo, como referencia de base
modelo_nulo = ajustar_modelo(df, [])
filas_referencia.append({
    "modelo_referencia": "Nulo (solo intercepto)", "variable_excluida": "(todas)",
    "n_variables": 0, "n_parametros": 1,
    "log_verosimilitud": round(modelo_nulo.llf, 3), "AIC": round(modelo_nulo.aic, 2),
    "pseudo_R2_McFadden": 0.0, "LLR_p_value": np.nan,
})

df_referencia = pd.DataFrame(filas_referencia)
df_referencia.to_csv(f"{DIR_TABLAS}/modelos_referencia_9_variables.csv", index=False, encoding="utf-8-sig")
print("=== Modelos de referencia (9 variables, punto de partida real de backward elimination) ===")
print(df_referencia.to_string(index=False))
print(f"\nGuardado: tablas/modelos_referencia_9_variables.csv")

# --- 4. Guardar el resumen completo (coeficientes) del mejor de los dos modelos de 9 variables ---
candidatos_9var = df_referencia[df_referencia["n_variables"] == 9].dropna(subset=["AIC"])
mejor_nombre = candidatos_9var.loc[candidatos_9var["AIC"].astype(float).idxmin(), "modelo_referencia"]
mejor_modelo = resumenes[mejor_nombre]
variable_excluida_mejor = df_referencia.set_index("modelo_referencia").loc[mejor_nombre, "variable_excluida"]
variables_mejor = [v for v in TODAS_LAS_VARIABLES if v != variable_excluida_mejor]
with open(f"{DIR_TABLAS}/resumen_mejor_modelo_9_variables.txt", "w", encoding="utf-8") as f:
    f.write(f"Mejor modelo de referencia (9 variables): {mejor_nombre}\n")
    f.write(f"Formula: {construir_formula(variables_mejor)}\n\n")
    f.write(str(mejor_modelo.summary()))
print(f"\nMejor modelo de referencia: {mejor_nombre} (AIC={resumenes[mejor_nombre].aic:.2f})")
print(f"Guardado: tablas/resumen_mejor_modelo_9_variables.txt")
