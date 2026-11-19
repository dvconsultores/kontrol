# Registro de intentos · ORG-07-EFFECTIVE-AUTHORITY-MATRIX

- **Modelo:** `deepseek-v4-pro` vía `mcp__deepseek__deepseek_chat`, sin sesión ni `thinking`.
- **Tope:** 8 llamadas.
- **EGRESS_CHECK:** en cada llamada, ENV_FILES=0, SECRETS=0, PROD_URLS=0, TOKENS=0, PRIVATE_KEYS=0, REAL_PII=0, REAL_PAYROLL=0 y BANK_DATA=0. Los briefs solo llevan código, contratos y nombres sintéticos.
- **Coste:** $0,435 por millón de tokens de entrada y $0,87 por millón de salida.

## Reclasificaciones y trabajo de Claude (declarados)

| Tarea | Ejecutor | Motivo |
|---|---|---|
| T01 `autoridad_efectiva_en` (ORG-04) | CLAUDE | Resolución canónica de autoridad |
| T02 proyección, reserva de personas, CSV, esquemas y API | CLAUDE | Control de acceso (OD-EA-01) |
| T03 PG del ciclo (`test_gov_org07_efectiva.py`, 17 pruebas) | CLAUDE | Evidencia del defecto y de las mutaciones |
| Contrato del frontend (`api.ts`: tipos, `etiquetaDeFuente` y `nombreDePersona`) y ajuste mecánico del Vitest existente (`fuente: null` en 2 fixtures y la aserción del aviso nuevo en MTZ-02) | CLAUDE | Es el contrato |
| Cabecera del CSV en `test_gov_org07_autoridad.py::test_gm14_csv` | CLAUDE | Cambio de contrato esperado (D-EA-09) |
| **Defecto de ORG-04** destapado por la E2E: activar una delegación daba 500 en la app real | CLAUDE | Depuración y causa raíz (ver abajo) |

## Llamadas

| # | Tarea | Tokens (entrada/salida) | Coste | Resultado | Motivo |
|---|---|---|---|---|---|
| 1 | T04 · pantalla y Vitest | 6798/7040 | $0,009082 | REJECT | `vigenciaDeFuente` entre los imports; 3 IIFE en el JSX; «Sustituye a Reservado» no salía; 7 errores de tsc en fixtures inventadas; ruta de `renderPagina` que no casaba; nombre del botón de detalle equivocado (error del brief de Claude) |
| 2 | T04 · reintento 1 | 10168/6457 | $0,010041 | REJECT parcial | Pantalla correcta y Vitest 30/30; quedaba 1 error de tsc (`id` duplicado en `buildFila`) |
| 3 | T04 · reintento 2 | 577/66 | $0,000308 | PASS | Quita la línea duplicada. Typecheck 0, lint limpio y Vitest 30/30 |
| 4 | T05 · E2E | 6793/5185 | $0,007466 | REJECT | 10 × TS2339 (`funcionarioApi` sin `nombre`) y una variable sin uso |
| — | T05 · sonda de Claude | — | — | CLAUDE | Copia temporal (`zz-sonda-efectiva.spec.ts`, borrada) con lo de compilación corregido: destapó el 500 de ORG-04 y un error de lógica (la suplencia acababa el mismo día en que se esperaba ver otra vez al titular). Con el arreglo de ORG-04 y el fin en HOY+2, pasó entera |
| 5 | T05 · reintento 1 | 814/488 | $0,000779 | REJECT parcial | 3 de 4 bloques válidos y aplicados; el cuarto quitaba además la comprobación de que la fila de la titular es visible |
| 6 | T05 · reintento 2 | 374/201 | $0,000338 | PASS | Bloque corregido. E2E 1/1 |

## Totales

- **Llamadas:** 6 de 8 (OWNER_EXCEPTION_USED=0); 2 tareas base y 4 reintentos.
- **Tokens:** 25.524 de entrada y 19.437 de salida.
- **Coste:** $0,028014.
- **Garantías:**
  - ningún parche se corrigió a mano para atribuírselo a DeepSeek;
  - el reintento 2 de T04 llegó en el informe del puente con el sangrado del marco, que se quitó antes de comparar;
  - no se usó `ruff --fix`.

## Defecto de ORG-04 (Claude)

- **Síntoma:** `POST /gobierno/ocupacion/asignaciones/{id}/activar` de una delegación respondía 500 (`GOV_ASSIGNMENT_COMPETENCY_IMMUTABLE`) en la app real.
- **Causa raíz:**
  - la sesión de la app tiene `autoflush=False` (`app/core/database.py`);
  - `activar` añadía las competencias delegadas con `db.add` y ponía `status = "ACTIVO"` antes del `flush`;
  - el INSERT salía después del UPDATE y el disparador `kontrol_gov_asignacion_competencia_inmutable` lo rechazaba.
- **Por qué las PG no lo veían:** la fábrica de sesiones de las pruebas usa el autoflush por defecto, y una consulta intermedia escribía las competencias mientras la asignación seguía en BORRADOR.
- **Antigüedad:** desde d1656a70 (2026-11-07). Ninguna E2E activaba una delegación.
- **Arreglo:** `_reemplazar_competencias` hace `flush` al terminar, con la asignación todavía en BORRADOR.
- **Regresión:** `test_org07_ea17_activar_delegacion_con_la_sesion_de_la_app` usa una sesión con `autoflush=False`. Fallaba antes del arreglo con el mismo error y pasa después.

## Mutaciones (Claude)

Script fuera del repositorio (`mutar_ea.py`):
- cada mutación exige un ancla única;
- corre sus pruebas con `-x`;
- restaura el original en `finally`.

| Id | Mutación | Prueba que la mata | Resultado |
|---|---|---|---|
| M1 | Ignorar ORG-04 | `test_org07_ea01_defecto_delegacion_visible` | MUERTA |
| M2 | Ignorar la fecha de corte (usar hoy) | `test_org07_ea07_historia_titular_suplente_titular` | MUERTA |
| M3 | Incluir las revocadas | `test_org07_ea04_delegacion_revocada_solo_en_la_historia` | MUERTA |
| M4 | Perder el límite de la delegación | `test_org07_ea01_defecto_delegacion_visible` | MUERTA |
| M5 | Perder el alcance (filtro de unidad) | `test_org07_ea11_alcance_en_la_unidad_del_delegante` | MUERTA |
| M6 | Duplicar la identidad base y derivada | `test_org07_ea02_base_y_delegada_conviven` | MUERTA |
| M7 | Omitir la fuente | `test_org07_ea06_suplencia_sustituye_sin_duplicar` | MUERTA |
| M8 | CSV sin filas de ORG-04 | `test_org07_ea14_csv_mismo_universo_que_la_pantalla` | MUERTA |
| M9 | OD-EA-01: persona visible sin permiso de ocupación | `test_org07_ea13_persona_reservada_sin_permiso_de_ocupacion` | MUERTA |

**Resultado:** 9 de 9 muertas.

## Defecto reproducido

- **Antes:** con `service_autoridad.py`, `schemas_autoridad.py` y `api_autoridad.py` de 65651eff, `test_org07_ea01_defecto_delegacion_visible` falla porque no hay ninguna fila delegada.
- **Después:** pasa.
- ORG07_DEFECT_REPRODUCED_BEFORE=YES · ORG07_DEFECT_FIXED_AFTER=YES.
