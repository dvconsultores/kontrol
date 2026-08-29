# MAPA DE EQUIVALENCIAS — 12 SPECS ACTUALES ↔ 56 SPECS MAESTRAS

> Regla aplicada: **no renombrar**. Las Specs existentes se conservan; el catálogo de 56 es el
> universo de control funcional.

| Spec maestra | Spec actual equivalente | Cobertura | Observación |
|---|---|---:|---|
| 001 Fundación | `001-fundacion` | 90 % | Falta validación Docker/PG real |
| 002 Seguridad y sesiones | `001-fundacion` | 85 % | MFA declarado y no construido |
| 003 Usuarios/roles/alcance | `001-fundacion` + `012` (T-01/T-02) | 70 % | Alcances sin UI |
| 004 Licenciamiento | `001-fundacion` + `010-licenciamiento-central` | 85 % | Dos Specs, una función — cohesión aceptable |
| 005 Design System | `001-fundacion` | 90 % | Cubierta y verificada (axe 19/19, responsive 198/198) |
| 006 Auditoría/observabilidad | `001-fundacion` + `009-reportes-auditoria` | 65 % | Instrumentación incompleta |
| 007 Organización | `001-fundacion` | 65 % | Centros de costo y unidades de negocio fuera |
| 008 Almacenes físicos | `001-fundacion` | 35 % | Solo maestro plano |
| 009 Terceros | `002-maestros` | 80 % | — |
| 010 Productos y servicios | `002-maestros` | 80 % | — |
| 011 Unidades/presentaciones | `002-maestros` | 45 % | Maestro sí, transacción no |
| **012 Maestros comerciales** | **ninguna** | **0 %** | **Requisito huérfano** |
| 013 Maestros financieros | `006-tesoreria` | 85 % | — |
| 014 Maestros fiscales/regulatorios | `007-nucleo-fiscal` + `008-regulacion-traslados` | 78 % | — |
| 015 Requisiciones | `004-compras-cuentas-por-pagar` | 55 % | Sin planificación de demanda |
| 016 Cotización proveedores | `004-compras` | 75 % | — |
| 017 Orden de compra | `004-compras` | 85 % | — |
| **018 Importaciones** | **ninguna** | **0 %** | **Requisito huérfano (DOCX)** |
| 019 Recepción física | `004-compras` | 50 % | Recepción contable, no física |
| **020 Incidencias de recepción** | **ninguna** | **0 %** | **Requisito huérfano (DOCX)** |
| 021 Confirmación de inventario recibido | `003-inventario-logistica` (parcial) | 30 % | Estados sí, proceso no |
| 022 Put-away | `003-inventario-logistica` (parcial) | 20 % | Columna sí, proceso no |
| 023 Núcleo inventario/Kardex | `003-inventario-logistica` | 88 % | Núcleo sólido |
| 024 Lotes/seriales | `003-inventario-logistica` | 85 % | — |
| 025 Transferencias/conteos/ajustes | `003-inventario-logistica` | 85 % | — |
| 026 Costos y valoración | `003-inventario-logistica` | 60 % | Sin landed cost |
| 027 Factura proveedor y match | `004-compras` | 85 % | Mejor cadena trazada del sistema |
| 028 CxP y pagos | `004-compras` | 85 % | — |
| 029 Cotización y pedido comercial | `005-ventas-cuentas-por-cobrar` | 55 % | Sin pedido como entidad |
| 030 Crédito y reserva | `005-ventas` + `003-inventario` | 75 % | Decisión de momento de reserva pendiente |
| 031 Cola y ruta de picking | `005-ventas` (esqueleto) | 15 % | — |
| 032 Picking y consolidación | `005-ventas` (esqueleto) | 25 % | — |
| **033 Confirmación de pedido** | **ninguna** | **0 %** | **Requisito huérfano (DOCX)** |
| 034 Liberación y facturación | `005-ventas` + `007-nucleo-fiscal` | 55 % | Sin vínculo factura↔pedido |
| 035 Despacho y regulación | `005-ventas` + `008-regulacion` | 65 % | — |
| 036 Devoluciones/NC/ND | `004-compras` + `005-ventas` | 75 % | — |
| 037 CxC | `005-ventas` | 85 % | — |
| 038 Tesorería | `006-tesoreria` | 85 % | — |
| 039 Motor fiscal | `007-nucleo-fiscal` | 70 % | LEGAL_BLOCKER |
| 040 Retenciones | `007-nucleo-fiscal` + `004-compras` | 65 % | LEGAL_BLOCKER |
| 041 IGTF | `006-tesoreria` + `007-nucleo-fiscal` | 70 % | LEGAL_BLOCKER |
| 042 Documentos fiscales y contingencia | `007-nucleo-fiscal` | 73 % | Contingencia sin UI |
| 043 Libros y cierres | `007-nucleo-fiscal` | 75 % | LEGAL_BLOCKER |
| 044 SICA/SIGESAI/SACS | `008-regulacion-traslados` | 73 % | — |
| **045 Motor de aprobaciones** | disperso en 004/005/003/008 | 35 % | **Sin Spec propietaria** |
| **046 Gestión documental** | **ninguna** | **8 %** | **Requisito huérfano** |
| **047 Notificaciones y tareas** | **ninguna** | **5 %** | **Requisito huérfano** |
| 048 Integraciones | `010-licenciamiento-central` (parcial) | 25 % | Sin Spec transversal |
| 049 Dashboard y analítica | `009-reportes-auditoria` | 55 % | — |
| 050 Reportes | `009-reportes-auditoria` | 74 % | — |
| 051 Auditoría avanzada | `009-reportes-auditoria` + `001` | 65 % | — |
| 052 Instalador/actualización | `001-fundacion` | 57 % | — |
| 053 Backup/continuidad | `001-fundacion` | 32 % | — |
| 054 QA integral | `012-auditoria-integral-e2e` | 78 % | Spec de auditoría, no funcional |
| 055 Seguridad y hardening | `001-fundacion` + `012` | 65 % | Sin Spec propietaria |
| 056 Homologación y release | `011-homologacion-liberacion` | 73 % | LEGAL_BLOCKER |

