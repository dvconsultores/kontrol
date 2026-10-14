# REMEDIACIÓN `REM-AUTH-ROUTE-CRAWL-001` — CIERRE

Fecha: 2026-08-30 · Rama `develop` · PostgreSQL 18.6

## Root Cause

**Dos renovaciones de sesión concurrentes con el mismo refresh token de un solo uso.**

El access token vive en memoria (`ADR-004`), así que **toda recarga** dispara la
restauración de sesión. En `AuthContext` había dos caminos que renovaban:

| Camino | Cómo llamaba |
|---|---|
| Restauración al montar | `refreshSession()` **directamente**, sin pasar por el mutex |
| Renovación ante un 401 | `refreshOnce()` en `client.ts`, con mutex `refreshInFlight` |

El mutex existía desde el principio. El problema es que **el primer camino no
participaba en él**: la restauración inicial y un 401 concurrente lanzaban dos
`POST /auth/refresh` con la misma cookie.

`rotate_session` revoca la sesión anterior al emitir la nueva —es lo que da
valor a la rotación— de modo que las dos no pueden ganar:

- Si la primera confirma antes de que la segunda lea la sesión → la segunda
  recibe `SESSION_REVOKED` **401**.
- Si ambas leen antes de que ninguna confirme → las dos revocan la misma sesión
  y crean dos nuevas; sobrevive una sola cookie y la otra sesión queda **viva y
  huérfana**.

### Evidencia previa

Instrumentando la secuencia de peticiones al recargar, **dos `POST /auth/refresh`
en el mismo milisegundo**:

```
1784ms  ->  POST /auth/refresh
1784ms  ->  POST /auth/refresh
1822ms  <-  200 /auth/refresh
1824ms  <-  200 /auth/refresh
```

Y en la base, tras una sesión de pruebas:

| Métrica | Valor |
|---|---:|
| Sesiones creadas | 800 |
| Revocadas | 316 |
| **Vivas** | **484** |
| Eventos `SESSION_REFRESHED` | 624 |

484 sesiones vivas para un puñado de inicios de sesión: cada carrera perdida
dejaba una sesión que nadie volvería a usar y que ningún cierre revocaría.
El 401 del recorrido era el síntoma visible; la fuga de sesiones, el silencioso.

Clasificación (§15): **E · dos refresh simultáneos**, con causa contribuyente
**H · restauración de sesión incompleta**. No es `A` (test incorrecto) ni `I`
(fixture defectuoso): la prueba recarga la página igual que un usuario al pulsar
F5.

## Spec propietaria

**002 · Seguridad, autenticación y sesiones** — justificación en
`docs/remediation/route-crawl-auth-owner.md`.

## Cambio aplicado

Mínimo y dentro de la arquitectura ya aprobada. `ADR-004` y la baseline §6 ya
exigen rotación y revocación; el mutex ya existía. **Se corrige la
implementación, no se inventa otra arquitectura** (§19).

| Archivo | Cambio |
|---|---|
| `src/api/client.ts` | Se expone `requestSessionRefresh()`, la **puerta única** que comparte la renovación en vuelo |
| `src/app/contexts/AuthContext.tsx` | La restauración inicial pasa por esa puerta; el manejador se registra **antes** de restaurar, porque el orden de los efectos importa |
| `app/modules/identity_access/service.py` | `rotate_session` bloquea la fila de sesión antes de leer su estado — ver «Segundo defecto» |
| `e2e/route-crawl.spec.ts` | La escucha empieza tras el login y se añade una comprobación explícita de 401/403 por ruta |
| `qa/local-backend-bootstrap.py` | Docstring: `KONTROL_COOKIE_SECURE=false` es obligatorio en la pila local por http — ver «Hallazgo de entorno» |

Resultado inmediato: **una sola** `POST /auth/refresh` por recarga.

### Sobre el 401 que quedaba

Tras el arreglo quedaba un `401 AUTH_REQUIRED` en `POST /auth/refresh` durante
la carga de `/login`, **antes** de iniciar sesión. Se investigó en lugar de
silenciarlo:

- La aplicación **hace bien** en intentar restaurar: la cookie es `HttpOnly` y
  JavaScript no puede saber si existe.
- El backend **hace bien** en responder 401: no hay sesión.
- No se puede omitir el intento en `/login`: `LoginPage` redirige a `/` cuando
  hay sesión, y esa redirección depende justamente de la restauración. Omitirla
  dejaría a un usuario ya autenticado mirando el formulario.

Es decir: comportamiento correcto en las tres capas. El «error» lo registra el
navegador por cualquier respuesta no-2xx, y pertenece al login, no al recorrido.

