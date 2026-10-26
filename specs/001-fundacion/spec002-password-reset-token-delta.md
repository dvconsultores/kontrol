# SPEC 002 · Delta — SHARED-CORE-SECURITY-HARDENING · AUTH-PASSWORD-RESET-TOKEN-DISCLOSED

| Campo | Valor |
|---|---|
| Spec dueña | **002** (Seguridad / Sesiones). Se aloja en `specs/001-fundacion/`, junto a FR-001-026 (recuperación de contraseña), por OBS-04 (la Spec 002 no tiene carpeta propia) |
| Deuda | AUTH-PASSWORD-RESET-TOKEN-DISCLOSED · **CRITICAL** (detectada en el delta MFA, §21) |
| Prioridad | OD-SEC-PRIORITY-01 = RATIFIED: se adelanta a la DELEGATION CEILING |
| Decisiones de la dueña | OD-AUTHRESET-01..06 = RATIFIED (§4) |
| HEAD de entrada | `d39f820` + Fase A del cierre MFA |
| Evidencia | `evidence/password-reset-token/` |
| GOVERNMENT_IMPLEMENTATION_AUTHORIZED | 0 |
| Estado | **IMPLEMENTED — CONVERGED (2026-10-26)**, §24–§26. Antes: **DESIGN COMPLETE — MATERIAL OQ = 0 — IMPLEMENTATION AUTHORIZED** por el encargo «SECURITY CLOSURE REMEDIATION + AUTH-PASSWORD-RESET-TOKEN-DISCLOSED» (Fase B) |

## 1. Discover (medido en el árbol de entrada)

| Elemento | Hecho medido |
|---|---|
| `POST /auth/password-reset/request` (`identity_access/api.py`) | Resuelve el tenant por código (desconocido → 401 `AUTH_INVALID_CREDENTIALS`), llama a `request_password_reset` y responde `{"ok": true, "reset_token": <token>}`, con el comentario «flujo demo» |
| `request_password_reset` (`service.py`) | Usuario desconocido → 401 `AUTH_INVALID_CREDENTIALS` («No revelar existencia», pero sí la revela por código y cuerpo). Token `secrets.token_urlsafe(32)` (256 bits). Guarda `sha256_hex(token)`. TTL **30 min**. No invalida tokens anteriores. Audita `PASSWORD_RESET_REQUESTED` |
| `confirm_password_reset` | Política de contraseña → 422. Busca por hash; usado, inexistente o caducado → 401 `RESET_TOKEN_INVALID`. **Lee y luego escribe `used_at`** (sin condición: dos consumos concurrentes pueden ganar los dos). Cambia el hash, pone `must_change_password=False`, audita `PASSWORD_RESET_CONFIRMED` y revoca las sesiones (`revoke_user_sessions`). No toca el MFA |
| Modelo `password_resets` | `user_id`, `token_hash` (índice **no** único), `expires_at`, `used_at`, `created_by`; ámbito por `user_id → users` |
| Sesiones | `revoke_user_sessions` marca `revoked_at`. **No hay sello de credencial**: un login que leyó el hash antiguo antes de que el reset confirme puede crear una sesión después |
| Canal de entrega fuera de banda | **No existe**: no hay SMTP ni proveedor de correo o SMS; las notificaciones (Spec 047) son internas de la aplicación, inservibles para quien no puede entrar |
| Reset administrativo de contraseña | **No existe** (solo el alta de usuario con contraseña temporal y el reset de **MFA**) |
| Rotura de cristal local | Solo `mfa_breakglass` (MFA). No hay una para la contraseña |
| Frontend | `/reset-password` (`ResetPasswordPage`): pide empresa y usuario y, si llega `reset_token`, **lo muestra en pantalla** («Modo demostración») y lo precarga. Enlace «¿Olvidó su contraseña?» en el login |
| Pruebas | `tests/test_password_reset.py` lee `reset_token` de la respuesta (dependen del defecto). Sin E2E del reset |
| Límites | Sin límite propio; el límite genérico por IP es la deuda DT-16 (`GENERIC_LOGIN_RATE_LIMIT_DEBT = PRESERVED`) |

## 2. Reproducción (B1)

Sonda en proceso contra el árbol de entrada, con identidades sintéticas del arnés de pruebas. Guarda solo formas, nunca valores
(`evidence/password-reset-token/reproduccion.txt`).

| Caso | HTTP | Forma de la respuesta | Token | Mediana (7 intentos) |
|---|---|---|---|---|
| Usuario existente | 200 | `{ok, reset_token}` | **presente** | 11,0 ms |
| Usuario inexistente | 401 | error `AUTH_INVALID_CREDENTIALS` | no | 9,5 ms |
| Tenant inexistente | 401 | error `AUTH_INVALID_CREDENTIALS` | no | 7,8 ms |
| Confirmar y luego reutilizar en serie | 200 y 401 | `RESET_TOKEN_INVALID` | — | — |

