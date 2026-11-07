# GOVERNMENT_NOT_READY_CATALOG

> Para cada proceso no listo (los 122): qué funciona, qué no, qué compuerta falta, a quién afecta, qué lo bloquea y cuál es la siguiente remediación. Escrito para la dueña.

## Government Core: ente, estructura y autoridad

**Impacto:** No se puede dar de alta el organismo ni decir quién tiene autoridad para qué: sin esto ningún otro proceso de Gobierno puede operar con control.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| ORG-01 Configurar el ente y su tipo | **SALIÓ DE ESTE CATÁLOGO** (GOV-0-01, 2026-10-30) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | ninguna (10 de 10 en PASS) | — | — | prueba de la dueña |
| ORG-02 Estructura organizativa por ejercicio (órgano, unidad ejecutora, dependencia, sede, centro gestor) | **SALIÓ DE ESTE CATÁLOGO** (GOV-0-02, 2026-10-31) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | ninguna (11 de 11 en PASS) | — | — | prueba de la dueña |
| ORG-03 Cargos con competencias y límites de firma/aprobación | **SALIÓ DE ESTE CATÁLOGO** (GOV-0-03, 2026-11-01) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |
| ORG-04 Delegaciones, suplencias, encargadurías y designaciones con acto | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Delegaciones del motor 045 (sin acto administrativo). | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N37 (clase C) | GOV-0, con DoD de producto completa (política §4) |
| ORG-05 Responsables por unidad, programa, cuenta, almacén, caja, contrato y bien, con historia | BLOCKED | Nada en Gobierno; prueba de dependencias GOV-0-04 (specs/gov-0-04-responsables). | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | DOMAIN_DEPENDENCY: 8 de 9 objetos sin modelo en Gobierno (BUD-03, ACC-01, WH-02, TRE-08, TRE-01, CNT-01, AST-01); MATERIAL_OQ OQ-ORG05-01..03 (specs/gov-0-04-responsables) | GOV-0, con DoD de producto completa (política §4) |
| ORG-06 Vincular usuario con identidad, cargo, unidad y alcance; separación de roles | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Usuarios, roles y alcance por empresa (003): otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | LEGAL_VALIDATION_REQUIRED N40 (clase C) | GOV-0, con DoD de producto completa (política §4) |
| ORG-07 Matriz auditable de quién puede solicitar, comprometer, causar, pagar, custodiar, aprobar y auditar | **SALIÓ DE ESTE CATÁLOGO** (GOV-ORG-07, 2026-11-02) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |

## Presupuesto público (Budget Ledger)

**Impacto:** Presupuesto no puede formular, certificar disponibilidad, comprometer ni causar; no hay ejecución presupuestaria que consultar.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| BUD-01 Ejercicio económico-financiero | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C); LEGAL_VALIDATION_REQUIRED N10 (clase C) | GOV-1, con DoD de producto completa (política §4) |
| BUD-02 Clasificador presupuestario versionado | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-02; LEGAL_VALIDATION_REQUIRED N10 (clase C) | GOV-1, con DoD de producto completa (política §4) |
| BUD-03 Plan, programas, proyectos, metas físicas e indicadores | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C) | GOV-1, con DoD de producto completa (política §4) |
| BUD-04 Fuentes de financiamiento y restricciones | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C) | GOV-1, con DoD de producto completa (política §4) |
| BUD-05 Formulación: anteproyecto, proyecto y presupuesto aprobado con su acto | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-01; D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C); LEGAL_VALIDATION_REQUIRED N37 (clase C) | GOV-1, con DoD de producto completa (política §4) |
| BUD-06 Disponibilidad y certificación de disponibilidad | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-1, con DoD de producto completa (política §4) |
| BUD-07 Precompromiso / reserva | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N37 (clase C) | GOV-1, con DoD de producto completa (política §4) |
| BUD-08 Compromiso presupuestario | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-1, con DoD de producto completa (política §4) |
| BUD-09 Causado / devengado | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N36 (clase C) | GOV-1, con DoD de producto completa (política §4) |
| BUD-10 Modificaciones presupuestarias con flujo de aprobación (E2E-02) | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-02; LEGAL_VALIDATION_REQUIRED N09 (clase C); LEGAL_VALIDATION_REQUIRED N37 (clase C) | GOV-1, con DoD de producto completa (política §4) |
| BUD-11 Ledger presupuestario inmutable y reconstruible | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-1, con DoD de producto completa (política §4) |
| BUD-12 Cierre y reconducción del ejercicio | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-1, con DoD de producto completa (política §4) |
| BUD-13 Formularios y reportes ONAPRE | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | MEDIUM | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C); LEGAL_VALIDATION_REQUIRED N09 (clase C); LEGAL_VALIDATION_REQUIRED N10 (clase C) | GOV-1, con DoD de producto completa (política §4) |

