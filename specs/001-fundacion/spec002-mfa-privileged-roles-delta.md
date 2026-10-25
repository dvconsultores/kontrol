# SPEC 002/003 · Delta — SHARED-CORE-P0-HARDENING-01 · MFA FOR PRIVILEGED ROLES

| Campo | Valor |
|---|---|
| Specs dueñas | **002** (Seguridad / Sesiones) · **003** (Usuarios / Roles / Alcance). Ninguna tiene carpeta propia (OBS-04 SPEC-SEGURIDAD-SIN-CARPETA, D, sigue abierta): la delta se aloja en `specs/001-fundacion/`, donde vive FR-001-024 («MFA preparado, habilitable»). Alojarla aquí **no** resuelve OBS-04 |
| Clase | SHARED_CORE HARDENING (gap P0 n.º 1 de OD-GSR-2). No es GOV-0 ni GOV-SPEC |
| Decisiones | OQ-GAB-2 = A (TOTP + códigos de recuperación + reautenticación; WebAuthn futuro) · OD-GSR-2 = A · contrato de seguridad de la dueña (Master Prompt §88–91) |
| HEAD de entrada | `37bc083` |
| Evidencia | `evidence/mfa-privileged-roles/` (se crea al implementar) |
| GOVERNMENT_IMPLEMENTATION_AUTHORIZED | 0 |
| Estado | **DESIGN COMPLETE — BLOCKED_BY_OWNER_DECISION** (OQ-MFA-1..3). DEEPSEEK CALLS = 0 |

## 1. Discover (medido en `37bc083`)

### 1.1 Estado actual

| Área | Medida |
|---|---|
| Requisito previo | FR-001-024 (P2): «MFA preparado (habilitable) sin implementar los flujos»; CVG-09 «Pendiente»; `security-baseline.md`: «obligatorio para propietario y perfiles críticos»; MASTER57: 002 «MFA declarado y no construido» |
| Modelo | `User.mfa_enabled` (bool, default `False`) existe y **nadie lo lee ni lo escribe** (0 usos en `app/` y `src/`) |
| Login | `POST /auth/login` → `authenticate` (Argon2id, bloqueo 5 fallos → 15 min, `LOGIN_FAILED/BLOCKED/SUCCESS` auditados) → `create_session` → access JWT HS256 de 15 min (`sub`, `type`, `iat`, `exp`, `tenant_id`) + refresh de 14 días en cookie HttpOnly con fila `sessions` (`refresh_token_hash`) |
| Refresh | `rotate_session`: un solo uso, `FOR UPDATE` + UPDATE condicional (`revoked_at IS NULL`); reutilización → 401 |
| Sesión por petición | `get_current_user` decodifica el access token y carga el usuario: **no lleva `sid` ni consulta la revocación**. Un access token sobrevive hasta 15 min a la revocación de su sesión |
| Cambio de credencial | `change_password` y `confirm_password_reset` **no revocan** las sesiones vivas |
| Límites | solo el bloqueo por usuario; `login_rate_limit_per_minute = 5` está declarado en `Settings` y **no se usa** (configuración muerta). Límites por ruta: DT-16, BLOCKED_BY_OWNER_DECISION → Spec 055 |
| RBAC | permisos `resource:action`; `require_permission`; rol protegido `ADMIN` (sembrado por `setup` con todos los permisos); roles por empresa (`Role.company_id`); `UserRole` con vigencia |
| Auditoría | `app/shared/audit.py::record_audit(action, entity_type, …, before, after, reason, evidence, ip)`: `before`, `after` y `evidence` son diccionarios libres, y por ahí podría fugarse un secreto |
| Cifrado | `cryptography==50.0.2` ya está en `requirements.lock` (AES-GCM disponible sin dependencias nuevas). TOTP (RFC 6238) cabe en la stdlib (`hmac`, `hashlib`, `struct`, `base64`, `secrets`) |
| QR | ninguna librería de QR en backend ni frontend |
| Frontend | `LoginPage.tsx` (137 líneas); `AuthContext` con el access token en memoria (ADR-004); `client.ts` con `refreshOnce` de vuelo único; `ConfirmationDialog` compartido; P18: los modales solo para confirmaciones breves |
| Pruebas backend | 52 llamadas a `/auth/login` en ~43 ficheros, cada uno con su propio `_login` (no hay helper común) |
| Pruebas E2E | 40 llamadas API a `/auth/login` y 38 ficheros con login por UI; helpers `entrar`/`loginConRastro` duplicados por fichero; sin `storageState`. El usuario E2E `admin` tiene el rol `ADMIN`. Duración medida de la suite: 291,8 s (4,9 min) |
| Configuración | `secret_key` obligatoria en todo entorno; `_trust_anchor_required_in_prod`; `_s3_no_soportado`. Los guiones de QA fijan `KONTROL_SECRET_KEY` con `setdefault` |
| Migraciones | 57 (`0057_spec047_notifications.py`); la siguiente es la `0058` |

### 1.2 Hallazgos que entran en el alcance

