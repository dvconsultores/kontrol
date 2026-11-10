# Delta · Clasificación de almacenamiento, zona y etiquetado

**Spec dueña:** 018 (Importaciones, DOCX §4). **Consume sin modificar:**
- Spec 008: `WarehouseZone`, `ZoneType` y `display_path`.
- Spec 011: unidades y `physical_factor`.
- Maestros: `TaxonomyNode` y `CatalogItem.category_id`.
- Spec 022: `putaway()`.
- Spec 046: `get_storage`.

**Autorización de implement:** encargo de la dueña del 2026-11-09, `SPEC018_CLASIFICACION_ZONA_ETIQUETADO`. `MATERIAL_DECISION_REQUIRED = 0`: lo que el sponsor no definió se resuelve como configuración, nunca como valor fijo en el código. `HARDCODED_ZONE_A_E = 0`.

## Resultado para la dueña

- **Maestros → Almacenamiento.** Configura:
  - condiciones especiales;
  - clases de tamaño;
  - el perfil de almacenamiento de cada producto: peso con unidad, volumen con unidad, clase de tamaño y condiciones;
  - las reglas de almacenamiento;
  - la política de cada almacén.
- **Compras → Importaciones → Expediente → Ubicación.** Para cada mercancía por ubicar:
  - clasifica y ve la zona determinada con su explicación;
  - genera e imprime la etiqueta cuando la regla la exige;
  - coloca la mercancía en una de las ubicaciones de esa zona.

## Arqueología

| Hecho | Consecuencia |
|---|---|
| `AttributeValue.typed_value` es JSON libre; `AttributeDefinition.unit` es texto sin FK; no hay servicio, API de valores, pantalla ni auditoría de valores | No sirve para una comparación cuantitativa con unidad gobernada: se crea una **extensión tipada mínima** (perfil de almacenamiento) |
| `UnitOfMeasure.dimension` admite `MASA`, `PESO` y `VOLUMEN`; `physical_factor(db, from, to)` convierte entre unidades de la misma dimensión, en directo o a la inversa | Las reglas comparan peso y volumen en la unidad de la regla con `physical_factor`; 10 kg y 10 000 g dan lo mismo si existe la conversión |
| `TaxonomyNode` tiene `parent_id` y `level` libre, sin convención de tipo o familia; el producto se vincula con `category_id` | La regla apunta a un nodo y casa con la categoría del producto o con cualquiera de sus ancestros: tipo, familia o categoría según cómo la empresa haya construido su árbol |
| `WarehouseZone` (por almacén, con `zone_type_id`) y `ZoneType` (por empresa) existen; KONTROL no define zonas fijas | La regla apunta a una zona concreta o a un tipo de zona. Ninguna lógica conoce «A» a «E» |
| La capacidad y las `restrictions` de la ubicación son informativas (`enforced: False`) | No se cambia esa semántica |
| `Warehouse.policies` es JSON sin gobierno | La política de clasificación es una tabla tipada propia |
| No hay rotación en el código ni Spec 015 | `ROTATION_CLASSIFICATION_COMPLETE = 0` y `ROTATION_DEPENDENCY_BLOCKED_BY_SPEC015 = 1`. Las reglas no llevan un criterio de rotación sin fuente |
| ReportLab (`reportlab.graphics.barcode` incluye QR) y `get_storage` existen; no hay concepto de etiqueta de mercancía | La etiqueta es un PDF guardado y verificado, con un QR del identificador interno, sin dependencia nueva |

## Decisiones

