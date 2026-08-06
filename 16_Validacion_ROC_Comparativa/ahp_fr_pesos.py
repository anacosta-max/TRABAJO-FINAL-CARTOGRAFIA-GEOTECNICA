# -*- coding: utf-8 -*-
"""
Módulo compartido: recalcula el peso de clase (w_c) de las 4 variables
CATEGÓRICAS de AHP+Combinado (geología, geomorfología, cobertura,
uso_actual) usando Frequency Ratio — LA FÓRMULA DEL LIBRO/CURSO, no una
aproximación:

    w_n = L_r / A_r

    L_r = % de los movimientos en masa TOTALES que contiene la clase n
          = (n° de los 128 puntos de movimiento que caen en la clase n) / 128

    A_r = % del ÁREA TOTAL de la cuenca que representa la clase n
          = (n° de celdas del ráster completo en la clase n) / (celdas válidas totales)

(Versión anterior de este módulo usaba, por error, "% de movimientos" /
"% de puntos ESTABLES" en vez de "% de ÁREA" — no es la fórmula del
libro, se corrigió aquí tras revisión explícita del usuario.)

L_r se calcula sobre los 128 PUNTOS de movimiento real (evento = punto,
como está definido el inventario de este proyecto). A_r se calcula sobre
el RÁSTER COMPLETO de cada variable (masked_by_pendiente_v2), no sobre los
256 puntos — el área de una clase es una propiedad del mapa completo, no
de la muestra.

El w_n resultante no está acotado a [0,1] (puede superar 1 si una clase
está sobrerrepresentada en movimientos respecto a su área). Para
mantenerlo en la misma escala 0-1 que el resto de w_c del proyecto
(pesos de literatura), se normaliza dividiendo por el w_n máximo de cada
variable: w_c = w_n / w_n_máximo.
"""
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio

INVENTARIO_SHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\Resultados"
    r"\11_Inventario_Discriminado_Estratificado\inventario_nuevo\puntos_inventario_estratificado.shp"
)
RASTER_FOLDER = r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\masked_by_pendiente_v2"
RENOMBRAR_COLUMNAS = {"dist_drena": "dist_drenajes", "geomorfolo": "geomorfologia"}
VARIABLES_CATEGORICAS_FR = ["geologia", "geomorfologia", "cobertura", "uso_actual"]
RASTERS_ARCHIVO = {
    "geologia": "geologia.tif", "geomorfologia": "geomorfologia.tif",
    "cobertura": "cobertura.tif", "uso_actual": "uso_actual.tif",
}


def calcular_pesos_clase_FR():
    """Devuelve (mapeos, valores_neutrales, registro):
    mapeos = {variable: {codigo: peso_wc}} listo para reclasificar
    valores_neutrales = {variable: peso_neutral} — para códigos que
    existan en el ráster pero nunca aparecieron entre los 128 puntos de
    movimiento (L_r=0 exacto -> se documenta, no se fuerza a 0 duro)
    registro = DataFrame con el detalle (L_r, A_r, w_n, n_celdas) para
    documentar en el informe."""
    puntos = gpd.read_file(INVENTARIO_SHP).rename(columns=RENOMBRAR_COLUMNAS)
    puntos_mov = puntos[puntos["Y"].astype(int) == 1]
    n_mov_total = len(puntos_mov)

    mapeos = {}
    valores_neutrales = {}
    registro = []
    for var in VARIABLES_CATEGORICAS_FR:
        # A_r: % de área a partir del ráster completo
        with rasterio.open(f"{RASTER_FOLDER}/{RASTERS_ARCHIVO[var]}") as src:
            arr = src.read(1).astype(float)
            if src.nodata is not None:
                arr = np.where(arr == src.nodata, np.nan, arr)
        celdas_validas_totales = int(np.sum(~np.isnan(arr)))
        codigos_raster, conteos_raster = np.unique(arr[~np.isnan(arr)], return_counts=True)
        area_por_codigo = dict(zip(codigos_raster, conteos_raster))

        # L_r: % de movimientos a partir de los 128 puntos
        valores_mov = puntos_mov[var].values
        codigos_mov, conteos_mov = np.unique(valores_mov, return_counts=True)
        mov_por_codigo = dict(zip(codigos_mov, conteos_mov))

        w_n_por_codigo = {}
        for codigo in area_por_codigo:
            n_celdas = area_por_codigo[codigo]
            A_r = n_celdas / celdas_validas_totales
            n_mov = mov_por_codigo.get(codigo, 0)
            L_r = n_mov / n_mov_total
            w_n = L_r / A_r if A_r > 0 else np.nan
            w_n_por_codigo[codigo] = w_n
            registro.append({
                "variable": var, "codigo": codigo, "n_celdas_raster": int(n_celdas),
                "pct_area_Ar": round(100 * A_r, 3), "n_movimientos": int(n_mov),
                "pct_movimientos_Lr": round(100 * L_r, 3), "w_n_L_r_sobre_A_r": round(w_n, 4),
            })

        w_n_max = max(v for v in w_n_por_codigo.values() if not np.isnan(v) and v > 0)
        w_n_validos_no_cero = [v for v in w_n_por_codigo.values() if not np.isnan(v) and v > 0]
        valor_neutral = round(float(np.mean(w_n_validos_no_cero)) / w_n_max, 4)

        mapeo = {}
        for codigo, w_n in w_n_por_codigo.items():
            mapeo[codigo] = round(w_n / w_n_max, 4)
        mapeos[var] = mapeo
        valores_neutrales[var] = valor_neutral

    registro_df = pd.DataFrame(registro)
    registro_df["peso_wc_normalizado"] = registro_df.apply(
        lambda r: mapeos[r["variable"]][r["codigo"]], axis=1)
    return mapeos, valores_neutrales, registro_df


if __name__ == "__main__":
    mapeos, valores_neutrales, registro = calcular_pesos_clase_FR()
    pd.set_option("display.width", 160)
    print(registro.to_string(index=False))
    print("\nValores neutrales (para códigos del ráster nunca vistos en los 128 puntos de movimiento):")
    print(valores_neutrales)
