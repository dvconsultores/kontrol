# T052 · registro de intentos

| Intento | Modelo | Coste | Resultado | Motivo |
|---|---|---|---|---|
| T052-A1, inicial | deepseek-v4-pro | $0,005225 | Producción: AUDIT_PASS. Pruebas: AUDIT_REJECT | Import erróneo de `EXIT_BUNDLE_INVALID`, código muerto y sin prueba real de `audit_backup_event` |
| T052-A1, reintento 1 | deepseek-v4-pro | $0,003236 | AUDIT_REJECT | `backup_cli.main.audit_backup_event` no existe |
| T052-A1, reintento 2 | deepseek-v4-pro | $0,003099 | AUDIT_REJECT | Firma inventada, `KONTROL_SKIP_AUDIT` inventada, campos de `AuditEvent` inexistentes |

`T052-A1` queda **BLOCKED**: reintentos semánticos agotados (2 de 2). Nada aplicado: el bloque de producción aprobado no se aplica sin su prueba dirigida. Claude no escribió el parche.

Causa del último fallo: el brief del reintento 2 resumía el intento anterior y omitía la firma de la función, así que el ejecutor, sin memoria, la inventó. Requiere rediagnóstico del brief; renombrar la tarea no reinicia el contador.
