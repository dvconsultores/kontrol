# KONTROL — GAP ANALYSIS INTEGRAL Y ROADMAP MAESTRO

| Campo | Valor |
|---|---|
| Iniciativa | `specs/013-gap-analysis-roadmap-maestro/` |
| Rama · HEAD | `develop` · `def2b52` |
| Fecha | 2026-08-29 |
| Universo de control | **56 Specs maestras** |
| Método | Estático + dinámico, no destructivo; pytest y vitest ejecutados en esta auditoría |
| Estado | **AUDITORÍA COMPLETADA — SIN IMPLEMENTACIÓN** |

---

# 1. RESUMEN EJECUTIVO

KONTROL tiene una **capa administrativa sólida y una capa operativa de almacén prácticamente
inexistente**. Esa es la conclusión central y explica por qué las auditorías anteriores daban
`CONDITIONAL GO` sin equivocarse: auditaban el producto contra las Specs escritas, y las Specs
escritas no cubren el proceso operativo real.

Lo construido está bien construido. 223 pruebas de backend y 210 de frontend pasan; el núcleo de
inventario es reconstruible desde movimientos; la cadena de compras está correctamente trazada con
conciliación triple; el motor fiscal tiene reglas versionadas con fuente; la navegación no tiene una
sola ruta huérfana. No hay chapuza.

Lo que falta no son detalles: **falta el tramo que va desde que la mercancía llega hasta que sale**.
Recepción física, incidencias, conteo, cuarentena, liberación, ubicación por zonas, cola de
preparación, ruta de picking, confirmación independiente y liberación para facturación. De las 137
etapas de proceso documentadas en los dos documentos de agosto de 2026, **30 están cubiertas (22 %)**.

Hay además tres brechas de trazabilidad que ninguna auditoría previa registró porque buscaban
código sin interfaz, no requisito sin código: **maestros comerciales**, **importaciones** y
**confirmación de pedido** son requisitos documentados sin ninguna Spec que los gobierne.

Y hay un hallazgo de veracidad: **KAUD-001, el único CRITICAL de la auditoría anterior, figura
como RESUELTO y cubre 7 de 9 módulos.** Los dos que faltan contienen exactamente las entidades que
el hallazgo original enumeraba.

---

# 2. ESTADO GENERAL DEL PROYECTO

| Dimensión | Medición |
|---|---:|
| LOC backend / frontend | 14.820 / 15.356 |
| Endpoints · rutas · páginas · menús | 275 · 78 · 77 · 72 |
| Tablas · migraciones | 144 · 14 (cadena lineal, head único `0014`) |
| pytest / vitest | **223 ✓ / 210 ✓** (ejecutados aquí) |
| Módulos con auditoría instrumentada | 7 de 9 |
| Etapas de proceso documentadas cubiertas | **30 de 137 (22 %)** |
| Specs existentes | 12 (`001`-`012`) |
| Índice global de integración | 62/100 *(referencia; leer con §12-15)* |
| Madurez máxima alcanzada | **M4** — ninguna Spec en M5 |

---

# 3. TOTAL DE SPECS

**56 Specs maestras** evaluadas una a una contra código, base de datos, pruebas y documentos fuente.
Detalle completo en [`56-specs-gap-analysis.md`](56-specs-gap-analysis.md).

---

# 4. DISTRIBUCIÓN POR ESTADO

| Estado | Cantidad |
|---|---:|
| COMPLETE_100 | **0** |
| SUBSTANTIALLY_COMPLETE | **25** |
| PARTIAL | **20** |
| SKELETON_ONLY | **5** |
| FRONTEND_ONLY | 0 |
| BACKEND_ONLY | 0 |
| DATABASE_ONLY | **1** |
| BROKEN | 0 |
| NOT_STARTED | **5** |
| FUTURE_SCOPE | 0 |
| BLOCKED | 0 |
| OUT_OF_SCOPE | 0 |
| **TOTAL** | **56** ✔ |

`IMPLEMENTED_WITHOUT_SPEC` actúa como bandera secundaria en **5** Specs: 007, 012, 045, 046, 048.

**Por qué 0 en COMPLETE_100:** ninguna Spec ha sido validada sobre PostgreSQL. Toda la evidencia
existente corre sobre SQLite. «Operativo E2E» exige el motor de producción.

