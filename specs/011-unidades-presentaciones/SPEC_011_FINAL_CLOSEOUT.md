# SPEC 011 — FINAL CLOSEOUT

**Unidades, presentaciones y conversiones** · 2026-08-30 · `develop` · PostgreSQL **18.6**

---

## 1. Estado

**`SPEC 011 COMPLETE_100`** — tercera Spec del proyecto en alcanzarlo, tras 045 y 008.

## 2. Fases ejecutadas

| Fase | Contenido | Tareas | Estado |
|---|---|---:|---|
| F1 · Unidades | Dimensión validada, precisión, redondeo, ámbito global | 7 | DONE |
| F2 · Presentaciones versionadas | `ProductPresentationVersion`, no solapamiento | 9 | DONE |
| F3 · Motor de conversión | Autoridad única transversal | 10 | DONE |
| F4 · Columnas transaccionales | 17 tablas × 4 columnas; 30 a `NUMERIC` | 10 | DONE |
| F5 · Backfill clasificado | 4 clases, reporte, aborto fiscal | 10 | DONE |
| F6 · API | 15 rutas | 11 | DONE |
| F7 · Pruebas | 24 nuevas | 20 | DONE |
| F8 · Frontend | 2 pantallas | 11 | DONE |
| F9 · E2E y cierre | 18 E2E, cross-browser, axe | 11 | DONE |

**F4 fue antes que F6**, por P23: cada día sin capturar la unidad amplía una deuda
irrecuperable.

## 3. Modelo implementado

```
UnitOfMeasure ──┬── UnitConversion            (física, sin versión)
                ├── CatalogItem.base_unit_id  (+ base_unit_locked)
                └── Presentation ── ProductPresentationVersion (factor + vigencia)

Línea: quantity + uom_id + presentation_id? + conversion_factor_snapshot
       + base_quantity + uom_source
```

## 4. UOM

`dimension` de vocabulario cerrado con `CHECK`, `decimals` (0-6), `rounding_mode`.
Catálogo **global** (`company_id` nulo) de solo lectura para la empresa, más
unidades propias. **Nace vacío**: KONTROL no entrega ninguna unidad.

`MASA` se admitió junto a `PESO` porque el código anterior ya la usaba: rechazarla
habría invalidado filas existentes (P5).

## 5. Unidad base

Obligatoria en productos inventariables, opcional en servicios.
`base_unit_locked` pasa a `true` con el **primer movimiento** y no vuelve atrás.
Cambiarla después devuelve `BASE_UNIT_LOCKED` con el recuento de movimientos.

## 6. Presentaciones

El factor vive en el par **producto-presentación**, no en la presentación
genérica: la caja de un producto son 100 unidades y la de otro 24.
`buyable`/`sellable`/`storable`/`dispatchable` separan la presentación comercial
de la unidad de despacho. Una presentación no es un SKU.

## 7. Versiones

Cambiar un factor **crea una versión** y cierra la anterior. **No existe endpoint
que edite una versión**: es deliberado. Índice único parcial sobre la versión
abierta más validación de rango en transacción; probado con dos usuarios
simultáneos.

## 8. Motor de conversión

`master_data/uom.py`: `resolve_conversion`, `to_base`, `to_base_bulk`,
`freeze_line`, `quantize`. **Autoridad única verificada por prueba de
arquitectura**: 0 cálculos `cantidad × factor` fuera del motor.

Conversión física y comercial separadas. `KG ↔ L` se rechaza con
`UOM_DIMENSION_MISMATCH`.

## 9. Snapshot histórico

`freeze_line` congela unidad, factor y cantidad base al emitir. La cantidad
original **nunca** se sobrescribe. `uom_source` distingue para siempre lo
capturado de lo supuesto.

**Prueba central (`test_el_historico_no_cambia_al_cambiar_el_factor`):** una orden
de 10 CAJAS emitida con `CAJA = 100` vale 1.000 UND; tras pasar el factor a 120,
sigue valiendo **1.000**, no 1.200, mientras un documento nuevo usa 120.

## 10. Punto de congelamiento

`FREEZE_STATES` declara el punto **por ciclo de vida**, no un literal único
(§15): la orden se congela al aprobarse, la recepción al confirmarse, la factura
al emitirse, el conteo al cerrarse. Un movimiento de inventario **nace
congelado**: no tiene borrador. Verificado por
`test_el_punto_de_congelamiento_es_por_ciclo_de_vida`.

## 11. Las 17 líneas MUST_HAVE_NOW

