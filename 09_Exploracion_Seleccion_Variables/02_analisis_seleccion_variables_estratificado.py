"""
CÓDIGO 2 (variante): ANÁLISIS Y SELECCIÓN DE VARIABLES — INVENTARIO ESTRATIFICADO (v2)
================================================================
Misma lógica que 02_analisis_seleccion_variables.py, pero usando el
inventario generado en `11_Inventario_Discriminado_Estratificado` (v2):
128 movimientos reales (sin modificar) + 128 puntos "NO" con disimilitud
ambiental MODERADA (3-5 de 8 variables clave) y muestreo espacialmente
estratificado (ver ../11_Inventario_Discriminado_Estratificado/README.md).

Se guarda en subcarpetas separadas (tablas_estratificado/, figuras_estratificado/)
para no sobreescribir ni los resultados originales (tablas/, figuras/) ni
los de la v1 discriminado-extremo (tablas_discriminado/, figuras_discriminado/).

Salidas (en esta carpeta):
  - tablas_estratificado/ranking_variables.csv
  - tablas_estratificado/estadisticas_numericas.csv
  - tablas_estratificado/estadisticas_categoricas.csv
  - tablas_estratificado/informacion_mutua_f_score.csv
  - figuras_estratificado/analisis_<variable>.png
  - figuras_estratificado/analisis_categorico_<variable>.png
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy import stats
from sklearn.metrics import roc_curve, auc
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import mutual_info_classif, f_classif
import warnings

warnings.filterwarnings("ignore")

# -------------------------------------------------------------------------
# Configuración de rutas
# -------------------------------------------------------------------------
INVENTARIO_ESTRATIFICADO_SHP = (
    r"C:\Users\Angela Acosta\OneDrive\Documentos\TRABAJO_FINAL_CARTOGRAFIA\MODELOS\Resultados"
    r"\11_Inventario_Discriminado_Estratificado\inventario_nuevo\puntos_inventario_estratificado.shp"
)
CARPETA_SALIDA = os.path.dirname(os.path.abspath(__file__))
DIR_TABLAS = os.path.join(CARPETA_SALIDA, "tablas_estratificado")
DIR_FIGURAS = os.path.join(CARPETA_SALIDA, "figuras_estratificado")
os.makedirs(DIR_TABLAS, exist_ok=True)
os.makedirs(DIR_FIGURAS, exist_ok=True)

# Percentiles poblacionales: reutiliza el dominio completo ya generado por
# 01_exploracion_variables.py (no depende del inventario, es el raster completo)
ARCHIVO_DOMINIO = os.path.join(CARPETA_SALIDA, "tablas", "dataframe_completo.pkl")

VARIABLES_CATEGORICAS = ["cobertura", "uso_actual", "geologia", "geomorfologia"]
VARIABLES_NUMERICAS = ["pendiente", "aspecto", "curvatura", "flujo_acum", "elevacion", "dist_drenajes"]
TODAS_LAS_VARIABLES = VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS

RENOMBRAR_COLUMNAS = {
    "dist_drena": "dist_drenajes",
    "geomorfolo": "geomorfologia",
}
COLUMNA_PRESENCIA = "Y"

print("=" * 60)
print("CÓDIGO 2 (INVENTARIO ESTRATIFICADO v2): ANÁLISIS Y SELECCIÓN DE VARIABLES")
print("=" * 60)

# -------------------------------------------------------------------------
# Carga del inventario estratificado (ya viene con 128 SI + 128 NO en un solo archivo)
# -------------------------------------------------------------------------
puntos = gpd.read_file(INVENTARIO_ESTRATIFICADO_SHP).rename(columns=RENOMBRAR_COLUMNAS)
df_clean = puntos[TODAS_LAS_VARIABLES + [COLUMNA_PRESENCIA]].copy()
df_clean = df_clean.rename(columns={COLUMNA_PRESENCIA: "inventario"})

print(f"Inventario estratificado cargado: {df_clean.shape}")
print(df_clean["inventario"].value_counts())

si_lands = df_clean[df_clean["inventario"] == 1]
no_lands = df_clean[df_clean["inventario"] == 0]
print(f"Puntos con movimiento: {len(si_lands)} | NO estratificados: {len(no_lands)}")

df_dominio = pd.read_pickle(ARCHIVO_DOMINIO) if os.path.exists(ARCHIVO_DOMINIO) else None
if df_dominio is None:
    print("AVISO: no se encontró tablas/dataframe_completo.pkl; ejecuta antes 01_exploracion_variables.py.")

# -------------------------------------------------------------------------
# Análisis de variables numéricas
# -------------------------------------------------------------------------
print("\n" + "=" * 80)
print("ANÁLISIS DETALLADO - VARIABLES NUMÉRICAS")
print("=" * 80)

results_numericas = {}

for var in VARIABLES_NUMERICAS:
    print(f"\n{'-'*60}\nVARIABLE: {var.upper()}\n{'-'*60}")

    data_si = si_lands[var].dropna()
    data_no = no_lands[var].dropna()

    stats_si = {"count": len(data_si), "mean": data_si.mean(), "median": data_si.median(), "std": data_si.std()}
    stats_no = {"count": len(data_no), "mean": data_no.mean(), "median": data_no.median(), "std": data_no.std()}

    t_stat, p_val_t = stats.ttest_ind(data_si, data_no)
    u_stat, p_val_u = stats.mannwhitneyu(data_si, data_no, alternative="two-sided")
    ks_stat, p_val_ks = stats.ks_2samp(data_si, data_no)

    data_all = df_clean[var]
    y_all = df_clean["inventario"]
    fpr, tpr, _ = roc_curve(y_all, data_all)
    auc_score = auc(fpr, tpr)

    results_numericas[var] = dict(
        stats_con_mm=stats_si, stats_sin_mm=stats_no,
        t_stat=t_stat, p_val_t=p_val_t, u_stat=u_stat, p_val_u=p_val_u,
        ks_stat=ks_stat, p_val_ks=p_val_ks, auc_score=auc_score,
        diferencia_media=stats_si["mean"] - stats_no["mean"],
        fpr=fpr, tpr=tpr,
    )

    print(f"  Con MM  - Media: {stats_si['mean']:.4f}  Mediana: {stats_si['median']:.4f}  Std: {stats_si['std']:.4f}")
    print(f"  NO estr.- Media: {stats_no['mean']:.4f}  Mediana: {stats_no['median']:.4f}  Std: {stats_no['std']:.4f}")
    signif = lambda p: "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print(f"  T-test:        t={t_stat:.4f}  p={p_val_t:.6f} {signif(p_val_t)}")
    print(f"  Mann-Whitney:  U={u_stat:.0f}  p={p_val_u:.6f} {signif(p_val_u)}")
    print(f"  Kolmogorov-S:  KS={ks_stat:.4f}  p={p_val_ks:.6f} {signif(p_val_ks)}")
    print(f"  AUC (ROC):     {auc_score:.4f}")

    if p_val_t < 0.05 or p_val_u < 0.05:
        direction = "altos" if stats_si["mean"] > stats_no["mean"] else "bajos"
        fuente = df_dominio[var].dropna() if df_dominio is not None else df_clean[var]
        p20, p40, p60, p80 = np.percentile(fuente, [20, 40, 60, 80])
        print(f"  Categorización sugerida (valores {direction} = mayor riesgo), percentiles poblacionales:")
        print(f"    p20={p20:.2f}  p40={p40:.2f}  p60={p60:.2f}  p80={p80:.2f}")

# -------------------------------------------------------------------------
# Análisis de variables categóricas
# -------------------------------------------------------------------------
print("\n" + "=" * 80)
print("ANÁLISIS DETALLADO - VARIABLES CATEGÓRICAS")
print("=" * 80)

results_categoricas = {}

for var in VARIABLES_CATEGORICAS:
    print(f"\n{'-'*60}\nVARIABLE CATEGÓRICA: {var.upper()}\n{'-'*60}")

    contingency_table = pd.crosstab(df_clean[var], df_clean["inventario"])
    try:
        chi2, p_chi2, dof, expected = stats.chi2_contingency(contingency_table)
    except Exception as e:
        print(f"  Error en chi-cuadrado: {e}")
        continue

    total_counts = contingency_table.sum(axis=1)
    proportions = (contingency_table.get(1, 0) / total_counts).fillna(0)
    sorted_props = proportions.sort_values(ascending=False)

    results_categoricas[var] = dict(
        chi2=chi2, p_chi2=p_chi2, contingency_table=contingency_table,
        proportions=proportions, n_categories=len(proportions),
        range_proportion=proportions.max() - proportions.min(),
    )

    print(f"  Categorías únicas: {len(proportions)}")
    print(f"  Chi-cuadrado: {chi2:.4f}  p={p_chi2:.6f}")
    print(f"  Rango de proporciones con movimiento: {proportions.min():.3f} - {proportions.max():.3f}")
    for cat, prop in sorted_props.items():
        n_mm = contingency_table.loc[cat, 1] if 1 in contingency_table.columns else 0
        n_tot = total_counts.loc[cat]
        print(f"    Categoría {cat:<10} {prop:.3f}  ({n_mm}/{n_tot})")

# -------------------------------------------------------------------------
# Ranking de variables
# -------------------------------------------------------------------------
print("\n" + "=" * 80)
print("RANKING DE VARIABLES POR PODER DISCRIMINATIVO")
print("=" * 80)

ranking_data = []
for var, r in results_numericas.items():
    ranking_data.append(dict(
        variable=var, tipo="numérica", auc_score=r["auc_score"],
        p_value_min=min(r["p_val_t"], r["p_val_u"]),
        significativa=min(r["p_val_t"], r["p_val_u"]) < 0.05,
    ))
for var, r in results_categoricas.items():
    auc_aprox = 0.5 + r["range_proportion"] / 2
    ranking_data.append(dict(
        variable=var, tipo="categórica", auc_score=auc_aprox,
        p_value_min=r["p_chi2"], significativa=r["p_chi2"] < 0.05,
    ))

ranking_df = pd.DataFrame(ranking_data).sort_values(["significativa", "auc_score"], ascending=[False, False])
ranking_df.insert(0, "rank", range(1, len(ranking_df) + 1))

print(f"{'Rank':<5}{'Variable':<18}{'Tipo':<12}{'AUC':<8}{'p-value':<12}{'Signif.'}")
for _, row in ranking_df.iterrows():
    signif = "***" if row["p_value_min"] < 0.001 else "**" if row["p_value_min"] < 0.01 else "*" if row["p_value_min"] < 0.05 else ""
    print(f"{row['rank']:<5}{row['variable']:<18}{row['tipo']:<12}{row['auc_score']:<8.3f}{row['p_value_min']:<12.6f}{signif}")

top5 = ranking_df.head(5)["variable"].tolist()
print(f"\nReferencia 'top 5' (no se descartan las demás): {top5}")

# -------------------------------------------------------------------------
# Información mutua y F-scores
# -------------------------------------------------------------------------
print("\n" + "=" * 50)
print("INFORMACIÓN MUTUA Y F-SCORES")
print("=" * 50)

X = df_clean[TODAS_LAS_VARIABLES].copy()
y = df_clean["inventario"]
es_discreta = [v in VARIABLES_CATEGORICAS for v in TODAS_LAS_VARIABLES]

X_scaled = StandardScaler().fit_transform(X)
mi_scores = mutual_info_classif(X_scaled, y, discrete_features=es_discreta, random_state=42)
f_scores, f_pvals = f_classif(X_scaled, y)

mi_f_df = pd.DataFrame({
    "variable": TODAS_LAS_VARIABLES,
    "mutual_info": mi_scores,
    "f_score": f_scores,
    "f_p_value": f_pvals,
}).sort_values("mutual_info", ascending=False)

print(mi_f_df.to_string(index=False))

# -------------------------------------------------------------------------
# Gráficos por variable
# -------------------------------------------------------------------------
print("\n" + "=" * 50)
print("GENERANDO GRÁFICOS")
print("=" * 50)

for var in VARIABLES_NUMERICAS:
    r = results_numericas[var]
    data_si = si_lands[var].dropna()
    data_no = no_lands[var].dropna()

    fig = plt.figure(figsize=(16, 11))
    gs = gridspec.GridSpec(2, 2, height_ratios=[1, 1], width_ratios=[2, 1])

    ax1 = plt.subplot(gs[0, 0])
    data_si.plot.kde(ax=ax1, label="Con MM", color="red", linewidth=2.5)
    data_no.plot.kde(ax=ax1, label="NO estratificado", color="blue", linewidth=2.5)
    ax1.axvline(data_si.mean(), color="black", linestyle="-", alpha=0.7)
    ax1.axvline(data_no.mean(), color="black", linestyle="--", alpha=0.7)
    ax1.set_title(f"Densidad: {var}")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    texto = f"AUC: {r['auc_score']:.3f}\nT-test p: {r['p_val_t']:.4f}\nMann-Whitney p: {r['p_val_u']:.4f}"
    ax1.text(0.02, 0.98, texto, transform=ax1.transAxes, va="top",
              bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))

    ax2 = plt.subplot(gs[0, 1])
    bp = ax2.boxplot([data_si, data_no], patch_artist=True, tick_labels=["Con MM", "NO estr."])
    for patch, color in zip(bp["boxes"], ["red", "blue"]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax2.set_title(f"Boxplot: {var}")
    ax2.grid(True, alpha=0.3)

    ax3 = plt.subplot(gs[1, 0])
    ax3.hist(data_si, bins=20, alpha=0.6, color="red", density=True, label="Con MM")
    ax3.hist(data_no, bins=20, alpha=0.6, color="blue", density=True, label="NO estratificado")
    ax3.set_title(f"Histograma: {var}")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    ax4 = plt.subplot(gs[1, 1])
    ax4.plot(r["fpr"], r["tpr"], color="darkorange", lw=2.5, label=f"AUC = {r['auc_score']:.3f}")
    ax4.plot([0, 1], [0, 1], color="navy", lw=1.5, linestyle="--")
    ax4.set_xlabel("Tasa de falsos positivos")
    ax4.set_ylabel("Tasa de verdaderos positivos")
    ax4.set_title(f"Curva ROC: {var}")
    ax4.legend(loc="lower right")
    ax4.grid(True, alpha=0.3)

    plt.suptitle(f"Análisis (inventario estratificado v2): {var}", fontsize=16)
    plt.tight_layout()
    plt.savefig(os.path.join(DIR_FIGURAS, f"analisis_{var}.png"), dpi=180)
    plt.close(fig)

for var in VARIABLES_CATEGORICAS:
    r = results_categoricas[var]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    r["contingency_table"].plot(kind="bar", stacked=True, ax=ax1, color=["steelblue", "firebrick"], alpha=0.8)
    ax1.set_title(f"Distribución: {var}")
    ax1.set_xlabel("Categoría (código)")
    ax1.legend(["NO estratificado", "Con MM"])
    ax1.grid(True, alpha=0.3)

    r["proportions"].sort_values(ascending=False).plot(kind="bar", ax=ax2, color="darkred", alpha=0.8)
    ax2.axhline(df_clean["inventario"].mean(), color="black", linestyle="--", label="Promedio general")
    ax2.set_title(f"Proporción con movimiento: {var}")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    texto = f"Chi2: {r['chi2']:.2f}\np-value: {r['p_chi2']:.4f}"
    ax2.text(0.02, 0.98, texto, transform=ax2.transAxes, va="top",
              bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))

    plt.tight_layout()
    plt.savefig(os.path.join(DIR_FIGURAS, f"analisis_categorico_{var}.png"), dpi=180)
    plt.close(fig)

# -------------------------------------------------------------------------
# Guardar resultados
# -------------------------------------------------------------------------
print("\n" + "=" * 50)
print("GUARDANDO RESULTADOS")
print("=" * 50)

ranking_df.to_csv(os.path.join(DIR_TABLAS, "ranking_variables.csv"), index=False)
mi_f_df.to_csv(os.path.join(DIR_TABLAS, "informacion_mutua_f_score.csv"), index=False)

df_num_out = pd.DataFrame([
    {"variable": v, "media_con_mm": r["stats_con_mm"]["mean"], "media_no_estr": r["stats_sin_mm"]["mean"],
     "t_stat": r["t_stat"], "p_val_t": r["p_val_t"], "u_stat": r["u_stat"], "p_val_u": r["p_val_u"],
     "ks_stat": r["ks_stat"], "p_val_ks": r["p_val_ks"], "auc_score": r["auc_score"]}
    for v, r in results_numericas.items()
])
df_num_out.to_csv(os.path.join(DIR_TABLAS, "estadisticas_numericas.csv"), index=False)

df_cat_out = pd.DataFrame([
    {"variable": v, "n_categorias": r["n_categories"], "chi2": r["chi2"], "p_chi2": r["p_chi2"],
     "rango_proporcion": r["range_proportion"]}
    for v, r in results_categoricas.items()
])
df_cat_out.to_csv(os.path.join(DIR_TABLAS, "estadisticas_categoricas.csv"), index=False)

print(f"Guardado en: {DIR_TABLAS}")
print(f"Figuras en:  {DIR_FIGURAS}")

print("\n" + "=" * 80)
print("RESUMEN FINAL - CÓDIGO 2 (INVENTARIO ESTRATIFICADO v2)")
print("=" * 80)
print(f"Variables analizadas: {len(TODAS_LAS_VARIABLES)}")
print(f"Observaciones: {len(df_clean)} (128 movimiento + 128 NO estratificados)")
print("Ranking completo guardado en tablas_estratificado/ranking_variables.csv")
print("=" * 80)
