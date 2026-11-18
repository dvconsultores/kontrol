# PROC-07/PROC-08-COMMISSION-POLICY · Registro de intentos (DeepSeek)

- **Modelo:** `deepseek-v4-pro`.
- **Tope global:** 18 llamadas (OD-CP-01), con `RETRY_MAX` 2 por subproblema.

**Control de salida previo a cada llamada:**

```
EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0
```

| # | Tarea | Tokens (entrada/salida) | Coste | Auditoría | Motivo |
|---|---|---|---|---|---|
| 1 | T02 · autoridad `service_comision_regla.py` | 10054/6579 | $0,010097 | REJECT | (R1) `_cargos_vigentes` devolvía asignaciones como cargos, así que CARGO, UNIDAD y COMPETENCIA no funcionaban; mypy lo detectó como arg-type. (R2) F401. (R3) `str(UUID(...))` en `inhibidos`. (R4) Los documentos no se ordenaban por nombre |
| 2 | T02 · reintento 1 | 1320/1214 | $0,001630 | PASS | — |
| 3 | T03 · servicio, esquemas y API de políticas | 11908/14682 | $0,017953 | REJECT | (S1) `field_errors[x].append` sobre un dict vacío: KeyError, es decir, HTTP 500. (S2) La anotación de `_validar_activacion` no coincidía con lo que devuelve. (S3) Importaba las etiquetas de `models`. (S4) Faltaba `tenant_id` en `_usuarios_por_ids`; el error venía del brief de Claude. (S5) F401, F841 e I001. (S6) Faltaba capturar `IntegrityError`. (S7) Consultas sin `company_id`. Además había un bloque sin efecto (SEARCH igual a REPLACE), que no cambió nada |
| 4 | T04 · PROC-02 consume la autoridad | 9021/9997 | $0,012622 | REJECT | (R1) Un SEARCH inventado y sin efecto. (R2) Un ancla inexistente para `designar_presidente`, con código muerto. (R3) Un `=======` suelto dentro de `crear`: bloque mal formado y SyntaxError. (R4) El fragmento B de Claude cortaba `ETIQUETAS["areas"]` a mitad de expresión, así que el reemplazo dejó el fichero roto. Los tres ficheros se devolvieron al estado anterior; nada se corrigió a mano |
| 5 | T03 · reintento 1 | 4268/2486 | $0,004019 | PASS | — |
| 6 | T04 · reintento 1 | 10225/13162 | $0,015899 | REJECT | 18 bloques bien formados con la semántica aceptada. Fallos: (R1) faltaba importar `GovernmentCommissionPolicy` (F821 y name-defined de mypy); (R2) `REGLA_VERSION_LCP` sin uso; (R3) I001 |
| 7 | T04 · reintento 2 (imports) | 760/307 | $0,000598 | REJECT parcial | R1 y R2 corregidos; persiste I001 (alias `faltantes as …` en el mismo bloque). Con los reintentos agotados, Claude reclasifica el resto como CLAUDE y separa el import del alias en su propio bloque, como pide isort. Es la única línea escrita por Claude en T04 y se declara así |
| — | T04 · línea de Claude | — | — | CLAUDE | La prueba de humo de Claude encontró que `ComisionIn` no aceptaba `politica_id`: el fragmento N del brief empezaba en la línea 41 y no incluía esa clase. Con los reintentos de T04 agotados, Claude añadió la línea `politica_id: str \| None = None` y lo declara. Después la prueba de humo pasa: HUMO_OK |
| 8 | T05 · PROC-07 apertura y evaluación | 10268/14917 | $0,017444 | REJECT | (R1) `cuenta_voto` de un suplente con su principal presente; el error venía del contrato de Claude y se detectó en la regresión de PROC-08. (R2) Lista de nombres en lugar del número, con union-attr. (R3) F841. (R4) arg-type en `_actor` |
| 9 | T06 · PROC-08 recomendación | 9305/6946 | $0,010091 | REJECT | (R1) La exclusión de inhibidos comparaba `official_id` con ids de miembro, así que nunca se activaba, y dejaba código muerto `if False`. (R2) `cuenta_voto` de suplentes, por el contrato de Claude. (R3) `inhibidos` recibía UUID. (R4) Se reutilizaba la variable `r`, con union-attr. (R5) I001 |
| 10 | T05 · reintento 1 | 2170/1558 | $0,002299 | REJECT | R2, R3 y R4 corregidos. Usa `_cuenta_voto` sin definirla: F821 |
| 11 | T06 · reintento 1 | 3432/1960 | $0,003198 | REJECT | (R6) Dos bloques repetían zonas ya cambiadas por otros dos y un SEARCH empezaba a mitad de indentación: aplicados en orden, el fichero quedaba roto. Se volvió al estado posterior a T06 sin tocar nada a mano |
| 12 | T05 · reintento 2 (`_cuenta_voto`) | 1065/252 | $0,000683 | REJECT | Faltaba importar `Iterable` (F821). Además, defecto semántico: la primera condición no comprobaba función ni condición, así que un suplente o un secretario presentes contaban voto. Con los reintentos de T05 agotados, Claude reclasifica el resto como CLAUDE: añade el import y reescribe `_cuenta_voto` (12 líneas) según la regla del contrato. Se declara |
| 13 | T06 · reintento 2 | 11252/3629 | $0,008052 | REJECT parcial | Bloques bien formados: aplicados. Quedan (a) `r` reutilizada (union-attr); (b) `cuenta_voto` duplicado en funciones anidadas, con `m.funcion == "SUPLENTE"`, un valor que no existe; (c) `inhibido` comparaba `official_id`; (d) F841 y var-annotated. Con los reintentos de T06 agotados, Claude reclasifica el resto como CLAUDE: lleva la regla de voto a la autoridad como `cuenta_voto` pública (la usan PROC-07 y PROC-08: una sola regla), corrige `inhibido` y el voto del estado, quita el código anidado y renombra la variable. Se declara |
| — | Excepción de la dueña | — | — | OWNER_EXCEPTION | 2026-11-17: tope ampliado de 18 a 26 llamadas («Ampliar a 26», la opción recomendada), con el diagnóstico de los reintentos agotados en T03 a T06 |
| 14 | T07a · pruebas de políticas, autoridad y PROC-02 | 8569/9519 | $0,012009 | REJECT parcial | Se aceptan las ediciones de proc02, mfa, n9 y seeds. Se rechaza el fichero nuevo: defectos de prueba (el ayudante LCP sin piso, «ua» en la empresa B, falta de If-Match, firma de `umbral`, claves inventadas, `field_errors` en `details`, documentos sin tipo). Una parte (el uso de «ua» en B) se copió del ejemplo de humo de Claude, que también tenía ese fallo. Otro fallo: colisión de códigos en n9 |
| 15 | T07a · reintento 1 | 13486/10156 | $0,014702 | REJECT parcial | Fichero nuevo aplicado: 12 de 14 pasan. Fallan `test_umbral_quorum_decision` (forma de regla y claves inventadas) y `test_regla_congelada` (activa una comisión sin miembros). Se rechazan los demás bloques: reenvíos de ediciones ya aplicadas, con marcadores de 8 caracteres y anclas inventadas; entre ellos iba el cambio de n9 |
| 16 | T07b · pruebas de integración PROC-07 y PROC-08 | 7287/6964 | $0,009229 | REJECT | Faltaba el fixture `gobierno` (403 MODULE_NOT_ENTITLED en las 9); `_apertura_body` con `mundo` y `exp` sin definir (F821); F841 |
| 17 | T07a · reintento 2 | 4474/2586 | $0,004196 | REJECT parcial | `test_umbral_quorum_decision` y n9 corregidos (13 de 14). En `test_regla_congelada`, el PUT reenviaba los requisitos con claves de salida y daba 422. Con los reintentos de T07a agotados, Claude reclasifica: filtra los requisitos y documentos a las claves de entrada (dos comprensiones y una constante) y lo declara. Resultado: 14 de 14 |
| 18 | T07b · reintento 1 | 14525/6856 | $0,012283 | REJECT | Corrigió `_apertura_body` y F841, pero ignoró R1 (el fixture `gobierno`). Un diagnóstico de Claude en una copia temporal mostró que el ciclo sin comisión pasa y que quedaban defectos de la prueba (If-Match en dos ayudantes; un escenario inalcanzable) |
| 19 | T09a · tipos, lista, ficha, rutas, menú y Vitest | 9126/14415 | $0,016511 | REJECT | Lista, ficha, rutas, menú y `pantallas.ts` aplicados. Las pruebas de la ficha montan la lista (ruta mal formada); TS1209 (`new …?.ApiError`); no entregó `PoliticaComisionPage.test.tsx` aparte (las pruebas de la ficha van en el fichero de la lista) |
| 20 | T09b · formulario y Vitest | 6209/19242 | $0,019441 | REJECT | El formulario se pinta. La prueba busca la etiqueta exacta «Código», pero los obligatorios se leen «Código (obligatorio)» (FormField); 7 de 9 fallan por eso |
| 21 | T07b · reintento 2 | 1711/1586 | $0,002124 | REJECT parcial | Diez de once bloques sin línea `FILE:`; Claude añadió solo esa cabecera, sin tocar el código, y lo declara. Resultado: 8 de 9. La prueba de la guarda enviaba un cuerpo de oferta inventado; con los reintentos agotados, Claude lo sustituye por el cuerpo del ayudante `_crear_oferta` y lo declara. Resultado: 9 de 9 |
| — | T09a y T09b · líneas de Claude | — | — | CLAUDE | `npm run typecheck` mostró 7 errores en los componentes: tipos de `politicasComision.ts` distintos de la API (fecha, mínimo y acto como texto u opcionales) y, en la lista, uso de `asChild` y `actions`, que no existen en Button ni en EmptyState, y un `map` de tipos mezclados. Los reintentos en curso solo cubrían las pruebas y el presupuesto se reservaba para T10 y T12. Claude corrigió los tipos y esas tres expresiones (y retiró el import que quedó sin uso). Se declara |
| 22 | T09a · reintento 1 (Vitest) | 13776/4701 | $0,010082 | PASS | 12 de 12 (lista 5 y ficha 7) |
| 23 | T09b · reintento 1 (Vitest) | 7628/5480 | $0,008086 | REJECT | 4 de 9: etiquetas repetidas en el componente («Tipo», «Cantidad», «Numerador»…), `selectOptions` sobre elementos que no son select y lectura del PUT de una llamada inexistente |
| — | Segunda excepción de la dueña | — | — | OWNER_EXCEPTION | 2026-11-17: tope ampliado de 26 a 31 («Ampliar a 31», la opción recomendada) para T10, en 2 llamadas, y la E2E, con el diagnóstico del quórum que el frontend calculaba en código |
| 24 | T09b · reintento 2 | 7544/7073 | $0,009435 | REJECT parcial | Etiquetas únicas en el componente: aplicadas y aceptadas. Prueba en 6 de 9: lee un tercer argumento inexistente de `apiFetch`, hace `JSON.parse` sobre un cuerpo que es objeto, (g) no elige el tipo de quórum ni el de comisión (la validación local impide el envío) y (h) espera `/p1` en lugar de `pol-1`. Con los reintentos agotados, Claude corrige esas aserciones, los tipos de la prueba (sin `any`) y un import sobrante en otras dos pruebas. Resultado: Vitest 21 de 21, typecheck y lint limpios. Se declara |
| 25 | T10a · pantallas de comisión | 14735/8650 | $0,013935 | REJECT parcial | 25 de 26 bloques aplicados. Se rechaza uno (SEARCH repetido 4 veces en las fixtures). Defectos: atributo inventado `eliminado_en` (mypy); un `=======` suelto en ComisionFormPage (SyntaxError); `designarPresidente` sin definir (TS2304) |
| 26 | T10b · expediente: regla y modo sin comisión | 10384/9620 | $0,012886 | REJECT | Quita el cálculo de quórum en el navegador (hardcode H1 del frontend). Errores: props `responsables` y `modo` sin declarar en la tarjeta de evaluación, tipos de `onRegistrar` viejos, `estado` posiblemente indefinido y dos variables sin uso |
| 27 | T10a · reintento 1 | 1866/1104 | $0,001772 | REJECT parcial | Rutas relativas mezcladas (`backend/` y `src/`); Claude las normalizó a rutas desde la raíz sin tocar el contenido, y lo declara. Corrige `eliminado_en`, `designarPresidente` y `preside` en las fixtures. El bloque del marcador volvió a salir mal formado: el fichero contiene una línea `=======` y el formato SEARCH/REPLACE no puede expresar sin ambigüedad que se borre. Claude restauró la cabecera original del FormField «Objeto o especialidad» (cuatro líneas, idénticas a HEAD) y lo declara |
| 28 | T10b · reintento 1 | 1696/1439 | $0,001990 | PASS | Rutas relativas a `resources/frontend`; aplicado con esa raíz. Typecheck y lint limpios. Vitest de Gobierno: 855 de 855 |
| 29 | T12 · E2E de políticas y adaptación de 8 E2E | 7379/9011 | $0,011049 | REJECT parcial | Aplicado: spec nueva, ayudante `politicaHistoricaE2E` y 8 ficheros adaptados. Lint: un import y un parámetro sin uso. La ejecución real destapó defectos de prueba y tres de producto en el formulario; Claude los cerró con los reintentos agotados (ver la fila de T12 y T09b de Claude) |
| 30 | T03 · reintento 2 (nombres de esquemas) | 389/219 | $0,000360 | PASS | `DecisionPoliticaIn` y `HistoriaPoliticaComisionOut`: OpenAPI sin cambios fuera del alcance |
| — | T05 · línea de Claude | — | — | CLAUDE | La PG dirigida (387 pasadas) avisó con SAWarning de un `db.get(Member, None)`: el estado de evaluación buscaba al autor del resultado por `member_id`, nulo cuando registra un responsable. Claude usa `official_id`, siempre informado, con filtro de empresa, en resultados y en aportes (dos bloques de 4 líneas). Con SAWarning tratado como error: 17 de 17. Se declara |
| — | T12 y T09b · trabajo de Claude tras la ejecución | — | — | CLAUDE | La E2E real se iteró con sondas temporales, ya retiradas. **Defectos de producto del formulario corregidos por Claude:** (1) un requisito podía enviarse sin función ni condición; ahora hay validación local; (2) los errores 422 con claves compuestas (`requisitos.0.funcion`) no se mostraban; ahora se ven en su sección y en el mensaje general; (3) «Aplica a la apertura» y «Aplica a la recomendación» arrancaban desmarcados, al revés que los valores por defecto del backend; ahora arrancan marcados, con validación local. **Ajustes de prueba en la E2E:** selectores estrictos (encabezados de nivel 1, `.first()`, «Mínimo» frente a «Mínimo de principales»), cuerpos de miembros con el contrato real de la API (`funcion`, `condicion`, `suplente_de_id`, respuesta 200), 12 funcionarios, permiso de ver para el usuario de la otra empresa (para que el 404 pruebe el aislamiento y no un 403), y consumo de PROC-07 y PROC-08 comprobado en el estado de la API, porque la regla solo se pinta dentro de los formularios de apertura y recomendación. Vitest del formulario: fixtures alineadas con el catálogo real. Resultado: CP-E2E-01 1 de 1 (1,2 min), Axe en 1280, 390 y 320 |
| — | Regresión E2E · ajustes de Claude | — | — | CLAUDE | De 14 E2E relacionadas pasan 11 a la primera. COM-E2E-01: la política se creaba después de abrir el formulario y la historia dice ahora «Activada con la política»; PROC-08: «Firmantes con voto: 3 de 3» (quórum calculado en el navegador, retirado por diseño) pasa a «(requerido 2 de 3)», que fija el backend; CNT-01: REAUTH_REQUIRED con 4 workers (deuda heredada OBS-E2E-CNT01-REAUTH-300S-01), pasa con 2. Tras los ajustes, las 14 en verde |