Quedan confirmadas la **divulgación del token** y la **enumeración** (código de estado y cuerpo).

## 3. Causa raíz

1. La ruta se escribió como «flujo demo» de la fundación (la entrega por correo quedó diferida) y nunca se cerró.
2. La respuesta anónima depende de la existencia de la cuenta.
3. El contrato del token no fija TTL, invalidación ni consumo atómico.
4. Las sesiones no están ligadas a la credencial con la que se abrieron.

## 4. Decisiones de la dueña aplicadas

| OD | Contenido | Dónde |
|---|---|---|
| OD-AUTHRESET-01 | Nunca se devuelve el token a un cliente anónimo (JSON, cabecera, HTML, URL, registros, auditoría, analítica, evidencia, excepción) | R-RST-01, §9, §11 |
| OD-AUTHRESET-02 | Respuesta pública idéntica exista o no la cuenta, esté inactiva o no se pueda entregar | R-RST-02, §9 |
| OD-AUTHRESET-03 | Solo canal de confianza fuera de banda; sin proveedor verificado, la solicitud es genérica y falla cerrada, y la recuperación soportada es la administrativa o la local | §6, D-01 |
| OD-AUTHRESET-04 | Token CSPRNG ≥ 256 bits, opaco, de un solo uso, solo hash, TTL 15 min, el nuevo invalida los anteriores, consumo atómico | R-RST-03..06 |
| OD-AUTHRESET-05 | El reset no desactiva ni borra el MFA ni sus códigos; el siguiente login exige MFA si aplica | R-RST-08 |
| OD-AUTHRESET-06 | Un reset correcto revoca todas las sesiones e invalida los demás tokens; nada revocado sigue vivo hasta su TTL | R-RST-07, D-03 |

## 5. Requisitos

| ID | Requisito |
|---|---|
| R-RST-01 | Ninguna respuesta de la solicitud anónima contiene el token ni nada derivado de él; el esquema OpenAPI no tiene la propiedad `reset_token` |
| R-RST-02 | `POST /auth/password-reset/request` responde **202** con el cuerpo fijo `{"ok": true}` para usuario existente, inexistente o inactivo y para tenant inexistente; sin cabeceras que dependan de la cuenta; las diferencias de tiempo se acotan (§12) |
| R-RST-03 | Token `secrets.token_urlsafe(32)` (256 bits), opaco; en BD solo `sha256_hex(token)`, con **índice único** |
| R-RST-04 | TTL **15 min** (`PASSWORD_RESET_TTL_MINUTES = 15`) |
| R-RST-05 | Emitir un token nuevo para un usuario invalida (`invalidated_at`) sus tokens activos, en la misma transacción |
| R-RST-06 | Consumo atómico: `UPDATE … SET used_at = :ahora WHERE id = :id AND used_at IS NULL AND invalidated_at IS NULL AND expires_at > :ahora` con `rowcount == 1`; de dos usos concurrentes gana **exactamente uno** |
| R-RST-07 | Un reset correcto, en una transacción: (a) cambia el hash, (b) **rota el sello de credencial**, (c) revoca todas las sesiones, (d) invalida los demás tokens del usuario y (e) audita. Toda sesión cuyo sello no coincida con el actual del usuario se rechaza en `get_current_auth` y en la renovación, aunque no esté revocada (cubre la carrera con un login en curso) |
| R-RST-08 | El reset no toca `auth_mfa_factors` ni `mfa_recovery_codes` ni `users.mfa_enabled`; el siguiente login de una cuenta con MFA obligatorio pasa por el desafío |
| R-RST-09 | Confirmación: `POST /auth/password-reset/confirm` → 200 `{"ok": true}`, o error determinista **400** `RESET_TOKEN_INVALID` (desconocido, alterado, usuario inexistente o inactivo), `RESET_TOKEN_EXPIRED`, `RESET_TOKEN_USED` (usado o invalidado), y **422** `PASSWORD_POLICY`; nunca 500 |
| R-RST-10 | Recuperación soportada sin canal fuera de banda: **rotura de cristal local** `python -m app.modules.identity_access.password_breakglass --tenant T --username U --confirm U --salida RUTA`. Emite un token (R-RST-03..05) y lo escribe **solo** en `RUTA` (modo 0600; se niega si existe); nunca por la salida estándar ni en registros; audita `PASSWORD_RESET_ADMIN_INITIATED` con fuente `CLI`; rechaza usuarios inactivos o inexistentes con un mensaje que no imprime datos internos. Quien lo ejecuta entrega el token por un canal de confianza y la persona elige su contraseña en `/reset-password` (el operador nunca la conoce) |
| R-RST-11 | La solicitud anónima no crea tokens (no hay canal de entrega). Audita `PASSWORD_RESET_REQUESTED` (resultado `NOT_DELIVERABLE`) solo si la cuenta existe y como mucho una vez por usuario cada 15 min (sin inundar la auditoría desde fuera) |
| R-RST-12 | Auditoría con lista blanca, sin token ni contraseñas: `PASSWORD_RESET_REQUESTED`, `PASSWORD_RESET_ADMIN_INITIATED`, `PASSWORD_RESET_COMPLETED`, `PASSWORD_RESET_FAILED` (con el motivo: `EXPIRED`, `USED` o `INVALID`; el último sin entidad), `PASSWORD_RESET_TOKEN_INVALIDATED`, y `SESSIONS_REVOKED_SECURITY_CHANGE` (existente) |
| R-RST-13 | El token no se escribe en el almacenamiento del navegador, no viaja en la URL, el formulario no lo autocompleta y la pantalla no lo muestra tras enviarlo |
| R-RST-14 | El cambio de contraseña propio (`/auth/password/change`) también rota el sello y conserva la sesión actual (actualiza su sello) e invalida los tokens pendientes |

