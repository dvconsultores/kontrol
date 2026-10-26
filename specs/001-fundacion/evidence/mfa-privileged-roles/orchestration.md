# SHARED-CORE-P0-HARDENING-01 (MFA) — orquestación Claude + DeepSeek

Claude diseñó, redactó los encargos, hizo el EGRESS antes de cada llamada, auditó, aplicó y verificó. DeepSeek escribió todo el
código y todas las pruebas. Claude solo aplicó correcciones de FORMATO automáticas (`ruff --select I --fix`, OD-ORCH-01) sobre
parches ya aceptados semánticamente. Ningún encargo llevó claves, secretos, rutas del home ni datos reales (contraseña y RIF
sintéticos de pruebas; vector público RFC 6238). Un bloque SEARCH sin coincidencia exacta se rechazó siempre; cuando el resto del
parche era correcto, se aplicaron los bloques auditados y el rechazado volvió a DeepSeek como reintento.

| Tarea | Modelo | Resultado de la auditoría | Reintentos |
|---|---|---|---|
| TM-A1 pruebas TOTP / cifrado / configuración + helper | v4-pro | REJECT (línea de depuración, rama muerta, reloj no monótono entre pruebas —contrato de Claude incompleto—, casos de `parse_key_ring`, lint) → c1 PASS | 1 |
| TM-A2 pruebas de política por capacidades | v4-pro | REJECT menor (`__import__`, docstring) → c1 PASS; G00 no sembraba el catálogo → c2 PASS | 2 |
| TM-A3 mundo de pruebas + pruebas de login | v4-pro | REJECT (imports ausentes, `Role.tenant_id` inexistente, B10 contradecía la antirrepetición, sesión arbitraria) → c1; F811 por importar la fixture → c2 (`pytest_plugins`, precedente del repo) PASS | 2 |
| TM-A4 pruebas de gestión / reautenticación / reset | v4-pro | REJECT (D01 con TOTP sobre un usuario sin factor, código muerto) → c1 REJECT (predicado con aridad errónea, alta STANDARD por desafío, D06 STANDARD) → c2 PASS | 2 |
| TM-A5 pruebas de autoridad de sesión | v4-pro | REJECT (función inventada, escritura directa en BD, cookies) → c1 REJECT (`__import__`, variables sin uso) → c2 PASS. Dos bloques con SEARCH idéntico (misma línea en H06 e I05) se aplicaron en orden, uno por ocurrencia; un bloque de imports falló porque Claude había reordenado imports después de que DeepSeek leyera el fichero: se restauró el estado leído y se aplicó (error de Claude) | 2 |
| TM-A6 auditoría / concurrencia / no-bypass / migración | v4-pro | REJECT (rutas erróneas, fixture que salía del `with`, esquema inventado) → dividida en a/b/c/d; a PASS; b/c/d → c2; e (import `os`, URL de la migración, UP037) PASS | 2 |
| TM-A7 ajustes de pruebas tras la implementación | v4-pro | NB01 casaba con `disable_mfa` → renombrado a `remove_own_factor`; D10 con objetivo dentro del techo; I05 alta voluntaria por Bearer → PASS | 1 |
| TM-1 modelo y migración 0058 | v4-pro | parcial: el default de contexto de `family_id` producía NULL (medido) y movía `mfa_enabled` → c1 PASS | 1 |
| TM-2 reloj, TOTP, cifrado, QR, configuración, `segno` | v4-pro | parcial: `match_step` con corte anticipado (contrato de tiempo constante) y lint de `mfa_crypto` → c1 PASS | 1 |
| TM-3a política por capacidades | v4-pro | REJECT (`RolePermission` sin importar) → c1 PASS | 1 |
| TM-3b servicio MFA | v4-pro | REJECT (consulta sobrante en rotura de cristal, `Tenant` de módulo erróneo, salto silencioso en el recifrado, tipos UUID) → c1; causa raíz de ~40 fallos: `from app.core.clock import now as clock_now` congelaba el reloj → envoltorio `clock_now()`; estrechamientos mypy, B904, `_as_utc` (contrato de Claude erróneo) → c2 PASS | 2 |
| TM-4 autoridad de sesión | v4-pro | parcial: `from uuid import uuid4 as uuid` rompía `uuid.uuid4()`; política vía `identity_service.mfa_policy` → c1 PASS | 1 |
| TM-4b `company_context` con la firma nueva | v4-flash | PASS (regresión detectada por la suite) | 0 |
| TM-5a rutas HTTP del MFA | v4-pro | REJECT (`AuthContext` usado como tupla) → c1 PASS (`_sesion_emitida`) | 1 |
| TM-5b reautenticación en 25 rutas | v4-flash | PASS | 0 |
| TM-5c exención de licencia de verify/enrollment/reauth | v4-flash | PASS (rojo → verde medido: `red-tm-5c.txt`) | 0 |
| TM-6 órdenes locales | v4-flash | PASS | 0 |
| TM-7a arnés de sesión de suites amplias | v4-pro | PASS | 0 |
| TM-7b-1..3 migración del login en suites amplias | v4-flash | lote 3: formato no conforme → c1 PASS | 1 |
| TM-7b-4 migración del login (10 ficheros) | v4-flash | formato no conforme → c1: 22/23 PASS, 1 SEARCH sin coincidencia (docstring acortado) → c2 PASS | 2 |
| TM-8a capa de datos MFA del frontend | v4-pro | parcial: `activated_at` no anulable (contrato de Claude incompleto), predicado con tipo estrecho, `mock.calls` sin tipar, aserción de método errónea → c1 PASS | 1 |
| TM-7c fallos de la suite amplia (arnés por motor, reloj por ganchos de sesión, SA-16, cabeza 0058) | v4-pro | parcial: 4/8 bloques PASS; `Engine` importado dos veces y bloques de imports no pedidos → c1: el `pytest_sessionfinish` nuevo REDEFINÍA el existente (limpieza de PostgreSQL; contrato de Claude incompleto) → corregido; diseño del registro inventado (encargo de Claude sin los bloques previos) → c2 PASS | 2 |
| TM-7d contrato OpenAPI de las rutas MFA | v4-pro / v4-flash | contenido PASS; formato (`ruta: ` delante) → c1; dos SEARCH idénticos ambiguos (indicación errónea de Claude) → c2 PASS | 2 |
| TM-8b login con segundo factor, alta, QR y códigos | v4-pro | REJECT (el paso 4 reconfirmaba el alta con el código ya consumido, redirección inalcanzable, `if` vacío, errores por forma, ids perdidos por `FormField`) → c1 (15/16) → c2 PASS; miga a ruta inexistente → subtarea TM-8b-d (en TM-8c-c1) | 2 |
| TM-8c «Verificación en dos pasos», reautenticación, reset administrativo | v4-pro | REJECT (`cerrar` anulaba el resolutor antes de llamarlo: la promesa nunca se resolvía; `require()`, tipo inexistente, foco en Confirmar; 2 bloques con `=======` literal) → c1 (13/15) → c2 PASS | 2 |
| TM-8d descarga local de los códigos sin `createObjectURL` (guarda de descargas del servidor) | v4-flash | PASS | 0 |

