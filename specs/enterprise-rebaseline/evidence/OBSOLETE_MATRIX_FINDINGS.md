# OBSOLETE_MATRIX_FINDINGS — revalidación de las 92 filas de la matriz antigua

Matriz antigua: `docs/roadmap/enterprise-application-completion/SPONSOR_APPLICATION_COVERAGE_MATRIX.csv` (2026-11-10). Cada fila antigua se mapea a los requisitos nuevos que la cubren (columna `OLD_ROW` de `ENTERPRISE_REQUIREMENTS_REBASELINE.csv`) y su estado nuevo agregado se deriva así:

- **COMPLETE:** todos los requisitos que la cubren están COMPLETE.
- **COMPLETE_WITH_SPONSOR_POINT:** todos están COMPLETE salvo un punto pendiente del sponsor.
- **NOT_BUILT:** ninguno está construido.
- **PRODUCT_DEFECT:** alguno tiene un defecto.
- **PARTIAL:** cualquier otro caso.

Veredictos:

- **FALSE_POSITIVE:** la matriz decía más de lo que hay.
- **FALSE_NEGATIVE:** decía menos de lo que hay.
- **DEFECT_NOT_REGISTERED:** acertaba en el grado, pero no registraba el defecto.
- **CORRECT:** el estado antiguo coincide con el nuevo.

**Resultado:** `OLD_MATRIX_FALSE_POSITIVES=41` · `OLD_MATRIX_FALSE_NEGATIVES=13` · `DEFECT_NOT_REGISTERED=19` · `OBSOLETE_ROWS=73` de 92 · `ALL_92_OLD_CAPABILITIES_REVALIDATED=YES` (sin filas sin mapear).

## Las 42 FUNCTIONAL_SLICE_COMPLETE

Ninguna conserva ese estado: la matriz nueva no lo usa. Su reclasificación está en la tabla siguiente, filtrando `OLD_STATUS = FUNCTIONAL_SLICE_COMPLETE`.

