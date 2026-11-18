# Spec · GOV-TRE-03 · Orden de pago desde obligación causada

- **Proceso:** TRE-03 · **Requisito:** GOV-TRE-003 (P0) · **Autorización:** encargo «P1 — GOV-TRE-03» de la dueña, 2026-11-17.
- **Entrada:** `7ef0c21`, alembic `0123_gov_bud09_causado`.
- **Normas:** N03, N05, N06, N24 (verificadas, A/B). Nada fuera de ellas se convierte en regla de plataforma.

## Propósito

Generar órdenes de pago **solo** desde causados BUD-09 formalizados y vigentes, con el expediente y la documentación exigidos por la política del ente, sin ejecutar el pago. TRE-03 es la frontera BUD-09 → TRE-03 → TRE-04.

## Historias

- **US1 (P1) Configurar.** Tesorería crea una política de órdenes de pago (criterio de tipo de gasto, documentos exigidos en la emisión, expediente completo sí/no, vigencia, fundamento, acto opcional) y la activa con fundamento y MFA. Configura el patrón de numeración. No hay políticas precargadas.
- **US2 (P1) Ordenar.** Tesorería ve las obligaciones causadas pendientes (causado, ordenado, pendiente, beneficiario, moneda), elige una o varias compatibles, fija el monto por obligación y la fecha de la orden, selecciona los documentos, guarda el borrador, revisa los controles, corrige y emite con MFA. Recibe el código y ve el nuevo pendiente de cada causado.
- **US3 (P1) Corregir.** Una orden emitida es inmutable; se anula con motivo, cargo con competencia y MFA, y el pendiente vuelve a cada causado.
- **US4 (P2) Consultar.** Lista con filtros (estado, fechas, beneficiario, moneda, causado, compromiso, texto), detalle con historia y CSV.

## Requisitos funcionales

- **FR-01** Fuente única: solo causados `FORMALIZADO` del mismo ente; borrador o anulado → 422.
- **FR-02** Por causado: `0 ≤ ordenado ≤ causado`; `pendiente = causado − Σ líneas de órdenes EMITIDAS`. Borradores y anuladas no consumen. Parciales y múltiples órdenes por causado.
- **FR-03** Una autoridad única del saldo ordenado (proyección neutral sobre los modelos), consumida por BUD-09, TRE-03 y, en el futuro, REP-05 y TRE-04. BUD-09 deja de publicar `monto_ordenado = 0`.
- **FR-04** Orden = cabecera + líneas (una por causado). Invariantes de la orden: misma empresa, mismo ejercicio, misma moneda, mismo beneficiario. Límite técnico: 100 líneas.
- **FR-05** El beneficiario sale de los causados (instantánea). Un borrador puede incluir causados sin beneficiario, pero la emisión se niega (FALTA_BENEFICIARIO). No se modifica el causado ni se inventa el beneficiario.
- **FR-06** Política versionada BORRADOR → VIGENTE → CERRADA, con `tipo_gasto` opcional (vacío = todos; si existe, debe coincidir con el tipo de gasto de la política de causado de cada línea), documentos exigidos (`EMISION`), `requiere_expediente_completo`, competencia (por defecto ORDENAR_PAGO × TESORERIA), vigencia, fundamento, `tipo_regla`, acto DOC-02 opcional. Activar exige fundamento y MFA.
- **FR-07** Documentos: cada tipo obligatorio de la política debe estar cubierto por un documento seleccionado, activo, con versión sha256, vinculado al ejercicio o ya congelado como evidencia de un causado de la orden (referencia, sin copiar archivos).
- **FR-08** Expediente completo (si la política lo exige): cada causado de la orden tiene al menos una evidencia BUD-09.
- **FR-09** Controles previos con mensajes concretos: COMPLETO, FALTA_DOCUMENTO, FALTA_EVIDENCIA, FALTA_BENEFICIARIO, FALTA_AUTORIDAD, SALDO_INSUFICIENTE, y además POLITICA, FECHA y COMPATIBILIDAD.
- **FR-10** Estados BORRADOR → EMITIDA → ANULADA. Sin PAGADA.
- **FR-11** Emisión en una transacción: bloquear la orden y los causados (FOR UPDATE, por id), recalcular el pendiente, validar la política, los documentos, el expediente, el beneficiario, la fecha, la autoridad y la SoD, numerar, congelar la instantánea y la huella, y auditar. `If-Match` obligatorio.
- **FR-12** Fecha: `fecha_orden ≥ max(fecha_efectiva)`, del año del ejercicio, y nunca futura. Se separan `fecha_orden`, `created_at` y `emitida_en`.
- **FR-13** Autoridad: cargo con ORDENAR_PAGO × TESORERIA (o la competencia de la política) en vigor **en la fecha de la orden**, autoridad funcional (ORG-06/ORG-04: ocupación, encargaduría y suplencia) y límite de monto con TRE-09 si la moneda difiere. Sin nombres de cargos.
- **FR-14** SoD CTL-01: proceso TRE-03 sobre el causado, con las acciones TRE03_CAUSAR → TRE03_ORDENAR. Solo bloquea si el ente tiene una regla vigente.
- **FR-15** Numeración configurable por ente (patrón con `{ANIO}` y `{NUMERO:n}`), única por empresa.
- **FR-16** Anulación con motivo de al menos 10 caracteres, cargo con la competencia en la fecha de anulación, permiso `cancel` y MFA. La orden queda; libera el pendiente. Frontera TRE-04: una orden con pagos no se anula (hoy, `monto_pagado = 0`, desde una sola proyección).
- **FR-17** Un causado con órdenes emitidas vigentes no se anula en BUD-09 (409).
- **FR-18** Instantánea al emitir: orden, fecha, beneficiario, moneda, monto, causados (código, monto asignado, compromiso, fuente), política y versión, documentos, evidencias, autoridad y regla SoD evaluada.
- **FR-19** Frontera TRE-04: `order_id`, `codigo`, beneficiario, moneda, monto ordenado, fecha, causados, expediente de origen, `monto_pagado`, `pendiente_de_pagar` y estado.
- **FR-20** Auditoría CTL-02 de borrador (creado y actualizado), emitida, anulada, política (creada, actualizada, activada y cerrada) y configuración.
- **FR-21** Menú Gobierno · Tesorería › «Órdenes de pago» y «Políticas de órdenes de pago», solo en las superficies GOBIERNO y MIXTO.

## Fuera de alcance

Ejecución del pago, cuenta bancaria, transferencias, cheques, conciliación (TRE-04); retenciones (TRE-05); asiento contable (ACC-02, N36); consumo de caja (TRE-02).

## Criterios de éxito

SC-01 Causado 100: las órdenes de 30 y 50 dejan 20, y una de 21 se rechaza. SC-02 Dos emisiones simultáneas nunca superan el causado. SC-03 Anular restituye el pendiente. SC-04 BUD-09 muestra el ordenado y el pendiente reales. SC-05 Cero hardcode institucional.
