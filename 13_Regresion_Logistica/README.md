# Regresión Logística y Selección de Variables por Pasos

Implementación del capítulo *Métodos basados en datos* del libro de
Cartografía Geotécnica, específicamente el modelo paramétrico de Regresión
Logística (GLM binomial), con selección de variables por pasos (stepwise
selection) en sus tres variantes clásicas: forward selection, backward
elimination y stepwise bidireccional, usando AIC como criterio de decisión
y registrando el pseudo R² de McFadden en cada paso (indicación del
profesor).

## Fuente de datos

Mismo inventario de 256 puntos usado en los otros dos métodos (`13_AHP_Combinado`,
`14_WoE_Susceptibilidad`): 128 movimientos reales sin modificar + 128 puntos
"NO" por disimilitud ambiental moderada y muestreo espacialmente
estratificado (carpeta de origen no incluida en este repo, por tamaño).

## Cómo replicar

Ejecutar en orden desde esta carpeta con el intérprete del proyecto
(`C:\Users\Angela Acosta\AppData\Local\Programs\Python\Python310\python.exe`):

```
config_base.py                # config compartida: carga de datos, agrupación de
                               # categorías raras, construcción de fórmulas,
                               # ajuste robusto del modelo logit (no se ejecuta directamente)
01_modelo_completo.py         # diagnóstico: el modelo de 10 variables no es identificable
02_forward_selection.py       # selección hacia adelante por AIC
03_backward_elimination.py    # eliminación hacia atrás por AIC
04_stepwise_bidireccional.py  # combinación de las dos anteriores
05_comparacion_metodos.py     # compara los 3 métodos, arma el modelo final, ROC/AUC
06_mapa_susceptibilidad.py    # aplica el modelo final a los rasters de toda la cuenca
07_generar_informe.py         # compila todo en Informe_Regresion_Logistica.docx
```

## Dos problemas de identificabilidad detectados y corregidos

Al intentar ajustar el modelo "completo" (las 10 variables a la vez, el
punto de partida clásico de backward elimination) aparecieron dos
problemas reales, diagnosticados con evidencia y corregidos en
`config_base.py` en vez de ignorarse:

1. **Separación (cuasi-)completa por categorías dispersas.** Varias
   categorías cualitativas tienen muy pocas observaciones y resultado
   homogéneo (p. ej. cobertura=3.0 con 1 sola observación, 100%
   movimiento). Se agrupan (función `colapsar_categorias_raras`) todas las
   categorías con menos de 5 observaciones en una clase "Otras"; si esa
   clase "Otras" seguiría siendo demasiado pequeña, se fusiona en su lugar
   con la categoría mayoritaria de la variable.
2. **Colinealidad casi perfecta entre `cobertura` y `uso_actual`.** Estas
   dos variables están casi anidadas 1 a 1 en la muestra (ver tabla de
   contingencia en el informe), lo que deja la matriz de diseño con rango
   deficiente cuando ambas entran juntas al modelo. `ajustar_modelo()`
   verifica el rango de la matriz de diseño (patsy) antes de cada ajuste y
   descarta cualquier combinación no identificable, igual que un modelo
   que no converge — así la selección por pasos evita automáticamente
   combinar ambas variables, sin necesidad de excluir una a mano.

`ajustar_modelo()` también prueba varios optimizadores (newton → bfgs →
lbfgs) y descarta cualquier resultado con parámetros no estimados, errores
estándar disparados (>15), o un optimizador que "converge" sin moverse del
punto nulo (patología observada con bfgs/lbfgs en problemas mal
condicionados).

## Resultado principal

Los tres métodos de selección por pasos convergen **exactamente** al mismo
modelo de 5 variables: `uso_actual + geologia + geomorfologia + curvatura
+ dist_drenajes` (AIC 356.89 → 268.93, pseudo R² de McFadden 0 → 0.3606) —
evidencia de un óptimo robusto por AIC, no dependiente del algoritmo de
búsqueda. `pendiente` (la variable de mayor peso en la jerarquía de
literatura usada en `08_Metodos_Conocimiento`) nunca entra al modelo,
coincidiendo con el hallazgo ya documentado en `06_Variables_Condicionantes`.
`dist_drenajes` es seleccionada por AIC pero no alcanza significancia
individual al 5% (p=0.135) en el modelo conjunto — se reporta como
limitación explícita.

El modelo final tiene AUC=0.869 y concentra el 71.1% de los movimientos
reales en las clases Alta+Muy alta de susceptibilidad (que cubren solo 40%
del área) — un desempeño de validación muy superior a los métodos
heurísticos puros de `08_Metodos_Conocimiento` (AHP 26.6%, Índices 25.8%)
y comparable al método combinado con Frequency Ratio (48.4%).

**Limitación:** el AUC y la validación se calcularon sobre la misma
muestra de ajuste (n=256), sin partición externa de entrenamiento/prueba,
dado el tamaño limitado del inventario.
