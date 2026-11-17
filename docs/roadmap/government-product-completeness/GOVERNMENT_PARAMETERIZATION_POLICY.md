# Política de parametrización de KONTROL Gobierno (GOV-ROADMAP-REBASELINE-02)

**Autoridad sobre:** qué puede vivir en el código y qué debe ser configuración, y cómo se clasifica cada regla.
Es vinculante para toda GOV-SPEC nueva y para la adaptación de los procesos ya construidos.

- **Decisión de la dueña (2026-11-16):** `ZERO_INSTITUTIONAL_HARDCODE=1`, `TENANT_CONFIGURABLE=1`, `NATIONAL_REUSABLE_PRODUCT=1`, `PROCESS_VERSIONED=1`, `NORMATIVE_RULES_VERSIONED=1`.
- **Precedencia:** la Constitución del proyecto prevalece sobre este documento. La arquitectura general sigue en `docs/roadmap/government-architecture-baseline.md`; esta política la amplía y no la sustituye.

## 1. Principio

KONTROL Gobierno es un producto nacional para la Administración Pública venezolana. Cualquier ente compatible lo adapta por configuración.

Naguanagua es el **primer tenant de implementación**. No es el modelo del producto:

```text
NAGUANAGUA_IS_PRODUCT_MODEL=NO   NAGUANAGUA_SPECIFIC_CODE=0   TENANT_SPECIFIC_CODE=0
INSTITUTION_SPECIFIC_BEHAVIOR_HARDCODED=0   LEGAL_OR_INSTITUTIONAL_VALUES_IN_CODE=0
```

## 2. Lo que nunca va en código

Todo lo que pueda variar legítimamente entre instituciones es configuración versionada del ente:
- institución, organigrama, direcciones, unidades, cargos, personas y responsables;
- jerarquía, competencias, delegaciones, suplencias y firmantes;
- rutas de aprobación, límites y montos;
- documentos exigidos, plazos, calendarios y feriados;
- numeraciones, series, trámites y formatos;
- plan de cuentas, clasificadores, cuentas bancarias, fondos, cajas y almacenes;
- retenciones, alícuotas, umbrales y reportes institucionales;
- integraciones concretas, proveedores externos y logos.

Prohibido además:
- condicionales por nombre de tenant o de institución (`if tenant == …`);
- nombres de unidades como lógica, como «Dirección de Administración», «Tesorería Municipal» o «Auditoría Interna». El producto opera con **capacidades** (§5);
- listas de pantallas, permisos o superficies repetidas en varios sitios: hay una sola autoridad por concepto. Ejemplos: `SUPERFICIE_POR_SEGMENTO`, `pantallas.ts` y el catálogo de permisos.

## 3. Lo que sí puede permanecer en código (invariantes de plataforma)

- aislamiento de tenant, autenticación y el marco de autorización;
- integridad transaccional, control de concurrencia y garantías append-only;
- criptografía y el marco de auditoría;
- motor de reglas y motor de flujo (el **intérprete**, no las reglas);
- validación de esquemas, infraestructura de versionado y fronteras de seguridad.

Parametrizar no significa convertir la plataforma en datos: la mecánica es código y la política institucional es dato.

## 4. Tres tipos de regla

| Tipo | Qué es | Dónde vive | Quién la cambia | Requisitos |
|---|---|---|---|---|
| `LEGAL_MANDATORY` | Obligación con fuente jurídica válida | `NormativeRule` ligada a `NormativeVersion` (ver `GOVERNMENT_NORMATIVE_ENGINE_BASELINE.md`) | Nadie del ente: solo una nueva versión normativa | `normative_source`, `version`, `effective_from`, `effective_to`, `verification_status`. Protegida: una regla inferior no la neutraliza |
| `INSTITUTIONAL_POLICY` | Decisión del ente dentro del margen legal | `TenantPolicyProfile` versionado por tenant | Autoridad del ente, con acto (DOC-02) cuando la materia lo exige | Versión, vigencia, acto o fundamento, y quién la adoptó |
| `OPERATIONAL_CONFIGURATION` | Ajuste de operación sin efecto jurídico | Configuración del ente | Usuarios autorizados (capacidad específica) | Auditoría del cambio |

