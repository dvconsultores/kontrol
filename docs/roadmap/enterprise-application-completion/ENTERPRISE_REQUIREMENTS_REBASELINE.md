# KONTROL Enterprise · rebaseline de requisitos

**Autoridad única del backlog Enterprise** desde el 2026-11-20. Sustituye a `SPONSOR_APPLICATION_COVERAGE_MATRIX.{md,csv}`, que queda como antecedente histórico: era una matriz por menú, con 73 de 92 filas obsoletas.

| Campo | Valor |
|---|---|
| Ciclo | `P3-ENTERPRISE-REBASELINE-AND-COMPLETION-MATRIX` |
| Programador | P3 · línea Enterprise |
| Orquestación | ChatGPT (dirección) · Claude (auditoría) · DeepSeek (no usado: ver ATTEMPT_LOG) · dueña (aceptación) |
| HEAD auditado | `origin/develop` `b726c1da`; HEAD local `b3b53046` (solo herramientas) |
| Alembic | cabeza única `0128_gov_tre04_pago` |
| Datos | `ENTERPRISE_REQUIREMENTS_REBASELINE.csv`: 277 filas, una por requisito |
| Defectos | `ENTERPRISE_CURRENT_DEFECTS.md`: 60 únicos |
| DAG | `ENTERPRISE_COMPLETION_DAG.md` |
| Evidencia | `specs/enterprise-rebaseline/evidence/` |

## Actualización V4 · 2026-11-21

`V4-INVENTORY-LEDGER-VALUATION-INTEGRITY` corrigió los defectos D-INV-TRANSFER-COST, D-INV-TRANSFER-RECEIPT,
D-INV-REVERSE-STATE, D-INV-RECOMPUTE, D-INV-ADJ-NO-APPLY y D-INV-COUNT-STUCK, más dos hallazgos del ciclo
(D-INV-TRANSFER-LOCATED y D-INV-FIFO-SAME-TX-ORDER). Siete filas dejan de ser PRODUCT_DEFECT y quedan PARTIAL por
huecos fuera de V4 (lote/serial en el ledger, reserva al aprobar la transferencia, pérdida en tránsito, congelamiento
del conteo, evidencia del ajuste, restricciones de base de datos). Ninguna fila pasa a COMPLETE.
Detalle: `specs/enterprise-v4-inventory-valuation/evidence/CIERRE.md`.

## PRODUCT COMPLETENESS GATE

| Campo | Valor |
|---|---|
| WHERE_IS_IT_IN_MENU | No aplica: ciclo de análisis, sin código de producto |
| WHAT_CAN_USER_DO | Nada nuevo en la aplicación. La dueña y ChatGPT disponen de un backlog requisito por requisito, con estado verificado contra el HEAD, defectos con fichero y línea, un DAG y cinco verticales siguientes |
| OWNER_UAT_READY | NOT_APPLICABLE para el ciclo. En el producto: 1 requisito de 277 |
| PRODUCT_STATUS | Sin cambio de producto (`PRODUCT_CODE_CHANGES=0`) |
| MISSING_GATES | Ejecución de pruebas en este puesto (ENVIRONMENT_FAILURE: sin PostgreSQL ni dependencias). La verificación es estática más evidencia registrada |
| WHY_UI_NOT_APPLICABLE | El encargo prohíbe código de producto en este ciclo (§36) |

## 1. Cómo se construyó

1. **Fuentes.** Se leyeron completas las 11 fuentes funcionales del sponsor (`SOURCE_INVENTORY.md`):
   - los Volúmenes 0–6;
   - los DOCX de Importación y de Pedido;
   - el mapa `procesos.png`;
   - SPEC057.
   
   Las normativas F3 y F6–F9 se registran sin extraer requisitos, para no inventar regulación. Saint es referencia comparativa, no requisito.
2. **Catálogo requisito por requisito.** Son 236 requisitos con identificador estable, fuente y sección. Además de las 92 opciones del menú, cubre:
   - reglas no negociables;
   - máquinas de estado;
   - integridad;
   - segregación de funciones;
   - concurrencia;
   - idempotencia;
   - costeo y valoración;
   - procesos de los DOCX;
   - los 13 E2E mínimos;
   - activos fijos.
   
   Importaciones se expande en las 42 filas de la Spec 018. Total: **277**.
