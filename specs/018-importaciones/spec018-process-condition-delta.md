# Spec 018 · delta: condición del proceso de recepción (§3)

- **Encargo:** `SPEC018_ESTADOS_SECCION_3`, 2026-11-11.
- **Spec dueña:** 018, dueña del proceso de Importaciones.
- **Autoridades del dato:** la recepción es de la Spec 019; la incidencia es de la 020; la confirmación de inventario es de la 021; el inventario y el put-away son de la 022/023.
- **Decisión:** `evidence/SPEC018_REMAINING_DECISIONS.md` → «Condición del proceso» (opción A).
- **Evidencia:** `evidence/process-condition/`.

## Decisión de la dueña (2026-11-11)

La fila del DOCX §3 —«Diferenciar inventario: recibido; disponible; pendiente de validación; bloqueado por incidencia»— se cierra como **condición del proceso**, no como estado físico del inventario. No se crea ningún estado nuevo de mercancía, no se mueve stock y la decisión de la Spec 020 —una incidencia no toca el inventario— permanece vigente.

## Contrato

- **PC-01. Autoridad de la condición.**
  - La condición es de la Spec 018 y se **deriva** del estado real de la recepción, su confirmación de inventario y sus incidencias vivas.
  - Una sola función de dominio, `purchasing.process_condition`, con una consulta por lote. Las dos superficies de producto consumen su resultado; ninguna recalcula.
  - No hay columna nueva ni tabla nueva: `MIGRATION_REQUIRED=0`.
  - No se crea un segundo motor de incidencias ni se activan las aristas `INCIDENT_OPEN`/`INCIDENT_CLOSE`.
- **PC-02. «Recibido».**
  - La recepción no está bloqueada y su inventario está confirmado (`confirmation_status = CONFIRMADA`, Spec 021).
  - No inventa una transición física nueva: describe el final del procedimiento.
- **PC-03. «Pendiente de validación».**
  - No hay incidencia bloqueante y el inventario aún no está confirmado.
  - Cubre la recepción recién creada, la recibida sin contar y la contada sin confirmar. Contar no valida: la validación la cierra la confirmación de la 021.
- **PC-04. «Bloqueado por incidencia».**
  - Existe al menos una incidencia viva que impide confirmar: estado distinto de `RESUELTA` y `ANULADA`.
  - Es el mismo criterio que la Spec 021 aplica con `INCIDENTS_UNRESOLVED`; la condición lo muestra, no lo reimplementa.
  - Una incidencia en `PENDIENTE_AUTORIZACION` también bloquea, porque tampoco permite confirmar.
- **PC-05. Precedencia.**
  - `si hay incidencia bloqueante → BLOQUEADO_POR_INCIDENCIA`
  - `si no la hay y el inventario no está confirmado → PENDIENTE_DE_VALIDACION`
  - `si ninguna de las anteriores aplica → RECIBIDO`
  - Una sola condición principal por recepción, determinista.
- **PC-06. Transición al abrir una incidencia.**
  - No hay escritura de la condición: el siguiente cálculo ya la muestra bloqueada.
  - No se emite evento de auditoría por el cambio de una condición derivada; la apertura la audita el motor de la Spec 020.
- **PC-07. Transición al resolver la incidencia.**
  - La condición se recalcula desde el estado real: si ya estaba confirmada vuelve a «Recibido»; si no, a «Pendiente de validación».
  - No se almacena manualmente ninguna condición.
- **PC-08. Exposición en Recepciones.**
  - `process_condition` en `GET /purchasing/receipts` y `GET /purchasing/receipts/{id}` (adición compatible).
  - Columna «Condición» en el listado y bloque «Condición del proceso» en la ficha.
  - Cuando está bloqueada, el texto explica por qué no puede avanzar y enlaza a las incidencias existentes de esa recepción.
- **PC-09. Exposición en el expediente de Importación.**
  - `logistics.receipts[].process_condition`, calculado con la misma función.
  - Se muestra en la sección «Recepción» del expediente; el enlace a incidencias conserva también el expediente de origen.
- **PC-10. Auditoría y reutilización.**
  - No se añade ningún evento de auditoría: lo material —incidencia, conteo, confirmación— ya lo auditan sus dueños.
  - No se añade permiso ni capacidad: la condición viaja con `compras:view`, el mismo permiso que ya abre ambas pantallas.
  - El texto humano llega del backend (`label`, `reason`); React no define una segunda tabla de condiciones.
- **PC-11. Seguridad y aislamiento.**
  - Las consultas se restringen a las recepciones ya filtradas por la empresa del contexto y, además, por `company_id`.
  - Otra empresa recibe 404 en el detalle y no ve la recepción en el listado.
- **PC-12. Compatibilidad con las Specs 019–022.**
  - Sin cambios de esquema, sin nuevos estados de inventario, sin cambios en las aristas de incidencia ni en el put-away.
  - Las guardias `test_spec019_architecture`, `test_spec020_architecture`, `test_spec021_architecture` y `test_spec022_architecture` no se modifican y siguen en verde.

### Recepciones fuera del flujo normal

`CANCELLED` y `REJECTED` no tienen condición del proceso (`null`): no son una cuarta condición y la pantalla sigue mostrando el estado del documento, que ya existe.

## Estado

CONVERGED el 2026-11-12. `MIGRATION_REQUIRED=0`. La verificación de producto de esta fila corre en `e2e/condicion-recepcion.spec.ts` (Chrome sobre PostgreSQL efímero, con ClamAV real y Axe): pendiente, bloqueada, recalculada y recibida a 1280, 390 y 320.

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|
| T018-PC-0 Delta, autoridad y decisiones | CLAUDE | n-a | NO | n-a | este documento | — | PC-01 a PC-12 fijados |
| T018-PC-A Backend: condición derivada y superficies | DEEPSEEK | deepseek-v4-flash | NO | 2 | `purchasing/process_condition.py`, `purchasing/{api,models,service}.py`, `imports/service.py` | pytest PostgreSQL | PC-01 a PC-09 |
| T018-PC-B Pruebas dirigidas y guardia estructural | DEEPSEEK | deepseek-v4-flash | NO | 2 | `tests/test_spec018_process_condition.py`, `tests/test_spec018_process_condition_architecture.py` | pytest PostgreSQL | casos 1 a 5, aislamiento y stock intacto |
| T018-PC-C Pantallas y pruebas de componente | DEEPSEEK | deepseek-v4-flash | NO | 2 | `CondicionDelProceso.tsx`, `RecepcionesPage.tsx`, `ImportacionRecepcion.tsx`, `api/types.ts`, `importaciones/tipos.ts`, `CondicionDelProceso.test.tsx` | Vitest, typecheck, lint, build | condición visible y sin tabla propia en React |
| T018-PC-D E2E, evidencia, matriz y UAT | DEEPSEEK | deepseek-v4-flash | NO | 2 | `e2e/importaciones.spec.ts`, `evidence/process-condition/`, matriz, tarjeta UAT | E2E Chrome PostgreSQL | 1280, 390 y 320 |
