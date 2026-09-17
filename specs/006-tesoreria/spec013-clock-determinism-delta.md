# SPEC 013 · DELTA DIRIGIDO CLOCK-013 — LAS PRUEBAS FINANCIERAS DEJAN DE DEPENDER DEL RELOJ

> Reconvergencia dirigida dentro de la Spec 013, ya `COMPLETE / CONVERGED`. No cambia
> ninguna regla de negocio: ni la vigencia, ni la selección de tasa, ni la procedencia,
> ni los contratos monetarios que cerraron FLOAT-038-A/B/C.

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` | `e43cf48` / `e43cf48` — coinciden |
| `COMMITS_AFTER_E43CF48` | **0** |
| `ACTUAL_BRANCH` | `develop` |
| `WORKTREE_STATE` | un fichero sin confirmar: `KONTROL_MASTER_COMPLETENESS_AUDIT.md`, de la auditoría previa, ajeno a este delta: no se borra, no se mueve, no se confirma |
| PostgreSQL | 16.2 · objetivo 18.6 → `ENVIRONMENT_BASELINE_DEVIATION` |

El clúster temporal de QA se reinicializó al rotar `/tmp`; se reconstruyó con la receta
documentada (`qa/pg-provision.sh`). `EXTERNAL_ENVIRONMENT`, sin impacto en el delta.

## 1. Dueña canónica

**SPEC 013 — Maestros financieros** (`specs/006-tesoreria`, artefactos `spec013-*`). El
fichero afectado, `tests/test_spec013_financial_masters.py`, es suyo. Apoyo:
`ADR-D0-001`, que fija la autoridad temporal del servidor. `OWNER_CONFLICT = 0`.

## 2. La deuda, recontada físicamente

| Fuente de reloj | Apariciones en `tests/test_spec013_financial_masters.py` |
|---|---:|
| `date.today()` | **57** |
| `datetime.today()`, `datetime.now()`, `utcnow()`, `time.time()` | **0** |

57 usos repartidos en **42 símbolos**. No hay otro fichero de pruebas de la 013.

## 3. La autoridad temporal del módulo

`ADR-D0-001` fija el **`UTC`** como zona del servidor: «los documentos fiscales se
comparan en instante absoluto; la zona local es presentación». El producto de tasas es
coherente con eso:

- `_momento_registro(None)` → `datetime.now(UTC)`;
- una fecha suelta `D` **empieza** a regir en `D 00:00 UTC`;
- `_momento_consulta(D)` mira hasta `D 23:59:59.999999 UTC`.

La prueba, en cambio, construía sus fechas con `date.today()`, que es el **día civil del
proceso**. Dos autoridades distintas en la misma prueba.

## 4. Reproducción del defecto — antes de tocar nada

En el momento de ejecutar, `UTC = 2026-09-17 01:24` y `America/Caracas = 2026-09-16 21:24`:
**días civiles distintos**. Mismo código, mismos datos, misma intención de negocio:

| Entorno | Resultado |
|---|---|
| `TZ=UTC` | **58 pasadas, 0 fallos** |
| `TZ=America/Caracas` | **1 fallo**: `test_la_tasa_de_hoy_sirve_para_una_operacion_de_hoy` |

```
app.core.errors.ConflictError: No hay tasa registrada para ese par en esa fecha.
rates.py:660  ·  code=MISSING_RATE
```

**Por qué.** Esa prueba registra la tasa en un **instante UTC**
(`effective_at=datetime.now(UTC)` → `2026-09-17T01:24Z`) y la consulta por **fecha civil
local** (`effective_at=date.today()` → `2026-09-16` en Caracas), que el producto mira
hasta `2026-09-16T23:59:59.999999Z`: **una hora y media antes** de que la tasa empiece a
regir. El producto responde correctamente que no hay tasa; la prueba se había preguntado
por otro día.

Evidencia: `evidence/clock-013/reproduccion-pre-fix.txt`.

### La dirección contraria

El historial registró fallos entre las 00:00 y las 02:00 CEST, cuando el día local va
**por delante** del de UTC. Esa dirección no es reproducible por zona horaria a la hora
de esta ejecución —a las 01:24 UTC ninguna zona del mundo está ya en el día siguiente—,
y se declara así en vez de fingir una reproducción. El arreglo elimina la dependencia en
**ambas** direcciones por construcción: después no queda ningún día civil local en el
fichero.

## 5. Inventario del reloj, clasificado

| Clase | Nº | Qué es |
|---|---:|---|
| `TEST_REFERENCE_DATE` | **47** | Fecha de conveniencia para sembrar observaciones, fuentes y duplicados |
| `EXPIRY_WINDOW` | **4** | `hoy−1`, `hoy+1`, `hoy−90`: ventanas relativas de vigencia y caducidad |
| `BUSINESS_DATE` | **6** | Consultas por fecha que ejercitan la ventana de día del producto |
| `EFFECTIVE_DATE` | — | La vigencia la fija el propio producto; la prueba solo la alimenta |
| `AUDIT_TIMESTAMP` | **0** | Los sellos de auditoría los pone el producto en `datetime.now(UTC)` |
| `UNKNOWN` | **0** | — |

Diez pruebas consultan **sin fecha explícita**, de modo que usan el «ahora» del propio
producto. Ese camino **se conserva**: una tasa vigente en una fecha pasada sigue siendo
la vigente ahora, así que esas pruebas siguen ejercitando la resolución por instante
actual sin depender de qué día sea hoy.

## 6. El producto no se toca

`app/modules/treasury/rates.py` usa `datetime.now(UTC)` en diez sitios y `date.today()`
en uno (`active_policy`, la vigencia de la política). Sobre un servidor en UTC —el
despliegue documentado— ambas cosas significan lo mismo. **No se modifica ningún fichero
de producto**, y no se ha encontrado un `PRODUCT_CLOCK_DEFECT` que exija decisión: lo que
fallaba era la prueba, que se preguntaba por un día distinto del que había escrito.

Queda **declarada como observación, no absorbida**: si algún día KONTROL se desplegara
sobre un servidor que no esté en UTC, `active_policy` usaría el día civil local mientras
la resolución de tasas usa el instante UTC. Hoy no ocurre y no se corrige aquí.

## 7. `/speckit.specify`

| ID | Requisito | Prioridad |
|---|---|---|
| FR-013-041 | Las pruebas de la 013 no dependen del **día civil** en que se ejecutan | P0 |
| FR-013-042 | No requieren `TZ=UTC` para ser deterministas | P0 |
| FR-013-043 | Las relaciones temporales se construyen desde una **referencia explícita**, no desde el reloj | P0 |
| FR-013-044 | La corrección no cambia vigencia, selección de tasa, caducidad ni procedencia | P0 |
| FR-013-045 | Donde el producto consulta su propia fecha actual, la prueba **sigue ejercitando esa ruta** en vez de eliminarla | P0 |
| FR-013-046 | La suite da el **mismo resultado** bajo UTC, `America/Caracas` y una tercera zona con día civil distinto | P0 |
| FR-013-047 | Existe una prueba que **detecta la reintroducción** de la dependencia del reloj | P0 |
| FR-013-048 | No se introducen esperas, reintentos, tolerancias ni marcas de omisión | P0 |
| FR-013-049 | La referencia temporal es explícita y no se convierte en una fecha global implícita | P1 |
| FR-013-050 | La 013 conserva su comportamiento funcional y su regresión previa | P0 |

## 8. `/speckit.clarify`

| # | Pregunta | Resolución | Material |
|---|---|---|---|
| 1 | Nº real de `date.today()` | **57**, contadas | No |
| 2 | Nº real de pruebas vulnerables | 1 reproducible ahora; **42 símbolos** construyen fechas con el reloj y son vulnerables por diseño según la hora | No |
| 3 | Cuáles son solo fixture | 47 usos | No |
| 4 | Cuáles prueban fecha de negocio | 6 usos, 10 pruebas consultan sin fecha | No |
| 5 | Autoridad de zona de la 013 | **UTC**, `ADR-D0-001` | No |
| 6 | ¿Hay ayudante de reloj canónico? | No existe ninguno en el repositorio | No |
| 7 | ¿Hay librería de tiempo congelado? | No, y no se añade | No |
| 8 | ¿Se usa `CURRENT_DATE` de PostgreSQL? | No en este dominio | No |
| 9 | ¿`date.today()` en el producto? | Sí, `active_policy`; coherente sobre servidor UTC (§6) | No |
| 10 | ¿`datetime.now()` sin zona en el producto? | No: siempre `datetime.now(UTC)` | No |
| 11 | ¿Pueden discrepar base y Python? | No: el clúster se inicializa en UTC (`ADR-D0-001`) | No |
| 12 | ¿Participa el frontend? | No | No |
| 13 | Prueba que falla históricamente | `test_la_tasa_de_hoy_sirve_para_una_operacion_de_hoy` y las de ventana | No |
| 14 | Relación con `TZ=UTC` | Era el parche que ocultaba la deuda; deja de hacer falta | No |
| 15 | Zona del entorno de ejecución | La del sistema; ya no importa | No |
| 16 | Frontera de medianoche | Deja de existir en el fichero: no queda día civil local | No |
| 17 | Horario de verano | Irrelevante: `America/Caracas` no lo aplica y no se audita aquí | No |
| 18 | Alcance de la referencia | Un solo fichero, explícita en su cabecera | No |
| 19 | ¿Se congela el tiempo globalmente? | **No**: nada de parchear `datetime` ni `date` | No |
| 20 | Ficheros de producto esperados | **0** | No |

**MATERIAL OQ = 0 · UNKNOWN = 0.**

## 9. `/speckit.plan`

`W01` checkpoint · `W02` inventario de relojes · `W03` recuento y clasificación ·
`W04` reproducción bajo zonas distintas · `W05` negocio frente a fixture ·
`W06` abstracciones existentes · `W07` diseño de la referencia ·
`W08` refactor de las pruebas afectadas · `W09` fecha de negocio ·
`W10` fronteras de vigencia · `W11` UTC · `W12` `America/Caracas` ·
`W13` tercera zona con día opuesto · `W14` frontera de medianoche ·
`W15` mutaciones · `W16` regresión dirigida de la 013 · `W17` regresión financiera ·
`W18` regresión completa · `W19` analyze final · `W20` trazabilidad · `W21` convergencia.

## 10. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G013-CLOCK-01 | Dueña resuelta | **PASA** |
| G013-CLOCK-02 | Usos de reloj inventariados | **PASA** — 57 |
| G013-CLOCK-03 | Pruebas vulnerables identificadas | **PASA** |
| G013-CLOCK-04 | Defecto reproducido | **PASA** — §4 |
| G013-CLOCK-05 | Fecha de negocio distinguida de la de fixture | **PASA** — §5 |
| G013-CLOCK-06 | Autoridad de zona conocida | **PASA** — UTC |
| G013-CLOCK-07 | Sin cambio de producto | **PASA** — 0 ficheros |
| G013-CLOCK-08 | Sin espera ni reintento | **PASA** |
| G013-CLOCK-09 | Referencia determinista definida | **PASA** |
| G013-CLOCK-10 | Semántica de vigencia preservada | **PASA** |
| G013-CLOCK-11 | Selección de tasa preservada | **PASA** |
| G013-CLOCK-12 | Sin cambios monetarios | **PASA** |
| G013-CLOCK-13 | Prueba de independencia de UTC | **PASA** |
| G013-CLOCK-14 | Prueba en `America/Caracas` | **PASA** |
| G013-CLOCK-15 | Prueba con día civil opuesto | **PASA** |
| G013-CLOCK-16 | Mutaciones significativas | **PASA** — 4 |
| G013-CLOCK-17 | Material OQ = 0 | **PASA** |
| G013-CLOCK-18 | UNKNOWN = 0 | **PASA** |
| G013-CLOCK-19 | Trazabilidad 100 % | **PASA** |

## 11. `/speckit.checklist`

- [ ] HEAD verificado · árbol clasificado · dueña confirmada
- [ ] `date.today()` contadas · otras fuentes de reloj contadas
- [ ] Pruebas afectadas identificadas · fallo reproducido bajo otra zona
- [ ] Fecha de negocio y fecha de fixture separadas · autoridad documentada
- [ ] Referencia determinista elegida · sin librería nueva · sin parche global
- [ ] Sin `sleep`, sin reintento, sin tolerancia, sin `skip`/`xfail`
- [ ] Pruebas bajo UTC, Caracas y una tercera zona · fronteras de vigencia
- [ ] Mutaciones definidas · Material OQ = 0 · UNKNOWN = 0 · trazabilidad 100 %

## 12. `/speckit.tasks`

| ID | Tarea | Fichero | Requisito | Mutación |
|---|---|---|---|---|
| T-01 | Referencia temporal explícita en la cabecera del fichero | `tests/test_spec013_financial_masters.py` | FR-013-043, 049 | M013-CLOCK-04 |
| T-02 | Sustituir las 57 construcciones con reloj por derivadas de la referencia | ídem | FR-013-041, 044 | M013-CLOCK-01, 02 |
| T-03 | La prueba de la ventana del día usa un instante fijo, no `now` | ídem | FR-013-045 | M013-CLOCK-03 |
| T-04 | Pruebas de frontera: antes, inicio, dentro, después | ídem | FR-013-043 | M013-CLOCK-03 |
| T-05 | Guarda estática dirigida al fichero | ídem | FR-013-047 | M013-CLOCK-04 |
| T-06 | Matriz de zonas horarias como evidencia | evidencia | FR-013-042, 046 | M013-CLOCK-01, 02 |

**Requisitos huérfanos: 0. Tareas huérfanas: 0.**

## 13. `/speckit.analyze` previo a implementar

| Contador | Valor |
|---|---:|
| BLOCKER / CRITICAL / CONTRADICTIONS | 0 / 0 / 0 |
| OWNER CONFLICT | 0 |
| ORPHAN REQUIREMENTS / TASKS | 0 / 0 |
| MATERIAL OQ / UNKNOWN | 0 / 0 |
| TRACEABILITY | 100 % |

Se consume la autorización expresa y se implementa.

## 14. `/speckit.implement`

Un solo fichero, y es de pruebas: `tests/test_spec013_financial_masters.py`.
**0 ficheros de producto.**

| Cambio | Detalle |
|---|---|
| `REFERENCIA = date(2026, 3, 11)` | El día de negocio de estas pruebas. Fija, pasada, a mitad de mes, posterior a la vigencia de la política que activan (`2020-01-01`) |
| `REFERENCIA_MEDIA_MANANA = datetime(2026, 3, 11, 10, 30, tzinfo=UTC)` | El instante de publicación, para probar que preguntar por un día es preguntar por el día entero |
| 58 sustituciones | Todas las construcciones con `date.today()` pasan a derivar de `REFERENCIA` |
| 5 sustituciones | Los instantes `datetime.now(UTC)` pasan a `REFERENCIA_MEDIA_MANANA`: eran inmunes a la zona, pero seguían leyendo el reloj |
| 4 pruebas nuevas | Independencia de zona, fronteras de vigencia, ventana del día y guarda estática |

**Lecturas de reloj que quedan en el fichero: 0.**

### Por qué una fecha fija y no «hoy en UTC»

Anclar en `datetime.now(UTC).date()` habría bastado para el defecto —UTC es UTC en
cualquier zona—, pero seguiría dependiendo del instante de ejecución en la frontera de
medianoche. Una referencia **pasada y fija** elimina la dependencia entera y, además,
conserva el camino que importaba: una tasa vigente desde una fecha pasada **sigue siendo
la vigente ahora**, de modo que las diez pruebas que consultan sin fecha explícita siguen
ejercitando la resolución por el instante actual del producto. No se cambió una regla por
una constante: se dejó de preguntar por un día distinto del que se había escrito.

### Lo que expresamente no cambia

Vigencia, arrastre, caducidad por política, selección entre fuentes, prioridad,
inversión, triangulación, procedencia y contratos monetarios: intactos. El producto no
se toca.

## 15. Evidencia — `evidence/clock-013/`

| Fichero | Contenido |
|---|---|
| `reproduccion-pre-fix.txt` | El RED: UTC 58/0 frente a `America/Caracas` 1 fallo, con la causa medida |
| `matriz-de-zonas.txt` | La suite bajo cinco entornos, incluido **sin `TZ`** |
| `mutaciones.txt` | M013-CLOCK-01..04 con restauración verificada |
| `regresion.txt` | Regresión completa bajo la zona real del sistema |

### Matriz de zonas horarias

| Entorno | Día civil | Resultado |
|---|---|---|
| **sin `TZ`** (Europe/Amsterdam, el del sistema) | 2026-09-17 | **62/62** |
| `TZ=UTC` | 2026-09-17 | **62/62** |
| `TZ=America/Caracas` | 2026-09-16 | **62/62** |
| `TZ=Pacific/Midway` | 2026-09-16 | **62/62** |
| `TZ=Pacific/Kiritimati` | 2026-09-17 | **62/62** |

Dos de las cinco zonas están en un **día civil distinto** del de UTC, y el resultado es
el mismo. `TZ=UTC` deja de ser necesario: era el parche que ocultaba la deuda.

### Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| M013-CLOCK-01 | El reloj en el registro de la tasa del día | **muere** — la prueba de la ventana del día y la guarda |
| M013-CLOCK-02 | Una fecha derivada colgando del calendario | **muere** — la prueba de fronteras |
| M013-CLOCK-03 | La siembra de vigencia desde el reloj | **muere** — tres pruebas |
| M013-CLOCK-04 | La referencia controlada vuelve a ser `date.today()` | **muere** — la guarda estática |

4/4 semánticamente efectivas; restauración `cmp` idéntica en las cuatro.

## 16. Clasificación de lo encontrado

| Hallazgo | Clase | Tratamiento |
|---|---|---|
| Las pruebas preguntaban por el día civil local | `TEST_DEFECT` / determinismo | **Corregido** |
| `active_policy` usa el día civil del servidor mientras las tasas usan instante UTC | observación, **no absorbida** | Coherente sobre servidor UTC, que es el despliegue documentado (`ADR-D0-001`). Se declara; no se corrige aquí |
| Clúster de QA y antivirus perdidos al rotar `/tmp` | `EXTERNAL_ENVIRONMENT` | Reconstruidos con la receta documentada; ClamAV 1.4.3 reinstalado y verificado con EICAR |
| PostgreSQL 16.2 frente a 18.6 | `ENVIRONMENT_BASELINE_DEVIATION` | Vigente |

`PRODUCT_CLOCK_DEFECT` = 0 · `NEW_REGRESSION_CLOCK_013` = 0 · `UNKNOWN` = 0.

## 17. Regresión

| Métrica | Valor |
|---|---:|
| TOTAL | **1.640** |
| PASSED | **1.632** |
| FAILED | **0** |
| ERRORS | **0** |
| SKIPPED | **8** (S3, esperados) |
| UNEXPECTED SKIPS | **0** |
| WARNINGS | **0** |
| EXIT | **0** |

Ejecutada **sola** y **sin forzar `TZ`**, bajo `Europe/Amsterdam`: el entorno cuyo
desfase con UTC originó la deuda. Denominador remedido: 1.636 del delta anterior más las
4 pruebas nuevas.

La tanda previa a reconstruir el entorno dio 37 fallos, todos de documentos y todos con
`SCAN_FAILED`: el antivirus se había ido con `/tmp`. Reinstalado ClamAV 1.4.3 y
verificado con EICAR, la tanda queda en cero. `EXTERNAL_ENVIRONMENT`, ajeno al delta.

## 18. `/speckit.analyze` final y trazabilidad

| Requisito | Prueba | Mutación |
|---|---|---|
| FR-013-041 | Las 62 pruebas del fichero, bajo cinco entornos | M013-CLOCK-01, 02, 03 |
| FR-013-042 | Tanda **sin `TZ`**: 62/62 | M013-CLOCK-02 |
| FR-013-043 | `REFERENCIA` y sus derivadas; `test_las_fronteras_de_vigencia_se_miden_contra_la_referencia` | M013-CLOCK-02, 03 |
| FR-013-044 | La regresión de la 013 y de tesorería, intacta | — |
| FR-013-045 | Las 10 pruebas que consultan sin fecha siguen ejercitando el «ahora» del producto | M013-CLOCK-03 |
| FR-013-046 | `test_la_vigencia_no_depende_de_la_zona_horaria_del_proceso` + matriz de cinco entornos | M013-CLOCK-03 |
| FR-013-047 | `test_estas_pruebas_no_leen_el_reloj` | M013-CLOCK-01, 04 |
| FR-013-048 | 0 `sleep`, 0 reintentos, 0 `skip`, 0 `xfail`, 0 tolerancias | — |
| FR-013-049 | `REFERENCIA` está declarada y comentada en la cabecera del fichero, con su porqué | M013-CLOCK-04 |
| FR-013-050 | Regresión completa 1.632/0 | — |

| Contador final | Valor |
|---|---:|
| Lecturas de reloj sin controlar en el ámbito vulnerable | **0** |
| BLOCKER / CRITICAL / CONTRADICTIONS | 0 / 0 / 0 |
| ORPHAN REQUIREMENTS / TASKS | 0 / 0 |
| MATERIAL OQ / UNKNOWN | 0 / 0 |
| Ficheros de producto modificados | **0** |
| Migraciones / cambios de esquema | **0** / **0** |
| **TRACEABILITY** | **100 %** |

## 19. Deudas no absorbidas

E2E-031-RESERVAS · E2E-HELPER-EMPRESA-AMBIGUO · INBOX-045-AISLAMIENTO · E2E-046-TIPOS ·
ORPHAN-046-SINGLE · IDEM-046-TRUNC · paginación de la bandeja · AUTH-MC-INTERMITENTE ·
D0-06 · D0-07 · OQ-048 · MD-049 · camino tras `EXPIRED` · Spec 018 · certificación de
compras · Spec 053 · deriva heredada de 21 operaciones · DT-03/04/06/07/10..18.
Y la observación nueva: **`POLICY-CLOCK-LOCAL`** — `active_policy` usa el día civil del
servidor mientras la resolución de tasas usa el instante UTC; coherente sobre el
despliegue documentado, declarado para su dueña (013/052).

## 20. Estado resultante

| | |
|---|---|
| **CLOCK-013** | **CLOSED / CONVERGED** |
| Spec 013 | sigue **`COMPLETE / CONVERGED`** |
| `TZ=UTC` como requisito de la suite | **eliminado** |
| Producto, migraciones, esquema, contratos monetarios | intactos |
