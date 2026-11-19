# Registro de intentos · ORG-04-AUTHORITY-ASSIGNMENT-POLICY

- **Modelo:** `deepseek-v4-pro` vía `mcp__deepseek__deepseek_chat`, sin sesión ni `thinking`.
- **Tope:** 24 llamadas (OD-AP-04).
- **EGRESS_CHECK:** en cada llamada, ENV_FILES=0, SECRETS=0, PROD_URLS=0, TOKENS=0, PRIVATE_KEYS=0, REAL_PII=0, REAL_PAYROLL=0 y BANK_DATA=0. Los briefs solo llevan código, contratos y textos legales públicos.
- **Coste:** $0,435 por millón de tokens de entrada y $0,87 por millón de salida, la misma tarifa del ciclo anterior.

## Reclasificaciones (Claude, declaradas)

| Tarea | Era | Pasa a | Motivo |
|---|---|---|---|
| T03 autoridad | DEEPSEEK | CLAUDE | Codifica pisos legales verificados y su fusión (solo endurece). Es semántica normativa, equivalente a una regla tributaria |
| T05 integración en `service_ocupacion` | DEEPSEEK | CLAUDE | Toca invariantes cercanas a la seguridad (autoridad propia y emisor), y el brief pasaba de 55 KB |
| T08 pruebas existentes | DEEPSEEK | CLAUDE | Solo 3 cambios mecánicos (renombre y contrato del catálogo) |
| T10b ficha de la asignación | DEEPSEEK | CLAUDE | Cambio pequeño, acoplado a los tipos del contrato. Se reservaron las llamadas para T09b y T11 |
| Tipos `politicasAsignacion.ts`, tipos de `api.ts`, rutas, menú y `pantallas.ts` | — | CLAUDE | Son el contrato |

## Llamadas

| # | Tarea | Tokens (entrada/salida) | Coste | Resultado | Motivo |
|---|---|---|---|---|---|
| 1 | T04 · servicio, esquemas y API de políticas | 15232/12902 | $0,017851 | REJECT | (a) Una función local `instantanea` tapaba la de la autoridad (F811). (b) `_detalle_base` llamaba con argumentos equivocados y lo ocultaba con `type: ignore`. (c) `opciones` llamaba a `pisos_aplicables` con la figura en None. (d) La ejecución destapó después un import inexistente (`app.core.errors.core`) y Literal inventados para figuras, acciones y materias |
| 2 | T04 · reintento 1 | 2476/376 | $0,001404 | REJECT parcial | Corrigió (a), (b) y (c). Faltaban las cabeceras `FILE`, que Claude normalizó sin tocar el contenido (declarado). Quedó un import sin uso (`pisos_aplicables`), y el orden de imports de `main.py` venía de la llamada 1: Claude corrigió esas dos líneas de lint sin `ruff --fix` (declarado) |
| 3 | T06 y T07 · pruebas PG | 4555/7804 | $0,008771 | REJECT | PUT con el detalle entero (422 extra), firma equivocada de `post_asignacion`, claves de fixture inventadas, una política con documento obligatorio que contaminaba otras pruebas y 5 fallos de lint |
| 4 | T09a · lista y ficha de políticas, y Vitest | 15143/11572 | $0,016655 | REJECT parcial | Las pantallas compilan y la ficha pasa 5 de 5. Fallan 2 pruebas de la lista (selector ambiguo y opción sin cargar) y hay un import sin uso |
| 5 | T04 · reintento 2 | 1497/806 | $0,001352 | PASS | Import corregido y Literal con los valores exactos del dominio |
| — | T04 · línea de Claude | — | — | CLAUDE | Con los reintentos agotados, la ejecución real destapó un tercer defecto: `cerrar` exigía el permiso inexistente `gobierno_ocupacion:close` (el contrato pedía `:revoke`). Claude cambió esa palabra (declarado) |
| 6 | T10a · formulario de asignación | 13017/5800 | $0,010708 | REJECT parcial | Marcadores «SEARCH:»/«REPLACE:» en línea, que Claude normalizó (marco). 21 de 22 bloques aplicables. Un SEARCH era ambiguo y faltaban las constantes de prueba |
| 7 | T06 · reintento 1 | 8863/5936 | $0,009020 | REJECT | Marco en línea con un `REPLACE:` sin su `SEARCH:`. El primer normalizador de Claude lo aplicó mal; se detectó por el SyntaxError, se restauró el fichero y se corrigió el normalizador para que falle ante esa estructura |
| 8 | T09a · reintento 1 | 2107/258 | $0,001141 | REJECT | Contenido correcto, pero marco en línea con ambigüedad de líneas en blanco |
| 9 | T10a · reintento 1 | 1159/909 | $0,001295 | REJECT | Rutas `src/pages/…` (normalizadas por Claude, declarado). Un bloque no cambiaba nada y el otro no definía las reglas de prueba |
| 10 | T09a · reintento 2 | 493/341 | $0,000511 | PASS | Mismo contenido con el marco correcto. Claude puso el nombre accesible en la `<table>` (contrato), que con los reintentos agotados era el único fallo restante. Resultado: 9 de 9 |
| 11 | T06 · reintento 2 | 9027/4492 | $0,007835 | REJECT parcial | Rutas sin prefijo (normalizadas). 22 de 23 bloques aplicados; uno ambiguo. Con los reintentos agotados, Claude aplicó a mano el cambio de ese bloque (`post_asignacion(mundo, body)`) y corrigió los defectos restantes: `activa(...)` por `accion(..., "activar")`, `crear_funcionario(mundo)`, una unidad inventada, el acto de la comisión emitido por otro cargo, la clave `regla_version`, el import de `_entrada` y una variable sin uso. Resultado: 20 de 20 |
| 12 | T10a · reintento 2 | 1242/722 | $0,001168 | REJECT parcial | 2 de 3 bloques aplicados. El tercero falló porque el brief de Claude daba un ancla errónea (el reintento 1 había metido `reglas` dentro de `catalogo`). Con los reintentos agotados, Claude completó la prueba: constantes de regla, renombres, 20 días en NAP-05 (la LOPPM exige «más de 15») y la respuesta del POST en los mocks. Resultado: 72 de 72 en ocupación |
| 13 | T09b · formulario de políticas y Vitest | 14263/14529 | $0,018845 | REJECT | `headers` en lugar de `ifMatch`, import sin uso, etiquetas sin el sufijo «(obligatorio)» y firma equivocada de `ApiError` |
| 14 | T11 · E2E | 11573/10096 | $0,013818 | REJECT | 2 variables sin uso. La ejecución real falló en los 3 escenarios: fechas fuera del ejercicio y texto exacto del código |
| 15 | T09b · reintento 1 | 4861/4060 | $0,005647 | PASS | 7 de 7 |
| 16 | T11 · reintento 1 | 10782/1851 | $0,006301 | REJECT parcial | 12 de 14 bloques aplicados. Dos bloques idénticos sobre una línea que aparece dos veces; Claude hizo esas dos sustituciones idénticas (declarado) |
| 17 | T11 · reintento 2 | 10217/2508 | $0,006626 | REJECT parcial | Aplicado entero: quita el titular duplicado del cargo de origen. Con los reintentos agotados, Claude corrigió en la ejecución real: esperar la URL del detalle tras el POST, `.first()` en un texto repetido, recargar la ficha tras activar por API, PUT con la entrada completa y la versión vigente, y editar y activar la v2 en lugar de la v1. Resultado: 3 de 3 |