**Por qué 0 en BROKEN:** nada falla en ejecución. Las brechas son de ausencia, no de defecto.
El 502 de producción registrado el 2026-08-11 es incidencia de infraestructura, no estado de Spec.

**Por qué 0 en FUTURE_SCOPE:** la integración en línea con SENIAT/SICA/SIGESAI/SACS sí es alcance
futuro legítimo (P20 prohíbe fabricar documentos oficiales), pero es alcance futuro *dentro* de la
Spec 044, que está sustancialmente completa. Ninguna Spec **entera** es futura.

---

# 5. DISTRIBUCIÓN POR MADUREZ

| Nivel | Cantidad | Specs |
|---|---:|---|
| M0 Documentada | 5 | 012, 018, 020, 033, 047 |
| M1 Skeleton | 6 | 021, 022, 031, 032, 046, 053 |
| M2 Aislada | 8 | 008, 011, 026, 045, 048, 049, 052, 055 |
| M3 Integrada | 12 | 003, 006, 007, 015, 019, 029, 034, 035, 039, 040, 042, 051 |
| M4 E2E probada | 25 | ver matriz |
| **M5 Production-ready** | **0** | — |

---

# 6. SPECS COMPLETAS

**Ninguna alcanza COMPLETE_100.** Las 25 en `SUBSTANTIALLY_COMPLETE` son:

001, 002, 004, 005, 009, 010, 013, 014, 016, 017, 023, 024, 025, 027, 028, 030, 036, 037, 038,
041, 043, 044, 050, 054, 056.

Núcleos más sólidos: **023 Kardex** (88 %), **025 Transferencias/conteos/ajustes** (86 %),
**028 CxP** (86 %), **037 CxC** (86 %), **027 Conciliación triple** (85 %), **005 Design System** (89 %).

---

# 7. SPECS PARCIALES

20 Specs: 003, 006, 007, 008, 011, 015, 019, 026, 029, 034, 035, 039, 040, 042, 045, 048, 049, 051, 052, 055.

Más críticas por impacto sistémico: **034 Facturación** (54 %), **029 Pedido** (57 %),
**011 Unidades en transacción** (45 %), **008 Almacenes físicos** (36 %), **045 Aprobaciones** (35 %).

---

# 8. SPECS NO INICIADAS

| # | Spec | Fuente que la exige |
|---|---|---|
| **012** | Maestros comerciales | Vol. 1 §7 · Vol. 2 §1 |
| **018** | Importaciones | DOCX Importación §1 (12 etapas) |
| **020** | Incidencias de recepción | DOCX Importación §2 |
| **033** | Confirmación independiente de pedido | DOCX Pedido §6-7 |
| **047** | Notificaciones y tareas | Vol. 2 §1 (rama Inicio) |

Más **046 Gestión documental** en `DATABASE_ONLY`: tabla existente, cero acceso.

---

# 9. SPECS ROTAS

**Ninguna.** Ver §4.

---

# 10. SPECS SIN TRAZABILIDAD

| Spec | Código existente sin Spec que lo gobierne |
|---|---|
| 007 | `cost_center_id` como `String(36)` sin tabla ni FK, en 2 tablas |
| 012 | `price_list`, `zone`, `payment_term`, `salesperson` como texto libre |
| 045 | `approval_requests` + 4 implementaciones ad-hoc de aprobación |
| 046 | `file_metadata` sin endpoint ni vínculo |
| 048 | Cliente HTTP en `licensing/service.py:375`; `outbox_events` sin publicador |

Además, **2 tablas muertas**: `outbox_events` y `feature_flags` — declaradas y con cero referencias
en todo el código.

---

# 11. FUTURE SCOPE

Ninguna Spec entera. Alcance futuro legítimo **dentro** de Specs activas:

- **044** — verificación en línea con organismos oficiales (requiere convenio; P20).
- **048** — integración bancaria directa (requiere convenio).
- **009 (Vol.1)** — contabilidad formal de partida doble, declarada fuera de roadmap en `CVG-009-04`.

---

# 12. TOP 10 BRECHAS

Ordenadas por impacto sistémico, no por volumen de código.