Regeneración mecánica (Claude, sin autoría): `resources/frontend/src/tests/fixtures/openapi-routes.json` se regeneró desde
`app.openapi()` con el mismo orden y formato; el diff solo añade 9 entradas (las 8 rutas MFA/reautenticación y `POST /roles`, que
ya existía en `HEAD` y faltaba en el inventario). El aplicador de parches no es atómico: en TM-8c aplicó 6 bloques y se detuvo al
crear un fichero en una carpeta inexistente; Claude creó la carpeta y aplicó el resto omitiendo los ya aplicados (verificado).

## TM-9 · arnés E2E con MFA (OQ-MFA-3)

| Tarea | Modelo | Resultado de la auditoría | Reintentos |
|---|---|---|---|
| TM-9a helper de sesión E2E (TOTP en Node, identidad por worker, cadena de cookie, reautenticación) | v4-pro / v4-flash | REJECT (`import base`, copia local obsoleta tras `iniciarSesion` → paso TOTP repetido, almacén de cookies compartido, `entrar` sin reautenticación, carrera en `waitForResponse`, cuerpo de respuesta en mensajes de error) → c1 parcial (seguía pisando el estado) → c2 PASS; vectores RFC 6238 8/8 | 2 |
| TM-9a-f sesiones reutilizadas para usuarios creados (`sesionDeUsuario`, `entrarComoUsuario`) | v4-pro | PASS (JSDoc duplicado → F2) | 0 |
| TM-9b clones por worker, clave MFA de la corrida, sonda por desafíos | v4-pro | parcial: el guion de siembra filtraba por CÓDIGO de tenant en lugar de id → c1 PASS | 1 |
| TM-9c cabeza 0058 en la línea base; MFA-M04 bajaba con `upgrade` | v4-flash | PASS (M04 era una prueba errónea: el `downgrade` nunca se ejecutaba) | 0 |
| TM-9e pruebas de la corrida al contrato con desafíos y 35 usuarios | v4-flash | PASS → c1 (una aserción más) PASS | 1 |
| TM-9d-1 piloto (helpers, billing, licencia-import) | v4-pro / v4-flash | parcial: `sesionApi` aplicado a usuarios creados → c1 PASS; E2E dirigidas 8/8 y 8/8 | 1 |
| TM-9d-2..9 (44 specs, en lotes) | v4-pro / v4-flash | muchos rechazos parciales: SEARCH sin coincidencia o repetidos, `test.request` inexistente, sesión inventada en `localStorage` (rechazada: el token vive en memoria), tipos importados del helper, `test.skip` alterados (R6), usuarios creados por la vía del worker. Se aplicaron solo los bloques auditados; los restos cerraron en F1a/F1b/F2/F3 | ≤ 2 por lote |

