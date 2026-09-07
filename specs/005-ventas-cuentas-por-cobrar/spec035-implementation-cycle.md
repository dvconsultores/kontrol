# SPEC 035 — DESPACHO, TRANSPORTE Y REGULACIÓN · CICLO DE IMPLEMENTACIÓN

> 2026-09-06, sobre `255f039`. Ciclo completo desde `/speckit.specify`.
> **`MATERIAL OQ = 0`.** Y un hallazgo que cambia el sentido del ciclo: **la compuerta de despacho
> existía y no comprobaba nada.**

## 1. La fuente

**Proceso 9 · Despacho final**

| ¶ | Texto |
|---|---|
| 101 | El pedido facturado pasa a despacho. |
| 102-103 | **Se verifica que corresponda: Pedido preparado + Pedido confirmado + Factura emitida.** |
| 104 | Se **autoriza** la salida física de la mercancía. |
| 105 | Se entrega al transportista, cliente o responsable del traslado según el mecanismo utilizado. |
| 106 | La mercancía **sale del almacén con su factura**. |
| 107 | Se registra la salida/despacho. |

Seis etapas. El ¶103 enumera las **tres** compuertas, y las tres tienen hoy su autoridad
consultable: la preparación en la Spec 032, la confirmación en la 033 y la factura en la 034.

## 2. El hallazgo

`validate_shipment` —la función cuyo nombre y docstring prometen la validación documental— dice
esto:

> «Validación documental del despacho (FR-005-023/024). Si falta/venció/no coincide un requisito, el
> despacho queda BLOQUEADO (regulación funcional completa en Spec 008).»

Y su cuerpo entero es:

```python
if shipment.status != "DRAFT": raise ConflictError(...)
shipment.validation_status = "APPROVED"
shipment.status = "READY"
```

**Aprueba siempre.** No mira la factura, ni la confirmación, ni un solo permiso. Y mientras tanto
`regulatory.evaluate_shipment` —que sí resuelve los perfiles aplicables por producto y operación,
busca los documentos oficiales requeridos y devuelve `BLOCKED` con sus motivos— existe, funciona y
**nadie la llama** desde el despacho.

El ciclo no consiste en construir la compuerta: consiste en **conectarla**.

## 3. Dos defectos más en la salida física

`confirm_shipment` registra el movimiento de salida así:

```python
quantity=-line.quantity
```

| Defecto | Consecuencia |
|---|---|
| Usa `quantity`, no `base_quantity` | Despachar 2 cajas de doce descuenta **2**, no 24. Es la cadena caja×12 rota en su último eslabón |
| No indica estado de mercancía | Descuenta de `DISPONIBLE`, pero tras la Spec 032 la mercancía está en **`PREPARADO`** en el Área de Confirmación. Descontaría de una fila que ya no tiene esas unidades |

Ninguno se ve hoy porque el único camino probado crea el despacho desde existencia suelta, sin pasar
por la cadena. En cuanto la cadena existe —y desde la Spec 034 existe entera— los dos se disparan.

## 4. Lo que decide cada autoridad

