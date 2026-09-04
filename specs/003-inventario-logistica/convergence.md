# CONVERGENCIA — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Ruta | `specs/003-inventario-logistica/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-003-01 | Política de costeo por defecto por empresa | Decisión de negocio (CL-003-11) | Costos | Pendiente |
| CVG-003-02 | Política de vencidos (bloqueo anticipado, destino) | Decisión (CL-003-12) | Almacén | Pendiente |
| CVG-003-03 | Política de ubicaciones/picking | Decisión (CL-003-14) | Logística | Pendiente |
| CVG-003-04 | Reservas: expiración por job/programado | Automatizar `expire_reservations` | Backend | Pendiente (job) |
| CVG-003-05 | Picking y despacho completos (PickList/shipment) | Dependen de Spec 005 (ventas) | Arquitecto | Pendiente (005) |
| CVG-003-06 | Recepción de compra completa | Depende de Spec 004 (compras) | Arquitecto | Pendiente (004) |

## 3. Implementado (003)

| Elemento | Estado |
|---|---|
| Modelos (15 tablas nuevas) + migración `0003_inventario` | ✔ |
| Maestros de custodia reutilizados de 001 (`organization`: warehouses/locations) | ✔ (CL-003-02) |
| Motor de movimientos balanceados e inmutables + reverso vinculado | ✔ |
| Tipos de movimiento versionados + seeds idempotentes | ✔ |
| Lotes, seriales/IMEI (unicidad), FEFO y transiciones de estado | ✔ |
| Reservas (reserva/liberación/expiración; disponible = físico − reservas) | ✔ |
| Balance reconstruible (`recompute`) + existencias + kardex | ✔ |
| Transferencias con máquina de estados y diferencias | ✔ |
| Conteos y ajustes con segregación (crea/revisa/aprueba) | ✔ |
| Costos por capas (promedio/FIFO versionado) + valoración | ✔ |
| API `/inventory/*` (25 endpoints) + integración v1 (`receive`/`ship`) | ✔ |
| Frontend: existencias, kardex, transferencias, conteos, ajustes | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 57/57 (incluye 20 de inventario) |
| Backend ruff | ✔ limpio (incluye migración) |
| Backend mypy | ✔ 54 archivos, 0 issues |
| Alembic | ✔ head `0003_inventario` (upgrade/downgrade) |
| OpenAPI | ✔ 25 endpoints `/inventory/*` (64 rutas totales) |
| Frontend tsc | ✔ limpio |
| Frontend eslint | ✔ limpio |
| Frontend vitest | ✔ 16/16 |
| Frontend build | ✔ build de producción OK |

## 5. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 002 implementado + autorización expresa) |
| Certificación (Docker/CI/legal, integración 004/005) | Pendiente — depende de 001 certificada y de Specs 004/005 |

---

# CONVERGENCIA — CAPACIDAD DE SALDO MULTIESTADO (2026-09-04)

`SPEC023 MULTI-STATE INVENTORY BALANCE WRITE CAPABILITY — COMPLETE / CONVERGED`

La Spec 023 **sigue** `PARTIALLY_IMPLEMENTED`: converge la capacidad, no la Spec. Le quedan
requisitos que nunca fueron de este ciclo —ubicación efectiva en la práctica, FEFO, valoración—.

## Compuerta

| Criterio | Resultado |
|---|---|
| Backend | **961 · 953 pasadas · 8 saltadas declaradas · 0 fallos** |
| — nuevas de esta capacidad | **41** (20 funcionales · 14 estructurales · 7 de migración y concurrencia) |
| Frontend | 285/285 · `tsc` · ESLint · build. Sin cambios: la capacidad es de servicio |
| Instalación limpia | subir a `head`, bajar la `0046`, volver a subir |
| Paridad ORM / Alembic / PostgreSQL | verificada con el insert real del ORM contra la tabla de Alembic |
| OpenAPI | sin deriva: no se añadió endpoint |
| Deuda P0 propia | **0** |

## Lo que cambió de verdad

1. **Existe una autoridad de estados.** Antes el catálogo vivía en un ADR y el motor escribía
   `DISPONIBLE` fijo. `R-D0-10-7` pasa de regla inaplicable a comportamiento: lo no declarado se
   rechaza antes de tocar existencias.
2. **El ledger conserva la procedencia.** Sin ella el saldo multiestado no era reconstruible y
   `R-D0-10-5` era papel mojado.