## Requisiciones públicas

**Impacto:** Una unidad no puede registrar su necesidad ni pedir la verificación presupuestaria previa a comprar.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| REQ-01 Registrar necesidad/requisición (bienes, servicios u obras) con estimación y especificaciones | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Requisiciones de compras privadas (004): otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N37 (clase C) | GOV-2, con DoD de producto completa (política §4) |
| REQ-02 Verificación presupuestaria previa a la contratación | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| REQ-03 Consolidar necesidades compatibles | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| REQ-04 Alertas de fraccionamiento | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| REQ-05 Cerrar o cancelar requisición liberando reservas | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |

## Contrataciones públicas / Licitaciones

**Impacto:** No se puede llevar un procedimiento de contratación pública ni su expediente, evaluación y adjudicación.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| PROC-01 Determinar la modalidad de selección y conservar la regla y las excepciones | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N37 (clase C) | GOV-2, con DoD de producto completa (política §4) |
| PROC-02 Comisión de contrataciones (miembros, suplentes, impedimentos) | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| PROC-03 Expediente único de contratación con cronología y lapsos | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| PROC-04 Pliego, invitaciones, aclaratorias, prórrogas y avisos | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | D-GOV-03 | GOV-2, con DoD de producto completa (política §4) |
| PROC-05 Oferentes y contratistas (RNC/SNC) | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Terceros/proveedores privados: otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-03 | GOV-2, con DoD de producto completa (política §4) |
| PROC-06 Recepción y apertura de ofertas | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Cotizaciones de compras privadas: otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| PROC-07 Evaluación técnica, económica y legal con matriz bloqueada | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| PROC-08 Recomendación, decisión, adjudicación, desierta, anulación o rechazo | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| PROC-09 Compromiso de responsabilidad social | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| PROC-10 Garantías y cauciones | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| PROC-11 Conflictos SoD en contratación | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Motor SoD 045 (las reglas por proceso son de Gobierno). | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| PROC-12 Trazabilidad completa de la compra pública (E2E-01) | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |

## Contratos públicos

**Impacto:** No se puede crear ni administrar un contrato público, sus hitos, adendas, garantías o pagos asociados.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| CNT-01 Crear contrato u orden desde la adjudicación | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Órdenes de compra privadas: otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| CNT-02 Adendas, prórrogas y variaciones versionadas | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| CNT-03 Ejecución: hitos, entregables, valuaciones, recepciones y cierre; factura contra recepción | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Recepciones y facturas de proveedor privadas: otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| CNT-04 Designación del supervisor del contrato | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| CNT-05 Bloqueo de pagos por encima del monto contractual | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| CNT-06 Penalidades, retenciones, anticipos, amortizaciones y garantías del contrato | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N38 (clase C) | GOV-2, con DoD de producto completa (política §4) |
| CNT-07 Terminación, resolución o rescisión | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| CNT-08 Expediente contractual completo | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |
| CNT-09 Alertas de vencimientos | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Notificaciones 047. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-2, con DoD de producto completa (política §4) |

## Almacén de consumo público

**Impacto:** Almacén no puede recibir contra contrato, controlar consumo público ni conciliar conteos con aprobación.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| WH-01 Recepción física contra orden/contrato separando consumo, capitalizable y patrimonial | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Recepción privada (003/004): otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N15 (clase C) | GOV-3, con DoD de producto completa (política §4) |
| WH-02 Inventario por almacén y movimientos sin negativo silencioso; consumo por programa | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Inventario privado (003/008): otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |
| WH-03 Salidas autorizadas con destino y beneficiario | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |
| WH-04 Conteos físicos y conciliación con aprobación de ajustes | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Conteos privados (003): otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |
| WH-05 Kardex reproducible por artículo, almacén y período | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Kardex privado (003). | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |

## Tesorería pública

