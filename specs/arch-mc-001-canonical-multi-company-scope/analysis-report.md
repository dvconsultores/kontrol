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

---

# N7 — ANÁLISIS

## 1. Cobertura de requisitos

30 requisitos funcionales, 6 no funcionales, 10 criterios de aceptación. Cada uno
con al menos una tarea; cada tarea con al menos un requisito.

**Requisitos huérfanos: 0. Tareas huérfanas: 0.**

## 2. Contradicciones

Se buscaron específicamente:

| Qué se buscó | Resultado |
|---|---|
| Alcance directo y derivado a la vez en una tabla | 0 |
| Autoridad duplicada | 0 |
| Unicidad que contradiga el alcance declarado | 0 |
| Ruta derivada anulable | 0 |
| Claves foráneas circulares entre migraciones | 0 |
| Trabajo de N8 colado en N7 | 0 |
| Trabajo de N9 o de la Spec 012 colado | 0 |
| Conflicto con Specs cerradas | 0 |
| Conflicto con ADR-D0-014 | 0 |

## 3. Tres discrepancias documentales encontradas

Ninguna es un bloqueo; las tres son casos de documento que no coincide con la
realidad medida, y las tres se corrigen en esta fase.

**Las rutas derivadas son 35, no 36.** La matriz canónica arrastraba el número
de una medición anterior. Comprobado contra los modelos vigentes.

**Las restricciones de unicidad son 31, no 13.** El «13» era una estimación
previa a N3, que creó las tablas de empresa ya con su unicidad correcta. Once de
las 31 son de empresa y **ninguna necesita cambiarse**.

**Trece tablas no declaran alcance.** N0 reportó cero sin declarar sobre 153
modelos; las de organización quedaron fuera de ese recuento. Son de empresa por
construcción y sus claves foráneas ya son correctas, así que es una laguna de
declaración, no de estructura.

## 4. Lo que ya estaba bien

Conviene decirlo, porque cambia el tamaño de la fase: **las 35 rutas derivadas
están completas** —clave foránea real y NOT NULL en todas— y **las once
unicidades de empresa ya son correctas**. N3 hizo bien ese trabajo.

Lo que falta es concreto y masivo: **80 tablas con `company_id` que la base no
contrasta con nada**, y 3 con `tenant_id` en la misma situación.

## 5. Ordenación de migraciones

Claves foráneas antes que obligatoriedad; coherencia compuesta después de las
simples. Sin ciclos: cada migración solo depende de que la anterior haya
terminado.

## 6. Decisiones materiales nuevas

**Ninguna.** Las dos preguntas abiertas se resolvieron con evidencia dentro de la
arquitectura aprobada:

- `OQ-N7-01` midiendo cada punto de creación: todos fijan la empresa.
- `OQ-N7-02` es declarativa, no de negocio.

Las reglas de borrado se derivan de P5, que ya estaba decidido. El alcance de
las unidades de medida viene de Spec 011 y `OQ-MC-01`, ya cerradas.

## 7. Resultado

```
BLOCKER                  : 0
CRITICAL                 : 0
CONTRADICTIONS           : 0
ORPHAN REQUIREMENTS      : 0
ORPHAN TASKS             : 0
UNRESOLVED MATERIAL OQ   : 0
```

**`/speckit.analyze: PASS`** — implementación autorizada por el prompt maestro.

---

# N8 — ANÁLISIS

## 1. Cobertura

26 requisitos funcionales, 4 no funcionales, 10 criterios de aceptación, 17
tareas. **Requisitos huérfanos: 0. Tareas huérfanas: 0.**

## 2. Contradicciones buscadas

| Qué | Resultado |
|---|---|
| Columna transitoria sin tarea de retirada | 0 |
| Repliegue sin prueba | 0 |
| Contrato sin prueba | 0 |
| Desajuste OpenAPI / runtime | **1 encontrado**: la cabecera no se declara |
| Dependencia oculta de N4 | **1 encontrada**: `planes()` lee el ORM |
| Dependencia del fixture hostil | **1 encontrada**: la base no era reproducible |
| Nulo con semántica contradictoria | 0 |
| Solape con N9 o con la Spec 012 | 0 |
| Skip ocultando requisito | **2 encontrados** |
| Documentación obsoleta | **1**: tres alcances cambiados en N7 |

Los seis hallazgos son trabajo de N8, no bloqueos: ninguno exige una decisión de
negocio nueva.

## 3. Lo que el análisis descartó

**No hay lectura ni escritura doble.** Se buscaron los patrones —`coalesce`,
`new or legacy`, escritura simultánea— y no existen. Las columnas transitorias
nunca se conectaron al modelo, así que no hubo transición que mantener.

**No hay cargas útiles heredadas.** N5 cerró el último caso.

**El módulo de migración ya está aislado**: cero importaciones desde el runtime.

## 4. El orden importa

El análisis obliga a un orden: desacoplar el clasificador **antes** de retirar
las columnas. No porque el clasificador dependa de ellas —no depende— sino
porque ya está roto por otra causa, y borrar primero convertiría un fallo
detectable en uno silencioso.

## 5. Decisiones materiales nuevas

**Ninguna.** El desacoplamiento aplica al conjunto de trabajo la misma pregunta
que `preflight` ya le hace al destino. El contrato de la cabecera documenta un
runtime que N1 decidió y N6 probó.

## 6. Resultado

```
BLOCKER                  : 0
CRITICAL                 : 0
CONTRADICTIONS           : 0
ORPHAN REQUIREMENTS      : 0
ORPHAN TASKS             : 0
UNRESOLVED MATERIAL OQ   : 0
```

**`/speckit.analyze: PASS`** — implementación autorizada.
