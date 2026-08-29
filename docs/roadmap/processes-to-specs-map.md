# MATRIZ DE PROCESOS — COBERTURA REAL ETAPA POR ETAPA

Leyenda: ✔ implementado y probado · ◐ parcial · ✖ ausente

## P-01 Organización (Empresa → Sucursal → Establecimiento → Almacén → Ubicación)

| Etapa | Estado | Spec |
|---|---|---|
| Empresa · Sucursal · Establecimiento · Almacén · Ubicación | ✔ | 007, 008 |
| Centro de costo · Unidad de negocio | ✖ | 007 |
| Zona/pasillo/rack | ◐ (sin nivel ni posición) | 008 |

**Veredicto:** PARTIAL. E2E verificado hasta Almacén.

## P-02 Compra nacional

| Etapa | Estado | Spec |
|---|---|---|
| Detectar necesidad · revisar rotación/demanda | ✖ | 015 |
| Requisición · aprobación | ✔ | 015, 045 |
| RFQ · oferta · comparación · selección | ✔ | 016 |
| Orden de compra · aprobación · estados | ✔ | 017 |
| Recepción | ◐ | 019 |
| Factura proveedor · three-way match | ✔ | 027 |
| CxP · pago · retención | ✔ | 028, 040 |

**Veredicto:** SUBSTANTIALLY_COMPLETE. Rompe en «revisar inventario/rotación» y en la profundidad de la recepción.

## P-03 Importación

| Etapa | Estado | Spec |
|---|---|---|
| INCOTERM · negociación | ✖ | 018 |
| Proforma · packing list · documentos de embarque · certificados | ✖ | 018, 046 |
| Anticipo / pago al proveedor | ◐ (pago genérico de CxP) | 028 |
| Seguimiento de embarque · agente | ✖ | 018 |
| Confirmación de despacho internacional | ✖ | 018 |
| Gestión de faltante o corrección documental | ✖ | 018, 020 |

**Veredicto:** NOT_STARTED. **Cadena rota desde la primera etapa.**

## P-04 Recepción

| Etapa | Estado | Spec |
|---|---|---|
| Confirmar arribo · programar descarga | ✖ | 019 |
| Recibir físicamente · bultos · pallets | ✖ | 019 |
| Comparar contra packing list / factura / orden | ◐ (solo contra orden) | 019, 027 |
| Inspección visual · daños · identificación | ◐ (`quality_status` binario) | 019 |
| Registrar faltante/sobrante/daño/referencia | ✖ | 020 |
| Evidencia de la incidencia | ✖ | 020, 046 |
| Escalar a Compras | ✖ | 020, 047 |
| Acta o registro de recepción | ◐ | 019 |
| Zona temporal de recepción | ✖ | 022 |

**Veredicto:** PARTIAL bajo. **Rompe en la primera etapa (arribo) y en toda la gestión de incidencias.**

## P-05 Confirmación de inventario recibido

| Etapa | Estado | Spec |
|---|---|---|
| Conteo detallado por SKU | ✖ | 021 |
| Comparación contra orden / packing / recepción física | ◐ (solo orden) | 021 |
| Validar descripción, referencia, presentación, unidad | ✖ | 011, 021 |
| Registrar ingreso · actualizar existencias | ✔ | 023 |
| Diferenciar recibido / disponible / pendiente / bloqueado | ✖ (entra directo a DISPONIBLE) | 021 |
| Tratamiento: ajuste / reclamo / investigación / cuarentena | ◐ (cuarentena existe, sin flujo de recepción) | 021, 025 |
| Confirmar y **liberar el lote** | ✖ | 021 |

**Veredicto:** SKELETON_ONLY. El motor de estados existe; el proceso que lo usa, no.

## P-06 Put-away (clasificación y ubicación)

| Etapa | Estado | Spec |
|---|---|---|
| Determinar zona por rotación/volumen/condiciones | ✖ | 008, 022 |
| Asignar zona/pasillo/rack/nivel/posición | ✖ | 008, 022 |
| Etiquetar · trasladar · confirmar colocación | ✖ | 022 |
| Registrar ubicación definitiva | ✖ (`location_id` nunca se escribe) | 022, 023 |
| Validar coincidencia física ↔ sistema | ✖ | 022 |
| Reubicar y corregir | ✖ | 022 |
| Liberar como disponible para despacho | ✖ | 021, 022 |

**Veredicto:** SKELETON_ONLY. **Ninguna etapa implementada.**

## P-07 Transferencia

| Etapa | Estado | Spec |
|---|---|---|
| Solicitud · salida · tránsito · recepción · diferencias | ✔ | 025 |

**Veredicto:** SUBSTANTIALLY_COMPLETE.

## P-08 Pedido (toma comercial)