1. **Confirmación de pedido inexistente (033).** No es solo una etapa: es un control de segregación de funciones. Sin ella, quien prepara es quien libera.
2. **Factura de venta sin vínculo a pedido (034).** Se puede facturar dos veces el mismo pedido, o facturar uno nunca preparado. Deuda que se encarece cada día.
3. **Ruta de picking por ubicación ausente (031/032).** El proceso lo describe como la característica distintiva de la operación; `PickListLine` no tiene ni ubicación ni secuencia.
4. **Put-away inexistente (022).** La mercancía entra al almacén sin posición física; `location_id` nunca se escribe.
5. **Motor de aprobaciones no transversal (045).** Nodo de mayor grado del grafo: bloquea seis Specs y ya generó cuatro implementaciones divergentes.
6. **Maestros comerciales sin Spec ni modelo (012).** Precio, descuento, condición y comisión como texto libre. Viola el Principio 8.
7. **Importaciones inexistentes (018).** Doce etapas documentadas, cero implementadas, y el negocio es importador.
8. **Unidad y presentación se pierden en la transacción (011).** El maestro las tiene; ninguna línea de documento las lleva.
9. **PostgreSQL nunca ejercitado (001/052/053).** Toda la evidencia del proyecto descansa sobre SQLite.
10. **Auditoría incompleta en dos módulos (006/051).** Empresa, sucursal, almacén, cliente, proveedor y producto no dejan rastro.

---

# 13. TOP 10 RIESGOS DE RETRABAJO

Si se continúa en el orden actual, esto habría que rehacerlo:

1. **Facturar sin confirmación** → cuando entre 033, todo el flujo de facturación se reescribe.
2. **Documentos sin unidad ni presentación** → backfill imposible sobre histórico; la conversión queda ambigua para siempre.
3. **Inventario sin ubicación** → el Kardex histórico no podrá responder «dónde estaba»; la reconstrucción por ubicación será inviable.
4. **Precios tecleados a mano** → al entrar 012, ninguna cotización histórica podrá recalcularse contra la regla vigente.
5. **Cuatro motores de aprobación divergentes** → al centralizar 045, hay que migrar cuatro modelos de datos distintos.
6. **Costo sin landed cost** → las capas de costo de mercancía importada quedan mal valoradas; afecta margen y libros.
7. **Picking sin ruta** → construir la UI de despacho ahora significa rehacerla entera al entrar 031.
8. **`cost_center_id` como texto** → normalizar después exige migración de datos sucios.
9. **Recepción sin cuarentena** → mercancía con incidencia ya contada como disponible; corregirlo retroactivamente distorsiona el Kardex.
10. **Reserva en momento indefinido** → si se decide reservar al emitir el pedido, cambia la semántica de todas las reservas existentes.

Los riesgos 2, 3 y 4 comparten una propiedad: **su coste crece con cada día de operación**.
Son los únicos que justifican interrumpir cualquier otro plan.

---

# 14. PROCESOS COMPLETOS

8 de 21: transferencia, CxC, CxP, pago, cobro, nota de crédito, nota de débito, regulatorio.

---

# 15. PROCESOS INCOMPLETOS

13 de 21. Detalle en [`processes-to-specs-map.md`](processes-to-specs-map.md).

| Proceso | Etapas cubiertas | Rompe en |
|---|---|---|
| Importación | 0/12 | Primera etapa |
| Put-away | 0/10 | Primera etapa |
| Confirmación de pedido | 0/8 | Primera etapa |
| Cola y ruta de picking | 0/10 | Primera etapa |
| Incidencias de recepción | 0/9 | Primera etapa |
| Confirmación de inventario recibido | 2/11 | Conteo por SKU |
| Preparación física | 2/12 | Llegada a la ubicación |
| Recepción física | 3/10 | Arribo |
| Toma del pedido | 4/7 | Condiciones desde maestro |
| Liberación y facturación | 4/9 | Autorización |
| Despacho | 4/6 | Verificación triple |
| Devolución | 4/6 | Inspección |
| Retenciones | 4/7 | Conceptos cargados |

---

# 16. FRONTEND

Sólido en forma, incompleto en alcance. 78 rutas sin huérfanas, design system uniforme, axe 19/19,
responsive 198/198, bundle 375 KB con 87 chunks por ruta. **18 pantallas exigidas por el
requerimiento no existen**, y tres ramas del menú canónico no tienen ninguna pantalla: Comercial,
Aprobaciones y Configuración del sistema.

Los 210 casos de vitest viven en 7 archivos, todos de componente o de puerta. **No hay una sola
prueba de las 77 páginas.**

