# SPEC 030 — INFORME DE IMPLEMENTACIÓN

| Campo | Valor |
|---|---|
| Ciclo | `SPEC 030 — IMPLEMENTATION CYCLE AUTHORIZED` (2026-09-02) |
| Decisión aplicada | `RESERVATION TRIGGER = ORDER_CONFIRMATION` · `DRAFT → SUBMITTED` · FIJO (`ADR-D0-003` v2) |
| Base de partida | `83946f8` (D0-03 cerrada) |
| Migración | `0043_spec030_reservation` (revisa `0042_spec029_origin`) |
| Entorno de verificación | PostgreSQL 18.6 (cluster aislado, UTC) · ClamAV 1.4.3 · Node 24.13 · Chromium/Firefox/WebKit |

## 1. Baseline medida (mismo instrumento antes y después)

| Métrica | Antes | Después | Δ |
|---|---:|---:|---:|
| Modelos | 177 | 177 | 0 |
| Tablas | 177 | 177 | 0 |
| Claves foráneas (referencias de columna, ORM) | 371 | 373 | +2 |
| Migraciones | 42 | 43 | +1 |
| Rutas | 311 | 318 | +7 |
| Operaciones | 429 | 437 | +8 |
| Operaciones con contrato de empresa | 367 | 375 | +8 |

Las dos claves foráneas nuevas son `reservations.source_order_id → sales_orders` y
`reservations.source_line_id → sales_order_lines`: la identidad estructural que faltaba. Ninguna
tabla nueva: la Spec 030 no crea un modelo de reservas, **evoluciona el de 003** (§32).

Nota de instrumento: el checkpoint de la Spec 029 publicó 366 claves foráneas contando de otra
forma. Aquí se mide con `sum(len(t.foreign_keys))` sobre el metadata del ORM, antes y después, para
que el delta sea comparable consigo mismo.

## 2. Las siete rutas nuevas

| Ruta | Permiso | Qué hace |
|---|---|---|
| `POST /sales/orders/{id}/submit` | `ventas:submit` | Confirma: reserva todo-o-nada en base y, sin crédito, libera |
| `POST /sales/orders/{id}/release` | `ventas:approve` | `SUBMITTED → RELEASED` tras la decisión de 045 |
| `POST /sales/orders/{id}/reject` | `ventas:approve` | Con motivo: cierra la solicitud viva y libera |
| `POST /sales/orders/{id}/revert` | `ventas:submit` | Con motivo: libera todo y vuelve a borrador |
| `POST /sales/orders/{id}/cancel` | `ventas:submit` | Con motivo: libera todo y cancela |
| `POST /sales/orders/expire-reservations` | `ventas:approve` | Vence reservas de pedido con TTL cumplido y sus pedidos |
| `GET/PUT /sales/settings/reservation` | lectura / `ventas:approve` | Política: disparador fijo + `reservation_ttl_days` |

`POST /sales/orders/{id}/transition` se conserva y delega (compatibilidad, §28 del clarify).

## 3. Los catorce hechos de la auditoría D0-03, uno por uno

