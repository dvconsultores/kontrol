# GOV-TRE-01 · TRE-01 Cuentas bancarias públicas (GOV-TRE-001, P0)

## 1. Lo que podrá hacer Tesorería (vista del sponsor)

Cuando este ciclo termine, Tesorería podrá registrar las cuentas bancarias del ente con su banco, tipo, moneda y número; vincular el acto administrativo que las habilita; indicar qué cargos están autorizados y bajo qué acto; activarlas; consultar las vigentes y las históricas; cambiar los autorizados conservando la historia; suspenderlas, reactivarlas y cerrarlas sin borrar nada; y revisar la auditoría.

Fuera de alcance: pagos, conciliación, programación financiera, conversión de monedas (TRE-09), contabilidad, personas firmantes (ORG-06) y responsables por cuenta (ORG-05).

## 2. Fuentes y decisiones

- **Requisito:** GOV-TRE-001 «Mantener cuentas bancarias publicas con banco, tipo, moneda, autorizados, vigencia y acto habilitante» (IR §7.7), fuentes N03, N05, N20, P0.
- **Normativa:** N03 (no permitir operaciones financieras sin autoridad y soporte; conservar responsabilidad y trazabilidad), N05 (control de tesorería y cuentas), N20 (control interno). Ninguna fija semántica de firmantes, vocabulario de tipos de cuenta ni catálogo de bancos: son decisiones de la dueña, no normas.

Decisiones de la dueña (2026-11-05):

| Id | Decisión |
|---|---|
| OD-TRE01-01 | **Autorizado = cargo de ORG-03**, con FK fuerte y vigencia propia. La persona que lo ocupa y su firma registrada en el banco quedan fuera de KONTROL hasta ORG-06 |
| OD-TRE01-02 | **Acto para activar y para cambios:** activar exige un acto DOC-02 EMITIDO o EFICAZ del mismo ente; cada alta o fin de un autorizado exige también un acto (el mismo u otro), registrado en la historia |
| OD-TRE01-03 | **Acto REVOCADO o NULO después:** la cuenta conserva estado e historia, se marca «acto habilitante sin efecto» y no admite nuevos autorizados ni reactivación hasta vincular un acto vigente. Nada se borra |
| OD-TRE01-04 | **Banco y número:** catálogo de bancos de Gobierno que registra Tesorería, con código de 4 dígitos, sin precargar códigos oficiales. Número de 20 dígitos validado contra ese código, guardado completo y mostrado enmascarado salvo a quien gestiona. Nunca completo en auditoría, registros ni URLs |
| OD-TRE01-05 | **Tipos:** CORRIENTE y AHORRO, lista cerrada, decisión de producto y no norma |
| OD-TRE01-06 | **Estados:** BORRADOR → VIGENTE ⇄ INACTIVA → CERRADA. Sin borrado; una cuenta cerrada no se reabre |
| OD-TRE01-07 | **Capacidad `gobierno_cuentas`:** `view` (consulta enmascarada), `manage` (crear, editar, autorizados, ver el número completo), `activate` con MFA (activar, inactivar, reactivar, cerrar) |

### Prueba de bloqueo material

| Clase | Resultado |
|---|---|
| ¿Qué significa «autorizados»? | A · cargos institucionales (OD-TRE01-01) |
| ¿Requiere ORG-06? ¿ORG-05? | No. No hay vínculo persona → cargo → usuario. GOV-ORG-006 sigue siendo ORG-05 |
| ¿N03/N05/N20 imponen firmantes o combinaciones? | No |
| ¿El acto designa cuenta, autorizados o ambos? | Ambos: acto de la cuenta y acto de cada cambio de autorizado |
| SECURITY · DATA_INTEGRITY · LEGAL · NORMATIVE · ARCHITECTURAL · TESTABILITY · DOMAIN_DEPENDENCY | 0 |

TRE01_FULL_PROCESS_IMPLEMENTABLE = 1 · ORG06_DEPENDENCY_REQUIRED = 0 · MATERIAL_BLOCKER = 0.

