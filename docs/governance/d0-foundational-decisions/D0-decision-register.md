# REGISTRO DE DECISIONES D0

| ID | Decisión | Estado | Clasificación de cierre | Responsable | Impacto | Specs bloqueadas |
|---|---|---|---|---|---|---|
| **D0-01** | PostgreSQL con paridad de producción | APPROVED | **CLOSED** | Arq. datos · DBA · DevOps · QA | Transversal (56) | Ninguna para empezar; **todas para cerrar** |
| **D0-02** | Motor transversal de aprobaciones | APPROVED | **CLOSED_WITH_CONFIGURATION_PENDING** | Arq. empresarial · Auditor · PO | 045 + 12 Specs | 045, 015, 017, 025, 030, 033 |
| **D0-03** | Momento de reserva de inventario | APPROVED · ACTIVE (v2 2026-09-02) | **CLOSED** — `RESERVATION TRIGGER = ORDER_CONFIRMATION` | Arq. procesos · Ventas · Inventario | 030 + 9 Specs | 030, 029, 031, 032 |
| **D0-04** | Modelo físico genérico de almacén | APPROVED | **CLOSED** | Arq. datos · Almacén · PO | 008 + 9 Specs | 008, 022, 031, 032 |
| **D0-05** | Reglas comerciales | APPROVED | **CLOSED_WITH_CONFIGURATION_PENDING** | Arq. datos · Ventas · Crédito | 012 + 6 Specs | 012, 029, 034 |
| **D0-06** | Autoridad central de licenciamiento | APPROVED (arquitectura) | **BUSINESS_DECISION_PENDING** | Arq. seguridad · Infra · PO | 004, 048, 052, 053 | Ninguna de código; sí el cierre de 004 |
| **D0-07** | Gobierno fiscal | APPROVED (gobierno) | **LEGAL_VALIDATION_PENDING** | Abogado tributario · Contador | 039-043, 014, 056 | Cierre de 039, 040, 041, 042, 043, 056 |
| **D0-08** | Gestión documental transversal | APPROVED | **CLOSED** | Arq. backend · Seguridad | 046 + 9 Specs | 046, 018, 020, 035 |
| **D0-09** | Unidad, presentación y conversión | APPROVED | **CLOSED** | Arq. datos · Compras · Ventas | 011 + 15 Specs | 011, 019, 021, 029, 032 |
| **D0-10** | Estados de mercancía | APPROVED · ACTIVE (v2 2026-09-03) | **CLOSED** — matriz de transiciones declarada; `R-D0-10-7` ejecutable | Arq. procesos · Almacén | 021, 023 + 9 Specs | 021, 022, 032 |
| **D0-11** | Vínculo pedido → factura | APPROVED | **CLOSED** | Arq. datos · Auditor · Contador | 034 + 6 Specs | 034 |
| **D0-12** | Confirmación independiente del pedido | APPROVED | **CLOSED_WITH_CONFIGURATION_PENDING** | Arq. procesos · Auditor | 033 + 4 Specs | 033, 034 |
| **D0-13** | Dimensiones organizacionales | APPROVED | **CLOSED** | Arq. datos · Contador | 007 + transversal | 007 |
| **D0-14** | Put-away: alcance de la reserva, capacidad y selección de ubicación | APPROVED · ACTIVE (2026-09-04) | **CLOSED** — la reserva es de almacén y no de ubicación; capacidad informativa en V1; ubicación manual con filtro de backend | Arq. procesos · Almacén · Ventas | 022, 031, 032 | 022 |

## Recuento de cierre

| Clasificación | Cantidad | Decisiones |
|---|---:|---|
| **CLOSED** | **9** | D0-01, D0-03 (2026-09-02), D0-04, D0-08, D0-09, D0-10, D0-11, D0-13, D0-14 |
| **CLOSED_WITH_CONFIGURATION_PENDING** | **3** | D0-02, D0-05, D0-12 |
| **BUSINESS_DECISION_PENDING** | **1** | D0-06 |
| **LEGAL_VALIDATION_PENDING** | **1** | D0-07 |
| **TECHNICAL_VALIDATION_PENDING** | 0 | — |
| **BLOCKED** | 0 | — |
| **TOTAL** | **13** | ✔ |

**11 de 13 decisiones quedan cerradas para efectos de construcción.** Las dos restantes no impiden
escribir Specs: D0-06 tiene la arquitectura cerrada y solo falta contratar hospedaje; D0-07 tiene el
gobierno cerrado y lo que falta es contenido tributario, que por definición no lo produce el software.

## Nota metodológica

Ninguna decisión quedó en estado ambiguo. Se aplicó estrictamente la distinción del §32 del encargo:

- **Decisión pendiente** = no se sabe qué hacer → bloquea.
- **Configuración pendiente** = se sabe qué hacer, faltan los valores del cliente → no bloquea.

Ejemplo: el motor de aprobaciones queda **CLOSED** aunque no se conozca ningún umbral de monto. La
arquitectura está decidida; los umbrales son datos de implantación.

## Documentos de cada decisión

| ID | ADR | Política |
|---|---|---|
| D0-01 | `adr/ADR-D0-001-postgresql-production-parity.md` | — |
| D0-02 | `adr/ADR-D0-002-approval-engine.md` | `policies/POL-D0-001-approval-policy.md` |
| D0-03 | `adr/ADR-D0-003-inventory-reservation.md` | `policies/POL-D0-002-stock-reservation-policy.md` |
| D0-04 | `adr/ADR-D0-004-warehouse-location-model.md` | `policies/POL-D0-003-warehouse-location-policy.md` |
| D0-05 | `adr/ADR-D0-005-commercial-rules.md` | `policies/POL-D0-004-commercial-policy.md` |
| D0-06 | `adr/ADR-D0-006-license-authority.md` | `policies/POL-D0-005-license-governance.md` |
| D0-07 | `adr/ADR-D0-007-fiscal-governance.md` | `policies/POL-D0-006-fiscal-governance.md` |
| D0-08 | `adr/ADR-D0-008-document-management.md` | — |
| D0-09 | `adr/ADR-D0-009-uom-presentation-snapshot.md` | — |
| D0-14 | `d0-14-checkpoint/d0-14-putaway-decisions.md` | `POL-D0-002` §7 ampliada con su consecuencia para el put-away |
| D0-10 | `adr/ADR-D0-010-goods-states.md` (v2) | `d0-10-checkpoint/` — matriz de transiciones, matriz de dueños, análisis del conflicto con reservas, convergencia |
| D0-11 | `adr/ADR-D0-011-order-invoice-link.md` | — |
| D0-12 | `adr/ADR-D0-012-order-confirmation.md` | — |
| D0-13 | `adr/ADR-D0-013-organizational-dimensions.md` | — |
