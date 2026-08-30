# BACKLOG MAESTRO

Estimación relativa: XS · S · M · L · XL. **No se estiman horas** (sin datos de velocidad del equipo).
Este backlog es una **propuesta**; no se ha ejecutado ninguna de sus tareas.

## OLA 0 — Correcciones estructurales

| ID | Spec | Brecha | Prio | Depende | Resultado esperado | Criterio de aceptación | Est. |
|---|---|---|---|---|---|---|---|
| B-001 | 006, 051 | `organization` y `master_data` sin auditoría | P0 | — | Toda alta/modificación de empresa, sucursal, almacén, tercero y producto emite `AuditEvent` | E2E crea empresa+cliente+producto y `GET /audit/events` devuelve ≥3 eventos con actor, before/after | S |
| B-002 | 001, 052 | Alembic nunca ejecutado en PostgreSQL | P0 | — | Cadena 0001→0014 aplicada en PG real | `alembic upgrade head` sin error y `alembic check` sin drift | M |
| B-003 | 001 | Timezone no confirmado en PG | P0 | B-002 | `DateTime(timezone=True)` verificado aware | Consulta de tipo de columna devuelve `timestamptz` en las 48 columnas | XS |
| B-004 | 053 | Backup/restore nunca probado | P0 | B-002 | Recuperación demostrada | Backup → destruir entorno → restore → login, datos, licencia e `installation_id` íntegros | M |
| B-005 | 052 | `latest` como tag por defecto | P2 | — | Despliegue reproducible | `compose.yaml` sin default `latest`; entrypoint rechaza tag no fijado | XS |
| B-006 | 054 | 4 documentos de estado desfasados | P2 | — | Expediente coherente | `012/tasks.md`, reporte ejecutivo §3-5, `requirements-coverage.md` y README actualizados | S |
| B-007 | 034 | `SalesInvoice` sin `order_id` | P0 | B-002 | Factura trazable a su pedido | Migración aditiva con FK nullable; nueva factura exige orden; no se puede facturar dos veces la misma orden | M |

## OLA 1 — Fundación de dominio

| ID | Spec | Brecha | Prio | Depende | Resultado esperado | Criterio de aceptación | Est. |
|---|---|---|---|---|---|---|---|
| ~~B-010~~ | 045 | ~~Sin motor transversal~~ | — | — | **COMPLETADA 2026-08-29** — Spec 045 COMPLETE_100 | Criterios cumplidos y verificados sobre PostgreSQL real | XL |
| B-011 | 008 | Sin nivel ni posición; sin jerarquía de zonas | P0 | B-002 | Dirección física completa | `Location` con zona/pasillo/rack/nivel/posición; zonas A–E clasificables; capacidad y restricciones efectivas | L |
| B-012 | 046 | Tabla de archivos sin endpoint ni vínculo | P0 | B-002 | Adjuntos operativos | Subida y descarga con hash SHA-256, vínculo `entity_type`/`entity_id`, versiones, permisos y auditoría | L |

## OLA 2 — Maestros indispensables

| ID | Spec | Brecha | Prio | Depende | Resultado esperado | Criterio de aceptación | Est. |
|---|---|---|---|---|---|---|---|
| B-020 | 012 | Rama comercial inexistente | P0 | B-010 | Precio y condiciones gobernados por regla | Lista de precios versionada con vigencia y fuente; regla de descuento con aprobación; condiciones, zonas, rutas y comisiones como maestros; cotización toma el precio del maestro | XL |
| B-021 | 011 | Líneas sin unidad ni presentación | P0 | B-002 | Dimensión preservada en la transacción | Toda línea lleva `uom_id` y `presentation_id`; comprar en cajas y vender en unidades reproducible en E2E con conversión verificada | L |
| B-022 | 007 | Centros de costo y unidades de negocio | P1 | B-002 | Maestros reales con FK | Tablas creadas, `cost_center_id` migrado a FK, pantallas de gestión, uso en requisición y alcance de usuario | M |

## OLA 3 — Abastecimiento e importación