## Totales

- **Llamadas:** 30, de un tope de 31.
  - El tope era 18 (OD-CP-01) y la dueña lo amplió dos veces: a 26 y a 31 (OWNER_EXCEPTION ×2).
- **Tareas base y reintentos:** 12 tareas base (T02, T03, T04, T05, T06, T07a, T07b, T09a, T09b, T10a, T10b y T12) y 18 reintentos, todos dentro de `RETRY_MAX: 2` por subproblema.
- **Resultado:** 5 PASS directos y 25 REJECT o REJECT parcial.
  - Los rechazos fueron siempre por defectos concretos y verificados.
  - Ningún parche se corrigió a mano para atribuírselo a DeepSeek.
  - No se usó `ruff --fix`.
- **Tokens:** 215.832 de entrada y 196.310 de salida.
- **Coste:** $0,264675.
- **Trabajo de Claude (CLAUDE_IMPLEMENTED):** solo después de agotar los reintentos de cada tarea, y declarado en cada fila «Claude»:
  - imports;
  - la regla de voto del suplente, llevada a la autoridad como `cuenta_voto`;
  - un campo de esquema que el brief había omitido;
  - tipos de TypeScript;
  - el filtrado de claves en una prueba;
  - la normalización del marco de los bloques (cabeceras `FILE:` y rutas);
  - tres defectos de producto del formulario destapados por la E2E;
  - los ajustes de las E2E.
