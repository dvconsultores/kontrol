# CLARIFICACIONES — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/008-regulacion-traslados/clarifications.md` |

## 1. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-008-01 | Permisos externos | ¿008 emite permisos de SENIAT/SUNAGRO/INSAI/SACS? | **No.** Kontrol **registra y valida** documentos oficiales; no fabrica permisos de organismos externos (DOC-01 §10) | Producto | Resuelto |
| CL-008-02 | Guías | ¿SICA/SIGESAI/SACS se generan? | Se **registran y validan** (número, organismo, vigencia, archivo, hash); no se emiten oficialmente | Logística | Resuelto |
| CL-008-03 | Bloqueo | ¿Cuándo se bloquea el despacho? | Si falta documento obligatorio, está vencido o no coincide con producto/lote/cantidad/origen/destino/vehículo/conductor | Logística | Resuelto |
| CL-008-04 | Evaluación | ¿Por documento o por línea? | Por **línea de despacho**; se consolidan los requisitos del movimiento (DOC-02 §11) | Arquitecto | Resuelto |
| CL-008-05 | Aplicabilidad | ¿Cómo se determina? | Por rubro, presentación, actor, actividad, origen, destino, establecimiento, cantidad, unidad, operación y vigencia | Logística | Resuelto |
| CL-008-06 | Contingencias | ¿Se habilitan libremente? | Solo mediante **regla oficial versionada** (P8) | Regulatorio | Resuelto |
| CL-008-07 | Dependencias | ¿Se implementa sin 005? | Requiere **001 certificada** y **002/003/005 implementados**; consume `Shipment` de 005 vía contrato v1 | Arquitecto | Resuelto |
| CL-008-08 | Picking vs traslado | ¿El picking ampara el traslado? | No: el picking no ampara el traslado físico; la guía fiscal no sustituye SICA/SIGESAI/SACS | Logística | Resuelto |
| CL-008-09 | Vehículos/conductores | ¿Maestros propios? | Sí: vehículos y conductores con identificación, capacidad, seguros y documentos | Logística | Resuelto |
| CL-008-10 | Reglas de validación por organismo | ¿Se hardcodean? | No: `PermitType`/`RegulatoryProfile` versionados; prohibido hardcodear (P8) | Regulatorio | Resuelto |

## 2. Supuestos declarados

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-008-01 | Los perfiles regulatorios se cargan como datos (rubro→organismo→documentos) | Reglas incompletas | Perfiles versionados con vigencia |
| SU-008-02 | La validación de guías es documental (archivo/hash/estado), no un servicio oficial en línea | Verificación parcial | `PermitInstance.verification` + auditoría |
| SU-008-03 | Un despacho regulado no sale sin evaluación aprobada | Fuga de mercancía | Bloqueo por regla (FR-008-022) |
| SU-008-04 | Los vehículos/conductores se registran por empresa/sitio | Duplicidad | `OfficialRegistration` con unicidad |
| SU-008-05 | 008 no reimplementa el despacho de 005 | Acoplamiento | Contrato de API v1 |

## 3. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-008-11 | Tolerancias/reglas concretas por organismo y rubro (matrices oficiales) | Configuración por defecto | No la fase documental (se cargan como datos) |
| CL-008-12 | Alcance de "documento fiscal/comercial" simultáneo con guías | Modelo de bloqueo | No la fase documental |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |
