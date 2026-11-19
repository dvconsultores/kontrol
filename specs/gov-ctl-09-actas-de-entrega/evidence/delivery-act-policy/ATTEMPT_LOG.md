# Registro de intentos · CTL-09-DELIVERY-ACT-POLICY

- **Modelo:** `deepseek-v4-pro` vía `mcp__deepseek__deepseek_chat`, sin sesión ni `thinking`.
- **Tope:** 16 llamadas (OD-AE-05).
- **EGRESS_CHECK:** en cada llamada, ENV_FILES=0, SECRETS=0, PROD_URLS=0, TOKENS=0, PRIVATE_KEYS=0, REAL_PII=0, REAL_PAYROLL=0 y BANK_DATA=0. Los briefs solo llevan código, contratos y texto legal público.
- **Coste:** $0,435 por millón de tokens de entrada y $0,87 por millón de salida.

## Reclasificaciones (Claude, declaradas)

| Tarea | Era | Pasa a | Motivo |
|---|---|---|---|
| T07 PG de políticas, regla y procesos | DEEPSEEK | CLAUDE | Es la evidencia del P0: debía reproducir el defecto contra HEAD y cubrir con exactitud las mutaciones. Se escribió un único fichero (`test_gov_ctl09_politica.py`, 13 pruebas) |
| T08 frontend de políticas | DEEPSEEK | DEEPSEEK partido en T08a (lista y ficha) y T08b (formulario) | Límite de 55 KB del brief |
| Tipos `politicasActa.ts`, `reglaActa.ts`, tipos de `api.ts`, rutas, menú, `pantallas.ts` y humo UAT | — | CLAUDE | Son el contrato |

## Llamadas

| # | Tarea | Tokens (entrada/salida) | Coste | Resultado | Motivo |
|---|---|---|---|---|---|
| 1 | T06 · servicio, esquemas y API de políticas | 15756/13934 | $0,018866 | REJECT | `include_router` sin sangría (SyntaxError); import fuera de orden; imports sin uso; `instantanea` sin importar; campos inventados (`GovernmentAct.estado/nombre`, `GovernmentUnit.nombre`); relaciones inexistentes (`politica.bindings`…); conflicto de tipos entre resumen y detalle |
| 2 | T09 · nueva acta y ficha, y Vitest | 16373/15304 | $0,013424 | REJECT | 4 pruebas fallaban (etiquetas con el sufijo «(obligatorio)» y un texto partido) y 2 `any` |
| 3 | T06 · reintento 1 | 5120/2712 | $0,004587 | REJECT parcial | 16 de 18 bloques aplicados. Uno era ambiguo (SEARCH presente 3 veces); el de imports de `main.py` no coincidía por un fragmento no contiguo del brief (error de Claude). Incluyó el campo nuevo `cargo_maxima_autoridad_codigo` (D-AE-14) |
| 4 | T06 · reintento 2 | 1169/555 | $0,000991 | PASS | Las 3 correcciones restantes (orden de imports y claves del resumen) |
| — | T06 · línea de Claude | — | — | CLAUDE | Con los reintentos agotados, la sonda destapó un 500: el detalle hereda `total_vinculos`/`total_requisitos` del resumen sin rellenarlos. Claude añadió esas dos claves (declarado) |
| 5 | T09 · reintento 1 | 2292/1424 | $0,002125 | REJECT parcial | Selectores corregidos; las pruebas seguían fallando porque cambiaban el `<select>` antes de cargar las opciones |
| 6 | T09 · reintento 2 | 1768/1000 | $0,001529 | REJECT parcial | 1 de 3 bloques válido; dos ponían `await` dentro de un callback no asíncrono. Con los reintentos agotados, Claude completó NAE-02 y NAE-03 (espera de la opción y `findAllByText`), las etiquetas de NAE-04 (`/^Receptor/`…) y un `body?.` (declarado) |
| 7 | T08a · lista y ficha de políticas | 15025/10582 | $0,015632 | REJECT | 10 errores de tipos: `formatearFecha` de otro módulo, rutas `../`, import sin uso y fixture incompleta |
| 8 | T08b · formulario de políticas | 11233/15472 | $0,018237 | REJECT | 48 errores: `@/components/Select` inexistente, `id` en FormField, manejadores de cambio que reciben el evento, imports sin uso y constructor de `ApiError` |
| 9 | T08a · reintento 1 | 1817/1582 | $0,002056 | REJECT parcial | Tipos corregidos; 2 pruebas fallaban por textos repetidos o partidos |
| 10 | T08b · reintento 1 | 15576/15002 | $0,019717 | REJECT parcial | Compila y pasa lint; 5 pruebas fallaban (selectores, llaves en `userEvent.type` y comparación por texto) |
| 11 | T08a · reintento 2 | 565/200 | $0,000420 | PASS | Faltaba la cabecera `FILE` del segundo bloque; Claude la normalizó (marco, declarado). 7 de 7 |
| 12 | T08b · reintento 2 | 4583/1077 | $0,002820 | REJECT parcial | 5 de 6 bloques aplicados; uno era ambiguo. Con los reintentos agotados, Claude corrigió la etiqueta (`/^Código(?! del)/`, porque el asterisco oculto también cuenta) y la URL codificada del mock de la vista previa (declarado). 29 de 29 en actas |
| 13 | T10 · E2E | 7155/6925 | $0,009137 | REJECT | Códigos de cargo recalculados, PUT y activación sobre la v1, `waitForResponse` sobre llamadas de `request`, selector ambiguo, URL del frontend armada con la API y creación en paralelo |
| 14 | T10 · reintento 1 | 7975/7524 | $0,009905 | REJECT | 6 variables sin uso (lint) e If-Match de `nueva-version` con la versión de creación |
| — | T10 · sonda de Claude | — | — | CLAUDE | Copia temporal del spec (`zz-sonda-actas.spec.ts`, borrada después) ejecutada contra la E2E real, para destapar todos los fallos de ejecución antes del último reintento: lista vacía sin tabla, «Quien entrega» sin dos puntos (error del contrato de Claude), If-Match de `nueva-version` y anexos A11 pendientes en el acta B. Con esas correcciones la sonda pasó entera |
| 15 | T10 · reintento 2 | 1583/1257 | $0,001782 | PASS (con una línea de Claude) | Las correcciones demostradas por la sonda. Quedó una variable sin uso (`politicaVersion`), que Claude eliminó (declarado). Resultado: E2E 1/1 |