---

# 17. BACKEND

275 endpoints en 15 módulos, máquinas de estado explícitas, idempotencia y concurrencia probadas.
Asimetría notable: la cadena de compras está trazada con FKs (`order_line_id`, `receipt_line_id`,
`triple_matches`) y la de ventas no. Dos tablas declaradas sin ningún consumidor.

---

# 18. BASE DE DATOS

144 tablas, 14 migraciones en cadena lineal con head único, cero columnas de dinero en `Float`
(ADR-012 documenta las 36 de cantidad). **Nunca ejecutada contra PostgreSQL.** Faltan FKs en cuatro
relaciones críticas: factura↔pedido, línea↔unidad, línea de picking↔ubicación, requisición↔centro de costo.

---

# 19. INTEGRACIONES

Una sola con contrato —licencia central, cliente `urllib.request`, sin red real probada—.
Correo, BCV, storage, webhooks y cola asíncrona: inexistentes. SENIAT/SICA/SIGESAI/SACS y bancos:
alcance futuro legítimo por P20.

**Ninguna integración externa ha sido probada contra un servicio real.**

---

# 20. QA

La infraestructura de QA es de las mejores partes del proyecto: puertas G1-G4 permanentes, crawler
de rutas, axe, responsive, cross-browser, idempotencia, E2E in-process 20/20. Lo que le falta es
profundidad: cero pruebas de página, rendimiento medido sobre base vacía, sin dispositivos reales,
sin carga.

---

# 21. SEGURIDAD

Aislamiento multi-tenant probado (401/403/IDOR/escritura cruzada), RBAC con `require_permission`,
lockout con 423, CSP/HSTS en nginx, 0 CVE. Falta SBOM, rate limiting global, política de uploads
(no hay uploads) y MFA (solo el campo `mfa_enabled`).

---

# 22. FISCAL

Mecanismo implementado y **no validado**: reglas versionadas con fuente legal, numeración y números
de control atómicos, hash SHA-256, notas con límite al saldo, libros reconstruibles, períodos y
declaraciones. Pero las alícuotas, conceptos ISLR y matrices oficiales **no están cargadas**, y no
ha habido revisión por abogado tributario ni contador público sobre el ejercicio vigente.

Conforme al Principio 19, el estado correcto es `LEGAL_VALIDATION_REQUIRED`. **No puede declararse
cumplimiento fiscal.** Falta contingencia de facturación (sin UI ni flujo).

---

# 23. INFRAESTRUCTURA

Compose completo con healthchecks, Dockerfiles, nginx endurecido, CLI de instalación y 8 scripts.
Nada de ello validado de extremo a extremo: backup/restore nunca ejecutado, rollback nunca probado,
`latest` como tag por defecto. Último estado registrado de producción: API en 502 por causa de
infraestructura (2026-08-11, no re-verificado aquí).

---

# 24. ROADMAP

Diez olas ordenadas por dependencia real. Detalle en [`roadmap-by-waves.md`](roadmap-by-waves.md).

| Ola | Contenido | Specs |
|---|---|---|
| **0** | Correcciones estructurales bloqueantes | 006, 001, 052, 053, 034(FK), 054 |
| **1** | Fundación de dominio | **045**, **008**, **046** |
| **2** | Maestros indispensables | **012**, **011**, 007 |
| **3** | Abastecimiento e importación | **018**, 015, 026 |
| **4** | Recepción, confirmación y almacenamiento | 019, **020**, **021**, **022** |
| **5** | Preparación del pedido | 029, 030, **031**, **032**, **033** |
| **6** | Facturación y despacho | 034, 035 |
| **7** | Fiscal y regulatorio *(paralelizable desde hoy)* | 039-044, 014, 056 |
| **8** | Transversales e información | **047**, 048, 049, 050, 051 |
| **9** | Operación, calidad y seguridad | 052, 053, 054, 055 |

La Ola 7 no depende de código y puede arrancar en paralelo con la Ola 0 en cuanto haya equipo fiscal.

---

# 25. PRÓXIMAS SPECS

