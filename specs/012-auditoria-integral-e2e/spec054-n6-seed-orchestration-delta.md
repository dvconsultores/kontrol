# SPEC 054 · Delta dirigida — N6-MULTICOMPANY-STARTUP

**Fecha** 2026-09-17 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`) ·
**Apoyo** SPEC047 (`qa/spec047-e2e-seed.py`) · **Base** `9e81019` · **Rama** `develop`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `git rev-parse HEAD` | `9e81019c939d95bacdc20920ad2710fe19d5c141` |
| `EXPECTED_HEAD` | `9e81019` — **coincide** |
| `COMMITS_AFTER_9E81019` | **0** |
| Rama | `develop` |
| Árbol | dos artefactos sin seguimiento, **preservados**: `KONTROL_MASTER_COMPLETENESS_AUDIT.md` y `qa/audits/KONTROL-AUDIT-POLICY-CLOCK-LOCAL-20260917/` |
| Clasificación de esos dos | `AUDIT_ARTIFACT_PRESERVED` — no entran en el commit de esta delta |

## 2. Dueña canónica

`N6_MULTICOMPANY_STARTUP` es una deuda de **señal E2E**: no hay defecto de producto en
juego, hay una suite que no llega a ejecutarse. La autoridad sobre las suites E2E y su
entorno es **SPEC054**, cuya carpeta física es `specs/012-auditoria-integral-e2e`
(`docs/roadmap/spec-equivalence-map.md:61`). Ahí está registrada la deuda
(`spec054-company-helper-delta.md` §14) y ahí viven los artefactos de esta delta.

**SPEC047 entra como apoyo** y solo por evidencia física: `qa/spec047-e2e-seed.py:38-43`
crea la empresa `D2` del tenant `DEMO`, y `qa/n6-multicompany-bootstrap.py:116-120` crea
**otra** empresa con el mismo `code="D2"` en el mismo tenant, con distinto `legal_name` y
distinto `rif`. Dos guiones escriben la misma identidad lógica con contenidos distintos:
es autoridad duplicada, y se resuelve en esta delta.

**SPEC003 y SPEC001 no entran.** Se comprobó si el defecto estaba en la resolución de
empresa (`app/core/company_context.py`) o en el contrato de alcances: no lo está. La
conducta del producto es la especificada; lo que falla es la siembra.

## 3. Inventario físico de la siembra E2E

Todos los guiones del directorio `qa/` que escriben datos de E2E, leídos enteros:

| Guion | Base a la que escribe | Qué escribe | Idempotente | Destructivo |
|---|---|---|---|---|
| `qa/pg-e2e-seed.py` | la de `KONTROL_DB_URL` | instalación, tenant `DEMO`, empresa `D1`, usuario `admin`, licencia `MULTI_COMPANY` | **sí** (`initialize` falla y hace `rollback`; la licencia se reimporta) | no |
| `qa/spec047-e2e-seed.py` | la de `KONTROL_DB_URL` | empresa `D2` del tenant `DEMO`; `UserScope(admin → D1)` si `admin` no tenía ninguno | **sí** (busca por `(tenant, code)`) | no |
| `qa/n6-multicompany-bootstrap.py` | **otra**: fichero SQLite `${TMPDIR}/kontrol-qa-n6.db` | instalación, tenant `DEMO`, `D1`, `admin`, licencia, empresa `D2`, tenant `DEMO2`, empresa `E1`, sucursales, almacenes, terceros `SOLO-DE-A`/`SOLO-DE-B`, usuarios `ua`/`ub`/`uab`/`uc`, y el fichero de ids | **no** | **sí**: `os.remove(DB_FILE)` en la línea 24 |
| `qa/n4-legacy-hostile-seed.py` | `kontrol_legacy` | fuera del alcance del E2E | — | — |

**Orden de ejecución declarado:** `pg-e2e-seed` → `spec047-e2e-seed` (lo dice el propio
docstring de la 047, línea 3). **Quién lo ejecuta:** nadie automáticamente.
`playwright.config.ts` **no tiene `globalSetup`**; la cadena se invoca a mano.

## 4. Identificación física de D2

| Pregunta | Respuesta medida |
|---|---|
| ¿Qué es `D2`? | Una segunda empresa del tenant `DEMO`, `status=ACTIVE` |
| ¿Quién la crea en la base del E2E? | `qa/spec047-e2e-seed.py`, con `legal_name='SEGUNDA EMPRESA E2E 047 CA'`, `rif='J-40470470-7'` |
| ¿Quién crea otra `D2`? | `qa/n6-multicompany-bootstrap.py`, con `legal_name='INVERSIONES SEGUNDA EMPRESA COMPAÑIA ANONIMA'`, `rif='J-40771283-5'`, en su propia base SQLite |
| ¿Colisionan hoy? | **No en la misma fila**, porque viven en bases distintas. Colisionarían en cuanto ambos apuntaran a la misma base: mismo `(tenant, code)`, contenido distinto |
| ¿Se puede borrar `D2`? | **No.** `notifications.spec.ts:244` la exige por nombre y `n6-multicompany.spec.ts` necesita dos empresas en el mismo tenant. Borrarla es borrar cobertura |

## 5. Causa raíz de `N6_MULTICOMPANY_STARTUP`

**El mundo que las 25 pruebas necesitan nunca se escribe en la base contra la que corren.**

`n6-multicompany.spec.ts` y `n6-a11y-responsive.spec.ts` entran como `ua`, `ub` o `uab`.
Esos usuarios los crea únicamente `qa/n6-multicompany-bootstrap.py`, que:

1. fija `KONTROL_DB_URL` a un fichero **SQLite propio** (línea 30), ignorando la base del E2E;
2. **borra ese fichero** antes de empezar (línea 24), de modo que no se puede ejecutar
   «encima» de nada;
3. vuelve a hacer `initialize()` desde cero (línea 57), que sobre una base ya inicializada
   fallaría.

Es decir: no es que la cadena de siembra se ejecute en mal orden, es que **ese guion es
estructuralmente incapaz de sembrar la base compartida**. Contra PostgreSQL los usuarios
no existen, el formulario de acceso no abre sesión y las 25 pruebas caducan en
`expect(page).toHaveURL(/\/$/)`.

Verificación física sobre la base del E2E recién sembrada (`kn6`):

```
select username from users → admin, bill-*, check-*, cxc-*, dev-*, disp-*, n047*, tz-*
(ningún ua, ub, uab, uc)
select code from tenants → DEMO         (ningún DEMO2)
select code from companies → D1, D2     (ninguna E1)
```

Y el fichero de ids que la suite lee, `/tmp/kontrol-n6-ids.json`, contiene los
identificadores del mundo **SQLite** —`empresa_a = b43007f6…`— que no existen en
PostgreSQL. La suite carga, entra al `login`, y ahí se queda.

### Hipótesis descartadas, con evidencia

| Hipótesis | Descartada porque |
|---|---|
| Colisión de siembras | Las dos siembras nunca se han ejecutado sobre la misma base |
| No idempotencia | `pg-e2e-seed` y `spec047-e2e-seed` son idempotentes (§7) |
| Dependencia de orden | El fallo es idéntico con cualquier orden: los usuarios no existen en ninguno |
| Actualización destructiva | Nada borra `ua`/`ub`/`uab`: nunca llegaron a existir |
| Contexto obsoleto | El fallo ocurre **antes** de resolver empresa, en el propio acceso |
| Defecto de producto | `POST /auth/login` responde correctamente: el usuario no existe |
| Entorno | Backend, Vite y PostgreSQL responden; `admin` entra en la misma ejecución |

## 6. Reproducción R1 — base limpia, siembra estándar, `D2` activa

Base `kn6` creada de cero, `alembic upgrade head`, `pg-e2e-seed.py`, `spec047-e2e-seed.py`,
backend reapuntado, suite global en Chromium.

| Medida | Valor |
|---|---|
| Ejecutadas | **212** |
| Pasan | **185** |
| Fallan | **27** |
| No ejecutadas | 0 |

Los 27, clasificados uno a uno:

| Nº | Prueba | Clasificación |
|---|---|---|
| 1 | `documents.spec.ts:309` tipos documentales | `PREEXISTING_SEALED` → **E2E-046-TIPOS**, dueña 046 |
| 2–13 | `n6-a11y-responsive.spec.ts` (12) | `N6_MULTICOMPANY_STARTUP` |
| 14–26 | `n6-multicompany.spec.ts` (13) | `N6_MULTICOMPANY_STARTUP` |
| 27 | `order-confirmation.spec.ts:323` | `E2E_SEED_EMPRESA_UNICA` |

**`N6_MULTICOMPANY_STARTUP` = 25. `UNKNOWN` = 0.**

### La medición anterior estaba contaminada y se descarta

El informe de `9e81019` daba 185/26 con `notifications:243` fallando por `409`. Esa base
tenía `D2` en `INACTIVE`, resto del experimento de causalidad de aquella delta: `409` es
`COMPANY_INACTIVE` (`app/core/company_context.py:153`). Sobre base limpia
`notifications:243` **pasa**, y aparece en su lugar `order-confirmation:323`. Se
**re-mide** y no se reutiliza ninguna cifra anterior.

## 7. Idempotencia, conmutatividad y diferencia lógica

Medido sobre `kn6`, comparando instantáneas lógicas completas (recuentos de
`tenants`, `companies`, `users`, `user_scopes`, `user_roles`, `parties`, artefactos y
eventos de licencia, más la fila de cada empresa) tras cada ejecución:

| Prueba | Resultado |
|---|---|
| `pg-e2e-seed.py` ×3 | Entidades idénticas: `setup: La instalación ya fue inicializada` |
| `spec047-e2e-seed.py` ×3 | Idéntico: `D2` se busca por `(tenant, code)`; el alcance del `admin` solo se crea si no tenía ninguno |
| Diferencia lógica que introduce la 047 | `+1 companies (D2, ACTIVE)`, `+1 user_scopes (admin → D1)` |
| Conmutatividad | La 047 **exige** que la 045 haya corrido: sin tenant `DEMO` lanza `NoResultFound`. El orden no es opcional y por eso esta delta lo fija en un único punto |

### Una fuga de idempotencia encontrada al medir, y corregida

`pg-e2e-seed.py` **no** era del todo idempotente: reimportaba la licencia en cada
ejecución. El estado no cambiaba —`license_states` se actualiza por instalación— pero
`license_artifacts` y `license_events` pasaron de 1 a 4 en tres repeticiones. Con la
siembra corriendo antes de cada suite eso escribiría una historia de importaciones que
nunca ocurrieron sobre una base de QA que dura semanas. La licencia se importa ahora
cuando hace falta: si ya hay una en `FULL_ACCESS` o `GRACE` y sin vencer, no se toca.
Medido tras la corrección: `lic_art = 4` antes y después de tres cadenas completas.

## 8. Causa raíz de `E2E_SEED_EMPRESA_UNICA`

**Un usuario creado por la API no declara alcance, así que su conjunto de empresas es el
que la base tenga en ese momento.**

`identity_access/service.py::create_user` no escribe ninguna fila en `user_scopes`, y
`app/core/company_context.py:82-83` dice —correctamente, y por decisión especificada— que
sin alcance declarado se admiten todas las empresas del tenant. Con `D2` activa eso son
dos, la interfaz pide elegir (`EstadoDeEmpresa.tsx:56`) y la pantalla de negocio no se
pinta.

Medido contra la base del E2E:

```
admin              → empresas alcanzables: 1  ['D1']
check-mu5m7p1lm1c1 → empresas alcanzables: 2  ['D1', 'D2']
```

`admin` tiene alcance porque se lo pone `qa/spec047-e2e-seed.py:47`. Los usuarios que las
suites crean —`bill-*`, `check-*`, `cxc-*`, `dev-*`, `disp-*`— tienen **cero** alcances:
53 usuarios en la base, 52 sin alcance.

**Radio de impacto medido, no supuesto.** De las seis suites que crean usuarios por API,
**solo `order-confirmation` entra por la interfaz con uno de ellos**
(`order-confirmation.spec.ts:329`). Las demás los usan por API mandando siempre
`X-Kontrol-Company`, donde la cabecera resuelve la ambigüedad. Por eso el defecto produce
**exactamente un fallo**, y no dieciocho.

### R2 — causalidad demostrada en los dos sentidos

| Ejecución | Única variable | Resultado |
|---|---|---|
| R2a | `D2 = ACTIVE` | `order-confirmation` **1 falla / 6 pasan** |
| R2b | `D2 = INACTIVE` | `order-confirmation` **7 / 7** |
| Restauración | `D2 = ACTIVE` | verificada por consulta |

## 9. Clasificación de `E2E_SEED_EMPRESA_UNICA`

**`INDEPENDENT_ROOT_CAUSE`.** Prueba por contrafactuales:

- Si `D2` no existiera, `N6_MULTICOMPANY_STARTUP` **seguiría fallando**: sus usuarios no
  existen, y eso es independiente del número de empresas.
- Si el mundo N6 no existiera, `E2E_SEED_EMPRESA_UNICA` **seguiría fallando**: `D2` la
  crea la siembra de la 047, que nada tiene que ver con N6.
- Ninguna de las dos correcciones arregla la otra: sembrar `ua`/`ub`/`uab` no da alcance a
  `check-*`, y dar alcance a `check-*` no crea `ua`.

Comparten **familia** —ambas son deuda de la capa de siembra— pero no causa. Por tanto
**NO se absorbe**: queda `OPEN`, dueña 054, con la causa raíz ya escrita y el radio de
impacto medido, que es más de lo que tenía al empezar esta delta.

Consecuencia declarada: al cerrar N6 la suite global **no llega a 0 fallos**. Quedan dos,
ambos identificados, con dueña y sin `UNKNOWN`.

## 10. `/speckit.specify` — requisitos

| ID | Requisito |
|---|---|
| FR-054-N6-001 | El mundo multiempresa de N6 se puede sembrar en **la misma base** contra la que corre el E2E, sea cual sea su motor |
| FR-054-N6-002 | Esa siembra es **idempotente**: ejecutarla N veces deja la misma base que ejecutarla una |
| FR-054-N6-003 | Esa siembra **no borra ni recrea** nada: ni ficheros, ni bases, ni filas |
| FR-054-N6-004 | `D2` tiene **una sola definición** en todo `qa/`; ningún guion puede crear una `D2` distinta |
| FR-054-N6-005 | Los usuarios `ua`, `ub`, `uab` y `uc` se crean con **alcance declarado**, para que su conjunto de empresas no dependa del contenido de la base |
| FR-054-N6-006 | El fichero de identificadores que la suite lee describe **la base contra la que la suite corre** |
| FR-054-N6-007 | La cadena de siembra tiene **un único punto de entrada** con el orden fijado |
| FR-054-N6-008 | La cadena se ejecuta **automáticamente** antes de la suite cuando el lanzador declara la base |
| FR-054-N6-009 | Si la siembra automática no puede ejecutarse, la suite **falla en voz alta**, nunca en silencio |
| FR-054-N6-010 | `qa/n6-multicompany-bootstrap.py` sigue funcionando para su pila SQLite autónoma, **sin duplicar** la definición del mundo |
| FR-054-N6-011 | La siembra no añade al mundo compartido ninguna entidad que las pruebas N6 no ejerciten |
| FR-054-N6-012 | Ficheros de producto modificados = **0**; migraciones = **0**; esquema = sin cambios |
| FR-054-N6-013 | Ninguna siembra acumula filas al repetirse, tampoco de auditoría |
| FR-054-N6-014 | Las pruebas de N6 no afirman nada que dependa de qué siembra construyó la base ni de cuántos datos de otras suites haya |

## 11. `/speckit.clarify` — preguntas y respuestas

| # | Pregunta | Respuesta | ¿Material? |
|---|---|---|---|
| 1 | ¿Hay defecto de producto? | **No**: `login` rechaza a un usuario inexistente, que es lo correcto | No |
| 2 | ¿La empresa B de N6 es la `D2` de la 047? | **Sí**: mismo `(tenant, code)`. Se unifica en una definición | No |
| 3 | ¿Se puede borrar `D2`? | **No**, y además está prohibido | No |
| 4 | ¿Se puede dejar `D2` inactiva? | **No**: apaga cobertura multiempresa y está prohibido | No |
| 5 | ¿Sembrar sucursales y almacenes de N6? | **No**: las suites N6 no los ejercitan (`grep` en ambos ficheros: ninguna referencia). Añadir estructura que nadie usa a la base compartida solo puede perturbar a quien sí cuenta almacenes | No |
| 6 | ¿Y el tenant `DEMO2`? | **Sí**: `n6-multicompany.spec.ts:271` lo necesita para probar que la frontera de tenant se respeta | No |
| 7 | ¿`globalSetup` o guion manual? | **`globalSetup`**, condicionado a que el lanzador declare `KONTROL_E2E_DB_URL`. Sin esa variable no hace nada; con ella, siembra o falla ruidosamente | No |
| 8 | ¿Serializar la suite? | **No**, y está prohibido. `fullyParallel` se mantiene | No |
| 9 | ¿`E2E_SEED_EMPRESA_UNICA` se cierra aquí? | **No**: `INDEPENDENT_ROOT_CAUSE` (§9) | No |
| 10 | ¿`documents:309` se toca? | **No**: es `E2E-046-TIPOS`, dueña 046, en la lista de no tocar | No |
| 11 | ¿La nota de `E2E-046-TIPOS` sigue siendo exacta? | **No del todo**: decía «aislada pasa». Sobre base limpia falla también aislada, porque sin filas suficientes no hay “Página siguiente”. Se corrige la nota; el defecto **no se toca** | No |
| 12 | ¿Cambia el esquema? | **No**. `alembic check` se mide antes y después | No |

**MATERIAL OQ = 0 · UNKNOWN = 0 · PRODUCT FIX REQUIRED = NO.**

## 12. Compuerta constitucional

| Principio | Cumplimiento |
|---|---|
| 1 — Spec antes que código | Este documento precede a toda edición |
| 2 — Autorización expresa | Delta dirigida autorizada por el owner; `MATERIAL OQ = 0` |
| 3 — Trazabilidad completa | §17: requisito → prueba → mutación |
| 5 — Datos históricos protegidos | La siembra no borra ni reescribe nada |
| 9 — Instalación independiente | La siembra no toca producto ni despliegue |
| 10 — Calidad demostrable | R1/R2 medidos, mutaciones §16 |
| 14 — Infraestructura reproducible | Un único punto de entrada con orden fijo |
| 21 — Paridad del motor | La siembra deja de atarse a SQLite |
| 22 — Autoridad única | Una sola definición de `D2` y del mundo N6 |
| 24 — Instalación limpia | R1 se mide sobre base creada de cero |
| 27 — Mutación observable | §16: las que no cambian lo observable se descartan y se explican |

**COMPUERTA: PASA.**

## 13. `/speckit.plan`

`W01` checkpoint · `W02` dueña · `W03` inventario de siembras · `W04` identificar `D2` ·
`W05` causa raíz N6 · `W06` R1 sobre base limpia · `W07` clasificación · `W08` idempotencia
y conmutatividad · `W09` causa raíz y radio de `EMPRESA_UNICA` · `W10` R2 en dos sentidos ·
`W11` clasificación SAME/INDEPENDENT · `W12` módulo de mundo único · `W13` siembra E2E ·
`W14` unificar `D2` con la 047 · `W15` delegar el arranque SQLite · `W16` orquestador ·
`W17` `globalSetup` · `W18` Chromium · `W19` Firefox · `W20` WebKit · `W21` mutaciones ·
`W22` regresiones · `W23` suite global re-medida · `W24` clasificación final ·
`W25` analyze y trazabilidad · `W26` gobernanza · `W27` convergencia.

### Diseño

```
qa/n6_world.py          autoridad única del mundo N6: empresas, tenant 2, terceros,
                        usuarios con alcance. Idempotente. Recibe la sesión.