## Totales

- **Llamadas:** 15 de 16 (OWNER_EXCEPTION_USED=0).
- **Reparto:** 6 tareas base (T06, T09, T08a, T08b, T10 y el reintento completo de T08b) y 9 reintentos.
- **Resultado:** 3 PASS, todos en un reintento (T06 r2, T08a r2 y T10 r2). El resto, REJECT o REJECT parcial con motivo verificado.
- **Tokens:** 107.990 de entrada y 94.550 de salida.
- **Coste:** $0,129234.
- **Garantías:**
  - ningún parche se corrigió a mano para atribuírselo a DeepSeek;
  - no se usó `ruff --fix`;
  - las normalizaciones de marco (cabecera `FILE`) no tocan el contenido.
- **Trabajo de Claude:**
  - análisis normativo y custodia de N34;
  - delta, plan y tareas;
  - migración 0127 y modelos;
  - autoridad `service_actas_regla.py` e integración en `service_actas` (regla, responsabilidad ORG-04, anexos, suscripción, ficha, `/regla`);
  - permisos, MFA y catálogo de auditoría;
  - pruebas PG del ciclo (T07 reclasificada) y constantes;
  - tipos del frontend, rutas, menú, `pantallas.ts`, humo UAT y exención de la guardia de puertas;
  - las líneas declaradas arriba;
  - mutaciones, auditoría de hardcode, N34_VALIDATION y cierre.

## Mutaciones (Claude)

Script fuera del repositorio (`mutar_ae.py`):
- cada mutación exige un ancla única;
- corre sus pruebas con `-x`;
- restaura el original en `finally`.

| Id | Mutación | Prueba que la mata | Resultado |
|---|---|---|---|
| M1 | Aplicabilidad: todo vínculo aplica a cualquier acta | `test_a17_en_la_unidad_de_hacienda_y_no_en_otra_unidad` | MUERTA |
| M2 | A17 global | `test_p0_instituto_municipal_no_recibe_a17` | MUERTA |
| M3 | Documento obligatorio: todo anexo resuelto | `test_a17_se_exige_cuando_la_politica_lo_declara_para_la_entidad` | MUERTA |
| M4 | Testigos: se ignora el mínimo de la política | `test_testigos_exigidos_por_la_politica_en_la_entrega` | MUERTA |
| M5 | Plazo: todo hito cumplido se da en plazo | `test_numeracion_y_plazo_interno` | MUERTA |
| M6 | ORG-04: no se comprueba que el saliente ejerza al corte | `test_responsabilidad_con_la_autoridad_de_org04` | MUERTA |
| M7 | Aislamiento: ficha de la política sin filtro de empresa | `test_politica_aislamiento_entre_empresas` | MUERTA |
| M8 | Congelación: se ignora la regla guardada | `test_version_congelada_en_el_acta` | MUERTA |
| M9 | Piso legal: el plazo interno puede superar el legal | `test_piso_legal_no_se_rebaja` | MUERTA |
| M10 | Numeración: se ignora el patrón de la política | `test_numeracion_y_plazo_interno` | MUERTA |

**Resultado:** 10 de 10 muertas.

## Defecto P0 reproducido

- **Antes:** `test_p0_instituto_municipal_no_recibe_a17` falla contra `service_actas.py` de HEAD (b65d5982). El acta de un instituto municipal (ámbito ENTE) recibe A17_1 a A17_5.
- **Después:** pasa con la autoridad nueva.
- CTL09_P0_DEFECT_REPRODUCED_BEFORE=YES · CTL09_P0_DEFECT_FIXED_AFTER=YES.
