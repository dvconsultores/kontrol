# EXTERNAL_RECOVERY_SECRET_INVENTORY (06)

Nunca se registran valores.

| Clase | PURPOSE | REQUIRED_AFTER_RESTORE | REGENERABLE | MUST_MATCH_ORIGINAL | ROTATABLE | QA_TEST_METHOD | DOCUMENTED_CUSTODY_REQUIREMENT |
|---|---|---|---|---|---|---|---|
| `KONTROL_BACKUP_KEY` | Cifrado y autenticación del paquete | Sí, para restaurar | No para una copia existente | **Sí** | Sí (copias nuevas) | Efímera por corrida; clave errónea → rc 3 | Custodia aparte de la copia y del servidor |
| `KONTROL_MFA_KEYS` | Cifrar el secreto TOTP | Sí | No sin realta de usuarios | **Sí** (los `kid` en uso) | Sí, con `mfa_rekey` | Anillo sintético; anillo erróneo → rc 7; TOTP válido tras restaurar | Aparte de la base y de sus copias (`instalar.md`) |
| Clave privada de la instalación | Firmar solicitudes y sincronización con la central | Sí | No (si no, se reemplaza la instalación, plan §5) | **Sí** (= `public_key`) | Solo por reemplazo | Clave sintética reprovisionada; errónea → rc 7 | Custodia aparte; no viaja en la copia |
| `KONTROL_SECRET_KEY` | Firma JWT | Sí, para arrancar | **Sí** | No (se recomienda rotarla) | Sí | Clave nueva en el destino; las sesiones anteriores se revocan | Aparte |
| `KONTROL_LICENSE_TRUST_KEYS` / PEM público | Ancla de confianza de licencias (pública) | Sí | No es secreta | Sí (o el conjunto vigente) | Según 010 | La misma ancla sintética | Configuración versionada |
| Credenciales de PostgreSQL (`KONTROL_DB_URL`) | Acceso a la base de destino | Sí | Sí | No | Sí | Usuario de QA por entorno, nunca en un argumento ni en la evidencia | Aparte |
| Credenciales externas (central, ClamAV) | Integraciones | Según uso | Sí | No | Sí | No aplica en QA (sin central) | Aparte |

**EXTERNAL_RECOVERY_SECRET_INVENTORY_COMPLETE = 1.**
