# MATRIZ DE IMPACTO D0 → 56 SPECS

Tipo de impacto: **E** estructural (cambia el modelo) · **F** funcional (cambia el comportamiento) ·
**G** gobierno (cambia la regla de aceptación) · **C** configuración.

| Decisión | Spec | Tipo | Bloquea inicio | Requiere migración |
|---|---|:--:|:--:|---|
| D0-01 | **todas (56)** | G | No | NO_MIGRATION |
| D0-01 | 001, 052, 053, 054 | F | No | NO_MIGRATION |
| D0-02 | **045** | E | **Sí** | BACKFILL_REQUIRED + MANUAL_REVIEW |
| D0-02 | 015, 017, 025, 030, 033 | F | **Sí** | SAFE_MIGRATION |
| D0-02 | 018, 026, 028, 034, 036, 040, 042 | F | No | SAFE_MIGRATION |
| D0-03 | **030** | E | **Sí** | SAFE_MIGRATION + MANUAL_REVIEW |
| D0-03 | 023, 031, 032 | F | **Sí** | SAFE_MIGRATION |
| D0-03 | 029, 033, 034, 035 | F | No | NO_MIGRATION |
| D0-04 | **008** | E | **Sí** | SAFE_MIGRATION |
| D0-04 | 022, 031, 032 | E | **Sí** | BACKFILL_REQUIRED + MANUAL_REVIEW |
| D0-04 | 019, 021, 023, 024, 025, 036 | E | No | SAFE_MIGRATION |
| D0-05 | **012** | E | **Sí** | BACKFILL_REQUIRED + MANUAL_REVIEW |
| D0-05 | 029, 030, 034 | F | **Sí** | SAFE_MIGRATION |
| D0-05 | 009, 036, 037 | F | No | SAFE_MIGRATION |
| D0-06 | **004** | G | No | NO_MIGRATION |
| D0-06 | 048, 052, 053 | F | No | NO_MIGRATION |
| D0-07 | **039, 040, 041, 042, 043** | G | No (bloquea **cierre**) | SAFE_MIGRATION |
| D0-07 | 014, 027, 028, 034, 037, 056 | G | No | NO_MIGRATION |
| D0-08 | **046** | E | **Sí** | SAFE_MIGRATION |
| D0-08 | 018, 020, 035 | F | **Sí** | NO_MIGRATION |
| D0-08 | 019, 021, 027, 036, 044, 050, 051 | F | No | NO_MIGRATION |
| D0-09 | **011** | E | **Sí** | **BACKFILL_REQUIRED + MANUAL_REVIEW** |
| D0-09 | **019** | E | **Sí** | **BACKFILL_REQUIRED** |
| D0-09 | 015-018, 020-023, 025, 026, 029, 032, 034, 035, 036 | E | No | **BACKFILL_REQUIRED** |

> **Corrección G0:** esta matriz omitía `019` como bloqueada por D0-09 (la línea de recepción debe
> capturar unidad y presentación, que es modelo). Corregido arriba.
| D0-10 | **021, 023** | E | **Sí** | SAFE_MIGRATION |
| D0-10 | 019, 020, 022, 024, 025, 030, 031, 032, 035, 036 | F | No | SAFE_MIGRATION |
| D0-11 | **034** | E | **Sí** | **BACKFILL_REQUIRED + DATA_LOSS_RISK** |
| D0-11 | 029, 030, 033, 035, 036, 037, 042 | F | No | NO_MIGRATION |
| D0-12 | **033** | E | **Sí** | SAFE_MIGRATION |
| D0-12 | 031, 032, 034, 035 | F | No | SAFE_MIGRATION |
| D0-13 | **007** | E | **Sí** | SAFE_MIGRATION + MANUAL_REVIEW |
| D0-13 | transversal (todas las transaccionales) | E | No | SAFE_MIGRATION |

## Specs con más decisiones incidentes

| Spec | Decisiones que la condicionan | Lectura |
|---|---:|---|
| **034 Facturación** | D0-02, 03, 05, 07, 09, 11, 12 → **7** | Es el punto donde converge casi todo el sistema. Escribirla antes que las demás garantiza reescribirla |
| **032 Picking** | D0-02, 03, 04, 09, 10, 12 → **6** | — |
| **030 Reserva** | D0-01, 02, 03, 04, 05, 09 → **6** | — |
| **021 Confirmación de recepción** | D0-04, 08, 09, 10, 13 → **5** | — |
| **029 Pedido comercial** | D0-03, 05, 09, 11, 13 → **5** | — |
| **019 Recepción física** | D0-04, 08, 09, 10, 13 → **5** | — |

## Decisiones con mayor alcance

| Decisión | Specs afectadas | Naturaleza |
|---|---:|---|
| **D0-01** PostgreSQL | 56 | Cambia el criterio de aceptación de todo el proyecto |
| **D0-09** UOM/presentación | 18 | Cambia el modelo de línea de todos los documentos |
| **D0-02** Aprobaciones | 13 | Sustituye 4 implementaciones divergentes |
| **D0-13** Dimensiones | 13 | Normaliza el contexto organizacional |
| **D0-04** Almacenes | 10 | Habilita toda la operación física |
| **D0-08** Documentos | 10 | Habilita toda la evidencia |
