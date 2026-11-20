# Auditoría de hardcode · CTL-02-AUDIT-PROCESS-RESOLUTION

**Búsqueda (§37):** `PROCESOS`, `process_id`, `process_name`, `GOV_AUDIT`, tuplas `("BUD-|CNT-|CTL-|PROC-|REP-|TRE-…", "Nombre"` y `proceso_etiqueta=` en `resources/backend/app`; `ETIQUETAS_PROCESO` y `PROCESOS_` en `resources/frontend/src`.

| Hallazgo | Clasificación | Estado |
|---|---|---|
| `service_auditoria.PROCESOS` (19 procesos) | Catálogo parcial de auditoría | **Eliminado.** Lo sustituye `procesos.py` |
| `app/modules/government/procesos.py` (39 procesos y 8 módulos) | Autoridad única. Completa por guardia: `test_ctl02_p05_*` y `test_ctl02_p06_*` | Vigente (AUDIT_PROCESS_AUTHORITIES=1) |
| `service_sod_eventos.PRODUCTORES[*].proceso_etiqueta` | Respaldo del adaptador SoD; con la autoridad completa no se usa. `test_ctl02_p07_*` exige que coincida con la autoridad | Conservado, protegido |
| `models.PROCESOS_SOD`, `service_sod.CATALOGO_SOD` | Catálogo del dominio SoD (CTL-01): procesos sujetos a reglas, con restricción en la base | Legítimo, de otro dominio (OBS-SOD-PROCESS-LABELS) |
| Frontend `ETIQUETAS_PROCESO_SOD` | Etiquetas del mismo dominio SoD | Legítimo, de otro dominio (OBS-SOD-PROCESS-LABELS) |
| Otras listas de procesos en el frontend de la bitácora o de la auditoría | — | Ninguna: ambas pantallas leen el catálogo del backend |
| Nombres de entes o regiones concretas en la autoridad | — | Ninguno |

**Resultado:** PARTIAL_PROCESS_CATALOGS=0 · AUDIT_PROCESS_AUTHORITIES=1 · ZERO_INSTITUTIONAL_HARDCODE=1 · NATIONAL_REUSABLE_PRODUCT=1.
