# MATRIZ REQUERIMIENTO → 56 SPECS

Fuente: Vol. 1 §4/§5/§7/§9, Vol. 2 §1/§3/§4/§5, DOCX de proceso (2026-08-25).

## Vol. 1 §4 — Alcance funcional (13 módulos)

| Módulo del requerimiento | Spec(s) maestra(s) | Cobertura |
|---|---|---|
| Inicio: dashboard, tareas, alertas, vencimientos, indicadores | 049, **047** | ◐ dashboard sí; tareas y alertas ✖ |
| Maestros: organización, terceros, productos, servicios, catálogos, **comercial**, financiero, fiscal, regulatorio | 007-014 | ◐ falta **012 comercial** |
| Compras: requisición→CxP | 015-017, 019, 027, 028 | ◐ |
| Ventas: cotización→CxC | 029-037 | ◐ |
| Inventario y logística | 022-026 | ◐ |
| CxC | 037 | ✔ |
| CxP | 028 | ✔ |
| Tesorería | 038 | ✔ |
| Fiscal | 039-043 | ◐ LEGAL_BLOCKER |
| Regulación | 044 | ✔ |
| **Aprobaciones** | **045** | ◐ disperso |
| Seguridad: usuarios, roles, acciones, alcances, sesiones, **MFA**, segregación | 002, 003 | ◐ MFA ✖ |
| Auditoría | 051 | ◐ |
| Reportes | 050 | ✔ |

## Vol. 1 §7 — Maestros

| Dominio | Requisito | Spec | Cobertura |
|---|---|---|---|
| Organización | Empresa, sucursal, establecimiento, almacén, ubicación, **centro de costo**, **unidad de negocio**, período | 007, 008 | ◐ |
| Terceros | Entidad común + extensiones | 009 | ✔ |
| Productos | Multirrubro, plantillas, atributos, unidades, presentaciones | 010, 011 | ◐ |
| Servicios | Modalidad, unidad de facturación, recurrencia, contrato, evidencia | 010 | ◐ recurrencia y contrato ✖ |
| **Comercial** | **Listas de precios, reglas, descuentos, comisiones, condiciones, crédito, zonas, rutas** | **012** | ✖ **sin Spec** |
| Financiero | Monedas, tasas, bancos, cuentas, cajas, métodos, instrumentos | 013 | ✔ |
| Fiscal | IVA, retenciones, ISLR, IGTF, series, correlativos, lotes, **imprentas**, perfiles | 014, 042 | ✔ |
| Regulatorio | Organismos, permisos, registros, perfiles, vehículos, certificados | 014, 044 | ✔ |

## Vol. 2 §1 — Menú canónico (20 ramas)

| Rama | Spec | Estado en el producto |
|---|---|---|
| Inicio | 049, 047 | ◐ falta Mis tareas / Mis aprobaciones / Alertas |
| Maestros/Organización | 007 | ◐ falta Centros de costo, Unidades de negocio |
| Maestros/Terceros | 009 | ✔ |
| Maestros/Productos y servicios | 010, 011 | ✔ |
| **Maestros/Comercial** | **012** | ✖ **rama entera ausente** |
| Maestros/Financiero | 013 | ✔ |
| Maestros/Fiscal | 014 | ✔ |
| Maestros/Regulatorio | 014 | ✔ |
| Compras | 015-017, 019 | ✔ |
| Ventas | 029-036 | ◐ falta bandeja de Crédito |
| Inventario y logística | 022-026 | ◐ falta Picking real |
| CxC / CxP | 037, 028 | ✔ (anidadas) |
| Tesorería | 038 | ✔ |
| Fiscal | 039-043 | ◐ falta Contingencia |
| Regulación y traslados | 044 | ✔ |
| Reportes | 050 | ✔ |
| **Aprobaciones** | **045** | ✖ solo regulatorio |
| Seguridad | 002, 003 | ◐ falta MFA, alcances |
| Auditoría | 051 | ◐ |
| **Configuración del sistema** | **048, 052, 053, 047** | ✖ solo `/diagnostico` |

## DOCX — Procesos operativos (fuente más reciente, 2026-08-25)

| Etapa documentada | Spec | Cobertura |
|---|---|---|
| Importación completa (12 etapas) | 018 | ✖ 0/12 |
| Recepción física (**12 etapas**, no 10) | 019 (8) · 020 (3) · 022 (1) | ✔ 11/12 (2026-09-03): 8 de 019 y 3 de 020; falta la 12 (022) |
| Confirmación de inventario recibido (11 etapas) | 021 | ◐ 2/11 |
| Clasificación y ubicación en almacén (10 etapas) | 022 | ✖ 0/10 |
| Zonas A–E | 008 | ✖ |
| Toma del pedido (7 etapas) | 029, 030 | ◐ 4/7 |
| Recepción en almacén y cola (4 etapas) | 031 | ✖ 0/4 |
| Ruta de picking (6 etapas) | 031 | ✖ 0/6 |
| Preparación física (8 etapas) | 032 | ◐ 2/8 |
| Consolidación (4 etapas) | 032 | ✖ 0/4 |
| Confirmación de pedido (8 etapas) | 033 | ✖ 0/8 |
| Liberación para facturación (3 etapas) | 034 | ✖ 0/3 |
| Facturación (6 etapas) | 034 | ◐ 4/6 |
| Despacho final (6 etapas) | 035 | ◐ 4/6 |

## Requisitos documentados SIN Spec en el repositorio

| Requisito | Fuente | Spec maestra que lo cubriría |
|---|---|---|
| Maestros comerciales completos | Vol. 1 §7, Vol. 2 §1 | 012 |
| Importaciones | DOCX Importación §1 | 018 |
| Confirmación independiente de pedido | DOCX Pedido §6-7 | 033 |
| Notificaciones, tareas y alertas | Vol. 2 §1 (Inicio) | 047 |
| Gestión documental y adjuntos | Vol. 1 §3 (evidencia), DOCX | 046 |
| Motor transversal de aprobaciones y delegaciones | Vol. 1 §4, Vol. 2 §1 | 045 |
| Configuración del sistema (correo, impresión, integraciones, storage, notificaciones, monitoreo, respaldos) | Vol. 2 §1 | 047, 048, 052, 053 |
| Centros de costo y unidades de negocio | Vol. 2 §3 | 007 |
| Zonas A–E, nivel y posición | DOCX Importación §4 | 008 |

**Total: 9 bloques de requisito documentado sin Spec que los gobierne.**

Incidencias de recepción salió de esta tabla el 2026-09-03: la Spec 020 la gobierna e implementa.

## SPEC057 — Gestión Integral de Activos Fijos (incorporada el 2026-10-07)

| Requisito | Fuente | Spec maestra |
|---|---|---|
| Políticas y maestros de activos; alta/capitalización; ficha patrimonial; componentes; costo inicial multimoneda; activo en construcción; ubicación, custodia, historial y etiquetado; libros contables/fiscales configurables; depreciación, vida útil y valor residual; mejoras; revaluación; deterioro; transferencias; inventario físico; desincorporación; documentos, garantías y seguros; mantenimiento mínimo; eventos contables y cierres; SoD; multiempresa; auditoría; reportes | `requerimientos/KONTROL_SPEC057_Ingenieria_Requerimientos_Activos_Fijos.pdf` §4–§26 | **057** (`PLANNED / NOT_STARTED`) |

Regla de ownership (PDF §28): la **023 Inventario/Kardex no es dueña** del activo fijo; puede aportar el
origen cuando una adquisición pasa por inventario, pero el activo patrimonial tiene ledger y ciclo
de vida propios. Integraciones declaradas: 003, 006, 007, 008, 009, 010, 013, 015–017, 018, 019, 026,
027, 043, 045, 046, 047, 048, 049, 050, 051, 052, 053, 054, 055. Exclusiones v1 (§31): CMMS avanzado,
telemetría/IoT, GPS, combustible, flotas, mantenimiento predictivo, leasing e IFRS 16 completos,
inmobiliaria integral, CAPEX completo, módulo asegurador, tasación automática.
