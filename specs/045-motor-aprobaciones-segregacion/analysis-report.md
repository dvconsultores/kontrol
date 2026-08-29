# `/speckit.analyze` — INFORME DE ANÁLISIS — SPEC 045

| Campo | Valor |
|---|---|
| Spec | `045-motor-aprobaciones-segregacion` |
| Fecha | 2026-08-29 |
| Resultado | **APTA PARA IMPLEMENTACIÓN** — sujeta a autorización expresa |

## 1. Consistencia interna

| Verificación | Resultado |
|---|---|
| Todo requisito tiene tarea | ✔ 40/40 |
| Toda tarea tiene requisito | ✔ 65/65 |
| Todo requisito P0 tiene criterio de aceptación | ✔ |
| Toda historia tiene criterio | ✔ 10/10 |
| Máquinas de estado sin transición huérfana | ✔ |
| Estados terminales sin salida | ✔ INV-01 |
| Contratos cubren los requisitos de API | ✔ |
| Modelo de datos soporta todos los requisitos | ✔ |
| Wireframes cubren las rutas declaradas | ✔ 5 rutas + 1 panel |
| Requisitos sin criterio | 1 — FR-045-067, contrato diferido y declarado |

## 2. Consistencia con la autoridad superior

| Autoridad | Verificación | Resultado |
|---|---|---|
| Constitución v1.1 | 23 principios revisados | Sin contradicción |
| **P22** autoridad única | Motor único; los cuatro actuales migran | **Cumple y lo materializa** |
| **P21** paridad de motor | Toda la evidencia sobre PostgreSQL | Cumple |
| **P23** captura anticipada | `policy_snapshot` y `fingerprint_fields` desde la primera solicitud | Cumple |
| P8 no hardcodear | Sin umbrales, niveles, roles ni monedas en código | Cumple · AC-23 lo verifica |
| P6 backend autoridad | `allowed_actions` en servidor; 403 real | Cumple |
| P18 / ADR-015 | Configuración en pantalla completa; modal solo para confirmar | Cumple |
| `ADR-D0-002` | Las 10 reglas trazadas a requisitos | Cumple íntegramente |
| Baseline arquitectónica §10 | Modelo idéntico al consolidado | Cumple |
| `ADR-013` | Idempotencia, ETag y locks | Cumple |
| `ADR-012` | Auditoría por `record_audit`, sin rastro paralelo | Cumple |
| `ADR-001` | Módulo con límites explícitos; no importa dominios | Cumple |

**Contradicciones con autoridad superior: 0.**

## 3. Conflictos detectados durante la especificación y su resolución

| # | Conflicto | Resolución |
|---|---|---|
| CF-01 | El motor necesita evidencia adjunta, pero la Spec 046 es posterior | Contrato `AttachmentLink` declarado sin implementar; evidencia interina en texto. **046 no exigirá cambios en el modelo de 045** |
| CF-02 | El motor debe avisar al aprobador, pero la Spec 047 es posterior | 045 emite eventos y expone bandeja; no notifica. Inversión de dependencia: 045 no conoce a 047 |
| CF-03 | La numeración de carpeta (045) no sigue la secuencia del repositorio (013) | Se adopta la numeración del catálogo maestro y se **actualiza** la recomendación previa de `spec-equivalence-map.md`, que proponía continuar desde 014 |
| CF-04 | El vencimiento podría leerse como aprobación tácita | CL-045-06: el silencio nunca decide. Marca y notifica (AC-16) |
| CF-05 | Comparar umbrales en multimoneda | Siempre en moneda base con tasa **snapshot del documento**, no del día de la decisión (AC-03) |
| CF-06 | Una huella sobre el documento completo haría el control inutilizable | Acotada a los campos de condición, con la lista almacenada para que sea auditable (AC-08) |

## 4. Riesgo dominante

**R-045-01 — desplegar el motor sin políticas configuradas dejaría los procesos sin ningún control.**

No es técnico sino de secuencia: sustituir cuatro controles débiles por un motor sin datos daría un
resultado peor que el punto de partida. Mitigación incorporada al plan como orden obligatorio
—política equivalente creada y verificada **antes** de cada corte— y como criterio de aceptación
(AC-20).

## 5. Dependencias externas

| Dependencia | Estado | ¿Bloquea especificar? | ¿Bloquea implementar? | ¿Bloquea cerrar? |
|---|---|:--:|:--:|:--:|
| BLK-D0-01 · PostgreSQL | Abierto | No | **Parcialmente** — la concurrencia no puede probarse | **Sí** |
| OQ-02 · umbrales y niveles | Abierto | No | No | No — es configuración |
| Spec 046 · adjuntos | No construida | No | No | No — contrato declarado |
| Spec 047 · notificaciones | No construida | No | No | No — eventos emitidos |
| Spec 003 · alcances de usuario | Parcial (72 %) | No | No | Conviene alinear |

**Ninguna dependencia impide comenzar la implementación.**

## 6. Impacto en el roadmap

Al completarse desbloquea **015, 017, 025, 030, 033 y 047**: el mayor desbloqueo individual del
catálogo de 56.

## 7. Criterio de preparación para implementación

| Criterio | Estado |
|---|---|
| Alcance definido con fuera de alcance explícito | ✔ |
| Historias con criterio de aceptación | ✔ 10 |
| Requisitos trazados a autoridad | ✔ 47 |
| Modelo de datos con restricciones | ✔ 7 tablas |
| Máquinas de estado con invariantes | ✔ 8 |
| Contratos con códigos de error | ✔ 10 |
| Wireframes conformes al estándar | ✔ 6 |
| Plan de pruebas con criterio de salida | ✔ |
| Riesgos con mitigación | ✔ 14 |
| Migración con orden obligatorio | ✔ |
| Sin valores de negocio en la especificación | ✔ |
| **Autorización de implementación** | **✖ pendiente** |

## 8. Veredicto

**SPEC 045 APTA PARA IMPLEMENTACIÓN.**

Sin contradicciones con la Constitución v1.1, los 29 ADR aprobados ni la baseline arquitectónica.
Los seis conflictos detectados quedaron resueltos y documentados. Trazabilidad completa: 0 requisitos
sin tarea, 0 tareas sin requisito.

**Se requiere autorización expresa que mencione `045` para ejecutar `/speckit.implement` (P2).**

Secuencia recomendada al autorizar: **F1 → F2 → F3 → F4 → F7 (parcial) → F5 → F6**, dejando la
migración para el final y sólo con la regresión de los cuatro dominios en verde. Invertir ese orden
es lo que materializa R-045-01.
