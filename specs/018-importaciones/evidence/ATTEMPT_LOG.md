# ENTERPRISE-DELIVERY-AND-IMPORTS-018 · registro de intentos

Llamadas secuenciales; todo el código lo propone DeepSeek salvo resolución mecánica de conflictos de la fusión.

| Subtarea | Intento | Modelo | Coste | Resultado |
|---|---|---|---|---|
| EDI-A migración de fusión | ATTEMPT | flash | $0,000237 | AUDIT_PASS |
| EDI-C backend de importaciones | ATTEMPT | pro | $0,016642 | AUDIT_REJECT parcial: nombre con `select("name")`, ids `UUID` contra columnas de texto, imports, duplicados, SEARCH sin coincidencia. Informe final truncado |
| EDI-C | RETRY_1 | pro | $0,008753 | Corrige `require_write_allowed` ausente en mutaciones, ids como cadena y consultas de nombre. **Desviación:** tres SEARCH idénticos de coincidencia múltiple aplicados como uno global; un bloque de prueba inventado descartado. `api.py` de ATTEMPT retirado para que entrara el nuevo |
| EDI-C | RETRY_2 | flash | $0,000117 | Sangría en `database.py` y restos en pruebas. Bloques dictados por Claude. Presupuesto cerrado |

### EDI-D (nueva subtarea)
- PREVIOUS_SUBTASK: EDI-C, presupuesto cerrado
- NEW_ROOT_CAUSE: MODELO_NO_CARGA. `app.core.scopes` no existe (es `app.core.scope`), `__table_args__` duplicado e ids anotados como UUID. El brief de Claude no dio la ruta real
- NEW_TECHNICAL_BOUNDARY: solo `imports/models.py`
- EVIDENCE: ModuleNotFoundError en las 9 pruebas; mypy 156
| EDI-D | ATTEMPT | flash | $0,000103 | Bloques dictados por Claude. AUDIT_PASS |
| EDI-D | RETRY_1 | flash | $0,000532 | Corrige el filtro que vaciaba el listado y pruebas. Bloques dictados por Claude |
| EDI-E pantallas | ATTEMPT | pro | $0,013505 | AUDIT_REJECT: `TextInput` tratado como valor (brief de Claude sin ese contrato), empresa nula, prueba sin QueryClientProvider. Rutas, menú, filtro y textos de Terceros aplicados |
| EDI-E | RETRY_1 | pro | $0,017724 | Páginas aplicadas; TSC y ESLint limpios. 4 de 7: defecto real, el listado siempre en error |
| EDI-E | RETRY_2 | flash | $0,000158 | Bloques dictados por Claude. Presupuesto cerrado |
| EDI-F E2E de importaciones | — | — | — | Llamada solo de pruebas 1 de 2 permitidas; lleva también el selector pendiente de EDI-E, con presupuesto cerrado |
| EDI-F | ATTEMPT | flash | $0,000766 | Aplicada. Corrida en Chrome real: destapó los defectos de EDI-G. Sonda temporal local, sin commitear |

### EDI-G (nueva subtarea)
- NEW_ROOT_CAUSE: DEFECTOS_VISIBLES_SOLO_EN_NAVEGADOR: expediente sin refrescar tras cada acción, avisos sin `role="alert"` y persistentes, campos sin etiqueta visible
- NEW_TECHNICAL_BOUNDARY: integración real de interfaz y backend
- EVIDENCE: la red muestra PATCH 200 sin GET posterior del detalle
| EDI-G | ATTEMPT | flash | $0,001263 | Bloques dictados por Claude tras depurar en navegador. Duda de DeepSeek resuelta: el prefijo coincide. AUDIT_PASS |
| EDI-G | RETRY_1 | flash | $0,000173 | Quita la key que borraba lo escrito; hallado por la E2E real. Bloques dictados por Claude |

| EDI-H semilla documental | ATTEMPT | flash | $0,000180 | Declara ImportDocument en la guarda N9. Bloques dictados. AUDIT_PASS |

| EDI-I segunda fusión Alembic | ATTEMPT | flash | $0,000224 | `public-upstream` avanzó con CTL-02. AUDIT_PASS |

## Totales

