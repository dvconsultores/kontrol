# Corridas de la orden canónica `python3 qa/certificar-release.py` (2026-10-24)

Manifiestos completos y saneados en `qa/certificaciones/<run_id>/` (fuera de Git). Una sola orden; sin pasos manuales; ninguna etapa reintentada.

| Corrida | RC | Veredicto | Primera etapa no PASS | Causa (atribuida) | Residuos |
|---|---|---|---|---|---|
| `cert_20261024T014731Z_918521` | 1 | CERTIFICATION_FAILURE | 80 (SQLite 1964/1/1070) | `test_o12_04` (prueba preexistente) dependía de que el intérprete no viviera bajo el HOME real; V6C en `~/.cache/…` → corregida en T5d (la versión de `HEAD` falla con un intérprete bajo el HOME real; la corregida pasa) | CLEAN |
| `cert_20261024T020828Z_5501c1` | 1 | CERTIFICATION_FAILURE | 80 (SQLite 1985/1/1070) | AIC-01 (prueba estructural preexistente) rechazó dos literales `.venv` en las pruebas nuevas → corregidas en T5k | CLEAN |
| `cert_20261024T022901Z_a9437e` | 3 | INVALID_ENVIRONMENT | 90 | anfitrión degradado durante la E2E: +577 068 páginas en swap, +1,86 GB de swap. La E2E dio 284/0/0. El muestreo reveló además que `app.modules.scheduler` (lanzado por el ayudante E2E con V6C) estaba clasificado como producto → T4c | CLEAN |
| `cert_20261024T031946Z_080982` | 3 | INVALID_ENVIRONMENT | 90 | anfitrión degradado durante la E2E: +363 778 páginas en swap (umbral 200 000), +0,90 GB de swap (umbral 1 GiB). La E2E dio 284/0/0 | CLEAN |
| `cert_20261024T104651Z_370530` | 3 | INVALID_ENVIRONMENT | 80 (SQLite 2042/0/1070, rc 0) | salto de reloj durante la suite: 713,7 s monotónicos frente a 4128,6 s de pared (desvío 3414,9 s); la corrida duró 74,5 min de pared para ~18 min de trabajo: suspensión del equipo (DERIVED; el journal no registra el evento). Previo: MemAvailable 7207 MB, swap 3034 MB, load 1,02; Opera abierto (~3,7 GB). Defecto propio detectado: el manifiesto quedó con `ENVIRONMENT_VALIDITY = VALID` → T1b | CLEAN |
| `cert_20261024T140249Z_078af5` | 3 | INVALID_ENVIRONMENT | 90 | MEMORY_PRESSURE / SWAP_ACTIVITY: durante la E2E +1 092 373 páginas escritas en swap y +2,95 GB de swap (umbrales 200 000 y 1 GiB). Sin suspensión: inhibidor `systemd-inhibit` propio (PID 16041, `sleep:idle:handle-lid-switch`, modo block) activo toda la corrida y `CLOCK_BOOTTIME−CLOCK_MONOTONIC` = 0 antes y después; NTP sincronizado. Equipo recién reiniciado (swap 0 al empezar); MemAvailable 7092 MB al empezar; Opera abierto (~3,1 GB). 0–80 PASS: SQLite 2043/0/1070, PostgreSQL 3087/0/26; la E2E dio 284/0/0 con procedencia correcta (0 fuera de lugar) | CLEAN |
| `cert_20261024T161414Z_09f664` | 70 | INTERRUPTED | 90 | INTERRUPTION (HOST_SHUTDOWN): a los 207,7 s de la E2E la etapa recibió SIGTERM; el journal del arranque anterior registra `endSessionDialog` a las 17:14:56Z y el apagado ordenado de la sesión (17:15:03Z); el equipo volvió a arrancar a las 17:45:07Z con otro núcleo (6.12.113). El inhibidor propio bloquea la suspensión, no el apagado. 0–80 PASS: SQLite 2043/0/1070, PostgreSQL 3087/0/26. 120 no pudo auditar (el PostgreSQL de QA ya había caído con la sesión) | Tras el reinicio: clúster QA en tmpfs desaparecido con sus bases, puertos 8000/5173/8010/55432 libres, 0 procesos y 0 inhibidores KONTROL → sin residuos |
| `cert_20261024T174958Z_ba4752` | 3 | INVALID_ENVIRONMENT | 90 | MEMORY_PRESSURE / SWAP_ACTIVITY: suite E2E 284 passed (5,6 min), pero la validez posterior midió +1 037 103 páginas escritas en swap y +2 598 000 kB de swap (umbrales 200 000 y 1 GiB); suspensión 0 s con el inhibidor propio (PID 15860, retirado por PID; 0 inhibidores KONTROL al terminar); NTP sincronizado. Al empezar: MemAvailable 6847 MB, swap 0, load1 11,5 (equipo recién arrancado; la etapa 10 esperó a 3 muestras sanas). OTHER_WORKLOAD_PRESENT = 1, solo observado. 0–80 PASS: SQLite 2043/0/1070, PostgreSQL 3087/0/26; 100/110 NOT_RUN | CLEAN (etapa 120) |