3. **Auditoría del HEAD.** Siete auditorías paralelas de solo lectura, con un brief común y estados del encargo §7–§9, leyeron el código: modelos, servicios, API, migraciones, frontend, router, menú, permisos, auditoría y E2E. Usaron además la evidencia registrada.
4. **Revisión de Claude.**
   - Leyó el código de 22 defectos de muestra: todos se confirmaron, en 4 casos con una parte PLAUSIBLE.
   - Resolvió una incoherencia de UAT: A11Y-IMPORT-SCROLL-REGIONS rebaja 40 filas a `OWNER_UAT_READY=NO`.
   - Consolidó la matriz y derivó las métricas por script.
5. **Límite declarado.** Ninguna prueba se volvió a ejecutar: el puesto no tiene PostgreSQL, `node_modules` ni dependencias del backend. Por eso:
   - `COMPLETE` significa «construido de punta a punta y sin hueco conocido en el código, con pruebas en el repositorio»;
   - `OWNER_UAT_READY` solo se mantiene si la evidencia registrada cumple **todas** las condiciones: PostgreSQL, navegador real, flujo completo, responsive, Axe y tarjeta.

## 2. Métricas

```ini
ENTERPRISE_REQUIREMENTS_TOTAL=277
COMPLETE=52
OWNER_UAT_READY=1
PARTIAL=139               ; V4 (2026-11-21): 132 → 139
NOT_BUILT=20
PRODUCT_DEFECT=63         ; V4: 70 → 63 (INV-01, 05, 06, 07, 08, 17 y TRV-08 sin defecto; quedan PARTIAL)
SPONSOR_VALIDATION_REQUIRED=3
OUT_OF_SCOPE_CONFIRMED=0

OLD_MATRIX_FALSE_POSITIVES=41
OLD_MATRIX_FALSE_NEGATIVES=13
OBSOLETE_ROWS=73          ; de 92 (además de FP y FN, 19 acertaban el grado pero ignoraban un defecto)

SPEC018_TOTAL=42
SPEC018_COMPLETE=39
SPEC018_PARTIAL=1          ; IMP-21 evidencia de la incidencia sin pantalla
SPEC018_NOT_BUILT=0
SPEC018_SPONSOR_VALIDATION_REQUIRED=1   ; IMP-34 Zonas A–E
SPEC018_PRODUCT_DEFECTS=1  ; IMP-28 expediente «recibida y ubicada» con recepción parcial sin confirmar
SPEC018_OWNER_UAT_READY=0  ; A11Y-IMPORT-SCROLL-REGIONS (Axe grave a 390/320 en el expediente)

DISPATCH_COST_RELIEF_HISTORICO=OPEN   ; 0098 solo crea la tabla; sin backfill autorizado (DCR-10)
RETURN_REJECTED_VALUATION=OPEN        ; reenter_return repone capa solo a DISPONIBLE (sales/service.py:3641)
ZERO_INSTITUTIONAL_HARDCODE=NO        ; «VED» fijo, cantidad tratada como importe, snapshot de tasa 1.0
```

### Las tres métricas de producto, por separado (norma de completitud)

| Métrica | Valor | Definición |
|---|---|---|
| Fundamento técnico | **250 de 277 (90 %)** con backend, total o parcial; 231 (83 %) con backend y frontend | Existe código que toca el requisito |
| Producto funcional | **52 de 277 (19 %)** COMPLETE | De punta a punta y sin hueco conocido; 39 de los 52 son de Importaciones |
| Listo para la dueña | **1 de 277** (CMP-06, comparar ofertas y adjudicar) | COMPLETE más PostgreSQL, navegador, responsive, Axe y tarjeta. `OWNER_ACCEPTED=0` |

La distancia entre el fundamento (90 %) y el producto funcional (19 %) es la brecha real. Casi todo existe a medias: falta la pantalla, falta la integración con el proceso vecino, o la regla está rota.

## 3. Por módulo