| # | Hecho auditado (D0-03) | Qué se hizo | Prueba que lo fija |
|---|---|---|---|
| CD-01 | Reserva tras aprobar el crédito, sin decisión | Disparador movido a `DRAFT → SUBMITTED`; `_reserve_order` eliminado | `test_spec030_architecture::test_solo_la_confirmacion_reserva` |
| CD-02 | `_reserve_order` retornaba en silencio sin almacén | `422 WAREHOUSE_REQUIRED` al confirmar con líneas de inventario | `test_confirmar_con_inventario_exige_almacen` |
| CD-03 | `reserve` leía y escribía sin bloqueo | `lock_balance` (`SELECT … FOR UPDATE`) antes de leer; orden determinista por producto | `test_spec030_concurrency` (2 casos) |
| CD-04 | Sin unicidad en `inventory_balances` | Índice único con `COALESCE` sobre la clave completa | hostil `test_10` (23505) |
| CD-05 | Cancelar no liberaba | `cancelar_pedido` libera atómicamente, con motivo | `test_cancelar_libera_y_el_segundo_intento_choca…` |
| CD-06 | El despacho marcaba `RELEASED` | Marca `FULFILLED` con motivo `DISPATCHED` | `test_liberar_a_preparacion_…_y_despachar_consume` |
| CD-07 | Reservaba la cantidad tecleada; campos Spec 011 vacíos | Reserva en `base_quantity` con factor snapshot; la línea captura la unidad al nacer | `test_la_reserva_se_hace_en_cantidad_base_…` |
| CD-08 | `source_document` texto libre, sin línea, sin unicidad | `source_type`/`source_order_id`/`source_line_id` con FK + índice único parcial por línea activa | `test_confirmar_dos_veces_no_duplica_la_reserva`, hostil `test_5` |
| CD-09 | `expires_at` nunca informado, sin planificador | TTL opcional por empresa (defecto nulo); expirar cierra reserva **y** pedido; sin worker | `test_ttl_opcional_…`, `test_no_hay_planificador_local` |
| CD-10 | `add_order_line` sin control de estado | `409 ORDER_NOT_EDITABLE` fuera de `DRAFT` | `test_un_pedido_emitido_no_admite_lineas` |
| CD-11 | Liberación manual sin motivo, también sobre reservas de pedido | Motivo obligatorio; `409 RESERVATION_ORDER_BOUND` para las de pedido | `test_la_reserva_de_un_pedido_no_se_libera_a_mano` |
| CD-12 | `ventas:approve` para toda transición | `ventas:submit` nuevo para emitir/revertir/cancelar | `test_el_permiso_de_emitir_existe_y_es_distinto_del_de_aprobar` |
| CD-13 | Sin auditoría de reserva en 003 | Cuatro eventos con el contrato completo de D0-03 §7 | `test_la_auditoria_de_la_reserva_dice_quien_que_cuanto_y_por_que` |
| CD-14 | `APPROVED` no observable | Deja de existir como estado; el pedido a crédito espera en `SUBMITTED` | `test_la_maquina_de_estados_es_la_de_d0_03` |

Los catorce estaban en el código antes de este ciclo y ninguno se cerró por eliminación silenciosa:
cada uno tiene una prueba que falla si vuelve.

## 4. Lo que se decidió al implementar (y no estaba en D0-03)

Tres precisiones que la decisión no fijaba y que el código exigía. Ninguna reabre D0-03.

**`CREDIT_PENDING` desaparece.** D0-03 dejó la máquina como `SUBMITTED → CREDIT_PENDING →
APPROVED → RELEASED`. Al implementar se vio que `CREDIT_PENDING` no aporta información: el pedido
con solicitud viva ya es distinguible por el estado de 045, y un estado que solo repite lo que otro
sistema sabe se desincroniza. El pedido a crédito **espera en `SUBMITTED`** y la aprobación se
materializa con `POST /release`. `APPROVED` corre la misma suerte y por el mismo motivo por el que
D0-03 lo llamó «fantasma».

**Quién mueve el pedido tras la decisión de 045.** El motor de aprobaciones no llama a los dominios
(es la inversión que impide una quinta implementación ad-hoc, P22). Compras ya resolvía esto con
`ensure_approved` en la transición del documento; ventas replica el patrón. Liberar es una acción
del dominio con el motor como compuerta.

**`Reservation.quantity` sigue siendo la cantidad tecleada.** La alternativa era redefinirla como
base. Se descartó: las reservas manuales no tienen presentación y las legadas no podrían
distinguirse. La reserva ahora guarda ambas, igual que un movimiento de inventario.

## 5. Defectos propios encontrados en la revisión del cambio

La revisión del propio diff, antes de dar por buena la regresión, encontró cuatro cosas. Se
corrigieron y se relanzó la regresión entera sobre el código corregido: la evidencia publicada
corresponde al código que se entrega, no a una versión anterior.

