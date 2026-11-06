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
| 14 | Regresión de Gobierno ×3, humo, base | `--orden qa/e2e-gobierno-regresion.sh` | **FAIL intermitente sobre el árbol final** · ver la corrección abajo. `r20261105t200116p3284205n4d596a` (antes de T037): 180/180, humo 1/1, `scope_scan` 0, integridad 87 controles 0 |
| 15 | E2E tras T037 | `e2e/gobierno-hallazgos.spec.ts` ×3 navegadores | PASS · `r20261105t224220p26906nf9f2e1`: 3/3 |
| 16 | E2E canónica | `qa/e2e-run.py --con-analizador` | PASS · `r20261105t225831p71421n216586`: 448/448, 0 reintentos, limpieza LIMPIA. Ver OBS-TRE02-FLAKE-02 |
| 17 | Ficha de pantallas y campos | `TRE02_SCREEN_FORM_MATRIX.md`, `TRE02_FIELD_CONTRACT.md` | PASS |
| 18 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS |
| 19 | Humo UAT | HUMO-UAT-01 en la pila relanzada | ver `UAT_SMOKE.md` |

## Corrección fuera de TRE-02, dentro del ciclo

**T037.** `vitest` terminaba con rc=1 por 2 rechazos no capturados en `HallazgoPage` (CTL-06). Ya ocurría en `5e3d214`: la línea base «vitest 1180» de los ciclos anteriores no era verde en rc. Causa: `escribirDetalle` relanza y los botones descartan la promesa con `void`. Efecto para la usuaria: ninguno visible, el error ya se mostraba. Corrección de DeepSeek: los cinco manejadores capturan el relanzamiento, y tras un fallo el panel sigue abierto con su texto. La prueba HLP-03b da rechazo no capturado sobre el código anterior y pasa con el nuevo.

## Corrección del cierre (2026-11-06): la regresión no está verde sobre el árbol final

El primer cierre dio la regresión por buena con una corrida anterior a T037. Repetida sobre `d5cfec1`:

| Corrida | Alcance | Resultado | Fallos |
|---|---|---|---|
| `r20261105t233825p130457n6dfde6` | regresión ×3 | 178/180 | DOC2-E2E-01 y GOV-E2E-01, firefox |
| `r20261106t000351p187642neab7f9` | regresión ×3 | 179/180 | GOV-E2E-01, firefox |
| `r20261106t002803p244878nf55bb5` | chromium y firefox | 120/120 | ninguno |
| `r20261106t004354p280943n33acc0` | regresión ×3 | 179/180 | PF-E2E-02, chromium |

En las tres regresiones: humo 1/1, `scope_scan` 0, integridad 0 violaciones.

**OBS-TRE02-REG-01 (abierta, bloquea el criterio §48).** Dos firmas:
- Adjuntar PDF en firefox: timeout de 60 s esperando `POST /documentos/{id}/vinculos`. No es el analizador: tarda 6 s, y 7 s con cuatro en paralelo.
- PF-E2E-02: el segundo registro, que debía rechazarse por duplicado, abrió la ficha PF-2028-VES.

**Hipótesis no demostrada:** en PF-E2E-02 el primer `fill` del ejercicio se pierde, el primer programa nace con el año por defecto (la prueba solo comprueba `/^Programa PF-/`) y el segundo no es duplicado. Una pérdida del estado del formulario explicaría también el adjunto, pero no se ha encontrado qué la causa. La renovación de token no pone `isAuthenticated` a falso. El índice único de la base impide dos programas iguales, así que no hay indicio de duplicado real.

**Mutaciones:** no se repitieron tras T037, que no toca reglas de TRE-02.

## Observaciones abiertas, sin causa demostrada

**OBS-TRE02-FLAKE-01.** `test_sg01_consulta_solo_lectura` falló una vez en PostgreSQL completo (`r20261105t184620p2587417n1e3bad`, 4462/1/18): `GET /gobierno/tesoreria/rubros` devolvió 403 a un usuario con `gobierno_caja:view`, tras dos GET de programas con 200 y las mismas dependencias. No se capturó el cuerpo del 403. No se repitió: 1 corrida completa posterior con sonda, 3 de la suite de seguridad y 30 de SG-01. **Causa desconocida.** Si reaparece, repetir con la sonda de 403 para obtener el código.

**OBS-TRE02-FLAKE-02.** La canónica `r20261105t224351p31008n5420ef` dio 431 aprobadas, 1 fallo y 16 sin correr: `n6-multicompany.spec.ts:104`, timeout de 20 s esperando `/organization/companies`. Sin relación aparente con T037 y la spec no cambia desde `d39f820`, pero eso no demuestra la causa. La corrida retiró sus trazas. La canónica siguiente fue 448/448. `--repeat-each` no sirve para medir esta spec: la primera pasada fue 13/13 y desde la segunda el arnés falla con `SESSION_REVOKED` para `uab`, así que los resultados de `r20261105t231246p112269n8bf7bf` y `r20261105t231434p117153nb3eba1` no prueban nada sobre el fallo. **Causa desconocida.**

**Corrida en paralelo, atribución retirada.** `r20261105t172333p1922596n680a6a` (PostgreSQL junto con la regresión) dio 4 fallos en `test_documents_security` y 1 en GOV3-E2E-01 firefox. Los 4 de documentos no se repitieron. El de firefox tiene la misma firma que OBS-TRE02-REG-01, que sí se repite sin suites en paralelo: la contención no lo explica.

## Limitaciones

- Las mutaciones no se repitieron tras T037: no toca reglas de TRE-02.
- Las filas GPC-070 y GPC-071 del backlog siguen con su texto de la retrospectiva, como los cierres anteriores.
