# AJUSTE DEL ROADMAP TRAS D0

El universo se mantiene en **56 Specs**. D0 no añade ni elimina Specs: cambia el **orden**, resuelve
bloqueos y adelanta dos capturas de datos.

## Cambio de bloqueos

| | Antes de D0 | Después de D0 |
|---|---:|---:|
| Bloqueantes que impiden **escribir** Specs | 5 | **0** |
| Bloqueantes que impiden **cerrar** Specs | 2 | 2 |
| Specs bloqueadas por decisión implícita | 13 | **0** |
| Decisiones estructurales sin documentar | 13 | **0** |

## Cambios en el orden de olas

| Ola | Antes de D0 | Después de D0 | Motivo del cambio |
|---|---|---|---|
| **0** | PG real · backup/restore · auditoría en 2 módulos · FK factura↔pedido · docs desfasados | **+ columnas de UOM, presentación y factor en líneas** (solo esquema) | `D0-historical-data-risk.md` H-01: cada línea escrita sin unidad es ambigua para siempre |
| **1** | 045 · 008 · 046 | **Sin cambio**, pero ahora con arquitectura decidida en ADR-D0-002, 004 y 008 | Las tres pasan de «hay que decidir cómo» a «hay que construir lo decidido» |
| **2** | 012 · 011 · 007 | **007 sube junto a 011** | ADR-D0-013 muestra que las dimensiones condicionan el modelo de línea igual que la unidad |
| **3** | 018 · 015 · 026 | Sin cambio | — |
| **4** | 019 · 020 · 021 · 022 | Sin cambio | Ahora con estados decididos (ADR-D0-010) |
| **5** | 029 · 030 · 031 · 032 · 033 | Sin cambio | Reserva y confirmación decididas (ADR-D0-003, 012) |
| **6** | 034 · 035 | **034 pierde su parte de esquema** (adelantada a Ola 0) | H-02 |
| **7** | Fiscal 039-044 · 014 · 056 | **Puede arrancar hoy** | El gobierno está cerrado; falta contenido tributario, que es trabajo externo |
| **8-9** | Sin cambio | Sin cambio | — |

## Recomendación de división de Specs, ahora fundamentada

El GAP Analysis propuso dividir `001-fundacion` y `005-ventas`. D0 lo confirma con criterio:

| Spec actual | Decisiones D0 que la atraviesan | Veredicto |
|---|---:|---|
| `001-fundacion` | D0-01, 04, 06, 08, 13 → 5 | **SPLIT** — cubre 10 maestras y 5 decisiones fundacionales distintas |
| `005-ventas` | D0-03, 05, 09, 11, 12, 13 → 6 | **SPLIT** — contiene los tres huecos mayores del sistema |

## Nuevas Specs implicadas por D0

Ninguna. Las 13 decisiones se reparten entre Specs maestras ya catalogadas:

| Decisión | Spec propietaria |
|---|---|
| D0-01 | 001 / 054 (criterio de aceptación) |
| D0-02 | **045** |
| D0-03 | **030** |
| D0-04 | **008** |
| D0-05 | **012** |
| D0-06 | **004** |
| D0-07 | **039-043** (gobierno transversal) |
| D0-08 | **046** |
| D0-09 | **011** |
| D0-10 | **021 / 023** |
| D0-11 | **034** |
| D0-12 | **033** |
| D0-13 | **007** |

## Orden recomendado tras D0

| Orden | Spec | Cambio respecto al GAP Analysis | Motivo |
|---:|---|---|---|
| 1ª | **045 Motor de aprobaciones** | Se mantiene | Sigue siendo el nodo de mayor grado; ahora con arquitectura cerrada |
| 2ª | **008 Almacenes físicos** | Se mantiene | Prerequisito de put-away y ruta de picking |
| 3ª | **011 Unidades y presentaciones** | **Sube del 5.º al 3.er puesto** | H-01: es el riesgo histórico máximo, por encima de su severidad nominal |
| 4ª | **046 Gestión documental** | Baja del 4.º al 4.º (sin cambio de posición, cambia lo que la precede) | Habilita evidencia en importación, incidencias y despacho |
| 5ª | **012 Maestros comerciales** | **Baja del 3.º al 5.º** | Su riesgo histórico (H-04) es alto pero menor que H-01, y depende de 045 para los descuentos aprobables |

**El único reordenamiento sustantivo es el intercambio entre 011 y 012**, y lo justifica el análisis
de datos no reconstruibles: una línea sin unidad es más irrecuperable que un precio sin lista, porque
el precio al menos quedó registrado como número y la unidad no quedó registrada en absoluto.
