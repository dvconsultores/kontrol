# PROC-03 · ATTEMPT LOG

ENTRY_HEAD = 5ef11bf2a258354e5e738d29d787af750d7457f4
ALEMBIC_HEAD_BEFORE = 0079_gov_proc02_comisiones
PRESUPUESTO: MAX_DEEPSEEK_CALLS_THIS_CYCLE=12, MAX_TEST_ONLY=2
PROC3-A1 ATTEMPT enviado (llamada 1/12)
PROC3-A1 ATTEMPT (1 llamada: la traza repite el mismo tool_use_id, no hubo duplicado). Modelos/migracion aplicados; AUDIT_REJECT: false() sin importar, rama de auditoria devuelve tupla. PROC3-A2 (incluye RETRY_1 de A1) enviado (llamada 2/12)
PROC3-A2: truncada por longitud (16000); aplicadas entregas 1-3 y servicio hasta editar; ultima funcion incompleta descartada por corte mecanico, sin contenido nuevo. AUDIT_REJECT: 34 errores mypy (atributos inexistentes). NEW_TECHNICAL_BOUNDARY=1 limite de salida. PROC3-A3 enviado con correcciones, resto de acciones y API (llamada 3/12)
PROC3-A3 ATTEMPT aplicado: entrega 1 salvo 2 bloques; AUDIT_REJECT: sin API, atributos inexistentes, if not _abierto siempre rechaza. PROC3-A3 RETRY_1 enviado (llamada 4/12)
PROC3-A3 RETRY_1 aplicado; migracion 6 triggers, arriba/abajo OK PG; AUDIT_REJECT parcial: if not _abierto persiste en 2 sitios, GET con require_write_allowed, catalogo con argumentos, tipos. PROC3-B1 enviado con esas correcciones, contadores, semilla N9 y prueba primaria (llamada 5/12, mixta)
PROC3-B1 aplicado; AUDIT_REJECT: DDL de eventos sobre tabla de folios, constructor con nombres incorrectos (producto). Diagnostico desechable en dos corridas con copia y restauracion exacta, sin autoria: 3/9; 6 fallos de la prueba por campos inventados y binario. PROC3-B1 RETRY_1 enviado (llamada 6/12, mixta)
PROC3-B1 RETRY_1: producto OK; 6/9, tres fallos de la prueba (texto, numero en PATCH, evento ya rectificado). PROC3-C1 enviado con esas correcciones (llamada 7/12, mixta)
PROC3-C1 aplicado (api.ts label y bloque de prueba rechazados: indentacion). PROC3-C2 enviado: ficha, paneles y esas correcciones (llamada 8/12, mixta)
PROC3-C2 truncada por longitud; aplicadas entregas 1-3; pagina parcial retenida fuera del repo. PROC3-C2 RETRY_1 enviado con cola de la pagina y correcciones (llamada 9/12, mixta)
PROC3-C2 RETRY_1: cola ensamblada al texto parcial (union mecanica); bloques sin ruta aplicados anadiendo la ruta, contenido literal; backend 9/9 PG; ficha con 41 errores tsc por nombres de campo inventados. PROC3-D1 (RETRY_2 de C2 + E2E, llamada 10/12, mixta) enviado
PROC3-D1: nombres de campo corregidos en 22/24 bloques; omitio la E2E. PROC3-D1 RETRY_1 enviado (llamada 11/12, mixta). Queda 1.
PROC3-D1 RETRY_1 aplicado. E2E: copia desechable fuera del repositorio y parche temporal restaurado, sin autoria, para ver todos los fallos con una sola llamada restante. Halló: rutas de catalogo y opciones mal formadas (producto), hito pierde fuente (producto), fechas ISO y etiqueta de folio en la cronologia (producto), selectores de la prueba. Tipos y build aparte: backend relacionado 1208/0, vitest 1449/0.
PROC3-D2 enviado (llamada 12/12, mixta; ultima)
PROC3-D2 AUDIT_PASS: 22 bloques aplicados; ruff, mypy 154 sin nuevos, tsc, eslint, build limpios; E2E real EXP-E2E-01 y 02 chromium 2/2, 0 reintentos.
Tras la ultima llamada: test_n9_resourcekinds[GovernmentProcurementFile] falla en la corrida conjunta por colision del codigo N9T-GovernmentP con GovernmentPosition; solo pasa 2/2. Defecto del ayudante de prueba, no del producto (OBS-N9-COLISION-01). Sin llamadas; no se corrige.
Humo: la linea de Expedientes anadida por PROC3-C1 exige ademas un permiso; revertida mecanicamente al contenido publicado (OBS-HUMO-EXP-01).
CIERRE: 12 llamadas (limite 12), con 2 truncadas por longitud y 1 respuesta sin la E2E; 5 reintentos o continuaciones (A1 RETRY via A2, A3 RETRY_1, B1 RETRY_1, C2 RETRY_1, D1 RETRY_1); test-only 0 puras, todas las pruebas fueron en llamadas mixtas; coste en uso.jsonl
Mecanico declarado: ruff --fix (orden de imports, imports sin uso); corte de funcion incompleta de A2; union de la cola de C2 a su parte recibida; ruta anadida a 4 bloques de C2 RETRY_1; reversion del humo; diagnosticos desechables con copia y restauracion.
