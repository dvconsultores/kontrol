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

| Elemento | Método |
|---|---|
| Base de datos | Full + incrementales/WAL, cifrados, retenidos y separados |
| Documentos/archivos | Replicación/versionado y verificación de hash |
| Configuración | Archivo de configuración versionado por ambiente |
| Identidad de instalación | Volumen `kontrol-license-state` (identidad, claves locales, licencia) |
| Licencia firmada | Volumen persistente + copia cifrada |
| Anillo `KONTROL_MFA_KEYS` | No viaja en la copia: se custodia aparte; sin él ningún factor TOTP se puede descifrar y los usuarios afectados deben volver a darse de alta |

## 3. Frecuencia

- Backup diario automático.
- Backup previo a migración.
- Backup previo a actualización.
- Verificación de restauración mensual automatizada; ejercicio integral trimestral.

## 4. Restauración (mismo servidor)

1. Restaurar volúmenes.
2. Arrancar en modo mantenimiento.
3. Validar identidad, licencia y última fecha confiable.
4. Sincronizar o importar paquete actual.
5. Ejecutar migraciones autorizadas.
6. Abrir operación según modo real (DOC-07 §16.2).

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

## 8. Estado

| Elemento | Estado |
|---|---|
| Plan de backup/restore | ✔ |
| Runbooks | ✔ (listado) |
| Ejecución | Pendiente (T-042) |
