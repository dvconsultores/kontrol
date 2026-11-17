# OWNER_DECISION · CTL-08 Historial de maestros sensibles (OQ-CTL08-01)

```text
STATUS=CLOSED
DECIDED_BY=la dueña (ratificación tras GOV-ROADMAP-REBASELINE-02)
DECISION_DATE=2026-11-16
POLICY=ZERO_INSTITUTIONAL_HARDCODE=1 · TENANT_CONFIGURABLE=1 · NATIONAL_REUSABLE_PRODUCT=1
OQ-CTL08-01=CLOSED  DECISION=CONFIGURABLE_SENSITIVE_MASTER_TYPES
CTL08_STATUS=BUILDABLE_NOW
```

Esta decisión es vinculante para la futura GOV-SPEC de CTL-08. Es producto nacional: no se reinterpreta como regla de Naguanagua.

## Decisión

**«Cuentas» no se limita a cuentas bancarias.**
- CTL-08 vigila **tipos configurables** de maestros sensibles, con clasificación tipada.
- Inicialmente soporta `BANK_ACCOUNT` (TRE-01) y `ACCOUNTING_ACCOUNT` (cuando exista ACC-01), además de cualquier otro tipo de cuenta que se incorpore legítimamente al modelo.
- **Prohibido:** `if maestro == "cuentas": usar cuentas bancarias`.

**Registro configurable `SensitiveMasterType`.** Atributos:
- identificación: `code`, `resource_type`, `domain`;
- control: `enabled`, `risk_level`, `approval_required`, `history_required`;
- vigencia y fuente: `effective_from`, `effective_to`, `tenant_policy`, `normative_basis`.

**Maestros vigilables (lista no cerrada en código):**
- clasificadores presupuestarios;
- cuentas bancarias;
- plan de cuentas contable;
- proveedores y terceros;
- otros maestros sensibles que el ente habilite.

**Reparto de responsabilidades:**
- **Cada dominio sigue siendo dueño de su maestro.**
- CTL-08 consume sus eventos e historia y da la visión transversal de control: valor anterior y nuevo, actor, autoridad, fecha, motivo, soporte, aprobación, tenant y correlación.
- Cuando exista ACC-01, `ACCOUNTING_ACCOUNT` entra en el alcance **sin refactor de CTL-08**.

## Patrón resultante (común con ORG-05)

```text
DOMINIO PROPIETARIO → RECURSO TIPADO → BINDING / EVENTO TRANSVERSAL → CONFIGURACIÓN DEL TENANT → HISTORIA VERSIONADA
```

Esta decisión supera `evidence/CTL08_DEPENDENCY_GATE.md` y `evidence/CTL08_MASTER_INVENTORY.md` (2026-11-07), que quedan como evidencia histórica.