qa/n6-e2e-seed.py       lo aplica a KONTROL_DB_URL y escribe el fichero de ids.
qa/spec047-e2e-seed.py  deja de definir D2 por su cuenta: la pide al módulo.
qa/n6-multicompany-bootstrap.py  conserva su pila SQLite y delega el mundo al módulo.
qa/e2e-seed.sh          único punto de entrada, orden fijo, idempotente.
e2e/global-setup.ts     lo ejecuta antes de la suite si el lanzador declaró la base.
```

## 14. `/speckit.checklist`

| Compuerta | Comprobación |
|---|---|
| G-N6-01 | `HEAD = 9e81019`, 0 commits posteriores |
| G-N6-02 | Dueña 054 resuelta por el mapa de equivalencia |
| G-N6-03 | Las cuatro siembras leídas enteras e inventariadas |
| G-N6-04 | `D2` identificada físicamente en las dos siembras |
| G-N6-05 | Causa raíz N6 demostrada, no inferida |
| G-N6-06 | Siete hipótesis alternativas descartadas con evidencia |
| G-N6-07 | R1 sobre base creada de cero |
| G-N6-08 | Los 27 fallos de R1 clasificados, `UNKNOWN = 0` |
| G-N6-09 | Medición anterior declarada contaminada y descartada |
| G-N6-10 | Idempotencia de cada siembra medida ×3 |
| G-N6-11 | Diferencia lógica de la 047 capturada |
| G-N6-12 | Causa raíz de `EMPRESA_UNICA` demostrada con sonda directa |
| G-N6-13 | Radio de impacto medido suite a suite |
| G-N6-14 | R2 en los dos sentidos, con restauración verificada |
| G-N6-15 | `SAME` vs `INDEPENDENT` resuelto por contrafactuales |
| G-N6-16 | `D2` con una sola definición en todo `qa/` |
| G-N6-17 | Siembra idempotente ×3 sobre la base del E2E |
| G-N6-18 | `ua`/`ub`/`uab`/`uc` con alcance declarado |
| G-N6-19 | N6 = 25 fallos → **0**, en Chromium, Firefox y WebKit |
| G-N6-20 | Suite global re-medida; residuales clasificados; `UNKNOWN = 0` |
| G-N6-21 | `E2E-HELPER-EMPRESA` sigue en verde |
| G-N6-22 | `notifications` (SPEC047) sigue en verde |
| G-N6-23 | Ficheros de producto = 0; `alembic check` idéntico antes y después |
| G-N6-24 | Mutaciones significativas, restauración verificada con `cmp` |

## 15. `/speckit.tasks`

`T01` `qa/n6_world.py` · `T02` `qa/n6-e2e-seed.py` · `T03` unificar `D2` en la 047 ·
`T04` delegar en el arranque SQLite · `T05` `qa/e2e-seed.sh` · `T06` `e2e/global-setup.ts`
y `playwright.config.ts` · `T07` idempotencia ×3 · `T08` N6 en tres navegadores ·
`T09` mutaciones · `T10` regresiones · `T11` suite global · `T12` gobernanza.

## 16. Implementación

| Fichero | Estado | Qué hace |
|---|---|---|
| `qa/n6_world.py` | **nuevo** | Autoridad única del mundo N6: `D2`, tenant `DEMO2` + `E1`, terceros marcadores y los cuatro usuarios **con alcance declarado**. Buscar y, si falta, crear; nada se borra ni se reescribe |
| `qa/n6-e2e-seed.py` | **nuevo** | Aplica ese mundo a la base de `KONTROL_DB_URL` y escribe el fichero de identificadores |
| `qa/e2e-seed.sh` | **nuevo** | Único punto de entrada de la cadena, con el orden fijado: 045 → 047 → N6 |
| `resources/frontend/e2e/global-setup.ts` | **nuevo** | Ejecuta la cadena antes de la suite cuando el lanzador declara la base; sin esa variable no toca nada; si no puede, **falla** |
| `resources/frontend/e2e/helpers/n6-mundo.ts` | **nuevo** | Lee el mundo sembrado —ids **y nombres**— con un error que nombra el remedio si falta |
| `qa/spec047-e2e-seed.py` | modificado | Deja de describir `D2` por su cuenta: la pide al módulo |
| `qa/n6-multicompany-bootstrap.py` | modificado | Conserva su pila SQLite y delega el mundo; sus sucursales y almacenes pasan a ser idempotentes |
| `qa/pg-e2e-seed.py` | modificado | No reimporta una licencia que ya sirve |
| `resources/frontend/playwright.config.ts` | modificado | Declara el `globalSetup` |
| `e2e/n6-multicompany.spec.ts` · `e2e/n6-a11y-responsive.spec.ts` | modificados | Dejan de codificar a mano el nombre de la empresa y de suponer que el tercero cabe en la primera página |

**Ficheros de producto = 0. Migraciones = 0. Esquema = sin cambios.**

### Lo que apareció al poder ejecutar la suite por primera vez

Sembrado el mundo, las 25 pruebas arrancaron y quedaron **7** fallos. No eran del
arranque: eran suposiciones que la suite había heredado de correr siempre contra una base
recién fabricada para ella.

| Fallos | Suposición | Por qué falla en la base compartida |
|---|---|---|
| 5 | El nombre de la empresa A es `"GLOBAL DV…"` | La empresa A es la que ya hubiera en el tenant: `Demo C.A.` en la base del E2E. Comprobar el literal era comprobar qué guion sembró |
| 2 | El tercero marcador se ve en la primera página | La lista pagina de veinte en veinte y la base del E2E acumula 94 terceros de otras suites |

Ambas se corrigen leyendo el mundo en vez de suponerlo: los nombres viajan con los
identificadores en el mismo fichero, y el marcador se busca por su prefijo. Buscar es
además **más exigente** que mirar la página: si el tercero de la otra empresa se colara, la
búsqueda lo traería a primera fila en vez de esconderlo al final.

### Un fallo de entorno, no del producto

WebKit dejaba caer tres pruebas —recargar, segunda pestaña, sesión restaurada—. La causa
estaba en el lanzador local, no en el repositorio: servía por `http://` sin
`KONTROL_COOKIE_SECURE=false`, y WebKit se niega a guardar una cookie `Secure` desde un
origen inseguro, así que la sesión no se restauraba. Es exactamente lo que advierte el
docstring de `qa/n6-multicompany-bootstrap.py:8-13`. Corregido **en el entorno**, sin tocar
el repositorio: 25/25 en WebKit.

