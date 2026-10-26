# MFA · Screen / Form Completeness Review (2026-10-26)

**Alcance:** toda la interfaz del MFA que entró con `d39f820`.

**Actores:**
- **PRIVILEGED** y **SENSITIVE**: el MFA es obligatorio (OQ-MFA-1 = A).
- **STANDARD**: el MFA es voluntario.
- **AUTHORIZED_ADMIN**: quien tiene `users:mfa_reset`, que es una capacidad SENSITIVE, así que también lleva MFA y reautenticación.

**Fuentes de verdad:**
- el backend, que es quien autoriza;
- `auth_mfa_factors`, el origen de verdad del factor;
- `users.mfa_enabled`, una vista derivada de lo anterior.

**Huecos encontrados en esta revisión:**
- **MFA-SF-01** — estado del factor y lista en Usuarios: corregido en TM-SF1a/b.
- **MFA-SF-02** — ayuda cuando no hay ni la aplicación ni códigos: corregido en TM-SF1b.

## 1. Inventario de pantallas

| SCREEN_ID | SCREEN_NAME | PROCESS_ID | BUSINESS_PURPOSE | PRIMARY_USER_GOAL | ACTORS | ENTRY / PRECONDITIONS | POSTCONDITIONS |
|---|---|---|---|---|---|---|---|
| MFA-S01 | Login · paso 2 (`/login`) | P-AUTH-01 inicio de sesión | Probar el segundo factor antes de emitir sesión | Entrar con el código de la aplicación o con uno de recuperación | PRIVILEGED, SENSITIVE, STANDARD con factor | Contraseña correcta → `MFA_REQUIRED`. El `challenge_token` vive solo en memoria (ni URL ni almacenamiento) | Sesión con `mfa_verified_at`, o bloqueo, o vuelta al paso 1 |
| MFA-S02 | Alta obligatoria (`/acceso/mfa/alta`) | P-AUTH-02 alta por desafío | Que nadie privilegiado opere sin factor | Configurar la aplicación y guardar los códigos | PRIVILEGED, SENSITIVE sin factor | `MFA_ENROLLMENT_REQUIRED` con desafío en el estado de navegación; sin estado → `/login` | Factor ACTIVE + 10 códigos + sesión |
| MFA-S03 | Alta con sesión / reemplazo (`/seguridad/mfa/alta`) | P-MFA-03 alta voluntaria o reemplazo | Activar (STANDARD) o cambiar de aplicación (todos) | Igual que S02 | Todos con sesión | Bearer + reautenticación reciente | Factor ACTIVE (el anterior queda reemplazado); estado refrescado (TM-10c) |
| MFA-S04 | Verificación en dos pasos (`/seguridad/mfa`) | P-MFA-04 gestión propia | Ver y mantener el propio factor | Ver el estado, regenerar códigos, reemplazar o quitar (solo STANDARD) | Todos con sesión | Sesión | Según la acción |
| MFA-S05 | QR + clave manual (componente de S02/S03) | P-AUTH-02 / P-MFA-03 | Transferir el secreto a la aplicación | Escanear o teclear la clave | Quien hace el alta | Alta iniciada | — |
| MFA-S06 | Panel de códigos de recuperación (S02/S03/S04) | P-MFA-05 | Entregar los códigos una sola vez | Copiarlos o descargarlos y confirmar que los guardó | Quien da de alta o regenera | Alta confirmada o regeneración | El usuario los guardó; no vuelven a mostrarse |
| MFA-S07 | Diálogo «Confirme su identidad» | P-MFA-06 reautenticación | Volver a probar identidad antes de una operación sensible | Confirmar con contraseña y código | Todos con sesión | Respuesta `REAUTH_REQUIRED` de una ruta protegida | `reauth` fresca (5 min) y la operación se reintenta |
| MFA-S08 | Restablecer verificación (Usuarios) | P-MFA-07 reset administrativo | Recuperar a quien perdió dispositivo y códigos | Restablecer el factor de otro usuario | AUTHORIZED_ADMIN | `users:mfa_reset`, MFA, reautenticación, techo de privilegio, mismo tenant, nunca a sí mismo | Factor del objetivo eliminado, sesiones del objetivo revocadas y alta obligatoria en su próximo inicio |

**ROLE_ACTION_MATRIX (backend autoritativo):**

