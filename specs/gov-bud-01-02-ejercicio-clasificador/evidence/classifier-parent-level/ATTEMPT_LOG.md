# Registro de intentos · BUD-02-CLASSIFIER-PARENT-LEVEL

- **Modelo:** `deepseek-v4-pro` vía `mcp__deepseek__deepseek_chat` (subagente `deepseek-executor`), sin sesión ni `thinking`.
- **Tope:** 6 llamadas.
- **EGRESS_CHECK:** en cada llamada, ENV_FILES=0, SECRETS=0, PROD_URLS=0, TOKENS=0, PRIVATE_KEYS=0, REAL_PII=0, REAL_PAYROLL=0 y BANK_DATA=0. El encargo solo lleva contratos, selectores y datos sintéticos.
- **Coste:** $0,435 por millón de tokens de entrada y $0,87 por millón de salida.

## Trabajo de Claude (declarado)

| Tarea | Ejecutor | Motivo |
|---|---|---|
| T01 regla única `validar_padre_partida` y normalización del padre | CLAUDE | Alcance por clasificador y empresa (frontera de aislamiento). Se escribió con la prueba del defecto: unas 20 líneas |
| T02 PG del ciclo (`test_gov_bud02_jerarquia.py`, 9 pruebas) y mutaciones | CLAUDE | Evidencia del defecto |
| T04 regresión, hardcode, tarjeta, roadmap y cierre | CLAUDE | Cierre |
| T05 accesibilidad de la lista de errores del CSV (`ClasificadorEjercicio.tsx`) | CLAUDE | Defecto real que destapó el Axe de la E2E: `<ul role="alert">` anula la semántica de lista (regla `listitem`, seria). Arreglo de una línea: `<div role="alert"><ul>` |

## Llamadas

| # | Tarea | Tokens (entrada/salida) | Coste | Resultado | Motivo |
|---|---|---|---|---|---|
| 1 | T03 · E2E de alta y CSV | 2848/2126 | $0,002978 | REJECT | Auditoría del parche PASS y aplicado tal cual, pero la E2E agotó el tiempo en `entrarEnGobierno`. La causa estaba en el **contrato de Claude**: dio como cuarto argumento la ruta del detalle, y es el enlace del menú |
| 2 | T03 · reintento 1 | 1115/244 | $0,000587 | PASS | Entra por el menú y abre el ejercicio por su enlace. Typecheck y lint limpios. Con el arreglo T05, E2E 1/1 con Axe a 1280, 390 y 320 |

## Totales

- **Llamadas:** 2 de 6 (OWNER_EXCEPTION_USED=0): 1 tarea base y 1 reintento.
- **Tokens:** 3963 de entrada y 2370 de salida.
- **Coste:** $0,003565.
- **Garantías:**
  - los bloques se aplicaron tal cual: el primero extraído de la respuesta original del puente, el segundo con `apply_file.py` tras quitar el sangrado del informe;
  - no se corrigió nada a mano;
  - no se usó `ruff --fix`.

## Mutaciones (Claude)

Script fuera del repositorio (`mutar_bud02.py`):
- cada mutación exige un ancla única;
- corre su prueba con `-x`;
- muestra la aserción que falla;
- restaura el original en `finally`.

| Id | Mutación | Prueba que la mata | Aserción | Resultado |
|---|---|---|---|---|
| M1 | Sin chequeo de nivel | `j01_defecto_nivel_3_con_padre_de_nivel_1` | 201 en lugar de 422 | MUERTA |
| M2 | Admite un padre del mismo nivel | `j02_niveles_raiz_mismo_salto_superior_e_inexistente` | 201 en lugar de 422 | MUERTA |
| M3 | Admite saltar niveles (cualquier padre inferior) | `j01_*` | 201 en lugar de 422 | MUERTA |
| M4 | Padre de otro clasificador de la misma empresa | `j03_padre_de_otro_clasificador_de_la_misma_empresa` | 201 en lugar de 422 | MUERTA |
| M5 | Padre de otra versión (ejercicio aprobado) | `j04_padre_de_otra_version_aprobada` | 201 en lugar de 422 | MUERTA |
| M6 | Padre de otra empresa (mismo año) | `j05_padre_de_otra_empresa` | 201 en lugar de 422 | MUERTA |
| M7 | El CSV omite la regla | `j07_csv_salto_de_nivel_y_orden_rechazan_todo_el_lote` | 200 en lugar de 422 | MUERTA |
| M8 | Importación parcial | `j07_*` | 200 en lugar de 422 | MUERTA |

**Resultado:** 8 de 8 muertas.

**Verde falso evitado.** En una primera versión, j03 y j04 construían el segundo ejercicio con las mismas partidas base. M4 y M5 morían entonces por «Ya existe una partida con ese código», no por el padre. Se rehízo el segundo ejercicio con solo su clasificador, y ahora las dos mueren por la aserción del padre.

## Defecto reproducido

- **Antes:** con `service_presupuesto.py` de b726c1da (más un stub de `validar_padre_partida` para la prueba unitaria), la suite del ciclo da 7 fallidas.
  - `j01`: el alta de nivel 3 con padre de nivel 1 devuelve **201**.
  - `j07`: el CSV con salto de nivel devuelve **200**.
  - `j02`: un padre del mismo nivel, uno superior y uno que salta niveles se aceptan.
  - `j03`, `j04` y `j05` fallan solo por el formato del error (sin `field_errors.codigo_padre`). El aislamiento por clasificador, versión y empresa ya existía.
- **Después:** 9/9.
- BUD02_DEFECT_REPRODUCED_BEFORE=YES · BUD02_DEFECT_FIXED_AFTER=YES.