## 17. Resultados

| Medición | Antes (R1) | Después |
|---|---|---|
| N6, Chromium | 0 / 25 | **25 / 25** |
| N6, Firefox | no ejecutable | **25 / 25** |
| N6, WebKit | no ejecutable | **25 / 25** |
| Suite global (Chromium) | 212 · 185 pasan · **27** fallan | 212 · **211 pasan · 1 falla** |
| `N6_MULTICOMPANY_STARTUP` | 25 | **0** |
| Deriva de esquema (`alembic check`) | 21 operaciones | **21 operaciones** — `NEW_DRIFT = 0` |

### El fallo que queda, clasificado

| Prueba | Clasificación | Dueña |
|---|---|---|
| `order-confirmation.spec.ts:323` | `E2E_SEED_EMPRESA_UNICA` — `INDEPENDENT_ROOT_CAUSE` (§9) | 054, **OPEN** |

`UNKNOWN = 0`. `documents.spec.ts:309` (**E2E-046-TIPOS**) pasó en esta ejecución y falló en
R1: depende de cuántos tipos documentales lleve la base, que es justo lo que su registro
describe. **No se absorbe**; se precisa su nota, porque decía «aislada pasa» y sobre base
limpia falla también aislada.

## 18. Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| M1 · alcance | Los usuarios sembrados no declaran alcance | **muere** — 4 fallos, justo los del alcance |
| M2 · reutilización | La empresa no se reutiliza: cada siembra crea otra `D2` | **muere** — 13 fallos |
| M5 · orquestación | La suite ya no siembra antes de empezar | **muere** — y lo hace con **una frase** que nombra el remedio, no con 25 caducidades de 20 s |
| M6 · nombre fijo | El nombre de la empresa vuelve a estar escrito a mano | **muere** — 5 fallos, los mismos que corrigió |
| M7 · paginación | El marcador vuelve a suponerse en la primera página | **muere** — 1 fallo |