**Fuentes de clase C** (N07–N10, N14–N17, N36, N37, N38, N40; registro `kontrol-gobierno-source-register.md`):
- **siguen sin sustentar una regla `LEGAL_MANDATORY`** activa en el producto;
- **ya no bloquean la capacidad**. La regla se modela como dato con `verification_status=PENDING_PIN`;
- **el ente puede adoptar el valor** como `INSTITUTIONAL_POLICY` propia. Lo hace con fundamento, bajo su responsabilidad, y rotulado como «adoptado por el ente», nunca como «exigido por la ley». Es el mismo patrón que la disponibilidad declarada de TRE-02 (OD-TRE02-02) y el clasificador provisto por el ente de D-GOV-02 (D02-B).

**Benchmarks** de otros entes o países:
- producen como mucho un `RECOMMENDED_DEFAULT` en una plantilla (§6);
- nunca producen `LEGAL_MANDATORY` sin fuente jurídica válida;
- no se copian procedimientos ajenos como si fueran obligatorios.

## 5. Capacidades en lugar de nombres

Los flujos piden **capacidades funcionales**, y el ente decide qué unidad o cargo las ejerce:

```text
BUDGET_MANAGEMENT  TREASURY  ACCOUNTING  PROCUREMENT  PUBLIC_ASSETS  LEGAL_REVIEW
INTERNAL_CONTROL   RECORDS_MANAGEMENT  WAREHOUSE  HUMAN_RESOURCES  PLANNING
```

- La autorización real sigue siendo `cargo → competencia (acción × materia) → límite`, con la matriz de autoridad (ORG-03/ORG-07).
- La capacidad es la etiqueta funcional que el motor de procesos usa para encontrar quién actúa.

## 6. Plantillas (`GOVERNMENT_TEMPLATE`)

- Una plantilla es **configuración clonable**, nunca una rama de código. Ejemplos: Administración Pública Municipal, Gobernación, Instituto Autónomo, Fundación Pública, Servicio Autónomo.
- Contiene `RECOMMENDED_DEFAULT` de estructura, capacidades, procesos, plazos y documentos.
- Al clonarse se convierte en `INSTITUTIONAL_POLICY` del ente, que la ajusta y publica versión.

## 7. Metodología por proceso

```text
AS_IS_DISCOVERY → OFFICIAL_NORMATIVE_RESEARCH → VERIFIABLE_PUBLIC_SECTOR_BENCHMARK → MULTIDISCIPLINARY_ANALYSIS
→ TO_BE_DESIGN → PARAMETRIC_PROCESS → FUNCTIONAL_LEGAL_VALIDATION → KONTROL_EXECUTION → EVIDENCE_AND_AUDIT
→ INSTITUTIONAL_DOCUMENTATION
```

`MISSING_LOCAL_MANUAL != TRUE_BLOCKED`. Si el ente no tiene manual, procedimiento, formato o catálogo, KONTROL le ayuda a levantarlo y documentarlo, y la versión resultante se publica como `INSTITUTIONAL_POLICY`.

## 8. Comprobación en cada GOV-SPEC (gate de diseño)

Toda GOV-SPEC nueva declara:
- **regla por regla:** su tipo (§4), su fuente y su verificación;
- **cada valor institucional:** dónde se configura y quién lo cambia;
- **evidencia de que no hay constantes institucionales en código:** nombres de unidad, montos, plazos o alícuotas.

Para los 44 procesos ya construidos, la evidencia la aporta la auditoría `GOV-PARAMETERIZATION-AUDIT-01` de P2. Esa auditoría clasifica cada uno como `KEEP_AS_IS`, `ADAPT_TO_PROCESS_ENGINE` o `REFACTOR_HARDCODED_POLICY`; este documento no anticipa su resultado.
