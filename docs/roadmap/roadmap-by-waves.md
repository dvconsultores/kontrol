# ROADMAP POR OLAS — ORDENADO POR DEPENDENCIA REAL

> No sigue el orden numérico. Cada ola solo contiene trabajo cuyos prerequisitos están cerrados
> al terminar la ola anterior. Las olas 0-2 no producen funcionalidad nueva visible: cierran
> deuda estructural que, de no cerrarse, obliga a rehacer las olas 3-6.

---

## OLA 0 — Correcciones estructurales bloqueantes

**Objetivo:** que la evidencia existente sea válida y que las afirmaciones publicadas sean ciertas.
No añade alcance.

| Trabajo | Spec maestra | Severidad | Por qué aquí |
|---|---|---|---|
| Instrumentar auditoría en `organization` y `master_data` | 006, 051 | HIGH | Cierra de verdad KAUD-001, hoy declarado resuelto sin serlo |
| Ejecutar `alembic upgrade head` + `alembic check` en PostgreSQL real | 001, 052 | BLOCKER | Toda la evidencia actual es SQLite; sin esto ningún estado es fiable |
| Backup → destruir → restore verificado | 053 | BLOCKER | Los scripts solo tienen `bash -n` |
| Fijar tag de imagen (quitar `latest` por defecto en compose) | 001, 052 | MEDIUM | Principio 14 |
| Sincronizar documentos de estado desfasados (4 archivos) | 054 | MEDIUM | El expediente se contradice consigo mismo |

**Salida esperada:** una línea base verificada sobre el motor de producción y un expediente sin
afirmaciones falsas.

---

## OLA 1 — Fundación faltante de dominio

**Objetivo:** construir los tres cimientos que todo lo demás necesita y que hoy no existen.

| Spec | Estado actual | Por qué ahora |
|---|---|---|
| **045 Motor de aprobaciones y segregación** | PARTIAL 35 % | Nodo de mayor grado: bloquea 015, 017, 025, 030, 033, 047. Ya hay 4 implementaciones ad-hoc que habría que reescribir después |
| **008 Estructura física de almacenes** (completar) | PARTIAL 36 % | Bloquea 022, 031, 032 y la calidad de 023. Añadir nivel/posición y jerarquía de zonas A–E |
| **046 Gestión documental y archivos** | DATABASE_ONLY | Bloquea 018, 020, 035, 050. Sin adjuntos no hay expediente de importación ni evidencia de incidencia |

**Salida esperada:** aprobaciones centralizadas con bandeja y delegación; direcciones físicas
completas; adjuntos vinculables a cualquier entidad con hash y versión.

---

## OLA 2 — Maestros indispensables

| Spec | Estado actual | Por qué ahora |
|---|---|---|
| **012 Maestros comerciales** | NOT_STARTED | Bloquea 029, 030, 034. Requisito huérfano; hoy son campos de texto libre (viola P8) |
| **011 Unidades y presentaciones en transacción** | PARTIAL 45 % | Añadir `uom_id`/`presentation_id` a las líneas de documento. Cuanto más tarde, más documentos históricos sin la dimensión |
| **007 Centros de costo y unidades de negocio** | PARTIAL 66 % | `cost_center_id` ya existe como texto suelto en dos tablas; convertirlo antes de que crezca |

**Salida esperada:** precio, descuento, condición y comisión gobernados por regla versionada;
cada línea de documento con su unidad y presentación.

---

## OLA 3 — Abastecimiento e importación

| Spec | Estado actual |
|---|---|
| **018 Importaciones** | NOT_STARTED — INCOTERM, proforma, packing list, embarque, agente, expediente |
| **015 Planificación de abastecimiento** (completar) | PARTIAL 55 % — rotación, demanda, punto de reorden |
| **026 Costos: landed cost** (completar) | PARTIAL 62 % — distribución de gastos de importación |

**Depende de:** 046 (expediente documental), 045 (aprobación de compra).

---

## OLA 4 — Recepción, confirmación y almacenamiento

Ésta es la cadena que hoy salta de "orden de compra" a "stock disponible" sin etapas intermedias.