**Impacto:** Tesorería no puede ordenar ni ejecutar pagos públicos con maker-checker, retenciones y conciliación.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| TRE-01 Cuentas bancarias públicas con autorizados y acto habilitante | **SALIÓ DE ESTE CATÁLOGO** (GOV-TRE-01, 2026-11-05) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |
| TRE-02 Programación financiera y disponibilidad de caja | **SALIÓ DE ESTE CATÁLOGO** (GOV-TRE-02 y T038, 2026-11-06) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |
| TRE-03 Orden de pago desde obligación causada | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |
| TRE-04 Pago con maker-checker, medios autorizados y bloqueo de duplicados | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Pagos privados (006): otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N37 (clase C) | GOV-3, con DoD de producto completa (política §4) |
| TRE-05 Retenciones tributarias/contractuales y comprobantes | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Retenciones fiscales privadas (007): otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N37 (clase C); LEGAL_VALIDATION_REQUIRED N38 (clase C) | GOV-3, con DoD de producto completa (política §4) |
| TRE-06 Conciliación bancaria | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Conciliación privada (006): otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |
| TRE-07 Anulación y reverso de pago | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |
| TRE-08 Fondos y cajas autorizadas: reposición, rendición y arqueo | BLOCKED (GOV-TRE-FUNCTIONAL-03, 2026-11-06) | Nada en Gobierno | La constitución y la reposición exigen orden de pago; los gastos, compromiso y causado; la resolución nombra al funcionario | todas (11 de 11) | HIGH | DOMAIN_DEPENDENCY: TRE-03/TRE-04 (orden de pago), BUD (compromiso y causado), ORG-06 (funcionario responsable) | Ver `specs/gov-tre-08-fondos-cajas/evidence/TRE08_BLOCKER_REPORT.md` |
| TRE-09 Provenance de tasas BCV | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Tasas privadas (038/048). | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |
| TRE-10 Trazabilidad del pago hasta presupuesto y contrato | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |

## Contabilidad pública

**Impacto:** Contabilidad no puede asentar, cerrar ni emitir estados conforme a la contabilidad pública.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| ACC-01 Plan de cuentas, mapeos presupuesto-contabilidad e historial de reglas | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) | GOV-3, con DoD de producto completa (política §4) |
| ACC-02 Asientos de doble partida automáticos y manuales; momentos contables; corrección por reverso | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) | GOV-3, con DoD de producto completa (política §4) |
| ACC-03 Cierres mensuales y anuales con checklist y reapertura excepcional | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |
| ACC-04 Balance de comprobación, estados y auxiliares | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) | GOV-3, con DoD de producto completa (política §4) |
| ACC-05 Conciliación presupuesto vs contabilidad vs tesorería vs cuentas por pagar | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |
| ACC-06 Terceros y beneficiarios | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Terceros privados (009): otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N38 (clase C) | GOV-3, con DoD de producto completa (política §4) |
| ACC-07 Multimoneda autorizada | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-3, con DoD de producto completa (política §4) |
| ACC-08 Exportaciones a sistemas rectores | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | MEDIUM | D-GOV-04 | GOV-3, con DoD de producto completa (política §4) |

## Bienes públicos / Activo fijo patrimonial

**Impacto:** Bienes no puede incorporar, etiquetar, asignar custodios, inventariar, revalorizar ni desincorporar bienes públicos.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| AST-01 Incorporación del bien: registro, categoría, origen y valor | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Spec 057 activos fijos privados (PLANNED / NOT_STARTED). | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-05; LEGAL_VALIDATION_REQUIRED N15 (clase C); LEGAL_VALIDATION_REQUIRED N17 (clase C); LEGAL_VALIDATION_REQUIRED N36 (clase C) | GOV-4, con DoD de producto completa (política §4) |
| AST-02 Codificación y etiquetado SUDEBIP | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-05; LEGAL_VALIDATION_REQUIRED N15 (clase C) | GOV-4, con DoD de producto completa (política §4) |
| AST-03 Ubicación y custodia con historial | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-4, con DoD de producto completa (política §4) |
| AST-04 Transferencias internas e inter-ente con acta | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-4, con DoD de producto completa (política §4) |
| AST-05 Inventario físico patrimonial por campaña | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-4, con DoD de producto completa (política §4) |
| AST-06 Revalorización con avalúo | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N14 (clase C) | GOV-4, con DoD de producto completa (política §4) |
| AST-07 Arrendamiento de bienes públicos | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | MEDIUM | LEGAL_VALIDATION_REQUIRED N16 (clase C) | GOV-4, con DoD de producto completa (política §4) |
| AST-08 Mantenimiento documental mínimo | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-4, con DoD de producto completa (política §4) |
| AST-09 Desincorporación (baja, enajenación, pérdida, robo) sin borrado físico | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-05; LEGAL_VALIDATION_REQUIRED N17 (clase C) | GOV-4, con DoD de producto completa (política §4) |
| AST-10 Relación con contabilidad y depreciación/valoración | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) | GOV-4, con DoD de producto completa (política §4) |
| AST-11 Actas de entrega de bienes por cambio de autoridad o custodio | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-4, con DoD de producto completa (política §4) |

## Expedientes y actos administrativos