## Última corrida (`cert_20261024T031946Z_080982`), con el módulo y las pruebas finales
- 00 PREFLIGHT PASS · 10 ENVIRONMENT_VALIDITY PASS (4 muestras, la primera no sana; VALID) · 20 locks regenerados idénticos · 30 V6R reconstruido por digest (`sha256:70729b46…`, amd64 `sha256:8fb4cfa1…`) · 40 V6R: CPython 3.13.16, freeze = lock (38), `pip check`, humo PASS (119 módulos, OpenAPI 544/533/11, 0 herramientas) · 50 V6C 49 · 60 subconjunto 38/38 (`RUNTIME_SUBSET_EQUAL = 1`) · 70 PostgreSQL 16.2, `ktest` existente, `btree_gist`, 0 bases y 0 esquemas previos.
- 80 BACKEND PASS: SQLite V6C **2041/0/1070** y PostgreSQL V6C **3085/0/26** (IN_PROCESS_CERTIFICATION_OVERLAY).
- 90 E2E: suite **284/0/0** (293,3 s), RUNTIME_SEPARADO, herramientas de producto ∅, `paridad_runtime` 1, paridad arnés = migración de la autoridad 1, limpieza LIMPIA, bases protegidas sin cambios; procedencia `/proc`: 115 registros, backend y autoridad en V6R, 113 ayudantes en V6C (incluidos los 7 ticks del planificador), 0 fuera de lugar. **Veredicto de la etapa: INVALID_ENVIRONMENT** por la validez posterior (incremento de páginas escritas en swap 363 778 > 200 000).
- 100 OPENAPI y 110 SECURITY: NOT_RUN en esta corrida (corte por el primer no-PASS); medidas sobre V6R/V6C reales en T4a: deriva 0 frente a la referencia y pip-audit 2.10.1 PyPI 0 · OSV 0 en los dos locks.
- 120 residuos CLEAN · 130 manifiesto con `CANONICAL_RUN_INPUT_HASH = sha256:80b33054145c01fdbe22f5cd05414e610052f300002f1fdb23da93c2ff6bf664` · 140 RC 3.

## Bloqueo
**BLOCKED BY ENVIRONMENT** (no de producto ni de la orden): en dos corridas seguidas la memoria del anfitrión no sostuvo la E2E sin paginar (aplicaciones de escritorio abiertas: Opera ≈ 2,8 GB y VS Code ≈ 0,9 GB residentes; swap usada al empezar ≈ 3,3 GB). El umbral de validez posterior no se toca para obtener verde. Desbloqueo: liberar memoria del equipo y volver a lanzar la misma orden.

## Intento 7 — no ejecutado (2026-10-24): HOST_PRECONDITION_NOT_MET
Comprobación previa (`ps -eo pid,rss,comm --sort=-rss`): Opera en marcha (22 procesos, ≈ 5,2 GB RSS sumado), además de VS Code (≈ 3,0 GB) y Chrome (≈ 1,5 GB); MemAvailable 6981 MB; swap usada 2934 MB; load 1,64/1,88/2,31; NTP sincronizado; sin suspensión acumulada. La precondición local de la estación (Opera cerrado durante toda la corrida) no se cumple: no se arrancó el inhibidor ni la orden canónica. Ningún cambio de código ni de umbrales.