14 llamadas · $0,060877. Llamadas solo de pruebas: 2 (EDI-F, EDI-H). Reintentos: 6.
**Declaración:** EDI-C RETRY_2, EDI-D y su RETRY_1, EDI-E RETRY_2, EDI-G y su RETRY_1, y EDI-H llevan bloques dictados literalmente por Claude tras depurar; DeepSeek los transcribió. La resolución de conflictos de la fusión y las declaraciones de cabeza y contador las aplicó Claude como ajuste mecánico.

## Ciclo 2

Sin código dictado: los briefs dan contratos e invariantes, y el código existente solo como contexto. Agotados los intentos, Claude rediseña.

| Subtarea | Intento | Modelo | Coste | Resultado |
|---|---|---|---|---|
| IMP2-A backend | ATTEMPT | pro | $0,007369 | Respuesta incompleta: solo `models.py`, correcto y aplicado |
| IMP2-A | RETRY_1 | pro | $0,023251 | AUDIT_REJECT: formato Markdown sin SEARCH, `resources.py` inventado, `except Exception`, `float` en dinero, `date.today()`, pruebas sin `reloj_mfa` |
| IMP2-A | RETRY_2 | pro | $0,015155 | Migración, catálogo, registro documental y servicio aplicados. Primer envío no llegó a DeepSeek: el brief de 131 KB era excesivo para el puente, sin coste ni reintento consumido; se redujo el alcance. Presupuesto cerrado |

### IMP2-B (rediseño tras cerrar IMP2-A)
- NEW_TECHNICAL_BOUNDARY: API HTTP, guardas y pruebas, que IMP2-A ya no cubre
- NEW_ROOT_CAUSE: defectos de la auditoría del servicio: vínculo sin comprobar dirección, `role` ausente, hitos con id de usuario
| IMP2-B API, guardas y pruebas | ATTEMPT | pro | $0,008064 | Solo `api.py`, aplicado; el modelo paró ahí |
| IMP2-B | RETRY_1 | pro | $0,011764 | AUDIT_REJECT parcial: rol inventado AGENTE_ADUANAL, 13 de 25 bloques sin coincidencia. Aplicados los válidos: dirección OUT, usuario real, funciones nuevas |
| IMP2-B | RETRY_2 | pro | $0,012711 | Aplicados: `update_file`, candidatos, anotaciones y guardas. Rechazados: exigir usuario al agente con columnas inexistentes y semilla inválida. **STOP**: rediseño |

### IMP2-C (rediseño tras STOP de IMP2-B)
- NEW_ROOT_CAUSE: dos errores de tipos en el servicio y pruebas escritas sobre modelos y claves que no existen
- NEW_TECHNICAL_BOUNDARY: entrega acotada: dos líneas de servicio, semilla n9 y un fichero de pruebas
| IMP2-C | ATTEMPT | pro | $0,004769 | Tres bloques de producto aplicados; el de pruebas llegó vacío |
| IMP2-C | RETRY_1 | pro | $0,009769 | Pruebas 1 de 2. Aplicado para medir |
| IMP2-C | RETRY_2 | pro | $0,006100 | Pruebas 2 de 2. 8 bloques aplicados, 3 rechazados (rol `AGENTE` inventado). **STOP y sin más llamadas de solo pruebas.** Se retiraron mecánicamente 5 pruebas sin ayudante válido; quedan 6 negativas de dinero, aislamiento y estado. Claude verificó esas reglas con una sonda temporal sin commitear, que descubrió que abrir una corrección fallaba por la clave `correction_id` fuera del catálogo |

### IMP2-D (siguiente entrega de producto)
- NEW_TECHNICAL_BOUNDARY: pantallas del ciclo 2
- Lleva además dos arreglos de producto hallados por la sonda y por mypy
| IMP2-D | ATTEMPT | pro | $0,020268 | AUDIT_REJECT parcial. Aplicados: tipos, selector de órdenes, selector de tercero, catálogo y `target_model`. Rechazados: las cuatro secciones nuevas y la composición: ocultaba negociación y orden en NEGOTIATING, rutas de Finanzas inventadas (el brief de Claude no las listaba), falta `apiFetch` en el resumen, instante sobre fecha de negocio, UUID libre en Documento relacionado, sin anclas ni solo lectura. Tres ficheros sin coincidencia porque el brief no los incluía |
| IMP2-D | RETRY_1 | pro | $0,020945 | Aplicado para medir. Un primer envío de 79 KB no llegó a DeepSeek (puente cortado, clasificador), sin coste ni reintento consumido; se redujo a 52 KB sin los intentos previos, que los motivos del rechazo cubrían |
| IMP2-D | RETRY_1, auditoría | — | — | AUDIT_REJECT parcial. Rutas corregidas. Rechazado: no compila, sin formulario de embarque ni confirmar despacho, sin anclas, candidatos sin carga inicial, resolución compartida, estados crudos, UUID en etiqueta, prueba sin el caso pedido, E2E con identificador inexistente |
| IMP2-D | RETRY_2 | pro | $0,017174 | Aplicado para medir. Presupuesto de la subtarea cerrado |
| IMP2-D | RETRY_2, auditoría | — | — | **STOP.** Sigue sin compilar: la rama de Documentos no se corrigió. Resto aplicado |

