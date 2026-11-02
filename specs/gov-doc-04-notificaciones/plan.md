# Plan · GOV-DOC-04 Notificaciones administrativas

## Decisiones de arquitectura
- **AD-DOC04-01 Módulo:** dentro de `app/modules/government` (`models.py` + `schemas_notificaciones.py`, `service_notificaciones.py`,
  `api_notificaciones.py`), con el patrón de DOC-02 (`acto_para_escribir`, `_versionar`, `_auditar`, `freeze_links`,
  `validar_coherencia`). No se reutiliza `app/modules/notifications` (047: avisos internos).
- **AD-DOC04-02 Eficacia:** función única `_eficacia_por_notificaciones(db, acto, actor)` en el servicio de DOC-04 que, con el acto
  bloqueado, decide EMITIDO → EFICAZ y escribe los campos de eficacia de DOC-02 (medio, referencia, fecha de publicación o
  notificación, documento de eficacia, fecha de eficacia) de la notificación determinante. DOC-02 rechaza `/eficacia` para PARTICULAR.
  Un solo escritor por campo: sin doble escritura.
- **AD-DOC04-03 Concurrencia:** `If-Match` de la notificación; `FOR UPDATE` de la notificación y del acto en intentos y anulación (el
  acto se bloquea primero, siempre, para no interbloquear); único parcial de destinatario por acto; `numero` de intento único.
- **AD-DOC04-04 Documentos:** `ResourceKind("GovernmentNotification")`; el oficio y las constancias se vinculan a la notificación y se
  congelan al registrar el intento; la constancia debe ser distinta del oficio.
- **AD-DOC04-05 Fechas:** civiles de Caracas (`hoy_de_negocio`); «publicación + 15 días» con `timedelta` en el backend y
  `sumarDiasDeNegocio` en la interfaz (ADR-020).
- **AD-DOC04-06 Interfaz:** `src/modules/gobierno/notificaciones/` (lista, página, formulario de destinatario, panel de intento,
  panel de anulación) + sección «Notificaciones» en `ActoPage` (sustituye el panel PARTICULAR de `RegistrarEficacia`, que queda solo
  para Gaceta).

## Decisiones de diseño (de Claude, dentro de las de la dueña)
- **PDD-DOC04-01** Una notificación NOTIFICADA es inmutable; los intentos no se editan ni se borran.
- **PDD-DOC04-02** La corrección de datos solo se permite en PENDIENTE sin intentos (después, el registro es la historia).
- **PDD-DOC04-03** El oficio se exige antes del primer intento y queda fijado en ese intento.
- **PDD-DOC04-04** Capacidades `gobierno_notificaciones:view/edit/record`; `edit` y `record` SENSIBLES.
- **PDD-DOC04-05** Reporte: lista del año con filtros y CSV (una fila por notificación con su último intento).
- **PDD-DOC04-06** DOC-02 se adapta en el mismo ciclo (OD-DOC04-03): rechazo de `/eficacia` PARTICULAR, contadores en `ActoOut`,
  `RegistrarEficacia` solo GENERAL, sección de notificaciones en el acto; las pruebas de DOC-02 que ejercían la notificación por
  `/eficacia` pasan a hacerlo por DOC-04.

## Puerta de la Constitución
| Compuerta | Valor |
|---|---|
| CURRENT_BRANCH / DEFAULT_BRANCH = develop · REMOTE_BRANCH_COUNT = 1 · HEAD_EQUALS_ORIGIN | 1 · 1 · 1 |
| DOC04_REQUIREMENTS_COMPLETE · FULL_PROCESS_IMPLEMENTABLE | 1 · 1 |
| PROCESS_MODEL · RECIPIENT · CHANNEL · CONSTANCIA · DOC02_INTEGRATION · EFFECTIVENESS · STATE_MACHINE | 1 cada una |
| DOCUMENT · MENU · SCREEN_FORM · FIELD · ROLE · REPORT · AUDIT · ERROR · OWNER_UAT_SCENARIO | 1 cada una |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 · 0 · 0 · 0 |
| P1 Spec antes que código · P2 autorización (encargo GOV-DOC-FUNCTIONAL-02, DOC-04) · P5 historia protegida · P6 seguridad en backend · P11 accesibilidad · P13 integridad transaccional · P18 sin modales salvo confirmación · P19 regla con fuente | cumplidas por diseño |

`GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 1` solo para DOC-04.
