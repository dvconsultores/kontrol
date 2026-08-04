# WIREFRAMES — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/006-tesoreria/wireframes/README.md` |

> Aplicación de las guías DOC-08 (WF-02 formulario maestro-detalle; WF-05 estados y transiciones) al módulo de tesorería. Todos los grids sin scroll horizontal (FR-006-101).

## 1. Cajas / Arqueo (WF-05 — estados)

- **Lista de sesiones**: caja, usuario, apertura, conteo, diferencia, estado (OPEN/ARCHED/PRE_CLOSED/CLOSED/REJECTED).
- **Detalle de sesión**: pestaña movimientos + pestaña arqueo.
- **Acciones por estado**: abrir → movimiento → arqueo → pre-cierre → cierre (con diferencia aprobada) → cerrar/rechazar.
- Líneas: `movement_type | medio | monto | referencia | estado`.

## 2. Ingreso / Egreso (WF-02 — maestro-detalle)

- **Cabecera**: tipo (ingreso/egreso), caja/cuenta, moneda, tasa snapshot, fecha valor, referencia.
- **Detalle (varios medios)**: `medio | instrumento | monto | referencia` — una transacción admite varios medios (FR-006-021).
- **Varias transacciones por documento**: el documento de ingreso/egreso agrupa varias transacciones (FR-006-021).
- Botón ejecutar con confirmación (idempotente).

## 3. Conciliación (WF-05 — estados)

- **Lista**: cuenta, período, balance inicial/final, estado (DRAFT/IN_PROGRESS/REVIEW/APPROVED/REJECTED).
- **Detalle**: dos paneles — estado de cuenta (banco) vs movimientos del sistema; columna de match score.
- **Resolución manual**: acción por línea (matched/diferencia/comisión/dif. cambiaria) con nota → auditoría.
- Acciones: match por reglas → revisar → aprobar/rechazar.

## 4. Transferencias y Depósitos

- Formulario origen → destino (caja/cuenta), monto, moneda, fecha valor, referencia.
- Confirmación de ejecución.

## 5. IGTF (vista de eventos)

- Lista de eventos IGTF por regla: `evento | fuente | monto | tasa snapshot | IGTF | regla`.
- Detalle de regla versionada (vigencia, params) — lectura desde 006; motor en 007.
- Aviso visual: IGTF ≠ IVA adicional (nunca se suman).

## 6. Navegación

- Sidebar (lucide-react): `Tesorería` → Cajas/Arqueo · Ingresos/Egresos · Transferencias · Conciliación · IGTF · (Maestros financieros).
- Rutas: `/tesoreria/cajas`, `/tesoreria/ingresos-egresos`, `/tesoreria/transferencias`, `/tesoreria/conciliacion`, `/tesoreria/igft`, `/tesoreria/maestros`.