## 3. Banco

`gov_banks`: catálogo por empresa. Código de 4 dígitos, único por empresa; nombre 3–120; estado ACTIVO o INACTIVO. Un banco inactivo no se ofrece para cuentas nuevas, y las existentes no cambian. No se precargan códigos: no se inventa ningún código oficial.

## 4. Cuenta

| Campo | Regla |
|---|---|
| Código | `CB-AAAA-NNNN` por empresa, del sistema |
| Denominación | 3–200: para qué es la cuenta |
| Banco | FK a un banco ACTIVO de la misma empresa |
| Tipo | CORRIENTE o AHORRO |
| Número | exactamente 20 dígitos; los 4 primeros == código del banco; único por empresa y banco |
| Moneda | VES, USD o EUR: vocabulario ya vigente en Gobierno (ORG-03), sin catálogo nuevo |
| Vigente desde / hasta | fechas civiles; hasta ≥ desde |
| Estado | BORRADOR, VIGENTE, INACTIVA, CERRADA |
| Acto habilitante | FK a `gov_acts` de la misma empresa |

### Máquina de estados

| Desde | Acción | Capacidad | Condición | A | Motivo | Auditoría |
|---|---|---|---|---|---|---|
| — | Registrar | manage | datos válidos | BORRADOR | — | GOV_BANK_ACCOUNT_CREATED |
| BORRADOR | Editar | manage | If-Match | BORRADOR | — | GOV_BANK_ACCOUNT_UPDATED |
| BORRADOR, VIGENTE, INACTIVA | Vincular acto | manage | acto EMITIDO o EFICAZ, misma empresa, fecha ≤ hoy | igual | — | GOV_BANK_ACCOUNT_ACT_LINKED |
| BORRADOR | Activar | activate (MFA) | acto con efecto + ≥1 autorizado en vigor | VIGENTE | — | GOV_BANK_ACCOUNT_ACTIVATED |
| VIGENTE | Inactivar | activate (MFA) | — | INACTIVA | 10–500 | GOV_BANK_ACCOUNT_DEACTIVATED |
| INACTIVA | Reactivar | activate (MFA) | acto con efecto + ≥1 autorizado en vigor | VIGENTE | 10–500 | GOV_BANK_ACCOUNT_REACTIVATED |
| VIGENTE, INACTIVA | Cerrar | activate (MFA) | fecha de cierre ≥ vigente desde | CERRADA | 10–500 | GOV_BANK_ACCOUNT_CLOSED |

Una cuenta CERRADA no admite ninguna acción. Al cerrar, los autorizados en vigor terminan con motivo «Cierre de la cuenta» y sin acto de fin: el cierre es el hecho que los termina.

### Acto sin efecto (OD-TRE01-03)

`acto_sin_efecto` se deriva al leer: el acto vinculado está REVOCADO o NULO. No cambia el estado de la cuenta. Mientras sea cierto se rechaza con 409 `GOV_BANK_ACCOUNT_ACT_WITHOUT_EFFECT`: añadir autorizado y reactivar. Vincular un acto vigente lo resuelve. Inactivar y cerrar siguen permitidos: reducen exposición.

## 5. Autorizados e historia

`gov_bank_account_authorizations`, una fila por autorización, nunca se sobrescribe:

- cargo (FK fuerte a `gov_positions`, VIGENTE y de la misma empresa al autorizar), con instantánea de código, denominación y unidad, como CTL-06;
- acto de alta (obligatorio, EMITIDO o EFICAZ, misma empresa);
- vigente desde (≥ vigente desde de la cuenta);
- al terminar: vigente hasta, acto de fin (obligatorio salvo en el cierre de la cuenta), motivo 10–500, quién y cuándo.

