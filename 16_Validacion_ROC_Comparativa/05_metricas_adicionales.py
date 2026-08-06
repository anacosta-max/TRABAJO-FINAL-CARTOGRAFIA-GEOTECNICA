# -*- coding: utf-8 -*-
"""
Métricas adicionales pedidas por el capítulo "Evaluación del modelo" del
libro (que no estaban en los scripts 01-03):

1. Distancia a la clasificación perfecta:  r = sqrt(FPR^2 + (1-TPR)^2)
   calculada en el punto de umbral de referencia de cada modelo (la
   esquina superior izquierda, FPR=0/TPR=1, es la clasificación perfecta;
   menor r = mejor).
2. Clasificación cualitativa del AUC según la escala de Swets (1988),
   usada en la literatura de zonificación de amenazas (SafeLand/JTC-1):
     AUC > 0.9  -> "Alto (altamente preciso)"
     AUC > 0.7  -> "Moderado (moderadamente preciso)"
     AUC > 0.5  -> "Aceptable (mejor que el azar)"
     AUC <= 0.5 -> "No aceptable"

Para AHP+Combinado, Índices y WoE se reutilizan las matrices de confusión
ya calculadas (umbral = mediana). Para la regresión logística se
recalculan las matrices de confusión a umbral = 0.5 (el umbral por
defecto que usa el capítulo del libro, ver Actividad 1) tanto en train
como en test, con el mismo split (semilla=42) que
03_roc_regresion_logistica_train_test.py.
"""
import os
import sys
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_TAB = os.path.join(BASE, "tablas")

RUTA_REGRESION = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS"
    r"\Resultados\13_Regresion_Logistica"
)
sys.path.insert(0, RUTA_REGRESION)
import geopandas as gpd
from sklearn.model_selection import train_test_split
from config_base import (
    INVENTARIO_SHP, RENOMBRAR_COLUMNAS, COLUMNA_PRESENCIA, TODAS_LAS_VARIABLES,
    VARIABLES_CATEGORICAS, MIN_OBS_CATEGORIA, CODIGO_OTRAS, ajustar_modelo,
)

VARIABLES_MODELO_FINAL = ["uso_actual", "geologia", "geomorfologia", "curvatura", "dist_drenajes"]
SEMILLA = 42


def distancia_clasificacion_perfecta(fpr, tpr):
    return float(np.sqrt(fpr ** 2 + (1 - tpr) ** 2))


def clasificar_auc_swets(auc):
    if auc > 0.9:
        return "Alto (altamente preciso)"
    elif auc > 0.7:
        return "Moderado (moderadamente preciso)"
    elif auc > 0.5:
        return "Aceptable (mejor que el azar)"
    else:
        return "No aceptable"


# ===========================================================================
# 1. AHP+Combinado y WoE — reutilizar matrices de confusión ya calculadas
#    (Índices se excluye de esta comparación por decisión del usuario:
#    casi redundante con AHP+Combinado)
# ===========================================================================
filas = []
for nombre, archivo in [("AHP+Combinado", "ahp+combinado_matriz_confusion_resumen.csv"),
                         ("WoE", "woe_matriz_confusion_resumen.csv")]:
    conf = pd.read_csv(f"{DIR_TAB}/{archivo}").iloc[0]
    TP, FP, TN, FN = conf["TP"], conf["FP"], conf["TN"], conf["FN"]
    fpr = FP / (FP + TN)
    tpr = TP / (TP + FN)
    r = distancia_clasificacion_perfecta(fpr, tpr)
    filas.append({
        "modelo": nombre, "conjunto": "Único (sin partición)", "umbral": conf["umbral_referencia"],
        "FPR": fpr, "TPR": tpr, "distancia_clasificacion_perfecta_r": r,
        "AUC": conf["AUC"], "clasificacion_Swets_1988": clasificar_auc_swets(conf["AUC"]),
    })

# ===========================================================================
# 2. Regresión logística — recalcular confusión a umbral=0.5 en train y test
#    (mismo split, semilla=42, que en 03_)
# ===========================================================================
puntos = gpd.read_file(INVENTARIO_SHP).rename(columns=RENOMBRAR_COLUMNAS)
df = puntos[TODAS_LAS_VARIABLES + [COLUMNA_PRESENCIA]].copy().rename(columns={COLUMNA_PRESENCIA: "inventario"})
df["inventario"] = df["inventario"].astype(int)
df_train, df_test = train_test_split(df, test_size=0.20, stratify=df["inventario"], random_state=SEMILLA)