**Impacto:** No hay expediente electrónico, actos administrativos con lapsos ni notificaciones con constancia.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| DOC-01 Expediente electrónico único con índice, foliado y versiones | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Gestión documental 046 (almacén y versiones; sin expediente). | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N40 (clase C) | GOV-5, con DoD de producto completa (política §4) |
| DOC-02 Actos administrativos con autoridad, motivación y eficacia | **SALIÓ DE ESTE CATÁLOGO** (GOV-DOC-02, 2026-11-01) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |
| DOC-03 Lapsos, suspensiones, subsanaciones y prórrogas | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-5, con DoD de producto completa (política §4) |
| DOC-04 Notificaciones administrativas con constancia de recepción | **SALIÓ DE ESTE CATÁLOGO** (GOV-DOC-04, 2026-11-02) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |
| DOC-05 Firma electrónica | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | D-GOV-08; LEGAL_VALIDATION_REQUIRED N40 (clase C) | GOV-5, con DoD de producto completa (política §4) |
| DOC-06 Preservación y retención de evidencia sin borrado | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | LEGAL_VALIDATION_REQUIRED N37 (clase C) | GOV-5, con DoD de producto completa (política §4) |
| DOC-07 Búsqueda por expediente, acto, tercero, contrato, presupuesto, bien y fecha | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Búsqueda documental 046. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | LEGAL_VALIDATION_REQUIRED N40 (clase C) | GOV-5, con DoD de producto completa (política §4) |
| DOC-08 Paquete de auditoría exportable | **SALIÓ DE ESTE CATÁLOGO** (GOV-DOC-08, 2026-11-04) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |

## Control interno, auditoría y rendición

**Impacto:** Control interno y auditores no tienen matriz SoD por proceso, bitácora institucional, rendición ni hallazgos.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| CTL-01 Matriz SoD por proceso y detección previa | **SALIÓ DE ESTE CATÁLOGO** (GOV-CTL-01, 2026-11-04) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |
| CTL-02 Bitácora institucional append-only con actor, autoridad, unidad y correlación | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Bitácora 006/051 (sin autoridad ni unidad). | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | LEGAL_VALIDATION_REQUIRED N40 (clase C) | GOV-5, con DoD de producto completa (política §4) |
| CTL-03 Administrador técnico sin autoridad funcional | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Separación ADMIN de 003 (sin rol de plataforma). | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | LEGAL_VALIDATION_REQUIRED N40 (clase C) | GOV-0, con DoD de producto completa (política §4) |
| CTL-04 Consulta y muestreo read-only del auditor | **SALIÓ DE ESTE CATÁLOGO** (GOV-CTL-04, 2026-11-03) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |
| CTL-05 Expediente de cuenta y reportes de rendición | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-5, con DoD de producto completa (política §4) |
| CTL-06 Hallazgos y planes de acción correctiva | **SALIÓ DE ESTE CATÁLOGO** (GOV-CTL-06, 2026-11-04) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |
| CTL-07 Alertas de operaciones atípicas | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-5, con DoD de producto completa (política §4) |
| CTL-08 Historial de cambios de maestros sensibles | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Auditoría de cambios privada. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-5, con DoD de producto completa (política §4) |
| CTL-09 Actas de entrega por cambio de responsable o autoridad | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-5, con DoD de producto completa (política §4) |
| CTL-10 Controles materiales que impiden cerrar ejercicio o proceso | **SALIÓ DE ESTE CATÁLOGO** (GOV-CTL-10, 2026-11-07) | Todo el proceso: ver `OWNER_UAT_READY_CATALOG.md` | — | — | — | — |

## Gobierno Digital: trámites e interoperabilidad

**Impacto:** No se pueden diseñar ni atender trámites, ni intercambiar datos con otros organismos.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| DIG-01 Catálogo de trámites con requisitos versionados y captura única | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-06 | GOV-6, con DoD de producto completa (política §4) |
| DIG-02 Solicitud, subsanación y seguimiento del trámite con estado visible (E2E-05) | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-06; LEGAL_VALIDATION_REQUIRED N40 (clase C) | GOV-6, con DoD de producto completa (política §4) |
| DIG-03 Interoperabilidad: datos del Estado, API, provenance, base de intercambio e inventario | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (11 de 11) | HIGH | D-GOV-08; LEGAL_VALIDATION_REQUIRED N40 (clase C) | GOV-6, con DoD de producto completa (política §4) |

## Gasto de personal e interfaz Atenea

