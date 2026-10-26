# SPEC 002/003 · Delta — SHARED-CORE-P0-HARDENING-01 · MFA FOR PRIVILEGED ROLES

| Campo | Valor |
|---|---|
| Specs dueñas | **002** (Seguridad / Sesiones) · **003** (Usuarios / Roles / Alcance). Ninguna tiene carpeta propia (OBS-04 SPEC-SEGURIDAD-SIN-CARPETA, D, sigue abierta): la delta se aloja en `specs/001-fundacion/`, donde vive FR-001-024 («MFA preparado, habilitable»). Alojarla aquí **no** resuelve OBS-04 |
| Clase | SHARED_CORE HARDENING (gap P0 n.º 1 de OD-GSR-2). No es GOV-0 ni GOV-SPEC |
| Decisiones | OQ-GAB-2 = A (TOTP + códigos de recuperación + reautenticación; WebAuthn futuro) · OD-GSR-2 = A · contrato de seguridad de la dueña (Master Prompt §88–91) |
| HEAD de entrada | `37bc083` |
| Evidencia | `evidence/mfa-privileged-roles/` (orquestación, mutaciones, dependencias, rojos medidos) |
| GOVERNMENT_IMPLEMENTATION_AUTHORIZED | 0 |
| Estado | **IMPLEMENTED — CONVERGED (2026-10-26)**: DoD verificada en §23 (backend SQLite y PostgreSQL, E2E completa y multinavegador, mutaciones, fugas y residuos); deudas en §21; Gobierno en §22. Antes: **DESIGN COMPLETE — OQ RESUELTAS (2026-10-25)**: OQ-MFA-1 = A, OQ-MFA-2 = A, OQ-MFA-3 = A (§18). IMPLEMENTATION AUTHORIZED por el encargo «SHARED-CORE-P0-HARDENING-01 … IMPLEMENTATION AUTHORIZED» |

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

### 4.1 Clasificación ratificada y medida (OQ-MFA-1 = A; sustituye a la tabla anterior)

PRIVILEGED y SENSITIVE exigen MFA; STANDARD lo tiene voluntario.

**Cómo se calcula la clase.**
- Se calcula sobre el **conjunto efectivo de permisos** de los roles vigentes del usuario, sea cual sea su alcance (un rol de una sola empresa no rebaja la clase).
- **Nunca** depende del nombre visible del rol. La excepción es el rol protegido `ADMIN`, que siempre es PRIVILEGED.
- Si varias clases aplican, gana la más alta.

**Universo clasificado.** Cada `resource:action` que exige alguna ruta (`require_permission`), que siembra `setup` o que añade alguna migración. Medido en `2636bfa` sobre las rutas: el efecto de cada permiso se revisó sobre el código (barrido de solo lectura con evidencia `fichero:línea`, verificado por muestreo).

| Clase | Permisos | Criterio y evidencia |
|---|---|---|
| **PRIVILEGED** (18) | `users:create`, `users:edit`, `users:deactivate`, `users:activate`, `users:mfa_reset` (nuevo), `roles:create`, `roles:edit`, `license:create`, `license:edit`, `license:approve`, `organization:create`, `organization:activate`, `organization:deactivate`, `organization:delete`, `organization:manage_structure`, `aprobaciones:configure`, `aprobaciones:delegate`, `aprobaciones:edit` | administración de seguridad, usuarios y roles; reset de MFA; autoridad de licencia y estructura; política de aprobación. La lista de 15 del diseño crece con 4 permisos **sembrados** (`users:edit`, `users:deactivate`, `users:activate`, `aprobaciones:edit`) que el primer barrido, hecho solo sobre las rutas, no veía |
| **SENSITIVE** (34) | `fiscal:create`, `fiscal:approve`, `tesoreria:create`, `tesoreria:approve`, `compras:approve`, `compras:apply`, `compras:create`, `compras:quality`, `ventas:approve`, `ventas:apply`, `ventas:create`, `ventas:quality`, `ventas:submit`, `inventario:approve`, `inventario:transition`, `inventario:create`, `inventario:confirm`, `inventario:reserve`, `aprobaciones:approve`, `aprobaciones:create`, `regulatorio:approve`, `regulatorio:create`, `homologacion:approve`, `audit:view`, `reportes:export`, `documentos:delete`, `documentos:manage_types`, `maestros:delete`, `maestros:create`, `comercial:manage_policies`, `comercial:publish`, `notificaciones:configure`, `tareas:configure`, `organization:edit` | ver la tabla 4.2 |
| **STANDARD** (34) | `dashboard:view`, `organization:view`, `users:view`, `roles:view`, `license:view`, `homologacion:view`, `homologacion:create`, `homologacion:edit`, `maestros:view`, `maestros:edit`, `maestros:deactivate`, `compras:view`, `ventas:view`, `inventario:view`, `tesoreria:view`, `fiscal:view`, `regulatorio:view`, `reportes:view`, `aprobaciones:view`, `documentos:view`, `documentos:create`, `documentos:edit`, `documentos:upload`, `documentos:download`, `documentos:link`, `documentos:deactivate`, `comercial:view`, `comercial:create`, `comercial:edit`, `comercial:archive`, `tareas:view`, `tareas:assign`, `tareas:complete`, `alertas:view` | analizados y sin efecto definitivo propio (ver 4.2) |

### 4.2 Evidencia de las reclasificaciones respecto al diseño

| Permiso | Efecto definitivo (1/0) | Evidencia (`app/modules/…`) |
|---|---|---|
| `inventario:transition` | **1** | `inventory/service.py` `approve_count` (registra movimientos de CONTEO), `confirm_transfer_ship` y `confirm_transfer_receipt` (`record_movement`). **INVENTORY_TRANSITION_DEFINITIVE_EFFECT = 1 → INVENTORY_TRANSITION_MFA_CLASS = SENSITIVE** (regla de §7, sin pregunta nueva) |
| `inventario:create` | 1 | `POST /movements` y `/movements/reverse` → `record_movement` (`inventory/api.py:357,372`); `/operations/ship` |
| `inventario:confirm` | 1 | `POST /receipts/{id}/confirmacion-inventario` → `reclassify` (`inventory/service.py:855-868`, `qty_on_hand`) |
| `inventario:reserve` | 1 | `POST /reservations` → `qty_reserved +=` (`inventory/service.py:1239,1247`) |
| `compras:create` | 1 | `POST /advances` → `Advance(status="ACTIVE", available=amount)` (`purchasing/service.py:1609`), aplicable sin aprobación |
| `compras:quality` | 1 | `POST /receipts/{id}/accept` → `record_movement` (`purchasing/service.py:674`); cancelar una incidencia evita la resolución `compras:approve` |
| `ventas:create` | 1 | picking `recoger` → `reclassify` y `consume_on_pick` (`sales/service.py:1532,1541`); devolución `recibir`; `/customer-advances` ACTIVE |
| `ventas:quality` | 1 | `POST /shipments/{id}/confirm` → DESPACHADO (`sales/service.py:2458`); `reingresar` |
| `ventas:submit` | 1 | `POST /orders/{id}/submit` → `inv_service.reserve` (`sales/service.py:707`) |
| `comercial:publish` | 1 | la versión de la lista de precios pasa a ACTIVE, publicación irreversible (`commercial/service.py:269-271`) |
| `maestros:create` | 1 (límite) | `POST /presentaciones/{id}/versiones` cierra la versión vigente y activa la nueva sin edición posterior (`master_data/uom_api.py:604-616`) |
| `regulatorio:create` | 1 | `POST /official-documents` crea el documento como `VALID` y levanta bloqueos de despacho (`regulatory/service.py:216-218,266-268`) |
| `aprobaciones:create` | 1 | `POST /requests/{id}/cancel` cancela cualquier solicitud abierta y deja sin efecto la puerta `ensure_approved` (`approvals/service.py:780-797`) |
| `documentos:manage_types`, `organization:edit` | — (configuración) | cambio de configuración (criterio de la dueña) |
| `comercial:create` / `comercial:edit` | 0 | borradores (DRAFT) y asignación de condiciones (`commercial/service.py:257,317-342`) |
| `documentos:create/edit/upload/download/link` | 0 | metadatos, versiones con historial, archivo lógico; un vínculo congelado está protegido |
| `maestros:edit/deactivate`, `homologacion:create/edit` | 0 | ediciones de maestro, baja lógica, DRAFT/CANDIDATE (la liberación exige `homologacion:approve`) |
| `*:view`, `alertas:view` | 0 | lecturas; los únicos POST son previsualizaciones que no crean nada |
| `documentos:deactivate`, `comercial:archive`, `tareas:view/assign/complete`, `users:view`, `roles:view` | 0 | ninguna ruta los consume con efecto definitivo (los cuatro primeros solo están sembrados). Si una ruta futura los consume, la Spec de esa ruta reabre su clase |