3. **Dos defectos vivos cerrados.** La recepción de transferencia ya materializa la cuarentena que
   decidía y el motor ignoraba. Y la reconstrucción dejó de acumular la cantidad tecleada: era la
   caja ×12 de la Spec 019, viva en `recompute_balances` y sin ninguna prueba que la mirase.

## Un tercer defecto, encontrado por la propia migración

La primera versión de la `0046` clasificaba `quantity > 0` como entrada y `< 0` como salida, y
**abortaba** ante un movimiento en cero antes que rellenarlo a ciegas. Hizo bien en abortar: eso es
lo que la reveló. El histórico tiene ceros —conversiones de tipo, correcciones— y todos tocaron la
fila `DISPONIBLE` como destino. Se clasifican como entrada, con su prueba.

## Handoff a la Spec 021

Las cuatro transiciones que necesita están declaradas y son ejecutables por el motor:
`RECIBIDO → DISPONIBLE`, `RECIBIDO → RECHAZADO`, `CUARENTENA → DISPONIBLE`, `CUARENTENA → RECHAZADO`.
Ninguna sale de `DISPONIBLE`, así que ninguna puede toparse con una reserva viva y `R-D0-10-10` no
la afecta.

**`SPEC 021 — READY_FOR_IMPLEMENTATION`.** No se implementó nada suyo: ni confirmación, ni
conciliación, ni liberación de lote, ni endpoint. Un guardia estructural lo comprueba por nombre.

---

# CONVERGENCIA — SPEC 022 · PUT-AWAY Y UBICACIÓN (2026-09-04)

## Lo que cierra

La cadena de entrada, entera. La mercancía se recibe (019), su excepción se registra y se trata
(020), se cuenta y se confirma (021), y ahora **se coloca**. La duodécima etapa del proceso de
recepción y las once de clasificación y ubicación quedan cubiertas.

## Lo que había que resolver sin romper nada

El bloqueo de esta Spec no era construir el put-away: era que ubicar la mercancía la habría vuelto
invendible. `lock_balance` filtraba `location_id IS NULL` en duro y `get_available` leía esa única
fila, de modo que en cuanto el stock se moviera a una ubicación real la Spec 030 dejaría de verlo.

`D0-14` cerró la semántica —la reserva es de almacén, no de ubicación— y dejó la representación
como elección de ingeniería. Se eligió mantener el contador en la fila ancla porque
`recompute_balances` **ya** proyectaba ahí las reservas: cualquier otra opción habría introducido
divergencia entre lo que el motor escribe y lo que la reconstrucción produce, y ninguna migración de
datos era necesaria.

## Las tres decisiones de `D0-14`, ejecutadas exactamente

| Decisión | Cómo se ejecutó |
|---|---|
| Reserva de almacén (`R-D0-14-1..5`) | `warehouse_sellable_on_hand` suma lo vendible de todas las ubicaciones; el ancla conserva el compromiso; el put-away nunca escribe `qty_reserved` |
| Capacidad informativa (`R-D0-14-6/7`) | Se expone con `"enforced": false`; no filtra candidatas ni rechaza colocaciones; ningún cálculo de ocupación |
| Ubicación manual (`R-D0-14-8/9/10`) | Candidatas filtradas por el backend y revalidadas en el envío; sin puntuación, sin recomendación, sin heurística |

## Compuerta

| Criterio | Resultado |
|---|---|
| Backend | **1036 · 1028 pasadas · 8 saltadas declaradas · 0 fallos** |
| — nuevas de esta Spec | **34** (13 funcionales · 14 estructurales · 7 de migración y concurrencia) |
| Frontend | **289/289** · `tsc` · ESLint · build |
| Rutas | 452 → **455** |
| Instalación limpia | subir a `head`, bajar la `0048`, volver a subir |
| Migración de datos | **ninguna**: la representación elegida no movió un solo dato |
| Deuda P0 propia | **0** |

## Handoff a la Spec 031

La existencia queda con empresa, almacén, producto, cantidad base, estado de mercancía, lote, serial
y **ubicación física real**. Es lo que la cola y la ruta de picking pedían.

Y queda igual de importante lo que **no** queda hecho: ninguna reserva está asignada a ninguna
ubicación. El compromiso sigue siendo del almacén, y decidir de qué ubicación se extrae para
satisfacerlo es de la 031. Un guardia estructural lo comprueba.

`SPEC 031 — READY_FOR_IMPLEMENTATION` tras esta convergencia.
