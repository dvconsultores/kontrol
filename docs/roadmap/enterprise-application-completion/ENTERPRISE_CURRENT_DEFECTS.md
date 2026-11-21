# KONTROL Enterprise · defectos de producto vigentes

Ciclo `P3-ENTERPRISE-REBASELINE-AND-COMPLETION-MATRIX` · 2026-11-20 · HEAD `b726c1da` (más `b3b53046`, herramientas).

**Qué es este registro.** Defectos demostrados leyendo el código del HEAD, deduplicados: un defecto que afecta a varias filas de la matriz aparece una sola vez, con sus filas.
- Detalle por fila: `specs/enterprise-rebaseline/evidence/PRODUCT_DEFECTS.md`.
- Matriz: `ENTERPRISE_REQUIREMENTS_REBASELINE.csv`.

**Cómo se verificó.**
- `V` = Claude lo verificó leyendo el código.
- `A` = lo confirmó el auditor por lectura.
- Ningún defecto se reprodujo ejecutando: este puesto no tiene PostgreSQL ni dependencias. El ciclo que lo corrija debe empezar con la prueba en rojo.

**Prioridad.** Todos son P0 (`PRODUCT_DEFECT`, regla §31 del encargo). Dentro de P0:
- **S1:** integridad monetaria o fiscal, seguridad, aislamiento o doble contabilización.
- **S2:** el proceso no se puede completar o el resultado mostrado es falso.
- **S3:** menor o de superficie.

**Clasificación:** todos son `PRODUCT_DEFECT` salvo indicación. Los marcados `CLAUDE_ONLY` (fiscal, dinero, seguridad, tenant) no se delegan a DeepSeek.

## S1 — integridad fiscal, monetaria y de seguridad

