# Plan · REP-10

## Constitution gate

```text
CONSTITUTION_GATE=PASS
LEGAL_SOURCE_STATUS=IR §12 (requisito de producto) + fuentes de los procesos consolidados (CTL-01, ORG-06, CTL-10, CTL-06)
LOCAL_RULE_UNIVERSALIZED=0
MATERIAL_DECISION_REQUIRED=0
MIGRATION=0 (solo lectura)
NEW_CAPABILITY=0 (gobierno_auditoria:view + gobierno_hallazgos:view existentes)
```

## Backend

- `app/modules/government/service_reporte_control.py` (nuevo): `reporte(db, ctx, *, desde, hasta, ver_hallazgos) -> dict`
  y `exportar_csv(db, ctx, *, desde, hasta, ver_hallazgos) -> tuple[str, bytes]`. Lee `AuditEvent` con
  `tenant_id == ctx.tenant_id`, `company_id == ctx.company_id`, `action` en las tres acciones y `event_time` en el
  período (`limites_del_dia_utc`). Hallazgos y acciones por `tenant_id`/`company_id`.
- `app/modules/government/api_reporte_control.py` (nuevo): router `prefix="/gobierno/control-interno"`,
  `GET /reporte` (JSON) y `GET /reporte.csv` (StreamingResponse, `db.commit()` tras auditar). Ambos con
  `require_module("gobierno")` y `require_permission("gobierno_auditoria", "view")`; `ver_hallazgos` se calcula con
  `identity_service.get_user_permissions(db, user)` + `user_has_permission(user, permisos, "gobierno_hallazgos", "view")`.
- `app/main.py`: incluir el router.
- `app/shared/audit_catalog_entries.py`: `GOV_INTERNAL_CONTROL_REPORT_EXPORTED` (entidad `GovernmentEntity`,
  `gov-rep-10`, COMPANY, SECURITY, BUSINESS_COMMIT, ("filas", "filtros")). Catálogo 485 → 486.

### Respuesta JSON

```text
{ periodo:{desde,hasta}, generado_en,
  conflictos_sod:{ total, por_regla:[{regla_codigo, regla_nombre, proceso, proceso_etiqueta, total}],
                   eventos:[{evento_id, fecha, usuario, regla_codigo, regla_nombre, proceso_etiqueta,
                             accion_etiqueta, accion_previa_etiqueta}] },
  bloqueos_identidad:{ total, por_motivo:[{codigo, etiqueta, total}], eventos:[{evento_id, fecha, usuario, etiqueta}] },
  bloqueos_cierre:{ total, por_politica:[{politica_codigo, accion_etiqueta, total}],
                    eventos:[{evento_id, fecha, usuario, politica_codigo, accion_etiqueta, objeto_codigo,
                              controles:[{etiqueta, pendientes}]}] },
  hallazgos:{ disponible, motivo|null, por_estado:{ESTADO:n}, por_riesgo:{RIESGO:n},
              acciones_por_estado:{ESTADO:n},
              acciones_vencidas:[{hallazgo_id, hallazgo_codigo, hallazgo_titulo, accion_orden, descripcion,
                                  cargo, unidad, fecha_objetivo, porcentaje, dias_atraso}] },
  overrides:{ disponible:false, motivo }, operaciones_duplicadas:{ disponible:false, motivo } }
```

Etiquetas de estado y riesgo traducidas en el frontend (Abierto, Plan de acción, En remediación, Evidencia presentada,
Cerrado; Alto, Medio, Bajo; Pendiente, En curso, Completada).

## Frontend

- `src/modules/gobierno/control/ReporteControlInternoPage.tsx` + `reporteControlApi.ts` + prueba Vitest.
- Ruta `gobierno/control-interno`, pantallas.ts `gobierno_auditoria:view`, Sidebar «Reporte de control interno» tras
  «Separación técnica y funcional», HUMO-UAT con la pantalla.
- Secciones con h2, tablas con caption, totales en tarjetas, enlaces a bitácora y hallazgo, botón «Exportar CSV»
  (descarga con `descargarArchivo`), filtros con DateInput y botón «Aplicar»; sin JSON crudo ni UUID visibles.

## Pruebas

- `tests/test_gov_rep10_control_interno.py` (PG): eventos sembrados con `record_audit` y acción correctiva con
  `sembrar(db, "GovernmentCorrectiveAction", empresa, sufijo)`; AC-01..AC-05, 403 y 422.
- E2E `e2e/gobierno-control-interno.spec.ts`: provoca un conflicto SoD real por la UI/API, comprueba el reporte, la
  exportación, el aislamiento, Axe y 1280/390/320.
