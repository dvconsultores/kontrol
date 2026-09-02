# D0-03 — OPCIONES DE DISPARADOR DE RESERVA

## 1. Nomenclatura atada a la máquina de estados

Cada opción se define por **la transición concreta** en la que nace la reserva. Sin esto, «liberar»,
«confirmar» y «emitir» significan cosas distintas según quién lea (ver current-state §3).

| Opción | Nombre | Transición del `SalesOrder` | Qué existe en ese momento |
|---|---|---|---|
| A | `RESERVE_ON_ORDER_CREATION` | creación en `DRAFT` (directa o por conversión de cotización) | Documento editable, sin compromiso |
| B | `RESERVE_ON_ORDER_CONFIRMATION` | `DRAFT → SUBMITTED` (emisión comercial: el vendedor confirma el pedido con el cliente; el documento deja de ser editable) | Compromiso comercial formal; crédito aún no evaluado |
| C | `RESERVE_ON_CREDIT_APPROVAL` | `CREDIT_PENDING → APPROVED` | Compromiso + crédito aprobado (**es lo que hace el código hoy**) |
| D | `RESERVE_ON_RELEASE` | `APPROVED → RELEASED` (liberación a preparación, entrada en cola de 031) | Todo lo anterior + el pedido va al almacén |
| E | `POLICY_DRIVEN_RESERVATION` | Configurable por empresa entre B, C, D (y otras) | — |
| F | Otra que la evidencia exija | Ninguna encontrada | — |

Nota: la «confirmación» de la opción B es la **emisión comercial del pedido**. No es la «confirmación
independiente» de ADR-D0-012/Spec 033, que ocurre tras el picking.

## 2. Evidencia que gobierna la comparación

| # | Evidencia | Fuente | A qué opción afecta |
|---|---|---|---|
| E1 | «determinar si **al emitir el pedido** el sistema reserva inmediatamente el inventario o solamente muestra una existencia disponible. Esta diferencia es crítica para evitar que dos vendedores comprometan el mismo stock» | DOCX Pedido §1 (citado en ADR v1) | El control de negocio se sitúa en la **emisión**; C y D dejan esa ventana abierta |
| E2 | La cotización nunca reserva; la conversión nunca reserva | FR-005-001 · FR-029-035 · prueba `test_convertir_no_reserva_inventario` | A viola la frontera de 029 |
| E3 | `DRAFT` es editable; `SUBMITTED` no | FR-005-011 · `QUOTE_EDITABLE`/estado de líneas | A bloquea stock por documentos que pueden no emitirse |
| E4 | «Pedido de contado» = pedido para el que 045 no abre solicitud; no existe atributo contado/crédito | current-state §5 | Un trigger distinto por tipo de pago **no tiene atributo sobre el que apoyarse**; C y B coinciden en el tiempo para contado |
| E5 | 031/032 asumen reserva firme al entrar en cola | ADR v1 «Por qué debe decidirse ahora» | D reserva justo antes del picking: la cadena comercial y de crédito corre sin protección |
| E6 | Backorder y sustitución son FUTURE | OQ-04 · POL-D0-002 §7 | Cualquier trigger posterior a la emisión descubre la insuficiencia **después** de haber comprometido al cliente, y sin backorder no tiene salida |
| E7 | Cambiar el disparador tras operar cambia la semántica de las reservas vivas | ADR v1 «Migración» | E multiplica esa fragilidad por empresa |
| E8 | La carrera de dos vendedores solo se cierra con bloqueo en BD, sea cual sea el trigger | concurrency-analysis | Neutral entre opciones; no discrimina |
| E9 | El pedido nace con origen comercial completo y condición de pago snapshot | Spec 029 | El compromiso comercial es verificable en `SUBMITTED` |
| E10 | Sin política de crédito, `ensure_approved` no bloquea | `approvals/integration.py:41-59` | Para contado, B ≡ C ≡ D en tiempo; la diferencia solo existe con crédito |

## 3. Matriz de decisión

Símbolos: ✔ favorable · △ mixto · ✘ desfavorable.

| Criterio | A Creación | B Confirmación | C Crédito aprobado | D Liberación | E Política |
|---|:-:|:-:|:-:|:-:|:-:|
| Evita sobreventa (dos vendedores) | ✔ | ✔ | ✘ ventana emisión→crédito (E1) | ✘ ventana mayor | △ depende del valor |
| No bloquea stock innecesariamente | ✘ borradores y conversiones (E3) | △ solo mientras se evalúa crédito, acotable por TTL | ✔ | ✔ | △ |
| Experiencia del cliente | ✘ | ✔ el vendedor sabe **al emitir** si hay stock | ✘ crédito aprobado y sin stock (E6) | ✘ ídem, más tarde | △ |
| Complejidad | △ | ✔ un punto, una regla | ✔ | △ nuevo evento | ✘ N máquinas de estado |
| Contado | ✘ | ✔ | ✔ (coincide con B, E10) | ✔ | △ |
| Crédito | ✘ | ✔ protege durante la evaluación; rechazo libera | ✘ pierde stock durante la evaluación | ✘ | △ |
| Cancelación | ✔ libera | ✔ libera | ✔ libera | ✔ libera | △ |
| Modificación | ✘ cada edición mueve reservas | ✔ solo en `DRAFT`, sin reserva; reemitir re-reserva | ✔ | ✔ | △ |
| Concurrencia | ✔ | ✔ | ✔ | ✔ | ✔ (E8) |
| Handoff a picking | ✔ | ✔ reserva firme mucho antes de 031 | ✔ | △ reserva y cola casi simultáneas | △ |
| Auditabilidad | ✔ | ✔ un trigger, un evento | ✔ | ✔ | ✘ trigger por reserva |
| Compatibilidad con el código actual | ✘ | ✘ mueve el punto | ✔ es el actual | ✘ | ✘ |
| Riesgo de migración | ✘ | △ SAFE + revisión de pedidos en vuelo | ✔ | △ | ✘ MANUAL_REVIEW por empresa |
| Configuración empresarial | ✘ | ✔ TTL y sobreventa siguen siendo configurables | ✔ | ✔ | ✔ pero sin backorder no es seguro cambiarla (E6) |