**MFA-G00:** todo permiso del universo debe estar en exactamente una lista. El que no esté, en ejecución cuenta como SENSITIVE (nunca STANDARD en silencio) y la suite falla.

**Gobierno:** cuando se autorice su implementación, sus roles privilegiados heredan este contrato (GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0).

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

BLOCKER = 0 · CRITICAL = 0 · CONTRADICTIONS = 0 · OWNER CONFLICT = 0 · ~~MATERIAL OQ = 3~~ → **MATERIAL OQ = 0** (2026-10-25, §18). P2 pasa a PASS.

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

~~`implement` queda BLOCKED_BY_OWNER_DECISION~~. Las OQ se resolvieron el 2026-10-25 (§18): el gate queda en `MATERIAL OQ = 0` y el encargo SHARED-CORE-P0-HARDENING-01 «IMPLEMENTATION AUTHORIZED» autoriza `implement` (P2). MFA_BYPASS = BLOCKED por diseño.

## 18. Decisiones de la dueña (2026-10-25)

| Id | Decisión | Efecto en el diseño |
|---|---|---|
| OQ-MFA-1 = A | MFA obligatorio para PRIVILEGED y SENSITIVE; voluntario para STANDARD; clasificación por capacidades | §4.1 + MFA-G00 |
| OQ-MFA-2 = A | QR con **`segno`** en el backend: versión fijada, lock reproducible, licencia registrada, auditoría de dependencias, sin instalación flotante ni respaldo oculto | `segno==1.6.6` (BSD-3-Clause, sin dependencias) entra en `requirements.txt` y `requirements.lock` con el mismo `uv pip compile` de cabecera. El QR codifica **solo** la URI `otpauth://` generada internamente. **Contrato de pintado:** el backend devuelve el SVG como `data:image/svg+xml;base64,…` y el frontend lo pinta **solo** con `<img src>`, que no ejecuta scripts; la URI de datos se valida con un prefijo exacto y prohíbe `dangerouslySetInnerHTML` y cualquier inyección de marcado (prueba de vitest más una prueba estructural). La clave manual sigue disponible. El QR nunca es fuente de verdad |
| OQ-MFA-3 = A | Una identidad o sesión privilegiada **por worker** para las suites amplias ajenas a MFA: aislada por worker, secreto TOTP sintético generado en ejecución, nada compartido, commiteado ni en la evidencia | §11. Reloj inyectable **solo** como parámetro de las funciones TOTP del servicio (p. ej. `now: Callable[[], datetime]` con un valor por defecto real), sin variable de entorno. Prueba estructural MFA-NOBYPASS: el código de `app/` no contiene `DISABLE_MFA`, `SKIP_MFA`, `TEST_MFA_MODE`, `ACCEPT_ANY_OTP`, `FIXED_OTP` ni ningún ajuste de `Settings` que desactive o relaje MFA. Sin `sleep`, reintentos ni omisiones |
| §4 del encargo | El arnés no sustituye a la E2E de MFA | E2E-MFA cubre el ciclo real: login con contraseña, `MFA_REQUIRED`, alta, desafío, OTP válido e inválido, antirrepetición, código de recuperación y su reutilización rechazada, regeneración, reautenticación, operación privilegiada irreversible, reset administrativo y seguridad de la sesión tras el reset o el cambio. No se certifica MFA con fixtures ya autenticados |
| F1 | IN_SCOPE | R-MFA-H2: una sesión revocada deja de autorizar en la petición siguiente, aunque el JWT no haya caducado |
| F2 | IN_SCOPE, con semántica exacta | cambio propio de contraseña: se revocan las **demás** sesiones y se conserva la actual (la persona acaba de demostrar la credencial nueva). Restablecimiento por token (credencial olvidada o comprometida): se revocan **todas**. Reset de MFA (administrativo o rotura de cristal): todas las del objetivo. Reemplazo propio del factor: las demás. Desactivación propia (STANDARD): las demás |
| F3 | `users.mfa_enabled` = vista derivada de compatibilidad | la escribe solo el servicio MFA en la misma transacción que el factor. Invariante probado: `mfa_enabled ⇔ existe factor ACTIVE`, en todos los flujos, incluidos el reset, la rotura de cristal y la desactivación |
| F4 | GENERIC_LOGIN_RATE_LIMIT_DEBT = PRESERVED (DT-16 / Spec 055) · MFA_ABUSE_PROTECTION = IN_SCOPE | R-MFA-I1..I5 en verificación TOTP, códigos de recuperación, reautenticación, confirmación del alta y reset |
| F5 | Auditoría con carga segura | R-MFA-J2 (texto del encargo recibido truncado en este punto; ver el informe) |

## 19. Contrato de implementación (2026-10-26; precisa §5–§9 sin cambiarles el sentido)

### 19.1 Reconciliaciones con el código medido en `2636bfa`