| ID | Spec | Brecha | Prio | Depende | Resultado esperado | Criterio de aceptación | Est. |
|---|---|---|---|---|---|---|---|
| B-030 | 018 | Importaciones inexistentes | P1 | B-012, B-010 | Expediente de importación completo | INCOTERM, proforma, packing list, documentos de embarque, certificados, anticipo, seguimiento y agente; expediente con adjuntos y estados | XL |
| B-031 | 015 | Sin planificación de demanda | P2 | B-021 | Requisición informada | Punto de reorden, rotación y proyección visibles al crear requisición | M |
| B-032 | 026 | Sin landed cost | P1 | B-030 | Costo real de importación | Gastos de importación distribuidos por criterio configurable e incorporados a las capas de costo | L |

## OLA 4 — Recepción, confirmación y almacenamiento

| ID | Spec | Brecha | Prio | Depende | Resultado esperado | Criterio de aceptación | Est. |
|---|---|---|---|---|---|---|---|
| B-040 | 019 | Recepción sin fase física | P0 | B-011, B-012 | Recepción real | Arribo, programación de descarga, bultos, pallets, inspección visual y evidencia adjunta | L |
| B-041 | 020 | Sin incidencias | P0 | B-040 | Incidencia trazable | Faltante, sobrante, daño, referencia errónea y diferencia documental con evidencia, escalamiento a Compras y estado | L |
| B-042 | 021 | Sin confirmación ni liberación | P0 | B-041, B-021 | Inventario liberado formalmente | Conteo por SKU, comparación contra orden/packing/física, estados recibido/pendiente/bloqueado/disponible, tratamiento (ajuste/reclamo/cuarentena) y liberación formal | XL |
| B-043 | 022 | Sin put-away | P0 | B-011, B-042 | Mercancía ubicada | Asignación de zona por criterio, traslado, confirmación física, validación física↔sistema, reubicación con corrección | L |

## OLA 5 — Preparación del pedido

| ID | Spec | Brecha | Prio | Depende | Resultado esperado | Criterio de aceptación | Est. |
|---|---|---|---|---|---|---|---|
| B-050 | 029 | Pedido sin entidad ni precio de maestro | P1 | B-020 | Pedido comercial real | Pedido distinto de orden, disponibilidad consultada al cotizar, precio y condiciones desde el maestro | L |
| B-051 | 030 | Momento de reserva indefinido | P0 | Decisión CL-013-06 | Reserva consistente | Decisión documentada en ADR; dos vendedores no pueden comprometer el mismo stock (prueba de concurrencia) | M |
| B-052 | 031 | Sin cola ni ruta | P0 | B-043 | Ruta de picking por ubicación | Cola con prioridad; recorrido ordenado por zona→pasillo→rack→nivel→posición; documento de picking usable por un almacenista | L |
| B-053 | 032 | Picking sin ejecución real | P0 | B-052 | Picking operativo | Almacenista asignado, línea marcada al preparar, registro de no localizado/insuficiente/dañado con evidencia, consolidación e identificación física del pedido | L |
| B-054 | 033 | Confirmación inexistente | P0 | B-053, B-010 | Segundo control independiente | Área de confirmación distinta del preparador; verificación producto a producto; no conforme devuelve a preparación; pedido `CONFIRMED` con acta | L |

## OLA 6 — Facturación y despacho

| ID | Spec | Brecha | Prio | Depende | Resultado esperado | Criterio de aceptación | Est. |
|---|---|---|---|---|---|---|---|
| B-060 | 034 | Sin compuerta de liberación | P0 | B-054, B-007 | Facturación gobernada | Solo se factura un pedido `CONFIRMED`; solicitud de facturación explícita; factura asociada al pedido; imposible doble facturación | M |
| B-061 | 035 | Despacho sin verificación triple ni POD | P1 | B-060 | Salida controlada | Verifica preparado+confirmado+facturado; dirección estructurada; evidencia de entrega adjunta | M |

## OLA 7 — Fiscal y regulatorio (paralelizable desde hoy)