| Fila | Módulo | Menú | Estado antiguo | Estado nuevo | Veredicto | Requisitos nuevos (desglose) |
|---|---|---|---|---|---|---|
| VOL2-001 | Inicio | Dashboard | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | INI-01 INI-02 (PARTIAL 1, PRODUCT_DEFECT 1) |
| VOL2-002 | Inicio | Mis tareas | FUNCTIONAL_SLICE_COMPLETE | COMPLETE | CORRECT | INI-03 (COMPLETE 1) |
| VOL2-003 | Inicio | Mis aprobaciones | FUNCTIONAL_SLICE_COMPLETE | COMPLETE | CORRECT | INI-04 (COMPLETE 1) |
| VOL2-004 | Inicio | Alertas | PARTIAL_PROCESS | PARTIAL | CORRECT | INI-05 (PARTIAL 1) |
| VOL2-005 | Inicio | Vencimientos | NOT_STARTED | PARTIAL | FALSE_NEGATIVE | INI-06 (PARTIAL 1) |
| VOL2-006 | Maestros/Organización | Empresas | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | ORG-01 ORG-09 (PARTIAL 2) |
| VOL2-007 | Maestros/Organización | Sucursales | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | ORG-02 (PARTIAL 1) |
| VOL2-008 | Maestros/Organización | Establecimientos | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | ORG-03 (PARTIAL 1) |
| VOL2-009 | Maestros/Organización | Almacenes | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | ORG-04 (PARTIAL 1) |
| VOL2-010 | Maestros/Organización | Ubicaciones | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | ORG-05 (PARTIAL 1) |
| VOL2-011 | Maestros/Organización | Centros de costo | NOT_STARTED | NOT_BUILT | CORRECT | ORG-06 (NOT_BUILT 1) |
| VOL2-012 | Maestros/Organización | Unidades de negocio | NOT_STARTED | NOT_BUILT | CORRECT | ORG-07 (NOT_BUILT 1) |
| VOL2-013 | Maestros/Terceros | Clientes, Proveedores, Transportistas, Conductores | OWNER_UAT_READY | PRODUCT_DEFECT | FALSE_POSITIVE | TER-01 TER-02 TER-03 TER-04 TER-05 TER-07 TER-08 TER-12 (PARTIAL 5, PRODUCT_DEFECT 2, COMPLETE 1) |
| VOL2-014 | Maestros/Terceros | Vendedores | NOT_STARTED | PARTIAL | FALSE_NEGATIVE | TER-06 (PARTIAL 1) |
| VOL2-015 | Maestros/Terceros | Beneficiarios | NOT_STARTED | PARTIAL | FALSE_NEGATIVE | TER-09 (PARTIAL 1) |
| VOL2-016 | Maestros/Terceros | Contactos y direcciones | OWNER_UAT_READY | PARTIAL | FALSE_POSITIVE | TER-10 TER-11 (COMPLETE 1, PARTIAL 1) |
| VOL2-017 | Maestros/Productos | Productos | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | PRD-01 PRD-11 PRD-12 PRD-14 PRD-15 (PARTIAL 3, PRODUCT_DEFECT 2) |
| VOL2-018 | Maestros/Productos | Servicios | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | PRD-02 PRD-03 (PARTIAL 1, PRODUCT_DEFECT 1) |
| VOL2-019 | Maestros/Productos | Sectores, rubros, categorías, familias, líneas | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | PRD-04 PRD-13 (PARTIAL 2) |
| VOL2-020 | Maestros/Productos | Plantillas | NOT_STARTED | PARTIAL | FALSE_NEGATIVE | PRD-05 (PARTIAL 1) |
| VOL2-021 | Maestros/Productos | Atributos | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | PRD-06 (PARTIAL 1) |
| VOL2-022 | Maestros/Productos | Marcas y modelos | NOT_STARTED | NOT_BUILT | CORRECT | PRD-07 PRD-08 (NOT_BUILT 2) |
| VOL2-023 | Maestros/Productos | Presentaciones | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | PRD-09 (PARTIAL 1) |
| VOL2-024 | Maestros/Productos | Unidades | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | PRD-10 (PRODUCT_DEFECT 1) |
| VOL2-025 | Maestros/Comercial | Listas y reglas de precios | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | COM-01 COM-02 (PRODUCT_DEFECT 1, PARTIAL 1) |
| VOL2-026 | Maestros/Comercial | Condiciones de pago | FRONTEND_SHELL | PARTIAL | CORRECT | COM-03 (PARTIAL 1) |
| VOL2-027 | Maestros/Comercial | Crédito | NOT_STARTED | PARTIAL | FALSE_NEGATIVE | COM-04 (PARTIAL 1) |
| VOL2-028 | Maestros/Comercial | Zonas y rutas | NOT_STARTED | PARTIAL | FALSE_NEGATIVE | COM-05 COM-06 (PARTIAL 2) |
| VOL2-029 | Maestros/Comercial | Comisiones | NOT_STARTED | NOT_BUILT | CORRECT | COM-07 (NOT_BUILT 1) |
| VOL2-030 | Maestros/Comercial | Descuentos | NOT_STARTED | PRODUCT_DEFECT | FALSE_NEGATIVE | COM-08 (PRODUCT_DEFECT 1) |
| VOL2-031 | Maestros/Financiero | Monedas y tasas | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | FIN-01 FIN-02 (PARTIAL 2) |
| VOL2-032 | Maestros/Financiero | Bancos, cuentas, cajas, métodos | PARTIAL_PROCESS | PARTIAL | CORRECT | FIN-03 FIN-04 FIN-05 FIN-06 (PARTIAL 4) |
| VOL2-033 | Maestros/Fiscal | Perfiles | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | FMA-01 (PRODUCT_DEFECT 1) |
| VOL2-034 | Maestros/Fiscal | IVA, retenciones, ISLR, IGTF | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | FMA-02 FMA-03 FMA-04 FMA-05 FMA-10 (PRODUCT_DEFECT 5) |
| VOL2-035 | Maestros/Fiscal | Series, correlativos, lotes, imprentas | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | FMA-06 FMA-07 FMA-08 FIS-10 (PRODUCT_DEFECT 3, NOT_BUILT 1) |
| VOL2-036 | Maestros/Fiscal | Plantillas fiscales | NOT_STARTED | NOT_BUILT | CORRECT | FMA-09 (NOT_BUILT 1) |
| VOL2-037 | Maestros/Regulatorio | Organismos, tipos, registros | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | REGM-01 REGM-02 REGM-03 REGM-04 (PARTIAL 3, PRODUCT_DEFECT 1) |
| VOL2-038 | Maestros/Regulatorio | Vehículos y certificados | PARTIAL_PROCESS | PARTIAL | CORRECT | REGM-05 REGM-06 (PARTIAL 2) |
| VOL2-039 | Compras | Requisiciones | PARTIAL_PROCESS | PARTIAL | CORRECT | CMP-01 CMP-02 (PARTIAL 2) |
| VOL2-040 | Compras | Solicitudes y ofertas | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | CMP-03 CMP-04 (PARTIAL 2) |
| VOL2-041 | Compras | Comparación de ofertas | NOT_STARTED | PARTIAL | FALSE_NEGATIVE | CMP-05 CMP-06 (PARTIAL 1, COMPLETE 1) |
| VOL2-042 | Compras | Órdenes | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | CMP-07 CMP-08 (PRODUCT_DEFECT 1, PARTIAL 1) |
| VOL2-043 | Compras | Recepciones | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | CMP-09 CMP-10 (COMPLETE 1, PARTIAL 1) |
| VOL2-044 | Compras | Incidencias de recepción | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | CMP-11 (PARTIAL 1) |
| VOL2-045 | Compras | Facturas | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | CMP-12 CMP-13 CMP-14 (PARTIAL 2, PRODUCT_DEFECT 1) |
| VOL2-046 | Compras | Devoluciones | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | CMP-16 (PRODUCT_DEFECT 1) |
| VOL2-047 | Importaciones | Expediente, negociación y documentación (IMP-06, 07, 08) | PARTIAL_PROCESS | COMPLETE | FALSE_NEGATIVE | IMP-07 IMP-08 IMP-09 (COMPLETE 3) |
| VOL2-048 | Importaciones | Seguimiento, agente, despacho, anticipo o pago y correcciones (IMP-09 a 12) | PARTIAL_PROCESS | COMPLETE | FALSE_NEGATIVE | IMP-10 IMP-11 IMP-12 IMP-13 (COMPLETE 4) |
| VOL2-049 | Importaciones | Arribo, recepción, diferencias, confirmación y ubicación desde el expediente | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | IMP-18 IMP-19 IMP-20 IMP-21 IMP-22 IMP-23 IMP-24 IMP-25 IMP-26 IMP-27 IMP-28 IMP-29 IMP-30 IMP-31 IMP-32 IMP-33 IMP-34 IMP-35 IMP-36 IMP-37 IMP-38 IMP-39 IMP-40 IMP-41 IMP-42 (COMPLETE 22, PARTIAL 1, PRODUCT_DEFECT 1, SPONSOR_VALIDATION_REQUIRED 1) |
| VOL2-050 | Importaciones | Gastos de importación (landed cost) | PARTIAL_PROCESS | COMPLETE | FALSE_NEGATIVE | IMP-14 IMP-15 IMP-16 IMP-17 (COMPLETE 4) |
| VOL2-051 | Ventas | Cotizaciones | PARTIAL_PROCESS | PARTIAL | CORRECT | VEN-01 VEN-02 (PARTIAL 2) |
| VOL2-052 | Ventas | Pedidos y órdenes | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | VEN-03 VEN-06 PED-01 (PARTIAL 2, PRODUCT_DEFECT 1) |
| VOL2-053 | Ventas | Crédito | NOT_STARTED | PARTIAL | FALSE_NEGATIVE | VEN-04 VEN-05 (PARTIAL 2) |
| VOL2-054 | Ventas | Preparación | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | VEN-07 PED-02 PED-05 PED-06 (PARTIAL 3, PRODUCT_DEFECT 1) |
| VOL2-055 | Ventas | Despachos | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | VEN-08 VEN-09 PED-09 (PRODUCT_DEFECT 2, SPONSOR_VALIDATION_REQUIRED 1) |
| VOL2-056 | Ventas | Facturas | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | VEN-10 VEN-11 PED-07 PED-08 (PRODUCT_DEFECT 3, PARTIAL 1) |
| VOL2-057 | Ventas | Devoluciones | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | VEN-15 INV-12 (PARTIAL 2) |
| VOL2-058 | Ventas | Notas | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | VEN-14 FIS-03 (PRODUCT_DEFECT 2) |
| VOL2-059 | Inventario | Existencias | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | INV-01 (PRODUCT_DEFECT 1) |
| VOL2-060 | Inventario | Kardex | PARTIAL_PROCESS | PARTIAL | CORRECT | INV-02 (PARTIAL 1) |
| VOL2-061 | Inventario | Reservas | FUNCTIONAL_SLICE_COMPLETE | COMPLETE | CORRECT | INV-03 (COMPLETE 1) |
| VOL2-062 | Inventario | Picking | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | PED-03 PED-04 INV-04 (PARTIAL 3) |
| VOL2-063 | Inventario | Transferencias | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | INV-05 (PRODUCT_DEFECT 1) |
| VOL2-064 | Inventario | Cargos y descargos | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | INV-06 (PRODUCT_DEFECT 1) |
| VOL2-065 | Inventario | Ajustes | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | INV-07 INV-18 (PRODUCT_DEFECT 1, PARTIAL 1) |
| VOL2-066 | Inventario | Conteos | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | INV-08 (PRODUCT_DEFECT 1) |
| VOL2-067 | Inventario | Costos | PARTIAL_PROCESS | PARTIAL | CORRECT | INV-09 INV-14 (PARTIAL 1, COMPLETE 1) |
| VOL2-068 | CxC | Documentos, cobros, anticipos, aplicaciones | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | VEN-12 VEN-13 CXC-01 CXC-02 CXC-03 CXC-04 CXC-08 (PRODUCT_DEFECT 6, PARTIAL 1) |
| VOL2-069 | CxC | Aging y cobranza | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | CXC-05 CXC-06 CXC-07 (PARTIAL 2, NOT_BUILT 1) |
| VOL2-070 | CxP | Documentos, pagos, anticipos, aplicaciones | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | CMP-15 CXP-01 CXP-03 CXP-04 CXP-05 CXP-07 (PRODUCT_DEFECT 4, PARTIAL 2) |
| VOL2-071 | CxP | Programación y aging | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | CXP-02 CXP-06 (PARTIAL 1, PRODUCT_DEFECT 1) |
| VOL2-072 | Tesorería | Caja y arqueos | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | TES-01 (PRODUCT_DEFECT 1) |
| VOL2-073 | Tesorería | Bancos, ingresos, egresos | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | TES-02 TES-03 (PRODUCT_DEFECT 1, PARTIAL 1) |
| VOL2-074 | Tesorería | Transferencias y depósitos | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | TES-04 TES-05 (PRODUCT_DEFECT 1, PARTIAL 1) |
| VOL2-075 | Tesorería | Conciliaciones | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | TES-06 (PRODUCT_DEFECT 1) |
| VOL2-076 | Fiscal | Emisión | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | FIS-01 FIS-02 (PRODUCT_DEFECT 2) |
| VOL2-077 | Fiscal | Retenciones y comprobantes | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | FIS-04 FIS-05 (PRODUCT_DEFECT 1, PARTIAL 1) |
| VOL2-078 | Fiscal | Libros y cierres | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | FIS-06 FIS-07 (PRODUCT_DEFECT 1, PARTIAL 1) |
| VOL2-079 | Fiscal | Contingencia | NOT_STARTED | NOT_BUILT | CORRECT | FIS-08 (NOT_BUILT 1) |
| VOL2-080 | Fiscal | Exportaciones | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | FIS-09 (PARTIAL 1) |
| VOL2-081 | Regulación | Guías y permisos | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | REG-01 REG-02 REG-07 (PRODUCT_DEFECT 2, PARTIAL 1) |
| VOL2-082 | Regulación | Validaciones y despachos regulados | PARTIAL_PROCESS | PRODUCT_DEFECT | DEFECT_NOT_REGISTERED | REG-03 REG-04 REG-09 (PARTIAL 2, PRODUCT_DEFECT 1) |
| VOL2-083 | Regulación | Vencimientos | NOT_STARTED | PARTIAL | FALSE_NEGATIVE | REG-06 (PARTIAL 1) |
| VOL2-084 | Reportes | Ejecutivos, operativos, financieros, fiscales, regulatorios | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | RPT-01 RPT-02 RPT-03 RPT-04 (PARTIAL 2, NOT_BUILT 1, PRODUCT_DEFECT 1) |
| VOL2-085 | Reportes | Auditoría | PARTIAL_PROCESS | PARTIAL | CORRECT | RPT-05 (PARTIAL 1) |
| VOL2-086 | Aprobaciones | Bandejas, excepciones y delegaciones | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | APR-01 APR-02 APR-03 APR-04 APR-05 APR-06 APR-07 (PARTIAL 6, PRODUCT_DEFECT 1) |
| VOL2-087 | Seguridad | Usuarios, roles, sesiones, MFA | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | SEG-01 SEG-02 SEG-04 SEG-05 (PARTIAL 3, COMPLETE 1) |
| VOL2-088 | Seguridad | Alcances | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | SEG-03 (PARTIAL 1) |
| VOL2-089 | Auditoría | Timeline, datos, accesos, impresiones, exportaciones | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | AUD-01 AUD-02 AUD-03 AUD-04 AUD-05 (COMPLETE 2, PARTIAL 3) |
| VOL2-090 | Auditoría | Incidentes | NOT_STARTED | NOT_BUILT | CORRECT | AUD-06 (NOT_BUILT 1) |
| VOL2-091 | Documentos | Biblioteca y tipos documentales | FUNCTIONAL_SLICE_COMPLETE | PRODUCT_DEFECT | FALSE_POSITIVE | DOC-01 DOC-02 DOC-03 DOC-04 (PARTIAL 3, PRODUCT_DEFECT 1) |
| VOL2-092 | Configuración | Correo, impresión, integraciones, almacenamiento, monitoreo, respaldos | FUNCTIONAL_SLICE_COMPLETE | PARTIAL | FALSE_POSITIVE | CFG-01 CFG-02 CFG-03 CFG-04 CFG-05 CFG-06 CFG-07 CFG-08 (NOT_BUILT 2, PARTIAL 6) |

