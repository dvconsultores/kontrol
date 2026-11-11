# Conteo independiente en la recepción: evidencia

Autoridad y decisión de la dueña: `../../INDEPENDENT_COUNT_AUTHORITY.md`. Delta: `../../spec021-independent-count-delta.md`. Registro de intentos: `ATTEMPT_LOG.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE: Inventario → Confirmación aplica el control, en Chrome sobre PostgreSQL |
| OWNER_READINESS_STATUS | OWNER_UAT_READY: pasos 96 a 101 de la tarjeta. `OWNER_ACCEPTED`: NO |

## Regla aplicada

- **Quién se separa:** receptor ≠ contador. Son receptores `goods_receipts.created_by` y `record_issued_by`, comparados por el id persistido del usuario.
- **Configuración:** el control está activo por defecto (`companies.receipt_count_same_user_allowed = false`). Se desactiva con `PUT /purchasing/settings/receipt-count`, que exige el permiso `compras:approve` y audita `COMPANY_RECEIPT_COUNT_POLICY_CHANGED` con el valor anterior y el nuevo. No es retroactivo.

## Puertas de completitud

| Puerta | Estado |
|---|---|
| BACKEND_COMPLETE | `registrar_conteo` rechaza al receptor (`INDEPENDENT_COUNT_REQUIRED`). `confirmar_inventario` exige cada línea contada (`COUNT_REQUIRED_BEFORE_CONFIRMATION`) y que no la haya contado un receptor, antes de cualquier movimiento |
| DATABASE_COMPLETE | Migración `0101_receipt_count_independence`. En PostgreSQL nuevo: sube a la cabeza → baja → vuelve a subir, con una sola cabeza. La columna es `NOT NULL DEFAULT false` |
| API_COMPLETE | `GET/PUT /purchasing/settings/receipt-count`. Los errores de negocio llevan códigos estables. OpenAPI: solo adiciones |
| FRONTEND / SCREEN / MENU_COMPLETE | Inventario → Confirmación (menú existente): el aviso del estado del control, la sección «Política de conteo» (visible solo con permiso) y el mensaje de negocio del backend cuando hay rechazo |
| PROCESS_COMPLETE | Recibir (A) → A no puede contar → B cuenta → se confirma → la mercancía queda DISPONIBLE |
| FIELDS_COMPLETE | La casilla «Permitir que quien recibe cuente la mercancía» |
| ROLES_COMPLETE | Se reutilizan permisos existentes: `inventario:confirm` para contar y confirmar, `compras:view` y `compras:approve` para la política. No se crearon roles artificiales |
| AUDIT_COMPLETE | `RECEIPT_LINE_COUNTED` y `RECEIPT_INVENTORY_CONFIRMED` con su autor (comprobado en la E2E con el usuario real), y `COMPANY_RECEIPT_COUNT_POLICY_CHANGED` con antes y después. Las denegaciones no se auditan: el contrato vigente audita hechos |
| SECURITY_COMPLETE | Lo aplica el backend: el rechazo ocurre igual llamando a la API directamente (probado por API y por pantalla). La política es por empresa: la de B no cambia al modificar la de A (probado) |
| CONCURRENCY_COMPLETE | `registrar_conteo` y `confirmar_inventario` bloquean la fila de la recepción con `with_for_update().execution_options(populate_existing=True)`, el patrón del módulo. La confirmación valida dentro de su transacción y con `counted_by` definitivo |
| E2E_COMPLETE | `e2e/conteo-independiente.spec.ts` |
| RESPONSIVE_COMPLETE | Flujo completo a 1280, 390 y 320, sin desbordamiento horizontal |
| ACCESSIBILITY_COMPLETE | Axe (WCAG 2.0/2.1 A y AA) con 0 faltas graves o críticas tras el rechazo y tras la confirmación, a 1280, 390 y 320. La casilla es un `input` nativo con `label` asociado y se usa con teclado |
| DOCUMENT / REPORTING | NOT_APPLICABLE: el control no genera documento. El rastro está en la bitácora |

## Pruebas

| Prueba | Resultado |
|---|---|
| `tests/test_spec021_independent_count.py`: el receptor no cuenta y no se escribe nada; cuenta otro y confirma con los autores correctos; sin conteo no se confirma y no quedan efectos; política por defecto, desactivación auditada y aislamiento por empresa | PASS en PostgreSQL |
| `tests/test_spec021_confirmation.py`, adaptado: cuenta `uab` (IC-08), sin debilitar el control | PASS |
| Regresión dirigida PostgreSQL: 41 ficheros (Specs 019 a 023, compras, importaciones, aprobaciones, auditoría, migraciones, alcance de empresa) | 524 PASS. Los 3 fallos son de la línea base: `n10` (sin la columna nueva), y dos de `spec019_receipt` |
| E2E en Chrome sobre PostgreSQL efímero, con analizador real: `conteo-independiente`, `receipts`, `inventory-confirmation` e `importaciones` (adaptadas) | 14/14 PASS |
| Vitest completo · typecheck · lint · build | 1911/1911 · limpio · limpio · correcto |
| ruff | limpio en los ficheros tocados |

## Hallazgo del arnés (corregido)

La E2E nueva es la primera en la que entran dos usuarios en un mismo navegador. Esto destapó un defecto previo de `e2e/helpers/sesion.ts`: al terminar, el fixture `_cadenaDeSesion` guardaba la única cookie de refresco en el estado de todos los usuarios que habían entrado. La prueba siguiente del worker actuaba como el segundo usuario: se midió «Emitido por ic-…» en `importaciones`. Corrección (llamada 4): el helper recuerda solo al último usuario que entró.

## Deudas fuera de alcance

Ninguna nueva. No se absorbieron:
- los estados §3;
- programar la descarga;
- la zona temporal;
- la trazabilidad hasta la ubicación final;
- las zonas A a E;
- ORDENES-UI-ETIQUETAS y EXISTENCIAS-UI-ALMACEN;
- QUOTE-REQUISITION-LINK;
- las deudas de costo;
- E2E-INVCONF y A11Y-IMPORT-SCROLL-REGIONS;
- Government.

## Cierre

- **Fusión con CTL-05 de P1** (`a245de0`): la migración de este ciclo se reencadenó como `0101` detrás de `0100_gov_ctl05_rendicion`, con una llamada extra que autorizó la dueña. El catálogo queda en 476.
- **Sobre el árbol fusionado:**
  - suite completa de backend en PostgreSQL, con analizador real: 5334 PASS y los 5 fallos de la línea base (`gobierno_integridad`, `n10`, `naive_datetime` y dos de `spec019_receipt`). NEW_FAILURES = 0;
  - Vitest 1922/1922; typecheck, lint y build limpios;
  - E2E del ciclo 14/14.
- **Publicado** en `7e53ca9`, con `HEAD == origin/develop`. La UAT `kuat` está en `0101`.
