# Trazabilidad · CNT-09

| Contrato | FR | Código | Prueba |
|---|---|---|---|
| C09-01 vencimiento del contrato efectivo | FR-01 | `condiciones` → `terminos_efectivos(db, contrato, hoy)["fecha_fin"]`; solo FORMALIZADO y sin CIERRE | PG prórroga_cnt02 |
| C09-02 garantía | FR-02 | `fase_garantia` (solo REGISTRADA) → `service_garantias._vigencia` | PG garantia_por_vencer_y_renovada; unitaria |
| C09-03 hito | FR-03 | VIGENTE y no en `_cumplidos` | PG hito_y_entregable…; E2E paso CNT-09 |
| C09-04 entregable | FR-04 | VIGENTE y sin `_conforme`; entregar sin conformar no cumple | PG hito_y_entregable…; E2E |
| C09-05 solo fechas autoritativas | FR-01..05 | `fase(fecha, hoy, dias)`; sin fecha, sin alerta; firma en días hábiles DEFERRED_BY_CALENDAR_AUTHORITY | PG unitaria fase |
| C09-06 no sustituye a la autoridad | Principio | Ningún servicio de CNT-09 escribe en tablas de negocio | PG «sin efectos» (foto idéntica) |
| C09-07 idempotencia | FR-07 | `clave()`, `:r<n>`; `crear_alerta` con `uq_alerts_company_dedupe` | PG doble _rec; tick doble |
| C09-08 resolución de alertas caducadas | FR-08 | `reconciliar` → `resolver_alerta_de_sistema` (no borra) | PG entregable conforme, hito recibido y garantía renovada; E2E pasos 6 y 9 |
| C09-09 cambio de fecha por CNT-02 | FR-01/08 | Clave con la fecha efectiva; la anterior queda RESUELTA | PG prórroga_cnt02 |
| C09-10 regla de 15 días de PROC-10 | FR-02 | `_vigencia` + `DIAS_POR_VENCER` (monkeypatch 3 → cambia el umbral) | PG unitaria |
| C09-11 planificador | FR-09 | `registry.py`: `gov_contract_deadline_alerts` (CNT09, OWNER_IDEMPOTENT) | PG tick doble; test_spec047_scheduler |
| C09-12 reutiliza el motor 047 | FR-10/14 | `crear_alerta`, `Alert`, `catalogo.ORIGENES`, `/alerts`; sin tablas de alertas nuevas | revisión; PG bandeja |
| C09-13 aislamiento por empresa | FR-16 | `company_id` en todas las consultas; 404 para otra empresa | PG contexto_aislamiento |
| C09-14 permisos | FR-11/12 | `gobierno_contratos:view`, `notificaciones:configure` (PUT), `alertas:view`; ORIGENES ocultan sin el permiso de origen | PG política 403; bandeja sin gobierno_contratos |
| C09-15 vista contextual del contrato | FR-11 | `GET /gobierno/contratos/{id}/alertas`; `AlertasContrato` | PG; Vitest; E2E «Alertas activas: 2» |
| C09-16 bandeja global | FR-14 | `/alertas` con filtros de severidad y origen | Vitest; E2E |
| C09-17 auditoría | FR-12/17 | ALERT_CREATED (047), `resolved_at` y GOV_CONTRACT_ALERT_POLICY_UPDATED | PG eventos |
| C09-18 concurrencia | FR-16 | Inserción única por clave; `carrera` | PG reconciliacion_concurrente |
| C09-19 sin efectos de negocio | FR-15 | — | PG foto (versión del contrato, estados, compromisos); E2E ejecución antes = después |
| C09-20 E2E / UAT | FR-17 | gobierno-contratos (tramo CNT-09), 1280/390/320 y Axe | E2E 2/2; humo UAT |
