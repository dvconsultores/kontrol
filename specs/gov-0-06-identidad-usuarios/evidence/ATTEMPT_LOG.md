# ORG-06 · registro de intentos

Regla endurecida: ATTEMPT, RETRY_1, RETRY_2, STOP por subtarea semántica real. Tras STOP solo sigue una subtarea con NEW_ROOT_CAUSE = 1 o NEW_TECHNICAL_BOUNDARY = 1, registrando antes PREVIOUS_SUBTASK, PREVIOUS_ROOT_CAUSE, NEW_SUBTASK, NEW_ROOT_CAUSE, NEW_TECHNICAL_BOUNDARY, WHY_SEMANTICALLY_DIFFERENT y EVIDENCE. PARALLEL_DEEPSEEK_CALLS = 0.

Entrada: `fba4a31`. PREVIOUS_PUBLIC_AUTHOR_MISMATCH = 1. HISTORY_REWRITTEN = 0. PREVIOUS_CYCLE_RETRY_POLICY_COMPLIANCE = PARTIAL. ALEMBIC_HEAD_BEFORE = 0076_gov_org04_ocupacion. MIGRATION_REVISION_SELECTED = 0077_gov_org06_identidad.

## Registro

```
T001 ATTEMPT enviado
T001 ATTEMPT AUDIT_REJECT: GOV-ORG-006 en docstring; unique=True duplica UniqueConstraint
T001 RETRY_1 AUDIT_PASS; migracion subir/bajar/subir OK en PostgreSQL
T002 ATTEMPT enviado
T002 ATTEMPT AUDIT_REJECT: falta import Literal; ids como int (son texto); motivo de politica no admite null
T002 RETRY_1 enviado
T002 RETRY_1 AUDIT_PASS
T003a ATTEMPT enviado
T003a ATTEMPT AUDIT_REJECT: permisos como texto (ValueError), import redundante de la fixture ocupacion, User sin importar
T003a RETRY_1 enviado
T003a RETRY_1 parcial: RED real por API ausente; quedan fechas sin isoformat y avisos de ruff
T003a RETRY_2 enviado
T003a RETRY_2 STOP: dejo sin importar _post. Restaurada la linea literal de la propuesta RETRY_1 (mecanico, declarado), sin nueva llamada.
T003d PREVIOUS_SUBTASK=T003a PREVIOUS_ROOT_CAUSE=errores de arnes (tipos de permisos, imports, fechas) NEW_SUBTASK=T003d NEW_ROOT_CAUSE=1 NEW_TECHNICAL_BOUNDARY=0 WHY_SEMANTICALLY_DIFFERENT=D05 usa uuid4 como cuenta y contradice el contrato: el caso prueba solape con cuenta real EVIDENCE=test_gov_org06_vinculos.py D05
T003d AUDIT_PASS; RED real: D01..D15 fallan por rutas ausentes (NOT_FOUND)
T004 ATTEMPT enviado
T003a excepcion mecanica declarada: .isoformat() en fechas restantes, sin llamada nueva (misma causa, presupuesto agotado)
T004 ATTEMPT AUDIT_REJECT: campos inventados en Role y GovernmentOfficial, email como usuario, eventos fuera del catalogo, solape sin fechas, UUID, SEARCH sobre lineas inexistentes (encargo sin esas lineas: causa compartida con Claude)
T004 RETRY_1 enviado
T004 RETRY_1 AUDIT_REJECT: status y estado confundidos, catalogo ORG-06 incompleto, estado ACTIVA inexistente en regla
T004 RETRY_2 enviado
T004 RETRY_2 AUDIT_PASS en service_identidad; un SEARCH de service_sod no caso: excepcion mecanica declarada, .estado por .status en usuarios_equivalentes, misma correccion ordenada, sin llamada nueva
T005 ATTEMPT enviado
T005 ATTEMPT AUDIT_REJECT: _situacion_vinculo inexistente; funcionario.get(estado) daria FUNCIONARIO_INACTIVO siempre; usuario opcional; detalle con caso oculto
T005 RETRY_1 enviado
T005 RETRY_1 aplicado (deepseek-v4-pro 1035/723 $0.000969)
T005 RETRY_1 AUDIT_PASS (ruff limpio; mypy solo 4 preexistentes)
SUBTAREA NUEVA T003e: PREVIOUS_SUBTASK=T003a-d (pruebas de vinculo D01-D15); PREVIOUS_ROOT_CAUSE=uso erroneo de ayudantes; NEW_SUBTASK=T003e pruebas de autoridad A01-A10 y ayudantes de guarda; NEW_ROOT_CAUSE=0; NEW_TECHNICAL_BOUNDARY=1 (derivacion de autoridad y guarda de operacion protegida, fichero nuevo); WHY_SEMANTICALLY_DIFFERENT=prueba autoridad derivada de ORG-04, no el ciclo de vida del vinculo; EVIDENCE=tasks T003 solo cubrio D01-D15
T003e ATTEMPT enviado
T003e ATTEMPT AUDIT_REJECT: F821 por imports ausentes, import desde org06_guarda de nombre ajeno, linea muerta en A02, vinculo duplicado en A04, monto numerico en A04, falta declara_delegable en A08, cuenta creada dos veces en A10
T003e RETRY_1 enviado
T003e RETRY_1 AUDIT_PASS con excepcion mecanica declarada: ruff --fix quito un import sin uso en org06_guarda.py, sin llamada nueva
SUBTAREA NUEVA T003s: PREVIOUS_SUBTASK=T003e; PREVIOUS_ROOT_CAUSE=montaje de pruebas de autoridad; NEW_SUBTASK=T003s pruebas S01-S09 y negativas N; NEW_ROOT_CAUSE=0; NEW_TECHNICAL_BOUNDARY=1 (separacion de funciones, categorias y politica, fichero nuevo); WHY_SEMANTICALLY_DIFFERENT=prueba CTL-01 y maker-checker por actor efectivo, no la derivacion de autoridad; EVIDENCE=encargo S01-S10 y seccion 54
T003s ATTEMPT enviado
T003s ATTEMPT AUDIT_REJECT: imports de modulos inexistentes, mundo.cuentas inventado, prefijo I doble, claves ocupacion inexistentes, campo estado inventado, emisor_vinculado como dict, S04 sin exigencia, S08 activa el vinculo y no la asignacion, S09 vinculo duplicado, N03 y N04 alteran el cargo emisor compartido, codigo muerto
T003s RETRY_1 enviado
T003s RETRY_1 AUDIT_REJECT: pruebas vaciadas de escenario (N03 afirma 200 tras revocar, N05 sobre otra tabla, S05-S09 con regla ajena, C01 y P01 inventan rutas); causa compartida: el encargo de reintento no reenvio los escenarios completos
T003s RETRY_2 enviado (ultimo intento de esta subtarea)
T003s RETRY_2 AUDIT_REJECT parcial: 18 pruebas con escenarios correctos; quedan defectos: clave id por vinculo_id en S04, version en cuerpo y no If-Match en C01 y P01, codigo GOV_PERMISSION_DENIED inventado en N06, nuevo_cargo desempaquetado en N02, fechas date sin isoformat en N02 y N03, variables sin uso. Ademas C01 paso 6 depende de evento ROLE_ASSIGNED que el ayudante no emite (causa del encargo).
T003s STOP: RETRY_SLOT=EXHAUSTED; NEW_ROOT_CAUSE=0; NEW_TECHNICAL_BOUNDARY=0 para estos defectos; NO_NEW_DEEPSEEK_CALL=1; fichero sin aprobar en el arbol; decision pendiente de la duena
PAUSA 2026-11-07: traslado de la duena; ciclo sin confirmar; T006 no enviado
DECISION DUENA 2026-11-07: T003s autorizada una llamada extra como excepcion registrada (EXCEPCION_1); PROCESS_COMPLIANCE quedara PARTIAL
T003s EXCEPCION_1 enviada
T003s EXCEPCION_1 AUDIT_PASS (bloque 2 sin efecto porque el 1 ya cubrio ambas sangrias); formato declarado: ruff --fix ordeno imports (I001), solo formato
T003 RED: 46/46 fallan por rutas ausentes (404 NOT_FOUND) en PostgreSQL
SUBTAREA NUEVA T006a: categorias, politica y guarda en service_identidad; incluye T004f con NEW_ROOT_CAUSE=1 (valor ACTIVE de User.status y Role.status del nucleo, nunca rechazado antes: T004 rechazo nombres de columna, no valores; evidencia app/modules/identity_access/authority.py)
T006a ATTEMPT enviado
T006a ATTEMPT AUDIT_REJECT: NoReturn sin importar, raise sin from None en except (B904), ids UUID pasados como str (mypy), indexado de opcional en la guarda, clave categoria_descripcion no pedida
T006a RETRY_1 enviado
T006a RETRY_1 aplicado: ruff limpio; queda 1 error mypy (indice str en dict[UUID, Role]) que no se comunico en el rechazo anterior (salida recortada por Claude)
T006a RETRY_2 enviado
T006a RETRY_2 AUDIT_PASS (ruff limpio; mypy solo los 4 preexistentes)
SUBTAREA NUEVA T006b: NEW_TECHNICAL_BOUNDARY=1 (integracion en servicios hermanos ORG-04, DOC-02 y CTL-01: service_ocupacion, service_actos, service_sod), distinta de T006a (service_identidad)
T006b ATTEMPT enviado
T006b ATTEMPT AUDIT_PASS (ruff limpio, mypy sin nuevos, import sin ciclos)
T006 regresion ORG-04+DOC-02+CTL-01 en PG: 123 pasan; 1 falla esperado test_cr01_catalogo_acciones (catalogo SoD con ORG-06; se actualiza en T007)
SUBTAREA NUEVA T007a: NEW_TECHNICAL_BOUNDARY=1 (capa HTTP: api_identidad.py y main.py)
T007a ATTEMPT enviado
T007a ATTEMPT aplicado; auditoria: rutas, permisos y estilo conformes
T007a ATTEMPT AUDIT_REJECT: importa User de app.schemas.auth (modulo inexistente: ModuleNotFoundError); primera linea del fichero es la cabecera "# FILE:" del formato
T007a RETRY_1 enviado
T007a RETRY_1 AUDIT_PASS (modulo importa; las rutas responden)
SUBTAREA NUEVA T007b: NEW_TECHNICAL_BOUNDARY=1 (registro transversal: catalogo de auditoria, auditoria institucional CTL-04 y recuentos de pruebas del nucleo por migracion 0077, 4 permisos y 11 eventos)
T007b ATTEMPT enviado
T007b ATTEMPT: 12 bloques aplicados y auditados conformes (falsa alarma de DeepSeek: gov-0-06 es el owner_spec real de los eventos ORG-06); bloque 1 AUDIT_REJECT: SEARCH con sangria inexistente (fragmento a mitad de linea)
T007b RETRY_1 enviado
T007b RETRY_1 AUDIT_PASS (la clave estado ya pasa el catalogo)
SUBTAREA NUEVA T007c (GREEN): PREVIOUS_SUBTASK=T004 (servicio de vinculos, auditado de forma estatica); NEW_ROOT_CAUSE=0 declarado con honestidad: es un nombre de clave, familia cercana a T004 RETRY_1 (status/estado en atributos ORM); NEW_TECHNICAL_BOUNDARY=1: frontera HTTP servicio-esquema de respuesta, solo observable al existir la API (ResponseValidationError 'status' requerido en VinculoResumen); EVIDENCE=traza de test_D01. Queda a juicio de la duena en el informe.
T007c ATTEMPT enviado
T007c ATTEMPT AUDIT_PASS (aviso MATERIAL DECISION de DeepSeek: falsa alarma, las pruebas ya existen)
T007c GREEN: 30/46 pasan. Quedan: (a) OcupacionInstitucional.ejercicio declarado str y el servicio da int (14 pruebas); (b) A03 espera 200 pero la plataforma rechaza con 422 UNKNOWN_QUERY_PARAMETER los parametros desconocidos (comportamiento mas estricto y correcto: defecto de la prueba); (c) N05 hace UPDATE sin cambio de valor, que el disparador IS DISTINCT FROM no rechaza (defecto de la prueba nacido del encargo de Claude)
SUBTAREA NUEVA T002c: NEW_ROOT_CAUSE=1 (tipo del ejercicio en el esquema de respuesta; T002 nunca se rechazo por eso)
T002c ATTEMPT enviado
T002c ATTEMPT AUDIT_PASS (linea unica)
SUBTAREA NUEVA T003g (GREEN de pruebas): NEW_ROOT_CAUSE=1 para A03 (contrato de plataforma UNKNOWN_QUERY_PARAMETER, nunca rechazado) y para N05 (UPDATE sin cambio no ejercita el disparador IS DISTINCT FROM; error del encargo de Claude, nunca rechazado); NEW_TECHNICAL_BOUNDARY=1 (defectos observados solo al ejecutar contra la API real)
T003g ATTEMPT enviado
T003g ATTEMPT AUDIT_PASS
GREEN tras T002c: 42/46. SUBTAREA NUEVA T003h: NEW_ROOT_CAUSE=1 (D15 compara con la clave "unidad_hija" en vez del id de la unidad del fixture; N04 viola ck_gov_positions_inactivo_fechado porque fecha valid_to sin status INACTIVO); ambos nunca rechazados
T003h ATTEMPT enviado
T003h ATTEMPT AUDIT_PASS. GREEN backend ORG-06: 46/46 en PostgreSQL; ruff limpio
SUBTAREA NUEVA T008: NEW_TECHNICAL_BOUNDARY=1 (concurrencia real con hilos en PostgreSQL, fichero nuevo)
T008 ATTEMPT enviado
T008 ATTEMPT AUDIT_REJECT: formato de error json()["error"]["code"] inexistente (es json()["code"]), vinculo_activo con un detalle en vez de cuerpo, clave exige en vez de exige_identidad, rol "Ejecutivo" inventado, aserciones C04 sin fin_efectivo y vigentes<=2 no pedida
T008 RETRY_1 enviado
T008 RETRY_1: 13 bloques aplicados; 6/6 pasan 3 veces; AUDIT_REJECT parcial: el bloque que quita la consulta vigentes no caso (F841)
T008 RETRY_2 enviado
T008 RETRY_2 AUDIT_PASS: 6/6 carreras en PostgreSQL (3 corridas previas 6/6), ruff limpio
SUBTAREA NUEVA T009: NEW_TECHNICAL_BOUNDARY=1 (frontend: cliente de tipos, registro de pantallas y menu)
T009 ATTEMPT enviado
T009 ATTEMPT AUDIT_PASS (tsc y eslint limpios; router pendiente hasta que existan las paginas)
SUBTAREA NUEVA T010a: NEW_TECHNICAL_BOUNDARY=1 (pantalla VinculosPage, fichero nuevo)
T010a ATTEMPT enviado
T010a ATTEMPT AUDIT_REJECT: catalogoQuery sin uso (TS6133); las opciones de estado salen de la constante y no del catalogo del servidor
T010a RETRY_1 enviado
T010a RETRY_1 AUDIT_PASS (tsc y eslint limpios)
SUBTAREA NUEVA T010b: NEW_TECHNICAL_BOUNDARY=1 (pantalla NuevoVinculoPage, fichero nuevo)
T010b ATTEMPT enviado
T010b ATTEMPT AUDIT_REJECT: import de @/components/ErrorDeCarga inexistente, ErrorDeCarga sin message, estado detalleNoEditable sin uso. Nota: el puente cambio una linea del fragmento de ejemplo al copiar (declarado por el puente; sin efecto en el fichero objetivo)
T010b RETRY_1 enviado
T010b RETRY_1 AUDIT_PASS (tsc y eslint limpios)
SUBTAREA NUEVA T010c: NEW_TECHNICAL_BOUNDARY=1 (pantalla VinculoPage, fichero nuevo)
T010c ATTEMPT enviado
T010c ATTEMPT AUDIT_REJECT: import de tipo sin uso (TS6196) y contexto posiblemente nulo en el aviso historico (TS18047)
T010c RETRY_1 enviado
T010c RETRY_1 aplicado (tsc y eslint limpios); AUDIT_REJECT por auditoria: migas a /gobierno/identidad/vinculos, ruta inexistente (la lista vive en /gobierno/identidad)
T010c RETRY_2 enviado
T010c RETRY_2 AUDIT_PASS
T010b RETRY_2 enviado (misma miga rota en el formulario)
T010b RETRY_2 AUDIT_PASS
SUBTAREA NUEVA T011a: NEW_TECHNICAL_BOUNDARY=1 (pantalla CategoriasPage)
T011a ATTEMPT enviado
T011a ATTEMPT AUDIT_PASS (tsc y eslint limpios; avisos MATERIAL DECISION de DeepSeek juzgados no materiales: supuestos razonables de presentacion)
SUBTAREA NUEVA T011b: NEW_TECHNICAL_BOUNDARY=1 (pantalla MiContextoPage y registro de rutas)
T011b ATTEMPT enviado
T011b ATTEMPT: router aplicado y conforme; MiContextoPage AUDIT_REJECT: prop message inexistente en LoadingState, PageHeader con breadcrumbs y children (la prop es crumbs, sin children), estado de cuenta etiquetado como situacion de vinculo, encabezado fuera de PageContent
T011b RETRY_1 enviado
T011b RETRY_1 AUDIT_PASS (tsc y eslint del frontend completo limpios)
Fixtures de frontend regeneradas con qa/fixtures_de_frontend.py (artefacto generado, no codigo).
T011a AUDIT_REJECT posterior (Vitest architecture-temporal): fechas formateadas con la zona del navegador en CategoriasPage (ADR-020)
T011a RETRY_1 enviado
T011a RETRY_1 AUDIT_PASS. Frontend: tsc 0, eslint 0, Vitest 133 ficheros 1379/1379
SUBTAREA NUEVA T012a: NEW_TECHNICAL_BOUNDARY=1 (Vitest de VinculosPage)
T012a ATTEMPT enviado
T012a ATTEMPT AUDIT_REJECT: la prueba espera los codigos ACTIVO y VIGENTE y la pantalla muestra sus etiquetas (Activo, Vigente), como pedia el encargo
T012a RETRY_1 enviado
T012a RETRY_1 AUDIT_PASS (7/7)
SUBTAREA NUEVA T012b: NEW_TECHNICAL_BOUNDARY=1 (Vitest de VinculoPage)
T012b ATTEMPT enviado
T012b ATTEMPT AUDIT_REJECT: errores simulados con Error y no ApiError, textos esperados inventados, selectores ambiguos (dos botones Cerrar, dos textos de conflictos), tipos invalidos (avocaciones texto, unidades sin id) y any
T012b RETRY_1 enviado
T012b RETRY_1: 9/11; AUDIT_REJECT: 404 con texto repetido (titulo y estado vacio), cierre sin ifMatch esperado, datos de prueba incompletos para tsc (situacion ACTIVA, ids, CompetenciaIdentidad)
T012b RETRY_2 enviado (ultimo)
T012b RETRY_2: 11/11 en Vitest; AUDIT_REJECT parcial por tsc (3 errores TS2322)
SUBTAREA NUEVA T012b-t: NEW_ROOT_CAUSE=1 (ensanchamiento del literal "VIGENTE" a string en una constante compartida sin anotacion; ningun rechazo anterior lo trato). PREVIOUS_SUBTASK=T012b, PREVIOUS_ROOT_CAUSE=campos y valores inventados; EVIDENCE=tsc TS2322 en lineas 89, 134, 161
T012b-t ATTEMPT enviado
T012b-t ATTEMPT AUDIT_PASS (bloque completo aunque el informe se trunco; tsc 0, 11/11)
SUBTAREA NUEVA T012c: NEW_TECHNICAL_BOUNDARY=1 (Vitest de NuevoVinculoPage)
T012c ATTEMPT enviado
T012c ATTEMPT AUDIT_REJECT: 5/6; el 422 se simula con un Error falso y no con ApiError; datos de prueba incompletos para tsc (estado, codigo, claves vinculada/vinculado en referencias)
T012c RETRY_1 enviado
T012c RETRY_1: 5/6; el caso 422 revela un defecto de producto: NuevoVinculoPage solo pinta field_errors si code == VALIDATION_ERROR y pierde los del servicio (GOV_IDENTITY_INVALID); tsc: situacion ACTIVO invalida
SUBTAREA NUEVA T010b-v: NEW_ROOT_CAUSE=1 (mapeo de field_errors condicionado al codigo; nunca rechazado antes); EVIDENCE=caso 422 de NuevoVinculoPage.test
T010b-v ATTEMPT enviado
T010b-v ATTEMPT AUDIT_PASS (6/6)
T012c RETRY_2 enviado (situacion ACTIVO invalida para tsc)
T012c RETRY_2 AUDIT_PASS (tsc 0; identidad 24/24)
SUBTAREA NUEVA T012d: NEW_TECHNICAL_BOUNDARY=1 (Vitest de CategoriasPage)
T012d ATTEMPT enviado
T012d ATTEMPT AUDIT_REJECT: 6/10; getByRole("form") sobre formularios sin nombre accesible, texto de titulo repetido (cabecera y migas), datos de prueba incompletos para tsc
T012d RETRY_1 enviado
T012d RETRY_1 AUDIT_REJECT: sigue usando getByRole("form") (dentro de la seccion), el boton de politica se busca antes de que cargue la politica, tsc (rol_id, motivo ausente) y variable sin uso
T012d RETRY_2 enviado (ultimo)
T012d RETRY_2: 8/10; quedan 2 fallos y tsc. Hallado defecto de producto: CategoriasPage solo pinta field_errors con code VALIDATION_ERROR (lineas 131, 179, 224), como T010b-v
T011a RETRY_2 enviado (misma correccion de producto que T010b-v en los tres formularios)
T011a RETRY_2 AUDIT_PASS (tres formularios; pregunta MATERIAL DECISION truncada, sin contenido juzgable)
SUBTAREA NUEVA T012d-g: NEW_ROOT_CAUSE=1 para causas no citadas en los rechazos de T012d: (a) el 409 se simula con Error y no con ApiError; (b) dos campos Motivo coexisten en la seccion de clasificacion cuando el panel de retiro esta abierto; (c) tipos sin motivo en CategoriaRol y en una politica. EVIDENCE=Vitest y tsc tras RETRY_2
T012d-g ATTEMPT enviado
T012d-g ATTEMPT: 4 de 5 bloques aplicados (AUDIT_PASS); bloque 3 AUDIT_REJECT (motivo dentro de historia, no en la politica); quedan el nombre del boton de envio del retiro (Confirmar retiro inventado; el real es Retirar) y motivo en politicaActiva
T012d-g RETRY_1 enviado
T012d-g RETRY_1 AUDIT_PASS
SUBTAREA NUEVA T012e: NEW_TECHNICAL_BOUNDARY=1 (Vitest de MiContextoPage)
T012e ATTEMPT enviado
T012e ATTEMPT: 3/6. Hallado defecto de producto en MiContextoPage: vuelve a enmascarar en el cliente un documento que el servidor ya entrega enmascarado (funcion formatearDocumentoEnmascarado no pedida)
T011b RETRY_2 enviado (mostrar el documento tal como lo entrega el servidor)
T011b RETRY_2 AUDIT_PASS (documento tal como lo entrega el servidor)
T012e RETRY_1 enviado
T012e RETRY_1 AUDIT_PASS. T012 completo: Vitest 138 ficheros, 1419/1419 (+40 de ORG-06); tsc 0; eslint 0
SUBTAREA NUEVA T013: NEW_TECHNICAL_BOUNDARY=1 (E2E Playwright de ORG-06 y axe)
T013 ATTEMPT enviado
T013 ATTEMPT TRUNCADO (finish_reason length a 18000 tokens; limite fijado por Claude): sin auditar
T013 causa real del corte: bucle degenerado (linea repetida) en la salida; RETRY_1 enviado con aviso explicito y max_tokens 24000
T013 RETRY_1 aplicado (539 lineas; tsc y eslint limpios). Primera corrida E2E en chromium
T013 RETRY_1 corrida chromium: 0/3; AUDIT_REJECT: RESPONSABLE omite capacidades del ejemplo (gobierno_cargos view/edit/publish, gobierno_actos view/edit/issue, gobierno_ocupacion:manage) y el alta de cargos responde PERMISSION_DENIED
T013 RETRY_2 enviado
T013 RETRY_2 aplicado; segunda corrida chromium
T013 corrida 2 chromium: 0/3 pero avanza; defectos: (producto) VinculoPage tiene dt/dd fuera de dl (axe dlitem, lineas 444-457); (prueba) codigo VIN-{uuid} supuesto en vez del codigo real; id leido de la URL antes de que la navegacion termine
SUBTAREA NUEVA T010c-a: NEW_ROOT_CAUSE=1 (estructura dl invalida hallada por axe; nunca rechazada)
T010c-a ATTEMPT enviado
T010c-a ATTEMPT AUDIT_PASS (dl valido; Vitest 11/11; tsc 0)
SUBTAREA NUEVA T013-g: NEW_ROOT_CAUSE=1 (codigo de vinculo supuesto como VIN-{uuid}; id leido de la URL sin esperar la navegacion), nunca rechazados en T013
T013-g ATTEMPT enviado
T013-g ATTEMPT AUDIT_PASS (aviso MATERIAL DECISION juzgado falso: el supuesto coincide con las lineas reales 291-292)
T013-g corrida 3 chromium: 0/3, todos defectos de la prueba: (1) getByText exacto sobre un dd que contiene codigo y situacion; (2) espera la palabra solape y el mensaje real es "Ya hay un vinculo activo para la cuenta o el funcionario"; (3) "Cerrar" sin exact pulsa otro boton y el panel no se abre
T013-g RETRY_1 enviado
T013-g RETRY_1 aplicado (3 bloques; la linea 319 del recorrido no se toco)
T013-g corrida 4 chromium: 0/3, defectos de la prueba: getByLabel Fecha ambiguo (casa con "Consultar a la fecha"); ocupacion futura en un cargo que ya tiene titular (409 GOV_ASSIGNMENT_OVERLAP); el usuario de accesibilidad no tiene gobierno_identidad:revoke y no ve el boton Cerrar
T013-g RETRY_2 enviado (ultimo)
T013-g RETRY_2 aplicado
T013-g corrida 5 chromium: 0/3. Defecto de producto: VinculoPage muestra Cerrar con gobierno_identidad:manage en vez de :revoke (la API exige revoke). Defecto de prueba nacido del encargo de Claude: la ocupacion futura usa el cargo emisor y ORG-04 rechaza que un cargo se designe a si mismo (GOV_ASSIGNMENT_ISSUER_INVALID)
SUBTAREA NUEVA T010c-p: NEW_ROOT_CAUSE=1 (capacidad equivocada en la accion Cerrar; nunca rechazada)
T010c-p ATTEMPT enviado
T010c-p ATTEMPT AUDIT_PASS (Vitest identidad en verde)
SUBTAREA NUEVA T013-h: NEW_ROOT_CAUSE=1 (ocupacion futura sobre el cargo emisor viola la regla ORG-04 de autodesignacion; boton Cerrar sin exact en el recorrido); el primer defecto nace del encargo de Claude
T013-h ATTEMPT enviado
T013-h ATTEMPT aplicado
T013-h corrida 6 chromium: el recorrido llega al cierre; quedan "Vinculo cerrado" duplicado (getByText estricto) y la ocupacion revocada sobre el cargo objetivo que ya tiene titular (409). IDE-E2E-03: encabezado del panel presente pero oculto, causa sin determinar (se investiga con evidencia conservada)
T013-h RETRY_1 enviado
T013-h RETRY_1 aplicado; corrida 7 con evidencia local conservada fuera del arbol (se borrara al terminar)
T013-h corrida 7 chromium: IDE-E2E-01 PASA. IDE-E2E-02: revocacion ORG-04 hecha con un usuario sin gobierno_ocupacion:revoke (403). IDE-E2E-03: evidencia conservada: el panel esta abierto (region Cerrar vinculo en el arbol), el indicador h2 se reporta oculto a 320 px con el menu lateral desplegado; ORG-04 usa el h1 como indicador del panel
T013-h RETRY_2 enviado (ultimo)
T013-h RETRY_2 aplicado; evidencia local de la corrida 7 borrada
T013-h corrida 8: IDE-E2E-01 pasa. IDE-E2E-02: revoca con la version previa a la activacion (409 STALE, version_actual 2). IDE-E2E-03: pulsa en el menu un enlace a categorias que no existe (categorias se abre desde la lista)
SUBTAREA NUEVA T013-i: NEW_ROOT_CAUSE=1 (version de la asignacion tras activar; navegacion por un enlace de menu inexistente), nunca rechazados
T013-i ATTEMPT enviado
T013-i ATTEMPT aplicado
T013-i corrida 9: IDE-E2E-01 pasa. IDE-E2E-02 (c): espera ver sin ocupacion hoy, pero ORG-04 cuenta completa la fecha final efectiva (la revocacion surte efecto con la eficacia del acto, hoy): hay que consultar a manana. IDE-E2E-03: navega a la URL del backend (API sin /api/v1) en vez de la ruta del frontend
T013-i RETRY_1 enviado
T013-i RETRY_1 aplicado
T013-i corrida 10 chromium: IDE-E2E-01 y 02 PASAN. IDE-E2E-03: axe scrollable-region-focusable en la vista 404 de la ficha a 320 px (zona desplazable sin elementos enfocables)
SUBTAREA NUEVA T010c-x: NEW_ROOT_CAUSE=1 (vista 404 sin salida enfocable; nunca rechazada)
T010c-x ATTEMPT enviado
T010c-x ATTEMPT AUDIT_PASS
T013 corrida 11 chromium: 3/3 PASAN. Siguiente: 3 navegadores x 3 repeticiones, 0 reintentos
T013 CERTIFICADA: chromium, firefox y webkit x3 repeticiones, 0 reintentos: 27/27
SUBTAREA NUEVA T014: NEW_TECHNICAL_BOUNDARY=1 (controles SQL de integridad posteriores a la E2E y su registro)
T014 ATTEMPT enviado
T014 ATTEMPT: 18 controles ejecutan sin error contra el esquema real (runner 3/3, 136 controles); AUDIT_REJECT en ID18: c.hasta >= current_date excluye las categorias ACTIVA con hasta nulo y el control daria siempre 0 (verde falso)
T014 RETRY_1 enviado
T014 RETRY_1 AUDIT_PASS (runner 3/3; 136 controles)
SUBTAREA NUEVA T015: NEW_TECHNICAL_BOUNDARY=1 (especificacion de mutantes M1-M20 sobre anclas elegidas y verificadas por Claude; el mutante lo redacta DeepSeek)
T015 ATTEMPT enviado
T015 ATTEMPT AUDIT_PASS: 20 mutantes, todas las anclas unicas y cada cambio coherente con su descripcion
T015 ronda 1: 15 KILLED, 5 SURVIVED (M1, M2, M6, M8, M10). M8 EQUIVALENTE justificado: ocupaciones_de_funcionario filtra desde <= fecha en SQL y situacion_en solo da FUTURA si fecha < desde. M1, M2, M6, M10: pruebas ausentes (escritura cruzada de ente, cuenta sin acceso, autoactivacion por el registrador, ocupacion revocada en el contexto)
SUBTAREA NUEVA T015r: NEW_TECHNICAL_BOUNDARY=1 (pruebas de refuerzo, fichero nuevo)
T015r ATTEMPT enviado
T015r ATTEMPT AUDIT_REJECT: pytest_plugins sin tests.test_gov_ctl06_hallazgos (fixture gobierno no encontrado)
T015r RETRY_1 enviado
T015r RETRY_1 AUDIT_PASS (4/4 contra el producto)
T015 ronda 2: M1, M2, M6, M10 KILLED con el refuerzo; M8 SURVIVED (equivalente justificado). Total 20: 19 KILLED, 1 EQUIVALENTE, 0 SUPERVIVIENTES
OpenAPI: 14 rutas nuevas de identidad y cambios SoD esperados; defecto: colision de nombre OpcionCuenta con schemas_caja renombra esquemas existentes de TRE-02 (cambio no autorizado)
SUBTAREA NUEVA T002d: NEW_ROOT_CAUSE=1 (colision de nombre de esquema Pydantic en OpenAPI)
T002d ATTEMPT enviado
SUBTAREA NUEVA T016h: NEW_TECHNICAL_BOUNDARY=1 (humo UAT de Gobierno con la pantalla de identidad)
T016h ATTEMPT enviado
T016h ATTEMPT AUDIT_PASS
T002d ATTEMPT AUDIT_PASS (aplicado tras terminar la suite PG; dos bloques)
Suite PG completa r20261108t010708: 2 failed, 4682 passed, 18 skipped. Fallos: test_read_catalog_completeness y test_pgs_26
SUBTAREA NUEVA T002e: NEW_ROOT_CAUSE=1 (GET /gobierno/identidad/mi-contexto, sin capacidad por diseño, sin clasificar en el guardián del catálogo de lecturas)
SUBTAREA NUEVA T016i: NEW_ROOT_CAUSE=1 (capacidad de bloqueos de PostgreSQL de QA). Medido: DROP SCHEMA completo = 6305 bloqueos con 251 tablas (6132 con 245 en fba4a31); dos solapados = 12609 (12263 en base); techo real medido = 12851 con max_locks_per_transaction=64 y max_connections=100 (nominal 6400); tres solapados fallan en ambos arboles. pgs_26 lanza dos DROP a la vez: margen ~240 bloqueos; pasa aislada 3/3 en ambos arboles y falla dentro de la suite
T002e ATTEMPT enviado
T002e ATTEMPT AUDIT_PASS (guardian del catalogo de lecturas en verde)
T016i ATTEMPT enviado
T016i ATTEMPT AUDIT_PASS
SUBTAREA NUEVA T016j: NEW_ROOT_CAUSE=1 (error nuevo de Mypy: variable politica reutilizada con dos tipos en _objeto_desde_evento)
T016j ATTEMPT enviado
T016j ATTEMPT AUDIT_PASS (mypy sin errores nuevos)
SUBTAREA NUEVA T016k: NEW_ROOT_CAUSE=1 (auditoria enlaza la politica de identidad a una ruta inexistente; la exigencia vive en la pantalla de categorias). Hallado por Claude al auditar rutas; ninguna prueba lo cubria
T016k ATTEMPT enviado
T016k ATTEMPT AUDIT_PASS (prueba r5 verde; roja con la ruta antigua)
Suite PG r20261108t121011: 31 failed, 4654 passed. 30 de copia/restauracion por error del montaje de Claude (guion sin KONTROL_PG_BIN_DIR: "No se encontro pg_dump"); no son defectos. SQLite r20261108t132106: 2793 passed, 1910 skipped, rc 0
SUBTAREA NUEVA T016l: NEW_ROOT_CAUSE=1 (CTL-10 activar sin capturar IntegrityError: dos activaciones simultaneas dan 500 en lugar de 409). REGRESSION_REPRODUCED=1: arbol actual 1/12 aislada y 1 en la suite; service_cierres sin cambios en el ciclo; ORG-06 alarga la ventana con consultas SoD. Base: 60 repeticiones en curso
T016l ATTEMPT enviado
T016l ATTEMPT aplicado; AUDIT_REJECT: cc01b falla por CheckViolation en el UPDATE rival, igual con y sin el try (prueba no discriminante). Causa: el encargo de Claude omitio los campos que exige la restriccion para VIGENTE
T016l RETRY_1 enviado
T016l RETRY_1 AUDIT_PASS (cc01b verde con la correccion; roja sin ella por UniqueViolation; fichero 5/5)
Control base fba4a31 cc01 x60: base pass=55 fail=5
Atribucion cc01 corregida: la base falla 5/60 y el arbol actual fallaba 1/12; defecto latente de CTL-10 anterior a ORG-06, no regresion del ciclo. La hipotesis de ventana ampliada por ORG-06 queda descartada
Suite PG sobre el arbol final interrumpida a peticion de la duena (traslado); sin resultado, se relanza al retomar
Retomado tras reinicio (2026-11-08 16:25): PG de QA reaprovisionado; se relanzan PG y SQLite sobre el arbol final
PRODUCT-FIRST OVERRIDE de la duena (2026-11-08): suites completas detenidas; certificacion razonable de la vertical; lo exhaustivo pasa a FINAL_GOVERNMENT_CERTIFICATION
Backend dirigido en PostgreSQL (Gobierno, copias, guardianes, migraciones): 827 passed, 0 failed
E2E representativa chromium: IDE-E2E-01 y 03 pasan; 02 falla con GOV_ASSIGNMENT_ACT_INVALID
SUBTAREA NUEVA T016m: NEW_ROOT_CAUSE=1 (E2E calcula ayerC con fecha UTC menos un dia: pasa solo entre 00 y 04 UTC, cuando equivale a hoy en Caracas). Defecto de la prueba; el servicio rechaza correctamente
T016m ATTEMPT enviado
T016m ATTEMPT AUDIT_PASS; E2E representativa chromium 3/3, 0 reintentos
Convergencia: 0 hallazgos sobre el arbol final
```