| Id | Hallazgo | Amenaza | Tratamiento |
|---|---|---|---|
| F1 | El access token no se liga a la sesión, así que la revocación tarda hasta 15 min en surtir efecto | T13 | R-MFA-H2: `sid` en el access token y comprobación por petición |
| F2 | Cambiar o restablecer la contraseña no revoca las sesiones | T13 | R-MFA-H4 |
| F3 | `mfa_enabled` es una segunda fuente de verdad sin dueño | T08 | D-04: queda derivada y la mantiene solo el servicio de MFA |
| F4 | `login_rate_limit_per_minute` es configuración muerta | — | **fuera de alcance** (es DT-16 / Spec 055); se registra y no se toca |
| F5 | La auditoría acepta diccionarios libres | T20 | R-MFA-J2: lista blanca de claves para los eventos MFA más prueba de no exposición |
| F6 | 78 inicios de sesión E2E y 52 de backend dan por hecho «contraseña ⇒ sesión» para `admin` | — | OQ-MFA-3 (arnés de pruebas) |

## 2. Requisitos (§89 A–M)

**A — Alta**
- R-MFA-A1: el backend detecta si un usuario **requiere** MFA (§4) y si ya tiene un factor activo.
- R-MFA-A2: el alta genera un secreto de 160 bits con `secrets` y lo guarda **cifrado** en estado `PENDING`. El secreto no está activo hasta verificarlo.
- R-MFA-A3: la respuesta del alta devuelve, **una sola vez**, la URI `otpauth://totp/KONTROL:<usuario>?secret=…&issuer=KONTROL&algorithm=SHA1&digits=6&period=30`, la clave manual en Base32 agrupada y el QR (OQ-MFA-2). Lleva `Cache-Control: no-store`.
- R-MFA-A4: el factor se activa solo tras verificar un código válido. Esa verificación consume su paso (R-MFA-B4). Al activarse se generan los códigos de recuperación.
- R-MFA-A5: reiniciar el alta sustituye el `PENDING` anterior; nunca hay dos factores activos (índice único parcial).

**B — Desafío en el login**
- R-MFA-B1: si la contraseña es correcta y el usuario tiene factor activo, `/auth/login` **no emite sesión, access token ni cookie**. Devuelve `status=MFA_REQUIRED` y un `challenge_token` opaco, de un solo uso y 5 min de vida.
- R-MFA-B2: si la contraseña es correcta y el usuario requiere MFA pero no tiene factor, devuelve `status=MFA_ENROLLMENT_REQUIRED` y un `challenge_token` de propósito `ENROLL`. Ese token solo sirve para los endpoints de alta.
- R-MFA-B3: `POST /auth/mfa/verify` con el desafío y un código TOTP (o de recuperación) válido emite la sesión con el mismo contrato que hoy el login: cuerpo `access_token…` y cookie de refresh.
- R-MFA-B4: TOTP según RFC 6238 (SHA-1, 6 dígitos, paso de 30 s), ventana de ±1 paso y comparación en tiempo constante. **Antirrepetición:** se acepta solo si `paso > last_used_step`, con un UPDATE condicional atómico.
- R-MFA-B5: el desafío queda ligado a usuario, tenant y propósito. Se guarda solo su hash SHA-256 y se consume atómicamente. Ni el desafío ni el código se aceptan como access token.

**C — Códigos de recuperación**
- R-MFA-C1: 10 códigos de 80 bits (16 caracteres Base32 en formato `XXXX-XXXX-XXXX-XXXX`), generados con `secrets`.
- R-MFA-C2: se muestran **una sola vez**, en la respuesta de activación o regeneración. Se guarda solo SHA-256 del código normalizado; a 80 bits, la búsqueda fuera de línea sobre un volcado no es viable.
- R-MFA-C3: cada código se usa una sola vez: `UPDATE … SET used_at WHERE id=? AND used_at IS NULL` y `rowcount == 1`. Dos usos concurrentes del mismo código dan exactamente un éxito.
- R-MFA-C4: regenerar (con reautenticación) invalida todo el lote anterior en la misma transacción.
- R-MFA-C5: tras entrar con un código de recuperación, la respuesta indica los códigos restantes y la UI ofrece regenerar. Con 0 restantes, el aviso es persistente.

**D — Gestión del factor**
- R-MFA-D1: `GET /auth/mfa` devuelve: requerido o no, clase de política, factor activo y fecha de activación, y códigos restantes. **Nunca** el secreto.
- R-MFA-D2: **reemplazar** el factor (con reautenticación) abre un alta nueva mientras el factor viejo sigue activo. La confirmación cambia uno por otro atómicamente, regenera los códigos y revoca las demás sesiones.
- R-MFA-D3: **desactivar** solo está permitido si el usuario **no** requiere MFA, y exige reautenticación. Para quien lo requiere: 403 `MFA_REQUIRED_BY_POLICY`.
- R-MFA-D4: el **reset administrativo** `POST /users/{id}/mfa/reset` exige:
  - el permiso nuevo `users:mfa_reset`;
  - reautenticación reciente del actor;
  - el mismo tenant (un objetivo de otro tenant da 404);
  - que el objetivo no sea el propio actor;
  - el techo de privilegio: el actor no puede resetear a un usuario con permisos que él no tiene.

  El reset borra el factor y los códigos, revoca **todas** las sesiones del objetivo y lo obliga a darse de alta en su siguiente login (R-MFA-B2). No toca la contraseña.

**E — Factor perdido**
- R-MFA-E1: la vía es un código de recuperación (C) o el reset administrativo (D4). No existe ningún endpoint que entre sin factor.
- R-MFA-E2: **rotura de cristal** para el último administrador: una orden local del servidor (`python -m app.modules.identity_access.mfa_breakglass --tenant … --username …`). Requiere acceso al anfitrión y confirmación interactiva, queda auditada con `source=CLI` y hace lo mismo que D4. **No es una ruta HTTP.**