## 6. Modelo de proceso

```
Persona sin acceso ─► /reset-password (paso «Solicitar») ─► 202 genérico ─► «Si la cuenta puede recuperarse…»
                                                          (sin token: no hay canal)
Persona ─► contacta con soporte ─► operador del servidor:
        password_breakglass --confirm --salida RUTA  ─► token (15 min, un uso) en RUTA (0600)
        ─► entrega por canal de confianza (en persona o por teléfono verificado)
Persona ─► /reset-password (paso «Tengo un código») ─► código + nueva contraseña ×2 ─► 200
        ─► sesiones revocadas, sello rotado, demás tokens invalidados, MFA intacto ─► /login (+ MFA si aplica)
```

El reset administrativo **web** no existe y no se crea aquí (D-02, FUTURE_SPEC).

## 7. Modelo de dominio y de datos (migración `0059_spec002_password_reset`)

| Tabla / columna | Cambio | Autoridad |
|---|---|---|
| `password_resets.invalidated_at` | Nueva, `DateTime(tz)`, nula | Servicio de reset |
| `password_resets.token_hash` | Pasa a **único** (`uq_password_resets_token_hash`) | BD |
| `password_resets.source` | Nueva, `String(16)`, no nula, por defecto `'SELF'` (`SELF` o `CLI`) | Servicio |
| `users.credential_stamp` | Nueva, `String(32)`, no nula. **Relleno:** un valor aleatorio distinto por usuario existente (`secrets.token_hex(16)`) | Solo los cambios de contraseña la rotan |
| `auth_sessions.credential_stamp` | Nueva, `String(32)`, nula. **Relleno:** el sello actual de su usuario, para no cerrar las sesiones vivas al migrar | Se fija al crear la sesión y se copia al rotar |
| `mfa_challenges.credential_stamp` | Nueva, `String(32)`, nula. **Relleno:** el sello de su usuario | Se fija al verificar la contraseña; la sesión que nace del desafío lo hereda |

**Invariantes:**
- Sesión válida ⇔ `revoked_at IS NULL` ∧ `credential_stamp = users.credential_stamp` (también en la renovación).
- Login, MFA y alta por desafío capturan el sello **en la misma lectura** en que leen el hash que verifican.
- Ámbito: `password_resets` hereda el tenant de `user_id` (sin cambios).
- La migración es reversible (`downgrade` quita columnas e índice) y se prueba en instalación limpia y en actualización, en PostgreSQL.

## 8. Modelo de seguridad (amenazas → control → prueba)

| Amenaza | Control | Prueba |
|---|---|---|
| Divulgación del token | R-RST-01: el request no devuelve token; esquema sin `reset_token` | RST-A01, RST-OAS |
| Enumeración de cuentas | R-RST-02: 202 y cuerpo idénticos; el tenant desconocido entra por el mismo camino | RST-A02..A04 |
| Oráculo de tiempo | §12: misma secuencia de consultas en ambos caminos; mediciones registradas | RST-T01 (medición, no aserción frágil) |
| Robo del token | 15 min, un uso, entrega fuera de banda, nunca en URL ni almacenamiento | RST-B*, E2E |
| Repetición del token | Consumo condicional (R-RST-06) | RST-B03 |
| Fuerza bruta del token | 256 bits; búsqueda por hash único | RST-B04 (alterado → INVALID) |
| Inundación de solicitudes y notificaciones | Sin token ni entrega en la solicitud; auditoría limitada por usuario (R-RST-11); el límite por IP es DT-16 (preservada) | RST-A05 |
| Reset entre tenants o entre usuarios | El token liga `user_id`; la rotura de cristal resuelve el tenant por código y el usuario dentro de él | RST-C01, RST-CLI03 |
| IDOR / BOLA | La confirmación no acepta `user_id`; solo el token | RST-B05 |
| Escalada del administrador | Sin ruta web; la CLI es local (acceso al servidor = confianza máxima) y queda auditada | RST-CLI01 |
| Sesión que sobrevive al reset | Revocación + sello (R-RST-07) | RST-S01..S04 |
| Degradación del MFA | R-RST-08 | RST-M01, RST-M02 |
| Fuga en registros o auditoría | Lista blanca; token y contraseñas nunca en `details`; el error no los incluye | RST-L01, RST-L02 |
| Fuga en el almacenamiento del navegador | R-RST-13 | vitest RST-UI, E2E |
| Fuga por Referer, URL o historial | El token se teclea; nunca en la URL | E2E (URL sin token) |
| Uso concurrente del mismo token | R-RST-06 | RST-B06 (hilos, en PostgreSQL) |
| Reutilización de un token antiguo | R-RST-05 | RST-B07 |
| Token débil | `token_urlsafe(32)` | RST-B08 (longitud y alfabeto) |
| Token en claro en la BD | Solo hash | RST-B09 |

