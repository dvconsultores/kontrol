# GOV-TRE-02 · registro de intentos (NC-ORCH-01)

Máximo 2 intentos semánticos por subtarea. Tras el segundo: dividir, rediseñar o bloquear.

| TASK_ID | ATTEMPT_1_RESULT | ATTEMPT_2_RESULT | POST_ATTEMPT_2_DECISION |
|---|---|---|---|
| T005 | REJECT: faltaba el texto real de los ficheros; el SEARCH de `mfa_policy` sustituía cuentas | pendiente | — |
| T015 | REJECT: firma de `accion` inventada; RV-03 sin línea en mayo; RV-12 con SQL inválido daría verde falso; fecha fija | pendiente | — |
| T018 | REJECT: firma de `accion` inventada; rutas y aserciones flojas | pendiente | — |
| T024 | REJECT: POST de línea confundido con PATCH; `accion` como detalle; cabeceras dentro del hilo | pendiente | — |
| T007 | REJECT: forma de catálogo y permisos supuesta, `skip` encubierto, cuenta válida entre las inválidas, If-Match mal enviado | pendiente | — |
| T023 | REJECT: firmas supuestas; SG-02 contra contrato; forma de CTL-04 y SoD supuesta | pendiente | — |
| T009 | REJECT: importa nombres de esquemas supuestos; falta `RubroIn` | pendiente | — |
| Rediseño | Tras los primeros rechazos se separa T007H (ayudantes) para que cada suite cite código real | — | — |
| T002 | REJECT: disparadores incondicionales (bloquean borradores); SEARCH con una clase inexistente; constante sin uso | pendiente | — |
| T005 (2) | — | PARCIAL: bloques correctos salvo SoD, con `crea_objeto` invertido | SPLIT: T005b solo para el proceso SoD |
| T007H | REJECT: llamada espuria en cerrar_regla, try/except oculto, cuenta de más, imports | pendiente | — |
| T002 (2) | — | PARCIAL: disparadores correctos; check de activación y único de código erróneos | SPLIT: T002c, corrección acotada |
| T008 | REJECT: atributos inexistentes (registered_by, registered_at, linea.item); entradas tratadas como dict | pendiente | — |
| T003 | REJECT: creada antes del modelo final; no puede coincidir con él | pendiente | — |

## Segundos intentos y decisiones (NC-ORCH-01)

| Tarea | Intento 1 | Intento 2 | POST_ATTEMPT_2_DECISION | Subtareas nuevas |
|---|---|---|---|---|
| T007H | rechazado (formas supuestas) | aceptado | n/a | — |
| T004 | aceptado | — | n/a | T004b (detalle de historia como objeto) |
| T002 | rechazado (disparadores) | parcial | SPLIT | T002c |
| T005 | rechazado (sin texto real) | parcial | SPLIT | T005b |
| T003 | rechazado (anterior al modelo) | pendiente de certificar en base nueva | — | — |
| T009 | rechazado (nombres supuestos) | parcial: import de User | SPLIT | T009c |
| T008 | rechazado (registered_by, dict) | rechazado: atributos inexistentes, estado de programa y versión confundidos, fórmula doble | SPLIT + REDESIGN | T008a, T008b, T008c, T008d, T008e |
| T007 | rechazado | rechazado: imports y formas | REDESIGN (corrección acotada) | T007R |
| T015 | rechazado | rechazado | REDESIGN (corrección acotada) | T015R |
| T018 | rechazado | rechazado | REDESIGN (corrección acotada) | T018R |
| T023 | rechazado | rechazado | REDESIGN (corrección acotada) | T023R |
| T024 | rechazado | rechazado | REDESIGN (corrección acotada) | T024R |

Ninguna subtarea original tuvo tercer intento. Cada subtarea nueva tiene alcance propio y máximo dos intentos.

## Subtareas nuevas tras dividir o rediseñar

Cada una con su propio límite de dos intentos. `—` = no hizo falta segundo intento.