| Módulo | Req. | COMPLETE | PARTIAL | DEFECT | NOT_BUILT | SPONSOR | UAT |
|---|---|---|---|---|---|---|---|
| Inicio | 6 | 2 | 3 | 1 | 0 | 0 | 0 |
| Maestros/Organización | 10 | 0 | 7 | 1 | 2 | 0 | 0 |
| Maestros/Terceros | 12 | 2 | 8 | 2 | 0 | 0 | 0 |
| Maestros/Productos | 15 | 0 | 9 | 4 | 2 | 0 | 0 |
| Maestros/Comercial | 8 | 0 | 5 | 2 | 1 | 0 | 0 |
| Maestros/Financiero | 6 | 0 | 6 | 0 | 0 | 0 | 0 |
| Maestros/Fiscal | 10 | 0 | 0 | 8 | 2 | 0 | 0 |
| Maestros/Regulatorio | 6 | 0 | 5 | 1 | 0 | 0 | 0 |
| Compras | 17 | 2 | 11 | 4 | 0 | 0 | 1 |
| Importaciones (Spec 018) | 42 | 39 | 1 | 1 | 0 | 1 | 0 |
| Ventas (incl. DOCX Pedido) | 25 | 0 | 14 | 10 | 0 | 1 | 0 |
| Inventario | 18 | 2 | 14 | 0 | 1 | 1 | 0 |
| CxC | 10 | 0 | 5 | 4 | 1 | 0 | 0 |
| CxP | 7 | 0 | 3 | 4 | 0 | 0 | 0 |
| Tesorería | 9 | 0 | 4 | 5 | 0 | 0 | 0 |
| Fiscal | 13 | 0 | 6 | 6 | 1 | 0 | 0 |
| Regulación | 9 | 0 | 5 | 3 | 1 | 0 | 0 |
| Reportes | 5 | 0 | 3 | 1 | 1 | 0 | 0 |
| Aprobaciones | 7 | 0 | 6 | 1 | 0 | 0 | 0 |
| Seguridad | 7 | 2 | 5 | 0 | 0 | 0 | 0 |
| Auditoría | 7 | 3 | 3 | 0 | 1 | 0 | 0 |
| Documentos | 4 | 0 | 3 | 1 | 0 | 0 | 0 |
| Configuración | 8 | 0 | 6 | 0 | 2 | 0 | 0 |
| Transversal | 11 | 0 | 7 | 4 | 0 | 0 | 0 |
| Activos fijos (SPEC057) | 5 | 0 | 0 | 0 | 5 | 0 | 0 |
| **Total** | **277** | **52** | **139** | **63** | **20** | **3** | **1** |

**COMPLETE fuera de Importaciones (13):**
- INI-03, Mis tareas;
- INI-04, Mis aprobaciones;
- TER-05, aprobación del proveedor antes de pagar;
- TER-10, contactos;
- CMP-06, adjudicar y emitir la OC;
- CMP-09, recepción con máquina de estados;
- INV-03, reservas;
- INV-14, alivio de costo en el despacho;
- SEG-05, MFA;
- SEG-07, deny by default;
- AUD-01, timeline;
- AUD-03, accesos;
- AUD-07, inmutabilidad de la auditoría.

**NOT_BUILT (20):**

| Módulo | Requisitos |
|---|---|
| Maestros/Organización | Centros de costo (DT-04: `cost_center_id` sin tabla ni FK), unidades de negocio |
| Maestros/Productos | Marcas, modelos |
| Maestros/Comercial | Comisiones |
| Maestros/Fiscal | Imprentas, plantillas fiscales |
| Fiscal | Contingencia |
| CxC | Cobranza (promesas y seguimiento) |
| Inventario | Valoración de lo rechazado |
| Regulación | Recepciones reguladas |
| Reportes | Reportes personalizados |
| Auditoría | Incidentes de seguridad. `incidents.spec.ts` cubre incidencias de recepción, no de seguridad |
| Configuración | Correo, integraciones |
| Activos fijos | AF-01..05 |

**SPONSOR_VALIDATION_REQUIRED (3):**
- IMP-34, zonas A–E. El mapa del sponsor las presenta como «Ejemplo de zonas» de una versión preliminar.
- VEN-09, entregado-no-facturado frente a «factura antes del despacho» del DOCX de Pedido.
- INV-15, backfill del costo histórico de despacho.

## 4. Pendientes y parciales históricos revalidados (§11–§12 del encargo)

