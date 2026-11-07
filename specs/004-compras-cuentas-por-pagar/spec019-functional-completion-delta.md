# Spec 019 · delta RECEPCION-FUNCTIONAL-COMPLETION

Delta dirigido dentro de la Spec 004, capacidad 019. Autorizado por el encargo RECEPCION-FUNCTIONAL-COMPLETION-02 (2026-11-07). Evidencia: `evidence/recepcion-functional-completion/`.

## Requisitos

| ID | Requisito |
|---|---|
| FR-019-019 | Toda orden recibible de la empresa se puede alcanzar desde la pantalla, por búsqueda o cargando más, sin truncado silencioso |
| FR-019-020 | Los estados recibibles tienen una sola autoridad |
| FR-019-021 | Identificación, referencia, estado físico y cada comparación de la inspección se envían tal como se declaran; lo no declarado va nulo |
| FR-019-022 | Aceptar revalida todas las líneas antes de cualquier efecto; una fila contradictoria bloquea la aceptación y no se repara adivinando |
| FR-019-023 | Solo un almacén activo recibe, al crear y al aceptar. La pantalla solo lo ofrece |
| FR-019-024 | El veredicto de conformidad, aprobado o rechazado, se puede dar por pantalla, se guarda y queda auditado |

## API

Cambio intencional y mínimo, sin operaciones nuevas:

- `GET /purchasing/orders` admite `q` y `receivable`. Son opcionales; los consumidores actuales no cambian.
- `GET /purchasing/receipts` añade `order_code` a cada elemento.
- `allowed_actions.receive` pasa a verdadero en `RECEIVED`. No tenía consumidores.
- Dos 409 nuevos: `WAREHOUSE_NOT_ELIGIBLE`, `RECEIPT_LINE_INTEGRITY`.
- Evento nuevo de auditoría: `RECEIPT_QUALITY_RECORDED`.

## Diseño del selector

Búsqueda y paginación en el servidor. El universo de órdenes crece sin tope, así que recorrer todas las páginas no escala y un `page_size` mayor solo movería el corte. El código se busca por `q` y el resto se alcanza con «Cargar más órdenes»; un aviso dice cuántas se muestran.

## Constitution gate

Sin migración, sin esquema, sin dependencia. Multiempresa: el filtro por empresa se conserva y la clave de consulta incluye la empresa. Sin backfill: una fila contradictoria queda bloqueada. BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · MATERIAL OQ 0.

## Trazabilidad

| Requisito | Prueba |
|---|---|
| FR-019-019 | O-01 a O-10, `test_o01` a `test_o04` |
| FR-019-020 | `test_estados_recibibles_son_una_sola_autoridad`, `test_orden_recibible_admite_recepcion`, `test_orden_no_recibible_se_rechaza` |
| FR-019-021 | I, R, OBS, INS |
| FR-019-022 | `test_h01_h08`, `test_h_linea_buena_antes_de_la_mala`, `test_h_linea_de_otra_orden`, `test_h09` |
| FR-019-023 | W-01 a W-06, `test_w_almacen_desactivado_no_acepta` |
| FR-019-024 | `test_conformidad_se_registra_y_audita`, `test_rechazada_cierra_la_recepcion`, Q |