**F — Reautenticación**
- R-MFA-F1: `POST /auth/reauth` con contraseña y TOTP (o código de recuperación) marca `sessions.reauth_at`. El usuario sin factor reautentica solo con la contraseña.
- R-MFA-F2: la dependencia `require_recent_reauth(max_age=300 s)` responde 403 `REAUTH_REQUIRED` si la reautenticación de **esta** sesión es más vieja.
- R-MFA-F3: lista cerrada de operaciones que la exigen:
  - alta de usuario;
  - asignar y retirar roles;
  - crear y editar roles y sus permisos;
  - toda la gestión MFA (D2, D3, D4, C4);
  - `organization:delete` y `organization:deactivate`;
  - `license:create`, `license:edit` y `license:approve`;
  - `aprobaciones:configure`.

  Gobierno heredará la dependencia; la lista crece solo por Spec.

**G — Política por capacidades**
- R-MFA-G1: la clase de un usuario se calcula sobre el **conjunto efectivo de permisos** de sus roles vigentes, no sobre el nombre del rol (§4). El rol protegido `ADMIN` es siempre PRIVILEGED.
- R-MFA-G2: la política se evalúa en el login, en `verify`, en cada `refresh` y al asignar un rol.

**H — Sesiones**
- R-MFA-H1: una sesión registra `auth_method` (`PASSWORD`, `PASSWORD_TOTP` o `PASSWORD_RECOVERY`), `mfa_verified_at` y `reauth_at`.
- R-MFA-H2: el access token lleva `sid`. `get_current_user` rechaza con 401 `SESSION_REVOKED` si la sesión está revocada o caducada, y la revocación es efectiva en la siguiente petición.
- R-MFA-H3: si al refrescar el usuario requiere MFA y la sesión no tiene `mfa_verified_at`, se revoca con 401 `MFA_REQUIRED` y hay que volver a entrar. Esto cubre la elevación de privilegio a mitad de sesión.
- R-MFA-H4: se revocan todas las sesiones del usuario al:
  - activar, reemplazar o desactivar el factor;
  - resetearlo;
  - cambiar o restablecer la contraseña;
  - recibir o perder un rol que cambia su clase.

  En el cambio voluntario se conserva la sesión actual.

**I — Límites de intentos (en BD; válidos con varios procesos)**
- R-MFA-I1: un desafío admite 5 códigos fallidos y luego queda invalidado.
- R-MFA-I2: cada fallo de TOTP, código de recuperación o reautenticación cuenta en el **mismo** `failed_attempts` / `lockout_until` del usuario (5 fallos → 15 min).
- R-MFA-I3: un alta `PENDING` admite 5 confirmaciones fallidas y luego se invalida.
- R-MFA-I4: con el bloqueo activo, `verify`, `reauth` y el alta responden 423 `AUTH_LOCKED`, sin evaluar el código.
- R-MFA-I5: el reset administrativo exige reautenticación; ningún reset borra el bloqueo del objetivo.

**J — Auditoría**
- R-MFA-J1: eventos (§9):
  - `MFA_ENROLLMENT_STARTED`, `MFA_ENROLLED`, `MFA_ENROLLMENT_FAILED`;
  - `MFA_CHALLENGE_ISSUED`, `MFA_VERIFY_SUCCESS`, `MFA_VERIFY_FAILED`, `MFA_REPLAY_REJECTED`;
  - `MFA_RECOVERY_CODE_USED`, `MFA_RECOVERY_CODES_REGENERATED`;
  - `MFA_FACTOR_REPLACED`, `MFA_DISABLED`, `MFA_RESET_BY_ADMIN`, `MFA_RESET_BREAKGLASS`;
  - `REAUTH_SUCCESS`, `REAUTH_FAILED`;
  - `SESSIONS_REVOKED_SECURITY_CHANGE`.
- R-MFA-J2: `evidence` solo admite estas claves: `method`, `policy_class`, `recovery_codes_remaining`, `reason`, `sessions_revoked` y `target_user_id`. **Nunca** códigos, secretos, URI, QR, desafíos ni hashes. Una prueba recorre todas las filas de auditoría y todos los registros tras cada flujo.

**K / L — UI/UX y accesibilidad:** §10.

**M — Recuperación operativa:** §11 y documentación de despliegue (clave, rotación, rotura de cristal, NTP).

## 3. Modelo de amenazas (§90)