Se corrigió la prueba —y **se hizo más estricta**, no más laxa:

| Antes | Ahora |
|---|---|
| Escucha desde antes del login; capta ruido de la preparación | Escucha desde después del login: mide lo que dice medir |
| Detecta 401 solo de refilón, por el texto de consola | **Comprueba explícitamente** que ninguna petición del recorrido devuelva 401 o 403, y nombra la ruta culpable |

Ninguna ruta se excluyó, ningún 401 se aceptó como éxito, ningún timeout se
amplió, ningún reintento ciego se añadió.

**Alternativa considerada y descartada:** una cookie legible de «pista de
sesión» para no intentar la restauración en frío. Añade superficie de cookie y
es una decisión de arquitectura de la Spec 002, no de una remediación puntual.
Queda anotada por si 002 la retoma.

## Segundo defecto, encontrado por las pruebas nuevas

La prueba `test_dos_renovaciones_simultaneas_no_pueden_ganar_las_dos` pasaba
aislada y **fallaba dentro de la suite**: las dos renovaciones devolvían 200.

No era una prueba inestable. Era el otro lado de la misma carrera, en el
servidor:

```python
session = db.get(AuthSession, sid)          # lee
if session.revoked_at is not None: ...      # comprueba
session.revoked_at = _now()                 # escribe
```

Entre leer y escribir hay una ventana. Bajo `READ COMMITTED` —el nivel por
defecto de PostgreSQL— dos transacciones pueden leer `revoked_at IS NULL`, ambas
marcarlo y ambas confirmar. Las dos prosperan.

**Por qué importa más que el 401.** La rotación de un solo uso existe para que
un refresh token robado se delate: si el atacante lo usa, el legítimo falla, o
al revés. Si las dos peticiones prosperan, esa detección desaparece y quedan
además sesiones vivas que ningún cierre revocará.

### Corrección

Bloqueo de fila antes de leer el estado, en `rotate_session`:

```python
session = db.execute(
    select(AuthSession).where(AuthSession.id == payload.get("sid")).with_for_update()
).scalars().first()
```

Una línea. La segunda transacción espera y encuentra la sesión ya revocada, así
que recibe 401. **Refuerza** la rotación en lugar de relajarla.

`with_for_update` es efectivo sobre PostgreSQL, que es el motor de producción
(`P21`). **Corrección del 2026-10-14 (`AUTH-ROTACION-SQLITE-HILOS`)**: la frase
original de este cierre —«inocuo en SQLite, que serializa las escrituras por su
cuenta»— era falsa para esta carrera: SQLite ignora `FOR UPDATE` y no retiene
ningún bloqueo entre leer y escribir, de modo que dos transacciones con
conexiones propias leían la sesión sin revocar y confirmaban las dos (5/5 con
las dos lecturas forzadas antes de la primera escritura). Desde entonces la
propiedad de la rotación la decide además un `UPDATE … WHERE revoked_at IS NULL`
cuyo `rowcount` distingue al ganador (1) del perdedor (0 → 401
`SESSION_REVOKED`), igual en los dos motores; el bloqueo de fila se conserva.
Delta: `specs/001-fundacion/spec001-auth-rotacion-sqlite-hilos-delta.md`.

Verificado con tres ejecuciones consecutivas de la suite de seguridad completa:
**28/28 estables**, sin intermitencia.

## Hallazgo de entorno: WebKit y la cookie `Secure`

Al ejecutar `route-crawl` en los tres navegadores, **WebKit fallaba en las 79
rutas** con `401 POST /auth/refresh`. Firefox y Chromium pasaban.

Causa: `KONTROL_COOKIE_SECURE` vale `true` por defecto, y **WebKit se niega a
guardar una cookie `Secure` desde un origen `http://`**. Chromium y Firefox hacen
una excepción con localhost; Safari no. Sin cookie no hay restauración, y toda
navegación queda sin sesión.

**No es un defecto de la aplicación**: en producción se sirve por HTTPS tras
Nginx y `Secure` es lo correcto —así queda en `compose.yaml`—. Es la pila local
la que debe declarar `KONTROL_COOKIE_SECURE=false`, como ya hacía
`qa/pg-migration-validation.sh`.

El problema es que la instrucción de arranque documentada en
`qa/local-backend-bootstrap.py` **omitía la variable**: el script la fijaba para
su propio proceso y luego indicaba levantar uvicorn sin ella. Corregido en su
docstring, con la explicación de por qué no es opcional.

Sin esta corrección, ninguna prueba E2E sobre WebKit podía autenticarse. La
detectó la comprobación de 401/403 añadida al recorrido; la comprobación
anterior, que solo leía la consola, nunca llegó a ejecutarse en WebKit.

