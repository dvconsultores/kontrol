# SPEC 054 · Delta dirigida — E2E-SEED-EMPRESA-UNICA

**Fecha** 2026-09-17 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`) ·
**Apoyo** SPEC033 (consumidora del fixture, `order-confirmation`) · **Base** `e205712` ·
**Rama** `develop`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` | `e205712` |
| `ACTUAL_HEAD` | `e205712` — **coincide** |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_E205712` | **0** |
| Árbol | `spec054-n6-seed-orchestration-delta.md` modificado (arrastre: cierre del hueco declarado en su §22, medido tras el commit) · dos artefactos de auditoría sin seguimiento, **preservados** |

## 2. Dueña canónica

**SPEC054.** La evidencia apunta a un fixture de pruebas que construye un usuario
distinto del que su escenario declara; la autoridad sobre las suites E2E y sus ayudantes
es la 054 (`docs/roadmap/spec-equivalence-map.md:61`).

**SPEC033 entra solo como consumidora**: `order-confirmation.spec.ts` es la única suite que
entra por la interfaz con uno de esos usuarios.

**SPEC003 NO es dueña.** Se verificó su contrato y el producto lo cumple (§5): sin alcance
declarado se admiten todas las empresas del tenant, y eso está escrito, documentado y es
deliberado (`app/core/company_context.py:54-84`). `OWNER_IDENTITY_CONFLICT = 0`.

## 3. Recuento físico de creaciones de usuario

No son seis: son **siete** puntos, y uno de ellos está en un ayudante compartido.

| # | Fichero | Usuario | ¿Entra por UI con él? | Empresas que el escenario declara | ¿Escribe alcance hoy? |
|---|---|---|---|---|---|
| 1 | `billing.spec.ts:59` | `bill-*` | no | una (`c.company`) | **no** |
| 2 | `dispatch.spec.ts:59` | `disp-*` | no | una | **no** |
| 3 | `receivables.spec.ts:59` | `cxc-*` | no | una | **no** |
| 4 | `returns.spec.ts:59` | `dev-*` | no | una | **no** |
| 5 | `order-confirmation.spec.ts:170` | `check-*` | **sí** (`:329`) | una | **no** |
| 6 | `helpers/ventas.ts:74` (consumen `rates`, `treasury`) | `tz-*` | no | una | **no** |
| 7 | `notifications.spec.ts:108` | `n047*` | no | **las dos, a propósito** | **no**, y así debe seguir |

Los seis primeros son **la misma función copiada literalmente**: `verificador(request, c, m)`,
idéntica salvo el prefijo del nombre de usuario. Esa duplicación es la razón de que el
mismo error exista en seis sitios a la vez.

El séptimo es distinto y **no se toca**: `notifications.spec.ts` crea su usuario con
`company_id: null` en el rol y sin alcance **porque necesita alcanzar D1 y D2**; su propio
comentario lo dice y `:244` lo exige. Es el caso «unrestricted» del contrato.

## 4. El modelo de alcance, físicamente

| Pregunta | Respuesta medida |
|---|---|
| Entidad | `UserScope` |
| Tabla | `user_scopes` |
| Campos | `user_id`, `company_id`, `branch_id` (`app/modules/identity_access/models.py:110`) |
| Autoridad | **`UserScope` es la autoridad de acceso; `UserRole` no.** Lo dice el propio producto: «Un rol con `company_id` nulo significa "este rol vale en cualquier empresa donde el usuario opere", que es el alcance del **permiso**. Confundirlo con la lista de acceso haría que cualquiera con un rol global viese todas las empresas del tenant» (`company_context.py:62-67`) |
| Semántica sin alcance | Se admiten **todas** las del tenant (`company_context.py:82-83`), y es deliberado: «es el caso del administrador que crea la instalación» |
| ¿Ruta de API que lo escriba? | **Ninguna.** `grep UserScope(` en todo el repo: dos escrituras, ambas en `qa/` |
| ¿UI? | **Ninguna.** Master56 fila 003 ya lo registra: «Sin UI de alcances» |
| Quién lo escribe hoy | `qa/spec047-e2e-seed.py:47` y `qa/n6_world.py:146` |

**Consecuencia que manda en el diseño:** un fixture que corre en el navegador **no puede
declarar alcance por API**, porque esa API no existe. Y crearla sería cambiar el producto.

## 5. Reproducción pre-fix, sobre base limpia

Base `keu` creada de cero, migrada, sembrada con `qa/e2e-seed.sh`. `D1`, `D2` y `E1`
activas; `admin→D1`, `ua→D1`, `ub→D2`, `uab→D1+D2`, `uc→E1`.

| Caso | Condición | Resultado |
|---|---|---|
| **R1** | `D2` activa, usuario sin alcance | **falla** — `order-confirmation:323`. Con dos trabajadores fallan 2; serializado falla **solo** `:323` |
| **R2** | `D2` inactiva, única variable cambiada | **7 / 7 pasan**. `D2` restaurada a activa y verificado |
| **R3** | `D2` activa, alcance explícito declarado | **el producto resuelve una sola empresa** |

### R3 en detalle — la medición que decide dónde está el defecto

```
A · como lo crea el fixture hoy (rol acotado a D1, sin UserScope): 2 empresas ['D1','D2']
B · con UserScope(D1) declarado:                                   1 empresa  ['D1']
C · sin cabecera de empresa el servidor resuelve solo:             SÍ (200)
```

`A` es el defecto: el fixture **sí** declara una empresa —`company_id: c.company` en el
rol— pero la declara en la entidad que no manda. `B` y `C` son la prueba de que el
producto hace lo especificado y de que, con el alcance en su sitio, la compuerta de
selección desaparece sin tocar nada más.

**PRODUCT FIX REQUIRED = NO.**

### Un defecto de producto ajeno, encontrado y no absorbido

Con dos trabajadores, `order-confirmation:204` falla con **500 `INTERNAL_ERROR`**:

```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint
  "uq_movement_types_company_code"
DETAIL: Key (company_id, code)=(…, ENTRADA_RECEPCION) already exists.
```

`create_movement_type` (`app/modules/inventory/api.py:192-200`) consulta y luego inserta
sin proteger la carrera. Lo llamativo es que el helper interno del mismo módulo
—`_ensure_movement_type`, `service.py:1648-1657`— **sí** lo hace bien, con
`begin_nested()` y `es_violacion_unica`, y su comentario explica exactamente este caso.
La ruta pública se quedó sin esa protección, contra el Principio 25.

Reproducción: aislada **pasa**; el fichero serializado **pasa**; con dos trabajadores
**falla**. Es una carrera, independiente del alcance. Se clasifica
`PRODUCT_DEFECT_DISCOVERED`, se registra como deuda nueva y **no se corrige aquí**:
`PRODUCT FILE CHANGES = 0` es invariante de esta delta.

## 6. `/speckit.specify` — requisitos

| ID | Requisito |
|---|---|
| FR-054-UNICA-001 | Un fixture E2E que represente un usuario limitado a una empresa declara ese alcance en la entidad que manda: `user_scopes` |
| FR-054-UNICA-002 | La visibilidad empresarial de un usuario de prueba no depende del número de empresas activas del tenant |
| FR-054-UNICA-003 | El ayudante expresa explícitamente si el usuario es de una empresa, de varias o sin restricción |
| FR-054-UNICA-004 | Los consumidores que necesitan varias empresas o ninguna restricción se preservan sin cambio de conducta |
| FR-054-UNICA-005 | `order-confirmation` es estable con `D1` y `D2` activas |
| FR-054-UNICA-006 | El ayudante falla temprano ante una petición incoherente, en vez de producir un usuario distinto del pedido |
| FR-054-UNICA-007 | No se modifica la semántica de acceso del producto |
| FR-054-UNICA-008 | No se modifica código de producto, ni configuración, ni esquema, ni migraciones |
| FR-054-UNICA-009 | Existe cobertura que detecta la reintroducción de un usuario sin alcance en un escenario de empresa única |
| FR-054-UNICA-010 | Declarar el alcance es idempotente y no acumula filas |
| FR-054-UNICA-011 | Hay **una sola** manera de asignar alcance en todo el repositorio |
| FR-054-UNICA-012 | La suite global se ejecuta después del arreglo y todo fallo restante queda clasificado |

## 7. `/speckit.clarify`

| # | Pregunta | Respuesta medida | ¿Material? |
|---|---|---|---|
| 1 | Dueña real | SPEC054; SPEC033 como consumidora | No |
| 2 | ¿Un ayudante o varios? | **Seis copias literales**, ninguna canónica | No |
| 3 | Nº real de puntos de creación | **7**, no 6 | No |
| 4 | Entidad del alcance | `UserScope` / `user_scopes` | No |
| 5 | Conducta sin alcance | Todas las del tenant, **especificada y correcta** | No |
| 6 | Conducta con alcance único | Una empresa, y el servidor resuelve sin cabecera (R3·B, R3·C) | No |
| 7 | Conducta multiempresa | Las declaradas (`uab→D1+D2`, verificado en base) | No |
| 8 | ¿Hay API o UI para el alcance? | **No**, ninguna de las dos | No |
| 9 | ¿Crear esa API? | **No**: sería cambio de producto → prohibido aquí | No |
| 10 | ¿Patrón canónico existente para que el E2E actúe sobre la base? | **Sí**: `helpers/planificador.ts` invoca el intérprete del backend con `KONTROL_E2E_DB_URL`. Se reutiliza, no se inventa | No |
| 11 | ¿Cambiar el defecto del ayudante? | No hay «defecto» global que cambiar: se crea el ayudante canónico y se exige alcance explícito donde el escenario declara una empresa | No |
| 12 | ¿Alcance obligatorio? | **Sí** en el ayudante nuevo (fail-fast); el caso sin restricción se expresa a propósito y por separado | No |
| 13 | ¿`notifications` se toca? | **No**: necesita alcanzar las dos y lo dice su propio comentario | No |
| 14 | Limpieza | Los usuarios de E2E no se borran hoy (la base de QA acumula); el alcance se declara de forma idempotente, que es el patrón real del repo | No |
| 15 | ¿El 500 de tipos de movimiento es de esta delta? | **No**: carrera de producto, aislada pasa. Registrada, no absorbida | No |
| 16 | ¿Esquema o migración? | **0** y **0** | No |
| 17 | ¿Defecto de producto para esta deuda? | **0** (R3) | No |

**MATERIAL OQ = 0 · UNKNOWN = 0 · PRODUCT FIX REQUIRED = NO · SCHEMA = 0 · MIGRATION = 0.**

## 8. Compuerta constitucional

| Principio | Cumplimiento |
|---|---|
| 1 — Spec antes que código | Este documento precede a toda edición del fixture |
| 2 — Autorización expresa | Concedida por el prompt con `MATERIAL OQ = 0` |
| 3 — Trazabilidad | §14 |
| 10 — Calidad demostrable | R1/R2/R3 medidos; mutaciones §13 |
| 22 — Autoridad única | Una sola manera de asignar alcance (FR-011) |
| 24 — Instalación limpia | R1/R2/R3 sobre base creada de cero |
| 25 — Las altas concurrentes las gobierna la base | El incumplimiento encontrado se **registra**, no se corrige aquí |
| 27 — Mutación observable | §13 descarta lo que no cambia lo observable |

**COMPUERTA: PASA.** `G-UNICA-01`…`G-UNICA-19` satisfechas.

## 9. `/speckit.plan`

`W01` checkpoint · `W02` dueña · `W03` inventario de ayudantes · `W04` recuento de
consumidores · `W05` modelo de alcance · `W06` R1/R2/R3 · `W07` patrón canónico ·
`W08` contrato del ayudante · `W09` autoridad única de asignación · `W10` idempotencia ·
`W11` adopción en los seis · `W12` U1..U4 · `W13` dirigida de `order-confirmation` ·
`W14` regresión de los consumidores · `W15` Chromium · `W16` Firefox · `W17` WebKit ·
`W18` mutaciones · `W19` suite global · `W20` clasificación · `W21` analyze y
trazabilidad · `W22` convergencia.

### Diseño

```
qa/alcance_de_usuario.py     autoridad única: declara el alcance de un usuario.
                             Idempotente. Módulo y orden de línea de comandos.
qa/n6_world.py               deja de escribir UserScope por su cuenta: lo pide ahí.
e2e/helpers/usuario.ts       ayudante canónico del verificador de escenario.
                             Exige empresas explícitas; sin ellas, falla al instante.
e2e/alcance-de-usuario.spec  U1 una empresa · U2 la otra · U3 las dos ·
                             U4 sin restricción · idempotencia · fail-fast.
```

## 10. `/speckit.checklist`

| Compuerta | Comprobación |
|---|---|
| G-UNICA-01 | `HEAD = e205712`, árbol clasificado |
| G-UNICA-02 | Causa raíz reproducida (R1) y causalidad en dos sentidos (R2) |
| G-UNICA-03 | Entidad de alcance identificada físicamente |
| G-UNICA-04 | Conducta del producto confirmada correcta (R3) |
| G-UNICA-05 | Siete puntos de creación inventariados |
| G-UNICA-06 | Semántica de empresa única medida |
| G-UNICA-07 | Semántica multiempresa medida |
| G-UNICA-08 | Estrategia canónica definida y reutilizando patrón existente |
| G-UNICA-09 | Sin atajo por `D2` inactiva ni por borrarla |
| G-UNICA-10 | Ficheros de producto = 0 |
| G-UNICA-11 | Esquema sin cambios |
| G-UNICA-12 | Migraciones = 0 |
| G-UNICA-13 | Dirigida de `order-confirmation` definida |
| G-UNICA-14 | Regresión de los demás consumidores definida |
| G-UNICA-15 | Mutaciones significativas |
| G-UNICA-16 | Suite global planificada |
| G-UNICA-17 | `MATERIAL OQ = 0` |
| G-UNICA-18 | `UNKNOWN = 0` |
| G-UNICA-19 | Trazabilidad 100 % |

## 11. `/speckit.tasks`

| ID | Requisito | Acción | Aceptación | Mutación |
|---|---|---|---|---|
| T01 | FR-011 | `qa/alcance_de_usuario.py`: autoridad única, idempotente | `user_scopes` correcto y estable al repetir | UNICA-04 |
| T02 | FR-011 | `qa/n6_world.py` la usa | mundo N6 idéntico; N6 sigue 25/25 | — |
| T03 | FR-001/003/006 | `e2e/helpers/usuario.ts` canónico con fail-fast | usuario con el alcance pedido | UNICA-01/06 |
| T04 | FR-001 | Adoptar en los seis verificadores | los seis crean el usuario que declaran | UNICA-01 |
| T05 | FR-004 | `notifications` intacta | sigue alcanzando D1 y D2 | UNICA-05 |
| T06 | FR-009 | `e2e/alcance-de-usuario.spec.ts` U1..U4 | detecta la reintroducción | UNICA-01/02/03 |
| T07 | FR-005 | `order-confirmation` con D2 activa | pasa en tres navegadores | UNICA-01 |
| T08 | FR-012 | Suite global y clasificación | `UNKNOWN = 0` | — |

## 12. `/speckit.analyze` previo

| Búsqueda | Resultado |
|---|---|
| `create_user` sin alcance en escenario de empresa única | 6 (los que esta delta corrige) |
| Suposiciones implícitas de «una sola empresa» | 1 (`order-confirmation:329`) |
| `D1` codificada a ciegas | 0 — el ayudante recibirá la empresa del escenario |
| `D2` inactiva escondida | 0 — restaurada y verificada tras R2 |
| Cambios de producto / esquema / migración | 0 / 0 / 0 |
| `sleeps` · `retries` · `skips` · aserciones debilitadas | 0 · 0 · 0 · 0 |
| `BLOCKER` · `CRITICAL` · contradicciones · conflicto de dueña | 0 · 0 · 0 · 0 |
| Requisitos o tareas huérfanos | 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

**AUTORIZACIÓN EXPRESA CONSUMIDA.**

## 13. Implementación

| Fichero | Estado | Qué hace |
|---|---|---|
| `qa/alcance_de_usuario.py` | **nuevo** | Autoridad única para conceder acceso a una empresa. Valida antes de escribir, completa lo que falte, se niega a lo contradictorio |
| `resources/frontend/e2e/helpers/usuario.ts` | **nuevo** | Verificador de escenario canónico: crea el usuario, le da el rol y **declara su alcance**. Sin empresas, falla al instante |
| `resources/frontend/e2e/alcance-de-usuario.spec.ts` | **nuevo** | U1, U1b, U2, U3, U4, idempotencia, fallo temprano y rechazo de lo contradictorio |
| `qa/n6_world.py` | modificado | Deja de escribir `UserScope` por su cuenta |
| `qa/spec047-e2e-seed.py` | modificado | Ídem |
| `billing` · `dispatch` · `receivables` · `returns` · `order-confirmation` · `helpers/ventas` | modificados | Las seis copias del verificador pasan a ser una llamada al ayudante |
| `notifications.spec.ts` | **intacto** | Su usuario sigue sin alcance a propósito |

**Ficheros de producto = 0 · configuración = 0 · esquema = 0 · migraciones = 0.**

### Por qué el alcance se declara desde `qa/` y no por API

Porque **no hay API**. `user_scopes` no se escribe desde ninguna ruta ni desde ninguna
pantalla: `grep UserScope(` devuelve dos escrituras en todo el repositorio y las dos están
en `qa/`. Crear ese endpoint sería cambiar el producto, que es justo lo que esta delta no
hace. El E2E ya tenía un patrón para actuar sobre su propia base —`helpers/planificador.ts`
invoca la orden canónica del planificador con `KONTROL_E2E_DB_URL`— y es el que se
reutiliza. No se inventa una segunda manera.

### Un fallo de mi propio código que encontró la prueba de contrato

La primera versión de `declarar()` escribía y **después** comprobaba. Ante una petición
contradictoria añadía su fila, fallaba a continuación, y el usuario quedaba operando en más
empresas que las de cualquiera de las dos peticiones. La prueba «pedir un alcance que
contradice el ya declarado falla, no se acumula» lo detectó en la primera ejecución. Ahora
valida antes de escribir y, cuando se niega, no ha escrito nada.

## 14. Resultados

| Medición | Antes | Después |
|---|---|---|
| `order-confirmation`, Chromium, `D2` activa | 6/7 (serializado) · 5/7 (dos trabajadores) | **7 / 7** |
| Cobertura de contrato del fixture | no existía | **8 / 8** |
| Los ocho consumidores del ayudante | — | **80 / 80** |
| N6 + ayudante de empresa (deudas ya cerradas) | — | **29 / 29** |
| Firefox · WebKit (dirigida) | — | **15 / 15** · **15 / 15** |
| Deriva de esquema | 21 operaciones | **21** — `NEW_DRIFT = 0` |
| Cabeza Alembic | `0057_spec047_notifications` | igual |

## 15. Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| UNICA-01 | El usuario de empresa única deja de declarar alcance | **muere** — 5 fallos: U1, U1b, U2 y `order-confirmation`, que es el defecto original |
| UNICA-02 | Se concede una empresa distinta de la pedida | **muere** — 11 fallos |
| UNICA-03 | La empresa sale del preparador, no del escenario («siempre D1») | **muere** — U2 y U3 |
| UNICA-04 | Se admite el alcance contradictorio | **muere** — la prueba de contradicción |
| UNICA-05 | Sin empresas declaradas se decide por el caller | **muere** — la prueba de fallo temprano |
| UNICA-06 | La orden informa de lo que había, no de lo pedido | **muere** — 13 fallos |

**6/6 significativas.** Restauración verificada con `cmp` en las seis.

UNICA-02 además **ensució la base**: concedió a `ua` una empresa de más y, al resembrar, la
guarda de `declarar()` se negó en voz alta a reconciliar un alcance contradictorio. Es la
conducta correcta y conviene decir el precio: una base cuyos alcances se han manipulado hay
que repararla a mano, y el mensaje de error dice exactamente qué sobra. Se repararon los
cinco usuarios sembrados y se verificó el resultado antes de seguir.

## 16. Deuda nueva encontrada, no absorbida

**`INV-MOVTYPE-CARRERA`** — `create_movement_type` (`app/modules/inventory/api.py:192-200`)
consulta y luego inserta sin proteger la carrera: dos peticiones simultáneas de la misma
empresa pasan las dos la consulta y la segunda sale como **500 `INTERNAL_ERROR`** en vez de
`409 MOVEMENT_TYPE_DUPLICATE`. El helper interno del mismo módulo
(`service.py:1648-1657`) sí lo hace bien, con `begin_nested()` y `es_violacion_unica`, y su
comentario describe este caso exacto. Contra el Principio 25.

Reproducción: aislada **pasa**, el fichero serializado **pasa**, con dos trabajadores
**falla**. Es una carrera y es de producto: `PRODUCT_DEFECT_DISCOVERED`. **No se corrige
aquí** —`PRODUCT FILE CHANGES = 0`— y se registra con dueña por decidir.

## 17. Suite global re-medida

Denominador recalculado, no heredado. Base `keu` limpia, `D1` y `D2` **activas**.

| Medida | Valor |
|---|---|
| Ficheros de prueba | **29** |
| Pruebas ejecutadas (Chromium) | **220** |
| Pasan | **219** |
| Fallan | **1** |
| Omitidas · sin ejecutar | 0 · 0 |

### Clasificación de lo que queda

| Clase | N.º | Detalle |
|---|---|---|
| `E2E_SEED_EMPRESA_UNICA` | **0** | — |
| `NEW_REGRESSION_EMPRESA_UNICA` | **0** | — |
| `N6_MULTICOMPANY_STARTUP` | **0** | 25/25 en la global |
| `E2E_HELPER_EMPRESA_AMBIGUO` | **0** | 4/4 en la global |
| `E2E_031_RESERVAS` | **1** | `putaway.spec.ts:341` cuenta **todas** las reservas de la empresa porque el endpoint no sabe filtrar por documento, y otra prueba reservó en paralelo: 298 esperadas, 299 leídas. Aislada pasa 9/9. Es el mecanismo exacto que el registro de esa deuda describe, manifestado en `putaway` y no solo en `picking` |
| `E2E_046_TIPOS` | **0** | `documents:309` pasó; con el antivirus disponible las dos suites de documentos van 12/12 |
| `EXTERNAL_ENVIRONMENT` | **0** en la medición final | En una medición previa 5 fallos de `documents` por no estar el antivirus en la máquina. Resuelto **en el entorno**: ClamAV 1.4.3 reinstalado y firma de prueba reconstruida sobre los bytes exactos que sube la suite. Sin tocar el repositorio |
| `PRODUCT_DEFECT_DISCOVERED` | **1**, no en esta ejecución | `INV-MOVTYPE-CARRERA` (§16): carrera en `create_movement_type`. Registrada, no absorbida |
| `TEST_DEFECT_OTHER` · `PREEXISTING_SEALED` · `INBOX_045_AISLAMIENTO` · `AUTH_MC_INTERMITTENT` | 0 | — |
| `UNKNOWN` | **0** | — |

## 18. `/speckit.analyze` final

| Búsqueda | Resultado |
|---|---|
| `create_user` sin alcance en escenario de empresa única | **0** |
| `D1` codificada a ciegas como default | **0** — UNICA-03 lo demuestra |
| `D2` inactiva escondida | **0** — activa en toda la medición, verificado por consulta |
| `D2` borrada · cobertura multiempresa reducida | **0** · **0** |
| Fuga de alcance entre pruebas · filas duplicadas | **0** · **0** |
| Cambios de producto · configuración · esquema · migraciones | **0** · **0** · **0** · **0** |
| `sleeps` · `retries` · `skips` · aserciones debilitadas | **0** · **0** · **0** · **0** |
| Dos maneras de conceder alcance | **0** — una sola, `qa/alcance_de_usuario.py` |
| `BLOCKER` · `CRITICAL` · contradicciones · conflicto de dueña | 0 · 0 · 0 · 0 |
| Requisitos huérfanos · tareas huérfanas | 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

## 19. Trazabilidad

| Requisito | Evidencia | Mutación |
|---|---|---|
| FR-054-UNICA-001 | `helpers/usuario.ts` declara alcance en `user_scopes`; U1 lo mide | UNICA-01 |
| FR-054-UNICA-002 | U1/U2 pasan con `D1` y `D2` activas; R2 mostró la dependencia anterior | UNICA-01 |
| FR-054-UNICA-003 | `empresas` es obligatorio y explícito; U3 cubre varias, U4 sin restricción | UNICA-05 |
| FR-054-UNICA-004 | `notifications` intacta y verde (7/7); U4 fija su contrato | UNICA-05 |
| FR-054-UNICA-005 | `order-confirmation` 7/7 con `D2` activa, en tres navegadores | UNICA-01 |
| FR-054-UNICA-006 | Fallo temprano medido por «pedir un usuario sin decir su empresa» | UNICA-05 |
| FR-054-UNICA-007 | U4 comprueba que la semántica del producto no cambió | — |
| FR-054-UNICA-008 | `git status`: nada bajo `app/` ni `src/`; `alembic check` 21 → 21 | — |
| FR-054-UNICA-009 | `alcance-de-usuario.spec.ts`, 8 pruebas | UNICA-01/02/03 |
| FR-054-UNICA-010 | «declarar dos veces lo mismo no acumula» | UNICA-04 |
| FR-054-UNICA-011 | `grep UserScope(`: una sola escritura, en `qa/alcance_de_usuario.py` | UNICA-06 |
| FR-054-UNICA-012 | §17 | — |

Cobertura **100 %**, huérfanos **0**.

### Clasificación de cada consumidor

| Consumidor | Tipo | Cómo quedó |
|---|---|---|
| `billing` · `dispatch` · `receivables` · `returns` · `helpers/ventas` (`rates`, `treasury`) | empresa única | Declaran la empresa del escenario; 80/80 |
| `order-confirmation` | empresa única, **entra por interfaz** | Declara y pasa con `D2` activa |
| `notifications` | **sin restricción, a propósito** | Intacta; U4 fija ese contrato para que nadie se lo cambie por descuido |

## 20. Convergencia

| Criterio | Estado |
|---|---|
| Causa raíz | **PROBADA** (R1, R2, R3) |
| Dueña | **RESUELTA** — 054, apoyo 033 |
| Semántica del producto | **SIN CAMBIOS** (U4) |
| Modelo de alcance | **VERIFICADO** |
| Consumidores | **TODOS CLASIFICADOS** |
| `D2` | **ACTIVA** de principio a fin |
| Tres navegadores | **PASAN** |
| `E2E_SEED_EMPRESA_UNICA` | **0 fallos** |
| Regresión de N6 y del ayudante de empresa | **PASAN** |
| Mutaciones | **6/6 mueren**, restauradas |
| Suite global | **220 · 219 · 1**, clasificada |
| `UNKNOWN` | **0** |
| Producto · esquema · migraciones · deriva nueva | 0 · 0 · 0 · 0 |

**VEREDICTO: CASO A — `E2E-SEED-EMPRESA-UNICA` COMPLETE / CONVERGED.**