| Id | Amenaza | Control | Requisitos | Prueba |
|---|---|---|---|---|
| T01 | Robo de credenciales | Segundo factor obligatorio para PRIVILEGED; sin sesión antes del factor | B1, B2, G1 | MFA-B01..04 |
| T02 | Fuerza bruta de OTP | 5 por desafío; bloqueo compartido | I1, I2, I4 | MFA-I01..05 |
| T03 | Enumeración de OTP o de usuarios | El desafío solo se emite tras la contraseña correcta; los errores de código son genéricos (`MFA_INVALID_CODE`) y no dicen si el código caducó o no pertenece al usuario | B1, B4 | MFA-B05 |
| T04 | Repetición de TOTP | `paso > last_used_step` mediante UPDATE condicional | B4 | MFA-B06, B07 (concurrente) |
| T05/T06 | Reutilización o uso paralelo de un código de recuperación | `used_at IS NULL` condicional con `rowcount == 1` | C3 | MFA-C03, C04 (concurrente, PostgreSQL) |
| T07 | Robo de códigos de recuperación | Se muestran una vez; solo hash; regenerar invalida; auditoría; aviso de restantes | C2, C4, C5 | MFA-C05..07 |
| T08 | Degradación de MFA | Ningún interruptor de configuración desactiva MFA; política evaluada en login y refresh; PRIVILEGED no puede desactivar | D3, G2, H3 | MFA-D03, H03, MFA-NOCFG |
| T09 | Borrado del factor | Reemplazar o desactivar exige reautenticación; PRIVILEGED vuelve al alta forzada | D2, D3, F2 | MFA-D02..04 |
| T10 | Reset no autorizado | Permiso, reautenticación, mismo tenant, no a sí mismo, techo de privilegio | D4 | MFA-D05..10 |
| T11 | Escalada de privilegio | Asignar rol exige reautenticación; cambio de clase revoca sesiones; refresh reevalúa | F3, H3, H4 | MFA-H03, H05 |
| T12 | Fijación de sesión | Sesión y refresh nuevos solo tras el factor; desafío de un solo uso con 5 min de vida | B3, B5 | MFA-B08 |
| T13 | Sesión reutilizada tras un cambio de seguridad | `sid` comprobado en cada petición; revocación en H4 | H2, H4 | MFA-H01, H02, H04 |
| T14 | Bypass por API directa | Autoridad en el backend; el `challenge_token` no es JWT de acceso; todo endpoint protegido lo rechaza | B5 | MFA-B09 (barrido OpenAPI de rutas protegidas) |
| T15/T16 | Factor de otro usuario / IDOR / BOLA | Los endpoints propios no reciben `user_id`; el reset administrativo filtra por tenant y da 404 | D1, D4 | MFA-D06, D07 |
| T17 | Desfase de reloj | ±1 paso; error genérico; NTP obligatorio en la documentación de despliegue | B4, M | MFA-B10 (bordes −2, −1, 0, +1, +2) |
| T18 | Carreras | UPDATE condicional; `FOR UPDATE` en desafío y alta; índice único parcial del factor activo | A5, B4, C3 | MFA-B07, C04, A05 |
| T19 | Volcado o backup de BD | Secreto en AES-256-GCM con clave fuera de la BD y del código; códigos y desafíos solo como hash | §6 | MFA-K01..04 |
| T20 | Fuga en logs, auditoría, API, frontend o QR | Lista blanca de auditoría; `no-store`; nada en URL ni en `localStorage`; QR sin servicio externo | J2, A3 | MFA-J01..03, E2E-MFA-07 |
| T21 | Abuso de la recuperación | Los códigos cuentan en el bloqueo; auditados; aviso de restantes | C5, I2 | MFA-C08 |
| T22 | Reset de contraseña como bypass | Restablecer la contraseña **no** toca el factor y revoca las sesiones | H4 | MFA-H06 |
| T23 | Secuestro del alta | El alta forzada exige contraseña; el `PENDING` se activa solo con un código; reemplazar exige reautenticación | A4, B2, D2 | MFA-A06 |
| T24 | Robo de la clave de cifrado | Clave solo en el entorno; anillo con rotación y recifrado; 0 claves en Git (prueba de residuos) | §6 | MFA-K05, RESIDUE |

## 4. Política de roles por capacidades (R-MFA-G1) — **OQ-MFA-1**

| Clase | Regla (permisos efectivos del usuario) | MFA |
|---|---|---|
| PRIVILEGED | rol protegido `ADMIN`, o cualquiera de: `users:create`, `users:mfa_reset`, `roles:create`, `roles:edit`, `license:create`, `license:edit`, `license:approve`, `organization:create`, `organization:delete`, `organization:deactivate`, `organization:activate`, `organization:manage_structure`, `aprobaciones:configure`, `aprobaciones:delegate` | **obligatorio** |
| SENSITIVE | cualquiera de: `audit:view`, `fiscal:approve`, `tesoreria:approve`, `aprobaciones:approve`, `reportes:export` | según OQ-MFA-1 |
| STANDARD | el resto | voluntario |

La regla es una constante versionada en el módulo `identity_access`, con pruebas por permiso. No es configuración: un interruptor así sería un vector de degradación (T08). La lista solo crece por Spec.

## 5. Modelo de datos (migración `0058_spec002_mfa`)

| Tabla / columna | Contenido |
|---|---|
| `auth_mfa_factors` | `id`, `tenant_id`, `user_id` FK, `type` (`TOTP`), `status` (`PENDING`/`ACTIVE`), `secret_ciphertext` (bytes), `key_id`, `digits` = 6, `period` = 30, `algorithm` = `SHA1`, `last_used_step` bigint nulo, `failed_confirmations`, `created_at`, `activated_at`, `created_by`. Índices únicos parciales: un `ACTIVE` y un `PENDING` por usuario |
| `auth_mfa_recovery_codes` | `id`, `user_id` FK, `factor_id` FK, `batch_id`, `code_hash` (char 64, único), `used_at` nulo, `created_at` |
| `auth_mfa_challenges` | `id`, `tenant_id`, `user_id` FK, `purpose` (`LOGIN`/`ENROLL`), `token_hash` (único), `expires_at`, `attempts`, `consumed_at`, `ip`, `user_agent`, `created_at` |
| `sessions` + | `auth_method`, `mfa_verified_at` nulo, `reauth_at` nulo |
| `users.mfa_enabled` | queda **derivada**: la escribe solo el servicio MFA, en la misma transacción que el factor. La fuente de verdad es `auth_mfa_factors` |
| Permiso | `users:mfa_reset`, añadido a la siembra aditiva del rol `ADMIN` en `setup` |

