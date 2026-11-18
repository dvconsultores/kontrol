# Delta · PROC-07/PROC-08-COMMISSION-POLICY · política de comisión configurable por el ente (2026-11-17)

- **Spec dueña:** `specs/gov-proc-02-comisiones` (comisiones de contrataciones).
- **Specs consumidoras:** `gov-proc-07-apertura-evaluacion` y `gov-proc-08-recomendacion-decision`, con un puntero en cada una.
- **Origen:**
  - los defectos P0 de PROC-07 y PROC-08 en `GOVERNMENT_OWNER_UAT_PARAMETERIZATION_AUDIT`;
  - la clasificación REFACTOR_HARDCODED_POLICY de PROC-02, PROC-07 y PROC-08.
- **Autorización:** el encargo «P2 — PROC-07 / PROC-08 · COMMISSION POLICY».
- **Plan y tareas:** `spec002-commission-policy-plan.md` y `spec002-commission-policy-tasks.md`.
- **Evidencia:** `evidence/commission-policy/`.

## 1. Arqueología

### Estado actual

- **PROC02_CURRENT_PURPOSE:** constituir la comisión de contrataciones.
  - Ciclo de vida BORRADOR → VIGENTE → CERRADA o DESCARTADA.
  - Miembros funcionarios (ORG-04) con función, área y condición, suplencia, término e inhibiciones. La historia es inmutable.
  - Al activarse exige un acto eficaz en Gaceta y la composición del art. 14 de la LCP.
- **PROC07_CURRENT_PURPOSE:** apertura y evaluación.
  - La comisión vinculada al expediente fija la matriz.
  - Abre las ofertas en acto público, con acta, asistentes y quórum.
  - Sus miembros evalúan.
- **PROC08_CURRENT_PURPOSE:** recomendación y decisión.
  - La comisión emite la recomendación firmada, que exige quórum de firmantes.
  - La máxima autoridad decide (adjudicar, desierta, terminar o nulidad).
- **Dependencia de comisión:** PROC-07 y PROC-08 leen la comisión vinculada al expediente (`committee_id`). Cada uno repite su propio cálculo de quórum.

### Defectos actuales (CURRENT_PRODUCT_DEFECTS)

| Id | Defecto | Evidencia |
|---|---|---|
| D1 | La apertura exige `committee_id`, aunque el expediente puede declarar «no interviene comisión». Ese procedimiento no puede abrir ni evaluar | `service_evaluacion.py:325` |
| D2 | La recomendación exige `committee_id`. Un procedimiento sin comisión no llega a la adjudicación ni a desierta | `service_decision.py:842` |
| D3 | Un miembro con inhibición ACEPTADA puede asistir y firmar. La inhibición no está ligada al expediente, solo a un `asunto` de texto | `models.py:2445`; `_miembros_comision` |

### Hardcode actual (CURRENT_HARDCODE)

| Id | Regla en código | Dónde | Clase |
|---|---|---|---|
| H1 | Quórum = `principales // 2 + 1` | `service_evaluacion.py:388` y `service_decision.py:880`, duplicado | INSTITUTIONAL_POLICY (OD-PROC07-01, «Sin fuente» en FUENTES) |
| H2 | Los firmantes deben alcanzar el mismo quórum (regla de decisión implícita) | `service_decision.py:870-889` | INSTITUTIONAL_POLICY (PDD-PROC08-10) |
| H3 | Composición: impar, tres áreas, suplente por principal, secretario y su suplente | `service_comisiones._faltantes` | LEGAL_MANDATORY (LCP art. 14, fuente verificada) |
| H4 | El acto de creación debe estar en Gaceta | `_acto_valido` | LEGAL_MANDATORY (RLCP art. 15) |
| H5 | No hay mínimo ni máximo de miembros, ni requisitos de cargo, unidad o competencia, ni presidencia, ni documentos de constitución | — | Ausente: INSTITUTIONAL_POLICY no configurable |
| H6 | Quien registró la comisión no puede activarla | `service_comisiones.activar` | Fuera de alcance (ver §7) |