### IMP2-E (rediseño tras STOP de IMP2-D)
- NEW_ROOT_CAUSE: fallos de compilación e integración medidos con TSC y Vitest; ninguno es de diseño. El brief de IMP2-D daba demasiado a la vez
- NEW_TECHNICAL_BOUNDARY: entrega mínima con fragmentos literales y un defecto por línea, sin reescribir secciones
- EVIDENCE: TS1005 en Documentos, TS2307 del import del selector, 6 de 9 en Vitest. Claude midió con arreglos temporales de sintaxis e import, retirados antes del envío
| IMP2-E | ATTEMPT | flash | $0,001161 | AUDIT_REJECT parcial. Aplicados E3 a E7, E10 y E11. Rechazados: SEARCH no contiguo (E2), Documentos sin arreglar (E1), estados inventados (E8), bloque malformado (E9) |
| IMP2-E | RETRY_1 | flash | $0,000224 | Tres arreglos restantes. E8 se retiró: era diagnóstico erróneo de Claude, la consulta ya tenía `enabled` |
| IMP2-E | RETRY_2 | flash | $0,000401 | Aplicado. Los SEARCH ampliados y el motivo los dio Claude como contexto existente; dos líneas de cierre y retirada |
| IMP2-E | ajuste mecánico | Claude | — | **STOP de IMP2-E.** Claude repuso la línea existente de apertura de la lista que el bloque D había eliminado: restauración de sintaxis sin efecto semántico |

### IMP2-F (rediseño tras STOP de IMP2-E)
- NEW_ROOT_CAUSE: RETRY_2 de IMP2-D retiró el formulario de hitos; hallado por Claude al recorrer el flujo en Chrome con una copia temporal de la E2E, sin commitear
- NEW_TECHNICAL_BOUNDARY: una sección de producto y adaptar las pruebas a la pantalla real. No es llamada de solo pruebas: lleva el defecto de producto
| IMP2-F | ATTEMPT | pro | $0,007529 | Aplicado para medir |
| IMP2-F | RETRY_1 | pro | $0,003544 | Aplicado para medir |
| IMP2-F | RETRY_2 | flash | $0,000137 | **STOP.** SEARCH no contiguo por un brief de Claude con fragmentos sueltos; el texto de sustitución se aplicó sin alterar en los cuatro puntos, y se declara como desviación |

### IMP2-G (rediseño tras STOP de IMP2-F)
- NEW_ROOT_CAUSE: defectos hallados en la revisión visual a 390 px: menú lateral fijo en todos los módulos, fecha de negocio mostrada como instante y un día antes; más el error de mypy dejado por IMP2-E
- NEW_TECHNICAL_BOUNDARY: tres ficheros de producto, ninguno de pruebas
| IMP2-G | ATTEMPT | flash | $0,000297 | Aplicado para medir |
| IMP2-G | ajuste mecánico | Claude | — | Sustitución de la clase de color inexistente `text-primary-600` por el token real `text-brand-600` en los enlaces del módulo; sin cambio de lógica |
| IMP2-G | RETRY_1 | flash | $0,000230 | Estados de finanzas, fila adaptable y rótulos de corrección. Aplicado |

### IMP2-H (subtarea nueva)
- NEW_ROOT_CAUSE: el guarda QC-01 exige `searchUrl` literal y la ruta del selector de órdenes lleva el id en el path; «Cargar más» de Finanzas sustituye en lugar de acumular, hallado por Claude en auditoría
- NEW_TECHNICAL_BOUNDARY: una ruta, su consumo y la paginación de candidatos
| IMP2-H | ATTEMPT | pro | $0,002289 | Ruta fija del selector y paginación acumulada. Aplicado para medir |
| IMP2-H | RETRY_1 | flash | $0,000283 | Traslado de la ruta y mocks. Aplicado |

