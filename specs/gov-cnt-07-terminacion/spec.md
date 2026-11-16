# Spec · CNT-07 Terminación, resolución o rescisión del contrato (GOV-CNT-008)

- **Iniciativa:** P2 · CNT-07 · 2026-11-16.
- **Entrada:** `e758ada9`, con cabeza `0121_gov_cnt09_alertas`.
- **Paralelo:** P1 trabaja en la activación manual de la licencia y el perfil Government. Solape funcional 0; solape de ficheros posible.
- **Fuentes:** `FUENTES.md` (N11, N12 y N25 leídas sobre el texto exacto).

## Objetivo

Quien representa al contratante abre un contrato **formalizado** y registra su **extinción jurídica anticipada**. Solo puede hacerlo bajo una de las tres figuras que prueban las fuentes (LCP art. 145):
- rescisión unilateral por causa no imputable al contratista;
- resolución por mutuo acuerdo;
- rescisión por causa imputable al contratista.

Cada extinción lleva causal tasada, motivación, acto DOC-02 eficaz, notificaciones DOC-04 y una vista de las consecuencias de ejecución y financieras. A partir de la fecha de eficacia, el sistema impide los hechos incompatibles en CNT-02, CNT-03 y CNT-04. Además retira las alertas de CNT-09 que dejan de tener objeto y proyecta la actuación en el expediente CNT-08.

**Qué no es CNT-07:**
- No es «cerrar contrato»: el cumplimiento normal y su cierre siguen en CNT-03 (LCP 146–151). CNT-07 solo lo **proyecta**.
- No toca la terminación del procedimiento antes del contrato (PROC-08).
- No reescribe el contrato: CNT-01 sigue FORMALIZADO e inmutable. La extinción es un hecho adicional y la situación se deriva por fecha.

## Decisiones de la dueña (2026-11-16)

| Id | Decisión |
|---|---|
| OD-CNT07-01 | **Acto base revocado o nulo después de formalizar** (LOPA 82–83). La extinción sigue registrada; el contrato, la pantalla y el expediente avisan «Acto base revocado/nulo: requiere actuación jurídica», con enlace al acto. No se reactiva nada. La consecuencia jurídica queda abierta: **OQ-CNT07-01** (no material para este ciclo) |
| OD-CNT07-02 | **Conclusión autorizada** (LCP 152 y 156; RLCP 190 y 193). En una rescisión, la actuación puede llevar alcance (texto) y fecha límite, respaldadas por el mismo acto decisorio. Los hechos de ejecución se admiten hasta esa fecha |
| OD-CNT07-03 | **Notificaciones.** Siempre, una notificación practicada del acto al contratista, identificada por su documento. En las rescisiones, si el contrato tiene garantías vigentes, además al menos una notificación practicada a otro destinatario (garante o cesionario) |
| OD-CNT07-04 | **Rescisión imputable.** Exige dos actos DOC-02: el de apertura del procedimiento, eficaz, y el decisorio, de fecha posterior a la eficacia de la apertura. La sustanciación (descargos y pruebas) no se modela |

## Contratos