**Hardcode de institución:** ninguno. La búsqueda de `Naguanagua`, `alcald` y de nombres de cargo en la lógica de comisiones da 0 (se repite al cierre, §6).

### Componentes reutilizables (REUSABLE_COMPONENTS)

- Comisión, miembros, inhibiciones e historia de PROC-02.
- Funcionarios y asignaciones de ORG-04: `_ejerce_cargo`.
- Competencias por versión de cargo: `service_autoridad.competencias_en_vigor`.
- Unidades (`gov_units`).
- Actos (DOC-02).
- Tipos documentales y `DocumentLink` (Spec 046), con su registro `RESOURCE_KINDS`.
- CTL-01: `evaluar_antes_de_actuar` con PROC02_ACTIVAR, PROC03_ABRIR y PROC03_RECOMENDAR.
- PROC-11: `verificar_antes_de_asumir_funcion`.
- La política de causado de BUD-09 como patrón hermano: estados, documentos por etapa e historia con instantánea.

### Superficies que faltan (MISSING_PRODUCT_SURFACES)

- Pantallas de políticas de comisión: lista, ficha, formulario e historia.
- Selección de la política al crear una comisión.
- Panel «Regla aplicada» en la comisión.
- Documentos de constitución.
- Marca de presidencia.
- Inhibición ligada a un expediente.
- Apertura y recomendación sin comisión.

### Contradicciones y cuestiones abiertas

- **Contradicciones:** 0.
- **Cuestiones materiales:** las cuatro se resolvieron con la dueña el 2026-11-17 (§4).

## 2. Clasificación de reglas

| Regla | Clase | Dónde vive |
|---|---|---|
| Una versión vigente por código; historia inmutable; la comisión formalizada congela su regla; aislamiento de tenant y empresa; concurrencia optimista | PLATFORM_INVARIANT | Esquema y servicio |
| El secretario no vota (LCP art. 14) | LEGAL_MANDATORY | Piso LCP |
| Número impar de principales, las tres áreas, suplente por principal, secretario y su suplente (LCP art. 14) | LEGAL_MANDATORY | Piso `LCP_ART14`, versión `LCP-2014+RLCP-2009`, con fuente. Aplica cuando la política declara esa base |
| Acto de creación eficaz y publicado en Gaceta (RLCP art. 15) | LEGAL_MANDATORY | Piso `LCP_ART14` |
| Un miembro con inhibición aceptada no actúa en ese procedimiento (RLCP art. 18) | LEGAL_MANDATORY | Autoridad |
| Mínimo y máximo de principales; requisitos por área, cargo, unidad, competencia o funcionario; presidencia; quórum; regla de decisión; voto del presidente; voto dirimente; base de la decisión; documentos por etapa; vigencia; fundamento; procesos en que aplica | INSTITUTIONAL_POLICY | Política del ente, con versiones |
| Código, nombre, descripción y orden de los requisitos | OPERATIONAL_CONFIGURATION | Política del ente |

El piso legal **no se puede rebajar**:

- una política con base `LCP_ART14` no puede desactivar ninguna de sus exigencias;
- el ente sí puede endurecerlas.

## 3. Requisitos

- **FR-CP-01 · Política de comisión.**
  - Entidad del ente (tenant y empresa) con estas secciones:
    - identidad: código, nombre y descripción;
    - tipo de comisión al que aplica: permanente, temporal o cualquiera;
    - procesos: apertura (PROC-07) y recomendación (PROC-08);
    - base normativa y fundamento;
    - acto que la adopta (opcional);
    - vigencia;
    - composición: mínimo y máximo de principales, impar, suplente por principal, secretario, suplente del secretario y presidencia;
    - requisitos de integración;
    - quórum y decisión;
    - documentos por etapa.
  - Estados: BORRADOR → VIGENTE → CERRADA.
  - **Validaciones al activar:**
    - la vigencia es coherente y no se solapa con otra versión vigente del mismo código;
    - el fundamento es obligatorio;
    - con base `LCP_ART14`, las exigencias del piso están activas;
    - el quórum y la decisión son coherentes con su tipo.
  - Solo se edita en BORRADOR.
