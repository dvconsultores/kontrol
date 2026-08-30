# PLAN — SPEC 011

## 1. Constitution Gate

| Principio | Cumplimiento | Cómo |
|---|---|---|
| P2 · Autorización expresa | ✅ | Ciclo documental autorizado; se detiene antes de implementar |
| P3 · Trazabilidad | ✅ | Matriz bidireccional item por item |
| P4 · Núcleo fiscal separado | ✅ | No se altera el motor fiscal; la factura conserva su snapshot (§53) |
| **P5 · Dato histórico protegido** | ✅ **eje de la Spec** | `base_quantity` congelada; lo fiscal irreconstruible no se toca |
| P6 · Backend es la autoridad | ✅ | `base_quantity` siempre recalculada en servidor (FR-011-043) |
| P8 · Sin negocio en código | ✅ | Catálogo de unidades **vacío**; ninguna unidad ni presentación codificada |
| P11 · WCAG 2.2 AA y responsive | ✅ | NFR-011-04/05 |
| P13 · Integridad transaccional | ✅ | `NUMERIC`, `factor > 0`, sin solapamiento, FK reales |
| P18 · Sin modales para formularios complejos | ✅ | Presentaciones en página completa |
| **P21 · Paridad del motor** | ✅ | PostgreSQL 18.x en toda la evidencia |
| **P22 · Autoridad única transversal** | ✅ **eje** | Un solo motor de conversión; ningún módulo replica el cálculo |
| **P23 · Captura temprana** | ✅ **eje** | La unidad de una transacción no se recupera después: se captura al escribir |

**0 violaciones. 0 enmiendas requeridas.**

## 2. Qué se implementa y qué no

| Se implementa | No se implementa |
|---|---|
| Unidad, dimensión, precisión, redondeo | Alias de unidad (`FUTURE_CAPABILITY`) |
| Unidad base obligatoria e inmutable con historial | Variantes y atributos (Spec 010) |
| Presentación por producto con factor versionado | Presentación genérica reutilizable (no aporta) |
| Motor único de conversión | Peso variable / *catch weight* (`FUTURE_CAPABILITY`) |
| 4 columnas de snapshot en 17 tablas | Los procesos de esas 17 tablas (§39) |
| 31 columnas de `Float` a `NUMERIC` | Motor de precios (Spec 012) |
| Backfill clasificado | Empaquetado de despacho (Spec 035) |
| 2 pantallas | Reportes (Spec 050) |

## 3. Arquitectura

```
app/modules/master_data/
    models.py      UnitOfMeasure+, UnitConversion*, Presentation*,
                   ProductPresentation, ProductPresentationVersion
    uom.py         ← NUEVO · motor único de conversión (P22)
    uom_api.py     ← NUEVO · endpoints

Consumidores (no se implementan aquí, solo reciben columnas):
    inventory · purchasing · sales   → 4 columnas por línea
```

`uom.py` es el equivalente de `structure.py` en la Spec 008: donde vive el valor,
probado sin API.

## 4. Decisiones técnicas

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| Factor en `ProductPresentationVersion` | Factor en `Presentation` | La caja de un producto no es la de otro |
| Versionado por vigencia | Sobrescritura | R-D0-09-4 |
| Snapshot en la línea **además** del versionado | Solo versionado | Un borrado de versión no puede romper el histórico |
| `NUMERIC(18,6)` | `Float` | `KQA-100` |
| Índice único parcial sobre versión abierta | `EXCLUDE USING gist` | Evita exigir `btree_gist`, fuera de la lista blanca de `ADR-D0-001` |
| Conversión física y comercial separadas | Motor común | Un kilo siempre son mil gramos; una caja no siempre son cien unidades |
| Snapshot al emitir | Al crear la línea | Un borrador antiguo mostraría un factor que el usuario nunca vio |
| `document_date` como fecha efectiva | `created_at` | Es la fecha con efecto fiscal |

## 5. Fases

| Fase | Contenido | Depende de | Por qué en este orden |
|---|---|---|---|
| **F1 · Modelo de unidades** | `UnitOfMeasure` extendida, `UnitConversion` a `NUMERIC` con validación de dimensión | — | Nada se convierte sin unidades correctas |
| **F2 · Presentaciones versionadas** | `ProductPresentation`, `ProductPresentationVersion`, restricción de no solapamiento | F1 | — |
| **F3 · Motor de conversión** | `resolve_conversion`, `to_base`, redondeo, resolución masiva | F1, F2 | Donde vive el valor; se prueba sin API |
| **F4 · Columnas transaccionales** | 4 columnas × 17 tablas, y `Float → NUMERIC` en 31 columnas | F3 | **Antes que la API de consumo**: cada día sin capturar la unidad amplía la deuda irrecuperable (P23) |
| **F5 · Backfill clasificado** | Clasificador de 4 clases, reporte, bloqueo fiscal | F4 | Los datos legados se clasifican una vez existen las columnas |
| **F6 · API** | Unidades, presentaciones, versiones, previsualización | F3 | — |
| **F7 · Pruebas de backend** | Unidad, integración, concurrencia, migración, **sobre PostgreSQL** | F5, F6 | Antes del frontend: valida el contrato que la UI consumirá |
| **F8 · Frontend** | 2 pantallas | F6, F7 | — |
| **F9 · E2E y cierre** | E2E, cross-browser, axe, responsive, convergencia | F8 | — |

