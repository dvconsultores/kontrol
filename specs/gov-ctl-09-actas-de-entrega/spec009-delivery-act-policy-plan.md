# Plan · CTL-09-DELIVERY-ACT-POLICY

## Migración `0127_gov_handover_policy` (CLAUDE_ONLY)

| Tabla | Columnas | Restricciones |
|---|---|---|
| `gov_handover_policies` | `company_id`, `codigo` (20), `numero_version`, `nombre` (200), `descripcion`, `fundamento` (2000), `act_id`, `vigente_desde`, `vigente_hasta`, `estado` (BORRADOR, VIGENTE o CERRADA), `numeracion_patron` (60), `testigos_en_entrega` (0..5), `version_anterior_id`, trazas de activación y cierre, `version` | `UNIQUE(company_id, codigo, numero_version)`; índice único parcial `(company_id) WHERE estado = 'VIGENTE'` (D-AE-03); fundamento fuera de BORRADOR; CHECK de cierre |
| `gov_handover_policy_bindings` | `supuesto` (N34_ART11..17), `alcance` (ENTE o UNIDAD), `unit_id` | `(alcance = 'UNIDAD') = (unit_id IS NOT NULL)` |
| `gov_handover_policy_requirements` | `codigo` (8), `titulo`, `evidencia` (DOCUMENTO, CERTIFICACION, DECLARACION o DATO), `obligatorio`, `ambito` (TODAS, ENTE o UNIDAD), `supuesto`, `document_type_id`, `fuente` | `UNIQUE(policy_id, codigo)` |
| `gov_handover_policy_deadlines` | `hito` (ELABORACION o REMISION_UAI), `valor` ≥ 1, `unidad` (DIAS_HABILES o DIAS_CONTINUOS), `fuente` | `UNIQUE(policy_id, hito)` |
| `gov_handover_policy_history` | `evento`, `version`, `instantanea`, `actor_id` | Inmutable en PG |

Cambios en tablas existentes:
- **`gov_handover_acts`:** `policy_id` (FK), `policy_version` y `regla` (JSON). El disparador `kontrol_gov_handover_act_immutable` protege también estos tres campos una vez suscrita el acta.
- **`gov_handover_annexes`:** `origen`, `supuesto`, `fuente`, `evidencia`, `declaracion` y `document_type_id`.

Permisos: `gobierno_actas:configure` (estándar) y `:activate` (MFA), concedidos a FUNCIONAL_COMPLETO.

## Autoridad `service_actas_regla.py` (CLAUDE)

Constantes:

| Constante | Contenido |
|---|---|
| `NORMA_N34` | Norma, instrumento, gaceta, versión y vigencia |
| `SUPUESTOS` | Arts. 11–17, con su vínculo (UNIVERSAL o DECLARADO), niveles, ámbitos, nota y anexos |
| `TESTIGOS_LEGALES` | Art. 9 |
| `PLAZOS_LEGALES` | Arts. 4, 21 y 22 |
| `PATRON_POR_DEFECTO` | Patrón de numeración `AE-{ANIO}-{NUMERO:4}` |

Funciones:

| Función | Qué hace |
|---|---|
| `motivo_vinculo_invalido(nivel, supuesto, alcance)`, `motivo_plazo_invalido(hito, valor, unidad)`, `motivo_codigo_requisito_invalido(codigo)`, `motivo_patron_invalido(patron)` | Validaciones del piso legal; devuelven `None` o el motivo |
| `vista_previa(patron, anio)`, `formatear_codigo`, `siguiente_codigo(db, ctx, regla, anio)` | Numeración |
| `politica_aplicable(db, ctx, fecha)` | Política VIGENTE cuya vigencia cubre la fecha |
| `instantanea(db, ctx, politica, ambito=, unit_id=, fecha=)`, `regla_aplicable(...)` | La regla aplicada |
| `regla_de(db, acta)` | La regla congelada, o la HISTORICA |
| `validar_testigos(regla, modalidad, testigos, auditor_valido)` | Testigos |
| `anexo_resuelto(anexo, tipos)`, `anexos_pendientes(db, company_id, anexos)` | Resolución de anexos según la evidencia |
| `responsabilidad(db, ctx, ...)` | Responsabilidad, con ORG-04 `detalle(...)["situacion"]` |
| `plazos(acta, regla, hoy)` | Estado de cada plazo |

Claves de la **regla**:

| Clave | Contenido |
|---|---|
| `origen` | POLITICA, LEGAL o HISTORICA, con su etiqueta |
| `politica` | La política aplicada |
| `regla_version` | Versión de la regla |
| `norma` | La norma N34 |
| `fecha` | Fecha de corte |
| `ambito`, `unit_id`, `unidad` | Ámbito y unidad del acta |
| `nivel_territorial`, `forma_organizativa` | Datos del ente |
| `supuestos` | `[{codigo, articulo, titulo, sujeto, vinculo, alcance, motivo, nota}]` |
| `anexos` | `[{codigo, titulo, obligatorio, generable, evidencia, fuente, origen, supuesto, document_type_id, document_type_nombre}]` |
| `testigos` | `{levantada_por_receptor, entrega: {minimo, fuente}}` |
| `plazos` | `[{hito, valor, unidad, base, fuente, origen}]` |
| `numeracion` | `{patron, origen}` |
| `fundamentos` | Fundamentos de la regla |
| `avisos` | Avisos para el usuario |
| `responsabilidad` | Solo en el acta |

## Integración en `service_actas` (CLAUDE)

- **Crear y editar:** resuelven la regla y la responsabilidad, validan los testigos con la regla, numeran con su patrón, fijan `policy_id`, `policy_version` y `regla`, y sincronizan los anexos.
- **Anexos:** `PUT` admite `declaracion` (solo en DECLARACION y DATO). Si el requisito fija un tipo documental, rechaza documentos de otro tipo.
- **Suscribir:** pendientes según la evidencia; la instantánea incluye la `regla` y los campos nuevos del anexo; el PDF cita la regla aplicada.
- **Ficha:** `regla`, `regla_congelada`, `responsabilidad`, `plazos` y los campos nuevos del anexo.
- **A11_2:** usa ORG-04 `_vigentes_en`. Se eliminan `ANEXOS_CATALOGO`, `ANEXOS_MUNICIPALES`, `_siguiente_codigo`, `_validar_testigos`, `_estado_vigente` y `_asignacion_al_corte`.
- **Nueva ruta:** `GET /gobierno/actas-entrega/regla?assignment_id=&fecha_corte=`.

## Políticas: servicio, esquemas y API (DEEPSEEK, patrón ORG-04)

Prefijo: `/gobierno/actas-entrega/politicas`.

| Ruta | Permiso |
|---|---|
| `GET /` (filtros `estado` y `q`), `GET /opciones`, `GET /numeracion/vista-previa?patron=&anio=`, `GET /{id}` | `:view` |
| `POST /`, `PUT /{id}` (If-Match), `POST /{id}/nueva-version` | `:configure` |
| `POST /{id}/activar` (If-Match) y `POST /{id}/cerrar` | `:activate` (MFA) |

- **Activar:** exige el fundamento y vuelve a validar los vínculos con el nivel del ente; la política VIGENTE anterior queda CERRADA (SUSTITUIDA).
- **Errores:** `GOV_HANDOVER_POLICY_INVALID` (422, con `field_errors` o `motivos`), `GOV_HANDOVER_POLICY_NOT_FOUND`, `GOV_HANDOVER_POLICY_STATE` y `VERSION_CONFLICT`.
- **Auditoría:** `GOV_HANDOVER_POLICY_CREATED`, `_UPDATED`, `_ACTIVATED`, `_CLOSED` y `_VERSIONED`.

## Frontend

- **Políticas** (DEEPSEEK, patrón ORG-04): `actas/politicasActa.ts` con los tipos (Claude), más `PoliticasActaPage`, `PoliticaActaPage` y `PoliticaActaFormPage`.
  - Rutas: `gobierno/actas-entrega/politicas`, con `/nueva`, `/:id` y `/:id/editar`.
  - Menú: «Políticas de actas», junto a «Actas de entrega».
  - Se declaran en `pantallas.ts` y entran en el humo UAT (junto con «Políticas de asignación», que faltaba).
- **`NuevaActaEntregaPage`:** consulta `/regla` con la ocupación y la fecha de corte, y muestra «Regla aplicada», los supuestos con su motivo, los anexos, los testigos exigidos, los plazos y los avisos.
- **`ActaEntregaPage`:** regla aplicada (congelada o no), responsabilidad, plazos, anexos con su origen y fuente, y declaración para los anexos DECLARACION y DATO.