## 9. Contrato de API

| Ruta | Antes | Después |
|---|---|---|
| `POST /api/v1/auth/password-reset/request` `{tenant_code, username}` | 200 `{ok, reset_token}` / 401 | **202** `{"ok": true}` siempre (validación de forma: 422 si falta un campo, igual para todos) |
| `POST /api/v1/auth/password-reset/confirm` `{token, new_password}` | 200 / 401 / 422 | 200 `{"ok": true}` · 400 `RESET_TOKEN_INVALID` / `RESET_TOKEN_EXPIRED` / `RESET_TOKEN_USED` · 422 `PASSWORD_POLICY` |

Las dos rutas siguen exentas de licencia y siguen siendo públicas por contrato. OpenAPI: modelos de respuesta explícitos sin la
propiedad `reset_token` (OPENAPI_UNEXPLAINED_DRIFT = 0).

## 10. Modelo UX/UI

### 10.1 Inventario de pantallas

| SCREEN_ID | Pantalla | Proceso | Objetivo | Actores | Revela | No revela |
|---|---|---|---|---|---|---|
| RST-S01 | `/reset-password`, paso «Solicitar» | P-RST-01 | Pedir recuperación | Persona sin acceso | Mensaje neutro | Existencia, estado, rol, MFA, destino |
| RST-S02 | `/reset-password`, paso «Tengo un código» | P-RST-02 | Fijar una contraseña nueva con el código recibido | Persona con código | Resultado y orientación sobre MFA y sesiones | El código tras enviarlo |
| RST-S03 | Resultado (éxito) | P-RST-02 | Volver a entrar | — | «Contraseña actualizada; sus sesiones se cerraron; entre de nuevo (y verifique su segundo factor si lo usa)» | — |
| RST-S04 | Estados del código: inválido, caducado, usado | P-RST-02 | Saber qué hacer | — | Pedir un código nuevo a soporte | — |
| RST-S05 | Reset administrativo web | — | **No existe** (D-02) | — | — | — |
| RST-S06 | Cambio forzado de contraseña | — | No aplica: el flujo no usa credencial temporal (la persona elige la contraseña) | — | — | — |

### 10.2 Contrato de campos

| FIELD_ID | Etiqueta | Tipo | Obligatorio | Validación UI → backend | Error | Ayuda | Auditoría | API / BD / UI |
|---|---|---|---|---|---|---|---|---|
| RST-F01 | «Empresa (código)» | texto, `autocomplete=organization` | sí | no vacío → existencia **no** comprobada en público | «Indique la empresa» | — | nunca | `tenant_code` / — / estado local |
| RST-F02 | «Usuario» | texto, `autocomplete=username` | sí | no vacío → idem | «Indique el usuario» | — | nunca | `username` |
| RST-F03 | «Código de recuperación de contraseña» | texto, `autocomplete=off`, `spellcheck=false`, máx. 64 | sí | no vacío → hash y estado | Mensajes de RST-S04 | «Se lo entrega el soporte; caduca a los 15 minutos y sirve una vez» | nunca el valor; `PASSWORD_RESET_FAILED` sin entidad si es inválido | `token` / `token_hash` / se borra del estado al enviar |
| RST-F04 | «Nueva contraseña» | `type=password`, `autocomplete=new-password` | sí | política (≥ 10, minúscula, mayúscula, número, no común) → `PASSWORD_POLICY` | Lista de incumplimientos | Texto de la política | nunca | `new_password` / Argon2id |
| RST-F05 | «Confirmar nueva contraseña» | `type=password`, `autocomplete=new-password` | sí | igual a RST-F04 (solo UI) | «Las contraseñas no coinciden» | — | nunca | solo UI |

### 10.3 Estados