## Totales

- **Llamadas:** 17 de 24 (OWNER_EXCEPTION_USED=0).
- **Reparto:** 6 tareas base (T04, T06+T07, T09a, T10a, T09b y T11) y 11 reintentos.
- **Resultado:** 3 PASS, todos en un reintento (T04 r2, T09a r2 y T09b r1) y ninguno al primer intento; el resto, REJECT o REJECT parcial con motivo verificado.
- **Tokens:** 126.507 de entrada y 84.962 de salida.
- **Coste:** $0,128947.
- **Garantías:**
  - ningún parche se corrigió a mano para atribuírselo a DeepSeek;
  - no se usó `ruff --fix`;
  - las normalizaciones de marco (cabeceras `FILE`, rutas y marcadores en línea) no tocan el contenido y se rechazan si son ambiguas.
- **Trabajo de Claude:**
  - diseño, delta, plan y tareas;
  - migración 0126 y modelos (era 0125; renumerada al fusionar TRE-03 de P1, que tomó la 0125);
  - autoridad `service_asignacion_regla.py`;
  - integración en `service_ocupacion`, esquemas y API de la regla;
  - permisos, MFA, catálogo de auditoría y ResourceKind;
  - semilla N9 de `GovernmentAssignment`;
  - tipos del frontend, rutas, menú y `pantallas.ts`;
  - ficha de la asignación (T10b);
  - las líneas declaradas arriba;
  - constantes declaradas (antes de fusionar: cabeza 0125, catálogo 604, permisos 179, MFA estándar 82, ResourceKinds 38; tras fusionar TRE-03: cabeza 0126, catálogo 613, permisos 184, MFA sensibles 83 y estándar 84);
  - el ayudante `enteActivo(…, nivel)` de la E2E;
  - mutaciones, auditoría de hardcode y certificación.

## Mutaciones (Claude, 2026-11-18)

Script fuera del repositorio (`mutar_ap.py`):
- cada mutación exige un ancla única;
- corre sus pruebas con `-x`;
- restaura el original en `finally`.

| Id | Mutación | Prueba que la mata | Resultado |
|---|---|---|---|
| M1 | Aplicabilidad normativa: la LOPPM rige en todo nivel | `test_p0_no_municipal_sin_autorizacion` | MUERTA |
| M2 | Se ignora el cargo emisor que fija la política | `test_emisor_por_cargo` | MUERTA |
| M3 | Se ignora la lista de competencias permitidas | `test_competencias_permitidas` | MUERTA |
| M4 | Ningún límite de duración se excede | `test_congelacion_de_version` | MUERTA |
| M5 | Se ignora el documento obligatorio | `test_documento_obligatorio_al_activar` | MUERTA |
| M6 | Ficha de la política sin filtro de empresa | `test_politica_aislamiento_empresas` | MUERTA |
| M7 | Se ignora la regla congelada | `test_congelacion_de_version` | MUERTA |
| M8 | No se exige la autorización especial | `test_p0_municipal_exige_autorizacion` | MUERTA |
| M9 | Avocación admitida pese a la política | `test_avocacion_prohibida_por_politica` | MUERTA |

**Resultado:** 9 de 9 muertas.

## Defecto P0 reproducido

- **Antes:** la prueba Vitest «no pide autorización municipal a un ente no municipal (P0)» falla contra `NuevaAsignacionPage.tsx` de HEAD (a51816b3), que pinta el campo de autorización (`expected <textarea> to be null`).
- **Después:** pasa con el componente nuevo.
- ORG04_P0_DEFECT_REPRODUCED_BEFORE=YES · ORG04_P0_DEFECT_FIXED_AFTER=YES.