| ID | Decisión |
|---|---|
| SC-01 | Módulo nuevo `app/modules/storage/` (modelos, motor, etiquetas y API), registrado en `main.py` y en `init_models` |
| SC-02 | Catálogos por empresa: `storage_conditions` y `storage_size_classes` (código, nombre, estado y versión). La empresa define cuáles existen |
| SC-03 | `product_storage_profiles`, uno por producto: peso (valor y unidad de dimensión `MASA` o `PESO`), volumen (valor y unidad `VOLUMEN`), clase de tamaño y condiciones (tabla `product_storage_conditions`). Todos los campos son opcionales |
| SC-04 | `storage_rules`, con criterios tipados y todos opcionales, pero al menos uno: taxonomía, clase de tamaño, condición, rango de peso con unidad y rango de volumen con unidad. Destino: exactamente uno entre una zona concreta (que exige almacén) y un tipo de zona. Además `label_policy` (`REQUIRED`, `OPTIONAL`, `NOT_REQUIRED`), `priority` (1 es la más alta), estado, vigencia (`valid_from`, `valid_to`) y versión |
| SC-05 | Resolución determinista. Primero cuentan las reglas vigentes que casan. Gana la mejor prioridad; entre iguales, la más específica, con más criterios. Si en el grupo ganador quedan destinos distintos: `AMBIGUOUS`. Si no casa ninguna: `NO_RULE`. Nunca se elige una zona por defecto |
| SC-06 | Explicación: cada resultado guarda las razones (qué criterio casó y cuál no), los criterios que faltan (un dato del producto que la regla necesita) y las reglas candidatas |
| SC-07 | `warehouse_storage_policies`, una por almacén: `mode` (`DISABLED`, que es el almacén simple con el comportamiento actual, o `ENFORCED`) y `on_no_rule` (`BLOCK` o `ALLOW_ANY`) |
| SC-08 | `storage_classifications` es una instantánea inmutable: regla y versión, entradas, resultado, destino, política de etiqueta, razones, actor y fecha. Reclasificar crea una fila nueva y deja la anterior `SUPERSEDED`. Solo se clasifica lo que aún está pendiente de ubicar |
| SC-09 | **Vigencia.** Al ubicar, si la regla cambió de versión o se desactivó: 409 `STORAGE_CLASSIFICATION_STALE`, y hay que reclasificar. Las reglas se editan con `expected_version` (409 `VERSION_CONFLICT`) |
| SC-10 | **Put-away del expediente.** Un endpoint propio valida y llama a `putaway()` sin modificarlo. En `ENFORCED`: el destino debe estar en una zona determinada (si no, 409 `LOCATION_OUTSIDE_DETERMINED_ZONE`); `REQUIRED` exige etiqueta previa (si no, 409 `STORAGE_LABEL_REQUIRED`); con `NO_RULE`, `BLOCK` impide ubicar y `ALLOW_ANY` deja elegir. En `DISABLED` se comporta como hoy. El put-away genérico de Inventario no cambia: un límite declarado |
| SC-11 | La etiqueta es identificación operativa interna, no regulatoria. Referencia `ETQ-nnnnnn`, correlativa por empresa con bloqueo de `Company`. Contiene empresa, código y nombre del producto, cantidad, recepción, expediente, zona, la ubicación si ya existe, la fecha y un QR con la referencia. PDF guardado y verificado, que se descarga y se imprime en línea |
| SC-12 | Permisos. Configurar condiciones, clases, perfiles y reglas: `maestros:*`. Política del almacén: `organization:edit`. Clasificar, etiquetar y ubicar: `inventario:create`. Consultar desde el expediente: `compras:view` |
| SC-13 | Auditoría con `record_audit` y acciones literales: alta y cambio de condición, de clase y de regla; perfil guardado; política guardada; clasificado; reclasificado; etiqueta generada |
| SC-14 | Aislamiento. Toda referencia (zona, tipo, taxonomía, clase, condición, unidad, producto, almacén) debe ser de la empresa (las unidades, también globales). Las zonas además deben estar activas y ser del almacén de la regla. Si no, 404 o 409 |

## Modelo (migración `0092_storage_classification`)

Tablas:
- `storage_conditions`
- `storage_size_classes`
- `product_storage_profiles`
- `product_storage_conditions`
- `storage_rules`
- `warehouse_storage_policies`
- `storage_classifications`
- `storage_labels`

Todas llevan `created_by` no nulo y `company_id`, con restricciones CHECK de coherencia: destino único, unidad con valor, rangos positivos y valores cerrados.

## Tareas

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | DONE_WHEN |
|---|---|---|---|---|---|---|---|
| T-SC-A | Módulo storage: modelos, migración, motor, API de configuración, auditoría y pruebas | DEEPSEEK | deepseek-v4-pro | SÍ (contrato fijado aquí) | SÍ | 2 | Motor y configuración probados en PostgreSQL y SQLite |
| T-SC-B | Integración con el expediente: vista, clasificación, put-away, etiqueta PDF y pruebas | DEEPSEEK | deepseek-v4-pro | SÍ | SÍ | 2 | Flujo del expediente y negativas probados |
| T-SC-C | Frontend: Maestros → Almacenamiento, sección del expediente y Vitest | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | Configurar, clasificar, etiquetar y ubicar |
| T-SC-D | E2E de usuario | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | Con etiqueta, sin etiqueta y sin regla |
| T-SC-E | Certificación, documentos y publicación | CLAUDE | n-a | NO | SÍ | 0 | `HEAD == origin/develop` |

## Fuera de alcance

- Rotación: depende de la Spec 015.
- Significado de las zonas A a E: requiere validación del sponsor.
- *Slotting* y elección automática de ubicación exacta.
- Hacer obligatoria la capacidad.
- Etiqueta de ubicación.
- Etiquetas regulatorias o GS1.
- Drivers de impresora.
- Aplicar la política en el put-away genérico de Inventario.

## Cierre

`CONVERGED` en el commit de cierre del ciclo en `develop`, tras la fusión ordinaria con PROC-07 (migración `0093_fusion_gov_storage`). Evidencia: `evidence/storage-classification/EVIDENCE.md`. Intentos: `evidence/storage-classification/ATTEMPT_LOG.md`. `ROTATION_CLASSIFICATION_COMPLETE = 0` (Spec 015). `SPONSOR_ZONE_A_E_VALIDATED = 0`. `OWNER_ACCEPTED` lo concede solo la dueña.
