# Spec Kit — KONTROL

## Flujo obligatorio

```
Ask for change
    │
    ▼
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.checklist
/speckit.tasks
/speckit.analyze
    │
    ▼  AUTORIZACIÓN EXPRESA
/speckit.implement
/speckit.converge
```

## Comandos y artefactos

| Comando | Artefacto(s) |
|---|---|
| `/speckit.specify` | `spec.md` (alcance, historias, requisitos, casos límite, criterios) |
| `/speckit.clarify` | `clarifications.md` (preguntas, decisiones, supuestos) |
| `/speckit.plan` | `plan.md`, `data-model.md` |
| `/speckit.checklist` | `checklist.md` |
| `/speckit.tasks` | `tasks.md` (atómicas, con dependencias y pruebas) |
| `/speckit.analyze` | `analysis-report.md` (consistencia, bloqueos) |
| `/speckit.implement` | Código (requiere autorización expresa que mencione la iniciativa) |
| `/speckit.converge` | `convergence.md` (brechas y trabajo residual) |

## Reglas

- No se implementa sin Spec aprobada, análisis consistente y **autorización
  expresa** que mencione el código de la iniciativa (Constitución P1/P2).
- Los artefactos se crean físicamente en `specs/<iniciativa>/`.
- La autorización genérica ("autorizo todo", "adelante") no es válida.

## Iniciativas

| Código | Alcance |
|---|---|
| 001-fundacion | Fundación: organización, seguridad, licencia local, auditoría, frontend base, Docker |
| 002-maestros | Terceros, productos, servicios, rubros, unidades, perfiles (roadmap) |
| 003-inventario-logistica | Movimientos, lotes, seriales, reservas, costos (roadmap) |
| 004-compras-cuentas-por-pagar | Requisición → orden → recepción → factura → CxP (roadmap) |
| 005-ventas-cuentas-por-cobrar | Cotización → pedido → despacho → factura → CxC (roadmap) |
| 006-tesoreria | Caja, bancos, cobros, pagos, conciliación (roadmap) |
| 007-nucleo-fiscal | IVA, retenciones, ISLR, IGTF, documentos, controles, libros (roadmap) |
| 008-regulacion-traslados | SICA, SIGESAI, SACS, permisos y bloqueo (roadmap) |
| 009-reportes-auditoria | Indicadores, reportes, exportaciones (roadmap) |
| 010-licenciamiento-central | Portal central del propietario (roadmap) |
| 011-homologacion-liberacion | Homologación SENIAT y liberación (roadmap) |
