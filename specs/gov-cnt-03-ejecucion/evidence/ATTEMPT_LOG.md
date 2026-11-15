# ATTEMPT_LOG · CNT-03 Ejecución del contrato (2026-11-15)

- Modelo: deepseek-v4-pro en todas las llamadas, sin session_id ni thinking.
- Tope del encargo: 8 llamadas. La dueña autorizó ampliaciones durante el ciclo:
  - 9.ª a 11.ª;
  - 12.ª;
  - 13.ª y 14.ª (solo E2E, y luego la 14.ª también para la página);
  - 15.ª y 16.ª (integración con CNT-02);
  - 17.ª.
- **17 llamadas con respuesta.** Además hubo un intento de C2 que se perdió por una caída de red de la estación (EAI_AGAIN): no dejó respuesta ni uso registrado y se reenvió. OWNER_EXCEPTION_USED=1.
- Uso total: 86.755 tokens de entrada / 121.972 de salida, **USD 0,1437**.

| Llamada | Encargo | Entrada/salida | USD | Auditoría |
|---|---|---|---|---|
| C1 | Modelo (8 tablas), guarda PG genérica, migración, permiso, MFA, SoD, auditoría y fijaciones | 8.111 / 18.772 | 0,0199 | 14/14 bloques. Defecto: ruff B905 y colisión de variable de bucle (mypy), corregidos en C2 |
| C2 | Servicio (16 mutaciones + lectura + opciones + CSV), esquemas, API y main; K1 | 12.363 / 28.345 | 0,0300 | 6/6 bloques. Defectos: kwargs a `_bloqueo` (TypeError), 12 errores de mypy y orden de import (el orden lo había dictado mal Claude) |
| C3 | Corrección K1–K3 + pruebas PG | 6.454 / 12.051 | 0,0133 | Correcciones parciales (3 bloques no-op, 1 roto). Pruebas REJECT: decorador, fixtures, ids, contrato/expediente, usuario y carrera |
| C4 | Pantalla, ruta, enlace y Vitest | 6.451 / 1.284 | 0,0039 | Solo entregó api.ts (detenido) |
| C5 | Restos del servicio + pruebas reescritas | 7.378 / 12.025 | 0,0137 | Servicio PASS. Pruebas: el vínculo de «ua» a sí mismo viola GOV_IDENTITY_SELF_LINK (error de diseño de Claude en el encargo) |
| C6 | Reintento de la pantalla (B–E) | 6.563 / 21.758 | 0,0218 | 4/4. Defectos: `ejecucion.flujo`, imports sin uso, caso d de Vitest; selectores de documento vacíos en 4 secciones (hallado después) |
| C7 | Corrección conjunta (servicio, pruebas, pantalla) | 13.943 / 5.022 | 0,0104 | Formato `<<<< ORIGINAL` normalizado (solo formato). Pruebas incompletas |
| C8 | E2E del sponsor | 3.082 / 3.334 | 0,0042 | Sin marcadores (normalizado). Bloque de permisos erróneo; textos, ids y clics de confirmación incorrectos |
| C9 | Pruebas PG completas (autorizada) | 11.892 / 11.573 | 0,0152 | 11/14 en verde; quedaban la lista de hitos y las fechas en texto en la concurrencia |
| C10 | Pantalla (selectores de documento, setAbierto) + E2E | 3.709 / 3.469 | 0,0046 | 4 bloques no-op y 1 sin coincidencia omitidos; el resto PASS |
| C11 | 3 defectos de pruebas + tipo de Axe | 1.226 / 918 | 0,0013 | SEARCH repetido aplicado a ambas apariciones de forma mecánica |
| C12 | `rec_a` y `codigoContrato!` | 392 / 177 | 0,0003 | PASS |
| C13 | Selectores `exact` en la E2E | 809 / 426 | 0,0007 | PASS (ruta con barra inicial) |
| C14 | `relative` en las 6 regiones (desbordamiento a 390/320 por un sr-only) | 451 / 465 | 0,0006 | Llegó como diff unificado; convertido a bloques (solo formato) |
| C15 | Proyección CNT-02 en `terminos_efectivos` | 2.362 / 1.409 | 0,0023 | Servicio PASS (6 SEARCH idénticos aplicados en orden). Prueba REJECT |
| C16 | Prueba de la proyección CNT-02 | 1.265 / 811 | 0,0011 | PASS |
| C17 | Pantalla en el catálogo de autoridad | 304 / 133 | 0,0002 | PASS |

## Reintentos semánticos y causas

- 11 reintentos (C3, C5, C6, C7, C9, C10, C11, C12, C13, C14 y C16). Las causas se dividieron en subproblemas; ninguno pasó de 2 reintentos, salvo las pruebas PG. En ese caso se reformuló el diseño de la prueba (cuenta supervisora vinculada) y se dividió el trabajo.
- Defectos de diseño de Claude hallados en la verificación:
  - el orden del import en main;
  - el vínculo de «ua» consigo mismo (regla GOV_IDENTITY_SELF_LINK);
  - no haber previsto el sr-only en las regiones de tabla.

## Integración mecánica de Claude (sin semántica)

- Normalización de formato (marcadores, rutas, diff unificado → bloques): C7, C8, C11, C13, C14 y C15. FORMAT_ONLY_EDITS=6.
- Resolución mecánica del merge con CNT-02 (P2):
  - imports y rutas de ambos lados;
  - catálogo de auditoría 551+5+18 = 574;
  - cabeza → 0119;
  - renombre de la migración no publicada 0118 → 0119 sobre 0118_gov_cnt02_modificaciones.
- Diagnóstico temporal (shim) en la E2E para medir el desbordamiento. Retirado; no se publica.
- Fixtures OpenAPI regeneradas con `qa/fixtures_de_frontend.py`.

CLAUDE_SEMANTIC_CODE_WRITTEN=0, CLAUDE_SEMANTIC_TESTS_WRITTEN=0, CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0, CLAUDE_SEMANTIC_QA_WRITTEN=0.