Paridad modelo↔migración (P26); instalación limpia y actualización sobre una base con datos (P24); PostgreSQL y SQLite (P21). SQLite no mantiene `FOR UPDATE`: la exclusión se apoya en el UPDATE condicional, como en `rotate_session`. Ninguna migración de datos: los usuarios existentes quedan sin factor y los PRIVILEGED pasan por el alta forzada en su siguiente login.

## 6. Cifrado y gestión de la clave (R-MFA-A2, T19, T24)

- `KONTROL_MFA_KEYS="<kid>:<base64url de 32 bytes>[,<kid>:<…>]"`. La primera clave cifra; todas descifran según el `key_id` guardado.
- AES-256-GCM (`cryptography`): nonce aleatorio de 96 bits por cifrado; AAD = `tenant_id|user_id|factor_id`, de modo que un texto cifrado copiado a otra fila no descifra.
- **Validación al arrancar (en todo entorno, como `secret_key`):**
  - falta la variable, está mal formada, tiene longitud distinta de 32 o hay `kid` duplicados → `Settings` falla y el servicio no arranca;
  - el error nombra el problema y nunca el valor.

  No hay clave por defecto ni derivada de `secret_key`.
- Un `key_id` desconocido al descifrar → 500 `MFA_KEY_UNAVAILABLE`, sin vuelta atrás a contraseña sola (T08) y auditado.
- **Rotación:** se añade una clave al principio del anillo y se ejecuta `python -m app.modules.identity_access.mfa_rekey`, que recifra cada factor con la activa en transacciones por lote e informa del recuento. La clave vieja se retira cuando el recuento con ese `kid` es 0.
- Pruebas y QA: clave **aleatoria por sesión de pytest y por corrida E2E**, generada en tiempo de ejecución, nunca escrita en el repositorio ni en la evidencia.

## 7. Contrato de API

| Ruta | Autenticación | Resultado |
|---|---|---|
| `POST /auth/login` | — | 200 con una de estas formas: (a) `{status:"AUTHENTICATED", access_token, token_type, expires_in, must_change_password, user}` + cookie; (b) `{status:"MFA_REQUIRED", challenge_token, expires_in, methods:["TOTP","RECOVERY_CODE"]}`; (c) `{status:"MFA_ENROLLMENT_REQUIRED", challenge_token, expires_in}`. Las formas (b) y (c) no fijan cookie |
| `POST /auth/mfa/verify` | desafío `LOGIN` | `{code}` o `{recovery_code}` → forma (a) + `recovery_codes_remaining` |
| `POST /auth/mfa/enrollment` | desafío `ENROLL` **o** Bearer (voluntario; con reautenticación si sustituye) | `{otpauth_uri, manual_key, qr_svg?, expires_in}`, `no-store` |
| `POST /auth/mfa/enrollment/confirm` | ídem | `{code}` → `{recovery_codes:[…10]}` y, por la vía del desafío, también la forma (a) |
| `GET /auth/mfa` | Bearer | estado (D1) |
| `POST /auth/mfa/recovery-codes` | Bearer + reautenticación | lote nuevo (C4) |
| `DELETE /auth/mfa` | Bearer + reautenticación | 204; 403 `MFA_REQUIRED_BY_POLICY` |
| `POST /auth/reauth` | Bearer | `{password, code?\|recovery_code?}` → `{reauth_valid_until}` |
| `POST /users/{user_id}/mfa/reset` | Bearer + `users:mfa_reset` + reautenticación | 204; 404 si es de otro tenant; 403 si es el propio actor o supera su techo |

Errores con el formato KONTROL actual: `MFA_INVALID_CODE` 401, `MFA_CHALLENGE_INVALID` 401, `AUTH_LOCKED` 423, `REAUTH_REQUIRED` 403, `MFA_REQUIRED` 401, `MFA_REQUIRED_BY_POLICY` 403, `MFA_KEY_UNAVAILABLE` 500. Los parámetros no declarados siguen el contrato vigente: el 422 es el gap n.º 5 y no se adelanta aquí. La deriva de OpenAPI es **esperada**, y la firma de referencia se regenera y se revisa ruta por ruta.

## 8. Contrato de auditoría

Ver J1/J2. `entity_type="User"`, `entity_id` = el usuario afectado, `user_id` = el actor y `session_id` cuando exista. Los eventos de rechazo se escriben aunque la petición falle; para eso usan el mismo patrón que hoy `LOGIN_FAILED` (commit propio antes de lanzar el error). El catálogo formal de 006/051 es el gap n.º 4: estos códigos entran en él cuando se aborde, sin renombrarlos.

## 9. Modelo UX/UI (K, L)

### 9.1 Pantallas (P18: rutas propias a pantalla completa; el único diálogo es la reautenticación, que es una confirmación breve con el componente compartido)

