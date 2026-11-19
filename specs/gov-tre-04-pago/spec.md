# Spec · GOV-TRE-04 · Pago con maker-checker, medios autorizados y bloqueo de duplicados

- **Proceso:** TRE-04 · **Requisitos:** GOV-TRE-004, GOV-TRE-005, GOV-TRE-010 (P0) · **Autorización:** encargo «P1 — TRE-04 · PAGO CON MAKER-CHECKER, MEDIOS AUTORIZADOS Y BLOQUEO DE DUPLICADOS» de la dueña, 2026-11-18.
- **Entrada:** `250227c`, alembic `0125_gov_tre03_orden_pago`.
- **Normas:** N05 (A), N20 (A), N23 (A) para las invariantes; N37 (C, normativa local) solo como **dato del ente**, versionado y con procedencia. Ver `evidence/N37_VALIDATION.md`.

## Propósito

Pagar una orden de pago TRE-03 **emitida**: preparar el pago (maker), autorizarlo (uno o más checkers con autoridad real), registrar su ejecución externa y llevar el monto pagado canónico de la orden, sin duplicados ni sobrepagos, bajo una política de pago versionada del ente. TRE-04 no envía nada al banco, no retiene (TRE-05), no concilia (TRE-06), no reversa pagos ejecutados (TRE-07) y no contabiliza (ACC).

## Historias

- **US1 (P1) Configurar.** Tesorería registra los medios de pago del ente (código, nombre, vigencia, si exige referencia externa, si es única y su formato opcional, procedencia) y crea una política de pago: moneda, medios permitidos, pago parcial sí/no, bandas de aprobación por monto con sus requisitos de autoridad (competencia × cantidad), competencia opcional del preparador, restricción de cargos autorizados en la cuenta, documentos por etapa, control de duplicado funcional (bloquear o advertir), vigencia, fundamento y clase de regla. La activa con MFA; la cierra; crea una versión nueva. Configura la numeración. Nada precargado.
- **US2 (P1) Preparar.** El maker elige una orden emitida con saldo (ve ordenado, pagado, en trámite y disponible), la política, la cuenta TRE-01, el medio, el monto y los documentos; guarda el borrador (no consume); revisa los controles y lo envía a autorización (reserva el monto y congela la política).
- **US3 (P1) Autorizar.** Cada checker declara el cargo con el que actúa y el requisito de la banda que cubre; el sistema valida competencia en vigor, autoridad funcional, límite y, si la política lo pide, que el cargo esté autorizado en la cuenta. El maker nunca autoriza su propio pago. Al completar las aprobaciones exigidas, el pago queda AUTORIZADO. Un checker puede rechazar con motivo.
- **US4 (P1) Registrar la ejecución.** Tesorería registra que el pago se ejecutó fuera de KONTROL (fecha valor, referencia externa según el medio, documentos de la etapa), con MFA. Sube el pagado de la orden y baja su pendiente.
- **US5 (P2) Anular antes de ejecutar y consultar.** Anular un borrador, o un pago pendiente/autorizado con motivo y MFA (libera la reserva). Lista con filtros, CSV y detalle con historia completa.

## Requisitos funcionales