**5/5 efectivas.** Restauración verificada con `cmp` en todas; las filas que M2 y M3
dejaron en la base se retiraron y se comprobó el recuento.

Se intentaron y **se descartan** dos, en vez de contarlas:

- **M3 · idempotencia** (el tercero se siembra otra vez en cada ejecución): con la cadena
  corrida tres veces quedan `SOLO-DE-A ×4` y `SOLO-DE-B ×4`, y la suite **pasa 25/25**. Es
  coherente: la prueba pregunta si el marcador de A está y si el de B no está, y duplicar
  el de A no cambia ninguna de las dos respuestas. La idempotencia queda respaldada por la
  medición directa de §7 —instantáneas lógicas idénticas ×3—, no por una mutación.
- **M4 · cambio de contraseña obligatorio** (`must_change_password=True` en los usuarios
  sembrados): la suite **pasa 25/25**. Se comprobó que la mutación llega de verdad a la
  base (`ua must_change=true`) y que el servidor lo publica en la respuesta de acceso, y
  aun así la prueba llega a `/`. Se deja el indicador en falso por exactitud del dato
  —nadie va a cambiar la contraseña de una cuenta de QA— y **no** se cuenta como mutación.

## 19. Regresiones

| Suite | Resultado |
|---|---|
| `e2e/empresa-helper.spec.ts` y las cuatro que consumen el ayudante (`E2E-HELPER-EMPRESA`) | verde en la global |
| `e2e/notifications.spec.ts` (SPEC047) | verde en la global, incluida `lo de una empresa no se ve ni se cuenta en otra` |
| Regresión de backend | **1664 recolectadas, 0 fallos** (salida 0), igual que la línea base de POLICY-CLOCK-LOCAL: 1656 pasan · 8 omitidas |
| `POLICY-CLOCK-LOCAL` | no se reabre: ningún fichero de `app/` ni de `src/` tocado |
| `eslint` sobre los ficheros nuevos | sin hallazgos |
| `tsc --noEmit` | **Corregido después** (2026-09-17): `tsc -p tsconfig.json` solo cubre `src` —`tsconfig.app.json` declara `include: ["src"]`—, así que **`e2e/` no entra en el typecheck del proyecto** y aquella ejecución, aunque limpia, no comprobó los ficheros nuevos. Verificado después con un typecheck explícito sobre `e2e/`: sin hallazgos. La conclusión no cambia; la afirmación estaba mal |
| `ruff` sobre `qa/` | mismo recuento antes y después: ningún hallazgo nuevo |
| Deriva de esquema | 21 operaciones, idéntica |