> **F4 va antes que F6** por el Principio 23, igual que la conversión a FK
> precedió a la API en la Spec 008. La razón es la misma y aquí es más grave: una
> ubicación olvidada podía reconstruirse desde el movimiento; **una unidad
> olvidada no puede reconstruirse desde nada.**

## 6. Migraciones previstas

Números provisionales (§44): la cadena está hoy en `0018` y el número real se fija
al implementar, comprobando `alembic heads`.

| Migración | Tipo | Contenido | Clasificación |
|---|---|---|---|
| `00XX_uom_model` | Esquema | Unidades extendidas, presentaciones versionadas, restricciones | `SAFE_MIGRATION` |
| `00XX_quantity_numeric` | Esquema + datos | 31 columnas `Float → NUMERIC`, con reporte de cambios de valor | `DATA_PRECISION_CHANGE` |
| `00XX_line_uom_columns` | Esquema | 4 columnas × 17 tablas, todas *nullable* al crearse | `SAFE_MIGRATION` |
| `00XX_uom_backfill` | Datos | Clasificación, backfill, reporte, bloqueo fiscal | `BACKFILL_REQUIRED` + `MANUAL_REVIEW_REQUIRED` + `BLOCKING_ON_FISCAL` |

Separación deliberada (§45, CL-011-16): las tres primeras son válidas en modo
offline (`alembic upgrade --sql`); la cuarta **no**, porque lee datos para
clasificarlos, y no debe evidenciarse así.

Las columnas nacen *nullable* y solo pasan a `NOT NULL` cuando el backfill
demuestra que no quedan líneas sin resolver. Forzar `NOT NULL` antes obligaría a
inventar un valor, que es lo que la Spec prohíbe.

### Riesgo declarado

`00XX_uom_backfill` es la migración de mayor riesgo del proyecto hasta la fecha,
por encima de `0018` de la Spec 008: allí se imponía integridad sobre referencias
que **existían**; aquí se asigna significado a un dato que **nunca se capturó**.
La política completa está en `legacy-uom-migration-matrix.md` y es normativa.

## 7. Impacto en módulos existentes

| Módulo | Cambio | Riesgo |
|---|---|---|
| `master_data` | Extensión mayor: 2 entidades nuevas, motor, API, 2 pantallas | Medio |
| `inventory` | 6 tablas reciben columnas; `Float → NUMERIC` en 12 columnas | **Alto** — es el módulo mejor probado |
| `purchasing` | 6 tablas | **Alto** |
| `sales` | 6 tablas | **Alto** |
| `regulatory` | 1 columna | Bajo |

Los tres dominios de alto riesgo ejecutan su batería completa como criterio de
salida, **sin cambio de expectativa** salvo donde el contrato cambie de forma
documentada.

## 8. Estrategia de pruebas

Toda la evidencia sobre PostgreSQL 18.x. Detalle en `test-plan.md`.

## 9. Rollout

1. Esquema y motor, sin consumidores: nada cambia de comportamiento.
2. Columnas *nullable*: las líneas nuevas empiezan a capturar unidad.
3. Backfill con reporte, revisable antes de endurecer.
4. `NOT NULL` solo cuando el reporte demuestre 0 líneas sin resolver.

Reversible en cada paso hasta el tercero. El cuarto es el punto de no retorno y
exige que el reporte esté limpio.

## 10. Políticas normativas anexas

| Documento | Gobierna |
|---|---|
| `transaction-uom-impact-matrix.md` | Qué líneas reciben columnas y cuáles no, con justificación |
| `legacy-uom-migration-matrix.md` | Clases del backfill, regla del factor 1, bloqueo fiscal, reporte |

Ninguno amplía el alcance: ambos **restringen** lo que la implementación puede
hacer.

## 11. Restricciones de esta iniciativa

No se implementa ninguna de las 14 Specs consumidoras. No se crea la migración.
No se toca el motor fiscal ni el de precios. No se declara `COMPLETE_100` de
nada.