| Estado | S01 | S02 |
|---|---|---|
| NORMAL, LOADING, SUCCESS | ✔ (éxito = mensaje neutro, igual para todos) | ✔ |
| ERROR, OFFLINE | ✔ «Sin conexión…» | ✔ |
| VALIDATION_ERROR | ✔ campos vacíos | ✔ política y coincidencia |
| RATE_LIMITED | N/A (DT-16; el 202 no cambia) | N/A |
| TOKEN_INVALID / TOKEN_EXPIRED / TOKEN_USED | — | ✔ mensajes distintos y accionables |
| PROCESS_BLOCKED | ✔ el texto explica que la recuperación la gestiona el soporte | — |
| PERMISSION_DENIED / REAUTH_REQUIRED | N/A (no hay flujo administrativo web) | N/A |
| CONCURRENT_MODIFICATION | — | ✔ el segundo envío del mismo código ve `RESET_TOKEN_USED` |

Reglas:
- Doble envío: el botón asíncrono se bloquea mientras dura la petición.
- El código no se precarga ni se muestra.
- Se elimina el «Modo demostración».
- El enlace «¿Olvidó su contraseña?» se conserva.

## 11. Auditoría

Lista blanca de `details`:
- `source` (`SELF`/`CLI`);
- `outcome`;
- `reason` (`EXPIRED`/`USED`/`INVALID`);
- `revoked_sessions` (número);
- `invalidated_tokens` (número).

Nunca va en la auditoría el token, su hash, contraseñas, IP del solicitante anónimo ni el `username` tecleado si la cuenta no existe.

## 12. Abuso y tiempo

- **La solicitud anónima** no tiene efectos amplificables: no crea token ni envía nada. Cuando aparezca un canal, su Spec deberá limitar
  por cuenta y por origen. Requisito de futuro.
- **Mismo trabajo en ambos caminos (existe o no):**
  - se resuelve el tenant y se busca el usuario, siempre;
  - la consulta de la limitación de auditoría se hace siempre, con `user_id` nulo si no hay cuenta;
  - la respuesta se construye igual.
- **Medición:** se registran las medianas de cada caso en la evidencia (RST-T01); no hay aserción temporal, porque sería frágil.
- **Fuerza bruta del token:** se descarta por la entropía.
- **Límite por IP:** es la deuda DT-16, preservada (no se absorbe).

## 13. Concurrencia

| Carrera | Control | Prueba (PostgreSQL, hilos) |
|---|---|---|
| Dos usos del mismo token | R-RST-06 | Exactamente 1 éxito y 1 `RESET_TOKEN_USED` |
| Dos emisiones para el mismo usuario | Invalidación en la misma transacción; índice único del hash | Queda 1 activo |
| Token antiguo tras uno nuevo | `invalidated_at` | `RESET_TOKEN_USED` |
| Reset frente a login en curso | Sello (R-RST-07) | La sesión creada con el sello antiguo → 401 en la siguiente petición |
| Reset frente a renovación | La renovación comprueba el sello y la revocación | Renovación → 401 |
| Reset frente a reset de MFA | Transacciones independientes; ninguna borra el trabajo de la otra; el sello rota igual | Ambos efectos presentes y sin 500 |

## 14. Decisiones de diseño

| ID | Decisión | Motivo |
|---|---|---|
| D-01 | Sin canal fuera de banda, la solicitud **no crea token** | Un token que nadie puede recibir solo crea estado y superficie |
| D-02 | El reset administrativo **web** queda como FUTURE_SPEC (recomendado, con la DELEGATION CEILING: capacidad SENSITIVE, MFA, reautenticación, techo, mismo tenant, nunca a sí mismo, token entregado fuera de banda, nunca una contraseña que conozca el administrador) | No existe hoy; crearlo es otra capacidad y otra superficie; la rotura de cristal local cubre la recuperación (patrón `mfa_breakglass`, §25 del encargo) |
| D-03 | Sello de credencial en usuario, sesión y desafío | Es el único control que cierra la carrera login/reset sin depender de relojes |
| D-04 | La CLI escribe el token en un fichero 0600 y no en la salida estándar | Evita historiales, registros de terminal y capturas |
| D-05 | Errores de confirmación en 400 con tres códigos | Son estados del negocio, no fallos de autenticación; distinguir caducado/usado no revela nada a quien no tiene el token |
| D-06 | La E2E obtiene el token ejecutando la CLI real dentro de la corrida (estado efímero, fuera de la evidencia) y la corrida retira de la evidencia los artefactos que lo contengan | Canal de confianza del arnés sin «modo de prueba» en el producto (OQ-MFA-3 por analogía) |

## 15. Constitution gate