**Recuento** (solo orientativo; la decisión no es por puntuación): A 5✔/1△/8✘ · **B 12✔/2△/1✘** · C 8✔/0△/6✘ · D 7✔/4△/4✘ · E 2✔/9△/4✘.

## 4. Evaluación por opción

### A — Order Creation
- **Pros.** Riesgo nulo de venta doble desde el primer segundo.
- **Contras.** Un borrador es editable y puede no emitirse (E3). La conversión de cotización crearía
  reservas, violando FR-029-035 y una prueba verde (E2). Cada edición de línea implicaría mover reservas.
- **Riesgos.** Stock bloqueado por trabajo en curso de los vendedores; el inventario deja de reflejar compromisos reales.
- **Veredicto.** **Rechazada.**

### B — Order Confirmation (`DRAFT → SUBMITTED`)
- **Pros.** Es exactamente el punto que el negocio señala (E1). Primer estado con compromiso formal y
  documento no editable (la propia definición del defecto en ADR v1). El vendedor sabe al emitir si
  hay stock; la insuficiencia se resuelve editando el borrador, no inventando backorder (E6). Para
  contado coincide con C y D (E10). Para crédito protege al cliente durante la evaluación; el rechazo libera.
- **Contras.** Requiere mover el punto de disparo del código y revisar pedidos en vuelo en la migración.
  Bloquea stock mientras se evalúa el crédito: acotable con TTL opcional por empresa.
- **Riesgos.** Evaluaciones de crédito eternas reteniendo stock → mitigado por TTL configurable y por
  la cancelación explícita. Una empresa que prefiriera no retener stock durante el crédito no tiene
  opción: se acepta conscientemente (ver E).
- **Veredicto.** **ELEGIDA.**

### C — Credit Approval (`CREDIT_PENDING → APPROVED`)
- **Pros.** No retiene stock por pedidos que el crédito rechazará. Es el código actual: migración trivial.
- **Contras.** Deja abierta la ventana emisión → aprobación, que es la que el negocio quiere cerrar
  (E1). Si al aprobar no hay stock, el pedido está aprobado y no se puede cumplir: sin backorder no
  hay salida (E6). «Es lo que hay» no es una razón (§56 del prompt).
- **Riesgos.** Cliente con crédito aprobado y sin mercancía; dos vendedores con el mismo stock prometido.
- **Veredicto.** **Rechazada.**

### D — Release (`APPROVED → RELEASED`)
- **Pros.** Reserva solo lo que el almacén va a preparar de inmediato.
- **Contras.** Todo lo de C con una ventana aún mayor. La reserva nace instantes antes de la cola de
  picking: no protege la fase comercial ni la de crédito (E5).
- **Riesgos.** Los de C, amplificados.
- **Veredicto.** **Rechazada.**

### E — Policy Driven (configurable por empresa)
- **Pros.** Flexibilidad comercial; era la recomendación de ADR v1.
- **Contras.** Cada valor alternativo (C, D) es inseguro sin backorder (E6): configurarlo sería
  ofrecer una opción que el producto no puede cumplir. Multiplica máquinas de estado, liberaciones y
  pruebas. Cambiar el valor en una empresa operando reinterpreta reservas vivas (E7). La razón de v1
  («un producto no puede imponer el momento») se responde así: el producto **sí** impone la semántica
  de sus estados (cotización, aprobación, mercancía); lo que no impone es la política de crédito, la
  vigencia ni la sobreventa, que siguen siendo configurables.
- **Riesgos.** Contrato no implementable por 030 sin resolver primero cuál valor usa cada empresa —
  exactamente el bloqueo que Master 56 detectó.
- **Veredicto.** **Rechazada para 030.** Reabrible solo si backorder entra en alcance (FUTURE).

### F — Alternativas exigidas por la evidencia
Se buscó una: reservar al emitir **solo para contado** y al aprobar para crédito. No hay atributo
contado/crédito en el pedido (E4); la única señal es que 045 abra o no solicitud, y eso se conoce en
la misma transición `SUBMITTED → CREDIT_PENDING`. Sería la opción E con otro nombre y el mismo
problema de E6. **No procede.**

## 5. Conclusión

`RESERVATION TRIGGER = ORDER_CONFIRMATION` — transición `DRAFT → SUBMITTED`, fija para todo tipo de
pedido. Detalle en `d0-03-reservation-decision.md`.