| Pantalla | Ruta | Contenido |
|---|---|---|
| Acceso, paso 2 | `/login` (segundo paso del mismo formulario) | campo de código (`inputmode="numeric"`, `autocomplete="one-time-code"`, 6 dígitos); enlace «Usar un código de recuperación» (cambia el campo y su validación); intentos restantes; «Volver» invalida el desafío en el cliente |
| Alta forzada o voluntaria | `/seguridad/mfa/alta` | 1) por qué; 2) QR y clave manual con «Copiar»; 3) verificar el código; 4) códigos de recuperación (copiar o descargar `.txt` generado en el cliente) y la casilla «Los he guardado», obligatoria para continuar |
| Mi seguridad | `/seguridad` | estado del factor, códigos restantes, regenerar, reemplazar, desactivar (solo STANDARD) y sesiones (lo existente) |
| Usuario (administración) | ficha del usuario | estado MFA del usuario y «Restablecer MFA» (permiso, reautenticación y confirmación) |
| Reautenticación | diálogo compartido `ReauthDialog` | contraseña más código (o código de recuperación); se abre ante `REAUTH_REQUIRED` y repite la operación original una sola vez |

### 9.2 Los 15 estados (§23) por pantalla

| Estado | Acceso, paso 2 | Alta | Mi seguridad | Reset administrativo |
|---|---|---|---|---|
| inicial | campo vacío y con foco | paso 1 | cargando estado | botón visible si hay permiso |
| cargando | — | generando secreto | esqueleto | — |
| vacío | — | — | «Sin factor» y CTA de alta | — |
| enviando | botón deshabilitado con indicador | ídem | ídem | ídem |
| éxito | redirección a destino o a cambio de contraseña | paso 4 | aviso «Códigos regenerados» | aviso y estado actualizado |
| error de validación | «Introduce 6 dígitos» / formato del código de recuperación | ídem | — | — |
| código inválido | «Código incorrecto. Te quedan N intentos» | ídem | — | — |
| bloqueado | «Cuenta bloqueada temporalmente», sin campo | ídem | ídem | — |
| desafío caducado | «La verificación caducó»; vuelve al paso 1 | ídem | — | — |
| prohibido | — | — | «Tu política exige MFA» (desactivar) | 403 «Sin permiso» |
| no encontrado | — | — | — | 404 |
| error del servidor | mensaje genérico con referencia de petición | ídem | ídem | ídem |
| sin conexión | «Sin conexión»; reintento manual | ídem | ídem | ídem |
| conflicto | — | «El alta se reinició en otra pestaña» | — | «El usuario ya no tiene factor» |
| deshabilitado | — | «Continuar» hasta marcar la casilla | desactivar oculto para PRIVILEGED | botón oculto sin permiso o si el objetivo es el propio actor |

### 9.3 Contrato de campos (§25)

| Campo | Tipo | Validación cliente | Validación servidor | Nunca |
|---|---|---|---|---|
| código TOTP | 6 dígitos | `^\d{6}$`, se ignoran los espacios | RFC 6238 ±1 paso, antirrepetición | se registra, se guarda en estado persistente o va en una URL |
| código de recuperación | 16 caracteres Base32 con guiones opcionales | `^[A-Z2-7]{4}(-?[A-Z2-7]{4}){3}$` sin distinguir mayúsculas | hash normalizado y un solo uso | ídem |
| contraseña (reautenticación) | texto | obligatoria | Argon2id | ídem |

### 9.4 Accesibilidad (WCAG 2.1 AA)

- Etiquetas visibles; los errores van con `aria-describedby` y una región `aria-live="polite"`.
- El foco pasa al campo nuevo en cada paso; los pasos del alta se anuncian como una lista con el paso actual.
- El QR lleva texto alternativo que remite a la clave manual, y la clave manual se lee carácter a carácter.
- Contraste AA y diseño adaptable a 320 px.
- Prueba axe sobre las 4 pantallas y el diálogo.

## 10. Recuperación operativa (M)

Se documenta en `deployment-model.md` y en el runbook de seguridad:
1. alta de `KONTROL_MFA_KEYS` en instalación y actualización (sin ella el servicio no arranca);
2. respaldo de la clave **separado** del backup de la BD (un backup restaurado sin su clave deja los factores inutilizables: el resultado es fallo cerrado, y sale la ruta 3);
3. rotura de cristal (E2) y procedimiento de rotación (§6);
4. NTP obligatorio en el servidor;
5. qué hacer ante pérdida del factor (C, D4 y E2).

La verificación real de backup y restauración es el gap n.º 6.

## 11. Estrategia de pruebas

| Capa | Contenido |
|---|---|
| Unitarias | vectores de RFC 6238 (apéndice B, SHA-1) y bordes de ventana; cifrado de ida y vuelta; AAD distinto → falla; anillo con `kid` desconocido |
| Servicio y API (SQLite y PostgreSQL) | MFA-A/B/C/D/F/G/H/I/J/K: flujos, negativas, IDOR, concurrencia (repetición, código de recuperación y rotación con hilos en PostgreSQL), barrido de rutas protegidas con el desafío como token |
| Migración | instalación limpia y actualización desde `0057` con datos; paridad |
| No exposición | tras cada flujo, recorrer `audit_events`, los registros capturados y las respuestas en busca del secreto, la URI, los códigos y el desafío: 0 apariciones |
| Mutaciones | antirrepetición, ventana, un solo uso, techo de privilegio, comprobación de `sid`, revocación de H4, rechazo de configuración: 0 supervivientes |
| E2E (Chromium, y Firefox y WebKit en las pantallas MFA) | E2E-MFA-01 alta forzada con QR, clave, verificación y códigos; 02 login con TOTP; 03 login con código de recuperación y aviso; 04 código incorrecto e intentos; 05 bloqueo; 06 regenerar con reautenticación; 07 nada en `localStorage`, `sessionStorage` ni URL; 08 reset administrativo y realta del objetivo; 09 axe y diseño adaptable |
| Arnés | **OQ-MFA-3** |