**17/17 integradas**, verificado por prueba de arquitectura que compara la matriz
aprobada contra el esquema real, sin exclusiones.

`inventory_balances`, `cost_layers` y `triple_matches` **no** las reciben, por
diseño: proyección, derivada y comparación. También verificado.

## 12. Float → Numeric

| Métrica | Valor |
|---|---:|
| Columnas auditadas | 31 |
| Columnas convertidas | **30** |
| Conservada a propósito | 1 (`presentations.content`, legado) |
| Filas con diferencia de valor | **0** |
| Redondeo comercial aplicado por la migración | **Ninguno** |

`base_fiscal` sigue en `NUMERIC(18,2)` — es dinero — y `base_quantity` en
`NUMERIC(18,6)` — es cantidad. **No se confundieron.**

## 13. Migraciones

| Migración | Tipo | Resultado |
|---|---|---|
| `0019_uom_model` | Esquema | **PASS**, válida offline |
| `0020_quantity_numeric` | Esquema + reporte | **PASS**, 30 columnas |
| `0021_line_uom_columns` | Esquema | **PASS**, todas *nullable* |
| `0022_uom_backfill` | Datos | **PASS**, y **bloquea** cuando debe |

## 14. Backfill

Cuatro clases verificadas por separado sobre PostgreSQL real:

| Clase | Comportamiento probado |
|---|---|
| `DETERMINISTIC_BACKFILL` | Unidad base del producto, factor 1, `LEGACY_ASSUMED_BASE` |
| `RECONSTRUCTIBLE_WITH_EVIDENCE` | Candidata **única**, con la regla registrada |
| `AMBIGUOUS` | `uom_id` nulo y `LEGACY_UNRESOLVED`; **no se adivina** |
| `NON_RECONSTRUCTIBLE_FISCAL` | **Cero escrituras**; migración abortada |

La `quantity` original permanece intacta en los cuatro casos.

## 15. ESC-011-01

**Semántica aplicada:** `KONTROL_UOM_BACKFILL_MAX_CRITICAL` es el número
**máximo tolerado**; el valor por defecto es **0**, es decir tolerancia cero:

```
critical_count > MAX_CRITICAL  ->  BLOCK
con MAX_CRITICAL = 0  ->  critical_count >= 1  ->  BLOCK
```

Sin ambigüedad matemática y **sin default permisivo**. Probado en ambos sentidos:
con el default una sola línea crítica aborta; subiéndolo deliberadamente la
migración continúa y la línea fiscal **sigue sin tocarse**, solo marcada. El
reporte registra el umbral y su procedencia (`DEFAULT` o `ENV:…`).

## 16. PostgreSQL

| | |
|---|---|
| Versión | **18.6**, la que fija `ADR-D0-001` |
| Migración limpia | `0001 → 0022` **PASS** |
| Upgrade pre-011 con datos | **PASS** en 7 escenarios sembrados |
| Paridad de esquema | `alembic check` = 18 líneas, **idénticas** al baseline pre-011 |

**011 no introduce ni una línea de drift.**

## 17-19. Backend, API, Frontend

`uom.py` + `uom_api.py`. **15 rutas**; el OpenAPI **global** de 280 rutas genera
sin error — se validó la aplicación entera, no solo 011 (§57).

2 pantallas con URL propia, más la entrada de menú. El formulario dice **«Una
CAJA equivale a ___ UND»**, no «Factor = 100». Los decimales viajan como texto:
un `NUMERIC(18,6)` convertido a `Number` perdería precisión.

## 20-22. Multiempresa, seguridad, auditoría

Unidad global de solo lectura (`UOM_GLOBAL_READ_ONLY`); presentaciones filtradas
por producto y empresa. `base_quantity` **siempre** recalculada en servidor: la
enviada por el cliente se ignora. `If-Match` con el mecanismo existente.

9 acciones auditadas por la capacidad transversal, incluidos los intentos
denegados. Sin tabla local.

## 23-26. Tests

| Suite | Resultado |
|---|---|
| Pytest | **351/351** |
| Vitest | **221/221** |
| Integración y contrato | Incluidos en Pytest |
| Playwright | **18/18** en 3 navegadores |
| Arquitectura | **11/11** |

## 27. Cross-browser

Chromium **6/6** · Firefox **6/6** · WebKit **6/6**. **WebKit se reporta como
WebKit.** Edge y Opera no disponibles: no se declara validación sobre ellos.

## 28-29. Responsive y accesibilidad