| ID | Spec | Brecha | Prio | Depende | Resultado esperado | Criterio de aceptación | Est. |
|---|---|---|---|---|---|---|---|
| B-070 | 039-043 | Alícuotas y conceptos no cargados | **LEGAL_BLOCKER** | Equipo fiscal | Reglas vigentes cargadas | Cada regla con fuente legal, Gaceta, vigencia y versión; certificada por abogado tributario y contador público | L |
| B-071 | 042 | Contingencia sin UI ni flujo | P1 | B-070 | Contingencia operable | Flujo de contingencia con regla oficial versionada y regularización posterior | M |
| B-072 | 044 | Matrices oficiales no cargadas | P1 | Equipo regulatorio | Perfiles por organismo/rubro | Matriz cargada como perfil versionado con fuente | M |
| B-073 | 056 | Acto formal no ejecutado | **LEGAL_BLOCKER** | B-070, B-002 | Versión fiscal homologada | Acto formal firmado + gates verdes + versión liberada | M |

## OLA 8 — Transversales e información

| ID | Spec | Brecha | Prio | Resultado esperado | Est. |
|---|---|---|---|---|---|
| B-080 | 047 | Sin notificaciones ni tareas | P1 | Mis tareas, Mis aprobaciones, alertas, vencimientos y correo | L |
| B-081 | 048 | Integraciones ausentes | P1 | BCV, SMTP, storage y webhooks con contrato y prueba | L |
| B-082 | 049 | Analítica insuficiente | P2 | Rotación, tendencias e indicadores por módulo | M |
| B-083 | 050 | Sin Excel ni parametrización | P3 | Exportación XLSX y reportes parametrizables | M |

## OLA 9 — Operación, calidad y seguridad

| ID | Spec | Brecha | Prio | Resultado esperado | Est. |
|---|---|---|---|---|---|
| B-090 | 054 | Sin pruebas de página | P1 | Cobertura de comportamiento de las pantallas críticas | L |
| B-091 | 054 | Rendimiento sobre base vacía | P1 | P50/P95/P99 con dataset representativo; N+1 e índices revisados | M |
| B-092 | 055 | Sin SBOM ni rate limiting | P2 | SBOM emitido; límite de tasa global; política de uploads | M |
| B-093 | 052 | Actualización sin rollback probado | P1 | Update con pre-check, backup previo y rollback demostrado | M |

## Quick wins vs. arreglos arquitectónicos

| Quick win (XS/S, no oculta arquitectura) | Arreglo arquitectónico (no confundir con quick win) |
|---|---|
| B-001 auditoría en 2 módulos | B-010 motor de aprobaciones |
| B-003 verificación de timezone | B-011 dirección física completa |
| B-005 fijar tag de imagen | B-020 maestros comerciales |
| B-006 sincronizar documentos | B-021 unidad y presentación en línea |
| — | B-042/B-043 confirmación y put-away |
| — | B-052/B-053/B-054 cola, picking y confirmación |

**Advertencia:** los quick wins de la izquierda son reales y baratos, pero cerrarlos no mueve la
aguja del producto. No deben usarse como evidencia de avance frente a la columna derecha.


## Cierre de la Spec 008 — 2026-08-30

`SPEC 008 COMPLETE_100`. Segunda Spec del proyecto en alcanzarlo.

- Desbloquea por contrato verificado: **022, 031, 032**, y parcialmente **023,
  025 y 019** (ver `008-unblocked-specs.md`).
- Deuda escalada, no asumida: drift de licenciamiento (Spec 010), 22 violaciones
  responsive (Specs 005/054) y el aprovisionamiento de PostgreSQL 18 en CI
  (Spec 054).
- **Próxima Spec recomendada: 011 — Unidades y presentaciones.** Sin cambio de
  prioridad: no hay evidencia nueva que lo justifique.


## Cierre de la Spec 011 — 2026-08-30

`SPEC 011 COMPLETE_100`. Tercera Spec del proyecto en alcanzarlo.

- Las 17 líneas transaccionales capturan ya unidad, presentación, factor
  congelado y cantidad base. 30 columnas pasaron de `Float` a `NUMERIC` sin una
  sola diferencia fiscal.
- Desbloqueo verificado por contrato en `011-unlocked-specs.md`: ninguna Spec
  queda `FULLY_UNLOCKED`; 011 elimina una dependencia común, no todas.
- Deuda escalada, no asumida: drift de licenciamiento (010), responsive
  preexistente (005/054), aprovisionamiento de PG 18 en CI y detección de
  imports por `tsc` (054).
- **Próxima Spec recomendada: 046 — Gestión documental.** Sin cambio de
  prioridad: ningún hallazgo lo justifica.