| # | Hallazgo | Por qué importaba | Corrección |
|---|---|---|---|
| 1 | La lectura con bloqueo (`SELECT … FOR UPDATE`) no refrescaba los atributos del objeto si el saldo ya estaba en el mapa de identidad de la sesión | La transacción habría esperado el bloqueo y decidido igualmente sobre el disponible **anterior**: la espera no serviría de nada. No se manifestaba en las pruebas porque en ellas el saldo se siembra desde otra sesión | `execution_options(populate_existing=True)` en la consulta bloqueante, con el porqué escrito al lado |
| 2 | El listado de pedidos pasó de `1+N` a `1+2N` consultas: `order_dict` pedía las reservas de cada pedido | Yo mismo introduje la amplificación al añadir reservas al detalle. Una página de cien pedidos son doscientas consultas | `orders_dict` trae líneas y reservas por lotes (dos consultas); `order_dict` acepta lo ya cargado. El listado baja a **tres** consultas, mejor que antes del cambio |
| 3 | El guardia `test_el_despacho_consume_y_no_libera` tenía una aserción tautológica (`"fulfill_reservation" in funciones_que_llaman(..., "fulfill_reservation")`) unida por `or` | Pasaba por la otra rama: media prueba no comprobaba nada. «Registrado ≠ probado» | Aserción única y directa sobre `confirm_shipment`, con mensaje de fallo |
| 4 | El camino nuevo por lotes del listado no lo recorría ninguna prueba | Habría sido código de producción sin cobertura, introducido para arreglar el punto 2 | Dos pruebas: equivalencia entre listado y detalle (con pedido confirmado y borrador) y acotación por empresa del listado |

## 6. Regresión

| Compuerta | Resultado |
|---|---|
| Backend completo (PostgreSQL 18.6 + ClamAV 1.4.3) | **831 pruebas · 823 pasadas · 8 saltadas (S3) · 0 fallos · 0 errores**; 56 de ellas nuevas de esta Spec |
| Frontend `vitest` | **283/283** (12 archivos) |
| `tsc -b` · ESLint · build | PASS · PASS · PASS |
| Playwright Spec 030 (3 navegadores) | **12/12** |
| Playwright route-crawl · axe WCAG 2.2 AA | **1/1** · **22/22** |
| Crawler responsive (36 rutas × 6 viewports) | 194/216; los 22 casos son los mismos de la auditoría del 2026-08-12 |
| Instalación limpia PostgreSQL vacío | `upgrade head` → `downgrade 0042` → `upgrade head` sin errores |
| Ruff (app, tests, alembic) | PASS |
| mypy (sales, inventory) | 27 errores preexistentes en 6 archivos; **0 introducidos** por esta Spec (los 3 que aparecieron se corrigieron: `to_base` con `Decimal`, `str(base_unit.id)`, motivo no nulo) |

## 7. Nota de ejecución

La primera ejecución de la regresión completa se perdió a mitad por un reinicio de la máquina que
borró el directorio de trabajo temporal (PostgreSQL y ClamAV viven ahí). Ambos se reaprovisionaron y
la regresión se relanzó entera. Los resultados publicados son los de la ejecución completa posterior al reinicio **y posterior a
las cuatro correcciones de §5**; nada se da por bueno de las ejecuciones interrumpidas ni de las
anteriores a esas correcciones.

## 8. Deuda

**Interna de la Spec 030: ninguna P0.** Anotado para otras Specs:

- `SalesOrderLine` no modela lote ni serial exigidos por el cliente. Cuando la Spec 024 lo añada, la
  reserva ya sabe transportarlos (`lot_id`/`serial_id` existen en el modelo y en `reserve`).
- No existe outbox transversal de eventos de dominio; la auditoría es la fuente. Si la Spec 047 lo
  introduce, los cuatro eventos de reserva son el punto de conexión.
- Los 22 casos de scroll horizontal a viewports ≤ 412 px ya figuraban en `active-blockers.md` como
  deuda responsive residual (P1, Specs 005 y 054). No los agrava esta Spec ni los resuelve.
