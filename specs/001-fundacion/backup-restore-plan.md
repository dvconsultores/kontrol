# PLAN DE BACKUP Y RESTAURACIÓN — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | Especialista en respaldo y restauración |
| Ruta | `specs/001-fundacion/backup-restore-plan.md` |

## 1. Objetivos

- RPO objetivo inicial ≤15 minutos para datos transaccionales.
- RTO objetivo inicial ≤4 horas; funciones fiscales críticas requieren plan específico (DOC-05 §11).
- No declarar que existe backup solo por ejecutar `pg_dump`; debe verificarse la restauración.

## 2. Contenido del backup

El paquete `.kbk` incluye, cifrado y autenticado:

| Elemento | Contenido |
|---|---|
| Base de datos | Volcado `pg_dump` de la instantánea |
| Documentos y exportaciones | Objetos referenciados por la instantánea |
| Manifiesto | Identidad de la instalación, revisión de Alembic, huellas por tabla, hashes de cada objeto, estado de licencia, recuento de auditoría |

Se custodian aparte y se reprovisionan al restaurar:

| Secreto | Motivo |
|---|---|
| `KONTROL_BACKUP_KEY` | Sin ella la copia es irrecuperable; no viaja en la copia |
| Anillo `KONTROL_MFA_KEYS` | Debe ser el mismo anillo, o los factores TOTP no se pueden descifrar |
| Clave privada de la instalación | Debe ser la del mismo par que la clave pública guardada |
| `KONTROL_SECRET_KEY` | Se genera nueva en el destino: invalida los tokens anteriores |
| Ancla de confianza de la licencia | Se reprovisiona para reverificar la licencia |
| Credenciales de la base destino | Se aportan en el destino |

## 3. Frecuencia

- Copia bajo demanda.
- Copia previa a migración.
- Copia previa a actualización.
- La planificación automática, la verificación periódica automatizada y el ejercicio integral trimestral son procedimientos a programar por el operador; no los ejecuta el producto.
- Deuda `BACKUP-SCHEDULE-RPO`: sin planificación automática ni WAL/PITR, el objetivo de RPO ≤15 min no se cumple; para cumplirlo hay que planificar copias con intervalo ≤15 min o implementar archivado continuo.

## 4. Restauración verificada (mismo servidor o servidor nuevo de la misma instalación)

1. Verificar el paquete sin tocar ningún destino.
2. Preparar destino vacío: base sin relaciones en `public`, raíz de almacén inexistente o vacía y volúmenes vacíos.
3. Reprovisionar los secretos externos: `KONTROL_BACKUP_KEY`, anillo `KONTROL_MFA_KEYS`, clave privada de la instalación, ancla de confianza de la licencia y credenciales de la base destino.
4. Restaurar con la misma instalación (`--expected-installation-id`) y revisión de Alembic conocida y cabeza.
5. Arrancar el backend; la licencia se reverifica.
6. Comprobar inicio de sesión, empresa y un documento.

| Código | Qué significa | Qué hace el operador |
|---|---|---|
| 0 | Correcto | Continúa con la comprobación |
| 1 | Error operativo | Revisa la causa y reintenta |
| 2 | Paquete inválido o corrupto | Usa otra copia |
| 3 | Clave errónea | Corrige `KONTROL_BACKUP_KEY` |
| 4 | Copia de otra instalación | Confirma `--expected-installation-id` |
| 5 | Destino no vacío | Vacía o crea un destino nuevo |
| 6 | Alembic incompatible o copia requiere actualización | Aplica la revisión autorizada |
| 7 | Secreto externo ausente o erróneo | Reprovisiona el secreto indicado |
| 8 | Restauración fallida y destino limpiado | Revisa la causa y reintenta |
| 9 | Copia inconsistente | Usa otra copia |

## 5. Migración a servidor nuevo

1. El administrador solicita traslado de instalación.
2. El nuevo servidor genera nueva identidad o solicitud de reemplazo.
3. El propietario aprueba la sustitución.
4. La instalación anterior pasa a REPLACED o REVOKED.
5. Se emite licencia para la nueva identidad.
6. Se restauran datos y se valida consistencia.
7. Se registra la fecha de corte para impedir operación simultánea no autorizada (DOC-07 §16.3).

## 6. Reglas de integridad

- Una restauración de backup antiguo debe activar reconciliación y no retroceder el vencimiento de licencia.
- Backup cifrado según política del cliente.
- Backup externo al servidor cuando sea posible.
- Verificación de hash de archivos restaurados.
- La restauración nunca sobrescribe un destino con datos; para repetirla, se vacía o se crea un destino nuevo.

## 7. Runbooks (DOC-05 §11)

