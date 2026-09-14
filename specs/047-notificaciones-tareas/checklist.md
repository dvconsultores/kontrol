# `/speckit.checklist` — SPEC 047

| # | Comprobación | Estado | Evidencia |
|---|---|---|---|
| 1 | Spec 047 localizada | [x] | No tenía carpeta; CL-047-01 |
| 2 | Modelos inventariados | [x] | `clarifications.md` §1 |
| 3 | Arquitectura de eventos y outbox identificada | [x] | `approval_events`, `audit_events`, `outbox_events` sin uso |
| 4 | Planificador identificado | [x] | No existe; dueña 047 por `ADR-D0-003`; mecanismo → OQ-047-01 |
| 5 | Dueña de la entrega externa identificada | [x] | 048 |
| 6 | Permisos identificados | [x] | CL-047-05 |
| 7 | Semántica de notificación | [x] | `spec.md` §4 |
| 8 | Semántica de tarea | [x] | `spec.md` §4 |
| 9 | Semántica de alerta | [x] | `spec.md` §4 |
| 10 | Frontera con la aprobación | [x] | CL-047-02 · R-047-01 |
| 11 | Resolución de destinatarios | [x] | CL-047-03 |
| 12 | Lectura por destinatario | [x] | R-047-02 |
| 13 | Idempotencia definida | [ ] | Clave según OQ-047-01 |
| 14 | Semántica de asignación | [x] | `plan.md` §1 |
| 15 | Semántica de completado | [x] | R-047-01 |
| 16 | Semántica de vencimiento | [x] | CL-047-04 |
| 17 | Zona horaria | [x] | CL-047-04 |
| 18 | Frontera de preferencias | [x] | FR-047-018 |
| 19 | Semántica de fallo de entrega | [x] | R-047-05 |
| 20 | Multiempresa | [x] | `plan.md` §1 |
| 21 | Cruce de tenant | [x] | `plan.md` §1 |
| 22 | IDOR | [x] | R-047-06/07 |
| 23 | Auditoría | [ ] | Momento de «creado» y «escalado» según OQ-047-01 |
| 24 | API | [ ] | Tras W04-W09 |
| 25 | OpenAPI | [ ] | Tras W17 |
| 26 | Frontend | [ ] | Textos según OQ-047-02 |
| 27 | Paginación | [x] | CL-047-06 |
| 28 | Pruebas de concurrencia | [x] | T047-111 |
| 29 | Mutaciones | [x] | T047-112 |
| 30 | Instalación limpia | [x] | T047-091 |
| 31 | Material OQ = 0 | [ ] | **2** |
| 32 | UNKNOWN = 0 | [x] | 0 |
| 33 | Trazabilidad = 100 % | [x] | Documental: 36/36 requisitos con tarea y prueba prevista; implementación 0/36 |

**27 de 33.** Las seis abiertas dependen de OQ-047-01 u OQ-047-02.