Varios cargos pueden estar autorizados a la vez. No se modelan combinaciones de firma. Un mismo cargo no puede tener dos autorizaciones en vigor en la misma cuenta: índice único parcial → 409 `GOV_BANK_AUTHORIZATION_DUPLICATE`. Si un cargo deja de estar VIGENTE, la autorización no se toca: la ficha lo avisa (`cargo_vigente = false`) para que Tesorería la termine con su acto.

`gov_bank_account_history`, inmutable: CREADA, EDITADA, ACTO_VINCULADO, ACTIVADA, INACTIVADA, REACTIVADA, CERRADA, AUTORIZADO_ALTA, AUTORIZADO_FIN.

## 6. Seguridad del número

- Se guarda en claro: es la práctica vigente del repositorio para cuentas (`party_bank_accounts`, `financial_accounts`) y no hay contrato de cifrado de campo de negocio. No se inventa uno en este ciclo.
- La API nunca lo devuelve en listados ni en el detalle: solo `numero_enmascarado` (`••••` + últimos 4).
- `GET /cuentas/{id}/numero` (`manage`) es la única salida del número completo. Audita GOV_BANK_ACCOUNT_NUMBER_VIEWED, sin el número.
- Nunca en auditoría, mensajes de error, logs ni URLs: los eventos llevan solo `numero_enmascarado`.

## 7. API (`/api/v1/gobierno/tesoreria`; guardas: permiso → empresa → módulo `gobierno`)

| # | Método y ruta | Permiso | Respuesta |
|---|---|---|---|
| 1 | GET `/bancos` (`estado?`) | view | listado |
| 2 | POST `/bancos` | manage | 201 banco |
| 3 | PATCH `/bancos/{id}` (If-Match) | manage | banco |
| 4 | GET `/cuentas` (`estado?`, `banco_id?`, `moneda?`, `cargo_id?`) | view | listado con resumen por estado |
| 5 | POST `/cuentas` | manage | 201 detalle |
| 6 | GET `/cuentas/{id}` | view | detalle con autorizados e historia |
| 7 | PATCH `/cuentas/{id}` (If-Match) | manage | detalle |
| 8 | GET `/cuentas/{id}/numero` | manage | `{numero}` |
| 9 | POST `/cuentas/{id}/acto` (If-Match) | manage | detalle |
| 10 | POST `/cuentas/{id}/autorizados` (If-Match) | manage | 201 detalle |
| 11 | POST `/cuentas/{id}/autorizados/{aid}/fin` (If-Match) | manage | detalle |
| 12 | POST `/cuentas/{id}/activar` (If-Match) | activate | detalle |
| 13 | POST `/cuentas/{id}/inactivar` (If-Match) | activate | detalle |
| 14 | POST `/cuentas/{id}/reactivar` (If-Match) | activate | detalle |
| 15 | POST `/cuentas/{id}/cerrar` (If-Match) | activate | detalle |
| 16 | GET `/opciones` | view | bancos activos, cargos vigentes y actos con efecto para los selectores |

Errores: 404 `GOV_BANK_NOT_FOUND` / `GOV_BANK_ACCOUNT_NOT_FOUND` / `GOV_BANK_AUTHORIZATION_NOT_FOUND`; 409 `GOV_BANK_ACCOUNT_STALE`, `GOV_BANK_ACCOUNT_INVALID_STATE`, `GOV_BANK_ACCOUNT_DUPLICATE`, `GOV_BANK_ACCOUNT_CONFLICT` (colisión del código correlativo), `GOV_BANK_CODE_DUPLICATE`, `GOV_BANK_ACCOUNT_ACT_WITHOUT_EFFECT`, `GOV_BANK_AUTHORIZATION_DUPLICATE`, `GOV_BANK_ACCOUNT_NOT_READY`; 422 `GOV_BANK_ACCOUNT_INVALID`; 428 `GOV_BANK_ACCOUNT_IF_MATCH_REQUIRED`.

### 7.1 Contrato exacto de entrada y salida

Toda entrada prohíbe campos extra (`company_id` del cliente → 422).

**Entradas**