| Histórico | Antes | Ahora | Por qué |
|---|---|---|---|
| Inicio → Vencimientos | NOT_STARTED | PARTIAL | Tres contadores en el dashboard; sin pantalla ni alertas |
| Organización → Centros de costo / Unidades de negocio | NOT_STARTED | NOT_BUILT | Sin tabla. DT-04 |
| Terceros → Vendedores / Beneficiarios | NOT_STARTED | PARTIAL | Solo etiqueta de rol; `salesperson_id` y `sales_commission_policies` reservados |
| Productos → Plantillas | NOT_STARTED | PARTIAL | Tablas sin API ni pantalla |
| Productos → Marcas y modelos | NOT_STARTED | NOT_BUILT | — |
| Comercial → Crédito / Zonas / Rutas / Descuentos | NOT_STARTED | PARTIAL; descuentos PRODUCT_DEFECT | Modelo y API sin pantalla. El descuento descarta su aprobación |
| Comercial → Comisiones | NOT_STARTED | NOT_BUILT | `gov_commission_policies` son de contratación pública, no de vendedores |
| Comercial → Condiciones de pago | FRONTEND_SHELL | PARTIAL | La pantalla sí llama a la API; falta asignarlas al cliente |
| Fiscal maestro → Plantillas fiscales | NOT_STARTED | NOT_BUILT | — |
| Compras → Comparación de ofertas | NOT_STARTED | CMP-05 PARTIAL y CMP-06 COMPLETE + UAT | Compara solo precio, descuento, plazo y vigencia. Falta impuesto, disponibilidad y calidad |
| Ventas → Crédito | NOT_STARTED | PARTIAL | Aprobación SALES_CREDIT por el motor de la Spec 045. Sin límite, exposición ni mora; sin menú |
| Fiscal → Contingencia | NOT_STARTED | NOT_BUILT | — |
| Regulación → Vencimientos | NOT_STARTED | PARTIAL | La guía vencida bloquea; sin paso a EXPIRED, alertas ni pantalla |
| Auditoría → Incidentes | NOT_STARTED | NOT_BUILT | Ver arriba |
| Dashboard, Alertas | PARTIAL_PROCESS | DEFECT / PARTIAL | El dashboard suma monedas distintas sin conversión |
| Listas y reglas de precios | PARTIAL_PROCESS | PRODUCT_DEFECT | La lista por cliente nunca se aplica (`party_id` frente a `customer_id`) |
| Bancos, cuentas, cajas y métodos | PARTIAL_PROCESS | PARTIAL | Sin auditoría, edición ni baja; moneda como texto libre; método sin IGTF |
| Perfiles fiscales, numeración, emisión, retenciones, libros y cierres | PARTIAL_PROCESS | PRODUCT_DEFECT | Ver S1 en `ENTERPRISE_CURRENT_DEFECTS.md` |
| Organismos y registros, vehículos y certificados, permisos, validaciones | PARTIAL_PROCESS | PARTIAL / DEFECT | La guía no se vincula al despacho; no se cruzan producto, lote ni vehículo; anular el bloqueo no libera |
| Requisiciones | PARTIAL_PROCESS | PARTIAL | Sin presupuesto. La aprobación es solo por monto |
| Devoluciones de compra | PARTIAL_PROCESS | PRODUCT_DEFECT | En DRAFT sin proveedor, transiciones, movimiento ni auditoría |
| Cotizaciones de venta | PARTIAL_PROCESS | PARTIAL | La cotización no reserva, como exige la regla. Falta documento imprimible o enviable, auditoría del alta y de las líneas, y E2E de usuario |
| Notas de venta | PARTIAL_PROCESS | PRODUCT_DEFECT | Vías heredadas sin documento fiscal |
| Kardex, transferencias, conteos, costos | PARTIAL_PROCESS | PARTIAL / DEFECT | Transferencia sin capa en destino; conteo bloqueado en FROZEN |
| CxC, CxP | PARTIAL_PROCESS | PRODUCT_DEFECT | El motor de aplicaciones no valida tercero, estado ni moneda; retenciones reaplicables |
| Reportes de auditoría | PARTIAL_PROCESS | PARTIAL | — |

Las **42 FUNCTIONAL_SLICE_COMPLETE** se reclasifican así (ninguna conserva el estado):

| Estado nuevo | Filas |
|---|---|
| COMPLETE | 3 |
| PARTIAL | 20 |
| PRODUCT_DEFECT | 19 |

Ninguna llega a OWNER_UAT_READY. Detalle en `specs/enterprise-rebaseline/evidence/OBSOLETE_MATRIX_FINDINGS.md`.

## 5. Costos y valoración (§14)

- **Landed cost:** COMPLETE (IMP-14..17). Se distribuye, se aplica a la capa y se revierte con bloqueo si la capa ya se consumió.
- **Despacho:** INV-14 COMPLETE. El despacho consume capas, landed cost incluido.
- **Transferencias: defecto S1.** La entrada no crea capa en el destino.
- **Reverso:** defecto S1. Vuelve a consumir capas.
- **Devoluciones:** solo se repone la capa si el destino es DISPONIBLE. `RETURN_REJECTED_VALUATION=OPEN`.
- **Histórico:** `DISPATCH_COST_RELIEF_HISTORICO=OPEN`. El backfill necesita autorización de la dueña.
- **Coherencia (INV-13): PARTIAL.** Hay proyecciones separadas de físico, reservado, disponible, recibido no confirmado, suministro abierto y capas. Ninguna conciliación físico↔capas ni caché↔ledger.

## 6. Hard-code (§27)

`ZERO_INSTITUTIONAL_HARDCODE=NO`.