## Totales del ciclo 2

23 llamadas · $0,173646. Llamadas solo de pruebas: 2 de 2. Reintentos: 14. Sin llamadas en paralelo. Incluye IMP2-M, migración de fusión con PROC-02 de Government ($0,000212, AUDIT_PASS).

**Declaración.** Todo el código de producto y de pruebas lo propuso DeepSeek. Claude hizo estos ajustes mecánicos: reponer una línea de apertura de lista borrada por un bloque, sustituir una clase de color inexistente por el token real, aplicar sin alterar en cuatro puntos el texto de IMP2-F RETRY_2 y en dos los de IMP2-C, retirar 5 pruebas rotas, y regenerar instantáneas y filas de catálogo. En RETRY_2 de IMP2-E y IMP2-H, el brief dio las líneas existentes que debían buscarse y describió el cierre a cambiar; no dictó cuerpos de función. Claude usó sondas temporales sin commitear, ya borradas: backend de reglas (`zz_sonda_ciclo2`) y copias de la E2E para recorrer el flujo en Chrome. Dos envíos no llegaron a DeepSeek por tamaño y no consumieron intento. El ciclo usó ocho subtareas: los rediseños se abrieron con causa nueva registrada.

## Ciclo 3

Tope: 12 llamadas. Diseño: las recepciones del expediente se derivan de `GoodsReceipt.order_id`, sin tablas ni migración.

| Subtarea | Intento | Modelo | Coste | Resultado |
|---|---|---|---|---|
| IMP3-A integración backend | ATTEMPT | pro | $0,008252 | AUDIT_REJECT: sin rutas, sin pruebas, sin `create_file_receipt`, columnas inexistentes |
| IMP3-A | RETRY_1 | pro | $0,013687 | Aplicado para medir |
| IMP3-A | RETRY_1, auditoría | — | — | Claude insertó dos saltos de línea que faltaban tras aplicar. Sigue: pruebas con marcador suelto y duplicadas, auditoría con firma equivocada, `next_action` sin etapa, errores de tipos |
| IMP3-A | RETRY_2 | pro | $0,006198 | AUDIT_REJECT: vallas sin rutas, sintaxis inválida en `after`, SEARCH vacío, bloque idéntico. **STOP** |

### IMP3-B (rediseño tras STOP de IMP3-A)
- NEW_ROOT_CAUSE: un brief con muchos retoques dispersos degrada el formato de respuesta. Claude quitó de las pruebas un marcador suelto y una copia idéntica de función
- NEW_TECHNICAL_BOUNDARY: funciones completas por fichero, con formato de ejemplo por bloque
| IMP3-B | ATTEMPT | pro | $0,005445 | 13 de 16 bloques aplicados; 3 sin coincidencia única |
| IMP3-B | RETRY_1 | pro | $0,004403 | Aplicado para medir |
| IMP3-B | RETRY_1, auditoría | — | — | 8 de 9 bloques aplicados. Mypy en 154. El bloque 5 no coincidía por una línea en blanco; medido con arreglo temporal: 14 de 15 pruebas |
| IMP3-B | RETRY_2 | flash | $0,000486 | Aplicado |
| IMP3-D frontend, enlaces y E2E | ATTEMPT | pro | $0,011400 | 23 de 26 bloques aplicados para medir |
| IMP3-D | RETRY_1 | pro | $0,014559 | AUDIT_REJECT: rutas `modules/importaciones` inexistentes, pruebas vacías, `Number()` prohibido, `Autorizado` con rutas inexactas, bloque mal formado |
| IMP3-D | RETRY_2 | pro | $0,007048 | Solo producto. Aplicado para medir. Claude retiró de la prueba el marcador suelto |

