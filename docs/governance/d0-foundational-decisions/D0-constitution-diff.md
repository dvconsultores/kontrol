# ENMIENDAS PROPUESTAS A LA CONSTITUCIÓN

> **No aplicadas.** La Constitución establece que ninguna enmienda procede sin aprobación de
> Producto, Arquitectura, Seguridad, Legal y QA. Este documento es la propuesta, no el cambio.

## Revisión de los principios vigentes frente a D0

| Principio | ¿D0 lo contradice? | ¿D0 lo refuerza? | Observación |
|---|:--:|:--:|---|
| P3 Trazabilidad completa | No | Sí | D0-09 y D0-11 son casos de trazabilidad rota que las enmiendas cubren |
| P4 Núcleo fiscal separado | No | Sí | D0-07 formaliza la frontera |
| P5 Datos históricos protegidos | No | **Sí, críticamente** | D0-09/11 muestran que proteger no basta: hay que **capturar** |
| P6 Seguridad en backend | No | Sí | D0-03 y D0-05 lo aplican a disponibilidad y a límites de descuento |
| P8 No hardcodear reglas | No | Sí | D0-05 y D0-07 son su aplicación directa |
| P9 Instalación independiente | No | Sí | D0-06 lo respeta íntegramente |
| P12 Decisiones documentadas | **Se incumple en la práctica** | — | 15 ADR en `PROPUESTO` — ver OQ-14 |
| P13 Integridad transaccional | No | Sí | D0-03 lo lleva al nivel de base de datos |
| P15 Datos del cliente protegidos | No | Sí | D0-06 fija el límite duro de metadatos |
| P17 No retrabajo por inconsistencia | No | Sí | D0-02 y D0-08 lo extienden de UI a dominio |
| P19 Reglas normativas versionadas | No | Sí | D0-07 añade el estado de validación profesional |
| P20 No sustitución de organismos | No | Sí | Sin cambios |

Ningún principio vigente resulta contradicho por las decisiones D0.

## Enmienda E-01 — Paridad de motor de persistencia

**Nuevo principio propuesto (P21):**

> La evidencia de calidad solo es válida sobre el motor de persistencia de producción. Ninguna
> función se declara terminada con evidencia obtenida sobre un motor distinto del que operará el
> cliente.

**Fundamento:** P10 exige calidad demostrable pero no dice *dónde* se demuestra. El GAP Analysis
mostró un CRITICAL que SQLite ocultó. Deriva de `ADR-D0-001`.

## Enmienda E-02 — Autoridad única por capacidad transversal

**Nuevo principio propuesto (P22):**

> Las capacidades transversales —aprobaciones, gestión documental, auditoría, notificaciones,
> reglas normativas— tienen una sola implementación en la plataforma. Ningún módulo implementa su
> propia versión de una capacidad transversal.

**Fundamento:** P17 prohíbe la divergencia en componentes de interfaz; no la prohíbe en el dominio.
El resultado fueron cuatro motores de aprobación distintos. Deriva de `ADR-D0-002` y `ADR-D0-008`.

## Enmienda E-03 — Captura anticipada de datos no reconstruibles

**Adición propuesta a P5:**

> Cuando un dato no pueda derivarse a posteriori de ninguna otra fuente, su captura se implementa en
> cuanto la decisión que lo exige queda aprobada, aunque la funcionalidad que lo explota se
> planifique para una fase posterior.

**Fundamento:** P5 protege lo registrado, pero no obliga a registrar. `D0-historical-data-risk.md`
documenta ocho casos en que la información se pierde por no capturarse, no por modificarse.
Deriva de `ADR-D0-009` y `ADR-D0-011`.

## Procedimiento

1. Revisión conjunta de Producto, Arquitectura, Seguridad, Legal y QA.
2. Si se aprueban, se incorporan a `.specify/memory/constitution.md` con versión 1.1 y registro de cambio.
3. Los ADR-D0 quedan como fundamento documental de cada enmienda.

**Ninguna enmienda se aplica en esta fase.**
