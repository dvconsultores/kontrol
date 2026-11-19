# ORG-07-EFFECTIVE-AUTHORITY-MATRIX · Cierre

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:**
  - Gobierno › «Matriz de autoridad»:
    - tabla con la columna «Ejerce»: persona, fuente, «Sustituye a» y vigencia de la asignación;
    - filas propias para cada delegación vigente;
    - filtros y «Exportar CSV»;
  - Gobierno › «Matriz de autoridad» › «Ver el detalle de …» › sección «Autoridad efectiva al …», con la competencia, la fuente, quién ejerce, la vigencia, el acto y la asignación.
- **WHAT_CAN_USER_DO:**
  - **Ver quién ejerce cada competencia a una fecha de corte:**
    - el titular, con origen CARGO;
    - una encargaduría, suplencia o comisión de servicio, con origen igual a la figura y el titular sustituido;
    - una delegación de atribuciones o de firma, en filas propias con los límites que guardó la asignación.
  - **Consultar una fecha pasada:** aparecen las asignaciones que estaban vigentes ese día, aunque hoy estén revocadas, finalizadas o vencidas.
  - **Seguir cada fila hasta su origen:** figura, código de la asignación, vigencia (`desde`, `hasta` y fin efectivo), acto, cargo de origen y avocaciones registradas.
  - **Filtrar** por unidad, cargo, acción, materia y texto libre. El texto libre también busca el código de la asignación y la persona cuando es visible.
  - **Exportar el CSV:** tiene las mismas filas que la pantalla y añade figura, persona, sustituido, asignación, vigencia, acto y cargo de origen.
  - **Persona reservada (OD-EA-01):** sin `gobierno_ocupacion:view`, la persona figura como «Reservado» en pantalla y en el CSV, y no se puede buscar por su nombre.
  - **Activar delegaciones en ORG-04:** antes daba 500 en la app real (D-EA-11); ahora funciona.
- **OWNER_UAT_READY:** YES. La tarjeta es `OWNER_UAT_CARD.md`, con los bloques A a F.
- **PRODUCT_STATUS:**
  - OWNER_UAT_READY.
  - CURRENT_PRODUCT_DEFECT=NO en ORG-07; antes era YES.
  - OWNER_ACCEPTED=NO: solo la dueña lo concede.
- **MISSING_GATES:** ninguno del ciclo.

## Cambio

- **Sin migración.** La cabeza de entrada era `0127_gov_handover_policy` y la de salida es `0128_gov_tre04_pago`, que llegó de P1 con el merge. MIGRATION_REQUIRED=0.
- **ORG-04 resuelve y ORG-07 proyecta:**
  - `service_ocupacion.autoridad_efectiva_en` es la API pública sobre `_vigentes_en`;
  - `service_autoridad._filas_filtradas` la consume;
  - AUTHORITY_ENGINES_CREATED=0, ORG03_REUSED=YES, ORG04_REUSED=YES.
- **Identidad de las filas:**
  - las filas del cargo siguen siendo `{cargo}:{accion}:{materia}`;
  - las de delegación son `{asignacion}:{accion}:{materia}`;
  - no hay duplicados.
- **Contrato:**
  - `MatrizFila.origen` pasa a texto con el vocabulario de las figuras y sigue valiendo CARGO en las filas base;
  - `MatrizFila.fuente` es nueva (MatrizFuente, MatrizPersona, MatrizCargoRef y MatrizActoRef);
  - el CSV tiene 9 columnas nuevas, añadidas al final;
  - no hay rutas nuevas.
- **Frontend:**
  - desaparece el aviso «llegarán con ORG-04»;
  - se añaden la columna «Ejerce» y la sección «Autoridad efectiva» del detalle.
- **Defecto de ORG-04 corregido (D-EA-11):**
  - `_reemplazar_competencias` hace `flush` mientras la asignación sigue en BORRADOR;
  - la regresión es `test_org07_ea17_*`, con la sesión de la app (`autoflush=False`).