| ID | Defecto | Filas | Ubicación | Ver. | Política |
|---|---|---|---|---|---|
| D-FIS-NUM-RACE | El correlativo fiscal y el número de control se asignan sin bloqueo de fila, y la BD no tiene unicidad: dos emisiones concurrentes pueden repetir número | FMA-06, FIS-01, FIS-10 | `fiscal/service.py:194-202`, `:238-245`; migración `0007` | V | CLAUDE_ONLY |
| D-FIS-CTRL-OVERLAP | Los rangos de lotes de control pueden solaparse: el mismo número de control puede existir dos veces | FMA-07, FIS-10 | `fiscal/service.py:208-231` | A | CLAUDE_ONLY |
| D-RATE-SCALE | La tasa se lee como porcentaje si es mayor que 1 y como fracción si no: una alícuota o retención del 1 % se cobra al 100 % y la del 0,5 % al 50 %. El cálculo se hace en float | FMA-02, FMA-03, FMA-04, CMP-15, TRV-05 | `fiscal/service.py:167`, `:458` | V | CLAUDE_ONLY. Decide la dueña: porcentaje o fracción |
| D-FIS-RATE-1 | Todo documento fiscal se guarda con `exchange_rate_snapshot=1.0`: en el libro, una factura en USD figura como bolívares | FIS-06, TRV-09, VEN-11 | `fiscal/service.py:354`, `:551`; `sales/service.py:2091` | V | CLAUDE_ONLY |
| D-SALES-EMIT-BYPASS | La pantalla de facturas crea una factura libre y la pasa a EMITTED por la transición genérica, sin correlativo ni número de control, y abre la CxC | VEN-10, PED-08, FIS-01 | `sales/service.py:2668-2678`; `sales/api.py:916-926`; `FacturasVentasPage.tsx:94-106` | V | CLAUDE_ONLY |
| D-FIS-NOTE-BYPASS | Dos vías paralelas de notas de crédito sin documento fiscal: `/fiscal/credit-debit-notes` (EMITTED sin numeración, solo limita el total) y la heredada `/sales/credit-notes` (número y monto libres, se aplica a la CxC) | FIS-03, VEN-14 | `fiscal/service.py:401-416`; `sales/api.py:939-967` | A | CLAUDE_ONLY |
| D-FIS-EMIT-ANY-STATE | `/fiscal/documents/emit` numera documentos en cualquier estado, también borradores o anulados | FIS-01 | `fiscal/service.py:268-277`, `:330-332` | A | CLAUDE_ONLY |
| D-APPLY-UNCHECKED | El motor de aplicaciones compartido entre CxC y CxP aplica cobros, pagos, anticipos y notas sin validar tercero, estado (DRAFT o REJECTED), dirección, tipo de destino ni moneda | CXC-02..04, CXC-10, VEN-13, CXP-01, CXP-05 | `purchasing/service.py:2315-2325`, `:2353-2390` | A | CLAUDE_ONLY |
| D-WHT-REAPPLY | Lo disponible de una retención nunca baja: la misma retención se aplica varias veces. REVERSADA no tiene transición de entrada | CMP-15, CXP-05, CXC-08, FIS-04 | `purchasing/service.py:181-189`, `:2326-2350` | A | CLAUDE_ONLY |
| D-CXC-DRAFT-NOTE | Una nota de crédito en DRAFT reduce el saldo del cliente y se puede aplicar | VEN-14, CXC-01, CXC-04 | `sales/service.py:2728-2800`, `:2842`, `:2879` | V | CLAUDE_ONLY |
| D-CXP-POST-NO-TREASURY | Un pago pasa a POSTED por la transición genérica sin movimiento de caja ni banco | CXP-03 | `purchasing/service.py:172-179`; `api.py:1194-1201` | A | CLAUDE_ONLY |
| D-PAY-SELF-APPROVE | El pago a proveedor no impide que quien lo crea lo apruebe. La contingencia regulatoria la autoriza quien la crea. Por defecto, el motor permite autoaprobar | APR-05, CXP-07 | `purchasing/service.py:2278-2286`; `regulatory/service.py:321`; `approvals/models.py:56-57` | V | CLAUDE_ONLY |
| D-ORDER-BYPASS | La transición genérica del pedido fija estados no delegados (INVOICED→SHIPPED sin despacho, sin salida de inventario y con la reserva viva) | VEN-06, PED-09 | `sales/service.py:901-933`, `:124` | V | — |
| D-ORDER-CANCEL-INVOICED | Se permite INVOICED→CANCELLED sin anular la factura ni la CxC | VEN-06 | `sales/service.py:124`, `:821-840` | V (máquina) | CLAUDE_ONLY |
| D-SHIP-CLIENT-LINES | El despacho acepta líneas del cliente sin cruzarlas con lo consolidado ni con lo facturado | VEN-08, PED-09 | `sales/api.py:131`; `sales/service.py:2359` | A | — |
| D-PROFILE-XCOMPANY | La comprobación de solape de perfiles no filtra por empresa: un perfil de otra empresa bloquea el código y revela que existe | PRD-11, FMA-01 | `master_data/service.py:166-176` | V | CLAUDE_ONLY (tenant) |
| D-APPROVAL-ROLE-TENANT | El resolutor de aprobadores busca roles por código sin filtrar por tenant: puede elegir el rol de otro tenant y dejar la aprobación sin aprobadores | APR-* | `approvals/service.py:266` | A | CLAUDE_ONLY (tenant) |
| D-IDEMP | El frontend manda `Idempotency-Key` como cabecera y tesorería y fiscal la leen del cuerpo: la clave nunca llega. Las claves de factura, movimiento, factura de proveedor y pago no son únicas | TRV-01 | `api/client.ts:226-227`; `treasury/api.py:236`; `fiscal/api.py:102`; migraciones `0003/0004/0005` | V | CLAUDE_ONLY (idempotencia) |
| D-APPROVAL-QTY-AS-VED | Las aprobaciones de inventario y compras envían una cantidad como si fuera un importe en VED | TRV-11 | `purchasing/service.py:1536-1538` | A | CLAUDE_ONLY |
| D-TES-IGTF-500 | Un IGTF en moneda extranjera sin tasa responde 500, y toma la última tasa sin mirar la fecha | FMA-05, TES-08 | `treasury/service.py:156-166`, `:927-928` | V | CLAUDE_ONLY |
| D-TES-CCY | Las transacciones bancarias no se validan contra la moneda de la cuenta, el saldo suma monedas distintas y la comisión no afecta el saldo | TES-02, TES-03, TES-09 | `treasury/service.py:536-551`, `:1037-1051` | A | CLAUDE_ONLY |
| D-TES-TRANSFER | Una transferencia admite caja y cuenta de origen a la vez (doble débito), origen igual a destino y monedas distintas sin conversión | TES-04, TES-05 | `treasury/service.py:680` | A | CLAUDE_ONLY |
| D-TES-ARQUEO | Se admiten movimientos después del arqueo, pero el cierre usa la diferencia congelada. Además puede haber dos sesiones abiertas de la misma caja | TES-01 | `treasury/service.py:412`, `:490` | A | CLAUDE_ONLY |
| D-TES-RECON | La conciliación se aprueba con líneas sin emparejar y sin cuadre. La resolución manual no se audita y no valida la empresa del movimiento | TES-06 | `treasury/service.py:815-861` | A | CLAUDE_ONLY |
| D-DISCOUNT | `requires_approval` del descuento se descarta, así que nunca se abre la solicitud. El descuento se valida como porcentaje y se resta como importe | COM-08, VEN-04, PED-01 | `sales/service.py:347`, `:430`, `:579`, `:2101-2102` | A | CLAUDE_ONLY (dinero) |
| D-FMA-VALIDITY | La regla de retención ignora su vigencia. El solape de reglas fiscales se comprueba solo en el borrador y solo si trae `effective_from` | FMA-03, FMA-04, FMA-10 | `fiscal/service.py:105-130`, `:441-448` | A | CLAUDE_ONLY |
| D-DASH-CCY | El dashboard suma importes de monedas distintas sin conversión, moneda ni período | INI-01, INI-02 | `reporting/service.py:62-91` | A | CLAUDE_ONLY (moneda) |

