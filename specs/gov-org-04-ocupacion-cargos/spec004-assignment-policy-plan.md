# Plan · ORG-04-AUTHORITY-ASSIGNMENT-POLICY

## Migración `0126_gov_assignment_policy` (CLAUDE_ONLY)

### `gov_assignment_policies`

Lleva `VersionMixin` y `created_by`.

| Columna | Regla |
|---|---|
| `company_id`, `codigo` String(20), `numero_version` ≥ 1, `nombre` String(200), `descripcion` Text | — |
| `figura` | Una de `FIGURAS_ASIGNACION` |
| `fundamento` String(2000) | Obligatorio fuera de BORRADOR |
| `act_id` | Opcional |
| `vigente_desde`, `vigente_hasta` | `vigente_hasta` ≥ `vigente_desde` |
| `estado` | BORRADOR, VIGENTE o CERRADA |
| `exige_fin` | bool, por defecto false |
| `max_dias` | ≥ 1, opcional |
| `acto_medio` | Uno de `MEDIOS_EFICACIA`, opcional |
| `emisor_tipo` | CUALQUIERA, CARGO o COMPETENCIA, con `emisor_position_id`, `emisor_competencia_accion` y `emisor_competencia_materia`. CHECK de coherencia |
| `autorizacion_requerida` | bool |
| `autorizacion_etiqueta` | String(120) |
| `autorizacion_ambito` | TODAS o MAXIMA_AUTORIDAD |
| `autorizacion_mas_de_dias` | ≥ 0, opcional. CHECK: si se exige la autorización, hay etiqueta y ámbito |
| `prohibe_avocacion` | bool |
| `version_anterior_id`, `activada_por`/`_en`, `cerrada_por`/`_en`, `motivo_cierre` | Trazas de versión, activación y cierre. CHECK de cierre |

Restricciones: `UNIQUE(company_id, codigo, numero_version)` e índice único parcial `(company_id, codigo) WHERE estado = 'VIGENTE'`.

### Tablas auxiliares

| Tabla | Columnas | Restricciones |
|---|---|---|
| `gov_assignment_policy_competencies` | `policy_id`, `company_id`, `accion`, `materia` | `UNIQUE(policy_id, accion, materia)` |
| `gov_assignment_policy_documents` | `policy_id`, `company_id`, `document_type_id`, `etapa` (ACTIVACION o REVOCACION), `obligatorio` | `UNIQUE(policy_id, document_type_id, etapa)` |
| `gov_assignment_policy_history` | `policy_id`, `company_id`, `evento` (CREADA, EDITADA, ACTIVADA, CERRADA, SUSTITUIDA o NUEVA_VERSION), `version`, `instantanea` JSON, `actor_id` | Inmutable en PG |

### Cambios en `gov_assignments`

- Columnas nuevas: `policy_id` (FK, opcional), `policy_version` y `regla` (JSON, opcional).
- `autorizacion_concejo` pasa a `autorizacion_especial`.
- El disparador `kontrol_gov_asignacion_no_editable` también protege `policy_id`, `policy_version` y `regla::text` fuera de BORRADOR.

### Permisos y documentos

- Permiso `gobierno_ocupacion:configure`, concedido a FUNCIONAL_COMPLETO y en la lista MFA estándar.
- `GovernmentAssignment` pasa a ser ResourceKind, con permiso `gobierno_ocupacion:view`.

## Autoridad `service_asignacion_regla.py`

### Pisos y regla

- `PISOS`: lista de dicts con estas claves:

  | Clave | Contenido |
  |---|---|
  | `codigo` | Código del piso |
  | `fuente` | Texto de la norma |
  | `version` | Versión del piso |
  | `vigente_desde` | date |
  | `niveles` | `None` para todos, o una tupla |
  | `figuras` | Tupla de figuras |
  | `exigencias` | Dict |

- `regla_base(nivel, figura, fecha, origen)` y `regla_aplicable(db, ctx, figura, fecha)` devuelven la **regla**, un dict con estas claves:

| Clave | Contenido |
|---|---|
| `origen` | POLITICA, PISO_LEGAL o HISTORICA |
| `politica` | `{id, codigo, numero_version, nombre}` o `None` |
| `regla_version` | `"{codigo} v{n}"` o «Pisos legales» |
| `figura`, `nivel_territorial` | — |
| `pisos` | `[{codigo, fuente, version}]` |
| `fundamentos` | Lista de textos: las fuentes de los pisos más el fundamento de la política |
| `exige_fin` | El de la figura **o** el de la política **o** `max_dias` no nulo |
| `limites` | `[{valor, unidad: DIAS o ANIOS, ambito: TODAS o MAXIMA_AUTORIDAD, fuente}]`: LEFP `1 ANIOS`; LOPPM `90 DIAS` (MAXIMA_AUTORIDAD); política `max_dias DIAS` |
| `acto_medio` | GACETA, por la LOAP en una delegación, o el de la política |
| `emisor` | `{regla: DELEGANTE, OTRO_CARGO o CUALQUIERA, tipo: CUALQUIERA, CARGO o COMPETENCIA, position_id, accion, materia}` |
| `autorizaciones` | Lista `[{etiqueta, ambito, mas_de_dias, fuente}]`: una por piso y otra por la política. Se exige cada una que aplique por ámbito y días; un solo campo `autorizacion_especial` registra la referencia (decisión de implementación, 2026-11-18: una lista evita endurecer de más al fusionar ámbitos y umbrales distintos) |
| `competencias_permitidas` | `[{accion, materia}]` o `None` |
| `admite_avocacion` | True solo en las figuras de DELEGACION sin `prohibe_avocacion` |
| `documentos` | `[{document_type_id, document_type_nombre, etapa, obligatorio}]` |

### Funciones

| Función | Qué hace |
|---|---|
| `politica_aplicable(db, ctx, figura, fecha)` | Política VIGENTE de la figura cuya vigencia cubre `fecha` |
| `instantanea(db, ctx, politica, nivel, fecha)` | Pisos más la política, fusionados |
| `regla_de(db, ctx, asignacion)` | `asignacion.regla` o `regla_base(..., origen="HISTORICA")` |
| `verificar(db, ctx, regla, datos, acto, cargo)` | Valida límites, autorización, medio, emisor y competencias permitidas. Códigos: GOV_ASSIGNMENT_LIMIT_EXCEEDED, GOV_ASSIGNMENT_ACT_INVALID, GOV_ASSIGNMENT_ISSUER_INVALID y GOV_ASSIGNMENT_NOT_DELEGABLE |
| `documentos_faltantes(db, company_id, regla, etapa, asignacion_id)` | Documentos obligatorios que faltan en una etapa |

## Integración en `service_ocupacion`

- **Catálogo:** `FIGURAS` pierde `base_legal` y `exige_gaceta`. `FiguraOut` pierde `base_legal`.
- **`validar(db, ctx, datos)`:** obtiene la regla con `regla_aplicable` y delega en `verificar` los pasos 3 (medio y emisor de la delegación), 6, 7 y la lista de competencias. Quedan en ORG-04 las invariantes de plataforma y la LOAP estructural: no subdelegar, dependencia y solo competencias propias. Sus mensajes citan la fuente que da el piso.
- **`crear` y `editar`:** guardan `policy_id`, `policy_version` y `regla` en el borrador.
- **`activar`:** recalcula la regla, la congela y exige los documentos de ACTIVACION.
- **`revocar`:** usa `regla_de` y exige los documentos de REVOCACION.
- **`avocar`:** exige `admite_avocacion`.
- **Detalle:** devuelve `regla`, `regla_congelada` y `politica`.
- **Nueva ruta:** `GET /gobierno/ocupacion/regla?figura=&desde=` → `ReglaAsignacionOut`.

## Políticas: servicio, esquemas y API

Siguen el patrón de las políticas de comisión. Prefijo: `/gobierno/ocupacion/politicas`.

| Ruta | Permiso |
|---|---|
| `GET /` (filtros `estado`, `figura` y `q`), `GET /opciones`, `GET /{id}` | `gobierno_ocupacion:view` |
| `POST /`, `PUT /{id}`, `POST /{id}/nueva-version` | `:configure` |
| `POST /{id}/activar` | `:activate` (MFA) |
| `POST /{id}/cerrar` | `:revoke` (MFA) |

La activación aplica D-AP-02 y D-AP-03, y exige el fundamento.

## Frontend

- **Políticas:** `politicasAsignacion.ts`, `PoliticasAsignacionPage`, `PoliticaAsignacionPage` y `PoliticaAsignacionFormPage`, en `src/modules/gobierno/ocupacion/`.
  - Rutas: `gobierno/ocupacion/politicas`, con `/nueva`, `/:id` y `/:id/editar`.
  - Menú: «Políticas de asignación», dentro de Gobierno y junto a «Ocupación de cargos».
  - Se declaran en `pantallas.ts`.
- **`NuevaAsignacionPage`:** pide la regla con la figura y la fecha `desde`, muestra «Regla aplicada» con origen, fundamentos y requisitos, y presenta la autorización solo si la regla la exige y su ámbito y sus días aplican.
- **`AsignacionPage`:** «Regla aplicada» (congelada o no), autorización con la etiqueta de la regla, documentos (`AdjuntosPanel`) y avocación solo si se admite.
