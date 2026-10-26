# Recuperación de contraseña · Screen / Form Completeness Gate (2026-10-26)

**Base del diseño:** contrato de §10 del delta `spec002-password-reset-token-delta.md`.

**Base de la evidencia:**
- `ResetPasswordPage.test.tsx` (10 pruebas);
- `e2e/password-reset.spec.ts` (7 casos × 3 motores);
- las pruebas de backend `test_password_reset_security.py`.

## 1. Gate por pantalla

| | RST-S01 «Solicitar» | RST-S02 «Tengo un código» | RST-S03 «Hecho» |
|---|---|---|---|
| PROCESS | P-RST-01 solicitar | P-RST-02 fijar contraseña | P-RST-02 cierre |
| ACTORS | persona sin acceso (anónima) | persona con código del soporte (anónima) | idem |
| FIELDS | RST-F01 empresa, RST-F02 usuario | RST-F03 código, RST-F04 contraseña, RST-F05 confirmación | — |
| ACTIONS | «Solicitar recuperación», «Tengo un código», «Volver al inicio de sesión» | «Restablecer contraseña», «Volver a solicitar», «Volver al inicio de sesión» | «Ir al inicio de sesión» |
| STATES | NORMAL, LOADING, VALIDATION_ERROR (campos vacíos), SUCCESS (aviso neutro tras el 202), ERROR/OFFLINE (`role=alert`) | NORMAL, LOADING (doble envío bloqueado), VALIDATION_ERROR (código vacío, no coinciden, política), TOKEN_INVALID, TOKEN_EXPIRED, TOKEN_USED (también reemplazado por uno nuevo), OFFLINE | SUCCESS (`role=status`) |
| PERMISSIONS | público; ninguna autorización depende de la UI | público; la autoridad es el token (backend) | — |
| VALIDATIONS | UI: no vacíos. Backend: forma (422 si falta un campo, igual para todos) | UI: no vacío, coincidencia. Backend: política, hash, uso, invalidación, caducidad, usuario activo | — |
| DB/API | 202 `{ok}`; sin filas de `password_resets`; auditoría limitada | 200/400/422; consumo atómico; sello rotado; sesiones revocadas; MFA intacto | — |
| AUDIT | `PASSWORD_RESET_REQUESTED` (≤ 1 por usuario cada 15 min; nunca para cuentas inexistentes) | `PASSWORD_RESET_COMPLETED`, `PASSWORD_RESET_FAILED` (`INVALID`, `EXPIRED`, `USED`), `PASSWORD_RESET_TOKEN_INVALIDATED`, `SESSIONS_REVOKED_SECURITY_CHANGE` | — |
| SECURITY | no revela existencia, estado, rol, MFA ni destino; sin token en la respuesta | el código no va a la URL ni al almacenamiento; se borra del estado tras éxito, caducidad o uso | orienta sobre sesiones y MFA |
| RESPONSIVE | 320 px sin scroll horizontal (E2E 07) | 320 px sin scroll horizontal (E2E 07) | — |
| ACCESSIBILITY | axe WCAG 2.0/2.1/2.2 AA sin serias (E2E 07); etiquetas y errores asociados (`FormField`) | idem; `autocomplete=off` en el código y `new-password` en las contraseñas | `role=status` |
| E2E | 01, 07 | 02, 03, 04, 05, 06, 07 | 02 |
| STATUS | **PASS** | **PASS** | **PASS** |

RST-S05 (reset administrativo web) y RST-S06 (cambio forzado con credencial temporal) **no existen** y no se crean: D-02 y §10.1 del delta.

## 2. Preguntas funcionales (§37 del encargo)

| Pregunta | Respuesta |
|---|---|
| ¿Qué intenta la persona? | Volver a entrar sin conocer su contraseña |
| ¿Qué debe revelar el sistema? | Cómo continuar (el soporte le da un código) y, al terminar, que se cerraron sus sesiones y que el MFA se sigue pidiendo |
| ¿Qué NO debe revelar? | Si la cuenta existe, su estado, su rol, su MFA, el destino de entrega ni el código |
| ¿Qué autoridad exige? | La posesión del código (un uso, 15 min); emitirlo exige acceso al servidor (CLI local, auditada) |
| ¿Qué evidencia queda? | Los eventos de auditoría de la fila AUDIT, sin token ni contraseñas |
| ¿Qué pasa con las sesiones? | Todas quedan revocadas y su sello deja de coincidir; ni las de una carrera sobreviven |
| ¿Qué pasa con el MFA? | Nada: el factor y los códigos se conservan y el siguiente login lo exige |
| ¿Y si se repite la solicitud? | La misma respuesta; como mucho un evento de auditoría cada 15 min |
| ¿Y si se reutiliza el código? | 400 `RESET_TOKEN_USED` (auditado); dos usos simultáneos → exactamente un éxito |
| ¿Y si el atacante conoce empresa y usuario? | Obtiene un 202 idéntico; no hay token ni canal que interceptar |
| ¿Y si no hay canal de entrega? | Es el estado actual: la solicitud falla cerrada y la recuperación la hace el soporte con la orden local |
| ¿Qué hace el soporte? | Verifica la identidad por un canal de confianza, ejecuta `password_breakglass`, entrega el código y borra el fichero (runbook en `backup-restore-plan.md` §7) |

## 3. Paridad DB / API / UI

- **La UI no anuncia un éxito que no ocurrió:** el paso «hecho» solo aparece con el 200 (vitest 5, E2E 02).
- **La API no expone lo que la UI oculta:** no hay token en ninguna respuesta ni en el esquema OpenAPI (OAS01).
- **La BD no permite lo que la API supone imposible:** `token_hash` único; UPDATE condicional (`used_at` e `invalidated_at` nulos); probado con concurrencia en PostgreSQL (B06).
- **No hay acción de UI que el backend autorice de más:** no existe flujo administrativo web, y la emisión es solo local.

DB_API_UI_CONTRACT_PARITY = PASS · SCREEN_FORM_COMPLETENESS_GATE = PASS · PROCESS_COMPLETENESS = PASS · FIELD_COMPLETENESS = PASS ·
UNEXPLAINED_UI_FUNCTIONAL_GAPS = 0.