### IMP3-E (rediseño tras STOP de IMP3-D)
- NEW_ROOT_CAUSE: Claude recorrió el flujo en Chrome con una sonda temporal, ya retirada: nombres de campos en el alta de recepción, expediente con datos en caché al volver, enlace de incidencias solo para aceptadas, tipo compartido incompleto. El flujo completo pasó con esos arreglos temporales
- NEW_TECHNICAL_BOUNDARY: esos defectos más las pruebas, con hechos medidos
| IMP3-E | ATTEMPT | pro | $0,007846 | 6 de 11 bloques aplicados; pruebas Vitest con ruta y ayudantes inexistentes rechazadas |
| IMP3-E | RETRY_1 | pro | $0,003291 | Tipos, `onClick`, tarjeta, selectores E2E y pruebas Vitest |
| IMP3-E | RETRY_2 | pro | $0,001961 | **STOP: tope de 12 llamadas.** Aplicados la tarjeta y `.first()` (texto de DeepSeek, también en la segunda línea, porque un bloque iba a otra). Rechazadas 2 pruebas Vitest con ayudantes inexistentes; Claude retiró su andamiaje sin uso. Sus reglas quedan en backend (`extra=forbid`) y en la E2E |
| Cierre | ajustes mecánicos | Claude | — | `API_URL` por la constante existente `API` en la E2E. Smoke temporal, sin commitear, en Chrome: Cargar más, vincular, desvincular, transportista y anular corrección, los cinco correctos |
| Cierre | ajustes mecánicos | Claude | — | Import de tipo sin uso retirado y `onClick={ubicar}` en lugar de `void`, exigido por el tipo de `AsyncButton`. Sin cambio de comportamiento |

## Totales del ciclo 3

12 llamadas (tope 12) · $0,084576. Solo de pruebas: 0. Reintentos: 8. Sin paralelo.

**Declaración.** El código de producto y pruebas lo propuso DeepSeek. Ajustes mecánicos de Claude: saltos de línea tras aplicar, marcadores sueltos y una copia idéntica de función en pruebas, retirar andamiaje sin uso, aplicar en dos líneas el mismo `.first()` de DeepSeek, `API_URL` por `API`, un import sin uso y `onClick={ubicar}`. Dos pruebas Vitest pedidas no entraron por agotarse el tope. Los briefs finales listaron etiquetas y pasos medidos en Chrome como hechos, sin cuerpos de función: es un caso límite que se declara. Sondas temporales en Chrome, sin commitear y borradas: recorrido del flujo y smoke del ciclo 2. Varios rechazos los causó un brief incompleto de Claude, como no incluir los contratos de componentes en IMP3-D.

## Ciclo 4 · gastos (2026-11-09)

12 llamadas (10 + 2 excepciones de la dueña). La llamada 12 cerró los defectos de compilación; la validación destapó que Importaciones no funcionaba sobre PostgreSQL y el ciclo paró.

## Bloque IMP-PG-INTEGRITY-01 (2026-11-09)

Todas con `deepseek-v4-pro`, sin paralelo.

| Tarea | Ranura | Coste | Resultado |
|---|---|---|---|
| IMP-PG-A | ATTEMPT | $0,004288 | Migraciones y cabezas aceptadas. Prueba rechazada: nulos en columnas obligatorias y `raises(Exception)` |
| IMP-PG-A | RETRY_1 (solo pruebas) | $0,004917 | Prueba aceptada, con ramas muertas que se retiran después |
| IMP-PG-B | ATTEMPT | $0,005303 | 11 de 12 bloques aceptados. Rechazado el de ramas muertas (`...` en el SEARCH, por cómo se presentó el contexto) |
| IMP-PG-B | RETRY_1 | $0,003473 | 5 de 6 aceptados. Rechazada la prueba de autor: `func`, `Integer` y `X-User-Id` inexistentes |
| IMP-PG-C | ATTEMPT + RETRY_2 de la prueba | $0,006073 | 9 de 9 aceptados |
| IMP-PG-D | ATTEMPT | $0,001251 | Prueba aceptada. **CSS rechazado:** dejaba visible la notificación más antigua. Presupuesto agotado: no se aplicó |

**Totales:** 6 llamadas (tope 6) · $0,026305 · solo de pruebas: 1 · reintentos: 3.

**Declaración.** Todo el código entregado lo propuso DeepSeek. Claude auditó, aplicó, renombró el fichero de la migración de gastos según su indicación, regeneró instantáneas y escribió esta documentación. **Desviación de §23:** para diagnosticar, Claude escribió en copias fuera del repositorio: mediciones de carga, una espera ampliada, una precarga de prueba y una copia de la E2E para móvil. Nada de eso se entregó, pero el encargo pedía diagnosticar leyendo y ejecutando.
