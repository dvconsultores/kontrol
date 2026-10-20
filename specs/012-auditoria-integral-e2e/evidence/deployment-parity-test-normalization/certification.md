# Certificación — DEPLOYMENT-PARITY-TEST-INCOMPATIBILITIES

**Árbol certificado:** HEAD `41c90f3` + `tests/test_openapi_security.py` + `tests/test_motor_para_hilos.py` +
`tests/test_license_middleware_event_loop.py`.
- Producto sin cambio: `app/` y `tests/conftest.py` sin diff.
- Todo con el analizador real.

## V0 (canónico vigente, `.venv`, CPython 3.11.16)
| Puerta | Corrida | Resultado |
|---|---|---|
| SQLite #1 | `r20261020t001223p910958n82f258` | rc 0 · **1885/0/1056** · 711,4 s · NORMAL |
| SQLite #2 | `r20261020t002429p993009n498d5c` | rc 0 · **1885/0/1056** · 715,5 s · NORMAL |
| PostgreSQL | `r20261020t003638p1075172nfa040e` | rc 0 · **2915/0/26** · 1673,2 s · NORMAL |
| E2E | `r20261020t013736p1693134n5a690e` | rc 0 · **284/0/0** · LIMPIA · protegidas sin cambio · 0 QueuePool · 0 errores no controlados · 0 respuestas 500 |
| OpenAPI | — | 544/533/11 |

## V2 (paridad de despliegue: CPython 3.13.15 + `pip install -r requirements.txt` + python-magic 0.4.27)
| Puerta | Corrida | Resultado |
|---|---|---|
| SQLite | `r20261020t010446p1352796nb86179` | rc 0 · **1885/0/1056** · 604,7 s · NORMAL (antes 1881/4/1056) |
| PostgreSQL | `r20261020t011504p1432748n2285d4` | rc 0 · **2915/0/26** · 1328,3 s · NORMAL (antes 2913/2/26) |
| E2E | `r20261020t014230p1722048n5040c7` | rc 0 · **284/0/0** · LIMPIA · protegidas sin cambio · 0 QueuePool · 0 errores no controlados · 0 respuestas 500 |
| OpenAPI | — | 544/533/11 · las mismas 4 diferencias generadas por el framework que en el diagnóstico · OPENAPI_CONTRACT_DRIFT = 0 |

**Totales:** los recuentos no cambian, porque no se añadieron pruebas, solo se normalizaron.

**E2E y equipo:**

| | Precheck | Muestreo de 1 Hz |
|---|---|---|
| V0 | 4,6 GB disponibles, swap 4,1 GB | memoria mínima 663 MB, swap máxima 9,2 GB, hasta 5 clamscan |
| V2 | 6,9 GB disponibles, swap 7,6 GB | memoria mínima 680 MB, swap máxima 10,3 GB, hasta 5 clamscan |

**Huecos de paridad que se mantienen (no absorbidos):**
- MIGRATION_TESTS_EXECUTED_WITH_V2 = 0: los 10 ficheros de TEST-MIGRACIONES-VENV-FIJO usan `.venv/bin/alembic`.
- E2E_BACKEND_INTERPRETER = V2 (`sys.executable`).
- E2E_MIGRATION_INTERPRETER: V2 para la base de la corrida y V0 para la autoridad central (`qa/e2e_corrida.py:393`).
- RELEASE_DEPLOYMENT_PARITY_CERTIFIED = 0.