- **Diseño, briefs, auditoría y certificación:** Claude. **Código semántico y pruebas:** DeepSeek, salvo lo declarado.

## Mutaciones (Claude, 2026-11-18 00:57 −04)

Script fuera del repositorio (`mutar_cp.py`): cada mutación exige un ancla única, corre sus pruebas con `-x` y restaura el original en `finally`. Después se verificó el árbol restaurado: 32 de 32 en las tres PG del ciclo.

| Id | Mutación | Fichero | Prueba que la mata | Resultado |
|---|---|---|---|---|
| M1 | Ficha de la política sin filtro de empresa (tenant bypass) | `service_comision_politicas.py` | `test_politica_ciclo_y_aislamiento` | MUERTA |
| M2 | Sin máximo de principales | `service_comision_regla.py` | `test_maximo_de_principales` | MUERTA |
| M3 | Todo funcionario cumple el requisito de competencia | `service_comision_regla.py` | `test_requisito_de_competencia` | MUERTA |
| M4 | Umbral de quórum y decisión fijo en 1 | `service_comision_regla.py` | `test_umbral_quorum_decision`, `test_quorum_por_unanimidad` | MUERTA |
| M5 | Se admite una política vencida o cerrada | `service_comision_politicas.py` | `test_comision_exige_politica_vigente` | MUERTA |
| M6 | Un miembro inhibido asiste a la apertura | `service_evaluacion.py` | `test_inhibido_no_asiste_y_actua_su_suplente` | MUERTA |
| M7 | Se ignora el documento obligatorio | `service_comision_regla.py` | `test_documento_de_constitucion`, `test_documento_de_apertura_obligatorio` | MUERTA |
| M8 | La política vigente se puede editar (history/formalized bypass) | `service_comision_politicas.py` | `test_politica_ciclo_y_aislamiento` | MUERTA |

**Resultado:** 8 de 8 muertas, ninguna sobrevive.