- **Hardcode:** limpio (ver `HARDCODE_AUDIT.md`).

## Evidencia

| Prueba | Resultado |
|---|---|
| PG del ciclo (`test_gov_org07_efectiva.py`) | 17/17: los 20 puntos del §29 |
| Defecto reproducido | `test_org07_ea01_defecto_delegacion_visible` falla contra 65651eff y pasa con el código nuevo |
| Mutaciones M1–M9 | 9/9 muertas (ver `ATTEMPT_LOG.md`) |
| PG dirigida antes del merge | 602/602 |
| PG dirigida tras el merge con TRE-04 (39 ficheros: ORG-03/04/06/07, CTL-01, TRE-03/04, catálogo de auditoría, N9, OpenAPI, contrato de consultas y MFA) | 659/659 |
| Vitest completo tras el merge | 2533/2533 (231 ficheros) |
| typecheck · lint · build | OK |
| ruff | limpio |
| mypy | 157 de línea base; 0 en ficheros del ciclo |
| OpenAPI | 908 rutas, ninguna nueva; cambian los esquemas de la matriz |
| E2E `gobierno-autoridad-efectiva.spec.ts` más la regresión de autoridad, ocupación y políticas de asignación, tras el merge | 12/12, con limpieza LIMPIA |
| Axe | 0 serious/critical a 1280, 390 y 320, con responsive a 390 y 320 |
| Humo UAT (`--project=humo-uat`) tras el merge | 1/1 |

### Vitest

- La primera corrida tras el merge se lanzó mientras la PG dirigida cargaba el anfitrión y dio 1 fallo de 2533.
- No se registró el nombre de la prueba.
- Las dos corridas siguientes salieron enteras: 2533/2533.
- Se declara como inestabilidad bajo carga, sin identificar.

### PG completa

Corrida de 10:33 a 13:42 (−04) del 19/11, sobre 65651eff más los cambios del ciclo: 5841 pasadas, 18 omitidas y 5 fallidas.

- **NEW_FAILURE (0).**
- **BASELINE_FAILURE (4):** los mismos de los cierres anteriores, ajenos al ciclo. Repetidos aislados, fallan igual.
  - `test_n10_convergence::test_el_orm_y_la_base_no_difieren_en_nada`
  - `test_naive_datetime_input::test_guard_d01_ningun_datetime_desnudo`
  - `test_spec019_receipt::test_una_recepcion_sin_lineas_no_se_acepta`
  - `test_spec019_receipt::test_rechazar_la_recepcion_deja_el_veredicto_guardado`
- **ENVIRONMENT_FAILURE (1):** `test_iso_barridos::test_barrido_cabecera_manipulada`.
  - A mitad del barrido, las peticiones de `admin_b` empezaron a responder 401 `AUTH_INVALID_TOKEN`, a partir de las rutas de maestros: la sesión del actor caducó durante una corrida larga en un anfitrión cargado.
  - Las rutas afectadas no son del ciclo. Repetida aislada, pasa.
- **TIME_WINDOW_BASELINE (0).** No se invocó OBS-PG-MIDNIGHT-CROSSING-01.

## DeepSeek

- 6 llamadas de 8: 2 tareas base y 4 reintentos.
- 25.524 tokens de entrada y 19.437 de salida, $0,028014.
- 2 PASS tras sus reintentos (T04 y T05).
- Claude hizo T01, T02, T03, T06, T07 y el contrato del frontend (ver `ATTEMPT_LOG.md`).

## Auditoría de parametrización

- ORG-07: CURRENT_PRODUCT_DEFECT pasa de YES a NO y PRIORITY de P1 a NONE.
- Totales: P0=2, P1 de 30 a 29, P2=9, NONE de 3 a 4.
- Defectos vigentes: de 4 a 3 (BUD-02, CTL-02 y CTL-04).
- **NEXT_CANDIDATE recomendado:** CTL-02 (procesos ausentes del registro de la bitácora). Tiene impacto transversal y CTL-04 depende de él.
