# PLAN · PROC-11 (GOV-PROC-017)

## Flujo de usuario (escrito antes de implementar)

```
WHERE_IS_IT_IN_MENU = Gobierno › Contrataciones › Funciones incompatibles
ACTOR = Control Interno (gobierno_sod:view / manage / activate)
PRECONDITIONS = módulo Gobierno encendido; capacidad; ente con expedientes de contratación
USER_ACTION_1 = declara la regla «Receptor no evalúa» (RECEPTOR ≠ EVALUADOR) con su fundamento
USER_ACTION_2 = la activa desde hoy con MFA
USER_ACTION_3 = abre el listado de conflictos del período y exporta
EXPECTED_RESULT = la regla queda VIGENTE; el listado muestra los expedientes donde la misma persona recibió una oferta
                  y además evaluó, con la evidencia de ambas funciones
NEGATIVE_CASES = sin capacidad → 403; otro ente → 404; activar con fecha pasada prohibida por vigencia; par igual → 422;
                 regla vigente solapada → 409; intento de asumir función incompatible → 409 GOV_SOD_ROLE_CONFLICT
AUDIT_RESULT = GOV_SOD_ROLE_RULE_CREATED, GOV_SOD_ROLE_RULE_ACTIVATED, GOV_SOD_ROLE_RULE_CLOSED,
               GOV_SOD_ROLE_CONFLICT_BLOCKED, GOV_SOD_ROLE_CONFLICTS_EXPORTED
```

## Arquitectura

- **Reutiliza** (no duplica): capacidad `gobierno_sod` y su política MFA, `usuarios_equivalentes`/`funcionarios_de_actor`
  (ORG-06), `record_audit`/`record_audit_after_rollback` (CTL-02), el expediente y sus registros (PROC-03/06/07/08),
  `If-Match` + versión (concurrencia de expediente), el patrón de auditoría de CTL-01 y el patrón de menú y pantalla.
- **Añade**: catálogo de funciones, matriz institucional versionada, cálculo de ocupación, detección y guarda preventiva.

### Modelo de datos (migración `0103_gov_proc11_sod_funciones`)

`gov_sod_role_rules` (COMPANY): `codigo` único por ente, `nombre`, `descripcion`, `proceso` (`PROC-03`), `rol_a`, `rol_b`,
`fundamento`, `vigente_desde`, `vigente_hasta`, `estado` (`BORRADOR|VIGENTE|CERRADA`), `version`, `activada_por/en`,
`cerrada_por/en`, `motivo_cierre`, `created_by`. Índice parcial único `(company_id, rol_a, rol_b)` donde `estado='VIGENTE'`.
`gov_sod_role_rule_history`: `rule_id`, `tipo`, `detalle` JSON, `created_by`.

### Ocupación (por expediente)

| Función | Fuente |
|---|---|
| SOLICITANTE | `files.created_by` ∪ funcionarios de `file_responsibles` con `rol='REQUIRENTE'` vigente |
| RECEPTOR | `offers.created_by` ∪ `offers.official_id` |
| EVALUADOR | miembros de la comisión del expediente ∪ `opening_attendees.official_id` ∪ `eval_contributions.created_by` ∪ `recommendations.emitida_por` ∪ `recommendation_signatories.official_id` |
| ADJUDICADOR | `decisions.decidida_por` ∪ `decisions.official_id` |

Se comparan por clase de equivalencia de actor (usuarios del mismo funcionario/delegación); el par se declara con la
fecha de la ocupación más reciente y se evalúa contra la regla en vigor a esa fecha (PDD-PROC11-09).

### API

| Método | Ruta | Capacidad |
|---|---|---|
| GET | `/gobierno/sod/funciones` | `gobierno_sod:view` |
| GET | `/gobierno/sod/funciones/reglas?estado=` | `gobierno_sod:view` |
| POST | `/gobierno/sod/funciones/reglas` | `gobierno_sod:manage` |
| POST | `/gobierno/sod/funciones/reglas/{id}/activar` (If-Match) | `gobierno_sod:activate` (MFA) |
| POST | `/gobierno/sod/funciones/reglas/{id}/cerrar` (If-Match) | `gobierno_sod:activate` (MFA) |
| GET | `/gobierno/sod/funciones/conflictos?desde=&hasta=&rol=&expediente_id=` | `gobierno_sod:view` |
| GET | `/gobierno/sod/funciones/conflictos.csv?...` | `gobierno_sod:view` |
| GET | `/gobierno/contrataciones/expedientes/{id}/conflictos-funciones` | `gobierno_expedientes:view` |

## Constitution Gate

| Compuerta | Resultado | Evidencia |
|---|---|---|
| REQUIREMENT_COMPLETE | PASS | GOV-PROC-017 verbatim en `FUENTES.md`; historias US1–US3; FR-001..013; SC-001..006 |
| NORMATIVE_AUTHORITY | PASS | N20 y N23 (clase A) imponen segregar y prevenir el conflicto; no fijan pares → matriz institucional |
| DOMAIN_DEPENDENCIES | PASS | PROC-03/06/07/08, ORG-06 y CTL-02 existen y están publicados; `PAGADOR` fuera de alcance declarado |
| SECURITY | PASS | capacidad existente `gobierno_sod`, MFA en activación, aislamiento por ente, backend autoridad |
| DATA_INTEGRITY | PASS | tabla versionada, historia inmutable, índice parcial de no solapamiento, sin borrado físico |
| ARCHITECTURE | PASS | reutiliza motores; no duplica CTL-01/CTL-02/ORG-06 ni el expediente |
| TESTABILITY | PASS | SC-001..006 verificables por API, PostgreSQL y E2E |
| MATERIAL_DECISION | PASS (ninguna) | la matriz es configuración de Control Interno (precedente OD-CTL01-02/04); `PAGADOR` se declara no disponible, no se simula |

`CONSTITUTION_GATE=PASS`

## Riesgos

- **Evadible por datos históricos.** El bloqueo solo impide conflictos nuevos; los anteriores se ven en el listado
  (SC-003). Se declara en la tarjeta de UAT.
- **`RECEPTOR` acotado a ofertas.** Ver PDD-PROC11-12; se declara en UAT y matrices.
- **Rendimiento.** La detección recorre los expedientes del período; se limita por período y se indexa por `file_id`.