- **FR-CP-02 · Versiones.**
  - «Nueva versión» copia una política vigente o cerrada en un BORRADOR con el mismo código y `numero_version + 1`.
  - Al activarla, la versión vigente anterior pasa a CERRADA con el motivo «Sustituida por la versión N».
  - Hay a lo sumo una versión VIGENTE por código; lo garantiza un índice único parcial.
  - Cada operación escribe la historia con su instantánea: CREADA, EDITADA, ACTIVADA, CERRADA, SUSTITUIDA y NUEVA_VERSION. La historia es inmutable en PostgreSQL.
- **FR-CP-03 · Requisitos de integración.** Cada requisito tiene:
  - etiqueta, función (MIEMBRO o SECRETARIO) y condición (PRINCIPAL, SUPLENTE o CUALQUIERA);
  - tipo, que es uno de estos:
    - `AREA`: el área LCP;
    - `CARGO`: el funcionario ejerce el cargo en la fecha (ORG-04);
    - `UNIDAD`: ejerce un cargo de esa unidad;
    - `COMPETENCIA`: un cargo que ejerce tiene en vigor esa acción y materia;
    - `FUNCIONARIO`: designación nominativa;
  - un mínimo y un máximo opcional.

  Los miembros se resuelven contra la organización real del ente en la fecha. Nunca se comparan nombres de cargo.
- **FR-CP-04 · Quórum y decisión.**
  - **Tipos** de quórum y de decisión: `ABSOLUTE_COUNT` (cantidad), `SIMPLE_MAJORITY`, `QUALIFIED_MAJORITY` (fracción n/d, mayor que 1/2 y como mucho 1) o `UNANIMITY`.
  - **Base de la decisión:** `MIEMBROS_CON_VOTO` o `ASISTENTES_CON_VOTO`.
  - **Presidente:** puede votar o no, y tener voto dirimente en caso de empate (solo con presidencia exigida).
  - **Votos:** votan los principales; un principal cuenta presente si asiste él o su suplente.
  - **Exclusiones:** no votan el secretario, el presidente cuando la política dice que no vota, ni un miembro inhibido en el expediente.
  - **Umbral:**

    | Tipo | Umbral |
    |---|---|
    | `ABSOLUTE_COUNT` | La cantidad |
    | `SIMPLE_MAJORITY` | `base // 2 + 1` |
    | `QUALIFIED_MAJORITY` | `ceil(base · n / d)` |
    | `UNANIMITY` | `base` |

    El umbral mínimo es 1.
- **FR-CP-05 · Autoridad única.**
  - `service_comision_regla.py` es el único sitio que sabe:
    - qué regla rige una comisión;
    - qué le falta para formalizarse;
    - cuál es el quórum y si una decisión alcanza la mayoría;
    - qué miembros están inhibidos;
    - qué documentos faltan.
  - PROC-02, PROC-07 y PROC-08 la consumen y no calculan quórum ni composición propios: `COMMISSION_POLICY_AUTHORITIES=1`.
- **FR-CP-06 · Comisión desde la política (PROC-02).**
  - Una comisión nueva elige una política VIGENTE del mismo tipo.
  - Al activarse congela la regla (`regla`, `policy_id`, `policy_version`). La regla no cambia aunque después cambien la política, el cargo o la unidad.
  - `faltantes` lo calcula la autoridad: piso, cardinalidad, requisitos, presidencia, acto y documentos de CONSTITUCION vinculados a la comisión.
  - La pantalla muestra los faltantes antes de activar.
  - Un miembro puede marcarse como presidente.
  - **Comisiones vigentes sin política (legado):** conservan la regla histórica, que se muestra de forma explícita como «Regla anterior a las políticas: mayoría simple de los principales con voto (OD-PROC07-01)».
- **FR-CP-07 · Inhibición por expediente.**
  - La inhibición puede ligarse a un expediente.
  - Aceptada, excluye al miembro de la apertura y de la recomendación de ese expediente. Actúa su suplente.