Propietario del seguimiento: **054 · QA integral automatizado**.

## Seguridad preservada

| Garantía | Estado |
|---|---|
| Rotación del refresh token | **Reforzada** — ahora es de un solo uso también bajo concurrencia |
| Revocación de la sesión anterior | **Intacta** |
| Expiración de sesión | **Intacta** — no se tocó ningún TTL |
| Access token en memoria, refresh en cookie `HttpOnly` | **Intacto** |
| Semántica 401 / 403 / 404 | **Intacta** |
| Permisos y aislamiento multiempresa | **Intactos** |

**No se alargó ningún token** para tapar la carrera (§30). **No se debilitó la
rotación** (§29): el único cambio de servidor la hace más estricta, no menos.

## Tests nuevos

### Backend — `tests/test_auth_session_rotation.py` (8)

| Prueba | Qué fija |
|---|---|
| `test_la_renovacion_rota_el_token_y_revoca_el_anterior` | La rotación entrega un token distinto |
| `test_un_token_ya_usado_no_sirve_dos_veces` | La garantía de un solo uso |
| `test_sin_cookie_se_responde_401_y_no_se_crea_sesion` | El arranque en frío: 401 correcto, sin efectos |
| `test_un_token_manipulado_no_renueva` | Firma alterada |
| `test_tras_cerrar_sesion_el_token_deja_de_servir` | Revocación por logout |
| `test_dos_renovaciones_simultaneas_no_pueden_ganar_las_dos` | **El defecto**: exactamente una prospera |
| `test_una_renovacion_fallida_no_deja_sesiones_huerfanas` | La fuga de sesiones |
| `test_rotate_session_rechaza_un_token_de_sesion_revocada` | El servicio, sin pasar por HTTP |

### Frontend — `src/api/client.test.ts` (9)

| Prueba | Qué fija |
|---|---|
| `varias llamadas simultáneas comparten una sola renovación` | El mutex |
| `una renovación posterior sí vuelve a pedirse` | No se cachea de más |
| `sin manejador registrado no renueva ni falla` | Arranque sin contexto |
| `la restauración inicial y un 401 concurrente no se duplican` | **El defecto**, reproducido |
| `un 401 renueva y reintenta la petición una sola vez` | Reintento único |
| `si la renovación falla, el 401 se propaga sin reintentar` | Sin bucle |
| `un 401 del propio endpoint de renovación no dispara otra` | Exclusión anti-bucle |
| `el login rechazado no intenta renovar` | Exclusión de rutas de auth |
| `un 403 no renueva` | 403 ≠ sesión caducada |

## Route crawl

| Momento | Resultado |
|---|---|
| Antes | **FAIL** — 5 errores `401` en consola |
| Tras el arreglo de la carrera | 1 error restante (arranque en frío) |
| Tras corregir el alcance de la prueba | **PASS**, con comprobación de 401/403 añadida |

## Regresión

| Suite | Resultado |
|---|---|
| Backend completo · PostgreSQL 18.6 | **439 pasan · 8 omitidas · 0 fallan** (447) |
| Frontend `tsc -b` | **0 errores** |
| Frontend `eslint --max-warnings 0` | **limpio** |
| Frontend Vitest | **245 / 245** |
| `vite build` real | **OK** |
| OpenAPI global | **294 rutas** |
| Playwright global · Chromium + Firefox + WebKit | **198 / 198** |
| `route-crawl` en los tres navegadores | **3 / 3** |
| Suite de seguridad, 3 ejecuciones seguidas | **28 / 28 estables** |

Las 8 omitidas son las de conformidad S3, por no haber servicio real; se omiten
diciéndolo.

## Ajuste de tiempo en las pruebas documentales

Al ejecutar los tres navegadores, tres pruebas de `documents.spec.ts` agotaron
los 30 s por defecto **en WebKit**. No enmascaraban nada: cada una realiza dos
cargas reales analizadas por ClamAV, y la más lenta tarda **31,6 s** medidos.

Se les asignó `test.setTimeout(120_000)` con la razón escrita al lado, siguiendo
la convención que ya usaba `route-crawl.spec.ts`. No se añadió reintento, no se
relajó ninguna afirmación y no se excluyó ninguna prueba.

## Verdict

**`ROUTE_CRAWL_AUTH_REMEDIATION COMPLETE_100`**

Causa raíz identificada y corregida en las dos capas · segundo defecto de
concurrencia encontrado y cerrado · `route-crawl` PASS en Chromium, Firefox y
WebKit · regresión global con **0 fallos** · **0 nuevas fallas** · seguridad
**reforzada**, no debilitada.
