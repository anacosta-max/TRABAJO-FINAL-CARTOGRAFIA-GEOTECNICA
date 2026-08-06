# -*- coding: utf-8 -*-
"""
Figuras de apoyo para el artículo: mapas de las 10 variables condicionantes
completas (continuas con colorbar, categóricas con leyenda de clases), más
el inventario de movimientos en masa sobre el DEM.
"""
import os
import numpy as np
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, TwoSlopeNorm

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_FIG = os.path.join(BASE, "figuras")
RASTER_FOLDER = r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\masked_by_pendiente_v2"
INVENTARIO_SHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\Resultados"
    r"\11_Inventario_Discriminado_Estratificado\inventario_nuevo\puntos_inventario_estratificado.shp"
)


def leer(nombre):
    with rasterio.open(f"{RASTER_FOLDER}/{nombre}") as src:
        arr = src.read(1).astype(float)
        if src.nodata is not None:
            arr = np.where(arr == src.nodata, np.nan, arr)
        return arr, src.transform, src.bounds


def mapa_continuo(nombre_archivo, titulo, etiqueta_cbar, salida, cmap="viridis",
                   norm=None, transform_log=False):
    arr, transform, bounds = leer(nombre_archivo)
    arr_plot = np.log1p(arr) if transform_log else arr
    fig, ax = plt.subplots(figsize=(5, 7))
    im = ax.imshow(arr_plot, cmap=cmap, norm=norm,
                    extent=[bounds.left, bounds.right, bounds.bottom, bounds.top])
    ax.set_title(f"{titulo}\nCuenca de la quebrada El Circio")
    ax.set_xticks([]); ax.set_yticks([])
    cbar = fig.colorbar(im, ax=ax, shrink=0.7, label=etiqueta_cbar)
    plt.tight_layout()
    plt.savefig(f"{DIR_FIG}/{salida}.png", dpi=170)
    plt.close(fig)
    print(f"Guardado: {salida}.png")
    return arr, transform, bounds


def mapa_categorico(nombre_archivo, titulo, nombres_dict, salida):
    arr, transform, bounds = leer(nombre_archivo)
    codigos_presentes = sorted(set(np.unique(arr[~np.isnan(arr)])))
    n = len(codigos_presentes)
    cmap_base = plt.get_cmap("tab20", n)
    colores = [cmap_base(i) for i in range(n)]
    cmap = ListedColormap(colores)
    arr_reindex = np.full(arr.shape, np.nan)
    for i, c in enumerate(codigos_presentes):
        arr_reindex = np.where(arr == c, i, arr_reindex)

    fig, ax = plt.subplots(figsize=(5.5, 7.5))
    im = ax.imshow(arr_reindex, cmap=cmap, vmin=-0.5, vmax=n - 0.5,
                    extent=[bounds.left, bounds.right, bounds.bottom, bounds.top])
    ax.set_title(f"{titulo}\nCuenca de la quebrada El Circio")
    ax.set_xticks([]); ax.set_yticks([])
    handles = [plt.Rectangle((0, 0), 1, 1, color=colores[i]) for i in range(n)]
    etiquetas = [f"{int(c)}. {nombres_dict.get(int(c), 'Sin clasificar')}" for c in codigos_presentes]
    ax.legend(handles, etiquetas, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              fontsize=6, ncol=1, frameon=False)
    plt.tight_layout()
    plt.savefig(f"{DIR_FIG}/{salida}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardado: {salida}.png")


# ===========================================================================
# Diccionarios de clases (categóricas)
# ===========================================================================
NOMBRES_GEOLOGIA = {1: "Neis Intrusivo de Pantanillo", 2: "Complejo Cajamarca - Esquistos verdes",
                     3: "Neis Intrusivo Abejorral", 4: "Formación Abejorral",
                     5: "Complejo Quebradagrande - Miembro Volcánico",
                     6: "Complejo Cajamarca - Filitas y esquistos cuarzo-sericíticos"}
NOMBRES_GEOMORFOLOGIA = {1: "Espolón bajo de longitud larga", 2: "Espolón moderado de longitud larga",
                          3: "Espolón faceteado alto de longitud larga", 4: "Espolón alto de longitud media",
                          5: "Lomo denudado bajo de longitud larga", 6: "Espolón festoneado alto de longitud larga",
                          7: "Escarpe de línea de falla", 8: "Lomo denudado bajo de longitud media",
                          9: "Espolón alto de longitud larga", 10: "Espolón moderado de longitud media",
                          11: "Faceta triangular", 12: "Espolón bajo de longitud media", 13: "Lomo de falla",
                          14: "Sierra y lomo de presión", 15: "Lomo denudado moderado de longitud larga",
                          16: "Ladera ondulada"}
