# REGISTRO DE RIESGOS — SPEC 045

| ID | Riesgo | Prob. | Impacto | Severidad | Mitigación |
|---|---|---|---|---|---|
| **R-045-01** | **Desplegar el motor sin políticas configuradas deja los procesos sin ningún control** — se pasa de cuatro controles débiles a cero | Media | **Crítico** | **ALTA** | La migración crea y activa una política equivalente **antes** de cada corte (plan §4). Prueba de equivalencia obligatoria (AC-20). Nunca se redirige un dominio sin política activa |
| R-045-02 | La migración de compras rompe la cadena mejor construida del sistema | Media | Alto | ALTA | Regresión completa de `test_purchasing.py` sin cambio de expectativa; corte dominio por dominio, no simultáneo |
| R-045-03 | La obsolescencia por huella resulta tan sensible que los usuarios buscan evitar el control | Media | Medio | MEDIA | Huella acotada a los campos de la condición (CL-045-05), no al documento completo; `fingerprint_fields` visible en la interfaz |
| R-045-04 | Sin PostgreSQL, la concurrencia y las restricciones no pueden probarse | **Alta** | Alto | **ALTA** | Dependencia declarada de BLK-D0-01; los casos de concurrencia son criterio de salida (test-plan §9) |
| R-045-05 | La delegación se usa para eludir la segregación | Media | Alto | ALTA | R-D0-02-8 y FR-045-043: el delegado hereda las restricciones; prueba negativa AC-06 |
| R-045-06 | Aparece un quinto motor de aprobación en una Spec futura | Media | Alto | ALTA | P22 lo convierte en violación constitucional; verificación por búsqueda en el criterio de salida (AC-21) |
| R-045-07 | Se codifican umbrales «provisionales» para poder demostrar | Media | Alto | ALTA | AC-23 y NFR-045-07: búsqueda de literales de negocio como criterio de salida |
| R-045-08 | El vencimiento se implementa como aprobación automática por presión operativa | Baja | **Crítico** | MEDIA | CL-045-06 y AC-16: el silencio nunca es decisión |
| R-045-09 | La bandeja degrada con volumen (N+1) | Media | Medio | MEDIA | Prueba de rendimiento con 1.000 solicitudes; índices por actor elegible y estado |
| R-045-10 | El contrato de adjuntos se implementa antes que la Spec 046 y diverge | Baja | Medio | BAJA | Contrato declarado, no implementado (CL-045-10); la evidencia interina es texto |
| R-045-11 | El motor termina conociendo la lógica de cada dominio | Media | Alto | ALTA | Regla de acoplamiento del plan §1: `approvals` no importa ningún módulo de dominio; `context` plano |
| R-045-12 | El histórico migrado se completa con políticas inventadas para que «cuadre» | Baja | Alto | MEDIA | FR-045-074 y AC-22: `LEGACY_UNVERSIONED` explícito |
| R-045-13 | Los umbrales no llegan a tiempo y se bloquea la entrega | Media | Bajo | BAJA | Son configuración (OQ-02), no bloqueo: el motor se entrega con políticas vacías |
| R-045-14 | Comparar montos sin normalizar produce niveles distintos según el día | Baja | Alto | MEDIA | FR-045-011: tasa snapshot del documento, no del día de la decisión (AC-03) |

## Riesgos que esta Spec cierra

| Riesgo previo | Cómo se cierra |
|---|---|
| Divergencia de cuatro motores de aprobación | Motor único obligatorio (P22) |
| Aprobaciones sin política identificable en fiscalización | `policy_snapshot` en cada solicitud |
| Aprobar algo distinto de lo revisado | Obsolescencia por huella |
| Autoaprobación silenciosa | Segregación configurable con prueba negativa |
| Operación detenida por ausencia del aprobador | Delegación acotada y auditada |

## Riesgo residual aceptado

**R-045-13** se acepta conscientemente: el motor puede entregarse y probarse sin que ninguna empresa
haya definido sus umbrales. Es la consecuencia deliberada de separar decisión de producto de
configuración de cliente (`POL-D0-001` §5, criterio de D0 §32).
