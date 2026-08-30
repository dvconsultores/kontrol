# INFORME DE ANÁLISIS — ARCH-MC-001

`/speckit.analyze ARCH-MC-001` · 2026-08-31

Comparación de: Constitución v1.1 → ADR → D0 → G0 → Gate multiempresa → baseline
→ Specs cerradas → auditoría de alcance → spec → clarify → research → plan →
data model → contratos → matriz de endpoints → matriz de tablas → tasks →
aceptación → plan de pruebas → riesgos → trazabilidad → roadmap.

---

## 1. Cobertura

| Métrica | Valor |
|---|---:|
| Requisitos funcionales | 50 |
| Requisitos no funcionales | 8 |
| Criterios de aceptación | 66 |
| Tareas | 103 |
| **FR sin tarea ni criterio** | **0** |
| **NFR sin tarea ni criterio** | **0** |
| **Criterios sin tarea** | **0** |
| **Tareas sin requisito** | **0** |

Verificado por script.

## 2. Clasificación completa

| Métrica | Valor |
|---|---:|
| Tablas del modelo | **166** |
| Clasificadas | **166** |
| **Sin clasificar** | **0** |
| De empresa | 133 (97 directas · 36 derivadas) |
| Derivadas por FK **anulable** | **0** |
| Operaciones de API | 404, todas con alcance declarado |

## 3. Coherencia con la Constitución

| Principio | Verificación | Estado |
|---|---|---|
| **P4** · núcleo fiscal separado | Series, control y libros por empresa: `AC-MC-50`..`55` | ✅ |
| **P5** · histórico protegido | `FR-MC-054`, `FR-MC-056`, `AC-MC-76` | ✅ |
| **P6** · el backend manda | `FR-MC-011`, `FR-MC-020`, `FR-MC-034` | ✅ |
| **P8** · nada hardcodeado | `FR-MC-035`: la licencia no degrada el esquema | ✅ |
| **P13** · integridad transaccional | FK reales en PostgreSQL, no solo en el servicio | ✅ |
| **P17/P22** · autoridad única | Un `CompanyContext`, no uno por módulo | ✅ |
| **P21** · paridad del motor | `NFR-MC-01`, `AC-MC-90` | ✅ |
| **P23** · captura temprana | La ventana determinista se cierra sola | ✅ |

## 4. Fronteras verificadas

| Frontera | Garantía |
|---|---|
| No se crea RBAC paralelo | `UserScope` y `user_roles` se adaptan (`FR-MC-031`) |
| No se toca la rotación de sesión | La cabecera no interviene en la renovación (`FR-MC-016`) |
| No se degrada la Spec 045 | Mantiene su empresa real (`FR-MC-071`) |
| No se rompe la Spec 008 | Es la referencia positiva (`FR-MC-070`) |
| No se altera la conversión de la Spec 011 | `FR-MC-074` |
| No se implementa la Spec 012 | Fuera de alcance, declarado |
| No se simula intercompany | Se **bloquea** (`AC-MC-63`, `AC-MC-65`) |

## 5. Contradicciones

**Ninguna** entre spec, plan, modelo, contratos, matrices, tareas y criterios.

Una aparente, resuelta explícitamente: `user_roles`, `user_scopes` y
`audit_events` figuran como `TENANT_SCOPE` y a la vez su `company_id` pasa a FK
real. No es contradicción —la fila pertenece al tenant, el alcance que la columna
expresa es de empresa— y queda documentado en `CL-MC-12`.

## 6. Riesgo dominante

`R-MC-1`: **dar por determinista un backfill que no lo es**.

Es el riesgo real. Un tenant que hoy tiene una empresa pudo tener dos el año
pasado. Rellenar por el recuento actual produciría datos que **parecen**
correctos y atribuyen facturas a la empresa equivocada.

Se contiene con `FR-MC-052` y `AC-MC-71`: el determinismo se decide por el
intervalo, reconstruyendo cuándo cada tenant dejó de ser monoempresa.

## 7. Lo que este análisis no puede cerrar

| Id | Pregunta | ¿Bloquea? |
|---|---|---|
| **OQ-MC-01** | ¿`units_of_measure`, `movement_types` y catálogos similares son del tenant o de la empresa? | **No** para especificar; **sí** para migrar esas tablas |
| **OQ-MC-02** | ¿El selector recuerda la última empresa por usuario y dispositivo? | No |

`OQ-MC-01` afecta a un puñado de catálogos y su ola no se ejecuta sin respuesta.
No condiciona el diseño.

## 8. Condición material para implementar

El entorno efímero perdió **PostgreSQL 18.6** y **ClamAV**. `NFR-MC-01` y
`AC-MC-90` exigen aceptación sobre PostgreSQL 18.x real, y la revalidación de la
Spec 046 exige un analizador real. Ambos deben reaprovisionarse (`T-MC-142`)
antes de empezar.

## 9. Verificación del Gate del §229

| Condición | Estado |
|---|---|
| Modelo canónico cerrado | ✅ ADR-D0-014 propuesto |
| 166 tablas clasificadas | ✅ 0 sin clasificar |
| 133 de empresa resueltas conceptualmente | ✅ 97 directas + 36 derivadas |
| 14 del tenant resueltas | ✅ 7 renombran, 3 pasan a FK real, 4 sin cambio |
| 17 actuales verificadas | ✅ probadas: Warehouse separa, Party no |
| `CompanyContext` cerrado | ✅ cabecera, con alternativas comparadas |
| Licencia cerrada | ✅ el backend impone el límite |
| Acceso usuario–empresa cerrado | ✅ sobre la estructura existente |
| Estrategia de migración cerrada | ✅ expandir/contraer por olas |
| Estrategia para lo ambiguo cerrada | ✅ `MC-A`..`MC-E` con aborto |
| Estrategia fiscal cerrada | ✅ ola 3, con criterios propios |
| Frontend cerrado | ✅ selector, cabecera, invalidación |
| API cerrada | ✅ 404 operaciones clasificadas |
| Seguridad cerrada | ✅ `AMC-01`..`AMC-17` |
| Plan de `REM-046-001` cerrado | ✅ N9 |
| Bloqueo de la Spec 012 registrado | ✅ |
| Pruebas definidas | ✅ |
| 0 contradicciones · 0 huérfanos | ✅ |

## 10. Veredicto

**`ARCH-MC-001 APTA PARA IMPLEMENTACIÓN`**

0 BLOCKER · 0 CRITICAL · 0 contradicciones · 0 requisitos huérfanos · 0 criterios
sin tarea · 0 tareas sin requisito · 166/166 tablas clasificadas · 404/404
operaciones con alcance · decisión de producto incorporada · `ADR-D0-014`
propuesto · dos preguntas abiertas, ninguna bloqueante del diseño.

**No se implementa.** Requiere autorización expresa y reaprovisionar el entorno.
