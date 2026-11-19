# Plan · GOV-TRE-04 · Pago

## Constitution gate

| Compuerta | Estado |
|---|---|
| Autorización expresa que nombra TRE-04 | PASS (encargo 2026-11-18) |
| MATERIAL OQ | 0. N37 no fija reglas concretas de pago verificables (ver `evidence/N37_VALIDATION.md`): todas quedan como datos del ente. Las decisiones de diseño son de Claude (PDD) |
| Contradicciones | 0 |
| Migración | `0126_gov_tre04_pago`, down `0125_gov_tre03_orden_pago`. No se tocan 0124 ni 0125. **Al integrar P2 (2026-11-19)** se reencadenó como `0127_gov_tre04_pago`, down `0126_gov_assignment_policy` (publicada por P2) |
| Cero hardcode | Medios, bandas, competencias, documentos, duplicado funcional y numeración son datos del ente |
| DeepSeek | `deepseek-v4-pro`, tope duro 12 al inicio, ampliado por la dueña a 20, 28, 32 y 33 (`OWNER_EXCEPTION_USED=1`); 2 reintentos por subproblema |

## Decisiones de diseño (PDD, de Claude)

- **PDD-TRE04-01 Saldo.** `proyeccion_obligaciones.py` es la única autoridad: `montos_pagados` (REGISTRADO) sustituye al 0 de TRE-03 y se añade `montos_en_tramite` (PENDIENTE_AUTORIZACION + AUTORIZADO). La API entrega `monto_ordenado`, `monto_pagado`, `monto_en_tramite`, `pendiente_de_pagar` y `disponible_para_pago`; el frontend no suma.
- **PDD-TRE04-02 Reserva.** El envío reserva para que ningún conjunto concurrente exceda el ordenado; la orden TRE-03 se bloquea `FOR UPDATE` en enviar, registrar y anular, y se recalcula bajo el bloqueo.
- **PDD-TRE04-03 Maker ≠ checker.** Invariante de plataforma (N05 clase A, «Maker-checker de pagos»; GOV-TRE-004). No se puede desactivar. Se compara por identidad con `usuarios_equivalentes` de CTL-01. El conflicto «quien emitió la orden autoriza su pago» es otro y vive en CTL-01 (proceso TRE-04), solo con regla del ente.
- **PDD-TRE04-04 Bandas.** Una política tiene bandas contiguas por monto en su moneda; cada banda lista requisitos `{accion, materia, cantidad}` del catálogo ORG-03. Modalidad única: todas las aprobaciones exigidas, en cualquier orden, por actores y cargos distintos. N-de-M y secuencial no se construyen (no hay requisito); el JSON de requisitos admite extenderlo.
- **PDD-TRE04-05 Ejecución = registro.** «Registrar pago ejecutado»: la Tesorería ejecutó el pago fuera de KONTROL; KONTROL registra fecha valor, referencia y soportes. La UI nunca dice «enviado al banco».
- **PDD-TRE04-06 Duplicados.** Tres niveles: idempotencia (`idempotency_key` en crear y registrar, índice único parcial, patrón de `treasury`); referencia externa única por (ente, medio) si el medio lo exige, con índice único parcial sobre `referencia_clave` (solo en REGISTRADO); duplicado funcional = misma orden + mismo importe entre pagos activos, con BLOQUEAR o ADVERTIR (confirmación con motivo) según la política.
- **PDD-TRE04-07 Cuenta.** Cuenta TRE-01 `VIGENTE` y en vigor; con `exige_cargo_autorizado_cuenta`, cada checker actúa con un cargo autorizado en esa cuenta (autorizaciones TRE-01 en vigor).
- **PDD-TRE04-08 Fechas.** `fecha_pago` (prevista) en el borrador; `fecha_valor` al registrar: ≥ `fecha_orden` de la orden y nunca futura. La política debe estar VIGENTE y en vigor en la fecha del envío.
- **PDD-TRE04-09 Numeración.** Patrón configurable por ente (`{ANIO}` y `{NUMERO:n}`, por defecto `{ANIO}-{NUMERO:5}`), asignado al enviar.
- **PDD-TRE04-10 Rechazo.** RECHAZADO es terminal; el maker prepara otro pago.

## 1. Modelo (migración 0127)