## 12. Decisiones de diseño

| Id | Decisión |
|---|---|
| D-01 | TOTP con la stdlib, sin dependencias nuevas para TOTP |
| D-02 | Cifrado AES-256-GCM con `cryptography` (ya en el lock) y anillo `KONTROL_MFA_KEYS` (§6) |
| D-03 | El desafío es un token opaco con hash en BD (no un JWT), así no puede confundirse con un access token |
| D-04 | `users.mfa_enabled` queda derivada (F3) |
| D-05 | El bloqueo de MFA comparte contador con el de contraseña (I2) |
| D-06 | El access token se liga a la sesión con `sid` y se comprueba en cada petición (F1). Cuesta una lectura por clave primaria por petición, y se acepta |
| D-07 | La política es una constante versionada, no configuración (T08) |
| D-08 | La rotura de cristal es una orden local, no HTTP (E2) |
| D-09 | La reautenticación vale 5 min por sesión (F2) |
| D-10 | Los parámetros TOTP son SHA-1, 6 dígitos y 30 s, por compatibilidad con las aplicaciones de autenticación habituales |

## 13. MATERIAL OQ (decisiones de la dueña)

| Id | Pregunta | Opciones | Recomendación |
|---|---|---|---|
| **OQ-MFA-1** | Alcance obligatorio de la política | **A:** obligatorio para PRIVILEGED y SENSITIVE, voluntario para STANDARD (es lo que dice `security-baseline.md`: «propietario y perfiles críticos»; aprobar dinero o fiscal es un perfil crítico). **B:** obligatorio solo para PRIVILEGED. **C:** obligatorio para todos | **A** |
| **OQ-MFA-2** | QR del alta (es una dependencia nueva) | **A:** `segno` (Python puro, sin dependencias, BSD-3) fijado en `requirements.lock`; el backend genera un SVG que el frontend pinta como `<img src="data:image/svg+xml;base64,…">`, sin inyección de marcado; pasa por pip-audit. **B:** librería de QR en el frontend (npm). **C:** sin QR, solo la clave manual y el enlace `otpauth://` | **A** |
| **OQ-MFA-3** | Arnés de pruebas con la antirrepetición (un login TOTP por usuario y paso de 30 s; los refresh son de un solo uso). Hoy `admin` (PRIVILEGED) entra 78 veces en E2E con 6 workers y 52 en backend | **A:** sesión privilegiada **por worker**: la siembra E2E crea `admin` con un secreto aleatorio de la corrida (fuera de Git, en el directorio de la corrida); un helper común hace un login TOTP por worker, reutiliza el access token en las llamadas API (15 min > 4,9 min de suite) y encadena el refresh de las pruebas de UI dentro del worker; los backends de pytest usan un fixture común con reloj inyectable en el módulo TOTP. Los 78 + 52 sitios pasan a los helpers comunes. **B:** las pruebas que no prueban privilegios cambian a usuarios STANDARD con permisos concretos y solo un subconjunto usa `admin` con MFA (cambia el significado de muchas pruebas). **C:** cada prueba con su identidad privilegiada propia sembrada (cientos de usuarios y un asignador entre workers) | **A**. Nunca se admite un interruptor de prueba que desactive MFA ni esperas o reintentos para cambiar de paso |

No se pregunta lo que el contrato ya fija: TOTP, códigos de recuperación, reautenticación, clave fuera del código y backend como autoridad.

## 14. Constitution gate

| Principio | Estado |
|---|---|
| P1 Spec antes que código | PASS: esta delta; 0 código |
| P2 Autorización expresa | PENDIENTE: el encargo autoriza la iniciativa; las OQ-MFA-1..3 bloquean `implement` |
| P3 Trazabilidad | PASS (§16) |
| P6 Seguridad en backend | PASS: toda decisión de MFA en el backend |
| P7 / P17 Frontend uniforme | PASS: componentes compartidos; `ReauthDialog` es un componente compartido, no una variante local |
| P8 No hardcodear reglas de negocio | PASS con nota: la política es una regla de **seguridad** versionada (D-07), no de negocio |
| P10 Calidad demostrable | PASS: §11 con negativas, concurrencia y mutaciones |
| P11 Accesibilidad | PASS (§9.4) |
| P12 Decisiones documentadas | PASS: D-01..10; ADR-004 se amplía (sesión ligada por `sid`) |
| P13 Integridad transaccional | PASS: UPDATE condicional y lote atómico |
| P15 Datos del cliente protegidos | PASS: cifrado, hash y no exposición |
| P18 Modales | PASS: rutas a pantalla completa; solo la confirmación breve de reautenticación |
| P21 Paridad de motor | PASS: PostgreSQL y SQLite |
| P24 Instalación limpia | PASS: está en §11 |
| P25 La concurrencia la gobierna la base | PASS: índices únicos parciales y UPDATE condicional |
| P26 Paridad de modelos y migraciones | PASS: está en §11 |
| P27 Mutación observable | PASS: está en §11 |

BLOCKER = 0 · CRITICAL = 0 · CONTRADICTIONS = 0 · OWNER CONFLICT = 0 · **MATERIAL OQ = 3** → `DEEPSEEK CALLS = 0`.

## 15. Plan y tareas