7 viewports de 320 a 1920: **sin scroll horizontal**. axe WCAG 2.2 AA sin
violaciones serias, operable con teclado, legible al 150%. **12/12 en los tres
navegadores.**

Un defecto propio detectado y corregido: los selectores de ancho fijo desbordaban
55 px a 320 px. Se hicieron fluidos.

## 30. Regresión fiscal

Cuatro facturas representativas —incluidos `2.5`, `0.333` y `1.000.000 × 0,01`—
comparadas antes y después:

**0 diferencias materiales** en base imponible, impuestos y totales.

## 31. Regresión multidominio

**351/351** sin exclusiones. Cinco defectos reales de tipo aparecieron y se
corrigieron, todos de la familia `KQA-100` (`Decimal` mezclado con `float`):
saldos de inventario, costeo FIFO y promedio, acumulado de recepción, varianza de
conciliación triple y serialización JSON en regulatorio. **Ninguno se ocultó
ajustando una prueba.**

## 32. Build e import resolution

`vite build` real **PASS**. Se ejecutó explícitamente porque `tsc` solo no basta:
en la Spec 008 no detectó un import de paquete inexistente (§91).

## 33. Performance

`to_base_bulk` resuelve un documento completo con un número de consultas
constante. Índice `ix_ppv_resolution` para la resolución por fecha e
`ix_ppv_bulk` para la masiva. Caché **por petición**, nunca entre peticiones.

## 34. Trazabilidad

75 FR · 8 NFR · 40 AC · 99 tareas. **0 huérfanos en las cuatro direcciones.**

## 35. `/speckit.converge 011`

| Comprobación | Resultado |
|---|---|
| Autoridad única de conversión (P22) | ✅ 0 cálculos fuera del motor |
| `unit_id=None` literal | ✅ 0 |
| `Float` en cantidades | ✅ 0 |
| Sistemas paralelos de permisos, auditoría o aprobaciones | ✅ 0 |
| Otras Specs implementadas | ✅ 0 |
| Drift | ✅ 0 atribuible a 011 |
| Literales de unidad en código | ✅ 0 |

**PASS.**

## 36. Deuda externa

| Deuda | Clasificación | Destino |
|---|---|---|
| 18 líneas de drift de licenciamiento | `DEFERRED_EXTERNAL_DEPENDENCY` | Spec 010 |
| 22 violaciones responsive preexistentes | `DEFERRED_EXTERNAL_DEPENDENCY` | Specs 005/054 |
| `qa/pg-provision.sh` sin camino a PG 18 | `DEFERRED_EXTERNAL_DEPENDENCY` | Spec 054 |
| `tsc` no detecta imports inexistentes | **Observación** | Spec 054 |
| `presentations.content` legado sin interpretar | **Observación** | Se conserva; interpretarlo exigiría decisión del cliente |

Ninguna rompe un requisito de 011.

## 37. Specs desbloqueadas — verificadas por contrato

| Spec | Estado | Qué obtiene |
|---|---|---|
| **015, 016, 017** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Líneas con presentación y factor congelado; falta su propio flujo |
| **019, 021** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Recepción compara `base_quantity`; falta el proceso |
| **023** | `PARTIALLY_UNLOCKED` | Movimientos ya convierten y congelan; el ledger completo es suyo |
| **025** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Transferencias y conteos con unidad |
| **026** | `PARTIALLY_UNLOCKED` | Costeo ya opera en `Decimal` sobre cantidad base |
| **027, 034** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Reimpresión desde snapshot disponible |
| **029, 031, 032, 035, 036** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Contratos declarados |
| **043** | `PARTIALLY_UNLOCKED` | `permit_instances.uom_id` disponible |

**Ninguna queda `FULLY_UNLOCKED`**: 011 satisface su dependencia de unidad, pero
cada una conserva las suyas propias.

## 38. Próxima Spec

**`046 — Gestión documental`**, según el roadmap vigente. Ningún hallazgo de esta
implementación cambia esa dependencia. **No se ha creado.**

## 39. Veredicto

**`SPEC 011 COMPLETE_100`**

0 BLOCKER · 0 CRITICAL · 0 contradicciones · 0 requisitos huérfanos · 0 tareas
abiertas · PostgreSQL 18.x · 4 migraciones PASS · 30 columnas convertidas sin
pérdida · 0 diferencias fiscales · backfill clasificado con aborto crítico
funcionando · snapshot histórico probado · autoridad única verificada ·
351/351 + 221/221 + 18/18 · convergencia PASS.