| Subtarea | Origen | Intento 1 | Intento 2 |
|---|---|---|---|
| T008a..d | T008 SPLIT | parcial (defectos concretos) | aceptado |
| T008e | T008 SPLIT | rechazado por encargo incompleto | aceptado |
| T008f | mypy | parcial | aceptado |
| T008g | mypy, import | aceptado | — |
| T007R | T007 REDESIGN | rechazado (SEARCH no único) | rechazado |
| T007S1..S5 | T007R SPLIT | aceptado | — |
| T015R, T018R, T023R | REDESIGN | parcial | aceptado |
| T024R | REDESIGN | aceptado | — |
| T015S/T, T018S, T023S, T024T | fallos al ejecutar | aceptado | — |
| T023U | mutante CJ-M04 | rechazado (check de la base) | aceptado |
| T009c, T009d, T009e | API | aceptado | — |
| T004b, T004c, T005c | esquemas y catálogo | aceptado | — |
| T010, T010b, T010c | contrato frontend | T010 parcial (defecto del `?` hallado por PP-04) | — |
| F11, F12, F14a, F14b, F22, F13 | pantallas | rechazado (tipos supuestos) | aceptado |
| F11c | filtros | parcial | aceptado |
| F13c | mes mal indexado, hallado por prueba | aceptado | — |
| U11..U14, U22 | pruebas de pantallas | parcial | subtareas U13c..U13e, U14b, U22b |
| T025 | delta OBS-TRE01-E2E-01 | parcial | aceptado (F25c tras tsc) |
| T026 | E2E | rechazado | aceptado; E1..E5 tras ejecutar |
| T027 | integridad | colisión de identificadores por encargo | T027b, 2 intentos |
| T034 | pruebas SG-15, SG-16 | aceptado | — |
| T035 | «—» en versión vigente | aceptado | — |
| T037 | HallazgoPage y HLP-03b | producto aceptado, prueba rechazada | prueba aceptada (T037T) |
| T038a | diagnóstico de E2E | rechazado (escritura no síncrona, enmascarado incompleto) | aceptado; firma de fixture errónea, por encargo ambiguo |
| T038b | marcas y aserción exacta en PF-E2E-02 | aceptado | — |
| T038c | SPLIT de T038a: firma de la fixture | aceptado | — |
| T038d | registro del proxy | rechazado (sin correlación, objeto equivocado) | aceptado; retirado por enmascarar el fallo |
| T038e | sincronización de PF-E2E-02 | aceptado | — |
| T038f | laboratorio | fallo al arrancar | aceptado |
| T038g | proxy keep-alive | aceptado; hipótesis refutada y revertido | — |
| T038h | preferencia en el laboratorio | rechazado (formato) | aceptado |
| T038i | preferencia de Firefox en la E2E | aceptado | — |
| T038j | retirada de marcas | aceptado | — |

Ningún identificador de tarea o subtarea tuvo tercer intento. MAX_SEMANTIC_RETRIES_PER_SUBTASK_OBSERVED = 2.

## Excepciones de formato y aplicación mecánica (hechas por Claude, sin contenido semántico)

- `ruff --fix` de orden de imports (`I001`) y de un import sin uso en `tre02_ayudantes.py`.
- Sangría de 8 a 4 espacios en un bloque de `service_auditoria` (T005), para que coincidiera con el fichero.
- Composición de las cuatro partes de `service_caja.py` en un solo fichero.
- Mi herramienta de sustitución quitó un decorador de ruta y, en otro paso, dejó dos líneas desplazadas; se restauraron con el texto exacto previo o la propuesta de DeepSeek.
- Retirada mecánica de `_delete_con_version` y `_patch_con_version` en la suite de programa, que T007R pedía quitar.
- `aplicar.py --omitir` numera desde 1: en T037 se aplicó por error el bloque de prueba rechazado; se restauró el fichero desde HEAD, que no tenía cambios del ciclo, y se aplicó el bloque correcto.
- T038: `T038a2` y `T038d2` salieron con `ENV_FILES` distinto de 0. Eran `process.env.*`, sin valores. El de `T038a2` lo leí después de lanzar la llamada: orden incorrecto, sin exposición. Los demás se leyeron antes.
- T038: la retirada de `helpers/sesion.ts` y `diagnostico.ts`, y las reversiones de `vite.config.ts`, se hicieron restaurando desde Git, sin autoría.
- El laboratorio y las sondas viven fuera del repositorio. Los registros `MOZ_LOG` se borraron sin imprimirlos.