| Principio | Estado |
|---|---|
| P1 Spec antes que código | PASS: este delta; 0 código antes de la autorización |
| P2 Autorización expresa | PASS: el encargo de la Fase B autoriza la iniciativa nombrándola |
| P3 Trazabilidad | PASS (§19) |
| P6 Seguridad en backend | PASS: token, sello y estado, todo en el backend |
| P7 / P17 Frontend uniforme | PASS: componentes compartidos (`FormField`, `AsyncButton`) |
| P10 Calidad demostrable | PASS: §16, negativas, concurrencia, mutaciones y E2E |
| P11 Accesibilidad | PASS: §10, axe y 320 px |
| P12 Decisiones documentadas | PASS: D-01..06 |
| P13 Integridad transaccional | PASS: R-RST-05..07 en una transacción |
| P15 Datos del cliente protegidos | PASS: solo hash; nada en registros |
| P18 Modales | PASS: pantalla completa, sin diálogos |
| P21 Paridad de motor | PASS: PostgreSQL autoritativo y SQLite |
| P24 Instalación limpia | PASS: `0059` en limpia y en actualización |
| P25 La concurrencia la gobierna la base | PASS: UPDATE condicional e índice único |
| P26 Paridad modelo↔migración | PASS: prueba de la migración |
| P27 Mutación observable | PASS (§16) |

BLOCKER = 0 · CRITICAL = 0 (el CRITICAL es el defecto que se corrige) · CONTRADICTIONS = 0 · OWNER CONFLICT = 0 · MATERIAL OQ = 0 ·
UNKNOWN = 0.

## 16. Plan, tareas y pruebas

Todas las tareas tienen:
- SECURITY_SENSITIVE = sí, EGRESS_SAFE = sí (identidades sintéticas, sin valores) y RETRY_MAX = 2;
- EXECUTOR = DeepSeek para el código y las pruebas (regla de la dueña del 2026-10-18), con diseño y auditoría de Claude (CLAUDE_ONLY por
  ser autenticación, sesiones y migración).

| Tarea | Contenido | MODEL | FILES | DONE_WHEN |
|---|---|---|---|---|
| TR-A | Pruebas en ROJO (backend): RST-A01..A05, B03..B09, S01..S04, M01..M02, L01..L02, CLI01..CLI04, C01, migración | v4-pro | `tests/test_password_reset_security.py` (nueva), `tests/test_spec002_migration_0059.py` (nueva) | Rojo por causa atribuida |
| TR-1 | Modelo y migración `0059` (columnas, índice único, relleno de sellos) | v4-pro | `identity_access/models.py`, `alembic/versions/0059_…` | Migración verde (limpia y actualización), PostgreSQL y SQLite |
| TR-2 | Servicio: solicitud sin token, emisión con invalidación, consumo atómico, confirmación, sello en login/MFA/refresh/cambio propio, auditoría | v4-pro | `identity_access/service.py`, `mfa_service.py`, `core/dependencies.py` | TR-A verde |
| TR-3 | API: 202 genérico, errores 400 y modelos de respuesta | v4-flash | `identity_access/api.py` | RST-A y OAS verdes |
| TR-4 | CLI `password_breakglass` | v4-flash | `identity_access/password_breakglass.py` | RST-CLI verdes |
| TR-5 | Ajuste de pruebas que dependían del defecto | v4-flash | `tests/test_password_reset.py` y otras medidas | Suites verdes |
| TR-6 | Frontend: `ResetPasswordPage` (dos pasos, sin token visible, estados) y vitest | v4-pro | `src/pages/ResetPasswordPage.tsx` y su prueba | vitest, tsc, lint |
| TR-7 | E2E y arnés: obtener el token con la CLI en la corrida, purga de la evidencia | v4-pro | `e2e/password-reset.spec.ts`, `qa/…` | E2E verde en 3 motores |
| TR-8 | Mutaciones (Claude, herramienta local) | — | — | 0 supervivientes |

Mutaciones previstas (§48 del encargo):
- devolver el token;
- respuesta distinta si la cuenta no existe;
- token en claro;
- sin caducidad;
- reutilización;
- doble éxito concurrente;
- sin revocar sesiones;
- sin comprobar el sello;
- desactivar el MFA;
- token en el registro;
- token en la auditoría;
- CLI sin confirmación;
- reset entre tenants;
- sin limitación de la auditoría anónima.

## 17. Checklist

| Ítem | Estado |
|---|---|
| Requisitos medibles y sin ambigüedad (R-RST-01..14) | ✔ |
| Cada amenaza con control y prueba (§8) | ✔ |
| Estados de pantalla y contrato de campos (§10) | ✔ |
| Migración reversible con relleno definido (§7) | ✔ |
| Deudas no absorbidas declaradas (§21) | ✔ |
| Sin dependencias nuevas | ✔ |

## 18. Analyze

- Requisitos huérfanos: 0. Tareas huérfanas: 0. Contradicciones: 0.
- R-RST-14 amplía el cambio de contraseña propio. Es necesario para que el sello no cierre la sesión de quien cambia su propia
  contraseña, y para que un token pendiente no sobreviva a un cambio voluntario.
- No hay expansión silenciosa de alcance: el reset administrativo web, el canal fuera de banda y el límite por IP quedan fuera y
  declarados.

## 19. Trazabilidad