| Id | Hecho medido | Decisión |
|---|---|---|
| RC-1 | `rotate_session` revoca la fila y crea otra; `test_auth_rotacion_atomica.py` y `test_auth_session_rotation.py` fijan esa semántica | Se **conserva**. Para que F1 no invalide cada access token en cada rotación, la sesión gana **`family_id`**: el id de la primera fila del login, copiado en cada rotación junto con `auth_method`, `mfa_verified_at` y `reauth_at`. El access token lleva `sid = family_id`. Autoriza solo si existe una fila de la familia con `revoked_at IS NULL` y `expires_at > ahora` |
| RC-2 | Revocar una sesión (logout, `DELETE /auth/sessions/{id}`, revocaciones de seguridad) | Revoca **toda la familia** de esa fila |
| RC-3 | `authenticate` pone `failed_attempts = 0` cuando la contraseña es correcta | Para un usuario con factor activo o que lo requiere, eso borraría los fallos de OTP (cinco fallos, login de nuevo, otros cinco). Por eso el contador **solo** se pone a cero tras el login **completo**. `LOGIN_SUCCESS` pasa a significar «login completo»; con el factor pendiente se audita `MFA_CHALLENGE_ISSUED` |
| RC-4 | `POST /auth/password-reset/request` devuelve el `reset_token` al cliente anónimo («flujo demo», `api.py`) y responde 401 si el usuario no existe | **Fuera del alcance** (NO SILENT SCOPE EXPANSION): deuda nueva **AUTH-PASSWORD-RESET-TOKEN-DISCLOSED** (§21). El MFA limita el daño: restablecer la contraseña no toca el factor (T22), así que PRIVILEGED y SENSITIVE siguen necesitando el factor después |
| RC-5 | `KONTROL_*` heredadas = FORBIDDEN en la orden canónica; la E2E y la certificación generan su propio `KONTROL_SECRET_KEY` | `KONTROL_MFA_KEYS` **obligatoria en `prod`** (sin ella no arranca). En otros entornos es opcional, pero si está se valida y, si falta, cualquier operación MFA falla cerrado con 503 `MFA_UNAVAILABLE`: no hay vuelta a contraseña sola ni clave por defecto. pytest y la corrida E2E generan una clave aleatoria en ejecución |
| RC-6 | `inventario:transition` llama a `approve_count`, `confirm_transfer_ship` y `confirm_transfer_receipt`, que registran movimientos (`record_movement`) | INVENTORY_TRANSITION_DEFINITIVE_EFFECT = **1** → **SENSITIVE** (regla de §7 del encargo) |
| RC-7 | El nombre de los eventos | Prevalecen los nombres mínimos de la dueña (§40 del encargo) sobre los de R-MFA-J1 |

### 19.2 Módulos y firmas (backend)

- `app/core/clock.py` — `def now() -> datetime` (UTC, aware). Es el **único** reloj de las decisiones MFA y de seguridad de la sesión: paso TOTP, caducidad del desafío, frescura de la reautenticación y `mfa_verified_at`. Las pruebas lo sustituyen con `monkeypatch`. No existe ninguna variable de entorno ni ajuste que lo cambie.
- `app/modules/identity_access/totp.py` (funciones puras, stdlib):
  - constantes `PERIOD = 30`, `DIGITS = 6`, `ALGORITHM = "SHA1"`, `SKEW_STEPS = 1`;
  - `generate_secret() -> bytes`: 20 bytes de `secrets`;
  - `encode_secret(raw) -> str`: Base32 sin `=`;
  - `format_manual_key(b32) -> str`: grupos de 4 separados por espacio;
  - `time_step(at) -> int`: `floor(unix / 30)`;
  - `code_at(raw, step) -> str`: HOTP de RFC 4226 con truncamiento dinámico y 6 dígitos con ceros a la izquierda;
  - `match_step(raw, code, at) -> int | None`:
    - `code` debe ser `^[0-9]{6}$` tras quitar los espacios; si no, `None`;
    - compara los 3 pasos `s-1, s, s+1`, **siempre los tres**, con `hmac.compare_digest`;
    - devuelve el paso que coincide;
  - `provisioning_uri(raw, *, account, issuer="KONTROL") -> str`: `otpauth://totp/{issuer}:{account}?secret=…&issuer=…&algorithm=SHA1&digits=6&period=30`, con `urllib.parse.quote`.
- `app/modules/identity_access/mfa_crypto.py`:
  - **Anillo:** `parse_key_ring(value) -> list[tuple[str, bytes]]`.
    - Formato `kid:clave[,kid:clave]`: `kid` con `^[A-Za-z0-9_-]{1,32}$` y clave en Base64url que descodifica a 32 bytes exactos.
    - Rechaza `kid` duplicados y el anillo vacío.
    - `ValueError` con mensajes que **nunca** incluyen la clave.
  - **Excepciones:** `MfaUnavailable(Exception)` y `MfaDecryptError(Exception)`.
  - **`encrypt_secret(raw, *, aad) -> tuple[str, bytes]`:** AES-256-GCM con la primera clave; nonce de 12 bytes; devuelve `(kid, nonce + texto_cifrado)`.
  - **`decrypt_secret(kid, blob, *, aad) -> bytes`:**
    - `kid` ausente del anillo → `MfaUnavailable`;
    - etiqueta inválida → `MfaDecryptError`.
  - **AAD:** `f"{tenant_id}|{user_id}|{factor_id}".encode()`.
- `app/core/config.py` — `mfa_keys: str | None = None` (`KONTROL_MFA_KEYS`), con un validador:
  - si la variable está, se pasa por `parse_key_ring` (error sin el valor);
  - si `environment == "prod"` y no está → `ValueError("KONTROL_MFA_KEYS es obligatoria en prod …")`.
- `app/modules/identity_access/mfa_policy.py`:
  - constantes `PRIVILEGED_PERMISSIONS`, `SENSITIVE_PERMISSIONS` y `STANDARD_PERMISSIONS` (frozensets **disjuntos**, §4.1) y `PRIVILEGED_ROLE_CODES = frozenset({"ADMIN"})`;
  - `classify(permissions, *, protected_role_codes) -> Literal["PRIVILEGED","SENSITIVE","STANDARD"]`:
    - un permiso que no esté en ninguna lista cuenta como SENSITIVE (fallo seguro en ejecución; MFA-G00 hace fallar la suite);
    - un rol protegido cuyo código esté en `PRIVILEGED_ROLE_CODES` → PRIVILEGED;
  - `requires_mfa(policy_class) -> bool`: PRIVILEGED o SENSITIVE;
  - `user_policy_class(db, user) -> str`: usa `get_user_permissions` y los códigos de rol protegidos del usuario.
- `app/modules/identity_access/mfa_service.py`: toda la lógica de §2 (alta, desafío, verificación, códigos, estado, regenerar, reemplazar, desactivar, reset administrativo, reautenticación, revocación por cambio de seguridad, rotura de cristal y recifrado). Su única puerta de auditoría es `_audit_mfa(db, action, *, user, actor_id=None, session_id=None, request_id=None, ip=None, **evidence)`:
  - acepta solo las claves `method`, `policy_class`, `recovery_codes_remaining`, `reason`, `sessions_revoked`, `target_user_id` y `attempts_remaining`, con valores `str | int | bool | None`;
  - cualquier otra clave o tipo → `ValueError`;
  - nunca usa `before`/`after`.
- `app/modules/identity_access/mfa_breakglass.py` y `mfa_rekey.py`: órdenes `python -m`, sin ruta HTTP.

### 19.3 Esquema (migración `0058_spec002_mfa`, `down_revision = "0057_spec047_notifications"`)

