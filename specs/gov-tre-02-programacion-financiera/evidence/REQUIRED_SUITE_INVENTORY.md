# GOV-TRE-02 · inventario de suites exigidas

Certificado el 2026-11-05/06. Ejecución: Claude. Código y pruebas: DeepSeek, auditados por Claude.

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Rama única y reconciliación | `git fetch`; ramas remotas; HEAD == origin | PASS · solo `develop`; HEAD == origin/develop == `5e3d214` al empezar |
| 2 | Requisito de Gobierno | GOV-TRE-002 → spec; OD-TRE02-01..04 de la dueña | PASS · presupuesto, TRE-06, TRE-09 y contabilidad no son dependencia material; MATERIAL_BLOCKER = 0 |
| 3 | Normativa | Reglamento N.º 3 LOAFSP, G.O. 38.433, arts. 2, 3, 5, 24, 60.1, 61..64 | PASS (diseño). Rubros y subperíodos de la ONT quedan como deuda no bloqueante |
| 4 | RED primero | suites de TRE-02 sobre `5e3d214` | PASS (RED) · 67/67 fallan (`RED.md`) |
| 5 | BD dirigida | migración 0074 subir / bajar / subir en base nueva | PASS · cabeza única; 6 tablas, 9 disparadores, 3 permisos; `alembic check` sin diferencias `gov_cash` |
| 6 | Pruebas dirigidas | `tests/test_gov_tre02_{programa,versiones,cierre,seguridad,concurrencia}.py` | PASS · 70 pruebas. RB-01..07 (T020) viven en `test_gov_tre02_cierre.py` |
| 7 | Mutaciones de negocio | `mutar2.py` | PASS · 36 mutantes: 36 muertos, 0 equivalentes, 0 supervivientes (`MUTATIONS.md`) |
| 8 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261105t204437p3415099n3bc8a0`: 4463/0/18. Ver OBS-TRE02-FLAKE-01 |
| 9 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261105t194511p3153471n80dd9e`: 2792/0/1689 |
| 10 | vitest · tsc · eslint · build | `node …` | PASS · vitest 1235/1235 (121 ficheros; rc=0, 0 errores no controlados); tsc 0; eslint 0; build correcto |
| 11 | ruff · mypy | `ruff check .` · `mypy app` | PASS · ruff limpio; mypy 154 = línea base |
| 12 | OpenAPI | contraste con `5e3d214` | PASS · 13 rutas nuevas (16 operaciones), 0 retiradas. Solo cambian 4 esquemas de SoD y 2 GET de `/gobierno/sod`: el catálogo de procesos admite «Programación financiera» |
| 13 | E2E de TRE-02 ×3 y delta OBS-TRE01-E2E-01 | dentro de la regresión de Gobierno | PASS · PF-E2E-01..03 y TRE-E2E-04 en chromium, firefox y webkit |
| 14 | Regresión de Gobierno ×3, humo, base | `--orden qa/e2e-gobierno-regresion.sh` | PASS · `r20261106t105947p765315nc5a9de`: 180/180, humo 1/1, `scope_scan` 0, integridad 87 controles 0, sobre el árbol final |
| 15 | E2E tras T037 | `e2e/gobierno-hallazgos.spec.ts` ×3 navegadores | PASS · `r20261105t224220p26906nf9f2e1`: 3/3 |
| 16 | E2E canónica | `qa/e2e-run.py --con-analizador` | PASS · `r20261106t112314p822280n711463`: 448/448, 0 reintentos, limpieza LIMPIA. Ver OBS-TRE02-FLAKE-02 y T038 |
| 17 | Ficha de pantallas y campos | `TRE02_SCREEN_FORM_MATRIX.md`, `TRE02_FIELD_CONTRACT.md` | PASS |
| 18 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS |
| 19 | Humo UAT | HUMO-UAT-01 en la pila relanzada | ver `UAT_SMOKE.md` |

## Corrección fuera de TRE-02, dentro del ciclo

**T037.** `vitest` terminaba con rc=1 por 2 rechazos no capturados en `HallazgoPage` (CTL-06). Ya ocurría en `5e3d214`: la línea base «vitest 1180» de los ciclos anteriores no era verde en rc. Causa: `escribirDetalle` relanza y los botones descartan la promesa con `void`. Efecto para la usuaria: ninguno visible, el error ya se mostraba. Corrección de DeepSeek: los cinco manejadores capturan el relanzamiento, y tras un fallo el panel sigue abierto con su texto. La prueba HLP-03b da rechazo no capturado sobre el código anterior y pasa con el nuevo.

## T038 · cierre de OBS-TRE02-REG-01 (2026-11-06)

El primer cierre dio la regresión por buena con una corrida anterior a T037. Repetida sobre el árbol final dio 178, 179 y 179 de 180. La dueña retiró TRE-02 a IMPLEMENTED_NOT_CERTIFIED hasta certificar.

**Firma B, PF-E2E-02. Causa demostrada: defecto de sincronización de la prueba.** Cronología capturada: clic en «Nuevo programa» a 44995 ms, `fill` a 45020 ms sobre el campo Ejercicio del filtro de la lista, GET del filtro a 45025 ms, y la lista sustituida por el formulario a 45036 ms, con su valor inicial. La prueba no esperaba el formulario, y `/^Programa PF-/` no veía el año equivocado. Corrección: espera del encabezado, `toHaveValue` antes de enviar, encabezado exacto y programa único en la lista. PF-E2E-01 ya esperaba el encabezado. Mi hipótesis previa de un remontaje que borra datos del usuario era falsa, y no se tocó código de producto ni contexto compartido.

