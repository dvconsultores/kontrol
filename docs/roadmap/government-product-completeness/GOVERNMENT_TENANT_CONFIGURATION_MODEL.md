# Modelo de configuración por tenant (GOV-ROADMAP-REBASELINE-02)

**Autoridad sobre:** qué configura cada ente, en qué orden y con qué estado. Cubre la organización parametrizable, las relaciones entre entes, el onboarding y las plantillas.

- **Estado:** diseño de referencia; no se implementa en este ciclo.
- **Base existente:** ORG-01..07 ya implementan una parte, como se indica en la tabla. El aislamiento de tenant sigue en `government-architecture-baseline.md` («Tenant / Organization Isolation»).

## 1. Organización parametrizable

| Concepto | Contenido | Hoy en el producto |
|---|---|---|
| `Institution` | El ente: nombre, tipo, RIF, jurisdicción, vigencia y acto | `GovernmentEntity` + `GovernmentEntityVersion` (ORG-01) |
| `OrganizationStructureVersion` | Estructura por ejercicio: BORRADOR → VIGENTE → CERRADA, con acto | `GovernmentStructure` (ORG-02) |
| `OrganizationalUnit` | Unidad con tipo configurable (órgano, unidad administrativa, ejecutora, dependencia, sede, centro gestor) | `GovernmentUnit` + versión (ORG-02) |
| `ReportingLine` | Relación jerárquica entre unidades | Jerarquía de `GovernmentUnit` |
| `Position` | Cargo por ejercicio | `GovernmentPosition` + versión (ORG-03) |
| `Competence` | Acción × materia, con límite monto+moneda o sin límite | `GovernmentPositionCompetency` (ORG-03) |
| `Authority` | Matriz de autoridad a fecha | ORG-07 |
| `Occupancy` / `Delegation` / `Substitution` | Ocupación, delegación, suplencia y encargaduría con acto y vigencia | `GovernmentAssignment` + historia (ORG-04) |
| `EffectivePeriod` | Vigencia desde/hasta en cada objeto versionado | Transversal |
| Capacidad funcional | `BUDGET_MANAGEMENT`, `TREASURY`… asignada por el ente a unidades o cargos | **Nuevo** (política de parametrización §5) |

El software **no conoce** nombres de unidades. Las encuentra por capacidad y competencia.

## 2. Relaciones entre entes

El organigrama de una alcaldía puede incluir institutos autónomos, fundaciones u otros organismos. No se asume que sean unidades internas. Por cada organismo relacionado se configura:

```text
ENTITY_RELATIONSHIP   (adscrito, tutelado, participado, interno)
ENTITY_TYPE           (instituto autónomo, fundación, empresa del Estado, servicio desconcentrado…)
LEGAL_PERSONALITY     (propia / sin personalidad)
ORGANIZATIONAL_LINK   (unidad interna del ente o tenant propio relacionado)
```

Si tiene personalidad jurídica y patrimonio propio, en principio es **otro tenant**: tiene su propio aislamiento, presupuesto y licencia. La decisión es configuración. No hace falta código específico.

## 3. Organigrama de Naguanagua

```text
NAGUANAGUA_ORGANIZATION_BASELINE   STATUS=FUNCTIONAL_REFERENCE   (no LEGAL_STRUCTURE_CERTIFIED)
```

- Es el organigrama general que entregó la dueña.
- Sirve para configurar el primer tenant y para probar la plantilla municipal.
- Pasa a estructura certificada solo cuando se contraste con los actos que la crean (ORG-02 exige acto para VIGENTE).
- Sus institutos y fundaciones se clasifican con §2 antes de cargarlos.

## 4. Estados de configuración del ente

La matriz canónica separa estas dimensiones (columnas nuevas de `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv`):

```text
PRODUCT_IMPLEMENTATION_STATUS   NOT_STARTED | IN_PROGRESS | COMPLETE
TENANT_CONFIGURATION_STATUS     NOT_APPLICABLE_UNTIL_BUILT | PENDING_ONBOARDING | CONFIGURED | PUBLISHED
NORMATIVE_VALIDATION_STATUS     NO_NORM_CITED | VERIFIED_SOURCES (A/B) | PENDING (clase C)
EXTERNAL_INTEGRATION_STATUS     NOT_APPLICABLE | PENDING | CONNECTED
OWNER_UAT_STATUS                (columnas OWNER_UAT_READY / OWNER_ACCEPTED, sin cambio)
```

Estas combinaciones son válidas, por ejemplo:

```text
PRODUCT=COMPLETE · TENANT=PENDING_ONBOARDING · NORMATIVE=PENDING · EXTERNAL=NOT_APPLICABLE · OWNER_UAT=READY
```

## 5. Onboarding guiado (orden)

1. Ente y tipo (ORG-01), elegido desde una plantilla.
2. Paquete normativo del tipo de ente, más los instrumentos propios (motor normativo §6).
3. Estructura y unidades del ejercicio (ORG-02), con su acto.
4. Capacidades por unidad o cargo.
5. Cargos y competencias (ORG-03); ocupación y delegaciones (ORG-04, ORG-06).
6. Calendario de días hábiles y feriados del ente (`BusinessCalendar`).
7. Clasificador presupuestario provisto por el ente, con procedencia (D02-B); plan de cuentas cuando exista ACC-01.
8. Procesos: elegir versión y parámetros (`TenantProcessConfiguration`), validar, previsualizar y publicar.

Cada paso responde a lo que necesita la administración funcional: qué falta, qué valida y qué se publica.

## 6. Plantillas

Las `GOVERNMENT_TEMPLATE` (política de parametrización §6) son configuraciones clonables por tipo de ente. Primera candidata: **Administración Pública Municipal**, construida a partir del primer tenant sin copiar sus datos particulares.
