# FASE D0 — DECISIONES FUNDACIONALES DE KONTROL

| Campo | Valor |
|---|---|
| Fase | D0 — Decisiones fundacionales |
| Estado | **COMPLETADA** (13/13 decisiones resueltas o formalmente clasificadas) |
| Fecha | 2026-08-29 |
| Rama · HEAD | `develop` · `def2b52` |
| Autoridad | Nivel 5 (ADR) bajo Constitución v1.0 |
| Alcance | Gobierno — **no compite con las 56 Specs funcionales** |
| Prohibiciones respetadas | Sin código productivo · sin migraciones · sin nuevas Specs funcionales · sin `/speckit.implement` |

## Por qué existe esta fase

El GAP Analysis (`docs/roadmap/`) determinó que 31 de las 56 Specs maestras están pendientes y que
la deuda se concentra en la capa operativa de almacén. Antes de escribir esas Specs hay que cerrar
las decisiones estructurales que hoy están **implícitas**: cada módulo que resolvió por su cuenta
aprobaciones, reservas, precios o ubicaciones generó una divergencia que después hay que migrar.

D0 convierte esas decisiones implícitas en reglas explícitas, trazables y obligatorias.

## Estructura

```
d0-foundational-decisions/
├── README.md                        (este archivo)
├── D0-decision-register.md          13 decisiones en formato completo
├── D0-impact-matrix.md              decisión → Spec afectada → tipo de impacto
├── D0-spec-dependencies.md          qué Specs no pueden empezar hasta cerrar qué
├── D0-blockers.md                   bloqueantes con responsable y acción
├── D0-open-questions.md             lo que falta decidir, clasificado
├── D0-fiscal-validation-matrix.md   24 reglas fiscales con fuente y estado
├── D0-historical-data-risk.md       deuda que impide reconstruir historia
├── D0-roadmap-adjustment.md         roadmap antes y después de D0
├── D0-constitution-diff.md          enmiendas propuestas (no aplicadas)
├── D0-acceptance-checklist.md       criterios de cierre
├── D0-final-resolution.md           entrega ejecutiva
├── adr/     ADR-D0-001 … ADR-D0-013
└── policies/ POL-D0-001 … POL-D0-006
```

## Relación con los ADR existentes

`specs/001-fundacion/adr/` contiene 15 ADR, **todos en estado `PROPUESTO` y ninguno aprobado**.
D0 no los duplica: los **extiende y los eleva**.

| ADR existente | Qué decidía | ADR D0 que lo extiende |
|---|---|---|
| ADR-003 PostgreSQL como fuente de verdad | PG es la fuente transaccional | **ADR-D0-001** añade *paridad con producción* en desarrollo, CI, QA y E2E |
| ADR-005 Firma asimétrica | Ed25519, clave privada solo en la autoridad | **ADR-D0-006** añade la arquitectura de la autoridad, contrato, rotación y privacidad |
| ADR-008 Estrategia de archivos | Volúmenes locales + metadatos en PG | **ADR-D0-008** añade el modelo de vinculación y versionado |
| ADR-012 Auditoría | Evento de auditoría con antes/después | Sin cambio; D0 registra la instrumentación incompleta como deuda |
| ADR-013 Idempotencia y concurrencia | Claves de idempotencia y control de concurrencia | **ADR-D0-003** lo aplica a la reserva de inventario |

**Hallazgo de gobierno:** que los 15 ADR fundacionales sigan en `PROPUESTO` significa que la
Constitución (P12: «toda decisión arquitectónica relevante se formaliza mediante ADR con estado de
aprobación») no se ha cumplido nunca en el proyecto. Registrado en `D0-open-questions.md` como
**OQ-14**.

## Regla de lectura

Ninguna Spec funcional posterior puede contradecir un ADR-D0 aprobado. Si una Spec necesita
apartarse, requiere enmienda del ADR con el procedimiento de la Constitución — no una excepción
local.