**Firma A, adjuntar en Firefox. Causa demostrada: cambios de red del anfitrión.** No era el vínculo: la petición que moría era `POST /documentos/{id}/versiones`, con `NS_ERROR_ABORT`.

| Experimento, Firefox | Muestras | Abortos |
|---|---|---|
| E2E sin registro en el proxy | 60 | 7 |
| E2E con registro síncrono en el proxy | 75 | 0 |
| E2E con `MOZ_LOG` | 30 | 0 |
| E2E con proxy keep-alive | 60 | 2 |
| Laboratorio normal | 1500 | **18** |
| Laboratorio simultáneo con `network.notify.changed=false` | 1500 | **0** |

Los dos laboratorios corrieron a la vez, bajo los mismos eventos de red. Los abortos caen en ráfagas simultáneas entre navegadores independientes, y el más rápido llegó a los 5009 ms: solo mueren peticiones que llevan más de 5 s esperando. Las direcciones IPv6 del Wi-Fi, con vigencia de 30 s, cambian continuamente; el arnés y `ip monitor` lo registran. Refutado: contención de suites, analizador y cierre de conexión del proxy. El registro en el proxy y `MOZ_LOG` parecían corregirlo por azar o por sincronización, sin explicación demostrada.

Corrección en el arnés: preferencia `network.notify.changed=false` en el proyecto Firefox. No se tocó producto ni aserción alguna.

**Certificación sobre el árbol final, sin reintentos ni instrumentación:**

| Suite | Corrida | Resultado |
|---|---|---|
| PF-E2E y documentos ×3 navegadores | `r20261106t104921p739961nef19fe` | 69/69 |
| Regresión de Gobierno ×3, humo, base | `r20261106t105947p765315nc5a9de` | 180/180, humo 1/1, `scope_scan` 0, integridad 87 controles 0 |
| Canónica | `r20261106t112314p822280n711463` | 448/448 |
| vitest · tsc · eslint · build | árbol final | 1235/1235 rc=0 · 0 · 0 · correcto |

PostgreSQL y SQLite no se repitieron: `resources/backend` y `resources/frontend/src` no cambian desde `ed1bf87`. Mutaciones no repetidas: T038 no cambia reglas de negocio, duplicados, máquina de estados, base ni dominio.

**Dos canónicas rojas sin causa separada.** `r20261106t100842p633076n747108` y `r20261106t102612p680474n3c59d1` dieron 430 aprobadas, 2 fallos y 16 sin correr, con timeouts de 30 s en pruebas que tardan de 3 a 12 s. Coincidieron con la carga media hasta 17, una suite ajena de otro proyecto y mi fixture de diagnóstico, que abría una página en cada prueba. Con el fixture retirado y sin suite ajena, la canónica pasó. No se separó cuánto aportó cada factor.

## Observaciones abiertas, sin causa demostrada

**OBS-TRE02-FLAKE-01.** `test_sg01_consulta_solo_lectura` falló una vez en PostgreSQL completo (`r20261105t184620p2587417n1e3bad`, 4462/1/18): `GET /gobierno/tesoreria/rubros` devolvió 403 a un usuario con `gobierno_caja:view`, tras dos GET de programas con 200 y las mismas dependencias. No se capturó el cuerpo del 403. No se repitió: 1 corrida completa posterior con sonda, 3 de la suite de seguridad y 30 de SG-01. **Causa desconocida.** Si reaparece, repetir con la sonda de 403 para obtener el código.

**OBS-TRE02-FLAKE-02.** La canónica `r20261105t224351p31008n5420ef` dio 431 aprobadas, 1 fallo y 16 sin correr: `n6-multicompany.spec.ts:104`, timeout de 20 s esperando `/organization/companies`. Sin relación aparente con T037 y la spec no cambia desde `d39f820`, pero eso no demuestra la causa. La corrida retiró sus trazas. La canónica siguiente fue 448/448. `--repeat-each` no sirve para medir esta spec: la primera pasada fue 13/13 y desde la segunda el arnés falla con `SESSION_REVOKED` para `uab`, así que los resultados de `r20261105t231246p112269n8bf7bf` y `r20261105t231434p117153nb3eba1` no prueban nada sobre el fallo. **Causa desconocida.**

**Corrida en paralelo, atribución retirada.** `r20261105t172333p1922596n680a6a` (PostgreSQL junto con la regresión) dio 4 fallos en `test_documents_security` y 1 en GOV3-E2E-01 firefox. Los 4 de documentos no se repitieron. El de firefox tiene la misma firma que OBS-TRE02-REG-01, que sí se repite sin suites en paralelo: la contención no lo explica.

**OBS-DOC-RED-01 (decisión de la dueña).** Un usuario real de Firefox con red inestable puede recibir «No fue posible adjuntar el documento» en una subida de 5 s o más. No es un defecto de KONTROL y el error es visible, pero la prueba ya no lo cubre, porque el arnés se aísla de esa condición.

**Chromium.** `ERR_NETWORK_CHANGED` se capturó una vez, al cargar un módulo. Chromium no ofrece preferencia equivalente, así que ese riesgo sigue en esta red.

## Limitaciones

- Las mutaciones no se repitieron tras T037: no toca reglas de TRE-02.
- Las filas GPC-070 y GPC-071 del backlog siguen con su texto de la retrospectiva, como los cierres anteriores.