def construir_mapeo_categorias(df_train, variables_categoricas, min_obs=MIN_OBS_CATEGORIA):
    mapeos = {}
    for var in variables_categoricas:
        conteos = df_train[var].value_counts()
        raras = conteos[conteos < min_obs].index.tolist()
        mapeo = {c: c for c in conteos.index}
        if raras:
            n_otras = int(conteos.loc[raras].sum())
            destino = CODIGO_OTRAS if n_otras >= min_obs else conteos.drop(index=raras).idxmax()
            for c in raras:
                mapeo[c] = destino
        mapeos[var] = mapeo
    return mapeos


def aplicar_mapeo_categorias(df, mapeos, variables_a_verificar):
    df = df.copy()
    fila_predecible = np.ones(len(df), dtype=bool)
    for var, mapeo in mapeos.items():
        no_vistas = ~df[var].isin(mapeo.keys())
        if no_vistas.any() and var in variables_a_verificar:
            fila_predecible &= ~no_vistas
        df[var] = df[var].where(~no_vistas, list(mapeo.values())[0])
        df[var] = df[var].map(lambda c: mapeo.get(c, c))
    return df, fila_predecible


mapeos = construir_mapeo_categorias(df_train, VARIABLES_CATEGORICAS)
variables_categoricas_del_modelo = [v for v in VARIABLES_MODELO_FINAL if v in VARIABLES_CATEGORICAS]
df_train_c, _ = aplicar_mapeo_categorias(df_train, mapeos, variables_categoricas_del_modelo)
df_test_c, predecible_test = aplicar_mapeo_categorias(df_test, mapeos, variables_categoricas_del_modelo)
df_test_c = df_test_c.loc[predecible_test].copy()

modelo_train = ajustar_modelo(df_train_c, VARIABLES_MODELO_FINAL)
prob_train = modelo_train.predict(df_train_c)
prob_test = modelo_train.predict(df_test_c)

auc_reg = pd.read_csv(f"{DIR_TAB}/regresion_auc_train_test.csv")
auc_train_val = auc_reg.loc[auc_reg["conjunto"].str.contains("Entrenamiento"), "AUC"].iloc[0]
auc_test_val = auc_reg.loc[auc_reg["conjunto"].str.contains("Prueba"), "AUC"].iloc[0]

for nombre_conjunto, y_real, prob, auc_val in [
    ("Entrenamiento (80%, umbral=0.5)", df_train_c["inventario"].values, prob_train, auc_train_val),
    ("Prueba/validación (20%, umbral=0.5)", df_test_c["inventario"].values, prob_test, auc_test_val),
]:
    pred = (prob >= 0.5).astype(int)
    TP = int(((pred == 1) & (y_real == 1)).sum())
    FP = int(((pred == 1) & (y_real == 0)).sum())
    TN = int(((pred == 0) & (y_real == 0)).sum())
    FN = int(((pred == 0) & (y_real == 1)).sum())
    fpr = FP / (FP + TN) if (FP + TN) > 0 else np.nan
    tpr = TP / (TP + FN) if (TP + FN) > 0 else np.nan
    r = distancia_clasificacion_perfecta(fpr, tpr)
    filas.append({
        "modelo": "Regresión Logística", "conjunto": nombre_conjunto, "umbral": 0.5,
        "FPR": fpr, "TPR": tpr, "distancia_clasificacion_perfecta_r": r,
        "AUC": auc_val, "clasificacion_Swets_1988": clasificar_auc_swets(auc_val),
    })

# ===========================================================================
# 3. Guardar tabla combinada
# ===========================================================================
tabla_final = pd.DataFrame(filas)
tabla_final.to_csv(f"{DIR_TAB}/metricas_adicionales_r_swets.csv", index=False, encoding="utf-8-sig")
print(tabla_final.round(4).to_string(index=False))
print(f"\nGuardado: tablas/metricas_adicionales_r_swets.csv")
