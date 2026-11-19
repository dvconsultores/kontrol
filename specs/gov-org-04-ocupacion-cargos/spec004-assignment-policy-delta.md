# Delta ORG-04 · Política de asignación (ORG-04-AUTHORITY-ASSIGNMENT-POLICY)

**Spec dueña:** `specs/gov-org-04-ocupacion-cargos/spec.md`. **Prioridad:** P0, por un defecto de producto vigente.

## 1. Defecto P0

- **Antes:**
  - el catálogo `FIGURAS` (`service_ocupacion.py`) da como base legal la LOPPM, una ley municipal, para cualquier ente;
  - la UI pide «Autorización del Concejo» en toda suplencia de máxima autoridad (`NuevaAsignacionPage.tsx`), pero el backend solo la exige si el ente es MUNICIPAL;
  - los plazos (15 y 90 días, un año), el medio del acto, el emisor y la avocación están escritos en el código.
- **Causa raíz:** no hay una autoridad única de reglas. La UI y el backend codifican cada uno su propia versión del régimen municipal.
- **Después:**
  - una sola autoridad (`service_asignacion_regla.py`) resuelve la regla aplicada: los pisos legales del régimen del ente más la política versionada que este configure;
  - el backend la usa para validar;
  - la UI la pide (`GET /gobierno/ocupacion/regla`) y solo muestra lo que la regla exige.

## 2. Fuentes verificadas (§9)

| Piso | Fuente | Aplicabilidad verificada | Exigencias |
|---|---|---|---|
| `LOAP_DELEGACION` | LOAP, G.O. 6.147 Ext. (17-11-2014), arts. 2, 34, 35, 40 y 41 | Art. 2 (p. 8 de la copia): Administración nacional, estados, distritos y municipios; supletoria para los demás órganos y entes. **Todo nivel** | Acto publicado en gaceta; el emisor es el cargo delegante; no se subdelega; el delegado depende del delegante; solo se delega lo que el cargo tiene; admite avocación |
| `LEFP_COMISION` | LEFP, G.O. 37.522 (06-09-2002), arts. 1, 71 y 72 | Art. 1: administraciones nacionales, estadales y municipales. **Todo nivel** | La comisión de servicio dura un año como máximo |
| `LOPPM_ART87` | LOPPM, G.O. 6.015 Ext. (28-12-2010), arts. 87 y 95.18 | **Solo** entes con `nivel_territorial = MUNICIPAL` | En una suplencia de la máxima autoridad: más de 15 días exige «Autorización del Concejo Municipal»; con más de 90 días decide el Concejo (falta absoluta) |

MATERIAL_NORMATIVE_UNKNOWN=NO: las tres fuentes se verificaron en las copias de `requerimientos/gobierno/normativa-n37-naguanagua/`.

## 3. Decisiones de la dueña (2026-11-18)

| Id | Decisión |
|---|---|
| OD-AP-01 | Sin política vigente para la figura, rigen **solo los pisos legales** del régimen del ente («Regla legal base, sin política institucional»). Con política vigente, se aplica automáticamente |
| OD-AP-02 | **Pisos por régimen:** LOAP y LEFP para todo nivel; LOPPM art. 87 solo en lo municipal. Están versionados y citan su fuente. La política puede endurecerlos, nunca rebajarlos |
| OD-AP-03 | Las asignaciones activadas antes de este delta **conservan su regla histórica**, sin backfill |
| OD-AP-04 | Tope de 24 llamadas a DeepSeek |

## 4. Decisiones de diseño de Claude

| Id | Decisión |
|---|---|
| D-AP-01 | Las **6 figuras** son taxonomía de plataforma: vocabulario nacional estable, con grupo, cargo de origen y competencias, y con CHECK en la BD que consumen PROC-02, CNT y CTL-09. Sus **reglas** salen de la figura del catálogo y pasan a pisos y políticas. `base_legal` sale del catálogo |
| D-AP-02 | Hay una política VIGENTE por código. Al activarla se rechaza otra VIGENTE de la misma figura con vigencia solapada. Aplica la política cuya vigencia cubre la fecha `desde` de la asignación |
| D-AP-03 | Endurecer: los pisos se aplican **siempre** y la política solo **añade** (límite de días, fin obligatorio, medio del acto, emisor, autorización, lista de competencias, prohibición de avocación y documentos). La activación rechaza una política que contradiga un piso: medio distinto de gaceta o emisor distinto del delegante en una delegación |
| D-AP-04 | La regla se guarda en el borrador y **se congela al activar**. El disparador de PG impide cambiar `policy_id`, `policy_version` o `regla` fuera de BORRADOR |
| D-AP-05 | `autorizacion_concejo` pasa a `autorizacion_especial` en la columna y en la API. Su etiqueta sale de la regla |
| D-AP-06 | SoD: `_exigir_no_autoridad_propia` es una invariante estructural de ORG-04: nadie formaliza su propia ocupación. La SoD configurable ya pasa por CTL-01 (`ORG04_ACTIVAR`, `ORG04_REVOCAR` y `ORG04_FINALIZAR`). No se crea otra autoridad: SOD_DUPLICATE_AUTHORITIES=0 |
| D-AP-07 | Las competencias se resuelven con ORG-03 (`competencias_en_vigor`). La política solo restringe con una lista de competencias permitidas. COMPETENCE_AUTHORITY=ORG03_REUSED |
| D-AP-08 | El emisor se puede exigir por CARGO o por COMPETENCIA del cargo emisor del acto (ORG-03), en la fecha del acto. Nunca por el nombre del cargo |