## Recomendación por Spec existente

| Spec actual | Cubre maestras | Tamaño | Recomendación | Motivo |
|---|---|---|---|---|
| `001-fundacion` | 001,002,003,005,006,007,008,052,053,055 | **XL** | **SPLIT** | Mezcla fundación, seguridad, organización, almacenes, instalación y hardening. 10 maestras en una Spec impide verificación E2E clara y explica que 008/053/055 quedaran a medias. |
| `002-maestros` | 009,010,011,014(parc.) | L | KEEP | Cohesión razonable; 011 requiere extensión, no división. |
| `003-inventario-logistica` | 021,022,023,024,025,026 | L | KEEP + EXTEND | Núcleo sólido; 021/022 deben crecer como Specs propias. |
| `004-compras-cuentas-por-pagar` | 015,016,017,019,027,028,036(parc.) | L | KEEP | La cadena mejor construida del sistema. |
| `005-ventas-cuentas-por-cobrar` | 029,030,031,032,034,035,036,037 | **XL** | **SPLIT** | Contiene los tres huecos mayores (031/032/033/034). Debe separarse comercial / preparación / facturación. |
| `006-tesoreria` | 013,038,041(parc.) | M | KEEP | — |
| `007-nucleo-fiscal` | 014,039,040,041,042,043 | L | KEEP | Cohesión fiscal correcta (P4). |
| `008-regulacion-traslados` | 044,035(parc.) | M | KEEP | — |
| `009-reportes-auditoria` | 049,050,051,006(parc.) | M | KEEP | — |
| `010-licenciamiento-central` | 004,048(parc.) | M | KEEP | — |
| `011-homologacion-liberacion` | 056 | S | KEEP | — |
| `012-auditoria-integral-e2e` | 054 | L | KEEP | Spec de proceso QA, no funcional. |

## Recomendación de rebaseline

**Propuesta (no ejecutada):** no renumerar. Conservar `001-012` y **abrir Specs nuevas desde `014`**
para las maestras huérfanas, registrando en cada una su número maestro de referencia.

Motivo: renumerar 12 Specs con evidencia, convergencia y trazabilidad ya emitida destruiría la
cadena del Principio 3 a cambio de estética. El mapa de equivalencias cumple la misma función
sin coste.