- Caída de base de datos.
- Pérdida de nodo.
- Certificado vencido.
- Cola (futuro).
- Almacenamiento.
- Integración.
- Seguridad (incidente).
- Rotación de la clave MFA:
  1. Generar la clave nueva con `python3 -c "import base64, secrets; print('k2:' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='))"`.
  2. Anteponerla al anillo de `KONTROL_MFA_KEYS`, por ejemplo `k2:…,k1:…`.
  3. Reiniciar el backend.
  4. Ejecutar dentro del backend `python -m app.modules.identity_access.mfa_rekey`; imprime `recifrados=<n>`.
  5. Cuando no queden factores con la clave antigua, retirarla del anillo y reiniciar.
- Rotura de cristal MFA (último administrador sin factor ni códigos): solo en el servidor, nunca por HTTP:
  `python -m app.modules.identity_access.mfa_breakglass --tenant <CODIGO> --username <USUARIO> --confirm <USUARIO>`
  Deja auditoría `MFA_RESET_BREAKGLASS`, revoca todas las sesiones del usuario y le obliga a darse de alta en su siguiente inicio de sesión.
- Rotura de cristal de contraseña (persona que no puede entrar; no hay canal de correo): solo en el servidor, nunca por HTTP:
  `python -m app.modules.identity_access.password_breakglass --tenant <CODIGO> --username <USUARIO> --confirm <USUARIO> --salida <RUTA>`
  Antes de emitirlo, el operador verifica la identidad de la persona por un canal de confianza. La orden escribe un código de un solo uso (caduca a los 15 minutos) solo en `<RUTA>` (permisos 0600; no sobrescribe un fichero existente) y nunca lo imprime. El operador lo entrega por ese canal y borra el fichero; la persona elige su contraseña en `/reset-password` («Tengo un código»). Deja auditoría `PASSWORD_RESET_ADMIN_INITIATED` (fuente CLI); un código nuevo invalida el anterior; el MFA de la persona no cambia.

## 8. Copia y restauración verificadas (ciclo 06)

- Órdenes y envoltorios: `python3 kontrol.py backup [--dest <dir>]`, `python3 kontrol.py backup-verify <paquete>` y `python3 kontrol.py restore <paquete> --expected-installation-id <ID>` ejecutan la orden dentro del contenedor `backend` y pasan `KONTROL_BACKUP_KEY` por nombre, nunca su valor. `scripts/backup.sh` y `scripts/restore.sh` permiten la ejecución directa en el anfitrión.
- Gestión de la clave: 32 bytes en base64url, en `KONTROL_BACKUP_KEY` o en `--key-file <fichero>` con permisos 0600; nunca como argumento. No viaja en la copia; sin ella la copia es irrecuperable.
- Precondiciones y garantías de `restore`: exige paquete íntegro, misma instalación, revisión de Alembic conocida y cabeza, destino vacío y secretos reprovisionados. Nunca sobrescribe ni borra un destino con datos. Si algo falla tras empezar a escribir, deja el destino vacío otra vez. Al terminar revoca las sesiones previas y registra `INSTALLATION_RESTORED` por tenant.
- Certificación real reproducible: `qa/backup_restore_cert.py` (origen sintético → copia en vivo → verificación → borrado de la fuente → restauración en base nueva → arranque en otro proceso → login con MFA, aislamiento de tenant, documento y exportación con su hash, punto de corte, escritura auditada, auditoría inmutable, contrato de entrada, sesión previa rechazada, licencia FULL_ACCESS).
- Medidas en la corrida del 2026-10-28 sobre PostgreSQL de QA: RTO 34,4 s desde el inicio de la restauración hasta el primer inicio de sesión (restauración 1,3 s; el resto, arranque y espera del paso TOTP); copia 0,19 s del conjunto sintético; ventana perdida = tiempo entre la instantánea y el desastre (1,3 s en la prueba).
- RPO/RTO frente a FR-001-083: el RTO objetivo de ≤4 h se cumple con holgura en la medición. El RPO objetivo de ≤15 min no se cumple con copias manuales.
- Deudas abiertas: `BACKUP-PG-TOOLS-IN-OPS-IMAGE` (la imagen `backend` aún no incluye `pg_dump`/`pg_restore`; hasta resolverla, la orden se ejecuta en un anfitrión con los clientes de PostgreSQL) y `BACKUP-SCHEDULE-RPO` (sin planificación automática ni WAL/PITR). No hay retención ni borrado automático de copias.

## 9. Estado

| Elemento | Estado |
|---|---|
| Plan de backup/restore | ✔ |
| Runbooks | ✔ (listado) |
| Ejecución | Pendiente (T-042) |
