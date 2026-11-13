# Plan · REP-03

## Constitution gate

```text
REQUIREMENT_COMPLETE=6/7 dimensiones de IR §12 con datos reales; monto declarado NO_DISPONIBLE (OBS-PROC08-MONTO-01, OPEN, no se absorbe)
NORMATIVE_AUTHORITY=IR §12 + procesos fuente PROC-03/06/07/08 ya certificados
DOMAIN_DEPENDENCIES=existentes; ninguna ausente salvo el monto
SECURITY=capacidad existente gobierno_expedientes:view; aislamiento tenant/empresa
DATA_INTEGRITY=solo lectura; sin tablas ni migración
ARCHITECTURE=servicio de reporte en government, etiquetas reutilizadas de service_expedientes
TESTABILITY=PG con datos sembrados por ORM real; E2E por menú
MATERIAL_DECISION_REQUIRED=0
CONSTITUTION_GATE=PASS
```

## Decisiones

| Id | Decisión | Fundamento |
|---|---|---|
| PDD-REP03-01 | Solo lectura, sin migración | IR §12 pide un reporte; evita colisión de Alembic |
| PDD-REP03-02 | Período por `GovernmentProcurementFile.fecha_inicio` (fecha civil); por defecto del 1 de enero a hoy (`hoy_de_negocio`); 422 `INVALID_DATE_RANGE` | Mismo contrato que REP-10 y CTL-02 |
| PDD-REP03-03 | Solo cuenta la decisión con `estado == "VIGENTE"` del expediente (la última vigente) | Una ANULADA o SUSTITUIDA no es la decisión actual (PROC-08) |
| PDD-REP03-04 | Proveedor = (`oferente_documento`, `oferente_nombre`) de `GovernmentProcurementOffer`; adjudicación = decisión VIGENTE ADJUDICADA con `offer_id` | PROC-06 y PROC-08 |
| PDD-REP03-05 | Tiempos en días naturales entre fechas de negocio. Recepción y evaluación son `datetime` → fecha de negocio con `fecha_de_negocio_de_instante` (o su equivalente en `app.shared.clock`) | ADR-020 |
| PDD-REP03-06 | Desviación de hito: CUMPLIDO con `fecha_real > fecha_prevista` = atraso; PREVISTO con `fecha_prevista < hoy` = vencido; NO_APLICA excluido | Datos de PROC-03 |
| PDD-REP03-07 | Monto declarado no disponible, sin estimarlo | No inventar montos (norma del encargo) |
| PDD-REP03-08 | CSV completo auditado `GOV_PROCUREMENT_REPORT_EXPORTED` (entidad `GovernmentProcurementFile`, `gov-rep-03`) | Patrón de REP-10 y CTL-06 |

## Backend

- `app/modules/government/service_reporte_contrataciones.py`:
  - `reporte(db, ctx, *, desde, hasta) -> dict`;
  - `exportar_csv(db, ctx, *, desde, hasta) -> (nombre, bytes)`.
- `app/modules/government/api_reporte_contrataciones.py`:
  - router `prefix="/gobierno/contrataciones/reporte"`;
  - `GET ""` (JSON) y `GET ".csv"`;
  - `require_permission("gobierno_expedientes", "view")` y `require_module("gobierno")`.
- `main.py`: include del router. Catálogo de auditoría +1 (487 → 488).

## Frontend

- `src/modules/gobierno/contrataciones/ReporteContratacionesPage.tsx` y su Vitest.
- Ruta `gobierno/contrataciones/reporte`, pantallas.ts y entrada en el Sidebar.
- Humo UAT: la pantalla, más la línea de PROC-11 (`/gobierno/sod/funciones`, «Funciones incompatibles»), que faltaba (§5).

## E2E

`e2e/gobierno-reporte-contrataciones.spec.ts`:
- expediente real creado por API como en las E2E de PROC-03;
- el reporte por el menú, el CSV, la negativa de período, el aislamiento y 1280, 390 y 320 px con Axe.