| Tabla | Claves |
|---|---|
| `gov_payment_settings` | 1 por empresa, `patron` |
| `gov_payment_methods` | `codigo` único por empresa, `nombre`, `descripcion`, `estado` ACTIVO/INACTIVO, `vigente_desde/hasta`, `exige_referencia`, `referencia_unica`, `patron_referencia` (regex opcional), `fundamento` |
| `gov_payment_policies` | `codigo` + `numero_version` únicos por empresa, `version_anterior_id`, `nombre`, `descripcion`, `moneda`, `permite_pago_parcial`, `preparador_competencia_accion/materia` (NULL = sin exigencia), `exige_cargo_autorizado_cuenta`, `control_duplicado` BLOQUEAR/ADVERTIR, `vigente_desde/hasta`, `fundamento`, `act_id`, `tipo_regla`, `estado`, activación y cierre |
| `gov_payment_policy_methods` | (`policy_id`, `method_id`) único |
| `gov_payment_policy_bands` | `orden`, `monto_desde`, `monto_hasta` NULL, `requisitos` JSON |
| `gov_payment_policy_documents` | `document_type_id`, `etapa` PREPARAR/AUTORIZAR/REGISTRAR/ANULAR, `obligatorio` |
| `gov_payment_policy_history` | append-only |
| `gov_payments` | `order_id`, `policy_id`, `policy_numero_version`, `policy_snapshot`, `estado`, `numero`, `codigo`, `fecha_pago`, `fecha_valor`, `account_id`, `method_id`, `moneda`, `monto > 0`, `concepto`, `referencia_externa`, `referencia_clave`, `idempotency_key`, `registro_idempotency_key`, preparador (cargo y funcionario en instantánea), `enviado_por/en`, `aprobaciones_requeridas`, `duplicado_confirmado`, `motivo_duplicado`, `registrado_por/en`, rechazo y anulación (por/en/motivo), `huella` |
| `gov_payment_approvals` | `payment_id`, `actor_id`, `cargo_id` + instantánea, `funcionario`, `requisito_indice`, `competencia_accion/materia`, `decision` APROBADA/RECHAZADA, `motivo`, `policy_numero_version`; único (`payment_id`, `actor_id`) |
| `gov_payment_documents` | `payment_id`, `etapa`, `document_id`, `document_type_id`, `document_version_id`, `sha256`, `snapshot` |
| `gov_payment_history` | append-only |

Todas con `__scope__ = Scope.COMPANY`. Disparadores PG: un pago fuera de BORRADOR no cambia salvo transiciones permitidas; REGISTRADO, RECHAZADO y ANULADO inmutables; nada se borra; aprobaciones, documentos e historias append-only. `ck_gov_sod_rules_proceso` suma `TRE-04`.

## 2. Parametrización

| Regla | Clase |
|---|---|
| Solo órdenes emitidas, saldo, sobrepago, reserva, concurrencia, moneda única, maker ≠ checker, historia, aislamiento | PLATFORM_INVARIANT (N05, N20, N23) |
| Medios, bandas y requisitos, preparador, cargo autorizado en cuenta, documentos, pago parcial, duplicado funcional | INSTITUTIONAL_POLICY (N37, dato del ente con `fundamento` y `tipo_regla`) |
| Numeración, patrón de referencia | OPERATIONAL_CONFIGURATION |
| Orden emisor ≠ autorizador del pago | INSTITUTIONAL_POLICY en CTL-01 |

## 3. API (`/api/v1/gobierno/tesoreria`)

| Método | Ruta | Permiso `gobierno_pagos` | MFA |
|---|---|---|---|
| GET/PUT | `/pagos/configuracion` | view / policy | — |
| GET/POST | `/medios-pago` · PUT `/medios-pago/{id}` (If-Match) | view / policy | — |
| GET/POST | `/politicas-pago` · GET/PUT `/politicas-pago/{id}` (If-Match, BORRADOR) | view / policy | — |
| POST | `/politicas-pago/{id}/activar` · `/cerrar` | policy | sí |
| POST | `/politicas-pago/{id}/nueva-version` | policy | — |
| GET | `/pagos` (filtros) · `/pagos/reporte.csv` · `/pagos/opciones` | view | — |
| POST | `/pagos` | manage | — |
| GET/PUT | `/pagos/{id}` (PUT If-Match, BORRADOR) · GET `/pagos/{id}/controles` | view / manage | — |
| POST | `/pagos/{id}/enviar` | manage | — |
| POST | `/pagos/{id}/aprobar` · `/rechazar` | authorize | sí |
| POST | `/pagos/{id}/registrar` | execute | sí |
| POST | `/pagos/{id}/anular` | manage (borrador) / cancel (enviado) | sí si enviado |

Permisos nuevos `gobierno_pagos`: view, manage, authorize, execute, cancel, policy (SENSITIVE: authorize, execute, cancel, policy). Catálogo 183 → 189.

## 4. Frontend (`src/modules/gobierno/tesoreria/pagos/`)

| Pantalla | Ruta |
|---|---|
| Lista con filtros y CSV | `/gobierno/tesoreria/pagos` |
| Nuevo / editar | `/gobierno/tesoreria/pagos/nuevo`, `/:id/editar` |
| Detalle: saldo de la orden, regla congelada, aprobaciones, controles, enviar, aprobar, rechazar, registrar, anular, historia, fronteras | `/gobierno/tesoreria/pagos/:id` |
| Políticas (lista, medios, numeración) y ficha | `/gobierno/tesoreria/politicas-pago`, `/:id` |

Menú «Gobierno · Tesorería». Se registran `router.tsx`, `pantallas.ts` y `Sidebar.tsx`.

## 5. Motor de procesos

| Componente | En TRE-04 |
|---|---|
| ProcessDefinition / Version | Política de pago versionada (`numero_version`) |
| Stages / Transitions | FR-03 |
| AuthorityBinding | Requisitos de banda (ORG-03) + autoridad funcional (ORG-06/ORG-04) + límite |
| ResponsibilityBinding | Preparador, aprobadores y registrador en instantánea |
| DOCUMENT_RULES | Documentos por etapa |
| CONTROL_RULES | `/controles` |
| SOD_RULES | Maker ≠ checker (invariante) + CTL-01 TRE-04 |
| NORMATIVE_BINDING | `fundamento` + `tipo_regla` |

## 6. Pruebas

Backend §46 (30 casos, carrera real en PG), mutaciones §47 (M1–M10), Vitest §48, E2E §49–§55 en un spec con 1280/390/320 y axe, humo UAT con las pantallas nuevas.
