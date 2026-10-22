# Atribución del timeout de `e2e/licencia-revision.spec.ts:115` (2026-10-22)

**Firma.** En las corridas completas `r20261022t005439` y `r20261022t010314` la prueba falló así:
- duración 32,8 s y 32,3 s, con un límite de 30 s;
- `Test timeout of 30000ms exceeded`;
- después, `apiRequestContext.post: Request context disposed` en `POST /auth/login`.

En ninguna de las dos quedó registrado el intérprete: el arnés no lo anotaba (NOT_MEASURED).

## Hechos medidos sin corridas nuevas

| Medida | Valor |
|---|---|
| Histórico de la prueba (70 corridas verdes, 13→22 oct, `timeout-diagnosis/licencia-revision-historico.txt`) | 17,4–23,1 s; nunca cerca de 30 s |
| Suite E2E completa verde, 18–21 oct (22 corridas) | 263–309 s (mediana ≈ 271 s) |
| Ventana del fallo (00:21–01:10) | 294 s (con 4 pruebas sin ejecutar) → 342 s → 392 s → 391 s: **+26 % a +44 %**, y empeorando |
| Otra prueba en la misma ventana | `accessibility.spec.ts:60` (`/seguridad/usuarios`) superó los 30 s a las 00:21 en `locator.fill`: no usa ayudantes ni licencias |
| Anfitrión en la ventana (`host.csv` de la SQLite V0 `r20261022t003605`, 00:36–00:55) | swap usada 7,3–8,2 GB; MemAvailable 2,7–4,7 GB; paginación entrante de 35 000–61 000 páginas por muestra de 30 s; load15 4,36 al empezar; la suite tardó **1,68×** la mediana de 46 corridas |
| Reloj y red de las corridas fallidas | `desvio_s` 0,0, sin salto; `red_cambio` false |

## Experimentos dirigidos (una pregunta por corrida; ninguna repetición para conseguir verde)

Las tres corridas tienen la misma forma:
- `qa/e2e-run.py --con-analizador -- e2e/licencia-revision.spec.ts --no-deps --trace on`;
- anfitrión recién arrancado, swap 0, ≈ 8,2 GB disponibles;
- PostgreSQL HEALTHY (2–3 ms); ClamAV 1.4.3;
- `boottime − monotonic` constante en 98,4 s (sin suspensión durante las corridas), NTP sincronizado.

| Corrida | Pregunta | Árbol | Intérprete (arnés = migración de la autoridad) | Resultado | Total | En API | Huecos síncronos | Login |
|---|---|---|---|---|---|---|---|---|
| D1 | ¿Aparece la firma sin el ciclo? | `git archive d20da5b` (aislado) | V0 3.11.16, por construcción (`.venv/bin/alembic`) | ✓ | 17,3 s | 0,77 s | 16,6 s | 49–58 ms |
| D2 | ¿Aparece con el cambio del ciclo, en el mismo entorno? | árbol de trabajo | V0 3.11.16 · paridad 1 (**medida**) | ✓ | 17,5 s | 0,77 s | 16,7 s | 50–59 ms |
| D3 | ¿Hay diferencia entre V0 y V5? | árbol de trabajo | V5 CPython 3.13.16 · `exe_real` = `ld-linux` del rootfs · paridad 1 (**medida**) | ✓ | 17,3 s | 0,79 s | 16,5 s | 50–58 ms |

Desglose de cada traza en `timeout-diagnosis/D{1,2,3}-traza.json` y telemetría en `timeout-diagnosis/telemetria.jsonl`.

## Lectura

- **El 95 % de la prueba no es API.** Unos 14 `execFileSync` de ayudantes Python, de ≈ 1,1–1,35 s cada uno, bloquean el bucle de Node: `licencia_firmada.py`, `autoridad_central.py emitir` y `rol_sin_permiso.py`. Las llamadas a la API suman 0,8 s, y el login, 50–60 ms. El coste está en arrancar el intérprete y cargar los módulos, lo que más sufre con la presión de memoria y la paginación.
- **`Request context disposed`** es **CONSEQUENCE_OF_GLOBAL_TIMEOUT**. Playwright cierra el contexto al vencer los 30 s, y el login en curso es la víctima; no es un fallo independiente.
- **El ciclo no es causal:**
  - D1 y D2 son idénticos en duración y perfil;
  - en V0 el cambio de T3 mantiene el mismo intérprete (V0), y D3 no muestra efecto de V5;
  - los ayudantes de la prueba corren en V0 en los dos modos (ver la deuda nueva E2E-SPECS-PYTHON-HELPERS-VENV-FIXED).
- **El analizador no es causal:** la prueba no sube documentos, y el proyecto `licencia-revision` corre después de `chromium`.
- **Backend y base no son causales:** API 0,8 s de 17 s y PostgreSQL de 2–3 ms.
- **ROOT_CAUSE_CLASS = ENVIRONMENT:**
  - degradación medida del anfitrión (swap y paginación) que ralentizó la suite completa un 26–44 % y llevó por encima de 30 s a dos pruebas distintas;
  - en el entorno sano, el mismo código (base, árbol, V0 y V5) da 17,3–17,5 s.
- **Factor que contribuye** (diseño de la prueba, no causa): la prueba gasta ≈ 57 % de su presupuesto en arrancar procesos Python síncronos, y por eso tolera solo ≈ 1,7× de degradación.
- **DERIVED:** que la presión de memoria ralentiza el arranque de los ayudantes se apoya en la correlación medida y en el mecanismo de los huecos síncronos. **NOT_MEASURED:** no se indujo presión de memoria a voluntad para reproducir el fallo.

**Deuda nueva, no absorbida:** **E2E-LICENSE-REVISION-ENVIRONMENT-LATENCY** (dueña 054; prueba dueña 010). No cambia ningún timeout ni ninguna prueba (OD-CERT-13).
