# CONVERGENCIA — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-005-01 | Política de crédito y límites por empresa | Decisión (CL-005-09) | Crédito | Pendiente |
| CVG-005-02 | Días de vencimiento por condición de pago | Decisión (CL-005-10) | CxC | Pendiente |
| CVG-005-03 | Emisión fiscal formal de factura de venta (numeración, libros) | Spec 007 | Fiscal | Pendiente (007) |
| CVG-005-04 | Regulación del despacho (SICA/SIGESAI/SACS) | Spec 008 | Logística | Pendiente (008) |
| CVG-005-05 | Conciliación bancaria de cobros | Spec 006 (tesorería) | Tesorería | Pendiente (006) |

## 3. Implementado (005)

| Elemento | Estado |
|---|---|
| Modelos (14 tablas) + migración `0005_ventas` | ✔ |
| Cotización (sin reserva) y pedidos | ✔ |
| Órdenes de venta (crédito + máquina de estados + aprobación por regla) | ✔ |
| Reserva al aprobar → **motor de 003** | ✔ |
| Picking y despacho (validación documental + salida → **003** + liberación de reservas) | ✔ |
| Factura de venta (snapshot fiscal + estados + inmutabilidad/anulación) | ✔ |
| Notas de crédito/débito y devoluciones | ✔ |
| CxC: open items RECEIVABLE, cobros (Payment IN), aplicaciones atómicas, anticipos, retenciones sufridas, aging — **reutiliza 004** | ✔ |
| API `/sales/*` (27 endpoints) | ✔ |
| Frontend: cotizaciones, órdenes, facturas, CxC | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 85/85 (incluye 11 de ventas) |
| Backend ruff | ✔ limpio (incluye migración) |
| Backend mypy | ✔ 66 archivos, 0 issues |
| Alembic | ✔ head `0005_ventas` (upgrade/downgrade) |
| OpenAPI | ✔ 27 endpoints `/sales/*` (123 rutas totales) |
| Frontend tsc / eslint | ✔ limpios |
| Frontend vitest / build | ✔ 16/16 · build OK |

## 5. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 002/003/004 implementados + autorización expresa) |
| Certificación (Docker/CI/legal, integración 006/007/008) | Pendiente — depende de 001 certificada y de Specs 006/007/008 |

---

# CONVERGENCIA — SPEC 029

## Puerta

| Invariante | Resultado |
|---|---:|
| Origen del precio persistido | 9 columnas × 2 líneas |
| Origen del descuento persistido | sí |
| Evidencia perdida en la conversión | 0 |
| Reprecio silencioso | 0 |
| Recálculo histórico | 0 |
| Segundo resolutor de precio | 0 |
| Reserva dentro de 029 | 0 |
| Decisión sobre `D0-03` | **ninguna** |
| Picking, factura o CxC como efecto | 0 |
| Conversiones duplicadas | 0 |
| Coma flotante monetaria | 0 |
| `company_id` redundante en líneas | 0 |
| Fuga entre empresas / tenants | 0 / 0 |
| Desviación ORM ↔ Alembic ↔ PostgreSQL | 0 |
| Desviación con OpenAPI | 0 |
| Trazabilidad | 100% |
| Deuda interna de la Spec 029 | 0 |

## Lo que cambió de verdad

Antes: `unit_price` era un número que alguien tecleó, y `resolve_price` existía
sin que nadie la llamara.

Ahora: el precio se resuelve, la línea guarda de qué versión salió, ese origen
sobrevive a que la versión se supere o se archive, y viaja intacto al pedido.
Escribir un precio a mano sigue siendo posible y ahora exige un motivo y
conserva al lado lo que decía la lista.

## Veredicto

`SPEC 029 — COMPLETE / CONVERGED`

---

# CONVERGENCIA — SPEC 030 · CRÉDITO / APROBACIÓN / RESERVA

## Puerta

| Criterio | Exigido | Resultado |
|---|---|---|
| Constitution Gate | PASS | PASS (13 validaciones, `spec030-implementation-cycle.md`) |
| BLOCKER · CRITICAL · CONTRADICTIONS | 0 · 0 · 0 | 0 · 0 · 0 |
| Requisitos huérfanos · Tareas huérfanas | 0 · 0 | 0 · 0 |
| OQ material | 0 | 0 |
| Trazabilidad | 100 % | 100 % (FR-030-001..063 · IMP-030-001..063) |
| Decisión D0-03 | no reabierta | no reabierta: disparador fijo `ORDER_CONFIRMATION` |
| Segundo motor de inventario o de aprobaciones | ninguno | ninguno |
| Planificador local | ninguno | ninguno |
| Backend | 0 fallos | **831 pruebas: 823 pasadas, 8 saltadas, 0 fallos, 0 errores** (PostgreSQL 18.6 + ClamAV 1.4.3) |
| Frontend | verde | 283/283 · `tsc` · ESLint · build |
| E2E | verde | 12/12 (3 navegadores) · axe 22/22 · route-crawl 1/1 |
| Instalación limpia | verde | `upgrade head → downgrade 0042 → upgrade head` |
| Deuda interna P0 | 0 | 0 |