| Actor | S01 | S02 | S03 | S04: quitar | S04: regenerar | S08 |
|---|---|---|---|---|---|---|
| PRIVILEGED / SENSITIVE | sí | sí (obligatoria) | reemplazo | **no** (`MFA_REQUIRED_BY_POLICY`) | sí, con reautenticación | solo con `users:mfa_reset`, dentro del techo |
| STANDARD | si tiene factor | no | alta y reemplazo | sí, con reautenticación | sí, con reautenticación | no (403) |

## 2. Contrato de campos

| FIELD_ID | LABEL | TYPE / FORMAT | REQUIRED / RO | SOURCE | VALIDATION (UI → backend) | ERROR | HELP | AUDIT | API / DB / UI |
|---|---|---|---|---|---|---|---|---|---|
| F-MFA-01 OTP | «Código de verificación» (`#mfa-code`, `#reauth-code`, paso 3 del alta) | 6 dígitos; admite un espacio central (`maxLength` 7), `inputMode=numeric`, `autocomplete=one-time-code` | Obligatorio; editable | Aplicación del usuario | UI: forma. Backend: TOTP SHA-1/30 s, paso actual o +1, antirrepetición por `last_used_step` (CAS) | «Código incorrecto. Le quedan N intentos.», «Ese código ya se usó…» | Texto del paso | `MFA_CHALLENGE_SUCCEEDED/FAILED` **sin el código** | API `code`; DB solo `last_used_step`; nunca persistido en el cliente |
| F-MFA-02 Código de recuperación | «Código de recuperación» (`#recovery-code`) | `XXXX-XXXX-XXXX-XXXX` (`maxLength` 19), `autocomplete=off` | Obligatorio en su modo | Panel S06 | Backend: hash, un solo uso (`used_at IS NULL`, condicional) | Mismo contrato de intentos | Enlace «Usar un código de recuperación» y ayuda MFA-SF-02 | `MFA_RECOVERY_CODE_USED` sin el código | DB `code_hash`; UI avisa de los restantes |
| F-MFA-03 Clave manual | «¿No puede escanear? Introduzca esta clave» | Base32 en grupos dentro de `<code aria-label="Clave manual…">`; solo lectura; botón «Copiar clave» | RO | Respuesta del alta | — | — | Texto del paso 2 | Nunca auditada | API `manual_key` solo en la respuesta del alta; DB cifrada AES-GCM con AAD; UI solo en memoria |
| F-MFA-04 QR | (imagen, `alt` descriptivo) | `<img src="data:image/svg+xml…">` (segno; OQ-MFA-2) | RO | Respuesta del alta | — | — | — | Nunca | Igual que F-MFA-03 |
| F-MFA-05 Lista de códigos | Lista `<ol>` de 10 | Solo lectura; copiar o descargar `.txt` (data URI, sin `createObjectURL`) | RO | Alta o regeneración | — | — | `role=status`: no volverán a verse | Solo el hecho (`MFA_RECOVERY_CODES_REGENERATED`) | Una vez en la API; hash en la BD; nunca en almacenamiento |
| F-MFA-06 Confirmación de guardado | «He guardado mis códigos…» | Casilla | Obligatoria para continuar | Usuario | «Continuar» deshabilitado hasta marcarla | — | — | — | Solo UI |
| F-MFA-07 Contraseña de reautenticación | «Contraseña» (`#reauth-password`) | `autocomplete=current-password` | Obligatoria | Usuario | Backend: Argon2id; cuenta para el bloqueo | `REAUTH_FAILED`, bloqueo | — | `MFA_REAUTH_SUCCEEDED/FAILED` sin la credencial | Nunca persistida |
| F-MFA-08 Usuario objetivo del reset | Fila de Usuarios (texto `<usuario> · …`) | Selección por botón de fila | — | `GET /users` (tenant de quien pregunta) | Backend: permiso, techo, mismo tenant, no a sí mismo | `MFA_RESET_CEILING`, `MFA_NOT_CONFIGURED`, `PERMISSION_DENIED` | Diálogo de confirmación con el nombre | `MFA_RESET_BY_ADMIN` (actor, objetivo, sesión, `request_id`) | API `user_id` en la ruta; UI muestra el estado del factor (MFA-SF-01) |