## S2 — el proceso no se completa o muestra un resultado falso

| ID | Defecto | Filas | Ubicación | Ver. |
|---|---|---|---|---|
| D-IMP-PARTIAL-ACCEPTED | El expediente muestra «Mercancía recibida y ubicada» con una recepción PARTIALLY_ACCEPTED sin confirmar | IMP-28 | `imports/service.py:1227-1235`, `:1663` | V |
| D-PICK-CORRECTION-DEADEND | Un pedido rechazado en confirmación o con faltante en picking queda varado en PREPARING sin camino de vuelta a confirmación. Además, TEST_DEFECT: `test_spec033_confirmation.py:343-346` simula la corrección escribiendo el estado a mano | PED-06, PED-04 | `sales/service.py:1302`, `:1490` | A |
| D-INV-LEDGER-LOT | El ledger no guarda lote ni serial: el saldo por lote o serial no se puede reconstruir y el picking no los confirma | INV-01, INV-10, INV-11 | `inventory/models.py:71` | A |
| D-3WAY-TAX | La conciliación triple pone `variance_tax` igual al impuesto de la línea: toda factura con IVA cae en EXCEPTION. La variación de cantidad se mide contra lo acumulado de la orden. EXCEPTION→APPROVED no exige resolución ni se audita | CMP-14 | `purchasing/service.py:2120-2137`, `:161`; `api.py:1063-1076` | V |
| D-PO-SYNC | La orden queda RECEIVED si la suma recibida alcanza la pedida, aunque una línea siga sin recibir | CMP-07 | `purchasing/service.py:1665-1676` | A |
| D-CXP-AGING | Un documento sin vencimiento cae en «90+», y la API nunca fija vencimiento. Lo no vencido se cuenta como «Vencido 0-30» | CXP-06 | `purchasing/service.py:2455-2456`; `CuentasPorPagarPage.tsx:148` | V |
| D-CXC-DUE-DATE | El vencimiento de la CxC es la fecha de emisión e ignora la condición de pago congelada | VEN-12 | `sales/service.py:2662`, `:4078` | A |
| D-RET-LINE | La línea de devolución de compra no valida empresa del producto ni cantidad mayor que cero | CMP-16 | `purchasing/service.py:2196-2202` | A |
| D-REG-GUIDE | La evaluación regulatoria usa la última guía válida del tipo para cualquier despacho y no cruza producto, lote, cantidad, origen, destino, vehículo ni conductor. Anular el bloqueo no libera el despacho ni se audita | REG-01, REG-04 | `regulatory/service.py:270-279`, `:300-308`; `sales/service.py:2424` | V (override) |
| D-REG-PROFILE | Un perfil regulatorio acotado por rubro, origen o destino se aplica a todo. La vigencia se ignora y la versión se ordena como texto | REGM-04 | `regulatory/service.py:235-240` | A |
| D-REG-HASH | El hash del documento oficial se calcula sobre los campos del registro, no sobre el archivo. Registrarlo no se audita | REG-07 | `regulatory/service.py:212-228` | A |
| D-RPT-JOB | El trabajo de reporte asíncrono descarta el resultado y apunta a un archivo inexistente | RPT-03 | `reporting/service.py:346-361` | A |
| D-PERIOD-NO-EFFECT | Cerrar un período fiscal no bloquea nada. Reabrirlo no exige un segundo aprobador ni se audita | ORG-08, FIS-07 | `fiscal/service.py:501-518` | A |
| D-RIF | El RIF se normaliza con o sin guiones según el tipo de persona: el mismo RIF entra dos veces | TER-01, TER-02 | `master_data/service.py:30-48`; `party_service.py:96` | V (normalización) |
| D-CUST-DECORATIVE | La ficha del cliente edita lista, condición, vendedor, zona y crédito como texto que ningún proceso lee. El endpoint real no tiene pantalla | TER-03, COM-01 | `TerceroExtensiones.tsx:38-43`; `commercial/service.py:369` | A |
| D-PRICE-LIST | La lista de precios por cliente nunca se aplica: Ventas pasa `party_id` como `customer_id` | COM-01 | `sales/service.py:297`; `commercial/service.py:368-371` | A |
| D-PRD-ROUTE | «Ver» producto lleva a NotFound y la pantalla de presentaciones es inalcanzable | PRD-15, PRD-09 | `ProductosPage.tsx:38`; `router.tsx:65-68` | V |
| D-SERVICES-LIST | Productos lista también servicios. Servicios filtra en el navegador sobre la primera página mixta | PRD-03 | `ProductosPage.tsx:23-24`; `ServiciosPage.tsx:21-22` | A |
| D-UOM-LEGACY | Las conversiones se crean por la ruta heredada, sin misma dimensión, sin auditoría y sin vigencia | PRD-10 | `CatalogosPage.tsx:38`; `master_data/api.py:409-433` | A |
| D-WIZARD | Los pasos 2 a 4 del asistente de producto son texto fijo y `inventory_profile_id` siempre es nulo | PRD-14 | `ProductoNuevoPage.tsx:29`, `:116-132` | A |
| D-FIS-PRINT | Toda impresión queda como ORIGINAL en «PRN-1»: una reimpresión no se distingue. El backend admite reimpresión sin motivo | FIS-02 | `EmisionPage.tsx:76`; `fiscal/api.py:86-89` | A |
| D-DOC-CONCURRENCY | Archivar durante una carga deja el documento ACTIVE. Borrar durante una carga da 500 y deja un huérfano. Medido en PostgreSQL; espera decisión | DOC-02 | `docs/roadmap/technical-debt-roadmap.md:99-100` | R |
| D-EST-ISSUANCE | `issuance_enabled` siempre es False y nada lo consulta. `establishment_id` de series y lotes no tiene FK | ORG-03 | `organization/api.py:218`; `fiscal/models.py:63`, `:78` | A |
| BASELINE · SALES-CONFIRMATION-EXTRA-WITHOUT-PRODUCT-500 | Una línea sobrante sin producto da 500 | PED-06 | `sales/service.py:1905-1916` | A |