| Spec | Estado actual |
|---|---|
| **019 Recepción física** (completar) | PARTIAL 50 % — arribo, programación, bultos, pallets, evidencia |
| **020 Incidencias de recepción** | NOT_STARTED — faltante/sobrante/daño/referencia, escalamiento, reclamo |
| **021 Confirmación y conciliación** | SKELETON_ONLY — conteo, tres vías, cuarentena, liberación formal |
| **022 Put-away y ubicación por zonas** | SKELETON_ONLY — asignación, traslado, confirmación física, reubicación |

**Depende de:** 008 (Ola 1), 011 (Ola 2), 046 (Ola 1), 018 (Ola 3).
**Salida esperada:** la mercancía entra con estado, ubicación y liberación formal — no como cifra.

---

## OLA 5 — Preparación del pedido

| Spec | Estado actual |
|---|---|
| **029 Pedido comercial** (completar) | PARTIAL 57 % — pedido como entidad, precio desde maestro, disponibilidad al cotizar |
| **030 Reserva** (resolver decisión) | SUBSTANTIALLY_COMPLETE 76 % — decidir momento de reserva (CL-013-06) |
| **031 Cola y ruta de picking** | SKELETON_ONLY — cola, prioridad, secuencia por ubicación |
| **032 Picking y consolidación** | SKELETON_ONLY — almacenista, escaneo, diferencia, daño, consolidación |
| **033 Confirmación independiente de pedido** | NOT_STARTED — segundo control con separación funcional |

**Depende de:** 008 + 022 (ubicaciones reales), 012 (precios), 045 (aprobaciones).
**Salida esperada:** el proceso documentado ejecutable de punta a punta por un almacenista real.

---

## OLA 6 — Facturación y despacho

| Spec | Estado actual |
|---|---|
| **034 Liberación y facturación** (reparar) | PARTIAL 54 % — vínculo factura↔pedido y compuerta de liberación |
| **035 Despacho** (completar) | PARTIAL 66 % — dirección estructurada, evidencia de entrega |

**Depende de:** 033. **Nota:** el vínculo factura↔pedido puede adelantarse a la Ola 0 como
migración aditiva si se acepta backfill nulo para las facturas históricas.

---

## OLA 7 — Fiscal y regulatorio (validación normativa)

| Spec | Bloqueo |
|---|---|
| 039, 040, 041, 042, 043, 014 | **LEGAL_BLOCKER** — carga de alícuotas, conceptos ISLR y matrices oficiales; validación por abogado tributario y contador |
| 042 Contingencia | Construir UI y flujo de contingencia de facturación |
| 044 Matrices regulatorias | Carga de perfiles oficiales por organismo/rubro |

**No depende de código**: puede correr en paralelo desde la Ola 0 con el equipo fiscal.

---

## OLA 8 — Información gerencial y transversales

| Spec | Estado actual |
|---|---|
| **047 Notificaciones y tareas** | NOT_STARTED — alertas, mis tareas, mis aprobaciones, correo |
| **048 Integraciones** | PARTIAL 25 % — BCV, correo, storage, webhooks |
| **049 Dashboard y analítica** (completar) | PARTIAL 56 % — rotación, tendencias |
| **050 Reportes** (completar) | 74 % — Excel, parametrización |
| **051 Auditoría avanzada** (completar) | 66 % |

---

## OLA 9 — Operación, calidad y homologación

| Spec | Trabajo |
|---|---|
| 052, 053 | Actualización, rollback, RPO/RTO documentados y probados |
| 054 | Dispositivos reales, carga, regresión sobre PG |
| 055 | SBOM, rate limiting, política de uploads |
| 056 | Acto formal de homologación y liberación de versión fiscal |

---

## Regla de ejecución

Ninguna ola posterior debe iniciarse antes de cerrar las dependencias que la anterior resuelve.
La tentación evidente será saltar a la Ola 5 o 6 porque son las visibles para el usuario; hacerlo
sin las Olas 1, 2 y 4 obliga a reescribir picking, facturación y recepción por segunda vez.