Ningún secreto (clave, OTP, código, contraseña) va a auditoría, analítica, registros o caché persistente del frontend. Lo prueban:
- `test_mfa_audit_no_leak.py`;
- la prueba de vitest «no escribe en localStorage ni sessionStorage»;
- el caso E2E 07;
- TM-9f, para la evidencia.

## 3. Estados por pantalla

Leyenda: ✔ cubierto y probado · N/A no aplica (con motivo) · DEP dependencia registrada.

| Estado | S01 | S02/S03 | S04 | S07 | S08 |
|---|---|---|---|---|---|
| NORMAL | ✔ | ✔ | ✔ | ✔ | ✔ |
| LOADING | ✔ «Verificando…» | ✔ | ✔ `LoadingState` | ✔ | ✔ «Cargando…» |
| EMPTY | N/A | N/A | N/A (siempre hay estado) | N/A | ✔ «Sin usuarios registrados.» |
| ERROR | ✔ | ✔ `ErrorState` | ✔ `ErrorState` con `request_id` y reintento | ✔ | ✔ `role=alert` |
| PERMISSION_DENIED | N/A | N/A | ✔ `MFA_REQUIRED_BY_POLICY` | N/A | ✔ sin botón; 403 → mensaje |
| DISABLED | N/A | ✔ «Continuar» hasta confirmar | ✔ «Ocultar códigos» hasta confirmar | N/A | ✔ sin botón si no hay factor (SF-01) |
| VALIDATION_ERROR | ✔ código mal formado | ✔ | N/A | ✔ | N/A |
| CONFLICT / CONCURRENT_MODIFICATION | ✔ antirrepetición CAS | ✔ `MFA_NO_PENDING_ENROLLMENT` (alta reiniciada en otra pestaña) | ✔ regenerar invalida el lote anterior (C04); la UI refresca | N/A | ✔ objetivo ya sin factor → `MFA_NOT_CONFIGURED` y refresco |
| OFFLINE | ✔ «Sin conexión…» | ✔ | ✔ | ✔ | ✔ |
| SAVE_SUCCESS | ✔ entra | ✔ «Segundo factor activado» | ✔ avisos | ✔ | ✔ «Verificación restablecida» y refresco |
| UNSAVED_CHANGES | N/A (sin datos de formulario que conservar) | N/A: abandonar el alta deja un alta pendiente que caduca; el secreto no debe persistir | N/A | N/A | N/A |
| STALE_DATA | N/A | ✔ invalida el estado al terminar (TM-10c) | ✔ | N/A | ✔ invalida la lista tras el reset (SF-01) |
| PROCESS_BLOCKED | ✔ bloqueo | ✔ | N/A | ✔ | N/A |
| MFA_REQUIRED | ✔ | — | ✔ «Su rol exige verificación…» | — | — |
| MFA_ENROLLMENT_REQUIRED | ✔ navega a S02 (estado, no URL) | ✔ | — | — | — |
| INVALID_CODE | ✔ intentos restantes | ✔ | — | ✔ | — |
| EXPIRED_CHALLENGE | ✔ `MFA_CHALLENGE_INVALID` → paso 1 | ✔ → `/login` | — | — | — |
| REPLAYED_CODE | ✔ `MFA_CODE_ALREADY_USED` | ✔ | — | ✔ (mismo backend) | — |
| RATE_LIMITED | ✔ `AUTH_ACCOUNT_LOCKED` (423) tras 5 fallos; límites en BD (`MFA_ABUSE_PROTECTION`) | ✔ | — | ✔ | — |
| RECOVERY_CODE_USED | ✔ aviso de los restantes | — | ✔ contador | ✔ | — |
| RECOVERY_CODES_EXHAUSTED | ✔ queda el TOTP; sin ambos → ayuda SF-02 y reset S08 | — | ✔ aviso con ≤ 3 (incluye 0) | — | — |
| FACTOR_ALREADY_CONFIGURED | — | ✔ S03 es reemplazo («Reemplazar la aplicación») | ✔ | — | — |
| MFA_DISABLED | — | — | ✔ «Desactivada» + «Configurar» | — | ✔ «no configurada» (SF-01) |
| RESET_COMPLETED | ✔ el objetivo vuelve a S02 | ✔ | — | — | ✔ |
| REAUTH_REQUIRED / REAUTH_EXPIRED | — | ✔ | ✔ el cliente abre S07 | ✔ | ✔ (ruta protegida) |
| MFA_UNAVAILABLE (sin anillo de claves) | ✔ «Contacte con el administrador» | ✔ | — | — | — |

