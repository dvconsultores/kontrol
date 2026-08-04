# CLARIFICACIONES — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Iniciativa | 009-reportes-auditoria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/009-reportes-auditoria/clarifications.md` |

## 1. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-009-01 | Alcance | ¿009 reimplementa módulos? | **No.** 009 **consume** datos de 003-008 en lectura (reportes como queries/vistas, no tablas) | Arquitecto | Resuelto |
| CL-009-02 | Exportación | ¿Cómo se audita? | **Exportación auditada**: cada exportación genera un evento (quién, cuándo, qué, filtros) — P5 | Auditoría | Resuelto |
| CL-009-03 | Reportes fiscales | ¿De dónde salen? | Reutilizan los **libros de 007** (ventas/compras/retenciones/IGTF) | Fiscal | Resuelto |
| CL-009-04 | Dashboard | ¿Fuente? | Endpoints **agregados** de 009 sobre los datos de 003-008 | Arquitecto | Resuelto |
| CL-009-05 | Dependencias | ¿Se implementa sin 003-008? | Requiere **001 certificada** y **003-008 implementados**; fase documental sin requisitos | Producto | Resuelto |
| CL-009-06 | Trabajos asíncronos | ¿Cola externa? | En esta fase **sin cola externa**: jobs en BD con estado/error (Polling) | Arquitecto | Resuelto |
| CL-009-07 | Auditoría | ¿Nuevo modelo? | Reutiliza **`AuditEvent` de 001**; 009 agrega timeline y exportaciones | Arquitecto | Resuelto |
| CL-009-08 | Reconstrucción | ¿Tablas editables? | No: saldos/libros/estados se **reconstruyen** desde eventos (DOC-01 §1) | Contador | Resuelto |
| CL-009-09 | Privacidad | ¿Qué se aplica? | Minimización, **permisos por campo** y retención configurable | Producto | Resuelto |
| CL-009-10 | Formatos de exportación | ¿CSV/PDF? | CSV y PDF (plantillas básicas); HTML imprimible | Producto | Resuelto |

## 2. Supuestos declarados

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-009-01 | Los reportes se sirven bajo demanda con filtros; no se materializan salvo caché | Rendimiento en datos grandes | Paginación + jobs asíncronos (FR-009-023) |
| SU-009-02 | El `AuditEvent` de 001 ya registra cambios/impresiones/exportaciones | Cobertura parcial | 009 agrega eventos de exportación propios |
| SU-009-03 | Los indicadores del dashboard son agregados recientes (no histórico total) | Costo de consulta | Índices por empresa/fecha |
| SU-009-04 | La contabilidad formal no está en alcance | Expectativa de balance | Documentar como fuera de alcance |
| SU-009-05 | 009 no modifica datos de 003-008 (solo lectura) | Mutación accidental | Endpoints de solo lectura + permisos |

## 3. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-009-11 | Plantillas PDF definitivas y marca | Exportación PDF | No la fase documental |
| CL-009-12 | Política de retención de exportaciones por empresa | Retención | No la fase documental |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |
