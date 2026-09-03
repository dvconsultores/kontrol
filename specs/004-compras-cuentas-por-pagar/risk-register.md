# REGISTRO DE RIESGOS — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Responsable | Especialista en gestión de riesgos |
| Ruta | `specs/004-compras-cuentas-por-pagar/risk-register.md` |

Formato: | ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |

| ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |
|---|---|---|---|---|---|---|
| RSK-004-01 | Factura del proveedor duplicada | Media | Alto | Clave de duplicidad + idempotencia + excepciones documentadas | Backend | Activo |
| RSK-004-02 | Aplicación que excede el saldo de CxP | Media | Crítico | Aplicaciones atómicas con bloqueo; no excede origen/destino | Backend | Activo |
| RSK-004-03 | Pago duplicado por reintentos | Media | Alto | `Idempotency-Key` en pago/aplicación | Backend | Activo |
| RSK-004-04 | Recepción sin actualizar inventario o duplicando lógica | Media | Alto | Invoca 003 `receive`; sin duplicar saldos/costos | Arquitecto | Activo |
| RSK-004-05 | Conciliación triple con diferencias no resueltas | Media | Alto | Diferencias explícitas + resolución auditada; POSTED condicionado | Contador | Activo |
| RSK-004-06 | Retención calculada mal (porcentajes hardcodeados) | Media | Alto | Reglas versionadas; motor fiscal en 007 (P8) | Contador | Activo |
| RSK-004-07 | Aprobaciones sin segregación | Baja | Crítico | Reglas de aprobación versionadas + segregación (DOC-02 §12) | Seguridad | Activo |
| RSK-004-08 | Aislamiento multiempresa débil | Baja | Crítico | company_id en cada agregado + pruebas negativas | Seguridad | Activo |
| RSK-004-09 | Acoplamiento con 003/006 | Media | Alto | Contratos de API v1 (receive; Payment/Application) | Arquitecto | Activo |
| RSK-004-10 | Snapshot ausente altera histórico | Media | Alto | Snapshot por línea (producto/precio/impuesto/tasa) | Datos | Activo |
| RSK-004-11 | Implementación sin dependencias previas | Media | Alto | Requiere 001 certificada + 002/003 implementados + autorización | Producto | Activo |

## Estado

| Elemento | Estado |
|---|---|
| Registro de riesgos | ✔ |
| Controles asignados | ✔ |
| Aprobación | Pendiente |

---

# RIESGOS — SPEC 019 (2026-09-03)

| ID | Riesgo | Impacto | Mitigación | Estado |
|---|---|---|---|---|
| R-019-01 | El asiento de inventario registra la cantidad tecleada en vez de la base | Inventario falso desde la primera recepción en cajas | El saldo acumula la cantidad base; prueba de la caja ×12 de extremo a extremo | **Cerrado** |
| R-019-02 | La presentación con la que llegó la mercancía no se captura | Dato irrecuperable: el camión se fue | Captura obligatoria en la línea, con factor congelado | **Cerrado** |
| R-019-03 | Un cambio del maestro reinterpreta una recepción histórica | Historia falsificada (P5) | Factor congelado en la línea; prueba de invariancia | **Cerrado** |
| R-019-04 | Bultos y daño observados se pierden | Sin base para la incidencia de 020 | Bultos declarados y contados; observación por línea que sobrevive a la aceptación | **Cerrado** |
| R-019-05 | Dos recepciones simultáneas contra la misma línea de orden | Una acumulación perdida; orden dada por recibida sin estarlo | Bloqueo de la línea antes de acumular | **Cerrado** |
| R-019-06 | Aceptar dos veces duplica el asiento | Inventario inflado | Máquina de estados; prueba de doble aceptación | **Cerrado** |
| R-019-07 | Recibir contra la línea de otra orden | Recepción cruzada | La línea debe pertenecer a la orden de la recepción | **Cerrado** |
| R-019-08 | Los seriales no se materializan | Trazabilidad rota | Normalización a texto separado por comas en un solo punto | **Cerrado** |
| R-019-09 | La recepción invade el put-away o la confirmación | Fronteras rotas entre Specs | Ubicación nula; sin estados de mercancía nuevos; guardias estructurales | **Cerrado** |
| R-019-10 | La corrección del saldo cambia el comportamiento de otros llamantes | Regresión silenciosa en compras, ventas o ajustes | Sin presentación el factor es 1 y las cantidades coinciden; regresión completa | **Cerrado** |

---

# RIESGOS — SPEC 020 (2026-09-03)

| ID | Riesgo | Impacto | Mitigación | Estado |
|---|---|---|---|---|
| R-020-01 | Tratar como tipo de incidencia lo que era dato de 019, estado de calidad o tratamiento | Vocabulario inventado; ocho categorías falsas en un registro cerrado | Cinco tipos extraídos del contrato; los ocho descartados quedan nombrados y la base los rechaza | **Cerrado** |
| R-020-02 | Volver a pedir el daño y el faltante que 019 ya capturó | Doble captura, dos verdades para el mismo hecho | La incidencia se apoya en la observación de la línea; prueba de que no se re-pregunta | **Cerrado** |
| R-020-03 | Registrar una cantidad afectada mayor que la recibida o la ordenada | Incidencia imposible; ajuste que descuadra el inventario | Tope por tipo —faltante contra lo ordenado, el resto contra lo recibido— probado en ambos bordes | **Cerrado** |
| R-020-04 | Texto libre como única autoridad de la resolución | Decisión no auditable ni verificable | Resolución de un conjunto cerrado; el motivo acompaña, no sustituye | **Cerrado** |
| R-020-05 | Dos resoluciones simultáneas sobre la misma incidencia | Dos desenlaces contradictorios para un mismo hecho | Bloqueo de fila y máquina de estados terminal; carrera probada con dos conexiones | **Cerrado** |
| R-020-06 | El ajuste autorizado se aplica sin aprobación | Ajuste de inventario sin quien lo respalde | `AJUSTE_AUTORIZADO` exige solicitud de aprobación aprobada; prueba de que sin ella no resuelve | **Cerrado** |
| R-020-07 | La incidencia sustituye el bloqueo de confirmación de 021 | Frontera rota: 020 decidiendo lo que 021 gobierna | 020 no toca el bloqueo; guardia estructural sobre el módulo de 021 | **Cerrado** |
| R-020-08 | La resolución mueve inventario o ubica mercancía | Invasión de 021, 022 y 023 | Ninguna resolución escribe asientos; guardias sobre `record_movement` y `location_id` | **Cerrado** |
| R-020-09 | La incidencia de línea y la documental comparten forma | Filas ambiguas: documental con línea, o de línea sin cantidad | Restricción condicional por tipo en ORM y migración; probada por los dos lados | **Cerrado** |
| R-020-10 | Una incidencia anulada sigue consumiendo cantidad afectada | Tope agotado por incidencias muertas; faltantes legítimos rechazados | Solo los estados vivos suman; prueba de que anular libera la cantidad | **Cerrado** |
| R-020-11 | La tabla creada por la migración no admite el insert de la aplicación | Instalación real inutilizable: toda incidencia falla con `NotNullViolation` | `server_default` en la migración, como el resto del repositorio; prueba nueva que inserta con el ORM contra la tabla que produce Alembic | **Cerrado** — encontrado por la e2e |
| R-020-12 | El nombre accesible de un campo contradice su etiqueta visible | Quien navega por voz nombra algo que no existe (WCAG 2.5.3) | Se quitó el `aria-label` que pisaba la asociación de `FormField` en los quince selectores de cinco páginas | **Cerrado** — encontrado por la e2e |
