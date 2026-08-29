# ADR-D0-012 — Confirmación independiente del pedido

| Campo | Valor |
|---|---|
| ID | D0-12 · Estado **APPROVED** (arquitectura) · política de segregación configurable |
| Fecha | 2026-08-29 |
| Responsable | Arquitecto de procesos · Auditor interno · Supervisor de almacén |
| Specs afectadas | **033** (propietaria) · 031, 032, 034, 035 |

## Problema

`ORDER_TRANSITIONS` (`sales/service.py:57`) va de `PREPARING` a `SHIPPED`. No existe estado
`CONFIRMED`, ni entidad de confirmación, ni compuerta hacia facturación. Búsqueda de
`confirmation`/`confirmacion` en los modelos: cero coincidencias.

## Por qué es más que una etapa

El documento no la describe como un paso administrativo sino como un **control independiente**:
*«Almacén prepara. Confirmación verifica. Facturación factura sobre un pedido previamente
confirmado.»* Es segregación de funciones. Su ausencia es una brecha de **control interno**, no solo
de funcionalidad: hoy quien prepara es efectivamente quien libera.

## Decisión

> **R-D0-12-1.** La confirmación es un **evento y una entidad distintos del picking**, con su propio
> actor, momento, resultado y evidencia. No es un campo booleano en el pedido ni un estado más de la
> lista de picking.
>
> **R-D0-12-2.** La confirmación compara el **pedido original** contra la **mercancía físicamente
> preparada**, verificando producto, SKU, cantidad, **presentación** (ADR-D0-009) y condición.
> La comparación es contra el pedido, no contra la lista de picking: comparar la preparación consigo
> misma no es un control.
>
> **R-D0-12-3.** Resultado **no conforme** → se registra incidencia con evidencia → el pedido vuelve
> a preparación → tras la corrección exige **nueva confirmación completa**, no parcial.
>
> **R-D0-12-4.** Resultado **conforme** → `CONFIRMED` → habilita `READY_FOR_BILLING`.
>
> **R-D0-12-5.** **Segregación configurable.** La política `same_user_allowed` es un dato por
> empresa y por proceso. KONTROL fija el **valor por defecto en `false`** para la confirmación
> respecto del picking, porque un control cuyo valor por defecto lo anula no es un control.
> Una empresa pequeña puede habilitarlo conscientemente; la decisión queda auditada.
>
> **R-D0-12-6.** **No se codifica la política de ningún cliente concreto.** Las reglas del proceso
> documentado son configuración de ese cliente, no reglas del producto.

## Máquina de estados

```
RESERVED → PREPARING → PREPARED → CONFIRMED → READY_FOR_BILLING → INVOICED → DISPATCHED → CLOSED
                ▲            │
                │            │ no conforme
                └────────────┘  (incidencia registrada; requiere reconfirmación)
```

`PREPARED` es nuevo y necesario: separa «el almacén terminó» de «control verificó». Sin él, la
confirmación no tendría un estado de entrada distinguible.

## Relación con las demás decisiones

| Decisión | Relación |
|---|---|
| ADR-D0-002 | La confirmación puede exigir aprobación cuando hay desviación autorizada |
| ADR-D0-009 | Verifica presentación, lo que exige que la línea la lleve |
| ADR-D0-010 | `PREPARADO` como estado de mercancía es el correlato físico de `PREPARED` |
| ADR-D0-011 | `CONFIRMED` es la condición de `order_id` facturable cuando la política lo exige |
| ADR-D0-008 | La incidencia de no conformidad lleva evidencia adjunta |

## Impacto

Frontend: pantalla de confirmación con lista de verificación línea a línea; registro de incidencia ·
Backend: entidad `OrderConfirmation` + `OrderConfirmationLine`; ampliación de la máquina de estados ·
DB: 2 tablas nuevas, 2 estados nuevos · QA: segregación activa impide confirmar al preparador;
no conforme devuelve y exige reconfirmación · Seguridad: control interno reforzado (P6) ·
Fiscal: la factura se apoya en un pedido verificado.

## Migración

**`SAFE_MIGRATION`** — aditiva. Los pedidos históricos, ya cerrados, no requieren confirmación
retroactiva. Los pedidos vivos en `PREPARING` al desplegar transitan a `PREPARED` y entran al nuevo
flujo.

## Criterios de aceptación

- [ ] La confirmación existe como entidad con actor, momento y resultado propios.
- [ ] Con segregación activa, el preparador no puede confirmar (probado).
- [ ] No conforme registra incidencia con evidencia y devuelve a preparación (probado).
- [ ] Facturar un pedido no confirmado es imposible cuando la política lo exige (probado).
- [ ] La política es dato por empresa; no hay ninguna regla de cliente en el código.

## Estado final

**APPROVED** — **CLOSED_WITH_CONFIGURATION_PENDING** (ver OQ-12).