| Requisito | Diseño | Prueba | Evidencia |
|---|---|---|---|
| R-RST-01 | §9 | RST-A01, OAS | rojo → verde |
| R-RST-02 | §9, §12 | RST-A02..A04, T01 | rojo → verde, medianas |
| R-RST-03..06 | §7, §13 | RST-B03..B09 | verde, concurrencia en PostgreSQL |
| R-RST-07 | §7, D-03 | RST-S01..S04 | verde |
| R-RST-08 | §4 | RST-M01..M02, E2E | verde |
| R-RST-09 | §9 | RST-B01..B05 | verde |
| R-RST-10 | §6, D-04 | RST-CLI01..CLI04, E2E | verde |
| R-RST-11 | §12 | RST-A05 | verde |
| R-RST-12 | §11 | RST-L01..L02 | verde |
| R-RST-13 | §10 | vitest, E2E | verde |
| R-RST-14 | §7 | RST-S04 | verde |

## 20. Requisitos de Gobierno (fuente releída: `requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf`)

| Requisito | Aplicación | Estado |
|---|---|---|
| RNF-GOV-011 seguridad (secretos fuera del código, rotación de credenciales) | Token solo como hash; sello de credencial; rotación por reset y por cambio propio | COVERED en la recuperación de contraseñas; la rotación periódica obligatoria es FUTURE_GOV_SPEC |
| RNF-GOV-006 autorización en backend | Token, sello y estado en el backend; sin control solo en la UI | COVERED |
| RNF-GOV-012 mínimo privilegio | Sin reset administrativo web (D-02); la CLI exige acceso al servidor | COVERED (el reset web, con la DELEGATION CEILING) |
| RNF-GOV-005 / GOV-CTL-002 / GOV-CTL-003 trazabilidad | Eventos de §11 con actor, fuente, sesión y `request_id` | COVERED; la inmutabilidad append-only es FUTURE_GOV_SPEC |
| GOV-CTL-004 administrador técnico | La CLI no fija contraseñas: entrega un token y la persona elige; queda auditada | COVERED por diseño |
| RNF-GOV-017 observabilidad sin secretos | §11 y RST-L01..L02 | COVERED |
| RNF-GOV-019 migraciones | `0059`, cabeza única, limpia y actualización en PostgreSQL | COVERED |
| RNF-GOV-020 QA | §16 | COVERED |
| RNF-GOV-014 accesibilidad | §10, axe y 320 px | COVERED |
| E2E-06 hostil multi-ente | RST-C01, RST-CLI03 | COVERED |
| GOV-DIG-004 intercambio entre organismos | No aplica (recuperación de personas) | FUTURE_GOV_SPEC |

ENGINEERING_REQUIREMENTS_DOCUMENT_REVIEWED = 1 · ENGINEERING_REQUIREMENTS_RECONCILED = 1 (de diseño; se reabre al cierre) ·
GOVERNMENT_REQUIREMENT_LINKAGE_RECONCILED = 1 · UNEXPLAINED_REQUIREMENT_OMISSIONS = 0.

## 21. Revisión multidisciplinar

| Perspectiva | Conclusión |
|---|---|
| Funcional | La persona sin acceso tiene camino (soporte → código → contraseña propia) |
| Seguridad | §8 completo; el CRITICAL se cierra |
| Arquitectura | El sello es un concepto nuevo y transversal de sesión; se documenta en ADR-004 (extensión) |
| Datos y BD | §7: migración reversible con relleno |
| UX/UI | §10: textos neutros y accionables; sin modo demo |
| Accesibilidad | Etiquetas, errores asociados, foco y 320 px |
| API | §9: contrato público estable y determinista |
| Auditoría | §11: lista blanca |
| Operaciones | Runbook de `password_breakglass` en `backup-restore-plan.md` §7 |
| Soporte | Procedimiento de verificación de identidad antes de emitir un código: responsabilidad organizativa, anotada en el runbook |
| QA | §16 y E2E en 3 motores |
| Preparación para Gobierno | §20 |

MULTIDISCIPLINARY_REVIEW_COMPLETE = 1.

## 22. Deudas (no absorbidas)

| DEBT_ID | Severidad | Siguiente acción |
|---|---|---|
| PASSWORD-RESET-OOB-CHANNEL-MISSING | MEDIUM | Spec de notificaciones fuera de banda (correo o SMS verificados) con límites por cuenta y por origen |
| ADMIN-PASSWORD-RESET-WEB-MISSING | MEDIUM | Con la DELEGATION CEILING (D-02) |
| GENERIC_LOGIN_RATE_LIMIT_DEBT | — | PRESERVED (DT-16) |

## 23. Autorización

`implement` autorizado por el encargo, que nombra la iniciativa (P2). Las decisiones OD-AUTHRESET-01..06 están ratificadas, MATERIAL OQ = 0
y el gate da PASS.

## 24. Ejecución y evidencia (cierre, 2026-10-26)

**Reparto y formato:**
- **DeepSeek:** todo el código, las pruebas, la migración, el frontend, la E2E y la documentación de producto.
- **Claude:** diseño, auditoría, aplicación tal cual y verificación (`evidence/password-reset-token/orchestration.md`).
- **Formato hecho por Claude:** `ruff --select I --fix` en dos ficheros.