**Impacto:** El gasto de personal no puede recibir los lotes de nómina de Atenea con control presupuestario y contable.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| HR-01 Estructura de cargos y plantillas presupuestarias de personal | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | D-GOV-07; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C) | GOV-7, con DoD de producto completa (política §4) |
| HR-02 Interfaz de nómina Atenea con maker-checker y sin duplicados (E2E-04) | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | HIGH | D-GOV-07; LEGAL_VALIDATION_REQUIRED N40 (clase C) | GOV-7, con DoD de producto completa (política §4) |
| HR-03 Reportes SISROE y de altos funcionarios | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-7, con DoD de producto completa (política §4) |

## Integraciones institucionales

**Impacto:** Ningún intercambio institucional (Atenea, bancos, SNC/RNC, SUDEBIP, ONAPRE/ONCOP, interoperabilidad, firma) está disponible.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| INT-01 Atenea: lotes de nómina idempotentes | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (9 de 9) | HIGH | D-GOV-07 | GOV-7, con DoD de producto completa (política §4) |
| INT-02 Bancos: archivos/APIs con contrato del banco | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (9 de 9) | HIGH | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | GOV-7, con DoD de producto completa (política §4) |
| INT-03 SNC/RNC: consulta de contratistas con provenance | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (9 de 9) | MEDIUM | D-GOV-03 | GOV-7, con DoD de producto completa (política §4) |
| INT-04 SUDEBIP: reportes y codificación por mecanismo oficial | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (9 de 9) | MEDIUM | D-GOV-05 | GOV-7, con DoD de producto completa (política §4) |
| INT-05 ONAPRE/ONCOP: formatos oficiales versionados | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (9 de 9) | MEDIUM | D-GOV-02; D-GOV-04 | GOV-7, con DoD de producto completa (política §4) |
| INT-06 Interoperabilidad del Estado (N26/N28) | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (9 de 9) | HIGH | D-GOV-08 | GOV-7, con DoD de producto completa (política §4) |
| INT-07 Firma electrónica: proveedor o certificado homologado | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (9 de 9) | MEDIUM | D-GOV-08 | GOV-7, con DoD de producto completa (política §4) |

## Reportes y tableros institucionales

**Impacto:** No existe el reporte o tablero institucional que el usuario necesita consultar y exportar.

| Proceso | Estado | Qué funciona | Qué no funciona | Compuerta que falta | Severidad | Dependencias | Siguiente remediación |
|---|---|---|---|---|---|---|---|
| REP-01 Ejecución presupuestaria (aprobado, modificado, comprometido, causado, pagado, disponible) | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Motor de reportes 050. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | D-GOV-02 | con el ciclo de su dominio, con DoD de producto completa (política §4) |
| REP-02 Plan vs presupuesto vs ejecución físico-financiera | BLOCKED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Motor de reportes 050. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | D-GOV-02 | con el ciclo de su dominio, con DoD de producto completa (política §4) |
| REP-03 Contrataciones por modalidad, estado, unidad, proveedor, monto y tiempos | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Motor de reportes 050. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | con el ciclo de su dominio, con DoD de producto completa (política §4) |
| REP-04 Contratos: comprometido, ejecutado, pagado, garantías y vencimientos | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Motor de reportes 050. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | con el ciclo de su dominio, con DoD de producto completa (política §4) |
| REP-05 Obligaciones causadas pendientes de orden o pago | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: CxP privadas (004): otro contrato. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | con el ciclo de su dominio, con DoD de producto completa (política §4) |
| REP-06 Tesorería: disponibilidad, pagos, conciliaciones y partidas en tránsito | NOT_STARTED | Nada en Gobierno. Existe un equivalente privado que **no** sirve tal cual: Reportes de tesorería privados (006). | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | con el ciclo de su dominio, con DoD de producto completa (política §4) |
| REP-07 Contabilidad: balance, diario, mayor, auxiliares y cierres | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | D-GOV-04 | con el ciclo de su dominio, con DoD de producto completa (política §4) |
| REP-08 Bienes públicos: inventario, custodios, ubicaciones, diferencias y desincorporaciones | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | D-GOV-05 | con el ciclo de su dominio, con DoD de producto completa (política §4) |
| REP-09 Rendición de cuentas por responsable y período | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | con el ciclo de su dominio, con DoD de producto completa (política §4) |
| REP-10 Control interno: overrides, conflictos SoD, duplicados, hallazgos | NOT_STARTED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | con el ciclo de su dominio, con DoD de producto completa (política §4) |
| REP-11 Trámites: volumen, tiempos, subsanaciones y cuellos de botella | BLOCKED | Nada en Gobierno. | No hay menú, pantalla, API, datos ni prueba de Gobierno | todas (10 de 10) | MEDIUM | D-GOV-06 | con el ciclo de su dominio, con DoD de producto completa (política §4) |

