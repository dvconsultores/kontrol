# NEXT_VERTICALS — siguientes ciclos P3

Se derivan del DAG (`docs/roadmap/enterprise-application-completion/ENTERPRISE_COMPLETION_DAG.md`). Cada target es una vertical completa: backend, frontend, menú, permisos, auditoría, pruebas, E2E en PostgreSQL, Axe, responsive y tarjeta de la dueña. La prioridad y el orden finales los fija ChatGPT; la aceptación, la dueña.

**Antes de cualquier target:**
- **D0, paquete de decisiones de la dueña.** No es código; está listado en el DAG.
- **Entorno:** PostgreSQL de QA y dependencias instaladas. Este puesto no las tiene.

## NEXT_P3_TARGET_1 — V4 INVENTORY-LEDGER-VALUATION-INTEGRITY

- **Por qué primero.**
  - Es S1: hay pérdida de valoración y un recálculo de saldos sin permiso.
  - No tiene dependencias en el DAG.
  - Su núcleo no espera decisión: corregir la capa de la transferencia, el reverso simétrico, el permiso y la auditoría del recálculo, la acción `apply` del ajuste y el flujo FROZEN→COUNTING no exige elegir política.
- **Recorrido de la dueña.**
  1. Transferir entre almacenes con tránsito y recibir con diferencia, que va a cuarentena; la valoración del destino conserva el costo.
  2. Contar con congelamiento y aprobar el ajuste; aplicarlo desde la pantalla.
  3. Revertir un movimiento sin descuadrar estados ni capas.
- **Cierra:** D-INV-TRANSFER-COST, D-INV-REVERSE-STATE, D-INV-RECOMPUTE, D-INV-ADJ-NO-APPLY, D-INV-COUNT-STUCK, D-INV-TRANSFER-RECEIPT y D-APPROVAL-QTY-AS-VED.
- **Aparte:** D-INV-LEDGER-LOT es una migración: sub-vertical `CLAUDE_ONLY`.
- **Decisiones que no bloquean el núcleo:** INV-16 (valoración de RECHAZADO), INV-12 (destinos de devolución), INV-15 (backfill histórico).
- **Ejecución:** costeo y permisos son `CLAUDE_ONLY`. A DeepSeek solo van las tareas mecánicas de UI, con contrato cerrado.

## NEXT_P3_TARGET_2 — V1 FISCAL-EMISSION-INTEGRITY ◆

- **Por qué.** Hoy un número fiscal puede repetirse, una alícuota del 1 % cobrar el 100 % y una factura en USD figurar como bolívares. Es el núcleo no negociable del Volumen 1 §5.
- **Antes de empezar** necesita de D0:
  - la escala de tasa (porcentaje o fracción);
  - la anulación o no de una factura emitida.
- **Recorrido de la dueña.**
  1. Configurar serie, lote de control e imprenta.
  2. Emitir una factura desde un pedido confirmado: correlativo y control únicos aun bajo concurrencia, tasa snapshot en VES.
  3. Reimprimir con motivo.
  4. Emitir una nota de crédito limitada al saldo, por la única vía fiscal.
  5. Comprobar que el libro de ventas cuadra en bolívares.
  6. Cerrar el período y comprobar que bloquea.
- **Cierra:** D-FIS-NUM-RACE, D-FIS-CTRL-OVERLAP, D-RATE-SCALE, D-FIS-RATE-1, D-SALES-EMIT-BYPASS, D-FIS-NOTE-BYPASS, D-FIS-EMIT-ANY-STATE, D-FMA-VALIDITY, D-FIS-PRINT y D-PERIOD-NO-EFFECT.
- **Ejecución:** fórmulas, escala, redondeo y vectores los fija Claude antes de delegar nada (política de dinero y fiscal).

## NEXT_P3_TARGET_3 — V7 TREASURY-CASH-BANK-INTEGRITY

- **Por qué.** Hoy una caja puede cerrar con diferencia falsa, una transferencia puede debitar dos veces y una conciliación se aprueba sin cuadrar. La idempotencia de la ejecución no funciona: la clave no llega.
- **Recorrido de la dueña.**
  1. Abrir caja, registrar movimientos, arquear, pre-cerrar y cerrar con la diferencia recalculada.
  2. Depositar en banco con moneda validada.
  3. Transferir entre cuentas con conversión explícita.
  4. Conciliar con la resolución manual auditada y aprobar solo cuadrado.
  5. Cobrar en varias monedas con IGTF por regla.
- **Cierra:** D-TES-ARQUEO, D-TES-CCY, D-TES-TRANSFER, D-TES-RECON, D-TES-IGTF-500 y D-IDEMP (la parte de tesorería y la unicidad de claves).
- **Decisión de D0:** moneda funcional configurable.

## NEXT_P3_TARGET_4 — V6 TENANT-SCOPE-AND-SEGREGATION ◆

- **Por qué.** Hoy todo usuario ve todas las empresas del tenant: no se pueden declarar alcances. Además:
  - el pago a proveedor se autoaprueba;
  - un perfil de otra empresa bloquea el código;
  - el resolutor de aprobadores no filtra por tenant.
- **Antes de empezar** necesita de D0:
  - qué ve un usuario sin alcance declarado;
  - qué excepciones llevan maker-checker que no se puede apagar.
- **Recorrido de la dueña.**
  1. Crear un usuario con alcance a una empresa y un almacén, y comprobar que no ve otra empresa.
  2. Editar los permisos de un rol.
  3. Ver y revocar sesiones de otro usuario.
  4. Comprobar que un pago creado por A no lo puede aprobar A.
- **Cierra:** D-PROFILE-XCOMPANY, D-APPROVAL-ROLE-TENANT y D-PAY-SELF-APPROVE. Cubre SEG-03 y APR-05 y es prerrequisito del crédito de V3.
- **Ejecución:** `CLAUDE_ONLY` (aislamiento de tenant, permisos).

## NEXT_P3_TARGET_5 — V2 RECEIVABLES-PAYABLES-APPLICATION-INTEGRITY

- **Depende de:** V1 (retención y nota fiscal) y V7 (el pago pasa por tesorería).
- **Recorrido de la dueña.**
  1. Emitir una factura con vencimiento según la condición de pago.
  2. Cobrar parcialmente en otra moneda con diferencial.
  3. Aplicar un anticipo del mismo cliente: el de otro cliente se rechaza.
  4. Aplicar una retención sufrida una sola vez.
  5. Comprobar que una nota en borrador no baja el saldo.
  6. Comprobar que el aging y el estado de cuenta cuadran.
  7. En CxP: programar el pago, pagar por tesorería, aplicar y ver el aging correcto.
- **Cierra:** D-APPLY-UNCHECKED, D-WHT-REAPPLY, D-CXC-DRAFT-NOTE, D-CXP-POST-NO-TREASURY, D-CXP-AGING y D-CXC-DUE-DATE.
- **Corrige también dos TEST_DEFECT:** `tests/test_purchasing.py:265-273` y la simulación de `test_spec033`.

## Después

En este orden:
1. **V3** ORDER-TO-CASH-STATE-INTEGRITY.
2. **V5** PROCURE-TO-PAY-COMPLETION.
3. **V10** IMPORTS-OWNER-UAT-READY:
   - IMP-28;
   - IMP-21;
   - A11Y-IMPORT-SCROLL-REGIONS;
   - las zonas A–E, que decide el sponsor.
4. **V8** REGULATED-DISPATCH-MATCHING.
5. **V11** REPORTING-DASHBOARD-CURRENCY.
6. **V9** MASTERS-COMMERCIAL-COMPLETION.
7. **V12** SPEC057 Activos fijos.
