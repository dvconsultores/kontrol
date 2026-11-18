# Plan · PROC-07/PROC-08-COMMISSION-POLICY

## Migración `0124_gov_commission_policy`

La migración va detrás de `0123_gov_bud09_causado`. Es CLAUDE_ONLY.

### Tablas nuevas

**`gov_commission_policies`**

Lleva `VersionMixin` (`version`, concurrencia optimista) y `created_by`.

| Columna | Tipo | Regla |
|---|---|---|
| `company_id` | FK | — |
| `codigo` | String(20) | — |
| `numero_version` | Integer | ≥ 1 |
| `nombre` | String(200) | — |
| `descripcion` | Text | Opcional |
| `tipo_comision` | — | `PERMANENTE`, `TEMPORAL` o `CUALQUIERA` |
| `aplica_apertura`, `aplica_recomendacion` | Boolean | Al menos una verdadera |
| `base_normativa` | — | `LCP_ART14` o `NINGUNA` |
| `fundamento` | String(2000) | Obligatorio fuera de BORRADOR |
| `act_id` | FK `gov_acts` | Opcional |
| `vigente_desde` | Date | — |
| `vigente_hasta` | Date | Opcional; si existe, ≥ `vigente_desde` |
| `estado` | — | `BORRADOR`, `VIGENTE` o `CERRADA` |
| `min_principales` | Integer | ≥ 1 |
| `max_principales` | Integer | Opcional; ≥ `min_principales` |
| `exige_impar`, `suplente_por_principal`, `exige_secretario`, `exige_suplente_secretario`, `exige_presidente` | Boolean | — |
| `quorum_tipo` | — | Uno de `TIPOS_MAYORIA` |
| `quorum_cantidad`, `quorum_numerador`, `quorum_denominador` | Integer | Opcionales |
| `decision_tipo` | — | Uno de `TIPOS_MAYORIA` |
| `decision_cantidad`, `decision_numerador`, `decision_denominador` | Integer | Opcionales |
| `decision_base` | — | `MIEMBROS_CON_VOTO` o `ASISTENTES_CON_VOTO` |
| `presidente_vota`, `presidente_dirimente` | Boolean | — |
| `acto_requerido` | Boolean | — |
| `acto_medio` | — | Opcional; uno de `MEDIOS_EFICACIA` |
| `version_anterior_id` | FK propia | Opcional |
| `activada_por`, `activada_en`, `cerrada_por`, `cerrada_en`, `motivo_cierre` | — | Trazas de activación y cierre |

Restricciones:

- `UNIQUE(company_id, codigo, numero_version)`;
- índice único parcial `(company_id, codigo) WHERE estado = 'VIGENTE'`.

Las restricciones CHECK (`TIPOS_MAYORIA` = `ABSOLUTE_COUNT`, `SIMPLE_MAJORITY`, `QUALIFIED_MAJORITY`, `UNANIMITY`) son estas:

- `quorum_tipo <> 'ABSOLUTE_COUNT'` o `quorum_cantidad >= 1`;
- `quorum_tipo <> 'QUALIFIED_MAJORITY'` o la fracción cumple `2·n > d` y `n <= d`;
- las mismas dos reglas para `decision_*`;
- `presidente_dirimente` exige `exige_presidente`;
- `estado = 'BORRADOR'` o `fundamento IS NOT NULL`;
- `estado = 'CERRADA'` exige `cerrada_en` y `motivo_cierre`.

**`gov_commission_policy_requirements`**

| Columna | Tipo | Regla |
|---|---|---|
| `policy_id`, `company_id` | FK | — |
| `orden` | Integer | ≥ 1 |
| `etiqueta` | String(200) | — |
| `funcion` | — | `MIEMBRO` o `SECRETARIO` |
| `condicion` | — | `PRINCIPAL`, `SUPLENTE` o `CUALQUIERA` |
| `tipo` | — | `AREA`, `CARGO`, `UNIDAD`, `COMPETENCIA` o `FUNCIONARIO` |
| `area` | — | Opcional |
| `position_id` | FK `gov_positions` | Opcional |
| `unit_id` | FK `gov_units` | Opcional |
| `competencia_accion`, `competencia_materia` | — | Opcionales |
| `official_id` | FK `gov_officials` | Opcional |
| `minimo` | Integer | ≥ 0 |
| `maximo` | Integer | Opcional; ≥ `minimo` |

Una restricción CHECK por tipo exige que esté presente exactamente la referencia de ese tipo:

| `tipo` | Referencia |
|---|---|
| `AREA` | `area` |
| `CARGO` | `position_id` |
| `UNIDAD` | `unit_id` |
| `COMPETENCIA` | `competencia_accion` y `competencia_materia` |
| `FUNCIONARIO` | `official_id` |

**`gov_commission_policy_documents`**

| Columna | Tipo | Regla |
|---|---|---|
| `policy_id`, `company_id` | FK | — |
| `document_type_id` | FK `document_types` | — |
| `etapa` | — | `CONSTITUCION`, `APERTURA` o `RECOMENDACION` |
| `obligatorio` | Boolean | — |
| `condicion` | String(300) | Opcional |

Restricción: `UNIQUE(policy_id, document_type_id, etapa)`.

**`gov_commission_policy_history`**

| Columna | Tipo | Regla |
|---|---|---|
| `policy_id`, `company_id` | FK | — |
| `evento` | — | `CREADA`, `EDITADA`, `ACTIVADA`, `CERRADA`, `SUSTITUIDA` o `NUEVA_VERSION` |
| `version` | Integer | — |
| `instantanea` | JSON | — |
| `actor_id` | — | — |

