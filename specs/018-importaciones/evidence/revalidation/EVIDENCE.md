# Spec 018 · revalidación de las filas EXISTS_NOT_REVALIDATED

Encargo `SPEC018_REVALIDACION_Y_CONTINUACION`, del 2026-11-11. Fuente: `requerimientos/Procesos - Importacion - Recepcion de Importación y Distribucion en Almacen.docx`, leído entero.

**Método.** Se hizo arqueología del backend, el frontend, el menú y los permisos. Después se midió cada fila con una sonda de Claude, fuera del repositorio, en Chrome sobre PostgreSQL efímero migrado a `0098` y con el analizador real. Se usó el usuario administrador del arnés. Corridas:
- `qa/e2e-runs/r20261111t131521p1861381n5ef73b`;
- `qa/e2e-runs/r20261111t131638p1864130n8adc7c`, que repite el caso del ajuste después de corregir la sonda.

## Resultado

| Fila | Estado | Medido |
|---|---|---|
| IMP-04 Aprobar según autoridad | **COMPLETE** | Política `PURCHASE_ORDER` con regla por umbral y un nivel. Desde Compras → Órdenes, «submit» → la orden queda SUBMITTED. Aprobarla antes de autorizarla da 409 `APPROVAL_PENDING`. En Aprobaciones → Mis aprobaciones, «Aprobar» → «approve» → APPROVED. Lo aplica el motor (`transition_order`: `require_for_document` / `ensure_approved`) |
| IMP-05 Seleccionar y confirmar proveedor | **PARTIAL** (construida en este ciclo, ver la matriz) | Compras → Cotizaciones solo crea cotizaciones y líneas. No hay comparación, ni adjudicación, ni orden emitida desde la oferta |
| §2 Acta o registro de recepción | **COMPLETE** | Después de confirmar, enviar a calidad, conforme y aceptar en Compras → Recepciones, la columna «Acta» muestra la fecha y el registro guarda `record_issued_at` y `record_issued_by`. El acta es el registro de recepción fechado y con su responsable, como decide la Spec 019 |
| §3 Estados recibido, disponible, pendiente y bloqueado | **PARTIAL** | Inventario → Existencias muestra RECIBIDO antes de confirmar y DISPONIBLE después. EXACT_FUNCTIONAL_GAP: ningún proceso produce «pendiente de validación» (`PENDIENTE_CONFIRMACION`) ni «bloqueado por incidencia» (`BLOQUEADO`). Las aristas `INCIDENT_OPEN` e `INCIDENT_CLOSE` (dueña: Spec 020) están en el catálogo, pero ningún código las usa, y la Spec 020 decidió expresamente que la incidencia no toque el inventario. Una incidencia abierta impide confirmar (`INCIDENTS_UNRESOLVED`), pero el estado no la muestra. Reparar exige revisar esa decisión de la Spec 020: queda como dependencia |
| Conteo independiente | **PARTIAL** | El mismo usuario recibe, cuenta (`/conteo`, 200) y confirma (`/confirmacion-inventario`, 200). `counted_by` se guarda, pero no se exige que sea otra persona. `confirmation_same_user_allowed` solo rige la confirmación de pedidos de venta (Spec 033). EXACT_FUNCTIONAL_GAP: falta la segregación entre quien recibe o cuenta y quien confirma en la recepción. Impacto: el control crítico «conteo independiente» no está garantizado. Se puede reparar con el precedente R-D0-12-5 (control activo por defecto y desactivable por empresa) |
| Autorización de ajustes | **COMPLETE** | Con una política `RECEIPT_INCIDENT` activa: en Compras → Incidencias, «tratar» → «Ajuste autorizado» → «Pendiente de autorización». En la bandeja, «Aprobar». Después «tratar» → «Ajuste autorizado» → «Resuelta». Sin política activa el ajuste no pide autorización: la autoridad la configura cada empresa en Aprobaciones |

**Defectos de pantalla vistos, que no bloquean las filas:**
- **ORDENES-UI-ETIQUETAS.** En Compras → Órdenes, la tabla muestra el UUID del proveedor y las acciones y estados con sus códigos internos (`submit`, `approve`, `SUBMITTED`).
- **EXISTENCIAS-UI-ALMACEN.** Inventario → Existencias muestra el almacén como UUID y el estado con su código.