## S3 — menores

| ID | Defecto | Filas | Ubicación |
|---|---|---|---|
| D-USERS-ACTIONS | La lista de usuarios anuncia editar y desactivar sin rutas detrás | SEG-01 | `identity_access/api.py:502` |
| D-HARDCODE-VED | «VED» fijo en contextos de aprobación y en la reclasificación | TRV-11 | `inventory/service.py:1006`, `:1180`; `location_validation.py:287`; `regulatory/service.py:355` |
| D-UI-PRINTER-FIXED | Imprenta «IMP-1» fija en la UI de numeración | FMA-07 | `NumeracionPage.tsx:51` |
| D-INV-PRESENTATION-LAYER | La recepción de compras crea la capa con la cantidad en su presentación (p. ej. 2 cajas) mientras el saldo suma la cantidad base (24); previo a V4, no corregido | INV-09 | `purchasing/service.py:1282`; `inventory/service.py` (`_apply_cost_in`) |

## Cerrados

| ID | Estado | Evidencia |
|---|---|---|
| D-INV-TRANSFER-COST | Corregido en V4 (2026-11-21) | `specs/enterprise-v4-inventory-valuation/evidence/CIERRE.md` |
| D-INV-REVERSE-STATE | Corregido en V4 (2026-11-21) | `specs/enterprise-v4-inventory-valuation/evidence/CIERRE.md` |
| D-INV-RECOMPUTE | Corregido en V4 (2026-11-21) | `specs/enterprise-v4-inventory-valuation/evidence/CIERRE.md` |
| D-INV-ADJ-NO-APPLY | Corregido en V4 (2026-11-21) | `specs/enterprise-v4-inventory-valuation/evidence/CIERRE.md` |
| D-INV-COUNT-STUCK | Corregido en V4 (2026-11-21) | `specs/enterprise-v4-inventory-valuation/evidence/CIERRE.md` |
| D-INV-TRANSFER-RECEIPT | Corregido en V4 (2026-11-21) | `specs/enterprise-v4-inventory-valuation/evidence/CIERRE.md` |
| D-INV-TRANSFER-LOCATED (hallazgo V4) | Encontrado y corregido en V4: la transferencia no podía sacar mercancía ubicada | idem |
| D-INV-FIFO-SAME-TX-ORDER (hallazgo V4) | Encontrado y corregido en V4: capas de una misma transacción empataban en el orden FIFO | idem |

D-APPROVAL-QTY-AS-VED sigue abierto: el defecto está en las incidencias de recepción de compras (V5/V10), no en el inventario. D-INV-LEDGER-LOT sigue abierto (sub-vertical diferida).

## Recuento

- Tras V4 (2026-11-21): **55 únicos abiertos: 27 S1, 24 S2 y 4 S3** (60 − 6 corregidos + 1 hallazgo abierto, D-INV-PRESENTATION-LAYER). Línea base del rebaseline: 30 S1, 27 S2 y 3 S3, 60 únicos.
- La matriz tiene 63 filas en estado `PRODUCT_DEFECT` (70 antes de V4).
- **TEST_DEFECT: 2.**
  - `test_spec033_confirmation.py:343-346`: simula la corrección escribiendo el estado a mano.
  - `tests/test_purchasing.py:265-273`: aplica un pago DRAFT y lo da por correcto. Valida D-APPLY-UNCHECKED.
- **BASELINE_DEBT: 1** (SALES-CONFIRMATION-EXTRA-WITHOUT-PRODUCT-500).
- **ENVIRONMENT_FAILURE: 1.** Este puesto no puede ejecutar backend, frontend ni PostgreSQL. No afecta al producto.
- **FIXTURE_DEFECT: 0.**