Incidencias del transporte (puente Sonnet → DeepSeek), todas registradas en los informes del puente:
- el puente transcribía a mano ficheros enteros y los truncaba o alteraba; se sustituyó por mensajes COMPUESTOS mecánicamente por Claude
  (encargo + reglas + extractos literales con número de línea, generados por `scratchpad/tools/extracto_login.py`), que el puente solo reenvía;
- las líneas en blanco llegaban como «un espacio»: el aplicador ganó `--normalizar-blancas` (equivalente al sangrado del marco, que la
  política ya permite quitar);
- egress: la contraseña SINTÉTICA de siembra de QA (ya presente en el repositorio) viajó en los mensajes de TM-9b y del lote 6a antes de
  enmascararla; desde entonces todo mensaje la sustituye por `<CONTRASENA_DE_SIEMBRA>` y el aplicador la restituye con `--desenmascarar`
  (solo para casar el SEARCH con el fichero). Ninguna clave, código TOTP, cookie ni token salió nunca.

## TM-10 / TM-11 · E2E dedicada del MFA y documentación de despliegue

| Tarea | Modelo | Resultado de la auditoría | Reintentos |
|---|---|---|---|
| TM-10 `e2e/mfa.spec.ts` (14 casos por la interfaz real) | v4-pro | REJECT (tipos de petición erróneos, ayudas que no casaban con las pantallas reales) → c1 → c2 PASS; la primera corrida dio fallos reales de la prueba | 2 (agotados) |
| TM-10b fallos medidos de la corrida 2 (compuerta de empresa de los usuarios creados, «disponibles: N» en un `span`, el bloqueo se ve en el siguiente login, filas de Usuarios como `div`, dos eventos de auditoría por `request_id`) | v4-pro | PASS; dos bloques compartían líneas → Claude los aplicó en dos pasadas ordenadas (sin tocar su texto) | 0 |
| TM-10c fallos medidos de la corrida 3 (03: «Guarde sus códigos…» es también etiqueta de la lista de pasos y la espera pasaba antes de existir la lista; 05: texto de bloqueo duplicado en el aviso global; 11: **defecto de producto**, el alta con sesión no invalidaba `["security","mfa"]` y la pantalla mostraba «Desactivada» durante el `staleTime`; 14: el menú lateral no plegable comprime el contenido a 320 px → deuda `SHELL-SIDEBAR-NOT-RESPONSIVE`) | v4-flash | REJECT (formato sin marcadores; quitaba `Navigate`, que el fichero usa) → c1 PASS. Mutación de la prueba unitaria nueva (sin la invalidación) → MUERE; fichero restaurado con hash idéntico | 1 |
| TM-10d axe de «/seguridad/mfa» (corrida 4: `target-size` serious en la cabecera del shell a 320 px, deuda SHELL-SIDEBAR-NOT-RESPONSIVE): axe de página completa a 1280 px + axe de `main` a 320 px + scroll a 320 px, sin `disableRules` ni `exclude` | v4-flash | REJECT (SEARCH con 2 coincidencias; el encargo de Claude señalaba líneas no únicas) → c1 PASS | 1 |
| TM-9f la evidencia E2E no conserva material MFA (las trazas de pruebas FALLIDAS llevaban `manual_key`/`recovery_codes` de usuarios efímeros; OQ-MFA-3): `retirar_material_mfa` en `limpiar`, residuo ⇒ corrida SUCIA | v4-flash | bloque 5 sin coincidencia y sin efecto (REPLACE = SEARCH) → omitido; `import zipfile` fuera de orden → `ruff --select I --fix` (formato, OD-ORCH-01); 33b sin `mkdir` de la evidencia (contrato de Claude incompleto; rojo medido) → c1 PASS; `test_e2e_corrida` 35/35 en PostgreSQL | 1 |
| TM-11 despliegue y documentación (`compose.yaml`, `.env.example`, matriz de entorno, runbooks de rotación y rotura de cristal, ADR-004, `instalar.md`, contratos) | v4-pro | PASS | 0 |
| TM-11b ajustes de TM-11 | v4-flash | PASS | 0 |