| Etapa | Estado | Spec |
|---|---|---|
| Consultar disponibilidad | ◐ (existe consulta; no integrada al cotizar) | 023, 029 |
| Definir productos, cantidades, condiciones | ✔ | 029 |
| Condiciones comerciales desde maestro | ✖ | 012 |
| Registrar y **emitir** pedido | ◐ (existe orden, no pedido distinto) | 029 |
| Enviar a Almacén | ✖ | 031 |
| **Reserva de inventario** | ◐ (ocurre al aprobar crédito, no al emitir) | 030 |

**Veredicto:** PARTIAL. Decisión pendiente sobre el momento de reserva.

## P-09 Picking

| Etapa | Estado | Spec |
|---|---|---|
| Almacén recibe pedido · cola de preparación · prioridad | ✖ | 031 |
| Obtener ubicaciones de cada producto | ✖ | 031 |
| Organizar recorrido por secuencia de ubicación | ✖ | 031 |
| Almacenista recorre, identifica, verifica SKU y cantidad | ✖ | 032 |
| Marcar línea como preparada | ◐ (estado de picklist global) | 032 |
| Registrar diferencia / daño / no localizado | ✖ | 032 |
| Consolidar e identificar el pedido físicamente | ✖ | 032 |

**Veredicto:** SKELETON_ONLY. **Es el proceso más distintivo del negocio y el menos construido.**

## P-10 Confirmación de pedido

| Etapa | Estado | Spec |
|---|---|---|
| Área de confirmación recibe el pedido preparado | ✖ | 033 |
| Segundo chequeo físico producto por producto | ✖ | 033 |
| Confirmar referencias, cantidades, presentación | ✖ | 033 |
| No conforme → incidencia → regreso a preparación → reconfirmación | ✖ | 033 |
| Pedido formalmente confirmado | ✖ | 033 |

**Veredicto:** NOT_STARTED. **Etapa completa ausente. Es además un control de segregación de funciones.**

## P-11 Facturación

| Etapa | Estado | Spec |
|---|---|---|
| Liberación para facturación desde Confirmación | ✖ | 034 |
| Solicitud de facturación | ✖ | 034 |
| Verificar datos comerciales y fiscales | ✔ | 034, 039 |
| Generar factura (productos + servicios + mixta) | ✔ | 034 |
| **Asociar la factura al pedido** | ✖ | 034 |
| Emitir documento fiscal (correlativo, control, hash) | ✔ | 042 |
| Inmutabilidad y anulación | ✔ | 042 |

**Veredicto:** PARTIAL. La factura funciona; la compuerta y el vínculo no existen.

## P-12 Despacho

| Etapa | Estado | Spec |
|---|---|---|
| Verificar preparado + confirmado + facturado | ◐ (solo validación regulatoria) | 035 |
| Autorizar salida física | ✔ | 035 |
| Transportista · vehículo · conductor | ✔ | 044 |
| Dirección de entrega estructurada | ✖ (`destination` es texto) | 035 |
| Guía y bloqueo regulatorio | ✔ | 044 |
| Registrar salida · evidencia de entrega | ◐ (salida sí, POD no) | 035 |

**Veredicto:** PARTIAL.

## P-13 a P-21 (resumen)

| Proceso | Veredicto | Rompe en |
|---|---|---|
| P-13 CxC | ✔ SUBSTANTIALLY_COMPLETE | Gestión de cobranza/promesas |
| P-14 CxP | ✔ SUBSTANTIALLY_COMPLETE | Calendario de programación |
| P-15 Pago | ✔ SUBSTANTIALLY_COMPLETE | — |
| P-16 Cobro | ✔ SUBSTANTIALLY_COMPLETE | — |
| P-17 Devolución | ◐ PARTIAL | Etapa de inspección previa al reingreso |
| P-18 Nota de crédito | ✔ SUBSTANTIALLY_COMPLETE | — |
| P-19 Nota de débito | ✔ SUBSTANTIALLY_COMPLETE | — |
| P-20 Retención | ◐ PARTIAL | Conceptos no cargados; enteramiento |
| P-21 Regulatorio | ✔ SUBSTANTIALLY_COMPLETE | Matrices oficiales no cargadas |

## Resumen de procesos

| | Cantidad | Procesos |
|---|---:|---|
| **Completos** | 8 | P-07, P-13, P-14, P-15, P-16, P-18, P-19, P-21 |
| **Parciales** | 8 | P-01, P-02, P-04, P-08, P-11, P-12, P-17, P-20 |
| **Esqueleto** | 2 | P-05, P-06, P-09 (3 en realidad) |
| **No iniciados** | 2 | P-03, P-10 |

**La cadena crítica del negocio —importar, recibir, ubicar, preparar, confirmar, facturar,
despachar— tiene 7 de sus 10 eslabones incompletos o ausentes.**
