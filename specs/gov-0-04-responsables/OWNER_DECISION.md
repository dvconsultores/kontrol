# OWNER_DECISION · ORG-05 Responsables (OQ-ORG05-01..03)

```text
STATUS=CLOSED
DECIDED_BY=la dueña (ratificación tras GOV-ROADMAP-REBASELINE-02)
DECISION_DATE=2026-11-16
POLICY=ZERO_INSTITUTIONAL_HARDCODE=1 · TENANT_CONFIGURABLE=1 · NATIONAL_REUSABLE_PRODUCT=1
OQ-ORG05-01=CLOSED  DECISION=PARAMETRIC_SUBJECT_TYPE
OQ-ORG05-02=CLOSED  DECISION=TYPED_RESOURCE_ACCOUNT
OQ-ORG05-03=CLOSED  DECISION=DOMAIN_OWNERSHIP_PLUS_TRANSVERSAL_RESPONSIBILITY_BINDING
ORG05_STATUS=BUILDABLE_NOW
```

Esta decisión es vinculante para la futura GOV-SPEC de ORG-05. Es producto nacional: **no se reinterpreta como regla de Naguanagua**.

## OQ-ORG05-01 · ¿El responsable es el cargo, la persona o ambos?

**Ambos, parametrizable por tipo de responsabilidad y de recurso.** No hay una respuesta global.

- `RESPONSIBLE_SUBJECT_TYPE ∈ {POSITION, PERSON, POSITION_AND_PERSON}`.
- La regla se define con estos atributos:
  - `resource_type`, `responsibility_type`, `subject_type`;
  - `effective_from`, `effective_to`;
  - `normative_basis`, `tenant_policy`.
- **Ejemplos conceptuales, que no se hardcodean.** Responsable institucional de unidad → normalmente POSITION. Custodio material de un bien → PERSON. Responsable de caja → configurable. Supervisor de contrato → según la norma o la configuración aplicable.
- **Al asignar a una persona** se conserva su contexto institucional vigente en ese momento:
  - persona, cargo y unidad;
  - ocupación;
  - acto o delegación, cuando aplique;
  - vigencia.

  **La historia nunca se reinterpreta con la ocupación actual.**

## OQ-ORG05-02 · ¿Qué significa «cuenta»?

**No se fija «cuenta» a un único dominio.**

- Se modela con un **tipo de recurso explícito**. Como mínimo, cuando existan sus dominios: `BANK_ACCOUNT` (TRE-01), `ACCOUNTING_ACCOUNT` (ACC-01) y `ACCOUNTABILITY_ACCOUNT` (dominio de rendición).
- Admite tipos nuevos sin migraciones específicas de ORG-05.
- **Prohibido** un `cuenta_id` sin tipo. Se usa una referencia tipada: `resource_type` + `resource_id`, o equivalente seguro.
- La disponibilidad de cada tipo depende de que exista su dominio propietario. **ORG-05 no es dueño de esos objetos.**
- Si el análisis normativo exige otro concepto de cuenta, se añade como tipo soportado, sin reinterpretar registros anteriores.

## OQ-ORG05-03 · ¿Registro transversal o responsabilidad por dominio?

**Modelo híbrido: autoridad del dominio + consolidación transversal.**

- **Cada dominio conserva la autoridad sobre su relación funcional:**
  - CNT-04, el supervisor contractual;
  - AST, el custodio del bien;
  - TRE-01, los autorizados de la cuenta bancaria;
  - TRE-08, el responsable de caja o fondo;
  - WH, el responsable de almacén.
- **`ResponsibilityBinding` es la capacidad transversal común.** Un dominio puede usarla directamente, o puede proyectarse o consolidarse desde la relación propietaria del dominio.
- **Principio:** `ONE_BUSINESS_AUTHORITY` · `MULTIPLE_READ_PROJECTIONS_ALLOWED`.
- **ORG-05 es la vista transversal institucional de responsabilidades**, con historia y vigencia. No duplica datos para mostrar una pantalla central ni crea una segunda verdad.
- **ORG-05 debe responder:**
  - quién es responsable, de qué y bajo qué rol;
  - desde cuándo y hasta cuándo;
  - por qué autoridad;
  - en qué unidad;
  - con qué fuente.

## Patrón resultante (común con CTL-08)

```text
DOMINIO PROPIETARIO → RECURSO TIPADO → BINDING / EVENTO TRANSVERSAL → CONFIGURACIÓN DEL TENANT → HISTORIA VERSIONADA
```

No se admiten:
- nombres de recursos, unidades o cargos hardcodeados;
- significados ambiguos de «cuenta»;
- listas cerradas;
- autoridad duplicada entre módulos.

Esta decisión supera los bloqueos B-ORG05-01..03 y la tabla `evidence/ORG05_TARGET_RESOURCE_MATRIX.md` (2026-11-01). Esos documentos quedan como evidencia histórica.