- `BancoIn`: `codigo` (string), `nombre` (3–120). `BancoCambios`: `nombre?`, `estado?` (ACTIVO, INACTIVO). El código no se edita: los números ya validados dependen de él.
- `CuentaIn`: `denominacion` (3–200), `banco_id`, `tipo`, `numero` (string), `moneda`, `vigente_desde`, `vigente_hasta?`. `CuentaCambios`: los mismos, todos opcionales.
- `ActoIn`: `acto_id`. `AutorizadoIn`: `cargo_id`, `acto_id`, `vigente_desde`. `FinAutorizacionIn`: `acto_id`, `vigente_hasta`, `motivo`.
- `MotivoIn` (inactivar y reactivar): `motivo` (10–500). `CierreIn`: `motivo` (10–500), `fecha_cierre`.

**El número y el código del banco no llevan restricciones de longitud ni patrón en el esquema:** los valida el servicio, porque un 422 del esquema devolvería el valor recibido. El mensaje nunca repite el valor.

**Salidas**

- Banco: `id, codigo, nombre, estado, version`.
- Resumen de cuenta: `id, codigo, denominacion, banco_id, banco_codigo, banco_nombre, tipo, moneda, numero_enmascarado, vigente_desde, vigente_hasta, estado, en_vigor, acto_sin_efecto, autorizados_en_vigor, version`.
- Listado: `{items: [resumen], resumen: {borradores, vigentes, inactivas, cerradas}}`; `resumen` cuenta toda la empresa, sin filtros. `cargo_id` filtra por autorización en vigor.
- Detalle: resumen + `acto` (referencia o null) + `registrada_por, registrada_en, activada_por, activada_en, cerrada_por, cerrada_en, fecha_cierre, motivo_cierre` + `autorizados` (primero los en vigor, después por `vigente_desde` descendente) + `historia` (cronológica).
- Referencia de acto: `id, tipo, numero, fecha, estado, asunto`.
- Autorizado: `id, cargo_id, cargo_codigo, cargo_denominacion, cargo_unidad, cargo_vigente, acto_alta, vigente_desde, vigente_hasta, acto_fin, motivo_fin, en_vigor, registrada_por, registrada_en, terminada_por, terminada_en`.
- Historia: `tipo, detalle, registrado_por, registrado_en`.
- `GET /numero`: `{numero}`.
- `GET /opciones`: `{bancos: [{id, codigo, nombre}], cargos: [{id, codigo, denominacion, unidad}], actos: [referencia]}`.

`en_vigor` de una cuenta: VIGENTE y hoy dentro de su vigencia. `en_vigor` de una autorización: `vigente_hasta` nulo.

### 7.2 Reglas de validación

| Caso | Respuesta |
|---|---|
| Número sin 20 dígitos, o sus 4 primeros ≠ código del banco | 422 `GOV_BANK_ACCOUNT_INVALID` |
| Código de banco sin 4 dígitos | 422 `GOV_BANK_ACCOUNT_INVALID` |
| Banco de otra empresa, inexistente o INACTIVO | 422 `GOV_BANK_ACCOUNT_INVALID`, mismo mensaje en los tres casos |
| Acto inexistente, de otra empresa, no EMITIDO ni EFICAZ, o con fecha futura | 422 `GOV_BANK_ACCOUNT_INVALID`, mismo mensaje |
| Cargo inexistente, de otra empresa, no VIGENTE o fuera de la estructura vigente del ejercicio | 422 `GOV_BANK_ACCOUNT_INVALID`, mismo mensaje |
| Alta o fin de autorización con fecha futura; alta antes del inicio de la cuenta o después de su fin; fin antes del alta | 422 `GOV_BANK_ACCOUNT_INVALID` |
| Fecha de cierre futura o anterior al inicio de la cuenta | 422 `GOV_BANK_ACCOUNT_INVALID` |
| Autorización inexistente, de otra cuenta o de otra empresa | 404 `GOV_BANK_AUTHORIZATION_NOT_FOUND` |
| Terminar una autorización ya terminada; acción en estado no permitido | 409 `GOV_BANK_ACCOUNT_INVALID_STATE` |
| Activar o reactivar sin acto, sin autorizados o con la vigencia vencida | 409 `GOV_BANK_ACCOUNT_NOT_READY` con `details.faltan` (`acto`, `autorizado`, `vigencia`) |
| Activar o reactivar con el acto REVOCADO o NULO | 409 `GOV_BANK_ACCOUNT_ACT_WITHOUT_EFFECT` |