**Lo que no aparece:**
- «HJ»;
- nombres de clientes;
- zonas fijas (A–E es un catálogo configurable);
- bancos fijos;
- roles comprobados por nombre, salvo los protegidos del sistema.

Las tasas de IVA, IGTF y retención salen de reglas versionadas. Los valores por defecto de los formularios son editables.

**Lo que impone una regla:**
- «VED» fijo en contextos de aprobación y de reclasificación;
- la cantidad enviada como importe en VED al motor de aprobaciones;
- `exchange_rate_snapshot=1.0` en la emisión fiscal.

**El proceso del DOCX de Pedido**, de un cliente concreto, queda fijo para todas las empresas en `ORDER_TRANSITIONS`: confirmación obligatoria y factura antes del despacho. Que sea configurable por empresa es decisión de la dueña.

## 7. Base de datos (§29) y OpenAPI (§30)

| Punto | Resultado |
|---|---|
| Fresh DB | PASS (R): cada corrida de `qa/e2e-run.py` crea y migra una base efímera |
| Upgrade / downgrade / upgrade again | PASS (R), solo incremental (`specs/gov-tre-04-pago/evidence/CIERRE.md:72`). No hay evidencia de `downgrade base` de la cadena completa |
| Single head | PASS (M+R) |
| Constraints | **FAIL**: sin `Unique` de numeración fiscal ni de número de control; claves de idempotencia sin unicidad |
| Índices | 159 de 165 tablas con `company_id` lo indexan; 6 excepciones |
| Concurrencia | PARCIAL: `with_for_update` en ventas, compras, almacenamiento y tesorería; ninguno en fiscal |
| Aislamiento | PASS, con D-APPROVAL-ROLE-TENANT y D-PROFILE-XCOMPANY. Un usuario sin alcance declarado ve todas las empresas del tenant: es diseño documentado, pero no hay forma de declarar alcances (SEG-03) |
| Postgres | `POSTGRESQL_REQUIRED=YES`. Ninguna certificación SQLite se acepta como prueba. Las filas de Terceros OWNER_UAT_READY de la matriz antigua solo tenían SQLite |

**OpenAPI (1 154 operaciones):**
- **Frontend sin backend:** 0 en Enterprise.
- **Backend sin llamada visible:** 87 (análisis estático); tras la revisión, 35 se llaman por otra vía, 30 son legítimas sin pantalla y 22 son capacidades de negocio sin pantalla. Entre estas últimas:
  - triple match;
  - retenciones practicadas y sufridas;
  - perfiles fiscales de terceros;
  - saldo de cuenta bancaria y por cliente;
  - condiciones comerciales por cliente;
  - edición de tipos documentales y vista previa;
  - tipos y bloqueo de ubicación;
  - catálogo de tipos de proceso de aprobación;
  - cancelación de solicitudes.
- **Contratos de escritura paralelos y vivos:**
  - `/sales/credit-notes`, `/sales/debit-notes` y `/sales/returns`, frente a la vía fiscal de la Spec 036;
  - `/purchasing/requisitions/{id}/lines`, frente a `/planning/requisitions/{id}/lines`.

## 8. Fronteras

- `ENTERPRISE_GOVERNMENT_FUNCTIONAL_OVERLAP = NO` en lo funcional. Gobierno tiene sus propios bancos, cuentas, tasas oficiales, comisiones de contratación, autoridad, auditoría institucional y alertas atípicas, paralelos a Enterprise. Ninguno cubre un requisito Enterprise ni se contó.
- Duplicados internos de Enterprise que se deben resolver:
  - «Regulatorio › Aprobaciones» heredado, frente al motor de aprobaciones;
  - dos entradas «Auditoría» en el menú;
  - conductor duplicado entre `drivers` y `transport_drivers`.
- Ni P1 ni P2 avanzaron ni se fusionaron durante el ciclo: `origin/develop` sigue en `b726c1da`.

## 9. Siguientes verticales

Ver `ENTERPRISE_COMPLETION_DAG.md` y `specs/enterprise-rebaseline/evidence/NEXT_VERTICALS.md`.

1. **V4** INVENTORY-LEDGER-VALUATION-INTEGRITY.
2. **V1** FISCAL-EMISSION-INTEGRITY ◆.
3. **V7** TREASURY-CASH-BANK-INTEGRITY.
4. **V6** TENANT-SCOPE-AND-SEGREGATION ◆.
5. **V2** RECEIVABLES-PAYABLES-APPLICATION-INTEGRITY.

◆ = necesita antes la decisión de la dueña o de ChatGPT (paquete D0).