| Orden | Spec | Motivo | Desbloquea |
|---|---|---|---|
| **1ª** | **045 Motor de aprobaciones y segregación** | Nodo de mayor grado de salida del grafo. Ya existen 4 implementaciones divergentes que crecerán | 015, 017, 025, 030, 033, 047 |
| **2ª** | **008 Estructura física de almacenes** (completar) | Sin nivel y posición no hay put-away ni ruta de picking. Es el prerequisito silencioso de toda la Ola 4 y 5 | 022, 031, 032, 023 |
| **3ª** | **012 Maestros comerciales** | Requisito huérfano que viola P8; bloquea el pedido comercial y la facturación correcta | 029, 030, 034 |
| **4ª** | **046 Gestión documental y archivos** | Sin adjuntos no hay expediente de importación, evidencia de incidencia ni prueba de entrega | 018, 020, 035, 050 |
| **5ª** | **011 Unidades y presentaciones en transacción** | Deuda que se encarece cada día de operación; backfill imposible más adelante | 019, 021, 029, 032 |

Después de estas cinco, la Ola 4 (recepción→confirmación→put-away) queda desbloqueada como bloque
coherente sobre un modelo de datos común.

---

# 26. DASHBOARD EJECUTIVO

| Área | Completa | Parcial | Faltante | Rota | Riesgo |
|---|---:|---:|---:|---:|---|
| Foundation | 2 | 3 | 0 | 0 | Medio — sin PG real |
| Security | 1 | 3 | 0 | 0 | Medio — sin MFA ni SBOM |
| Masters | 4 | 3 | 1 | 0 | **Alto** — comercial ausente |
| Purchasing | 3 | 1 | 0 | 0 | Bajo |
| Imports | 0 | 0 | 1 | 0 | **Crítico** — 0/12 etapas |
| Receiving | 0 | 1 | 3 | 0 | **Crítico** — 3/40 etapas |
| Inventory | 3 | 1 | 0 | 0 | **Alto** — sin dimensión de ubicación |
| Sales | 2 | 2 | 0 | 0 | Alto |
| Picking | 0 | 0 | 3 | 0 | **Crítico** — 2/30 etapas |
| Billing | 0 | 1 | 0 | 0 | **Crítico** — sin vínculo ni compuerta |
| AR | 1 | 0 | 0 | 0 | Bajo |
| AP | 1 | 0 | 0 | 0 | Bajo |
| Treasury | 1 | 0 | 0 | 0 | Bajo |
| Fiscal | 2 | 3 | 0 | 0 | **LEGAL_BLOCKER** |
| Regulatory | 1 | 0 | 0 | 0 | Medio — matrices sin cargar |
| Reporting | 1 | 2 | 1 | 0 | Medio |
| QA | 1 | 0 | 0 | 0 | Medio |
| Infrastructure | 0 | 2 | 1 | 0 | **Alto** — restore no probado |

---

# 27. BLOQUEANTES

| ID | Spec | Descripción | Tipo | Impacto | Acción | Responsable |
|---|---|---|---|---|---|---|
| BLK-01 | 001, 052, 053 | Sin instancia PostgreSQL: `alembic upgrade`/`check`, drift, timezone, backup/restore | TECHNICAL_BLOCKER | Ninguna Spec puede alcanzar M5 | Aprovisionar PG y ejecutar | DevSecOps |
| BLK-02 | 039-043, 014, 056 | Alícuotas, conceptos ISLR y matrices oficiales sin cargar ni validar | **LEGAL_BLOCKER** | Sin certificación fiscal ni homologación | Contratar revisión tributaria y contable | Legal / Fiscal |
| BLK-03 | 045 | Sin decisión sobre umbrales y niveles de autoridad por empresa | PROCESS_BLOCKER | No se puede especificar el motor | Definir política de aprobación | Producto / Compras |
| BLK-04 | 030 | Momento de reserva de inventario sin decidir (CL-013-06) | PROCESS_BLOCKER | Bloquea 029, 031 | Decidir y emitir ADR | Producto / Ventas |
| BLK-05 | 008, 022 | Zonificación real del almacén (A-E) sin definir | PROCESS_BLOCKER | Bloquea put-away y ruta de picking | Levantamiento físico del almacén | Almacén / Logística |
| BLK-06 | 012 | Política de precios, descuentos y comisiones sin definir | PROCESS_BLOCKER | Bloquea 029, 034 | Definir reglas comerciales | Producto / Ventas |
| BLK-07 | 004, 048 | Servidor central de licencias no existe | DEPENDENCY_BLOCKER | Sincronización nunca probada contra red real | Decidir proveedor y desplegar | Producto |

