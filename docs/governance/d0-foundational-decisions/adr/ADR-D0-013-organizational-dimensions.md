# ADR-D0-013 — Dimensiones organizacionales por tipo de documento

| Campo | Valor |
|---|---|
| ID | D0-13 · Estado **APPROVED** · 2026-08-29 |
| Responsable | Arquitecto de datos · Contador público · Auditor interno |
| Specs afectadas | **007** (propietaria) · prácticamente todas las transaccionales |

## Problema

`cost_center_id` existe como `String(36)` **sin tabla destino y sin FK** en `purchase_requisitions`
y `user_scopes`. No hay `cost_centers` ni `business_units`. Y no está definido qué dimensiones debe
llevar cada documento: hoy cada módulo decide por su cuenta.

## Decisión

> **R-D0-13-1.** `CostCenter` y `BusinessUnit` son maestros con tabla propia, código, vigencia,
> jerarquía opcional y estado. `cost_center_id` pasa a ser FK real.
>
> **R-D0-13-2.** Las dimensiones aplicables a cada documento se declaran en la matriz siguiente.
> `O` = obligatorio · `C` = opcional configurable por empresa · `—` = no aplica.

| Documento | company | branch | establishment | warehouse | location | cost_center | business_unit |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Requisición de compra | O | O | — | C | — | **C** | C |
| Orden de compra | O | O | — | C | — | C | C |
| Expediente de importación | O | O | — | C | — | C | C |
| Recepción de mercancía | O | O | — | **O** | C¹ | C | C |
| Incidencia de recepción | O | O | — | O | C¹ | — | — |
| Movimiento de inventario | O | — | — | **O** | **O**¹ | C | C |
| Transferencia | O | — | — | **O** (origen y destino) | C¹ | — | — |
| Conteo / ajuste | O | — | — | O | C¹ | C | C |
| Cotización de venta | O | O | — | — | — | — | C |
| Pedido / orden de venta | O | O | C² | C | — | C | C |
| Lista de picking | O | — | — | **O** | **O**¹ | — | — |
| Confirmación de pedido | O | O | — | O | — | — | — |
| Despacho | O | O | — | **O** | — | — | — |
| **Factura de venta** | O | O | **O**² | — | — | C | C |
| Nota de crédito / débito | O | O | **O**² | — | — | C | C |
| Factura de proveedor | O | O | C | — | — | C | C |
| Pago / cobro | O | O | — | — | — | C | C |
| Sesión de caja | O | O | C | — | — | — | — |
| Documento fiscal | O | O | **O**² | — | — | — | — |

¹ Obligatorio cuando el almacén está declarado `location_managed` (ADR-D0-004 R-D0-04-3).
² El **establecimiento** es el lugar de emisión fiscal: determina serie, correlativo y lote de
control (Vol. 2 §3). Es obligatorio en todo documento fiscal, y ésta es la razón de que
«Establecimiento» exista como maestro y no como texto.

## Reglas

| ID | Regla |
|---|---|
| R-D0-13-3 | Ninguna dimensión organizacional puede ser texto libre ni identificador sin FK. |
| R-D0-13-4 | Toda dimensión de un documento debe pertenecer a la empresa del documento. Una referencia cruzada entre empresas es un fallo de aislamiento (P9, P11). |
| R-D0-13-5 | La obligatoriedad de las marcadas `C` es configuración por empresa; la de las marcadas `O` es regla del producto. |
| R-D0-13-6 | Las dimensiones se **congelan en el documento**. Reorganizar la empresa no reescribe documentos históricos (P5). |
| R-D0-13-7 | El alcance de usuario (`user_scopes`) se expresa sobre estas mismas dimensiones; no existe un segundo vocabulario de alcance. |

## Impacto

Frontend: pantallas de centros de costo y unidades de negocio; selector de dimensiones según el tipo
de documento · Backend: validación de pertenencia por dimensión · DB: 2 tablas nuevas, `cost_center_id`
pasa a FK, columnas nuevas donde la matriz las exige · QA: rechazo de dimensión de otra empresa ·
Seguridad: refuerza el aislamiento multiempresa · Fiscal: el establecimiento como lugar de emisión
queda formalizado.

## Migración

**`SAFE_MIGRATION`** para el esquema.
**`MANUAL_REVIEW_REQUIRED`** para `cost_center_id`: los valores de texto existentes deben revisarse
antes de convertirse en FK. Si no corresponden a ningún centro real, se conservan en `legacy_value`
y la FK queda nula. No se crean centros de costo inventados para que la migración cuadre.

## Criterios de aceptación

- [ ] `CostCenter` y `BusinessUnit` existen como maestros con pantalla de gestión.
- [ ] Cada documento exige exactamente las dimensiones de la matriz.
- [ ] Una dimensión de otra empresa se rechaza (probado).
- [ ] Todo documento fiscal tiene establecimiento.
- [ ] Reorganizar no altera documentos históricos (probado).

## Estado final

**APPROVED** — **CLOSED**.