Una vez cerradas las OQ, todas las tareas tienen `SECURITY_SENSITIVE` = sí, `EGRESS_SAFE` = sí (valores sintéticos, sin claves ni rutas del home) y `RETRY_MAX` = 2. Por la regla de la dueña del 2026-10-18, DeepSeek escribe todo el código y las pruebas aunque la tarea sea `CLAUDE_ONLY` por naturaleza; Claude diseña, audita y certifica.

| Tarea | Contenido | MODEL | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|
| TM-A | Pruebas en rojo: unitarias (TOTP, cifrado) y de servicio/API A..K | v4-pro | `tests/test_mfa_*.py` | rojo atribuido | rojo por causa correcta |
| TM-1 | Modelos y migración `0058` | v4-pro | `identity_access/models.py`, `alembic/versions/0058_…` | paridad, instalación limpia y actualización | verde en PostgreSQL y SQLite |
| TM-2 | `mfa_crypto` (anillo, AES-GCM) + validador de `Settings` + `totp` | v4-pro | `identity_access/mfa_crypto.py`, `totp.py`, `core/config.py` | unitarias | verde |
| TM-3 | Servicio MFA: alta, desafío, verificación, códigos, gestión, política, reset, bloqueo, auditoría | v4-pro | `identity_access/mfa_service.py`, `service.py` | MFA-A..J | verde |
| TM-4 | Sesión ligada (`sid`), `require_recent_reauth`, revocación H4 | v4-pro | `core/security.py`, `core/dependencies.py`, `service.py` | MFA-H, F | verde |
| TM-5 | API y guardas de reautenticación en la lista F3 | v4-pro | `identity_access/api.py` y los routers de F3 | API y barrido | verde; OpenAPI revisada |
| TM-6 | Órdenes `mfa_breakglass` y `mfa_rekey` | v4-pro | `identity_access/mfa_breakglass.py`, `mfa_rekey.py` | pruebas CLI | verde |
| TM-7 | Arnés backend (OQ-MFA-3) | v4-flash | `tests/conftest.py` y los ~43 `_login` | suite completa | SQLite y PostgreSQL verdes |
| TM-8 | Frontend: login paso 2, alta, mi seguridad, reset administrativo, `ReauthDialog`, cliente | v4-pro | `src/pages/*`, `src/components/ReauthDialog.tsx`, `src/api/*`, `AuthContext.tsx` | vitest + typecheck + lint | verde |
| TM-9 | Arnés E2E (OQ-MFA-3) + siembra con secreto de corrida | v4-flash | `e2e/helpers/*`, los 40 specs, `qa/pg-e2e-seed.py`, `qa/e2e_corrida.py` | E2E completa | 0 fallos |
| TM-10 | E2E-MFA-01..09 | v4-pro | `e2e/mfa-*.spec.ts` | E2E | verde en los 3 motores |
| TM-11 | Documentación de despliegue, runbook, ADR-004 ampliado, trazabilidad, deudas | CLAUDE (diseño) | `specs/001-fundacion/*`, `docs/*` | revisión | hecho |

Orden: TM-A → TM-1 → TM-2 → TM-3 → TM-4 → TM-5 → TM-6 → TM-7 → TM-8 → TM-9 → TM-10 → TM-11. No se apila trabajo sobre una tarea en rojo. La aplicación de la obligatoriedad (TM-3/TM-4) y los arneses (TM-7/TM-9) se convergen en el mismo ciclo: el commit solo entra con las suites completas en verde.

## 16. Trazabilidad

| Requisito | Amenazas | Tareas | Pruebas |
|---|---|---|---|
| A1–A5 | T18, T23 | TM-1..3, TM-8 | MFA-A01..06, E2E-MFA-01 |
| B1–B5 | T01, T03, T04, T12, T14, T17 | TM-3..5, TM-8 | MFA-B01..10, E2E-MFA-02, 04 |
| C1–C5 | T05–T07, T21 | TM-3, TM-8 | MFA-C01..08, E2E-MFA-03, 06 |
| D1–D4 | T09, T10, T15, T16 | TM-3, TM-5, TM-8 | MFA-D01..10, E2E-MFA-08 |
| E1–E2 | T10 | TM-6, TM-11 | MFA-E01..03 |
| F1–F3 | T09, T11 | TM-4, TM-5, TM-8 | MFA-F01..06, E2E-MFA-06 |
| G1–G2 | T08, T11 | TM-3 | MFA-G01..(1 por permiso de §4) |
| H1–H4 | T11, T13, T22 | TM-4 | MFA-H01..06 |
| I1–I5 | T02, T21 | TM-3 | MFA-I01..05, E2E-MFA-05 |
| J1–J2 | T20 | TM-3 | MFA-J01..03 |
| K, L | T20 | TM-8, TM-10 | vitest, E2E-MFA-07, 09 |
| M | T17, T19, T24 | TM-2, TM-6, TM-11 | MFA-K01..05, revisión |

Requisitos 13/13 trazados · amenazas 24/24 con control y prueba · tareas sin requisito = 0 · **TRACEABILITY_COMPLETE = 1** (de diseño).

## 17. Autorización

`implement` queda **BLOCKED_BY_OWNER_DECISION** hasta que la dueña resuelva OQ-MFA-1, OQ-MFA-2 y OQ-MFA-3. Con las tres resueltas, el gate pasa a `MATERIAL OQ = 0` y el encargo SHARED-CORE-P0-HARDENING-01 autoriza `implement` (P2). MFA_BYPASS = BLOCKED por diseño.