## Intento 8 — no ejecutado (2026-10-24): HOST_PRECONDITION_NOT_MET
Opera sigue en marcha: 20 procesos (≈ 5,0 GB RSS sumado), con los mismos PID que en el intento 7 (p. ej. 9958, 10359, 13816), es decir, el proceso de Opera no se cerró (posiblemente sigue en segundo plano tras cerrar las ventanas). VS Code (28 procesos, ≈ 3,0 GB) y Chrome (16, ≈ 1,8 GB) también abiertos. No se arrancó el inhibidor ni la orden. Ningún cambio.

## Intento 9 — no ejecutado (2026-10-24): HOST_PRECONDITION_NOT_MET
Opera sigue en marcha: 24 procesos; proceso principal PID 9958 (el mismo de los intentos 7 y 8). Además, un `pytest` ajeno a esta corrida (PID 413125) en ejecución. No se arrancó el inhibidor ni la orden. Ningún cambio.


## Política multiproyecto (dueña, 2026-10-24)
Los intentos 7–9 «no ejecutados» quedan superados: la dueña retiró como precondición cerrar Opera, Chrome, VS Code o detener otros proyectos (PROJECT_ISOLATION_REQUIRED = 1; solo se tocan recursos con propiedad KONTROL probada; la única autoridad del entorno es la puerta de la orden canónica; otras cargas se registran como OTHER_WORKLOAD_PRESENT, sin culparlas).

## Clasificación tras la octava corrida
Cuatro corridas (3, 4, 6, 8) con el producto en verde y la E2E paginando por encima del umbral, con y sin aplicaciones de escritorio cerradas, con y sin inhibidor: **CERTIFICATION_HOST_CAPACITY_INSUFFICIENT = 1**. Sin cambios de umbrales, perfil E2E ni código. MATERIAL_OQ OD-CERT-27 para la dueña: A (equipo dedicado o CI, perfil sin cambios; recomendada) o B (delta del perfil de QA con menos concurrencia de navegadores).

## OD-CERT-27 = A (2026-10-24)
La estación de desarrollo no vuelve a usarse para la certificación oficial. No se ejecutó ninguna corrida canónica nueva. La corrida de diagnóstico `r20261024t185614p424055n541fd2` (`qa/e2e-run.py --con-analizador`, 284 passed, RC 0) sirvió solo para medir la huella de memoria de la E2E (`e2e-memory-footprint-diagnostic.json`); no es una certificación. Estado: BLOCKED_BY_INFRASTRUCTURE (`certification-host-requirements.md`).

## OD-CERT-28 = 28-B (2026-10-25)
No se ejecutó ninguna corrida oficial en la estación. Diagnósticos de la orden canónica en `--solo-preflight`, que no certifican:
- `cert_20261025T030458Z_b7175b`: RC 70, la política rechazó `GIT_EDITOR`. Era un falso positivo del prefijo `GIT_`, corregido en TP-2-c1.
- `cert_20261025T031439Z_08f08b`: RC 4, árbol `a97220d6…` ligado al hash v2.

Certificación oficial pendiente de un anfitrión dedicado.
- `cert_20261025T041939Z_e2a887`: RC 4 con el árbol final. `CERTIFICATION_INPUT_TREE_HASH = 77126ca1663b924e3b098ef5d2d255e09346fd00`; `CANONICAL_RUN_INPUT_HASH = sha256:af206871a5aefd1df3d4e377816df613220bb3273debce751af52affc2b700db` (v2); 0 variables prohibidas. Es el árbol que el anfitrión dedicado debe reproducir (SOURCE_WORKTREE_CONTENT_MATCH). Delta de código (12 rutas, sin evidencia ni `.md` de specs): `sha256:15516cf9af4a39920283a4782eb6812fff75124f7a29f32eefa2d132d99bc7bd`.