El orden de comprobación en una escritura es: 428 → 404 → 409 versión → 409 estado → resto. El fin de una autorización se admite con el acto de la cuenta sin efecto: reduce exposición. Se permite dejar una cuenta VIGENTE sin autorizados; la ficha lo avisa.

Concurrencia: `SELECT … FOR UPDATE` de la cuenta + If-Match en toda escritura; unicidad en base para número y autorización en vigor.

## 8. Roles, MFA y auditoría

`gobierno_cuentas:view` y `:manage` STANDARD; `:activate` SENSITIVE. ADMIN técnico no recibe nada por serlo; la migración concede los tres a FUNCIONAL_COMPLETO, como los procesos anteriores.

Catálogo (`owner_spec` `gov-tre-01`): GOV_BANK_CREATED, GOV_BANK_UPDATED, GOV_BANK_ACCOUNT_CREATED, _UPDATED, _ACT_LINKED, _ACTIVATED, _DEACTIVATED, _REACTIVATED, _CLOSED, _NUMBER_VIEWED, GOV_BANK_AUTHORIZATION_ADDED, _ENDED. Doce acciones, clase BUSINESS_COMMIT, sin el número completo.

**CTL-04:** proceso «TRE-01 · Cuentas bancarias públicas»; rastreo de `GovernmentBankAccount` → ficha de la cuenta.

**CTL-01:** proceso `TRE-01` en el catálogo SoD con 6 acciones (TRE01_REGISTRAR crea el objeto, TRE01_ACTIVAR, TRE01_AUTORIZAR, TRE01_FIN_AUTORIZACION, TRE01_INACTIVAR, TRE01_CERRAR) y guarda integrada. No se crea ninguna regla: quedan disponibles para Control Interno.

## 9. Menú y pantallas

Sección **Gobierno · Tesorería**: «Cuentas bancarias» y «Bancos».

| Pantalla | Ruta | Contenido |
|---|---|---|
| S1 · Cuentas bancarias | `/gobierno/tesoreria/cuentas` | indicadores por estado; filtros estado, banco, moneda, cargo; tabla: código, denominación, banco, tipo, moneda, número enmascarado, estado, autorizados |
| S2 · Nueva cuenta | `/gobierno/tesoreria/cuentas/nueva` | formulario de la cuenta |
| S3 · Cuenta | `/gobierno/tesoreria/cuentas/:id` | datos; ver número (`manage`); acto; autorizados vigentes e históricos; acciones por estado; historia; aviso de acto sin efecto |
| S4 · Bancos | `/gobierno/tesoreria/bancos` | catálogo: alta, edición, activo o inactivo |

## 10. Escenario de éxito para la prueba de la dueña

1. Tesorería registra el banco con su código.
2. Registra una cuenta: banco, tipo, moneda, número de 20 dígitos.
3. Vincula un acto EMITIDO o EFICAZ del ente.
4. Autoriza un cargo vigente, con su acto.
5. Activa la cuenta (MFA): queda «Vigente».
6. Autoriza otro cargo y termina el primero, con acto y motivo: la historia conserva ambos.
7. Inactiva y reactiva con motivo; cierra con motivo y fecha.
8. Sistema › Auditoría registra cada paso sin el número completo.
9. **Negativas:** otra empresa no ve la cuenta; un cargo de otro ente o un acto en borrador se rechazan; número que no empieza por el código del banco se rechaza; con el acto revocado aparece el aviso y no se admiten autorizados.

OWNER_UAT_SCENARIO_DEFINED = 1.
