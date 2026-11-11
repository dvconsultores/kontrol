# Programar descarga desde la importación: autoridad

Encargo `SPEC018_PROGRAMAR_DESCARGA`, del 2026-11-11. Fila de la matriz: «§2 Programar descarga», PARTIAL.

```text
SOURCE_REQUIREMENT=DOCX «Procesos - Importacion - Recepcion…» §2, literal: «Confirmar arribo de la mercancía.» / «Programar descarga y recepción.» / «Recibir físicamente.» No pide nada más: ni ventana, ni responsable, ni muelle, ni ubicación, ni observaciones, ni estados.
CURRENT_EXISTING_CAPABILITY=goods_receipts.unloading_scheduled_at (Spec 019, «etapa 2»). Se fija SOLO al crear la recepción: POST /purchasing/receipts y POST /importaciones/{id}/receipts (el body ya acepta unloading_scheduled_at). No hay forma de programar ni reprogramar una recepción que ya existe.
CURRENT_OWNER_DOMAIN=Recepciones (purchasing, Spec 019). Importaciones orquesta: crea la recepción sobre file.order_id (vínculo estructurado expediente → orden → recepción).
CURRENT_DATABASE_FIELD=goods_receipts.unloading_scheduled_at TIMESTAMPTZ NULL
CURRENT_API=create con el campo; GET /purchasing/receipts y GET /purchasing/receipts/{id} lo devuelven; el detalle del expediente (logistics.receipts) NO lo devuelve
CURRENT_FRONTEND=Compras → Recepciones: «Descarga programada» solo en el formulario de alta (hora de Caracas). Ni la tabla de Recepciones ni el expediente de Importaciones lo muestran. El formulario «Crear recepción» del expediente no lo pide.
CURRENT_PERMISSIONS=compras:create (crear la recepción, confirmar el arribo, confirmar la recepción)
CURRENT_AUDIT=RECEIPT_CREATED incluye unloading_scheduled_at; IMPORT_RECEIPT_CREATED; RECEIPT_ARRIVAL_CONFIRMED. No hay evento para reprogramar.
GAP=(1) programar o reprogramar una recepción abierta; (2) hacerlo desde el expediente; (3) ver la programación en el expediente y en la tabla de Recepciones.
```

## Decisión (MATERIAL_DECISION_REQUIRED = 0)

- **Caso A.** La fuente solo exige programar, y lo que se programa es un instante. Se reutiliza `unloading_scheduled_at` como única fuente de verdad: ni columna nueva ni motor nuevo. `MIGRATION_REQUIRED = 0`.
- **Cuándo se puede programar.** En una recepción abierta (DRAFT o CONFIRMED): es la misma definición que la acción hermana «Confirmar arribo» (`confirmar_arribo`, `RECEIPT_NOT_OPEN`). Es una BUSINESS_RULE con precedente en el código, no inventada. Una recepción cerrada, cancelada, rechazada o ya en calidad no se reprograma.
- **Pasado.** No se restringe, porque la fuente no lo hace: se puede registrar una descarga ya ocurrida.
- **Borrar.** Se permite con un valor nulo. Es UX_CONVENIENCE, auditada.
- **Permisos.** Ver: `compras:view`, como hoy en Recepciones y en Importaciones. Programar, editar y borrar: `compras:create`, el mismo de las acciones hermanas de la etapa (arribo y confirmación). No es una aprobación.
- **Zona horaria.** Se entra como hora de Caracas en el frontend (`instanteDesdeHoraDeCaracas`). El backend la recibe como `InstanteDeEntrada` (con zona, normalizado a UTC; OD-TIME-01) y se muestra con `formatearInstante`. No hay conversión especial.
