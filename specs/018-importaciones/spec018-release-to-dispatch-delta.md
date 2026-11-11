# Spec 018 · delta: liberar para preparación y despacho (§4)

Encargo `SPEC018_RELEASE_TO_PREPARATION_AND_DISPATCH`, del 2026-11-10. Spec dueña: 018. Evidencia: `evidence/release-to-dispatch/`.

## Requisito

DOCX §4, «Liberar para preparación y despacho». La matriz lo tenía PARTIAL porque la «disponibilidad no [estaba] verificada en un pedido»: la E2E llegaba a la mercancía ubicada y no seguía hasta el despacho.

## Decisiones

- **RTD-01. No hay estado de liberación nuevo.** Ni un estado de mercancía (`INVENTORY_RELEASED` o similar) ni un botón «Liberar». La mercancía importada se puede vender por los contratos que ya existen:
  - confirmación (Spec 021);
  - estado `DISPONIBLE`, el único de `SELLABLE_STATES` y de `RESERVABLE_STATES` en `app/modules/inventory/states.py`;
  - pedido `RELEASED` (Spec 030), que es el traspaso a picking y no un estado de inventario.
- **RTD-02. D0-14 se cumple.** Pasar de la ubicación nula a una física, y reubicar después, no vuelve invendible la mercancía.
- **RTD-03. La salida es la transición terminal PREPARADO → DESPACHADO** (Spec 035, D0-10). El saldo despachado sigue registrado en el almacén con ese estado y deja de ser vendible.
- **RTD-04. Deuda abierta DISPATCH-COST-RELIEF** (decisión de la dueña, 2026-11-10). La salida no consume capas de costo y no lleva costo propio, así que lo despachado sigue en la valoración y no hay costo de ventas. Resolverlo es una decisión material, fuera de este delta:
  - el método de consumo;
  - el costo de ventas;
  - si lo DESPACHADO sigue en custodia;
  - el cruce entre las Specs 023, 034 y 035.

  La E2E solo afirma que el despacho no destruye la valoración.

## Alcance

No se cambian el producto, el esquema ni la API. El delta se cierra con evidencia de extremo a extremo, extendiendo la E2E dueña `resources/frontend/e2e/importaciones.spec.ts`.

**Fuera de alcance, y abiertos:**
- IMPORT-PUTAWAY-ATRIBUCION;
- las zonas A a E (pendientes de validar por el sponsor);
- el suministro abierto por almacén;
- DISPATCH-COST-RELIEF.

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T018-RTD-A Extender la E2E: importación → venta → despacho | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `e2e/importaciones.spec.ts` | la propia E2E | PASS en Chrome sobre PostgreSQL a 1280, 390 y 320 |
| T018-RTD-B Ajustar la E2E al contrato medido (estados, movimientos, 409) | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `e2e/importaciones.spec.ts` | la propia E2E | PASS, typecheck y lint limpios |
| T018-RTD-C Medición, decisión de costo, matriz, tarjeta y evidencia | CLAUDE | n-a | NO | n-a | n-a | documentos | — | matriz recontada, deuda registrada |