| Pregunta del ciclo | Autoridad | Respuesta |
|---|---|---|
| §18 ¿Qué es despachar? | ¶106-107 | La mercancía sale del almacén y se registra la salida. `confirm_shipment` es ese acto |
| §17 ¿Cuándo `SHIPPED`? | ¶104-107 | Tras la salida física autorizada, no antes |
| §19 ¿Qué entidad? | Spec 005 | `Shipment` y `ShipmentLine` existen, con lote, serial, presentación, factor y cantidad base |
| §23 ¿Qué estado fiscal habilita? | ¶103 | **Factura emitida**, no generada. El ¶95 y el ¶97 son dos actos y el ¶103 exige el segundo |
| §34 ¿Qué transición de mercancía? | matriz `D0-10` fila 61: «`PREPARADO` → `DESPACHADO` → `VENDIDO` \| **035** \| Spec no construida» | Este ciclo activa `PREPARADO → DESPACHADO` |
| §39 ¿Cómo se sabe qué permisos aplican? | `regulatory._applicable_profiles` | Por perfil de empresa, operación y producto. No por el nombre del producto |
| §40-43 SICA / SIGESAI / SACS | Spec 044 | Cada requisito se evalúa por separado y **cualquiera** que falte o esté vencido bloquea |
| §50 ¿Verificación en línea? | maestro: «Sin API oficial: v1 no emite permiso» | Se registra, valida contra lo registrado, adjunta y bloquea. **No se emite ni se verifica en línea** |
| §21 ¿Despacho parcial? | ¶103 y `ADR-D0-012` | La cadena es completa por construcción: la 033 no confirma un pedido incompleto y la 034 no lo factura parcialmente. Sin autoridad para lo parcial, no se implementa |

### Por qué `DESPACHADO → VENDIDO` no se activa

La matriz se la asigna a la 035, pero el Proceso 9 termina en «la mercancía sale del almacén» y
«se registra la salida». Ninguna de sus seis etapas es «vendido». Activar una arista que ningún
evento del proceso escribe dejaría código muerto, que es lo que este tramo ha evitado en cada ciclo
—la 032 dejó `CONFIRMED` para la 033, la 033 dejó `READY_FOR_BILLING` para la 034—. Queda `DENIED`
hasta que una fuente declare su momento.

## 5. Lo que este ciclo construye

1. **La compuerta real** en `validate_shipment`: pedido facturado, confirmación vigente, factura
   emitida y evaluación regulatoria sin bloqueos. Las tres del ¶103 más la cuarta que el módulo
   regulatorio ya sabía calcular.
2. **La salida física correcta**: en cantidad **base** y desde el estado **`PREPARADO`**, con la
   arista `PREPARADO → DESPACHADO` que `D0-10` reservó para esta Spec.
3. Los datos de transporte exigidos antes de autorizar (¶105).
4. **La superficie de uso**: la cola de pedidos por despachar, el detalle del despacho y la
   pantalla que los recorre. Sin ella la compuerta existiría solo para quien llame a la API.

### Tres decisiones de la superficie, y por qué ninguna es material

| Decisión | Por qué no decide nada nuevo |
|---|---|
| La pantalla **no tiene campo de cantidad** | Es §21 llevado a la interfaz: sin autoridad para el despacho parcial, sale lo que la 032 consolidó. `_lineas_consolidadas` lo deriva del plan cerrado, en cantidad base, con lote y serial |
| El **almacén de origen no se pregunta** | La mercancía está consolidada en el del pedido. Elegir otro describiría un traslado que no ocurrió |
| El orden de la cola es por `invoiced_at` | Es **presentacional**. A diferencia de la cola de picking —donde `D0-15` tuvo que decidir quién recibe existencia escasa— aquí cada pedido ya tiene su mercancía apartada y consolidada: el orden no reparte nada |

El vehículo y el conductor salen de los maestros que el módulo regulatorio ya tenía
(`transport_vehicles`, `transport_drivers`), y se comprueba que sean de la empresa del despacho.
Ninguno es obligatorio: el ¶105 admite «transportista, cliente o responsable del traslado».

## 6. Fronteras

La 035 **no** recoge, no consolida, no verifica de nuevo, no factura, no emite permisos oficiales,
no simula verificación en línea y **no** implementa devoluciones: eso es de la Spec 036.

## 7. La separación que hay que conservar

`D0-07` sigue abierto y las Specs 039-043 siguen en `BLOCKED_BY_LEGAL_VALIDATION`. Este ciclo
certifica el despacho **técnica y funcionalmente**; **no** afirma homologación fiscal ni liberación
legal para producción. Y la Spec 044 sigue `BLOCKED_BY_EXTERNAL_SERVICE`: sin API oficial, la
validación es contra lo registrado, no contra la autoridad.
