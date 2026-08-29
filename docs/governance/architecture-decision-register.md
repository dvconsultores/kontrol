# REGISTRO MAESTRO DE DECISIONES ARQUITECTÓNICAS

| Campo | Valor |
|---|---|
| Última actualización | Gate G0 · 2026-08-29 |
| ADR vigentes (`APPROVED`) | **29** |
| ADR en `PROPUESTO` | **0** |
| ADR `SUPERSEDED` totales | **0** (1 supersesión parcial de sección) |
| ADR `REJECTED` | **0** |

> Solo los ADR en estado `APPROVED` representan arquitectura vigente.
> Los ADR históricos no se borran: se actualizan o se marcan, conservando trazabilidad.

## Bloque fundacional — `specs/001-fundacion/adr/`

| ADR | Título | Estado | Fecha | Sustituye | Sustituido por | Specs afectadas |
|---|---|---|---|---|---|---|
| ADR-001 | Monolito modular | **APPROVED** | 2026-08-03 · G0 | — | — | 001, todas |
| ADR-002 | Instalación independiente por cliente | **APPROVED** | 2026-08-03 · G0 | — | — | 001, 004, 052, 053 |
| ADR-003 | PostgreSQL como fuente de verdad | **APPROVED** (actualizado G0) | 2026-08-03 · G0 | — | **extendido por ADR-D0-001** | todas |
| ADR-004 | Autenticación y almacenamiento de sesión | **APPROVED** | 2026-08-03 · G0 | — | — | 002, 003, 055 |
| ADR-005 | Licenciamiento con firma asimétrica | **APPROVED** (actualizado G0) | 2026-08-03 · G0 | — | **extendido por ADR-D0-006** | 004 |
| ADR-006 | Sistema de diseño compartido | **APPROVED** | 2026-08-03 · G0 | — | — | 005, todas las de UI |
| ADR-007 | ReportLab para documentos desde backend | **APPROVED** | 2026-08-03 · G0 | — | — | 042, 050 |
| ADR-008 | Estrategia de archivos | **APPROVED** (actualizado G0) | 2026-08-03 · G0 | — | **§Consecuencias superseded por ADR-D0-008** | 046 |
| ADR-009 | Cola y workers (diferimiento) | **APPROVED** (diferimiento vigente) | 2026-08-03 · G0 | — | — | 048, 050 |
| ADR-010 | Observabilidad | **APPROVED** | 2026-08-03 · G0 | — | — | 006, 051 |
| ADR-011 | Multiempresa | **APPROVED** (actualizado G0) | 2026-08-03 · G0 | — | **extendido por ADR-D0-004 y ADR-D0-013** | 007, 008, 013 |
| ADR-012 | Auditoría | **APPROVED** | 2026-08-03 · G0 | — | — | 006, 051 |
| ADR-013 | Idempotencia y concurrencia | **APPROVED** | 2026-08-03 · G0 | — | — | 023, 028, 030, 034, 042 |
| ADR-014 | Versionado de dependencias | **APPROVED** | 2026-08-03 · G0 | — | — | 001, 052, 055 |
| ADR-015 | Política de modales | **APPROVED** | 2026-08-03 · G0 | — | — | 005, todas las de UI |

## Bloque fundacional D0 — `docs/governance/d0-foundational-decisions/adr/`

| ADR | Título | Estado | Fecha | Extiende | Specs afectadas |
|---|---|---|---|---|---|
| ADR-D0-001 | PostgreSQL con paridad de producción | **APPROVED** | 2026-08-29 | ADR-003 | las 56 |
| ADR-D0-002 | Motor transversal de aprobaciones | **APPROVED** | 2026-08-29 | — | 045, 015, 017, 025, 030, 033 + 7 |
| ADR-D0-003 | Momento y semántica de la reserva | **APPROVED** | 2026-08-29 | ADR-013 | 030, 023, 029, 031, 032 + 4 |
| ADR-D0-004 | Modelo físico genérico de almacén | **APPROVED** | 2026-08-29 | ADR-011 | 008, 019, 022, 031, 032 + 5 |
| ADR-D0-005 | Reglas comerciales | **APPROVED** | 2026-08-29 | — | 012, 029, 030, 034 + 3 |
| ADR-D0-006 | Autoridad central de licenciamiento | **APPROVED** | 2026-08-29 | ADR-005, ADR-002 | 004, 048, 052, 053 |
| ADR-D0-007 | Gobierno fiscal | **APPROVED** | 2026-08-29 | — | 039-043, 014, 056 |
| ADR-D0-008 | Gestión documental transversal | **APPROVED** | 2026-08-29 | ADR-008 | 046, 018, 020, 035 + 6 |
| ADR-D0-009 | Unidad, presentación y conversión | **APPROVED** | 2026-08-29 | — | 011 + 17 |
| ADR-D0-010 | Estados de mercancía | **APPROVED** | 2026-08-29 | — | 021, 023 + 10 |
| ADR-D0-011 | Vínculo pedido → factura | **APPROVED** | 2026-08-29 | — | 034 + 7 |
| ADR-D0-012 | Confirmación independiente del pedido | **APPROVED** | 2026-08-29 | — | 033, 034, 031, 032, 035 |
| ADR-D0-013 | Dimensiones organizacionales | **APPROVED** | 2026-08-29 | ADR-011 | 007 + transversal |

## Bloque de auditoría — `specs/012-auditoria-integral-e2e/`

| ADR | Título | Estado | Fecha | Nota |
|---|---|---|---|---|
| **ADR-016** *(era «ADR-012»)* | Precisión numérica: cantidad y medida en `Float` frente a `Numeric` | **APPROVED** | 2026-08-12 | Renumerado en G0 — ver §Colisión |

## Colisión de numeración resuelta en G0

Se detectaron **dos ADR distintos numerados 012**:

| Ruta | Tema | Fecha |
|---|---|---|
| `specs/001-fundacion/adr/ADR-012.md` | Auditoría | 2026-08-03 |
| `specs/012-auditoria-integral-e2e/adr-012-numeric-precision.md` | Precisión numérica | 2026-08-12 |

La colisión nació de que el segundo tomó su número de la **Spec** que lo originó (012) en lugar de la
secuencia del registro de ADR. Citar «ADR-012» en cualquier documento es hoy ambiguo.

**Resolución:** el ADR de precisión numérica pasa a ser **ADR-016** en este registro maestro. El
archivo no se renombra ni se mueve —conservar la ruta preserva los enlaces existentes— y se le añade
una nota de equivalencia. `ADR-012` designa, de forma única, el ADR de Auditoría.

**Regla derivada:** los ADR se numeran en una secuencia global única del registro maestro, nunca
según la Spec que los origina. Los ADR de la fase D0 usan el prefijo `ADR-D0-` precisamente para no
competir con esa secuencia.

## Recuento

| Bloque | ADR | Estado |
|---|---:|---|
| Fundacional `001` | 15 | 15 `APPROVED` (4 actualizados en G0) |
| Fundacional D0 | 13 | 13 `APPROVED` |
| Auditoría (ADR-016) | 1 | 1 `APPROVED` |
| **Total vigente** | **29** | **0 en `PROPUESTO`** |