En PostgreSQL tiene disparadores de inmutabilidad (UPDATE, DELETE y TRUNCATE).

### Columnas nuevas en tablas existentes

| Tabla | Cambio |
|---|---|
| `gov_procurement_committees` | `policy_id` (FK, opcional), `policy_version` (int, opcional), `regla` (JSON, opcional) |
| `gov_procurement_committee_members` | `preside` (bool, false). Índice único parcial: un presidente vigente por comisión |
| `gov_procurement_committee_conflicts` | `file_id` (FK `gov_procurement_files`, opcional) |
| `gov_procurement_openings` | `committee_id` pasa a opcional. `modo` (`COMISION` o `UNIDAD_CONTRATANTE`, por defecto `COMISION`). `miembros_con_voto`, `asistentes_con_voto` y `quorum_requerido` pasan a opcionales. `regla` (JSON, opcional). CHECK: con `modo = 'COMISION'` hay comisión y quórum; con `modo = 'UNIDAD_CONTRATANTE'` no hay ninguno |
| `gov_procurement_opening_responsibles` (nueva) | `opening_id`, `responsible_id` (FK `gov_procurement_file_responsibles`), `official_id`, `rol`. `UNIQUE(opening_id, responsible_id)`. Asistentes de una apertura sin comisión |
| `gov_procurement_recommendation_responsibles` (nueva) | Lo mismo para la recomendación sin comisión |
| `gov_procurement_eval_contributions` y `gov_procurement_eval_results` | `member_id` pasa a opcional y se añade `responsible_id` (FK, opcional). CHECK `actor`: exactamente uno de los dos. En aportes, índice único parcial raíz por responsable |

### Permisos, documentos y SoD

- **Permiso:** `gobierno_comisiones:configure`, concedido al rol `FUNCIONAL_COMPLETO`.
- **Documentos:** `RESOURCE_KINDS` admite `GovernmentProcurementCommittee`, con permiso `gobierno_comisiones:view`.
- **SoD:** sin cambios. La comisión sigue sometida a CTL-01 (PROC02_ACTIVAR, PROC03_ABRIR y PROC03_RECOMENDAR) y a PROC-11 (función EVALUADOR). No hay una segunda autoridad SoD.

## Autoridad `service_comision_regla.py`

| Función | Qué hace |
|---|---|
| `PISO_LCP_ART14` | Exigencias del piso, versión `LCP-2014+RLCP-2009` y fuente |
| `REGLA_LEGADO` | La regla histórica de OD-PROC07-01 |
| `instantanea(db, politica)` | Devuelve el dict de la regla, con requisitos, documentos y etiquetas |
| `regla_de(comision)` | `comision.regla` o `REGLA_LEGADO` |
| `umbral(tipo, cantidad, n, d, base)` | Calcula el umbral según FR-CP-04 |
| `faltantes(db, ctx, regla, comision, miembros, fecha)` | Lista de lo que impide formalizar |
| `inhibidos(db, ctx, comision_id, file_id)` | Ids de miembros con inhibición ACEPTADA en ese expediente |
| `evaluar_quorum(regla, miembros, presentes, inhibidos)` | Quórum de la sesión |
| `evaluar_decision(regla, miembros, presentes, a_favor, inhibidos)` | Si la decisión alcanza la mayoría |
| `documentos_faltantes(db, ctx, regla, etapa, resource_type, resource_id)` | Documentos de la etapa que faltan |

## Servicio, API y esquemas de políticas

- **Ficheros:** `service_comision_politicas.py`, `schemas_comision_politicas.py` y `api_comision_politicas.py`, bajo `/government/commission-policies`.
- **Rutas:**

  | Método y ruta | Qué hace | Permiso |
  |---|---|---|
  | `GET /` | Lista, con filtros `estado` y `q` | `:view` |
  | `GET /opciones` | Catálogos, más cargos, unidades, funcionarios y tipos documentales del ente | `:view` |
  | `GET /{id}` | Ficha, con requisitos, documentos e historia | `:view` |
  | `POST /` | Crea | `:configure` |
  | `PUT /{id}` | Edita | `:configure` |
  | `POST /{id}/activar` | Activa | `:activate` (MFA) |
  | `POST /{id}/cerrar` | Cierra | `:close` (MFA) |
  | `POST /{id}/nueva-version` | Nueva versión | `:configure` |

## Pantallas

- **Políticas de comisión** (nuevas):
  - `PoliticasComisionPage` (lista);
  - `PoliticaComisionFormPage` (crear y editar);
  - `PoliticaComisionPage` (ficha e historia).
- **Rutas:** `gobierno/contrataciones/politicas-comision`, con `/nueva`, `/:id` y `/:id/editar`. Se declaran en el menú de Contrataciones y en `pantallas.ts`.
- **Cambios en pantallas existentes:**
  - `ComisionFormPage`: selector de política;
  - `ComisionPage`: «Regla aplicada», presidencia, documentos de constitución (`AdjuntosPanel`) e inhibición con expediente;
  - `ExpedienteEvaluacion` y `ExpedienteDecision`: modo sin comisión y contador de quórum que sale de la regla del backend.

**Decisión de diseño (2026-11-17):** los asistentes y firmantes sin comisión van en tablas propias. Así no se alteran CHECK existentes con nombres truncados por hash y la cadena de migraciones sigue compilando en modo offline.