| Tabla | Columnas y restricciones |
|---|---|
| `mfa_factors` | `id` (UUID str 36 PK), `created_at`/`updated_at`, `created_by`, `tenant_id` FK `tenants` NOT NULL, `user_id` FK `users` NOT NULL indexado, `status` String(16) CHECK IN (`PENDING`,`ACTIVE`,`REVOKED`), `secret_ciphertext` LargeBinary NOT NULL (vacío en `REVOKED`), `key_id` String(32) NULL (NULL solo en `REVOKED`), `digits` int 6, `period` int 30, `algorithm` String(8) `SHA1`, `last_used_step` BigInteger NULL, `failed_confirmations` int 0 NOT NULL, `pending_expires_at`, `activated_at` y `revoked_at` DateTime(tz) NULL. Únicos parciales `uq_mfa_factor_active (user_id) WHERE status='ACTIVE'` y `uq_mfa_factor_pending (user_id) WHERE status='PENDING'` (en PostgreSQL y SQLite). `__scope__ = Scope.TENANT` |
| `mfa_recovery_codes` | `id`, `created_at`/`updated_at`, `user_id` FK `users` NOT NULL indexado, `factor_id` FK `mfa_factors` NOT NULL, `code_hash` String(64) UNIQUE NOT NULL, `used_at` NULL. `__scope_authority__ = "user_id → users"` |
| `mfa_challenges` | `id`, `created_at`/`updated_at`, `tenant_id` FK NOT NULL, `user_id` FK NOT NULL indexado, `purpose` CHECK IN (`LOGIN`,`ENROLL`), `token_hash` String(64) UNIQUE NOT NULL, `expires_at` NOT NULL, `attempts` int 0, `consumed_at` NULL, `ip` String(45), `user_agent` String(255). `__scope__ = Scope.TENANT` |
| `sessions` + | `family_id` String(36) NOT NULL indexado (en la migración se rellena `family_id = id` en las filas existentes); `auth_method` String(24) NOT NULL, `server_default 'PASSWORD'`, CHECK IN (`PASSWORD`,`PASSWORD_TOTP`,`PASSWORD_RECOVERY`); `mfa_verified_at` y `reauth_at` DateTime(tz) NULL |
| `permissions` / `role_permissions` | `users:mfa_reset` creado y concedido al rol `ADMIN` con el patrón idempotente de `0024`/`0057`; `setup` lo añade a `resources_actions["users"]` |

`users.mfa_enabled` se conserva como vista derivada (§18 F3). Se pone a `False` en las filas existentes y la escribe solo `mfa_service`.

### 19.4 Contrato HTTP (8 rutas nuevas + 4 cambiadas)

| Ruta | Entrada | Autorización | Éxito | Errores |
|---|---|---|---|---|
| `POST /auth/login` (cambia) | igual que hoy | — | 200: `AUTHENTICATED` (los campos de hoy + `status`, `sid` en el token, cookie) · `MFA_REQUIRED` `{status, challenge_token, expires_in: 300, methods:["TOTP","RECOVERY_CODE"]}` · `MFA_ENROLLMENT_REQUIRED` `{status, challenge_token, expires_in: 300}`. Los dos últimos **sin** cookie ni access token | los de hoy |
| `POST /auth/mfa/verify` | `{challenge_token, code?, recovery_code?}`, exactamente uno de los dos (`extra="forbid"`) | desafío `LOGIN` | `AUTHENTICATED` + `recovery_codes_remaining` + cookie | 401 `MFA_CHALLENGE_INVALID` · 401 `MFA_INVALID_CODE` (`details.attempts_remaining`) · 401 `MFA_CODE_ALREADY_USED` · 423 `AUTH_ACCOUNT_LOCKED` · 503 `MFA_UNAVAILABLE` · 422 |
| `POST /auth/mfa/enrollment` | `{challenge_token?}` | desafío `ENROLL` **o** Bearer + reautenticación reciente | `{otpauth_uri, manual_key, qr_svg_data_uri, expires_in: 600}` + `Cache-Control: no-store` | 401 `MFA_CHALLENGE_INVALID` · 403 `REAUTH_REQUIRED` · 503 |
| `POST /auth/mfa/enrollment/confirm` | `{challenge_token?, code}` | ídem | `{recovery_codes:[10]}`; por la vía del desafío además `AUTHENTICATED` + cookie; por la vía Bearer con factor previo: reemplazo atómico y revocación de las **otras** familias | 401 `MFA_INVALID_CODE` · 409 `MFA_NO_PENDING_ENROLLMENT` · 423 · 503 |
| `GET /auth/mfa` | — | Bearer | `{required, policy_class, enabled, activated_at, recovery_codes_remaining}` | 401 |
| `POST /auth/mfa/recovery-codes` | — | Bearer + reautenticación | `{recovery_codes:[10]}`, `no-store` | 403 `REAUTH_REQUIRED` · 409 `MFA_NOT_CONFIGURED` |
| `DELETE /auth/mfa` | — | Bearer + reautenticación | 204; revoca las **otras** familias | 403 `MFA_REQUIRED_BY_POLICY` · 409 `MFA_NOT_CONFIGURED` |
| `POST /auth/reauth` | `{password, code?, recovery_code?}` | Bearer | `{reauth_valid_until}` | 401 `REAUTH_FAILED` · 423 · 503 |
| `POST /users/{user_id}/mfa/reset` | — | `users:mfa_reset` + reautenticación | 204; revoca **todas** las familias del objetivo | 404 `USER_NOT_FOUND` (otro tenant) · 403 `MFA_RESET_SELF_FORBIDDEN` · 403 `MFA_RESET_CEILING` (el objetivo tiene algún permiso que el actor no tiene) · 409 `MFA_NOT_CONFIGURED` |
| `POST /auth/refresh` (cambia) | igual | cookie | igual; el token lleva `sid = family_id` | 401 `MFA_REQUIRED` (revoca la familia) si la política exige MFA y la familia no tiene `mfa_verified_at` |
| `POST /auth/change-password` (cambia) | igual | Bearer | igual; revoca las **otras** familias | los de hoy |
| `POST /auth/password-reset/confirm` (cambia) | igual | token | igual; revoca **todas** las familias | los de hoy |

**`get_current_user`** (y la nueva `get_current_session`):
- falta `sid` → 401 `AUTH_INVALID_TOKEN`;
- familia sin fila activa → 401 `SESSION_REVOKED`;
- `mfa_verified_at` nulo y política que exige MFA → 401 `MFA_REQUIRED`.

`require_recent_reauth()`: 403 `REAUTH_REQUIRED` si `reauth_at` es nulo o tiene más de 300 s según `clock.now()`. El login completo fija `reauth_at = mfa_verified_at = clock.now()` (en STANDARD sin factor, solo `reauth_at`).

**Registro cerrado de operaciones con reautenticación** (constante `REAUTH_PROTECTED_OPERATIONS`, con prueba de que cada ruta listada lleva la dependencia):
- `POST /users` y `POST|DELETE /users/{id}/roles…`;
- las rutas de `roles:create` y `roles:edit`;
- las de `organization:delete` y `organization:deactivate`;
- las de `license:create`, `license:edit` y `license:approve`;
- las de `aprobaciones:configure`;
- las 4 de gestión MFA.

Al asignar o retirar un rol, si cambia la clase de política del objetivo, se revocan todas sus familias (R-MFA-H4).

### 19.5 Límites (MFA_ABUSE_PROTECTION; en BD)

- Desafío: 5 intentos y queda consumido.
- Alta `PENDING`: 5 `failed_confirmations` y pasa a `REVOKED`.
- Cada fallo de OTP, de código de recuperación o de reautenticación suma en `users.failed_attempts`; con 5 se bloquea 15 min. Durante el bloqueo, 423 sin evaluar el código.
- El código de recuperación se consume con `UPDATE … WHERE used_at IS NULL` y `rowcount == 1`. La antirrepetición TOTP se hace con `UPDATE mfa_factors SET last_used_step = :s WHERE id = :id AND (last_used_step IS NULL OR last_used_step < :s)` y `rowcount == 1`.
- Los límites por origen o IP son la deuda genérica DT-16 (GENERIC_LOGIN_RATE_LIMIT_DEBT = PRESERVED). El límite por cuenta deja como mucho 5 intentos por cada 15 min, venga de donde venga el intento.

