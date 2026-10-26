# AUTH-PASSWORD-RESET-TOKEN-DISCLOSED — orquestación Claude + DeepSeek (2026-10-26)

**Reparto de trabajo:**
- **Claude:** diseñó (delta `spec002-password-reset-token-delta.md`), escribió cada encargo con su EGRESS comprobado por programa, auditó, aplicó tal cual y verificó.
- **DeepSeek:** escribió todo el código de producto, todas las pruebas, la migración, el frontend, la E2E y la documentación de producto.

**Correcciones de formato de Claude (OD-ORCH-01):** `ruff --select I --fix` en dos ficheros (la prueba TR-A1 y la migración `0059`).

**Valor histórico:** el único valor sensible que aparece en los ficheros tocados es la contraseña sintética histórica de QA. Viajó enmascarado (`<SEMILLA_HISTORICA>`) y el aplicador la restituyó en local.

| Tarea | Contenido | Modelo | Resultado de la auditoría | Reintentos |
|---|---|---|---|---|
| TR-A1 | Pruebas en rojo del contrato (A, B, S, M, L, CLI, OAS) | v4-pro / v4-flash | **c0:** reloj inventado, carpetas con `mkdtemp`, `AuditEvent` de otro módulo, comparación UUID/recuento, columna inexistente → rechazado.<br>**c1:** contenido correcto; quedaban lint (imports, E402, F841).<br>**c2:** imports correctos; el SEARCH de F841 no era único → se divide en TR-A1b → PASS | 2 |
| TR-A1c | Quitar el atributo `details` (contrato erróneo de Claude) | v4-flash | PASS | 0 |
| TR-A2 | Pruebas de la migración `0059` | v4-pro / v4-flash | **c0:** R02 dependía del orden de UUID aleatorios; R04 contradecía el contrato del downgrade; parámetro sobrante.<br>**c1:** contenido correcto sin marco.<br>**c2:** solo marco; contenido idéntico byte a byte → PASS | 2 |
| TR-1 | Modelo y migración `0059` (sello de credencial, `invalidated_at`, `source`, `token_hash` único) | v4-pro / v4-flash | **c0:** salida degenerada (repitió el encargo en bucle).<br>**c1:** contenido correcto; quedaba F841.<br>**c2:** formato `<ruta>` no aplicable → se divide en TR-1c → PASS | 2 |
| TR-5a | Las pruebas que insertan usuarios por SQL en la cabeza necesitan `credential_stamp` | v4-flash | **c0:** formato `<ruta>` (provocado por la redacción del encargo de Claude).<br>**c1:** PASS | 1 |
| TR-2 | Servicio: solicitud sin token, emisión, consumo atómico, sello en login, MFA, renovación y cambio propio | v4-pro / v4-flash | **c0:** se aplicaron 14 de 15 bloques; `verify_login` usaba el sello recargado (abría la carrera login/reset) → rechazado.<br>**c1:** PASS.<br>**c2:** omitió el bloque de mypy → se divide en TR-2b → PASS. (La primera llamada se perdió por un error de red `EAI_AGAIN`; no consumió reintento) | 2 |
| TR-3 | API: 202 con cuerpo fijo y `extra="forbid"` | v4-flash | PASS | 0 |
| TR-4 | CLI `password_breakglass` | v4-flash | **c0:** descriptor abierto y fichero vacío en los errores.<br>**c1:** las validaciones no borraban el fichero; tipo `str \| None`.<br>**c2:** contenido correcto sin marcadores → se divide en TR-4b (solo marco; idéntico byte a byte) → PASS | 2 |
| TR-5 | Pruebas que dependían del defecto o de la cabeza `0058` | v4-flash | PASS (con el valor histórico enmascarado) | 0 |
| TR-6 | Pantalla `/reset-password` (tres pasos) y 10 vitest | v4-pro | **c0:** formato; `err.body` inexistente; aviso siempre visible; `role` erróneo; `reset_token` en el tipo.<br>**c1:** página correcta; 7 pruebas con un localizador ambiguo (medido).<br>**c2:** PASS | 2 |
| TR-A3 | Pruebas que matan 5 mutantes supervivientes | v4-pro | **Intentos anteriores:** el lote combinado omitió TR-A3; el envío en solitario devolvió solo los imports (aplicados) → se divide en a y b.<br>**TR-A3a:** c0 con números de línea en el SEARCH y firma de `sesiones_de` errónea → c1 PASS.<br>**TR-A3b:** c0 con función inventada y sesión de otro usuario → c1 PASS | 1 por subtarea |
| TR-7 | E2E por la interfaz real (código por la orden local, trazas y capturas apagadas) | v4-pro / v4-flash | **c0:** formato, import inexistente, campo `tenant` en lugar de `tenant_code`, sesión del arnés equivocada, textos adivinados.<br>**c1:** 2 localizadores no estrictos (medido en los 3 motores).<br>**c2:** PASS | 2 |
| TR-2c | Ventana de la auditoría anónima medida con el mismo reloj que escribe `created_at` (la suite completa en PostgreSQL falló en A06 y B09: el reloj de suite inyectado iba ~11 h adelantado; reproducido con un desfase de 12 h en ambos motores) | v4-flash | PASS (A06 en verde con el desfase) | 0 |
| TR-A1d | B09 mide la caducidad con el reloj inyectado, no contra `created_at` | v4-flash | c0: bloques 2 y 3 sin línea de ruta (no aplicables) → c1 (solo formato) PASS; 33 + 1 en SQLite y 34 en PostgreSQL con desfase de 12 h | 1 |
| TR-8 | Documentación: contratos, runbook de `password_breakglass`, ADR-004 | v4-flash | PASS | 0 |

**Mutaciones:** 20/20 muertas tras TR-A3 (`mutaciones.md`).

**Rojo atribuido:** `rojo-tr-a1.txt`.

**Reproducción:** `reproduccion.txt`.

**Coste de esta fase:** 33 llamadas · 110 946 tokens de entrada · 81 328 de salida · **0,0979 USD**.

**Coste acumulado de la sesión:** 227 llamadas · 0,9487 USD. El coste del puente (Sonnet) lo factura la sesión de Claude Code.

**Lecciones registradas para los encargos:**
- Dar el ancla de fin de fichero SIN números de línea.
- No describir el formato como `<ruta>`.
- Una tarea por llamada: los lotes combinados hicieron que DeepSeek omitiera bloques.
- No adjuntar extractos largos de «patrón» cuando provocan eco: TR-1 entró en bucle.