NOMBRES_COBERTURA = {1: "Cultivos permanentes arbustivos", 2: "Pastos limpios", 3: "Pastos arbolados",
                      4: "Pastos enmalezados", 5: "Mosaico de cultivos", 6: "Mosaico de pastos y cultivos",
                      7: "Mosaico de cultivos/pastos/espacios naturales", 8: "Bosque fragmentado",
                      9: "Bosque de galería y/o ripario", 10: "Plantación forestal",
                      11: "Vegetación secundaria o en transición", 12: "Ríos (50 m)",
                      13: "Cultivos permanentes herbáceos", 14: "Cultivos permanentes arbóreos"}
NOMBRES_USO_ACTUAL = {30202: "Cultivos transitorios semi-intensivos (CTS)",
                       30204: "Cultivos permanentes semi-intensivos (CPS)",
                       30206: "Pastoreo semi-intensivo (PSI)", 30207: "Pastoreo extensivo (PEX)",
                       30211: "Sistema forestal productor (FPD)", 30212: "Sistemas forestales protectores (FPR)",
                       30213: "Áreas para conservación/recuperación de la naturaleza (CRE)",
                       30214: "Protección", 30230: "Cuerpos de Agua Naturales"}

# ===========================================================================
# 6 variables continuas
# ===========================================================================
mapa_continuo("elevacion.tif", "Modelo de Elevación Digital (DEM)", "msnm", "dem", cmap="terrain")
mapa_continuo("pendiente.tif", "Mapa de pendientes", "grados", "pendiente", cmap="YlOrRd")
mapa_continuo("aspecto.tif", "Mapa de aspecto (orientación de ladera)", "grados (0-360°)", "aspecto", cmap="twilight")

arr_curv, _, bounds_c = leer("curvatura.tif")
norm_curv = TwoSlopeNorm(vmin=float(np.nanmin(arr_curv)), vcenter=0, vmax=float(np.nanmax(arr_curv)))
mapa_continuo("curvatura.tif", "Mapa de curvatura", "curvatura (cóncava − / convexa +)",
              "curvatura", cmap="RdBu_r", norm=norm_curv)

mapa_continuo("flujo_acumulado.tif", "Mapa de flujo acumulado (escala log)",
              "ln(1 + celdas acumuladas)", "flujo_acum", cmap="Blues", transform_log=True)
mapa_continuo("dist_drenajes.tif", "Mapa de distancia a drenajes", "metros",
              "dist_drenajes", cmap="GnBu_r")

# ===========================================================================
# 4 variables categóricas
# ===========================================================================
mapa_categorico("geologia.tif", "Mapa geológico", NOMBRES_GEOLOGIA, "geologia")
mapa_categorico("geomorfologia.tif", "Mapa geomorfológico", NOMBRES_GEOMORFOLOGIA, "geomorfologia")
mapa_categorico("cobertura.tif", "Mapa de cobertura de la tierra", NOMBRES_COBERTURA, "cobertura")
mapa_categorico("uso_actual.tif", "Mapa de uso actual del suelo", NOMBRES_USO_ACTUAL, "uso_actual")

# ===========================================================================
# Inventario de movimientos sobre el DEM
# ===========================================================================
elev, transform, bounds = leer("elevacion.tif")
puntos = gpd.read_file(INVENTARIO_SHP)
mov = puntos[puntos["Y"].astype(int) == 1]
no_mov = puntos[puntos["Y"].astype(int) == 0]

fig, ax = plt.subplots(figsize=(5, 7))
ax.imshow(elev, cmap="Greys", alpha=0.6, extent=[bounds.left, bounds.right, bounds.bottom, bounds.top])
ax.scatter(no_mov.geometry.x, no_mov.geometry.y, s=8, c="#1a9850", label=f"Estables (n={len(no_mov)})", alpha=0.8)
ax.scatter(mov.geometry.x, mov.geometry.y, s=8, c="#d73027", label=f"Movimiento (n={len(mov)})", alpha=0.8)
ax.set_title("Inventario de movimientos en masa\nCuenca de la quebrada El Circio")
ax.set_xticks([]); ax.set_yticks([])
ax.legend(loc="lower right", fontsize=8)
plt.tight_layout()
plt.savefig(f"{DIR_FIG}/inventario.png", dpi=170)
plt.close(fig)
print("Guardado: inventario.png")