**Reclasificación de las 42 FUNCTIONAL_SLICE_COMPLETE:** PARTIAL 20, PRODUCT_DEFECT 19, COMPLETE 3. Ninguna llega a OWNER_UAT_READY.

**Veredictos totales:** FALSE_POSITIVE 41, DEFECT_NOT_REGISTERED 19, CORRECT 19, FALSE_NEGATIVE 13.

## Hallazgos de la matriz antigua que no dependen del estado

1. **Filas OWNER_UAT_READY de Terceros (VOL2-013 y VOL2-016).** Su E2E se registró solo sobre SQLite. Además hay dos defectos: TER-02 (RIF duplicable) y TER-03 (campos del cliente que ningún proceso lee). Vendedor y beneficiario no tienen extensión.
2. **Columnas BACKEND/DATABASE en «NO» con el motor ya construido.** Pasa en VOL2-003, 045 y 086, que existen con el motor de aprobaciones (Spec 045) y con la factura de proveedor.
3. **Rutas citadas inexistentes.** `/purchasing/incidents` no existe; las reales son `/purchasing/incidencias` y `/purchasing/receipts/{id}/incidencias`.
4. **Menú real con entradas que la matriz no listaba:** Confirmación, Put-away, Tipos de movimiento, Lotes, Seriales, Necesidades de reposición, Notas de crédito de compras, Confirmación de pedido, Facturación, IGTF, Cambio, Reembolsos, Posición, Fuentes de tasa, Políticas y Delegaciones.
5. **Matriz de la Spec 018.** IMP-21 pasa de COMPLETE a PARTIAL: la pantalla de incidencias no permite adjuntar evidencia. IMP-28 pasa de COMPLETE a PRODUCT_DEFECT: una recepción parcialmente aceptada aparece como «recibida y ubicada». Ningún COMPLETE de la Spec 018 llega a OWNER_UAT_READY, por A11Y-IMPORT-SCROLL-REGIONS.
6. **Inicio → Vencimientos.** Era NOT_STARTED y hoy es PARTIAL: hay contadores en el dashboard, pero no hay pantalla.