| Id | Contrato |
|---|---|
| C07-01 | **Solo contratos FORMALIZADO.** Otro estado responde 409 `GOV_CONTRACT_TERMINATION_NOT_FORMALIZED`. Otra empresa, 404 |
| C07-02 | **Figura respaldada.** Catálogo cerrado: `RESCISION_NO_IMPUTABLE` (LCP 152), `RESOLUCION_MUTUO_ACUERDO` (LCP 154) y `RESCISION_IMPUTABLE` (LCP 155). `CUMPLIMIENTO` es una proyección de CNT-03, no una figura registrable. Cualquier otro valor da 422 |
| C07-03 | **Causal obligatoria y tasada por figura.** NO_IMPUTABLE: `INTERES_DEL_CONTRATANTE`. MUTUO_ACUERDO: `CIRCUNSTANCIAS_ACONSEJABLES`. IMPUTABLE: `LCP_155_1` a `LCP_155_9` (la 9 solo en OBRAS) o `CLAUSULA_CONTRATO` con referencia obligatoria (RLCP 193) |
| C07-04 | **Motivación obligatoria** (LOPA 9): `hechos` y `fundamento` de 20 a 4000 caracteres. El acto decisorio debe traer `hechos` y `fundamentos` no vacíos |
| C07-05 | **Acto DOC-02 decisorio.** De la empresa, de carácter PARTICULAR, en estado EFICAZ (ni REVOCADO ni NULO), con competencia APROBAR × CONTRATACIONES y fecha posterior o igual a la de formalización del contrato. No se crea ni se copia el acto |
| C07-06 | **Autoridad válida.** `_autoridad_valida(cargo del acto, fecha del acto, APROBAR, CONTRATACIONES)` y `exigir_autoridad_funcional`, igual que CNT-04 y PROC-10. Si falla: 422 y auditoría `GOV_CONTRACT_TERMINATION_BLOCKED` |
| C07-07 | **Eficacia separada del registro.** Se guardan aparte la fecha del acto, la fecha de eficacia (la de DOC-04, que es la última notificación practicada) y el instante de registro. `created_at` nunca es una fecha jurídica |
| C07-08 | **Notificaciones DOC-04** del acto decisorio, según OD-CNT07-03. Se listan con su estado y enlace. No hay tabla propia de notificaciones |
| C07-09 | **Una extinción por contrato.** Índice único parcial: un solo BORRADOR y una sola FORMALIZADA por contrato. FOR UPDATE del contrato, `If-Match` sobre el borrador. Una segunda formalización da 409 `GOV_CONTRACT_TERMINATION_ALREADY_EXISTS` |
| C07-10 | **Historia inmutable.** Una FORMALIZADA no admite UPDATE, DELETE ni TRUNCATE (trigger PG); solo un BORRADOR se puede editar o descartar. No existe «deshacer terminación» |
| C07-11 | **Consecuencias financieras sin efectos.** Se muestran el monto vigente en la fecha de eficacia, lo valuado conformado y presentado, lo recibido, lo facturado conforme, el saldo no ejecutado (monto vigente menos valuado conformado; FINANCIAL_EXECUTION_BASE), el saldo por valuar de CNT-03, los compromisos BUD-08 del expediente y las garantías. No crea pagos, causado ni anulaciones |
| C07-12 | **CNT-06 no se absorbe.** La indemnización (RLCP 191 y 194) y las penalidades se muestran como regla y CONSECUENCIA_PENDIENTE_CNT06, sin cálculo |
| C07-13 | **Garantías en PROC-10.** Se listan las garantías del contrato con su estado y su enlace a la autoridad PROC-10. Ninguna se ejecuta ni se libera automáticamente |
| C07-14 | **Situación por fecha.** `situacion_contractual(db, company_id, contract_id, fecha)` devuelve VIGENTE o EXTINGUIDO (con la figura) según la FORMALIZADA con `fecha_eficacia <= fecha`. Incluye `fecha_limite_ejecucion` (la de la conclusión autorizada o la de eficacia) y la alerta de OD-CNT07-01 |
| C07-15 | **Guardas posteriores** (409 `GOV_CONTRACT_TERMINATED`, con `fecha_limite`), siempre sobre la fecha del hecho: ver §Guardas |
| C07-16 | **Aislamiento.** Todo filtra por `tenant_id` y `company_id`. Otra empresa: 404 en contrato, borrador y reporte. Un acto o documento de otra empresa: 422 sin revelar nada |
| C07-17 | **Concurrencia.** Dos formalizaciones simultáneas: una gana y la otra recibe 409, sin estado mixto |
| C07-18 | **CNT-08.** CNT-07 sale de `FUENTES_FUTURAS` y entra en `ORDEN_PROCESO`, la sección «Terminación / resolución / rescisión», la cronología, `ids_del_expediente` y el paquete (`included_sources`) |
| C07-19 | **CNT-09.** Un contrato extinguido en la fecha de la corrida deja de generar condiciones; la reconciliación existente resuelve sus alertas activas sin borrarlas |
| C07-20 | **Reporte.** `GET /gobierno/contratos/terminaciones/reporte.csv`, con filtros `figura`, `desde` y `hasta` (por fecha de eficacia) y las actuaciones FORMALIZADA de la empresa |
| C07-21 | **Permiso.** Capacidad nueva `gobierno_contratos:terminate`, SENSITIVE (MFA de sesión, mecanismo canónico de Gobierno), concedida a FUNCIONAL_COMPLETO. Consultar exige `gobierno_contratos:view` |
| C07-22 | **SoD y auditoría.** Acciones `PROC03_TERMINACION_PREPARAR` y `PROC03_TERMINACION_FORMALIZAR` en el catálogo SoD (el ente las configura). Eventos `GOV_CONTRACT_TERMINATION_DRAFT_CREATED`, `_DRAFT_UPDATED`, `_DRAFT_DISCARDED`, `_FORMALIZED` y `_BLOCKED`, sin material documental |
| C07-23 | **Rescisión imputable con apertura** (OD-CNT07-04): acto de apertura EFICAZ, con la misma validación que C07-05/06, distinto del decisorio, y con `fecha_eficacia` de la apertura anterior a la fecha del acto decisorio |
| C07-24 | **Mutuo acuerdo con documento.** Documento del acuerdo vinculado al expediente (`_documento_valido` de CNT-01, más integridad). Al formalizar se sella, como en CNT-02 |
| C07-25 | **Conclusión autorizada** (OD-CNT07-02): solo en rescisiones; alcance de 10 a 1000 caracteres; fecha límite posterior a la eficacia |
| C07-26 | **Coherencia con lo ya registrado.** No se formaliza si ya existen hechos de ejecución guardados (§Guardas), modificaciones formalizadas o designaciones con fecha posterior a la fecha límite: 409 `GOV_CONTRACT_TERMINATION_LATER_FACTS`, con la lista |
| C07-27 | **Obligaciones informativas.** La evaluación de desempeño al SNC (LCP 51, toda rescisión) y la publicación en el SNC (LCP 8, imputable) se muestran como pendientes externas. KONTROL no las ejecuta |
| C07-28 | **UI y E2E.** Pantalla `/gobierno/contratos/:id/terminacion`, enlazada desde la ficha del contrato. La ficha muestra la situación. Recorrido del sponsor completo a 1280, 390 y 320 px, con Axe sin «serious» nuevos |