### 19.6 Arnés de pruebas (OQ-MFA-3 = A)

- **Backend:** `tests/mfa_apoyo.py` contiene:
  - `codigo_totp(clave_manual, instante)`: implementación **independiente** de RFC 4226/6238, el oráculo;
  - `RelojMfa`: fixture que sustituye `app.core.clock.now`;
  - `iniciar_sesion(client, tenant, usuario, contraseña) -> dict[str, str]` (cabeceras), que recorre las tres respuestas reales del login, da de alta el factor por API cuando hace falta y guarda la clave en memoria por prueba. Si el paso actual ya se usó con ese usuario, adelanta el reloj al paso siguiente: no hay espera ni reintento.

  Los `_login` de cada fichero pasan a usar ese helper.
- **E2E:**
  - la corrida genera `KONTROL_MFA_KEYS` en ejecución;
  - la siembra crea identidades por `parallelIndex` (`admin_w0`…`admin_w5` y las equivalentes de N6), sin factor;
  - un fixture de worker:
    - hace un solo alta y login por API con TOTP calculado en Node (`node:crypto`);
    - guarda la clave y la cookie de refresh en un directorio temporal de la corrida con modo 0600, fuera del repositorio y de la evidencia, que se borra al terminar;
    - encadena la cookie entre pruebas;
    - renueva la reautenticación por API cuando tiene más de 120 s.

  La E2E de MFA (TM-10) usa identidades propias y el flujo real por UI.

## 20. Requisitos de Gobierno (revisión de la fuente, §46 del encargo)

Fuente revisada: `requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf` (texto extraído y leído: tabla 10 de RNF y tabla 7.11 de control interno). Clasificación: PROJECT_REQUIREMENT.

| Requisito | Texto (resumen literal) | Requisito núcleo | Diseño | Pruebas | Estado |
|---|---|---|---|---|---|
| RNF-GOV-011 | «Cifrado en tránsito, secretos fuera de código, MFA para roles privilegiados y rotación de credenciales» | A–F, G, §6 | §4.1, §6, §19.2 | MFA-A..G, MFA-K | MFA de roles privilegiados → **cubierto**. Secretos fuera de código → **cubierto** para la clave MFA (`KONTROL_MFA_KEYS`). Rotación → **cubierta** para la clave MFA (`mfa_rekey`); la rotación de contraseñas y otras credenciales queda **FUTURE_GOV_SPEC / DEPENDENCY** (fuera del MFA). Cifrado en tránsito → despliegue (TLS), fuera de este delta |
| RNF-GOV-006 | «Toda autorización crítica se valida en backend; no confiar en UI ni claims sin verificación contextual» | B5, F2, H2 | §19.4 (`sid` contra la BD, política en cada petición, reautenticación en el backend) | MFA-B09, MFA-H01..02, MFA-F | **cubierto**: el JWT ya no basta, se verifica contra la familia de sesión viva |
| RNF-GOV-012 | «Roles predefinidos no conceden autoridad transversal; permisos por capacidades y alcance» | G1, D4 (techo) | §4.1 (clase por capacidad y no por nombre) | MFA-G00..G, MFA-D | **cubierto** en lo que toca al MFA. El techo de delegación es el gap n.º 2 (**DEPENDENCY**) |
| RNF-GOV-005 | «100 % de transacciones P0 con actor, autoridad, fuente, soporte, timestamp y correlación» | J | §19.2 `_audit_mfa` (actor, `session_id`, `request_id`, IP, fuente `API`/`CLI`) | MFA-J | **cubierto** para los eventos MFA; el catálogo formal es el gap n.º 4 (**DEPENDENCY**) |
| GOV-CTL-002 | «Bitácora append-only de autenticación…» | J | eventos MFA y de sesión en `audit_events` | MFA-J | **cubierto** el registro de la autenticación; append-only con inmutabilidad en BD → OQ-GAB-3 / GOV-5 (**FUTURE_GOV_SPEC**) |
| GOV-CTL-003 | «Autor, actor efectivo, rol, unidad, IP/sesión técnica, timestamp y correlación» | J | `user_id` = actor, `entity_id` = objetivo, `session_id`, `ip`, `request_id` | MFA-J | **cubierto** salvo rol y unidad de Gobierno (**FUTURE_GOV_SPEC**) |
| GOV-CTL-004 | «No permitir al administrador técnico fabricar autoridad funcional para comprometer, pagar o aprobar» | D4 | techo de privilegio del reset; el reset **no** toca la contraseña y obliga a un alta nueva del objetivo | MFA-D08..10 | **cubierto parcialmente**: el reset de MFA no da acceso a la cuenta del objetivo. La separación general entre administrador técnico y autoridad funcional es el gap n.º 2 y Gobierno (**DEPENDENCY / FUTURE_GOV_SPEC**) |
| RNF-GOV-017 | «Logs… sin filtrar secretos» | J2 | lista blanca y sin secretos en registros | MFA-J01..03 | **cubierto** para MFA |

ENGINEERING_REQUIREMENTS_DOCUMENT_REVIEWED = 1 · ENGINEERING_REQUIREMENTS_RECONCILED = 1 (de diseño; se reabre en la reconciliación final) · UNEXPLAINED_REQUIREMENT_OMISSIONS = 0.

## 21. Deudas nuevas detectadas (no absorbidas; NO SILENT SCOPE EXPANSION)