## 20. Hallazgo registrado, no corregido aquí

Al morir M2 quedó a la vista que **`companies` no tiene índice único sobre
`(tenant_id, code)`**: la mutación creó tres `D2` en el mismo tenant sin que la base se
quejara. La unicidad de la identidad de empresa descansa hoy en la disciplina de cada
guion, no en el motor. Corregirlo es una migración —y esta delta tiene migraciones = 0—,
así que se registra como deuda nueva y **no se absorbe**.

## 21. `/speckit.analyze` y trazabilidad

| Requisito | Evidencia | Mutación |
|---|---|---|
| FR-054-N6-001 | `qa/n6-e2e-seed.py` siembra sobre `KONTROL_DB_URL`; 25/25 contra PostgreSQL | M5 |
| FR-054-N6-002 | §7: instantáneas lógicas idénticas en tres repeticiones de la cadena | — (M3 descartada, razonada) |
| FR-054-N6-003 | `qa/n6_world.py` solo hace `select` y `add`; ningún `delete`, ningún `remove` | M2 |
| FR-054-N6-004 | `qa/spec047-e2e-seed.py` pide `EMPRESA_B` al módulo; `grep` de `code="D2"` en `qa/`: una sola aparición | M2 |
| FR-054-N6-005 | `ua→D1`, `ub→D2`, `uab→D1+D2`, `uc→E1`, consultado en la base | M1 |
| FR-054-N6-006 | El fichero de ids lo escribe la misma siembra que crea las filas | M5 |
| FR-054-N6-007 | `qa/e2e-seed.sh` | M5 |
| FR-054-N6-008 | `playwright.config.ts` → `globalSetup`; la cadena aparece en la cabecera de cada ejecución | M5 |
| FR-054-N6-009 | Sin mundo, la suite muere con una frase que nombra el remedio (§18, M5) | M5 |
| FR-054-N6-010 | `qa/n6-multicompany-bootstrap.py` delega y conserva su pila | — |
| FR-054-N6-011 | Ni sucursales ni almacenes en la siembra compartida; `grep` en las suites N6: ninguna referencia | — |
| FR-054-N6-012 | `git status`: ningún fichero bajo `app/` ni `src/`; `alembic check` idéntico | — |
| FR-054-N6-013 | `license_artifacts` estable en 4 tras tres cadenas completas | — |
| FR-054-N6-014 | Nombres leídos del mundo; marcador buscado, no paginado | M6 · M7 |