## Guardas (C07-15)

La fecha límite es la de la conclusión autorizada o, si no la hay, la de eficacia.

| Proceso | Operación | Fecha comparada | Regla |
|---|---|---|---|
| CNT-03 | `iniciar` | `fecha` | > límite → 409 |
| CNT-03 | `crear_hito` | `fecha_prevista` | > límite → 409 |
| CNT-03 | `crear_entregable` | `fecha_vencimiento` | > límite → 409 |
| CNT-03 | `entregar` | `fecha_entrega` | > límite → 409 |
| CNT-03 | `presentar_valuacion` | `periodo_hasta` (período ejecutado) | > límite → 409 |
| CNT-03 | `terminar_obra` | `fecha` | > límite → 409 |
| CNT-03 | `revisar_entrega`, `resolver_valuacion`, `registrar_recepcion`, `vincular_factura`, `cerrar` y anulaciones | — | **Se admiten**: conforman y liquidan lo ejecutado antes, que es la base de RLCP 191.a |
| CNT-02 | `formalizar` | `vigente_desde` (o `fecha_instrumento`) | Extinguido en esa fecha → 409 |
| CNT-04 | `designar` | `desde` | > límite → 409 |

La historia anterior nunca se toca: los hechos con fecha menor o igual al límite siguen siendo válidos aunque hoy el contrato esté extinguido.

## Decisiones de diseño (no materiales)

- **D07-01:** tabla propia `gov_contract_terminations`, inmutable al formalizar. El trigger de `gov_contracts` no cambia.
- **D07-02:** el MFA es el de sesión por permiso SENSITIVE, como en `formalize` y `execute`. Gobierno no usa `require_recent_reauth`, cuyo conjunto `REAUTH_PROTECTED_OPERATIONS` está fijado por la prueba MFA-F03.
- **D07-03:** la competencia es APROBAR × CONTRATACIONES, la misma que CNT-04 y PROC-10 exigen a sus actos. No se inventa «RESCINDIR».
- **D07-04:** los compromisos BUD-08 se muestran con su enlace a la acción canónica (anular, total) de BUD-08. No hay anulación automática ni parcial (`CNT07_AUTO_ANNULS_BUD08=0`).
- **D07-05:** no hay estado programado (FUENTES.md: TERMINACION_PROGRAMADA = NOT_PROVEN). Como la eficacia nace de DOC-04, nunca es futura.
- **D07-06:** el CUMPLIMIENTO se proyecta desde el `estado_ejecucion` de CNT-03 (CERRADA) en la situación, sin registro editable.

## Fuera de alcance

- CNT-05, CNT-06 (BLOCKED_N38), BUD-09 (BLOCKED_N36) y TRE-04 (BLOCKED_N37).
- Medidas preventivas (LCP 157–164).
- La remisión y la publicación externas al SNC.
- La sustanciación del procedimiento de rescisión.
- La UAT remota.
