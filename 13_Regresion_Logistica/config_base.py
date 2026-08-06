"""
Configuración compartida para la Regresión Logística (capítulo "Métodos
basados en datos" — sección de Modelos Paramétricos / GLM) aplicada a las
10 variables condicionantes de este proyecto.

Fuente de datos: el mismo inventario de 11_Inventario_Discriminado_Estratificado
usado en 06_Variables_Condicionantes — 128 movimientos reales (sin
modificar) + 128 puntos "NO" por disimilitud ambiental moderada y muestreo
espacialmente estratificado.

Decisión metodológica (confirmada por el usuario) para la selección de
variables por pasos (stepwise): cada variable —numérica o categórica—
entra o sale COMPLETA del modelo en cada paso (todas las dummies de una
categórica se mueven juntas), usando el AIC como criterio de decisión.
Esto evita los problemas de convergencia que tendría tratar cada dummy
individual como predictor independiente con solo 256 observaciones (el
propio capítulo del libro tiene ese problema en su ejemplo con geología).

Problema detectado y solución (separación cuasi-completa):
Al probar el modelo saturado (las 10 variables) se encontró que varias
categorías de las variables cualitativas tienen muy pocas observaciones
y, además, un resultado homogéneo (todas "movimiento" o todas "NO"), p. ej.
cobertura=3.0 (n=1, 100% movimiento), uso_actual=30211.0 (n=2, 0% movimiento),
geologia=5.0 (n=1, 100% movimiento), geomorfologia=13.0 (n=3, 0% movimiento).
Esto produce separación (cuasi-)completa: la verosimilitud no tiene un
máximo finito bien definido para esas categorías y los optimizadores o se
quedan estancados (Newton/BFGS) o divergen a coeficientes artificialmente
grandes (Powell). La solución estándar (y la que se aplica aquí) es agrupar,
antes de modelar, cualquier categoría con menos de MIN_OBS_CATEGORIA
observaciones en una clase "Otras" para esa variable. Esto se documenta en
el informe con una tabla de las categorías agrupadas.

Segundo problema detectado (independiente del anterior): incluso después
de agrupar las categorías raras, el modelo con las 10 variables sigue sin
converger de forma sana. La causa es que "cobertura" (cobertura vegetal)
y "uso_actual" (uso actual del suelo) están casi perfectamente anidadas en
esta muestra (cada clase de cobertura corresponde casi 1 a 1 con una clase
de uso actual), lo que deja la matriz de diseño con rango deficiente
(columnas linealmente dependientes) cuando ambas entran juntas al modelo:
el modelo no es identificable. Por eso `ajustar_modelo` calcula el rango de
la matriz de diseño (patsy) antes de ajustar y descarta (igual que una no
convergencia) cualquier combinación de variables que sea deficiente en
rango. Esto hace que la selección por pasos evite automáticamente incluir
"cobertura" y "uso_actual" al mismo tiempo, sin necesidad de excluir una de
las dos a mano; cuál de las dos aporta más se decide por AIC durante el
forward/backward/stepwise, igual que con cualquier otro par de variables.
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import patsy
from patsy.contrasts import Treatment
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings("ignore")

INVENTARIO_SHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\Resultados"
    r"\11_Inventario_Discriminado_Estratificado\inventario_nuevo\puntos_inventario_estratificado.shp"
)
RASTER_FOLDER = r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\masked_by_pendiente_v2"

CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))
DIR_TABLAS = os.path.join(CARPETA_BASE, "tablas")
DIR_FIGURAS = os.path.join(CARPETA_BASE, "figuras")
os.makedirs(DIR_TABLAS, exist_ok=True)
os.makedirs(DIR_FIGURAS, exist_ok=True)

VARIABLES_NUMERICAS = ["pendiente", "aspecto", "curvatura", "flujo_acum", "elevacion", "dist_drenajes"]
VARIABLES_CATEGORICAS = ["cobertura", "uso_actual", "geologia", "geomorfologia"]
TODAS_LAS_VARIABLES = VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS

RENOMBRAR_COLUMNAS = {"dist_drena": "dist_drenajes", "geomorfolo": "geomorfologia"}
COLUMNA_PRESENCIA = "Y"
CODIGO_OTRAS = 9999.0
MIN_OBS_CATEGORIA = 5

RASTERS = {
    "pendiente.tif": "pendiente", "aspecto.tif": "aspecto", "curvatura.tif": "curvatura",
    "flujo_acumulado.tif": "flujo_acum", "elevacion.tif": "elevacion", "dist_drenajes.tif": "dist_drenajes",
    "cobertura.tif": "cobertura", "uso_actual.tif": "uso_actual", "geologia.tif": "geologia",
    "geomorfologia.tif": "geomorfologia",
}


def colapsar_categorias_raras(df, min_obs=MIN_OBS_CATEGORIA):
    """Agrupa, para cada variable categórica, las categorías con menos de
    `min_obs` observaciones en una clase "Otras" (CODIGO_OTRAS). Si la
    clase "Otras" resultante seguiría teniendo menos de `min_obs`
    observaciones (p. ej. cuando solo hay una categoría rara), esas
    observaciones se fusionan directamente con la categoría mayoritaria de
    la variable en vez de crear una clase "Otras" igual de pequeña. Devuelve
    el dataframe modificado y un registro (lista de dicts) de qué
    categorías se agruparon, para documentar en el informe."""
    df = df.copy()
    registro = []
    for var in VARIABLES_CATEGORICAS:
        conteos = df[var].value_counts()
        raras = conteos[conteos < min_obs].index.tolist()
        if not raras:
            continue
        n_otras = int(conteos.loc[raras].sum())
        if n_otras >= min_obs:
            destino = CODIGO_OTRAS
            etiqueta_destino = "Otras"
        else:
            destino = conteos.drop(index=raras).idxmax()
            etiqueta_destino = f"fusionada con categoría mayoritaria {destino}"
        for cat in raras:
            registro.append({
                "variable": var, "categoria_original": cat,
                "n_obs": int(conteos[cat]), "destino": etiqueta_destino,
            })
        df[var] = df[var].where(~df[var].isin(raras), destino)
    return df, pd.DataFrame(registro)


def cargar_datos(colapsar_raras=True):
    """Carga el inventario base (256 puntos) usado en todo el capítulo.
    Por defecto agrupa categorías cualitativas con pocas observaciones
    (ver colapsar_categorias_raras) para evitar separación cuasi-completa."""
    puntos = gpd.read_file(INVENTARIO_SHP).rename(columns=RENOMBRAR_COLUMNAS)
    df = puntos[TODAS_LAS_VARIABLES + [COLUMNA_PRESENCIA]].copy()
    df = df.rename(columns={COLUMNA_PRESENCIA: "inventario"})
    df["inventario"] = df["inventario"].astype(int)
    if colapsar_raras:
        df, _ = colapsar_categorias_raras(df)
    return df


# Categoría de referencia (base) de cada variable cualitativa: la más
# frecuente en la muestra ya con categorías raras agrupadas (en vez de la
# que quede primera en orden numérico por defecto, que a veces es la
# clase "Otras"). Esto NO cambia el ajuste del modelo (mismas probabilidades
# predichas, mismo AIC, mismo pseudo R2) — solo hace más intuitiva la
# interpretación de cada coeficiente/odds ratio, al compararlo siempre
# contra la clase más común de la cuenca en vez de contra una minoritaria.
REFERENCIA_CATEGORICAS = {
    "cobertura": 2.0,        # Pastos limpios (n=79, la más frecuente)
    "uso_actual": 30204.0,   # Cultivos permanentes semi-intensivos (n=80)
    "geologia": 3.0,         # Neis Intrusivo Abejorral (n=97)
    "geomorfologia": 9.0,    # Espolón alto de longitud larga (n=53)
}


def construir_formula(variables_incluidas):
    """Arma una fórmula de patsy/statsmodels a partir de una lista de
    nombres de variable, envolviendo las categóricas en C(..., Treatment(
    reference=...)) para fijar la categoría más frecuente como base."""
    if not variables_incluidas:
        return "inventario ~ 1"
    partes = []
    for v in variables_incluidas:
        if v in VARIABLES_CATEGORICAS:
            ref = REFERENCIA_CATEGORICAS.get(v)
            partes.append(f"C({v}, Treatment(reference={ref}))" if ref is not None else f"C({v})")
        else:
            partes.append(v)
    return "inventario ~ " + " + ".join(partes)


UMBRAL_STD_ERR = 15  # error estándar de un coeficiente por encima de esto delata separación

def _modelo_es_sano(modelo):
    """Descarta modelos con signos claros de separación (cuasi-)completa:
    parámetros no estimados (NaN), errores estándar disparados, o un
    optimizador que "convergió" sin moverse del punto nulo (frecuente en
    bfgs/lbfgs cuando el problema es mal condicionado: reportan
    convergencia pero la log-verosimilitud queda igual a la del modelo
    nulo, es decir, no ajustaron nada en realidad)."""
    if modelo is None:
        return False
    if modelo.params.isna().any() or modelo.bse.isna().any():
        return False
    if (modelo.bse > UMBRAL_STD_ERR).any():
        return False
    if modelo.df_model > 0 and modelo.llf <= modelo.llnull + 1e-6:
        return False
    return True


def _diseno_es_rango_completo(df, formula):
    """Verifica que la matriz de diseño (patsy) de la fórmula no tenga
    columnas linealmente dependientes (rango deficiente), lo que vuelve
    el modelo no identificable (típicamente por variables categóricas
    casi anidadas, p. ej. cobertura y uso_actual en este dataset)."""
    _, X = patsy.dmatrices(formula, df, return_type="dataframe")
    rango = np.linalg.matrix_rank(X.values)
    return rango == X.shape[1]


def ajustar_modelo(df, variables_incluidas, maxiter=200):
    """Ajusta un modelo logit de statsmodels con las variables dadas,
    probando varios optimizadores. Devuelve el primer resultado "sano"
    (convergió y sin señales de separación); si ninguno lo es, o si la
    combinación de variables produce una matriz de diseño con rango
    deficiente (no identificable), devuelve None. Con
    `colapsar_categorias_raras` ya aplicado en cargar_datos(), esto
    normalmente converge con el optimizador por defecto (newton)."""
    formula = construir_formula(variables_incluidas)
    if not _diseno_es_rango_completo(df, formula):
        return None
    for metodo in ("newton", "bfgs", "lbfgs"):
        try:
            modelo = smf.logit(formula=formula, data=df).fit(disp=0, maxiter=maxiter, method=metodo)
        except Exception:
            continue
        if modelo.mle_retvals.get("converged", True) and _modelo_es_sano(modelo):
            return modelo
    return None
