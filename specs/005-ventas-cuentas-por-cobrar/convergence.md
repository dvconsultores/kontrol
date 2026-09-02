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
