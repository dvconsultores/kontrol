# DECISIONES · REP-10 (decisiones de diseño con fundamento documental; ninguna de la dueña pendiente)

| Id | Decisión | Fundamento |
|---|---|---|
| PDD-REP10-01 | Reporte de solo lectura sobre datos ya persistidos; sin tablas nuevas ni migración | IR §12 pide un reporte, no un proceso nuevo; evita colisión de Alembic con P2 |
| PDD-REP10-02 | Período por fecha de negocio (America/Caracas), `desde`/`hasta` inclusivos, por defecto del 1 de enero del año de negocio a hoy; `desde > hasta` → 422 `INVALID_DATE_RANGE` (mismo contrato que CTL-02) | ADR-020; patrón `limites_del_dia_utc` de la bitácora |
| PDD-REP10-03 | Los eventos (conflictos SoD, bloqueos de identidad y de cierre) se filtran por período; hallazgos y acciones se muestran en su estado ACTUAL (instantánea a la fecha de consulta) | Un hallazgo abierto de un período anterior sigue siendo un riesgo vigente |
| PDD-REP10-04 | Capacidad de la pantalla: `gobierno_auditoria:view` (Control Interno, la misma de la bitácora). La sección de hallazgos exige además `gobierno_hallazgos:view`; sin ella la sección se declara «Sin permiso para ver hallazgos». Sin capacidad nueva | Permiso técnico ≠ autoridad: no se amplía lo que cada rol ya ve |
| PDD-REP10-05 | Overrides: categoría declarada «No aplica: en Gobierno los controles de segregación de funciones solo bloquean; no existe excepción ni dispensa (CTL-01)». Operaciones duplicadas: «No disponible: requiere órdenes de pago y pagos (TRE-03, TRE-04), que aún no existen en Gobierno.» | No fingir controles ni sustituir dominios ausentes |
| PDD-REP10-06 | Textos humanos: acciones SoD con `service_sod.etiqueta_de`, cierres con `ACCIONES_CIERRE`/`TIPOS_CONTROL`, identidad con `service_separacion._etiqueta_denegacion`, procesos con `PROCESOS`, usuarios con `_usuarios_por_ids`. Sin UUID ni códigos crudos en pantalla | Norma de pantalla §16 |
| PDD-REP10-07 | Exportación CSV de todas las secciones con el período; se audita como `GOV_INTERNAL_CONTROL_REPORT_EXPORTED` (`filas`, `filtros`) igual que `GOV_FINDINGS_EXPORTED` | CTL-02: toda exportación de información de control se registra |
| PDD-REP10-08 | Listas de eventos limitadas a los 50 más recientes por sección, con el total real; el detalle completo se abre en la bitácora (`/gobierno/bitacora/<evento>`) y el hallazgo en `/gobierno/hallazgos/<id>` | Rendimiento y reutilización de CTL-02/CTL-06 |
| PDD-REP10-09 | Aislamiento: todo filtro por `tenant_id` y `company_id` del contexto | Constitución, aislamiento de tenant |