## Lo que cambió de verdad

Antes: el pedido reservaba al aprobar el crédito, en un punto que nadie decidió. Entre emitir y
aprobar, el stock quedaba libre y dos vendedores podían prometer la misma unidad. La comprobación de
disponible se hacía sin bloqueo, así que ni siquiera dentro de esa ventana estaba garantizada.
Cancelar no devolvía nada. Un pedido sin almacén pasaba a `RESERVED` sin reservar. Se reservaba la
cantidad tecleada, de modo que dos cajas de doce comprometían dos unidades. La reserva no sabía de
qué línea venía, el despacho la marcaba como liberada en vez de consumida, y nada de esto dejaba
rastro en la auditoría.

Ahora: la reserva nace al confirmar el pedido, que es donde el negocio pidió que naciera. Es todo o
nada, en unidad base, con el saldo bloqueado en PostgreSQL mientras se decide. El crédito ocurre
después y sobre stock ya comprometido; si lo rechazan, se devuelve en la misma transacción.
Modificar un pedido emitido es revertirlo a borrador, que libera entero y deja obsoleta la
aprobación: no hay ajustes por diferencia que puedan cuadrar mal. Cancelar libera. Expirar, si la
empresa lo configura, libera y cierra el pedido, porque un pedido vivo sin reserva sería mentira.
Despachar consume. Cada uno de esos movimientos deja quién, qué pedido, qué línea, cuánto en
tecleado y en base, con qué disparador y por qué motivo.

Y hay catorce pruebas cuyo único trabajo es fallar si algo de esto se deshace.

## Los catorce hechos de la auditoría D0-03

Cerrados uno por uno, cada uno con la prueba que impide su regreso: ver
`spec030-implementation-report.md` §3. Ninguno se cerró borrando código: el disparador se movió, no
se suprimió; las reservas legadas se conservan con el disparador con el que nacieron.

## Lo que se decidió al implementar

`CREDIT_PENDING` y `APPROVED` dejan de ser estados del pedido —el pedido a crédito espera en
`SUBMITTED` y la aprobación se materializa liberando— y `Reservation.quantity` sigue siendo la
cantidad tecleada, con `base_quantity` al lado. Las tres decisiones están razonadas en
`spec030-implementation-report.md` §4 y ninguna reabre D0-03.

## Revisión del propio cambio

Cuatro defectos propios encontrados y corregidos antes de dar la regresión por buena: una lectura
con bloqueo que podía decidir sobre datos rancios, una amplificación de consultas que yo mismo
introduje en el listado, una aserción tautológica en un guardia estructural y un camino de código
nuevo sin cobertura. Detalle en `spec030-implementation-report.md` §5. La regresión publicada es
posterior a las cuatro correcciones.

## Un hallazgo del entorno, ajeno a esta Spec

La primera ejecución de la regresión completa terminó con un fallo:
`test_mc_preflight.py::test_la_base_rechaza_una_escritura_aunque_el_codigo_falle`. No era de la
Spec 030 ni de código productivo: faltaba la base `kontrol_legacy`, que el reinicio de la máquina se
llevó junto con el resto del directorio temporal.

Lo que merece quedar escrito no es la ausencia —se sembró de nuevo con
`qa/n4-legacy-hostile-seed.py`, que existe precisamente porque ya se perdió una vez— sino **por qué
la ausencia produjo un fallo en vez de un salto**: el guardia de esa prueba decide saltar buscando
`"does not exist"` en el mensaje del error, y este PostgreSQL responde en español («no existe la
base de datos»). Sus quince pruebas hermanas saltan bien porque comprueban la conexión de otra
forma. Cuatro líneas más arriba, la propia prueba advierte de esto para su aserción: «se comprueba
el tipo de error de psycopg2, no su mensaje: el mensaje viene traducido y depende de la
configuración regional». La lección estaba aprendida para la aserción y no para el guardia.

Con la base sembrada, esas dieciséis pruebas se ejecutan de verdad (32/32 en el fichero, cero
saltos) y la regresión publicada aquí es la de un entorno íntegro. **No se ha tocado esa prueba**:
pertenece al preflight multiempresa (N4/N8), no a esta Spec. Queda anotada para su propietario,
porque en cualquier entorno con PostgreSQL en otro idioma y sin base legado volverá a fallar por el
motivo equivocado.

## Deuda

**Interna: ninguna P0.** Anotado para otras Specs: la línea de pedido aún no modela lote ni serial
exigidos (Spec 024); no existe outbox transversal y la auditoría hace de fuente (Spec 047); los 22
casos de scroll horizontal en viewports estrechos siguen siendo la deuda responsive ya registrada.

## Veredicto

`SPEC 030 — COMPLETE / CONVERGED`
