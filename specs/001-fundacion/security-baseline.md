# LÍNEA BASE DE SEGURIDAD — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | Arquitecto de seguridad |
| Ruta | `specs/001-fundacion/security-baseline.md` |

## 1. Identidad y autenticación

- Contraseñas con Argon2id y política de complejidad.
- MFA preparado (habilitable); obligatorio para propietario y perfiles críticos.
- Recuperación con token de un solo uso, expiración y revocación.
- Bloqueo por fuerza bruta y rate limiting.
- Cookies HttpOnly/Secure/SameSite para refresh; access token corto en memoria; CSRF (ADR-004).
- Rotación de refresh token y revocación de sesiones; cierre en todas las pestañas.

## 2. Autorización

- RBAC + alcance + condiciones; deny by default.
- Permisos por acción (no solo CRUD): ver, crear, editar, aprobar, rechazar, activar, desactivar, eliminar, anular, reversar, imprimir, reimprimir, exportar, cerrar, reabrir, configurar, auditar.
- Backend como autoridad; el frontend no deduce integridad referencial.
- Segregación de funciones (SoD) y roles protegidos.

## 3. Protección de datos

- TLS en tránsito; cifrado en reposo; secretos fuera del código.
- Backups cifrados; retención documental.
- Minimización; permisos por campo; exportaciones auditadas.

## 4. Seguridad de aplicación

- OWASP ASVS; validación de entrada; XSS; SSRF; inyección; file upload (MIME real, tamaño, hash); rate limits.
- Headers: CSP, HSTS, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
- CORS restrictivo.
- No retornar excepciones SQL, stack traces, rutas internas ni secretos (contrato de errores).

## 5. Seguridad de API

- Scopes, expiración, idempotencia, límites, auditoría.
- Contrato de errores uniforme; request ID.

## 6. Seguridad de base de datos

- Usuario PostgreSQL restringido (no superusuario en la app).
- RLS/controles; pgaudit a evaluar; bloqueo de DDL productivo.
- Migraciones revisadas con respaldo y rollback.

## 7. Seguridad de documentos

- Antivirus opcional; MIME real; hash; URLs firmadas; expiración; autorización por objeto.

## 8. Administración privilegiada

- Acceso privilegiado temporal, justificado, aprobado y registrado.

## 9. Gestión de secretos e infraestructura

- Secretos fuera del repositorio (`.env.example` solo con nombres).
- SBOM; escaneo de imágenes Docker; escaneo de secretos en CI; gestión de CVE.
- Imágenes versionadas y no root.

## 10. Licenciamiento

- Clave privada del propietario jamás en la instalación, imágenes, Git o variables distribuidas.
- Detección de clonación y manipulación → SECURITY_SUSPENSION.
- Fecha confiable persistente; el navegador no decide.

## 11. Incidentes

- Detección, triage, contención, evidencia, notificación, recuperación y postmortem.

## 12. Estado

| Elemento | Estado |
|---|---|
| Línea base de seguridad | ✔ |
| Aprobación | Pendiente |
