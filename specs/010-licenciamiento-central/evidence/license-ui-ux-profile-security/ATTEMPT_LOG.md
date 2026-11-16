# Registro de intentos · «Mi licencia» real + perfil fail-closed + frontera backend por perfil

Modelo: `deepseek-v4-pro` en todas las llamadas.
- Tope global: 8 llamadas (objetivo 3..5).
- Máximo 2 reintentos por subproblema real.
- OWNER_EXCEPTION_INHERITED=0. **OWNER_EXCEPTION_USED=2** (llamadas 9 y 10, autorizadas por la dueña tras la PG completa).

| # | Encargo | Subproblema | Tokens (entrada / salida) | USD | Resultado de la auditoría |
|---|---|---|---|---|---|
| 1 | E1 | Backend: `require_enterprise_surface`, tabla de routers, reverificación de `minimum_version`, pruebas RVR-MV, PENF y MVR | 5.412 / 6.272 | 0,0077 | 12/15 aplicados. REJECT: SEARCH de cuatro decoradores no contiguos (0 coincidencias); `_caso` llamado con una firma inexistente y `.hex()` sobre una cadena hex; MVR-01 enviaba el payload sin firmar |
| 2 | E1r1 | Reintento 1 de E1 | 4.346 / 3.721 | 0,0050 | 8/8 aplicados. Defectos: `calls` acumulado entre rutas; penf_05 sin rutas, porque FastAPI 0.141 no aplana `app.routes` (diagnóstico de Claude: `iter_route_contexts`); rvr_12 fijaba el conjunto FAILURES antiguo (omisión del diseño de Claude) |
| 3 | E2 | Frontend: `licencia-presentacion`, «Mi licencia» rediseñada, `ActivarLicencia` en los seis modos y sin permiso, perfil fail-closed | 9.842 / 8.571 | 0,0116 | 14/16 aplicados. REJECT: SEARCH de `rawModules` inventado; bloque de imports con SEARCH inexistente y REPLACE vacío; faltaba el import de `usePerfilDeInstalacion` |
| 4 | R2 | Reintento 2 (último) de E1 + reintento 1 de E2 | 1.670 / 1.389 | 0,0019 | 6/6 aplicados. penf_05: faltaban en la lista esperada los prefijos de estructura de almacenes (lista del diseño de Claude) → tarea dividida en E3 |
| 5 | E3 | Pruebas Vitest + tarea dividida de penf_05 | — / — | — | **Sin respuesta**: el MCP abortó tras 2045 s sin progreso. Se cuenta como llamada consumida |
| 6 | E3 (reenvío) | El mismo encargo, sin cambios | 5.581 / 7.186 | 0,0086 | 21/21 aplicados (un bloque repetido, aplicado mecánicamente a sus 8 apariciones). Defectos: `cleanup` sin importar, `renderRuta` inexistente, `render` sin QueryClientProvider, tabla de textos con `descripcion = titulo`, `sort` sobre un array readonly, botón «Validando…» |
| 7 | F | Reintento 1 de E3 + E4 (E2E de cuatro pruebas e inventario de `ejecutarPython`) | 7.457 / 6.793 | 0,0090 | 11/11 aplicados (`montar()` mecánico en 5 apariciones). Vitest en verde. E2E: modo estricto en `role=status` (aviso inline + notificación); las capturas se perdían con la limpieza MFA |
| 8 | G | Reintento 2 de E3 (carrera de LICUX-07) + reintento 1 de E4 | 1.435 / 800 | 0,0012 | 4/4. Vitest 2304/2304. E2E 4/4 |
| 9 | E5 | **Excepción 1 de la dueña.** Regresión de la PG completa: la guarda OAS-14 (`_matriz_runtime`) rechazaba toda dependencia añadida en `include_router`. Se admite solo la frontera de superficie (`kontrol_surface`) que no llega a `get_current_auth`; pruebas OAS-14b/c/d | 2.445 / 1.329 | 0,0022 | 4/4 aplicados (bloques sin ruta: un único fichero objetivo, asignados por contenido). OAS-14 siguió rojo por el diseño de Claude: pidió `originales + extra` y FastAPI ordena `extra + originales` |
| 10 | E5r1 | **Excepción 2 de la dueña.** Reintento 1 de E5: originales como sufijo; 14b con una ruta que tiene dependencia propia; anotaciones | 1.315 / 1.235 | 0,0016 | 4/4 aplicados (marcadores de 7 caracteres ausentes, normalizados). `test_openapi_security.py` 46/46. ruff B010 por el `setattr` que pidió el encargo: corregido con `ruff check --fix --select B010` (herramienta) |

**Total:** 10 llamadas, 8 del tope y 2 autorizadas por la dueña. 39.503 tokens de entrada y 37.296 de salida (sin contar la llamada 5, que no informó uso). **USD 0,0489.**

## Diagnósticos de Claude (causa raíz, sin escribir código)

- **La UI no visible para la dueña:**
  - las pilas UAT 16773 (b98d4e6) y 16873 (2d74eef) son anteriores a 6befc1c;
  - además, en el HEAD, `MODOS_DE_ACTIVACION` excluía FULL_ACCESS, que es el modo de ambas pilas.
- **FastAPI 0.141:** `app.routes` contiene `_IncludedRouter`. Las rutas efectivas se obtienen con `fastapi.routing.iter_route_contexts(app.routes)`, cuyos contextos traen `.path`, `.route` y `.dependant`.
- **E2E:** la limpieza de material MFA del ejecutor canónico borra la carpeta de cada prueba. Las capturas van a `project.outputDir/evidencia-licux/`.

## Retoques mecánicos de Claude (FORMAT_ONLY_EDITS)

1. E3: un SEARCH sin sangría con 8 apariciones (clic de confirmación del diálogo), aplicado a todas con `--todas`.
2. F: `render(<MiLicenciaPage />)` → `montar()` en sus 5 apariciones, con `--todas`.
3. E5: ruta añadida delante de cada bloque (un único fichero objetivo).
4. E5r1: marcadores `SEARCH`/`REPLACE` desnudos normalizados a los de 7 caracteres; contenido intacto.
5. E5r1: `ruff check --fix --select B010` (autocorrección de la herramienta: `setattr` constante → asignación).

## Defectos de diseño de Claude

- No previ que rvr_12 fija el conjunto FAILURES.
- Lista de prefijos de penf_05 incompleta (estructura de almacenes).
- No previ que la guarda OAS-14 prohíbe dependencias de inclusión (hallado en la PG completa), y en E5 supuse mal el orden de las dependencias (`extra + originales`) y pedí un `setattr` que ruff prohíbe.
- No previ la doble `role=status` (aviso inline y notificación), ni que la limpieza MFA borra las capturas.

CLAUDE_SEMANTIC_CODE_WRITTEN=0 · CLAUDE_SEMANTIC_TESTS_WRITTEN=0 · CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0 · CLAUDE_SEMANTIC_QA_WRITTEN=0