| DEBT_ID | Spec dueña | Categoría | Severidad | Evidencia | Impacto | Bloqueo | Siguiente acción |
|---|---|---|---|---|---|---|---|
| AUTH-PASSWORD-RESET-TOKEN-DISCLOSED | 002 | seguridad | **CRITICAL** | `identity_access/api.py` `reset_request` devuelve `reset_token` al cliente anónimo («flujo demo»); `request_password_reset` da 401 si el usuario no existe | cualquiera que conozca el tenant y el usuario restablece la contraseña de una cuenta STANDARD; enumeración de usuarios. Las cuentas con MFA siguen protegidas por el factor (T22) | no bloquea MFA | ciclo propio de la Spec 002 (canal de entrega del token); escalado a la dueña en el informe |
| INVENTORY-RECOMPUTE-UNGUARDED | 003-inventario | autorización | HIGH | `inventory/api.py:235` `POST /balances/recompute` solo exige sesión | cualquier usuario autenticado reconstruye los saldos de la empresa del contexto | no | delta de la Spec dueña de inventario |
| APPROVAL-CANCEL-WITHOUT-REQUESTER-CHECK | 045 | SoD | HIGH | `approvals/service.py:780-797` | `aprobaciones:create` cancela cualquier solicitud abierta y levanta la puerta | no (mitigado: el permiso pasa a SENSITIVE) | gap n.º 2 (delegación / SoD) |
| APPLY-SOURCE-STATUS-UNCHECKED | 013/038 | integridad financiera | HIGH | `purchasing/service.py:1513-1527` `apply_source` no comprueba el estado de la fuente | se aplican pagos y notas en DRAFT | no | delta de la Spec dueña |
| REGULATORY-DOCUMENT-SELF-VALID | regulatoria | control | MEDIUM | `regulatory/service.py:216-218` crea el documento como `VALID` | un documento autodeclarado levanta bloqueos de despacho | no (mitigado: SENSITIVE) | delta de la Spec dueña |
| GENERIC_LOGIN_RATE_LIMIT_DEBT | 055 | seguridad | — | `login_rate_limit_per_minute` sin uso | — | — | **PRESERVED** (DT-16) |
| ALEMBIC-CHECK-DRIFT-PREEXISTING | 001 | esquema | MEDIUM | `alembic check` sobre una base en `0058` informa diferencias modelo↔migración AJENAS al MFA (presentes en `HEAD` antes de este ciclo; las tablas y columnas de `0058` no aparecen) | P26 (paridad modelo↔migración) no está verificada por máquina para todo el esquema | no | delta de la Spec 001 que convierta `alembic check` en compuerta y cierre las diferencias |
| QA-CRAWLERS-SIN-MFA | 012 | QA | LOW | `resources/frontend/e2e/audit-route-crawler.mjs` y `audit-responsive-crawler.mjs` (herramientas manuales, fuera de la corrida canónica) siguen entrando por formulario con contraseña | con MFA no pasan del segundo factor para `admin` | no | migrarlos al helper `e2e/helpers/sesion.ts` cuando se vuelvan a usar |
| SHELL-SIDEBAR-NOT-RESPONSIVE | 001 | responsive | MEDIUM | `resources/frontend/src/layout/Sidebar.tsx` (`collapsed` empieza en `false`, ancho fijo `w-64`, sin consulta de medios); a 320 px el menú ocupa 256 px y comprime el `main` de TODAS las pantallas (captura de la E2E MFA 14, corrida `r20261026t024651…`); las comprobaciones de «sin scroll horizontal» pasan porque el contenido se recorta, no porque se adapte; axe a 320 px da `target-size` (serious) en la cabecera (`campana` y enlace de licencia, corrida `r20261026t030343…`) | en móvil pequeño el contenido es ilegible hasta plegar el menú a mano | no (la E2E MFA pasa axe de página completa a 1280 px, axe de `main` y scroll a 320 px) | delta de la Spec 001 (shell): menú plegado o en cajón por debajo de `md` |
| TEST-FIXTURE-PASSWORD-LITERAL | 012 | QA | LOW | la contraseña sintética de QA (EGR-MFA-01) sigue como literal en 64 pruebas y guiones y en 22 registros de evidencia de ciclos anteriores; no autentica en ningún entorno persistente y la E2E canónica ya no la usa (TM-EG1) | ninguno de seguridad; incumple el objetivo «EXPOSED_CREDENTIAL_IN_GIT = 0» | no | ciclo de QA: generar el valor en `conftest` y en los guiones manuales; la historia no se reescribe |
| E2E-TRACE-PURGE-REDUCES-DIAGNOSIS | 012 | QA | LOW | TM-9f retira la carpeta entera de una prueba fallida si su traza lleva la respuesta del alta MFA del worker (la primera prueba de cada worker la lleva); en la corrida `r20261026t110824…` se perdió así la traza de `documents-a11y` y solo quedó el error en `suite.log` | menos diagnóstico de los fallos; ningún secreto | no | redactar las respuestas del alta dentro del `trace.zip` en lugar de borrar la carpeta, o hacer el alta del worker en la siembra |
| DOCS-A11Y-UPLOAD-TIMEOUT | 046 | pruebas | MEDIUM | `e2e/documents-a11y.spec.ts` «carga operable solo con teclado» sube con analizador real con el presupuesto por defecto de 30 s y espera 30 s dentro (23,4 s y 31,7 s medidos); sus hermanas de `documents.spec.ts` declaran 120 s | falla por tiempo con el equipo cargado | **sí** (E2E canónica) | **FIXED** en este ciclo (TM-DOC1) |
| E2E-AUDIT-ROW-TWO-EVENTS-PER-REQUEST | 012 | pruebas | MEDIUM | desde `d39f820` un login completo deja `LOGIN_SUCCESS` y `MFA_CHALLENGE_SUCCEEDED` con el mismo `request_id`; `e2e/auditoria-fecha.spec.ts` localizaba la fila por `request_id` y fallaba en modo estricto cuando ambas caían en la primera página (corrida `r20261026t111632…`) | fallo intermitente por orden de eventos | **sí** (E2E canónica) | **FIXED** (TM-AUD1: fila acotada a `LOGIN_SUCCESS`); `auditoria-sobre.spec.ts` ya usaba `.first()` con `toBeVisible` |
| E2E-REAUTH-DIALOG | 002 | pruebas | LOW | la reautenticación vale 5 min desde el login y la E2E no inyecta reloj (OQ-MFA-3 prohíbe atajos): el diálogo «Confirme su identidad» no aparece en E2E | su comportamiento lo cubren `ReauthContext.test.tsx` (6 pruebas) y las de backend (`require_recent_reauth`, MFA-D*) | no | aceptado; revisar si la plataforma de E2E gana un reloj del servidor controlable |

### 21.1 Decisión tomada durante la implementación (BLOCKING_CURRENT_SCOPE)

| ID | Hallazgo | Decisión | Evidencia |
|---|---|---|---|
| LIC-READONLY-MFA-ROUTES | con la licencia en `READ_ONLY`, el middleware bloqueaba `POST /auth/mfa/verify`, `/auth/mfa/enrollment(/confirm)` y `/auth/reauth`, así que nadie con MFA podía iniciar sesión ni reautenticarse para reparar la licencia | se añaden a `LICENSE_EXEMPT_PREFIXES` junto a `login`/`refresh`, que ya lo estaban: completan la autenticación, no escriben datos de negocio | `evidence/mfa-privileged-roles/red-tm-5c.txt` (rojo → verde, 17 pruebas) |

## 22. Reconciliación final de Gobierno (fuente releída al cierre, 2026-10-26)

Fuente: `requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf` (texto extraído de nuevo; tablas de RNF, 7.11 de
control interno y de servicios digitales). Clasificación: PROJECT_REQUIREMENT. Este delta es SHARED_CORE: deja la base que Gobierno heredará;
no implementa Gobierno (GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0; sin módulos `gov_*`, sin GOV-0, sin GOV-SPEC, sin Spec 057; la línea base
`9a41503` sigue en la historia y `requerimientos/` no tiene cambios rastreados).