## 4. Recorrido funcional por actor

| Paso | PRIVILEGED / SENSITIVE | STANDARD | AUTHORIZED_ADMIN | Evidencia |
|---|---|---|---|---|
| Primer login → alta obligatoria | ✔ | sin MFA | — | E2E 01; MFA-B |
| QR y clave manual | ✔ | ✔ (voluntario) | — | E2E 01/11; vitest de `MfaQrImage` |
| Fallo de validación en el alta | ✔ | ✔ | — | vitest de `MfaAltaPage`; MFA-A |
| Generación y confirmación de códigos | ✔ | ✔ | — | E2E 01/06 |
| Cerrar sesión y volver a entrar | ✔ | ✔ | — | E2E 02/13 |
| OTP erróneo, OTP válido y repetición | ✔ | ✔ | — | E2E 04/02/10 |
| Uso y reutilización de un código de recuperación | ✔ / ✔ | ✔ | — | E2E 03; MFA-C, M05 |
| Regeneración | ✔ | ✔ | — | E2E 06; C04 |
| Reautenticación | ✔ | ✔ | ✔ | `ReauthContext.test` (6); MFA-F; E2E-REAUTH-DIALOG (DEP) |
| Reset administrativo y revocación de sesiones | objetivo | objetivo | ✔ | E2E 08/09; MFA-D, M06/M07 |
| Refresco del estado del factor | ✔ | ✔ | ✔ (SF-01) | TM-10c; TM-SF1 |
| Móvil a 320 px | ✔ | ✔ | ✔ | E2E 14 (axe de `main` y scroll); shell → DEP |

SENSITIVE comparte flujo con PRIVILEGED. Lo prueba la clasificación del backend (MFA-G: `aprobaciones:create` y similares exigen MFA); la E2E usa ADMIN, que es PRIVILEGED.

**MFA_SCREEN_PROCESS_COMPLETENESS = PASS.**

## 5. Gap analysis

| Categoría | Hueco | Clasificación |
|---|---|---|
| MISSING_FIELDS | Estado del factor en Usuarios | **FIXED** (MFA-SF-01) |
| MISSING_FIELDS | Motivo del reset administrativo | **FUTURE_SPEC**: catálogo de auditoría (P0 n.º 3), que define qué eventos llevan motivo para toda la plataforma |
| MISSING_ACTIONS | — | ninguno (imprimir los códigos: EXPLICITLY_OUT_OF_SCOPE; copiar y descargar bastan, y la impresión depende del navegador) |
| MISSING_STATES | UNSAVED_CHANGES en el alta | EXPLICITLY_OUT_OF_SCOPE: el secreto no debe persistir; el alta pendiente caduca y se reinicia |
| MISSING_VALIDATIONS | — | ninguno |
| MISSING_PERMISSIONS | — | ninguno (el backend es autoritativo; prueba NEGATIVE en MFA-D/H) |
| MISSING_AUDIT | Motivo del reset | FUTURE_SPEC (ver arriba) |
| MISSING_HELP | Qué hacer sin aplicación ni códigos | **FIXED** (MFA-SF-02) |
| MISSING_ERROR_HANDLING | `MFA_RESET_SELF_FORBIDDEN` y `MFA_METHOD_REQUIRED` sin texto propio en la UI | EXPLICITLY_OUT_OF_SCOPE: inalcanzables desde la UI (no hay botón sobre uno mismo; la UI siempre envía un único método); si llegan, se muestra el mensaje en castellano del backend |
| MISSING_RESPONSIVE_BEHAVIOR | Cabecera del shell a 320 px | DEPENDENCY: SHELL-SIDEBAR-NOT-RESPONSIVE (Spec 001); el contenido MFA pasa axe y no tiene scroll a 320 px |
| MISSING_ACCESSIBILITY | — | ninguno (axe WCAG 2.0/2.1/2.2 AA sin violaciones serias en S01, S02 y S04; teclado y foco en vitest) |
| MISSING_E2E | Diálogo de reautenticación | DEPENDENCY: E2E-REAUTH-DIALOG (aceptado; OQ-MFA-3 prohíbe forzar el reloj) |

**UNEXPLAINED_UI_FUNCTIONAL_GAPS = 0.**