---

# 28. DECISIONES PENDIENTES

Registradas, **no inventadas**. Cuando el código difiere de lo documentado, se anota el conflicto.

| ID | Decisión | Estado actual del código | Documento | Conflicto |
|---|---|---|---|---|
| DEC-01 | **Momento de reserva de stock** | Reserva al aprobar crédito (`APPROVED→RESERVED`) | DOCX Pedido §1 pide determinar si se reserva **al emitir el pedido** | **Sí** — el vendedor emite y el stock sigue libre hasta la aprobación |
| DEC-02 | **Presentación y unidad por línea** | Solo `quantity` | Vol. 1 §7, DOCX Recepción §3 | **Sí** — la diferencia «por presentación» y «por unidad» no es detectable |
| DEC-03 | **Tratamiento de incidencias de recepción** | Solo `quantity_rejected` + `quality` binario | DOCX Importación §2 exige faltante/sobrante/daño/referencia con evidencia | **Sí** |
| DEC-04 | **Confirmación independiente obligatoria** | No existe | DOCX Pedido §6-7 la define como control con separación funcional | **Sí** |
| DEC-05 | **Factura directa sin pedido** | Permitida de facto (la factura no exige orden) | DOCX Pedido §8 exige pedido confirmado previo | **Sí** — decidir si la factura directa es un caso legítimo y regularlo |
| DEC-06 | **Transporte propio vs. tercero** | `transport` como texto | Vol. 2, DOCX Pedido §9 | Parcial |
| DEC-07 | **Modalidad fiscal y contingencia** | Emisión implementada, contingencia sin flujo | Vol. 0 §4, Vol. 1 §9 | Pendiente |
| DEC-08 | **Alcance SICA/SIGESAI** | Registro y validación, sin fabricación (correcto por P20) | Vol. 1, F4/F5 | Sin conflicto |
| DEC-09 | **Costos de importación** | Sin landed cost | DOCX Importación §1 | **Sí** |
| DEC-10 | **Workflows de aprobación** | 4 implementaciones ad-hoc | Vol. 1 §4 (módulo Aprobaciones) | **Sí** |

---

# 29. RECOMENDACIÓN DE REBASELINE

**Propuesta, no ejecutada.** No renumerar. Conservar `001`-`012` y abrir Specs nuevas desde `014`
para las maestras huérfanas, cada una declarando su número maestro de referencia.

Renumerar doce Specs que ya tienen evidencia, convergencia y trazabilidad emitida destruiría la
cadena del Principio 3 a cambio de estética. El mapa de equivalencias cumple la misma función
sin coste. Recomendación de división: `001-fundacion` (cubre 10 maestras) y `005-ventas` (cubre 8,
incluidos los tres huecos mayores) deberían dividirse antes de recibir trabajo nuevo.

---

# 30. CONCLUSIÓN

**De las 56 Specs maestras de KONTROL:**

- **0 están completas** (`COMPLETE_100`)
- **25 están sustancialmente completas**
- **20 están parciales**
- **5 están iniciadas solo como skeleton**
- **1 existe solo en base de datos**
- **0 están rotas**
- **5 no han comenzado**
- **0 corresponden a future scope**
- **0 están bloqueadas como Spec** *(7 bloqueantes operan sobre Specs activas)*

**Por tanto:**

- **Faltan construir completamente 5 Specs** (012, 018, 020, 033, 047).
- **Faltan completar o remediar 26 Specs adicionales** (20 parciales + 5 esqueleto + 1 database-only).
- **Trabajo total pendiente: 31 de 56 Specs.**

El proyecto no está a mitad de camino: está **completo en la mitad administrativa y sin empezar en
la mitad operativa**. La buena noticia es que la mitad construida es de calidad y que las 31
pendientes se agrupan en un bloque coherente con un modelo de datos común —ubicaciones, unidades,
estados de mercancía y aprobaciones— y no en 31 problemas independientes.

**Recomendación:** cerrar la Ola 0, decidir los siete bloqueantes de proceso, y abrir la Spec 045
(motor de aprobaciones) como primera iniciativa del roadmap.

**Este análisis se detiene aquí.** No se ha implementado nada, no se ha creado ninguna Spec del
roadmap y no se ha ejecutado `/speckit.implement`. **Se solicita autorización expresa para
comenzar la primera Spec.**