- **FR-CP-08 · PROC-07.**
  - **Con comisión:** la apertura usa la regla congelada (quórum), excluye a los inhibidos y exige los documentos de la etapa APERTURA vinculados al expediente. El acta guarda la regla aplicada.
  - **Sin comisión declarada:** la apertura la hacen los responsables vigentes del expediente (RESPONSABLE o SUSTANCIACIÓN), en modo `UNIDAD_CONTRATANTE`, sin quórum. El acta registra el motivo de no intervención (corrige D1).
- **FR-CP-09 · PROC-08.**
  - **Con comisión:** la recomendación usa la regla congelada. El quórum se calcula sobre los asistentes (por defecto, los firmantes) y la decisión sobre los firmantes, según la base. Se excluye a los inhibidos y se exigen los documentos de RECOMENDACION.
  - **Sin comisión:** firman los responsables vigentes del expediente, en modo `UNIDAD_CONTRATANTE` (corrige D2).
- **FR-CP-10 · Permisos.**
  - Se añade la acción nueva `gobierno_comisiones:configure`, que crea, edita y versiona políticas. Va sin MFA, como `manage`.
  - Activar y cerrar una política usa `gobierno_comisiones:activate` y `:close`, que ya exigen MFA.
  - Ver usa `:view`.
  - Ningún permiso nombra un cargo.
- **FR-CP-11 · Auditoría.** Eventos nuevos:
  - `GOV_COMMISSION_POLICY_CREATED`, `_UPDATED`, `_ACTIVATED`, `_CLOSED` y `_VERSIONED`;
  - `GOV_COMMITTEE_MEMBER_PRESIDENCY_SET`.

  La activación de la comisión registra la política y su versión. Todos los eventos van al catálogo de auditoría.
- **FR-CP-12 · Pantallas.**
  - Gobierno · Contrataciones › «Políticas de comisión»: lista con filtro, formulario (todas las secciones de FR-CP-01), ficha con activar, cerrar, nueva versión e historia.
  - En «Comisiones»: política, «Regla aplicada», faltantes legibles, presidencia, documentos e inhibición con expediente.
  - En el expediente: apertura y recomendación sin comisión, y contador de quórum según la regla del backend.
- **FR-CP-13 · Aislamiento.** Políticas, requisitos, documentos e historia llevan `company_id`. Otra empresa u otro tenant no las ve ni las usa.

## 4. Decisiones de la dueña (2026-11-17, AskUserQuestion)

| Id | Decisión |
|---|---|
| OD-CP-01 | Tope global de DeepSeek de 18 llamadas en este ciclo, con RETRY_MAX 2 por subproblema |
| OD-CP-02 | Sin comisión, actúan y firman los responsables del expediente (RESPONSABLE o SUSTANCIACIÓN). No aplica quórum y el acta registra el motivo |
| OD-CP-03 | La LCP art. 14 es un piso legal versionado. El ente lo puede endurecer pero no rebajar |
| OD-CP-04 | Las comisiones vigentes sin política conservan su regla histórica, mostrada de forma explícita. Las nuevas exigen política. Sin backfill |

## 5. Gate de entrada

| Comprobación | Resultado |
|---|---|
| BLOCKER | 0 |
| CRITICAL_CONTRADICTIONS | 0 |
| OWNER_CONFLICT | 0 |
| UNKNOWN_MATERIAL_REQUIREMENTS | 0 |
| UNRESOLVED_ARCHITECTURE_CONFLICT | 0 |
| MATERIAL OQ | 0 (OD-CP-01..04) |

## 6. Auditoría de hardcode al cierre

Se ejecuta la búsqueda del §5 del encargo sobre los ficheros del ciclo. El resultado se registra en `evidence/commission-policy/HARDCODE_AUDIT.md`.

## 7. Fuera de alcance

- H6, la autoactivación de la comisión. Es un control de cuatro ojos ya existente. Pasarlo a una regla CTL-01 cambia el comportamiento de los entes actuales y queda como deuda de PROC-02: `OBS-PROC02-SELF-ACTIVATION-CTL01-01`.
- Las causales legales de desierta, rechazo y nulidad (LCP arts. 76, 112 y 113). Son LEGAL_MANDATORY y no tienen que ver con la comisión.
- Agendas, convocatorias y actas de sesión como entidades propias. Por ahora los documentos se exigen por tipo documental.
- El motor de procesos.