## Coste (todas las llamadas a `deepseek_chat` del ciclo, leídas de las trazas de los puentes)

193 llamadas · 1 052 108 tokens de entrada · 577 174 de salida · **0,8506 USD** (incluida la Fase A). El coste del puente (Sonnet) no se incluye: lo
factura la sesión de Claude Code.

## Purga de evidencia con material MFA sintético (Claude, 2026-10-26)

Antes de TM-9f, las trazas `trace.zip`, capturas y `error-context.md` de las pruebas FALLIDAS de las corridas E2E de este ciclo (`qa/e2e-runs/`, fuera de Git) contenían respuestas del alta de usuarios efímeros, sobre bases ya eliminadas y con la clave de anillo de cada corrida generada en memoria. Claude eliminó las carpetas `test-results/mfa-*` de tres corridas, los `.playwright-artifacts-*` de la corrida interrumpida y 10 `trace.zip` más con esas marcas; un nuevo barrido de `qa/e2e-runs/` da 0 ficheros. Desde TM-9f la propia corrida las retira y lo anota en el manifiesto (`limpieza.material_mfa`).

Formato al cierre (Claude, OD-ORCH-01): `ruff --select I --fix` sobre 9 pruebas cuyo `from sesion_mfa import login_completo` (TM-7b) había quedado fuera de orden; solo cambia la posición del import; los 9 ficheros se repitieron en SQLite y PostgreSQL.

## Fase A · cierre de gobernanza (2026-10-26)

| Tarea | Modelo | Resultado de la auditoría | Reintentos |
|---|---|---|---|
| TM-EG1 contraseña E2E propia de cada corrida (incidente EGR-MFA-01) | v4-flash | Encargo con el valor histórico enmascarado (`<SEMILLA_HISTORICA>`) y comprobación por programa de que no viajaba. Intento 0: bloques de `e2e_corrida.py` con un espacio de sangría de más → rechazados; se aplicaron los 4 auditados → c1 PASS. La variable local `b` de la prueba 34 oculta el alias de módulo `b` sin efecto (anotado); `test_e2e_corrida` 36/36 | 1 |
| TM-SF1a `mfa_enabled` en el listado de usuarios (MFA-SF-01) | v4-flash | PASS; primero se aplicó solo la prueba y dio rojo (`KeyError: 'mfa_enabled'`), luego el cambio → verde 19/19 | 0 |
| TM-SF1b UI de Usuarios, ayuda del login y aserciones E2E (MFA-SF-01/02) | v4-pro | Primero las pruebas: rojo de 2 (vitest); producto aplicado. Rechazados: espía fuera de ámbito, `setup()` pisaba el mock, dos SEARCH E2E no únicos → c1: formato `<ruta>` y un localizador no acotado (modo estricto) → c2 PASS | 2 |
| TM-DOC1 presupuesto de la carga con analizador real en `documents-a11y` (DOCS-A11Y-UPLOAD-TIMEOUT, preexistente) | v4-flash | PASS (patrón de `documents.spec.ts`) | 0 |
| TM-AUD1 fila de auditoría acotada a `LOGIN_SUCCESS` (dos eventos por `request_id` desde el MFA) | v4-flash | PASS | 0 |
