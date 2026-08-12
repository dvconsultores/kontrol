# Matriz de Integraciones Externas — Spec 012 (pasada 2)

> Regla (§29): no se declara una integración "funcionando" por la existencia de un cliente API; debe existir prueba y efecto verificado.

| Integración | Módulo | Configurada | Consumidor | Timeout/Retry | Idempotencia | Logs | Test | Estado |
|---|---|---|---|---|---|---|---|---|
| BCV (tasas oficiales) | Tesorería | — | — | — | — | — | — | **NO CONFIGURADA / no localizada** (sin cliente en backend) |
| Correo (SMTP) | Identity (password reset) | Parcial (requiere SMTP env) | `POST /auth/password-reset/request` | — | — | — | No E2E de envío | PARCIAL (sin prueba de envío real) |
| Licenciamiento central | Licensing (010) | Sí (`license_central_config`) | `sync_license` (cliente inyectable) | — | Sí (idempotencia por día) | Sí | test_licensing_central | PARCIAL (contrato v1; sync real no probado en red) |
| Storage (archivos) | Fiscal/Regulatorio | Parcial (KONTROL_STORAGE_PATH) | file_id/attachment | — | — | — | No E2E de subida/descarga | PARCIAL |
| SICA / SIGESAI / SACS | Regulatorio (008) | — | — | — | — | — | — | **NO INTEGRADA** (solo registro/validación de documentos; P20 no sustituye organismos) |
| Bancos | Tesorería | — | — | — | — | — | — | NO INTEGRADA (sin API bancaria) |
| Webhooks | — | — | — | — | — | — | — | NO EXISTE |
| SENIAT (facturación/control) | Fiscal (007) | — | — | — | — | — | — | NO INTEGRADA (solo emisión interna con correlativos/control propios) |
| Reportes PDF/CSV | Reportes (009) | Parcial | `POST /reporting/exports` | — | — | — | **Falla: no genera archivo (KAUD-002)** | **ROTA** |
| Workers/jobs | Reportes (009) | Parcial | `POST /reporting/jobs` | — | — | — | UI simula lista (KAUD-003) | PARCIAL/ROTA |

## Conclusiones

- **No hay integraciones externas obligatorias probadas** en esta pasada (BCV, SENIAT, SICA/SIGESAI/SACS, bancos, correo) — todas están en estado NO CONFIGURADA / PARCIAL / pendiente de convenio oficial (P20 de la Constitución).
- La única "integración" con consumidor activo — **exportación de reportes** — está **rota funcionalmente** (KAUD-002): se registra metadata pero no se genera el archivo.
- El **licenciamiento central** tiene contrato v1 e idempotencia por día, pero la sincronización real (red) no se probó en esta pasada.

**Recomendación:** para cada fila NO CONFIGURADA, decidir explícitamente FUTURE_SCOPE (si la Spec o el roadmap lo difieren) o convertirla en requisito con prueba. No declarar integraciones funcionando sin evidencia.