| Requisito | Estado al cierre | Evidencia de implementación |
|---|---|---|
| RNF-GOV-011 seguridad | **COVERED** en MFA de roles privilegiados, secretos fuera del código (`KONTROL_MFA_KEYS`, nunca en el repositorio ni en la evidencia) y rotación de la clave MFA (`mfa_rekey`); **FUTURE_GOV_SPEC / DEPENDENCY** la rotación de contraseñas y demás credenciales; TLS es despliegue | `test_mfa_*` (backend), mutantes M01–M11 muertos (`mutaciones.md`), runbook de rotación en `backup-restore-plan.md` §7 |
| RNF-GOV-006 autorización en backend | **COVERED**: `sid` contra la familia de sesión viva, política y reautenticación en el servidor | `test_mfa_session_authority.py`, `test_mfa_no_bypass.py`, M02/M03/M10 muertos |
| RNF-GOV-012 mínimo privilegio | **COVERED** para el MFA (clase por capacidad, no por nombre de rol); el techo general de delegación sigue como gap n.º 2 (**DEPENDENCY**) | `test_mfa_policy.py`, M01 muerto, §4.1 |
| RNF-GOV-005 / GOV-CTL-002 / GOV-CTL-003 trazabilidad | **COVERED** para los eventos MFA (actor, objetivo, sesión, IP, `request_id`, fuente); append-only con inmutabilidad en BD, y rol y unidad de Gobierno → **FUTURE_GOV_SPEC** (OQ-GAB-3 / GOV-5) | `test_mfa_audit_no_leak.py`; E2E `mfa.spec.ts` y suites con rastro de auditoría |
| GOV-CTL-004 el administrador técnico no fabrica autoridad | **PARTIAL (por diseño)**: el reset de MFA tiene techo de privilegio, no puede hacerse sobre uno mismo, no toca la contraseña y obliga a un alta nueva; la separación general administrador técnico ↔ autoridad funcional es gap n.º 2 / Gobierno | M06/M07 muertos; E2E 08–09 (reset y revocación) |
| RNF-GOV-017 observabilidad sin secretos | **COVERED**: lista blanca de auditoría, registros sin secretos; la evidencia E2E retira por sí misma el material MFA de las trazas de pruebas fallidas (TM-9f) | `test_mfa_audit_no_leak.py`, `test_e2ecorrida_33/33b`, barrido de `qa/e2e-runs/` = 0 |
| RNF-GOV-010 copias y restauración | **COVERED en documentación**: el anillo de claves MFA es parte de lo que se respalda y custodia (sin él, los factores no se descifran) y tiene runbook de rotura de cristal; **DEPENDENCY** el simulacro de restauración con validación antes de producción (no se ejecutó en este ciclo) | `backup-restore-plan.md` §2 y §7, ADR-004 (extensión) |
| RNF-GOV-014 / GOV-DIG-007 accesibilidad | **COVERED** en las pantallas MFA (axe WCAG 2.0/2.1/2.2 AA sin violaciones serias, teclado, 320 px sin scroll horizontal); la cabecera del shell a 320 px es la deuda SHELL-SIDEBAR-NOT-RESPONSIVE (§21) | E2E `mfa.spec.ts` 14; vitest de las pantallas MFA |
| RNF-GOV-015 interoperabilidad | **COVERED** para las rutas MFA: contrato OpenAPI, códigos de error deterministas (`MFA_*`, `REAUTH_REQUIRED`) | `test_openapi_security.py`, `openapi-routes.json`, `contracts/api-contracts.md` |
| RNF-GOV-016 portabilidad | **COVERED**: `segno==1.6.6` (BSD, Python puro) y criptografía ya presente; ninguna dependencia propietaria | `dependencias.md` (pip-audit limpio) |
| GOV-DIG-004 intercambio entre organismos | **FUTURE_GOV_SPEC**: el MFA protege a personas; la autenticación máquina-a-máquina entre organismos no es de este delta | — |

ENGINEERING_REQUIREMENTS_DOCUMENT_REVIEWED = 1 · ENGINEERING_REQUIREMENTS_RECONCILED = 1 (final) · UNEXPLAINED_REQUIREMENT_OMISSIONS = 0 ·
GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 · GOVERNMENT_MODULES_CREATED = 0.

## 23. Resumen de ejecución y evidencia (cierre, 2026-10-26)

Todo el código, las pruebas, el código de QA y la documentación de producto los escribió DeepSeek; Claude diseñó, auditó, aplicó tal
cual y verificó (detalle por tarea, reintentos, rechazos y coste en `evidence/mfa-privileged-roles/orchestration.md`). Excepciones de
formato de Claude: `ruff --select I --fix` (OD-ORCH-01) y la regeneración mecánica de `openapi-routes.json`.

| Verificación | Orden | Resultado |
|---|---|---|
| Backend PostgreSQL con analizador real y telemetría | `qa/suite_tiempos.py --motor postgres --con-analizador` | 3386 pasan · 0 fallan · 18 omitidas · anomalía NORMAL (`qa/backend-runs/r20261026t033649…`) |
| Backend SQLite con analizador real y telemetría | `qa/suite_tiempos.py --motor sqlite --con-analizador` | 2336 pasan · 0 fallan · 1068 omitidas (solo PostgreSQL) · NORMAL (`r20261026t041014…`); los 9 ficheros reordenados por `ruff` se repitieron después en ambos motores (100+4 / 104) |
| Migración `0058` | `test_spec002_migration_0058.py` (instalación limpia, actualización, bajada y subida) en PostgreSQL | verde |
| `ruff` / `mypy` | `ruff check` · `mypy app` | ruff limpio; mypy sin errores en código del ciclo (los 154 restantes están en líneas confirmadas antes de este ciclo) |
| Frontend | `tsc -b` · `eslint --max-warnings 0` · `vitest` · `vite build` | 0 · 0 · 545/545 · build correcto |
| E2E canónica completa con analizador | `qa/e2e-run.py --con-analizador` | **306 pasan · 0 fallan · 0 omitidas**, proyectos de licencia incluidos; limpieza LIMPIA; `material_mfa` 0; bases protegidas sin cambios (`qa/e2e-runs/r20261026t033040…`) |
| E2E MFA multinavegador | `qa/e2e-run.py --con-analizador -- --project=firefox --project=webkit e2e/mfa.spec.ts e2e/sesion-totp.spec.ts` | 66/66 (22 por motor: chromium, firefox, webkit) |
| Base tras la E2E | `qa/e2e-bases.py listar` · manifiesto | 0 bases de corrida · `protegidas_sin_cambios = true` · puertos 8000/5173/8010 libres |
| Mutaciones | `mutaciones.md` | 11/11 muertas (MUTATION_SURVIVORS = 0); más la mutación de la invalidación de TM-10c (muere) |
| Dependencias | `dependencias.md` | `segno==1.6.6` (BSD), pip-audit limpio, `pip check` correcto |
| Fugas | barrido de los ficheros del ciclo y de `qa/e2e-runs/` | 0 claves, códigos u `otpauth://` reales; solo marcadores, alfabeto base32 y el vector público RFC 6238 |
| Residuos | `.mutbak`/`.orig`/`.rej`/`.bak`, bases, puertos, estado E2E | 0; el único no rastreado ajeno al ciclo es material de la dueña (`requerimientos/KONTROL_SNAT_2026_00093.docx`), intacto y fuera del commit |

Trazabilidad: cada requisito de §2 (A–M) tiene su diseño (§4–§10, §19), sus pruebas (MFA-A..M en backend, vitest de cada pantalla,
`e2e/mfa.spec.ts` 01–14) y su evidencia en esta tabla; las decisiones (§18, §21.1) y las deudas (§21) tienen dueño y siguiente acción;
Gobierno queda reconciliado en §22. TRACEABILITY_COMPLETE = 1 · MFA_BYPASS = BLOCKED · NEGATIVE_AUTHORIZATION verificada (MFA-D, MFA-H,
`test_mfa_no_bypass.py`) · CURRENT_SECRET_EXPOSURE = 0 · HISTORICAL_EGRESS_INCIDENT = 1 (EGR-MFA-01, §24.1; corregido el 2026-10-26: la versión anterior decía «SECRET_EXPOSURE = 0» sin distinguir el incidente histórico) · PRODUCTION_TOUCHED = 0.

## 24. Cierre de gobernanza del MFA (Fase A, 2026-10-26)

El código de `d39f820` no se reescribe. Esta fase repara el contrato de cierre:
- el incidente de EGRESS;
- la revisión de pantallas y formularios;
- la reconciliación de Gobierno releída;
- la convergencia;
- las métricas.

