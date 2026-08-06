# -*- coding: utf-8 -*-
"""
Mosaico compacto con las 5 variables continuas restantes (pendiente,
aspecto, curvatura, flujo acumulado, distancia a drenajes) en una sola
figura, para no sobrecargar el artículo con 5 figuras grandes separadas.
"""
import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_FIG = os.path.join(BASE, "figuras")
RASTER_FOLDER = r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\masked_by_pendiente_v2"


def leer(nombre):
    with rasterio.open(f"{RASTER_FOLDER}/{nombre}") as src:
        arr = src.read(1).astype(float)
        if src.nodata is not None:
            arr = np.where(arr == src.nodata, np.nan, arr)
        return arr, src.bounds


variables = [
    ("pendiente.tif", "Pendiente (°)", "YlOrRd", False, None),
    ("aspecto.tif", "Aspecto (°)", "twilight", False, None),
    ("curvatura.tif", "Curvatura", "RdBu_r", False, "diverging"),
    ("flujo_acumulado.tif", "Flujo acum. (ln)", "Blues", True, None),
    ("dist_drenajes.tif", "Dist. drenajes (m)", "GnBu_r", False, None),
]

fig, axes = plt.subplots(1, 5, figsize=(11, 4.2))
for ax, (archivo, titulo, cmap, log, tipo_norm) in zip(axes, variables):
    arr, bounds = leer(archivo)
    arr_plot = np.log1p(arr) if log else arr
    norm = None
    if tipo_norm == "diverging":
        norm = TwoSlopeNorm(vmin=float(np.nanmin(arr_plot)), vcenter=0, vmax=float(np.nanmax(arr_plot)))
    im = ax.imshow(arr_plot, cmap=cmap, norm=norm,
                    extent=[bounds.left, bounds.right, bounds.bottom, bounds.top])
    ax.set_title(titulo, fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.85, pad=0.02, aspect=12)
    cbar.ax.tick_params(labelsize=6)

fig.suptitle("Variables continuas condicionantes — cuenca de la quebrada El Circio", fontsize=10, y=1.02)
plt.tight_layout()
plt.savefig(f"{DIR_FIG}/mosaico_continuas.png", dpi=180, bbox_inches="tight")
plt.close(fig)
print("Guardado: mosaico_continuas.png")