## 5. Clasificación de reglas

| Regla | Clase |
|---|---|
| Aislamiento por tenant y empresa; historia inmutable; concurrencia optimista; cargo y estructura vigentes; vigencia coherente | PLATFORM_INVARIANT |
| Figuras, grupos, cargo de origen por figura; firma = FIRMAR; suplencia solo de un titular; un cargo no se designa a sí mismo; nadie formaliza su propia ocupación; solapamiento por grupo | PLATFORM_INVARIANT |
| Gaceta, emisor delegante, no subdelegar, dependencia, solo competencias propias y avocación en la delegación | LEGAL_MANDATORY (LOAP) |
| Comisión de servicio de un año como máximo | LEGAL_MANDATORY (LEFP) |
| Autorización del Concejo con más de 15 días y tope de 90 en la suplencia de la máxima autoridad municipal | LEGAL_MANDATORY (LOPPM, solo MUNICIPAL) |
| Límite de días, fin obligatorio, medio del acto, emisor por cargo o competencia, autorización especial, competencias permitidas, prohibir avocación y documentos por etapa | INSTITUTIONAL_POLICY |
| Códigos `POL-`/`ASG-`, etiquetas y textos de ayuda | OPERATIONAL_CONFIGURATION |

## 6. Requisitos

| Id | Requisito |
|---|---|
| FR-AP-01 | Política de asignación por empresa: código, versión, nombre, figura, fundamento, acto, vigencia y estado BORRADOR, VIGENTE o CERRADA, con historia inmutable y concurrencia optimista |
| FR-AP-02 | Reglas configurables: `max_dias`, `exige_fin`, `acto_medio`, emisor (CUALQUIERA, CARGO o COMPETENCIA), autorización especial (etiqueta, ámbito TODAS o MAXIMA_AUTORIDAD, `mas_de_dias`), competencias permitidas, `prohibe_avocacion` y documentos por etapa (ACTIVACION y REVOCACION) |
| FR-AP-03 | Pisos legales versionados con fuente, aplicabilidad por nivel territorial, fecha desde la que rigen y exigencias (§2) |
| FR-AP-04 | Autoridad única `regla_aplicable(figura, desde)`: pisos más política vigente, con fusión que solo endurece (D-AP-03) |
| FR-AP-05 | El backend valida crear, editar, activar, revocar y avocar con la regla. Revocar y avocar usan la regla congelada |
| FR-AP-06 | La asignación guarda `policy_id`, `policy_version` y `regla`, congeladas al activar (D-AP-04). La regla de una asignación de legado es la histórica (OD-AP-03) |
| FR-AP-07 | La autorización especial se pide y se exige solo si la regla aplicada lo determina (§20). COUNCIL_AUTH_RULE_DIVERGENCE=0 |
| FR-AP-08 | Los documentos obligatorios de cada etapa se exigen al activar y al revocar (adjuntos a `GovernmentAssignment`) |
| FR-AP-09 | API de políticas: listar, opciones, ficha, crear, editar, activar (MFA), cerrar (MFA) y nueva versión. Además, `GET /gobierno/ocupacion/regla` |
| FR-AP-10 | Permiso `gobierno_ocupacion:configure` y 5 eventos de auditoría GOV_ASSIGNMENT_POLICY_* |
| FR-AP-11 | Pantallas: lista, ficha (con historia y versiones) y formulario de políticas, en el menú de Gobierno; en la asignación, «Regla aplicada», autorización condicional y documentos |
| FR-AP-12 | Autoridad temporal: la ocupación del cargo en una fecha refleja la asignación activa, con su regla y su figura |
| FR-AP-13 | Pruebas: PG, mutaciones M1–M8, Vitest y E2E (principal, no municipal, autorización condicional, congelación de versión y resolución de autoridad), con Axe en 1280, 390 y 320 |

## 7. Gate

BLOCKER=0 · CRITICAL=0 · CONTRADICTIONS=0 · OWNER_CONFLICT=0 · MATERIAL_OQ=0 (OD-AP-01 a 04 resueltas) · UNKNOWN=0.