### 24.1 Incidente EGR-MFA-01

Reconciliado en `evidence/mfa-privileged-roles/egress-incident.md`. El valor es una contraseña SINTÉTICA de QA, ya presente en el
repositorio; no autentica en ningún entorno persistente.

Medidas tomadas:
- **Rotación:** la E2E canónica genera una contraseña por corrida (TM-EG1, `test_e2ecorrida_34`).
- **Purga:** se eliminaron 623 artefactos locales en `qa/e2e-runs` y 159 copias en el scratchpad (quedan 0).

Métricas: EGRESS_INCIDENT_COUNT = 1 · EGRESS_INCIDENT_SYNTHETIC = 1 · EXPOSED_CREDENTIAL_STILL_VALID = 0 ·
EXPOSED_CREDENTIAL_ROTATED_OR_DESTROYED = 1 · EXPOSED_CREDENTIAL_IN_EVIDENCE = 0 · CURRENT_SECRET_EXPOSURE = 0 · EGRESS_INCIDENT_CLOSED = 1.

La métrica EXPOSED_CREDENTIAL_IN_GIT = 1 contradice el objetivo, y la contradicción queda explicada: es un dato de prueba anterior al
incidente, que el incidente no añadió. Queda la deuda TEST-FIXTURE-PASSWORD-LITERAL (LOW).

### 24.2 Screen / Form Completeness

Revisión completa en `evidence/mfa-privileged-roles/screen-form-completeness.md`: 8 pantallas, 8 campos, estados y recorrido por actor.

Huecos corregidos, con rojo atribuido y luego verde:
- **MFA-SF-01:** estado del factor en Usuarios, botón solo con factor y refresco tras el reset (TM-SF1a/b). Rojo: `KeyError: 'mfa_enabled'`
  en el backend y la prueba de la fila en vitest.
- **MFA-SF-02:** ayuda para quien no tiene ni la aplicación ni códigos (TM-SF1b). Rojo en vitest.

El resto de huecos queda clasificado (FUTURE_SPEC / DEPENDENCY / OUT_OF_SCOPE con motivo).

Métricas: MFA_SCREEN_PROCESS_COMPLETENESS = PASS · UNEXPLAINED_UI_FUNCTIONAL_GAPS = 0.

### 24.3 Ingeniería de Requerimientos de Gobierno (releída)

Se releyó el PDF desde su texto extraído (SHA-256 `8f86615f63ecfa0b…`), sin apoyarse en el resumen de §22. Se ratifica §22 y se añaden
los requisitos que aplican al MFA y no estaban:

| Requisito | Estado | Evidencia |
|---|---|---|
| RNF-GOV-018 retención y legal hold | **DEPENDENCY** | La retención configurable de eventos de auditoría y desafíos MFA es transversal: catálogo de auditoría (P0 n.º 3) y Gobierno |
| RNF-GOV-019 migraciones de una cabeza, instalación limpia y actualización en PostgreSQL | **COVERED** | `0058_spec002_mfa`, cabeza única; `test_spec002_migration_0058.py` (limpia, actualización, bajada y subida) en PostgreSQL |
| RNF-GOV-020 QA (unitarias, contrato, integración PostgreSQL, E2E principal y hostil, regresión, mutación) | **COVERED** | §23 y §24.5 |
| E2E-06 hostil multi-ente (aplicado al MFA) | **COVERED** | MFA-D06: reset de otro tenant → denegado; listado acotado al tenant |

Métricas: ENGINEERING_REQUIREMENTS_DOCUMENT_REVIEWED = 1 · ENGINEERING_REQUIREMENTS_RECONCILED = 1 · APPLICABLE_REQUIREMENTS_COVERAGE = 100 %
(COVERED, PARTIAL por diseño, DEPENDENCY o FUTURE_GOV_SPEC, todos con motivo) · UNEXPLAINED_REQUIREMENT_OMISSIONS = 0 ·
FUNCTIONALITY_ACCIDENTALLY_OMITTED = 0 · GOVERNMENT_REQUIREMENT_LINKAGE_RECONCILED = 1.

### 24.4 Convergencia

`/speckit-converge` no se puede aplicar a un delta. Su paso 1 (`check-prerequisites.sh --require-spec --require-tasks`) resuelve siempre
`specs/012-auditoria-integral-e2e` (`.specify/feature.json`), que no tiene `spec.md` ni `plan.md`, así que la orden se detiene antes de
evaluar; además no lee ficheros `specNNN-*-delta.md`. Se aplica la convergencia equivalente sobre este delta, por dimensión:

| Dimensión | Resultado |
|---|---|
| Requisitos (§2 A–M) | Todos con diseño, prueba y evidencia (§16, §23) |
| Tareas (§15) | TM-A…TM-11 hechas. **Hallazgo:** TM-9 pedía una «siembra con secreto de corrida» y solo la clave MFA era de corrida → `partial`, cerrado con TM-EG1. TM-8 nombraba `ReauthDialog.tsx`; el diálogo vive en `ReauthContext.tsx` (misma función; se reconcilia el nombre) |
| Código | Sin código no pedido; TM-SF1 añade solo lo que exigen MFA-SF-01/02 |
| Pruebas | Backend, vitest, E2E y mutaciones (§23); rojos atribuidos de TM-SF1 |
| Evidencia | `evidence/mfa-privileged-roles/` (orquestación, incidente, revisión de pantallas, mutaciones, dependencias) |
| Hoja de ruta | Secuencia OD-SEC-PRIORITY-01: siguiente, AUTH-PASSWORD-RESET-TOKEN-DISCLOSED |
| Deuda técnica | §21, más TEST-FIXTURE-PASSWORD-LITERAL (LOW) |
| Trazabilidad | Completa |
| Pantallas y formularios | PASS (§24.2) |
| Residuos | Ver §24.5 |
| Git | Solo ficheros del ciclo; material de la dueña intacto |

MFA_CONVERGENCE = PASS.

### 24.5 Verificación de la Fase A

| Verificación | Resultado |
|---|---|
| `test_e2e_corrida` (PostgreSQL) | 36/36, incluida la 34 (contraseña por corrida) |
| `test_mfa_management` | 19/19 (rojo `KeyError: 'mfa_enabled'` → verde) |
| Pruebas backend que tocan el listado de usuarios | 84 pasan, 6 omitidas (solo PostgreSQL) |
| Frontend | vitest 546/546 · tsc 0 · eslint 0 |
| E2E canónica con analizador (corrida `r20261026t112502…`) | **306 pasan · 0 fallan · 0 omitidas**; limpieza LIMPIA; `material_mfa` 0; bases protegidas sin cambios; valor histórico en la evidencia: 0 |
| Corridas intermedias | `r20261026t110824…`: DOCS-A11Y-UPLOAD-TIMEOUT (preexistente) → TM-DOC1. `r20261026t111632…`: E2E-AUDIT-ROW-TWO-EVENTS-PER-REQUEST → TM-AUD1. Las dos causas están medidas; no se reintentó para ver verde |
| Multinavegador MFA (`mfa.spec.ts` + vectores TOTP) | **66/66** en chromium, firefox y webkit (`r20261026t113201…`); REAL_SAFARI_NOT_MEASURED |
| Residuos | 0 bases de corrida; puertos libres; scratchpad sin el valor histórico |

**MFA_STATUS = CLOSED / CONVERGED** (Fase A: A1–A5 PASS).
