# ANÁLISIS — 005-VENTAS-CUENTAS-POR-COBRAR (`/speckit.analyze`)

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/analysis-report.md` |

## 1. Verificaciones realizadas

| Verificación | Resultado |
|---|---|
| Contradicciones | Ninguna detectada entre `spec.md`, `plan.md`, `data-model.md` y `contracts/api-contracts.md` |
| Duplicidades | Ninguna; reutiliza artefactos de 001/002/003/004 (errores, componentes, patrones WF, motor de 003, motor de aplicaciones de 004) |
| Requisitos sin tarea | Ninguno (trazabilidad completa) |
| Tareas sin requisito | Ninguna |
| Criterios no verificables | Ninguno (todos con prueba en `test-plan.md`) |
| Contratos incompletos | Completos para la fase (cotización → cobro; contrato para 006) |
| Riesgos sin control | Ninguno (`risk-register.md`) |
| Decisiones no documentadas | Ninguna (research + clarifications) |
| Dependencias | Correctas: 005 depende de 001, 002 (clientes/catálogo), 003 (inventario) y 004 (motor de aplicaciones CxC) |
| Cobertura de pruebas | Todos los requisitos con prueba, incluida la concurrencia de cobros |
| Cumplimiento de Constitución | Compatible (verificación en `plan.md`; núcleo fiscal separado P4) |
| Alcance y exclusiones | Respetados (006 tesorería / 007 fiscal / 008 regulación / 009 reportes fuera de alcance) |
| Consistencia de nombres | KONTROL/kontrol; sin INNOVA en artefactos nuevos |
| Ausencia de INNOVA | ✔ (solo referencias legado en documentos fuente) |

## 2. Hallazgos

| Clasificación | Hallazgo |
|---|---|
| BLOCKER | Ninguno |
| CRITICAL | Ninguno |
| HIGH | Dependencias: la implementación requiere 001 certificada, **002/003/004 implementados** — no bloquea la fase documental |
| MEDIUM | Políticas pendientes: límites de crédito y días de vencimiento por empresa (CL-005-09/10) |
| LOW | Factura comercial hasta 007 (emisión fiscal formal fuera de 005) — planificado |
| INFORMATIONAL | CxC reutiliza el motor de aplicaciones de 004 (CL-005-01) |

## 3. Conclusión

La Spec **005-ventas-cuentas-por-cobrar** está completa, consistente y sin bloqueos para la fase documental. **No se debe implementar** sin: (1) certificación de 001 (CI verde, Docker validado), (2) **002/003/004 implementados**, y (3) autorización expresa que mencione **005-ventas-cuentas-por-cobrar**.

## 4. Estado

| Elemento | Estado |
|---|---|
| `/speckit.analyze` ejecutado | ✔ |
| Contradicciones bloqueantes | Ninguna |
| Lista para implementación | ✔ (sujeta a 001 certificada + 002/003/004 implementados + autorización) |

---

# ANALYZE — SPEC 029 · IMPLEMENTACIÓN

| Categoría | Resultado |
|---|---:|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICCIONES | 0 |
| REQUISITOS HUÉRFANOS | 0 |
| TAREAS HUÉRFANAS | 0 |
| PREGUNTAS ABIERTAS MATERIALES | 0 |

## Antes de implementar

Una decisión no estaba documentada: la **cardinalidad** de la conversión. Se
resolvió **1:1** por el contrato del propio ciclo —«una cotización no puede
producir múltiples pedidos si el contrato es 1:1; si permite 1:N, debe estar
expresamente modelado»— y porque es la lectura que se puede ampliar después. Un
1:N por defecto no se estrecha sin romper datos.

No se registró como pregunta abierta material porque la regla existía; lo que
faltaba era aplicarla.

## Lo que la implementación encontró

| Hallazgo | Tipo | Resolución |
|---|---|---|
| La línea truncaba el precio del maestro: 4 decimales → 2 | CRITICAL propio | Escala igualada en `0042` |
| La cotización nacía en `ACTIVE`, estado sin transiciones | CONTRADICCIÓN | Ciclo declarado; nace en `DRAFT` |
| El detalle del pedido no mostraba el origen | CRITICAL propio | `order_dict` lo expone |
| La reserva existente vive en 029 y es de la 030 | FRONTERA | Auditada, **no tocada**, documentada |
| `sales_invoice_lines` sigue en `Numeric(18,2)` | ANOTADO | Es de la Spec 034 |

## Lo que se buscó y no se encontró

Segundo resolutor de precio, origen no persistido, evidencia perdida en la
conversión, reprecio silencioso, precio manual sin procedencia, código de
reserva nuevo, suposición sobre `D0-03`, picking o factura dentro de 029, coma
flotante monetaria, `company_id` redundante en las líneas, ruta hija sin
validación del padre y prueba negativa que falla por el motivo equivocado.
