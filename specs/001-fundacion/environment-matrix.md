# MATRIZ DE ENTORNOS — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | Arquitecto de infraestructura |
| Ruta | `specs/001-fundacion/environment-matrix.md` |

## Ambientes

| Ambiente | Propósito | Datos | Migraciones | Secreto | Observabilidad | Fuente DOC |
|---|---|---|---|---|---|---|
| Local | Desarrollo con hot reload, correo falso, secretos locales | Sintéticos | Automáticas controladas | Locales | Logs | DOC-05 §8 |
| Development | Integración continua | Prueba | Automáticas controladas | CI secrets | Logs + métricas | DOC-05 §8 |
| QA | Suites E2E/seguridad/rendimiento | Prueba | Revisadas | CI secrets | Completa mínima | DOC-05 §8 |
| UAT | Usuarios de negocio | Anonimizados/sintéticos | Revisadas | Gestión | Completa | DOC-05 §8 |
| Staging fiscal | Versión fiscal, impresión, control, regresión | Sintéticos | Revisadas + evidencia | Gestión | Completa | DOC-05 §8 |
| Producción | Alta disponibilidad según SLA | Productivos | Ventana + backup + rollback | Secret manager | Completa mínima + alertas | DOC-05 §8 |
| DR | Recuperable, runbooks | Replica | — | — | — | DOC-05 §8 |

## Variables de entorno (prefijo `KONTROL_`)

| Variable | Descripción | Obligatoria | Sensible |
|---|---|---|---|
| `KONTROL_ENV` | Ambiente (local/dev/qa/uat/staging/prod) | Sí | No |
| `KONTROL_DB_URL` | Conexión PostgreSQL (usuario restringido) | Sí | Sí |
| `KONTROL_SECRET_KEY` | Clave para firma de tokens/sesiones | Sí | Sí |
| `KONTROL_MFA_KEYS` | Anillo de claves AES-256-GCM para cifrar secretos TOTP | Sí en `prod` | Sí |
| `KONTROL_COOKIE_SECURE` | Flag Secure para cookies | Sí | No |
| `KONTROL_CORS_ORIGINS` | Orígenes permitidos | Sí | No |
| `KONTROL_LICENSE_PUBLIC_KEY_KID` | kid de clave pública de licencia | Sí | No |
| `KONTROL_INSTALLATION_VOLUME` | Ruta del volumen de identidad | Sí | No |
| `KONTROL_STORAGE_PATH` | Ruta de almacenamiento documental | Sí | No |
| `KONTROL_BACKUP_PATH` | Ruta de respaldos | Sí | No |
| `KONTROL_LOG_LEVEL` | Nivel de log | No | No |

> Las variables sensibles se validan al inicio y el servicio falla de forma segura si faltan (FR-001-005). Nunca se versionan valores reales (solo `.env.example`).

## Estado

| Elemento | Estado |
|---|---|
| Matriz de entornos | ✔ |
| Variables definidas | ✔ |
| Aprobación | Pendiente |