- **FR-01** Solo órdenes TRE-03 `EMITIDA` del mismo ente.
- **FR-02** Autoridad única del saldo pagable en `proyeccion_obligaciones.py`: `monto_pagado = Σ pagos REGISTRADO`, `en_tramite = Σ PENDIENTE_AUTORIZACION + AUTORIZADO`, `pendiente_de_pagar = ordenado − pagado`, `disponible_para_pago = ordenado − pagado − en_tramite`. Ni el frontend ni los reportes vuelven a sumar.
- **FR-03** Estados: BORRADOR → PENDIENTE_AUTORIZACION → AUTORIZADO → REGISTRADO; BORRADOR → ANULADO; PENDIENTE_AUTORIZACION → RECHAZADO; PENDIENTE_AUTORIZACION/AUTORIZADO → ANULADO. El borrador no consume; pendiente y autorizado reservan; registrado consume; rechazado y anulado liberan. Solo el borrador se edita; REGISTRADO, RECHAZADO y ANULADO son inmutables.
- **FR-04** Sobrepago: ningún envío ni registro deja `pagado + en_tramite > ordenado` (409 `GOV_PAYMENT_OVERPAYMENT`), con la orden bloqueada `FOR UPDATE`. Dos envíos simultáneos nunca suman más que el ordenado (prueba en PostgreSQL).
- **FR-05** Pago parcial solo si la política lo permite; si no, el monto debe ser el disponible completo (422 `GOV_PAYMENT_PARTIAL_NOT_ALLOWED`). Varios pagos por orden.
- **FR-06** Moneda: pago = orden = política = cuenta. Sin conversión.
- **FR-07** Cuenta TRE-01 del mismo ente, `VIGENTE` y en vigor en la fecha.
- **FR-08** Medio de pago del catálogo del ente, `ACTIVO`, en vigor y permitido por la política congelada.
- **FR-09** Política versionada BORRADOR → VIGENTE → CERRADA; editar solo en BORRADOR; nueva versión desde una VIGENTE o CERRADA (mismo código, `numero_version + 1`); activar la nueva cierra la anterior. Activar exige fundamento, ≥ 1 medio, bandas contiguas desde 0 y MFA.
- **FR-10** Al enviar se congelan `policy_id`, `numero_version` y una instantánea con medio, banda aplicable y requisitos, documentos y controles. Aprobar y registrar usan la instantánea, nunca la política actual.
- **FR-11** Bandas: `monto > desde` y (`hasta` nulo o `monto ≤ hasta`); requisitos `[{accion, materia, cantidad}]` del catálogo ORG-03; aprobaciones exigidas = Σ cantidad.
- **FR-12** Maker ≠ checker (invariante de plataforma, N05 y GOV-TRE-004), por identidad (`usuarios_equivalentes`), no solo por `user_id`; checkers distintos entre sí (422/409 `GOV_PAYMENT_MAKER_CHECKER`).
- **FR-13** Checker: cargo declarado con la competencia del requisito en vigor en la fecha de aprobación (`_autoridad_valida`), autoridad funcional ORG-06/ORG-04 (`exigir_autoridad_funcional`: ocupación, encargaduría, suplencia, delegación) y límite de la competencia (`verificar_limite`). Si la política lo exige, el cargo está autorizado en la cuenta (TRE-01). Se guardan actor, cargo, funcionario, requisito, decisión, fecha y versión de la política.
- **FR-14** Preparador: si la política fija una competencia de preparación, el envío exige un cargo con ella y autoridad funcional.
- **FR-15** Duplicados: (a) idempotencia de creación y de registro por `idempotency_key`; (b) referencia externa única por (ente, medio) cuando el medio lo exige, en servicio y con índice único parcial; (c) duplicado funcional (misma orden e importe entre pagos activos): la política decide BLOQUEAR (409 `GOV_PAYMENT_DUPLICATE`) o ADVERTIR (el envío exige confirmar con motivo, que queda en la historia).
- **FR-16** Referencia externa: obligatoria, única y con patrón opcional según el medio; no hay formato bancario fijo.
- **FR-17** Documentos por etapa (PREPARAR, AUTORIZAR, REGISTRAR, ANULAR) desde la política congelada; vale el documento activo con versión sha256 vinculado al ejercicio de la orden o congelado en la orden.
- **FR-18** MFA en autorizar, rechazar, registrar, anular un pago enviado, y activar o cerrar una política.
- **FR-19** CTL-01: proceso `TRE-04` sobre la orden de pago (TRE04_ORDENAR → TRE04_AUTORIZAR): un ente puede impedir que quien emitió la orden autorice su pago. Es otro conflicto que maker ≠ checker; nunca dos eventos para el mismo.
- **FR-20** TRE-03: una orden con pagos registrados o en trámite no se anula (409); el detalle de la orden muestra pagado y pendiente reales.
- **FR-21** Auditoría CTL-02 de medios, política, configuración y cada transición del pago. Historia append-only visible en el detalle.
- **FR-22** Aislamiento: otra empresa recibe 404 al leer, editar, autorizar, registrar o anular.
- **FR-23** Menú Gobierno · Tesorería › «Pagos» y «Políticas de pago».

## Fuera de alcance

Integración bancaria (`BANK_API_INTEGRATION=OUT_OF_SCOPE`), reverso de pago ejecutado (TRE-07), retenciones (TRE-05), conciliación (TRE-06), asiento contable (`ACCOUNTING_ENTRY=OUT_OF_SCOPE`), conversión de moneda.

## Criterios de éxito

SC-01 Orden 100: 40 + 30 + 30 deja pendiente 0; 31 sobre 30 se rechaza. SC-02 Dos envíos de 70 en paralelo sobre 100: uno pasa. SC-03 El maker no autoriza su pago. SC-04 El monto elige la banda. SC-05 Un pago congelado en v1 sigue en v1 tras activar v2. SC-06 Referencia repetida bloqueada. SC-07 Cero hardcode institucional.