### Compuertas

`G-N6-01`…`G-N6-24`: **24/24 satisfechas**. Las dos que dependían de mutaciones
descartadas (`G-N6-17` idempotencia, `G-N6-24` significatividad) se satisfacen con la
medición directa y con la declaración explícita de lo descartado.

## 22. Cobertura que este entorno no permite, declarada

- ~~La pila SQLite autónoma no se re-ejecutó de extremo a extremo.~~ **Cubierto después**
  (2026-09-17, tras el commit): se levantó esa pila —`qa/n6-multicompany-bootstrap.py`,
  backend sobre `sqlite+pysqlite:////tmp/kontrol-qa-n6.db`, Vite— y la suite pasa
  **25/25 en Chromium, Firefox y WebKit** también ahí. El mundo se verificó fila a fila:
  dos tenants, `D1`/`D2`/`E1`, sucursales `A1`/`B1`/`C1`, almacenes `ALM-A`/`ALM-B`,
  ambos terceros marcadores y `ua→D1`, `ub→D2`, `uab→D1+D2`, `uc→E1`.

  Lo que esto demuestra, y no se podía demostrar antes: en esa pila la empresa A se llama
  `GLOBAL DV ASESORES, C.A.` y en la del E2E `Demo C.A.`, y **la misma suite sin tocar
  pasa contra las dos**. Es la comprobación directa de FR-054-N6-014.

  De paso quedó verificada la guarda de FR-054-N6-008: sin `KONTROL_E2E_DB_URL`, la
  ejecución arranca en «Running 25 tests» sin cadena de siembra alguna, porque el
  `globalSetup` no escribe en una base que no administra.
- **A→B en las suites que no son de N6** sigue sin cubrirse: el `admin` de la base del E2E
  está acotado a `D1` a propósito. Lo que sí quedó cubierto, y antes no, es el cambio de
  empresa completo dentro de `n6-multicompany.spec.ts`.

## 23. Convergencia

| Criterio | Estado |
|---|---|
| `N6_MULTICOMPANY_STARTUP` | **0 fallos** en tres navegadores · deuda **CERRADA** |
| `E2E_SEED_EMPRESA_UNICA` | `INDEPENDENT_ROOT_CAUSE` · **OPEN**, con causa raíz y radio medidos |
| Suite global | 212 · 211 pasan · 1 falla, clasificada |
| `UNKNOWN` | **0** |
| Ficheros de producto | **0** |
| Migraciones · esquema | **0** · sin cambios |
| Mutaciones | 5 efectivas · 2 descartadas y explicadas |
| Deudas nuevas registradas | `SEED-EMPRESA-CODIGO-NO-UNICO` |