| Verificación | Resultado |
|---|---|
| Reproducción (B1) | `reproduccion.txt`: token en la respuesta y 401 en las cuentas inexistentes, confirmados |
| Rojo atribuido | `rojo-tr-a1.txt`: 27 rojas por el defecto o por la capacidad ausente, más 3 de la migración |
| Pruebas de seguridad del reset | `test_password_reset_security.py`: 33 pasan + B06 (concurrencia, solo PostgreSQL); `test_spec002_migration_0059.py` 4/4 en PostgreSQL |
| Suites dirigidas (reset, MFA, rotación, OpenAPI) | SQLite 175/0 · PostgreSQL 191/0 |
| Mutaciones | 20/20 muertas (`mutaciones.md`); la primera corrida dejó 5 supervivientes, que mataron las pruebas S05–S08 y B11 |
| Frontend | vitest 556/556 (`ResetPasswordPage.test.tsx` 10/10) · tsc 0 · eslint 0 · build correcto |
| E2E del reset | 21/21 (7 casos × chromium, firefox y webkit), sin trazas ni capturas (código fuera de la evidencia); REAL_SAFARI_NOT_MEASURED |
| E2E canónica completa con analizador | **313 pasan · 0 fallan · 0 omitidas**; limpieza LIMPIA; `material_mfa` 0; bases protegidas sin cambios; 0 bases de corrida (`r20261026t140815…`) |
| Backend completo PostgreSQL / SQLite con analizador | ver §24.1 |
| OpenAPI | La solicitud declara 202 (sin 200) y `reset_token` no aparece en todo el esquema (OAS01); OPENAPI_UNEXPLAINED_DRIFT = 0 |
| mypy / ruff | ruff limpio; mypy sin errores nuevos (154, todos en líneas confirmadas antes del ciclo) |

**Riesgos residuales, aceptados y anotados:**
- **La caducidad de 15 min no se prueba en la E2E:** no se controla el reloj del servidor ni se puede esperar. La cubren B08 y vitest 6.
- **Una aserción de la E2E podría imprimir el código:** si fallara la de URL en el caso 02, el código saldría en `suite.log`. Ese código ya sería de un solo uso, estaría consumido o caducado, y su base se destruye al final de la corrida.

### 24.1 Backend completo (analizador real y telemetría, `qa/suite_tiempos.py`)

| Motor | Resultado |
|---|---|
| PostgreSQL, primera corrida (`r20261026t141552…`) | 3424 pasan · **2 fallan** (A06 y B09). Causa medida: el reloj de suite inyectado se adelantaba ~11 h y la ventana de auditoría (producto) y B09 (prueba) mezclaban ese reloj con `created_at` (reloj real). Reproducido con un desfase de 12 h en ambos motores → TR-2c (producto) y TR-A1d (prueba); en verde con el desfase |
| PostgreSQL, corrida final (`r20261026t150112…`) | **3426 pasan · 0 fallan · 18 omitidas** · anomalía NORMAL |
| SQLite, corrida final (`r20261026t153732…`) | **2370 pasan · 0 fallan · 1074 omitidas** (solo PostgreSQL) · NORMAL |

## 25. Reconciliación final de Gobierno

§20 se ratifica sin cambios tras releer la fuente al cierre. El sello de credencial añade cobertura a:
- **RNF-GOV-011:** rotación efectiva de la credencial a efectos de sesión;
- **RNF-GOV-006:** la autoridad de sesión está en el backend.

ENGINEERING_REQUIREMENTS_RECONCILED = 1 (final) · UNEXPLAINED_REQUIREMENT_OMISSIONS = 0 · GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0.

## 26. Convergencia

`/speckit-converge` no se aplica a un delta, por el mismo motivo medido en el delta MFA (§24.4): el prerrequisito resuelve la Spec 012,
que no tiene `spec.md` ni `plan.md`. Convergencia equivalente:

| Dimensión | Resultado |
|---|---|
| Requisitos | R-RST-01..14 implementados y probados (§19) |
| Tareas (§16) | Todas hechas. TR-A1/A2/1/2/4/6/7 se dividieron al agotar reintentos (TR-A1b/c, TR-1c, TR-2b, TR-4b, TR-A3a/b); TR-5a nació de la prueba M03 de la 0058 |
| Código | Sin código no pedido; `ResetAcknowledged` y `extra="forbid"` son contrato de §9 |
| Pruebas | Rojo atribuido, mutaciones 20/20 y E2E en 3 motores |
| Pantallas y formularios | Gate PASS (`screen-form-completeness.md`) |
| Deuda | §22 sin absorber; ninguna pasó a bloqueante |
| Residuos y Git | Ver el informe de cierre |

PASSWORD_RESET_CONVERGENCE = PASS.
