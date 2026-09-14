# SPEC — 006-TESORERIA

| Campo | Valor |
|---|---|
| Código | 006-tesoreria |
| Nombre | Tesorería: cajas, bancos, ingresos, egresos, transferencias, depósitos, conciliaciones, arqueos e IGTF |
| Versión | 1.0 (especificada — pendiente de `/speckit.analyze` y autorización expresa) |
| Estado | ESPECIFICADA |
| Fecha | 2026-08-04 |
| Responsable | Product Owner de KONTROL |
| Dependencia | **001-fundacion** + **002-maestros** (terceros, maestros financieros) + **004-compras-cuentas-por-pagar** (pagos) + **005-ventas-cuentas-por-cobrar** (cobros). La implementación de 006 requiere 001 certificada, 002/004/005 implementados, y autorización expresa |
| Fuente | DOC-01 §4; DOC-02 §3, §10, §12; DOC-03 §9; DOC-08 |
| Ruta | `specs/006-tesoreria/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa se implementa solo tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **006-tesoreria**.

---

## 1. Problema

Con los ciclos de compras (004) y ventas (005) implementados —que registran pagos OUT y cobros IN— falta la **tesorería** que los ejecuta y concilia: cajas (apertura, movimientos, arqueo, pre-cierre, cierre y diferencias), bancos y cuentas, ingresos/egresos, transferencias y depósitos, conciliaciones asistidas, comisiones, diferencias cambiarias e **IGTF** por regla y evento.

Sin este módulo no es posible: ejecutar los pagos/cobros contra caja o banco, controlar cajas con arqueos y cierres aprobados, conciliar estados de cuenta con movimientos del sistema (con reglas y resolución manual auditada), ni evaluar el IGTF — todo ello exigido por la Constitución (P5 datos históricos protegidos, P8 no hardcodear, P13 integridad transaccional).

## 2. Objetivos

1. **Cajas**: control por apertura → movimientos → arqueo → pre-cierre → cierre y diferencias (DOC-02 §10).
2. **Bancos y cuentas**: transacciones con moneda, fecha valor, referencia, comisiones y conciliación.
3. **Ingresos y egresos**: ejecutar cobros (de 005) y pagos (de 004) separados de la factura/obligación; varios medios por transacción y varias transacciones por documento.
4. **Transferencias y depósitos**: entre cajas/cuentas.
5. **Conciliación**: asistida con reglas (match score) y resolución manual auditada.
6. **IGTF**: evaluado por regla y evento (no confundir con IVA adicional); referido a reglas versionadas (motor fiscal en 007).
7. **Integración**: consumir los pagos de 004 y cobros de 005 (contratos v1); anticipos sin aplicación inicial y posterior imputación.
8. **Maestros financieros**: bancos, cuentas, cajas, métodos e instrumentos, monedas y tasas (DOC-02 §3) como prerequisito si no existen.

## 3. Fuera de alcance

- **Núcleo fiscal** (emisión, numeración, libros, cierres fiscales, cálculo IVA/ISLR/IGTF completo) — **Spec 007**. 006 estructura el IGTF por regla/evento y lo refiere a reglas versionadas.
- **Regulación y traslados** — Spec 008.
- **Reportes** — Spec 009.
- Los documentos de compra/venta (004/005) no se reimplementan: 006 los consume.

## 4. Actores

| Actor | Uso |
|---|---|
| Tesorería | Ejecuta ingresos/egresos, transferencias y depósitos |
| Cajero | Abre caja, registra movimientos, arquea y cierra |
| Contador | Conciliaciones y comisiones/diferencias cambiarias |
| Aprobador de pago | Aprueba egresos (segregación DOC-02 §12) |
| Auditor | Trazabilidad de caja/banco/conciliación |

## 5. Historias de usuario

| ID | Historia |
|---|---|
| US-006-001 | Como cajero, quiero abrir una caja y registrar movimientos con control por sesión. |
| US-006-002 | Como cajero, quiero realizar el arqueo y pre-cierre de la caja y aprobar las diferencias. |
| US-006-003 | Como tesorería, quiero registrar ingresos (cobros de 005) y egresos (pagos de 004) contra caja o banco. |
| US-006-004 | Como tesorería, quiero usar varios medios por transacción y varias transacciones por documento. |
| US-006-005 | Como tesorería, quiero ejecutar transferencias entre cajas/cuentas y depósitos. |
| US-006-006 | Como contador, quiero conciliar el estado de cuenta con los movimientos del sistema (asistida por reglas). |
| US-006-007 | Como contador, quiero resolver manualmente diferencias de conciliación con auditoría. |
| US-006-008 | Como contador, quiero que el IGTF se evalúe por regla y evento (sin confundirlo con IVA adicional). |
| US-006-009 | Como contador, quiero registrar comisiones y diferencias cambiarias sin alterar el IVA original. |
| US-006-010 | Como tesorería, quiero registrar anticipos sin aplicación inicial y luego imputarlos. |
| US-006-011 | Como auditor, quiero la trazabilidad completa de caja, banco y conciliación. |

## 6. Requisitos funcionales

Convención: `FR-006-XXX`. Cada requisito tiene fuente (DOC), prioridad (P0/P1/P2), actor, precondición, flujo, excepciones, resultado, auditoría y prueba.

### 6.1 Cajas (sesiones y arqueo)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-006-001 | `CashSession`: caja, usuario, apertura, movimientos, conteo, diferencia y estado. | DOC-03 §9 | P0 | Cajero |
| FR-006-002 | Control de cajas: apertura → movimientos → arqueo → pre-cierre → cierre y diferencias. | DOC-02 §10 | P0 | Cajero |
| FR-006-003 | Una caja **no se cierra con diferencia** sin aprobación/justificación. | DOC-02 §10 | P0 | Sistema |
| FR-006-004 | Arqueo con conteo por método/instrumento y diferencia explícita. | DOC-02 §10 | P1 | Cajero |

### 6.2 Bancos y cuentas

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-006-010 | `BankTransaction`: cuenta, fecha, fecha valor, monto, referencia, fuente y estado. | DOC-03 §9 | P0 | Tesorería |
| FR-006-011 | Cuentas bancarias con moneda, comisiones y conciliación. | DOC-02 §10 | P0 | Tesorería |
| FR-006-012 | Maestros financieros: bancos, cuentas, cajas, métodos e instrumentos, monedas y tasas (prerequisito si no existen). | DOC-02 §3 | P0 | Administrador |

### 6.3 Ingresos y egresos

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-006-020 | Ingresos (cobros de 005, depósitos) y egresos (pagos de 004) **separados de la factura y de la obligación**. | DOC-02 §10 | P0 | Tesorería |
| FR-006-021 | Varios **medios por transacción** y varias **transacciones por documento**. | DOC-02 §10 | P0 | Tesorería |
| FR-006-022 | Ejecución del pago/cobro en caja o banco con instrumentos e **idempotencia**. | DOC-02 §10 | P0 | Tesorería |
| FR-006-023 | Transferencias entre cajas/cuentas y depósitos. | DOC-02 §4 | P1 | Tesorería |

### 6.4 Conciliación

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-006-030 | Conciliación **asistida con reglas** (match score) y resolución manual **auditada**. | DOC-02 §10 | P0 | Contador |
| FR-006-031 | `Reconciliation`: estado de cuenta, transacción, movimiento del sistema, puntuación, estado y resolución. | DOC-03 §9 | P0 | Contador |
| FR-006-032 | Comisiones y diferencias cambiarias al conciliar; **no alteran el IVA original**. | DOC-02 §9/§10 | P1 | Contador |
| FR-006-033 | Cierre y reapertura de períodos con aprobación. | DOC-02 §3 | P1 | Contador |

### 6.5 IGTF

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-006-040 | IGTF evaluado **por regla y evento**; no confundir con IVA adicional. | DOC-02 §10 | P0 | Sistema |
| FR-006-041 | IGTF referido a **reglas versionadas** (motor fiscal en 007); no hardcodear tasas (P8). | DOC-01 §8 | P0 | Sistema |

### 6.6 Integración (004/005) y transversales

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-006-050 | 006 consume los **pagos de 004** y **cobros de 005** para ejecución y conciliación (contratos v1). | DOC-01 §1 | P0 | Sistema |
| FR-006-051 | Anticipos sin aplicación inicial y posterior imputación (reutiliza 004/005). | DOC-02 §10 | P1 | Tesorería |
| FR-006-052 | Monedas y tasas **históricas**; snapshot por transacción. | DOC-01 §3 | P0 | Sistema |
| FR-006-100 | Aislamiento multiempresa; idempotencia en POST críticos; decimal exacto. | DOC-03 §12 | P0 | Sistema |
| FR-006-101 | Frontend: pantallas completas (arqueo WF-05, conciliación WF-05, ingreso/egreso WF-02), sin scroll horizontal. | DOC-08 | P0 | Sistema |

### 6.7 Delta dirigido FLOAT-038-A — importe exacto del movimiento bancario (Spec 038 · 2026-09-14)

Autoridad: `OQ-FLOAT-038-A-01` y `-02`, cerradas por el owner (`clarifications.md` §5).
Detalle del ciclo: `spec038-bank-amount-decimal-delta.md`.

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-038-FLOAT-A-001 | `amount` y `commission` de `POST /treasury/bank-transactions` se reciben **solo como texto decimal**; un número JSON se rechaza con 422. | OQ-01 | P0 | Sistema |
| FR-038-FLOAT-A-002 | Forma léxica estricta: dígitos ASCII y parte fraccionaria opcional; sin notación científica, `NaN`, `Infinity`, espacios ni separadores. `amount` sin signo; `commission` admite `-`. | OQ-01 | P0 | Sistema |
| FR-038-FLOAT-A-003 | Escala ≤ la de la columna (2) y dígitos enteros ≤ precisión − escala (16); si no, 422. Sin redondeo de PostgreSQL ni cuantización. | OQ-02 | P0 | Sistema |
| FR-038-FLOAT-A-004 | Se conserva `amount > 0`. | contrato previo | P0 | Sistema |
| FR-038-FLOAT-A-005 | `Decimal` de la frontera a PostgreSQL: servicio y ORM sin `float`. | `KQA-100` | P0 | Sistema |
| FR-038-FLOAT-A-006 | `POST` y `GET /treasury/bank-transactions` devuelven `amount` y `commission` como texto con escala 2, con modelo de respuesta declarado en OpenAPI. | OQ-01 | P0 | Sistema |
| FR-038-FLOAT-A-007 | Una petición rechazada no deja fila ni cambia saldos. | OQ-02 | P0 | Sistema |
| FR-038-FLOAT-A-008 | El frontend envía y muestra el importe como texto, sin `Number`, `parseFloat` ni `+`. | OQ-01 | P0 | Sistema |
| FR-038-FLOAT-A-009 | El cambio incompatible se declara en contratos, OpenAPI, pruebas y convergencia. | OQ-01 | P0 | Sistema |

## 7. Reglas no negociables aplicables (Constitución / DOC-01 §5)

- No existe eliminación física de pagos aprobados, cobros aplicados ni cierres; corrección por reverso vinculado (P5).
- Los saldos de caja/banco se calculan desde movimientos y cierres; no se editan.
- Una caja no se cierra con diferencia sin aprobación/justificación.
- El IGTF se evalúa por regla y evento; no se confunde con IVA adicional.
- Las comisiones y diferencias cambiarias no alteran el IVA original.
- Reglas de IGTF y conciliación **versionadas**; prohibido hardcodear (P8).
- 006 consume los pagos/cobros de 004/005; no duplica su lógica.

## 8. Criterios de éxito (resumen)

- Una caja recorre apertura → movimientos → arqueo → pre-cierre → cierre con diferencias aprobadas.
- Los pagos de 004 y cobros de 005 se ejecutan y concilian contra caja/banco.
- La conciliación asistida resuelve diferencias con reglas y resolución manual auditada.
- El IGTF se evalúa por regla y evento, sin confundirlo con IVA.
- Comisiones y diferencias cambiarias no alteran el IVA original.
- Los maestros financieros (bancos, cuentas, cajas, monedas, tasas, métodos e instrumentos) están disponibles.
- La trazabilidad de caja/banco/conciliación es completa.
