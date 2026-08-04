# PLAN DE PRUEBAS — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/008-regulacion-traslados/test-plan.md` |

> Estrategia: pytest backend (sqlite in-memory, fixture `conftest.py`), Vitest frontend, build. Se añade `tests/test_regulatory.py`.

| ID | Tipo | Caso | Prerrequisito | Resultado esperado | Estado |
|---|---|---|---|---|---|
| TP-008-01 | Unit | Crear autoridad regulatoria | — | Autoridad con código y método de validación | ⬜ |
| TP-008-02 | Unit | Crear tipo de permiso por autoridad | Autoridad | Tipo con alcance y validación | ⬜ |
| TP-008-03 | Unit | Registro oficial | Autoridad | Registro con número, fechas, archivo, estado | ⬜ |
| TP-008-04 | Unit | Vehículo y conductor | Party | Registro con identificación/capacidad/documentos | ⬜ |
| TP-008-05 | Unit | Perfil regulatorio exige documentos | Rubro/operación | Perfil con documentos requeridos | ⬜ |
| TP-008-06 | Unit | PermitInstance completo | Tipo + vehículo | Instancia con número, vigencia, origen/destino, transporte | ⬜ |
| TP-008-07 | Unit | Ciclo de permiso | Instancia | DRAFT→REGISTERED→VERIFIED→APPROVED_FOR_USE→USED→EXPIRED; REJECTED | ⬜ |
| TP-008-08 | Unit | Guía SICA/SIGESAI/SACS registrada | Autoridad | Guía con hash y verificación; no fabricada | ⬜ |
| TP-008-09 | Unit | Documento conserva trazabilidad | Guía | Número/organismo/vigencia/archivo/hash/verificación/auditoría | ⬜ |
| TP-008-10 | Negativo | No se elimina permiso | Instancia | Corrección por documento vinculado | ⬜ |
| TP-008-11 | Unit | Evaluación por línea de despacho | Shipment 005 | Evaluación por línea con requisitos consolidados | ⬜ |
| TP-008-12 | Unit | RegulatoryEvaluation registra bloqueos | Evaluación | Resultados, bloqueos y anulación | ⬜ |
| TP-008-13 | Negativo | Despacho bloqueado sin documento | Evaluación | Bloqueo por faltante/vencido/no coincidencia | ⬜ |
| TP-008-14 | Unit | Aplicabilidad por rubro/operación | Perfil | Solo exige documentos aplicables | ⬜ |
| TP-008-15 | Unit | Requisito simultáneo fiscal + SICA + SIGESAI + SACS | Despacho | Consolida múltiples documentos | ⬜ |
| TP-008-16 | Unit | ApprovalRequest | Objeto + regla | Solicitante/aprobadores/riesgo/decisión/estado | ⬜ |
| TP-008-17 | Unit | Contingencia con regla versionada | Regla oficial | Habilitada solo con regla; sin regla → rechazo | ⬜ |
| TP-008-18 | Unit | Picking no ampara traslado | Despacho | Bloqueo de salida sin evaluación | ⬜ |
| TP-008-19 | Integración | Contract con 005 (`Shipment`) | Despachos | 008 consume sin duplicar | ⬜ |
| TP-008-20 | Unit | Aislamiento multiempresa | 2 empresas | Sin fuga de datos | ⬜ |
| TP-008-21 | UI | Pantallas regulatorias | Frontend | Organismos/permisos/evaluación sin scroll horizontal | ⬜ |
