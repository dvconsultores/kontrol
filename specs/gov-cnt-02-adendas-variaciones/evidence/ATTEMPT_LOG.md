# CNT-02 · Registro de intentos de DeepSeek (2026-11-15)

- **Modelo:** siempre `deepseek-v4-pro`, sin `session_id` ni `thinking` y con `max_tokens` explícito.
- **Egreso:** antes de cada llamada se comprobó `EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0`. Las coincidencias de «Secretaria de la Comisión» son nombres de cargos de prueba: falsos positivos revisados.
- **Topes:** el tope inicial era de 8 llamadas (`OWNER_EXCEPTION_INHERITED=0`). La dueña autorizó dos ampliaciones:
  - primera, hasta 4 llamadas más (tope 12);
  - segunda, 2 más (tope 14).

  En total, `OWNER_EXCEPTION_USED=2`, con 6 llamadas extra.

| Llamada | Encargo | Entrada/salida (tokens) | USD | Resultado de la auditoría |
|---|---|---|---|---|
| 1 | T002: modelos y guardas, migración 0117, auditoría (+5), SoD (+2), cabezas y endurecimiento H01–H09 de CNT-01 | 16274/19741 | 0,024254 | **AUDIT_PASS**: 24 bloques exactos; Alembic up/down/up en PG; CNT-01 y recuentos en verde. Solo quedó 1 error nuevo de mypy (A·R1). El puente se cortó al redactar su informe final; la respuesta íntegra se tomó del fichero que guardó la herramienta |
| 2 | T003: servicio, esquemas y API de CNT-02, más A·R1 | 13850/17055 | 0,020752 | **AUDIT_REJECT** (D1–D8). Imports de un módulo equivocado (el servicio no llegaba a importarse); `certificate_id` en lugar de `certificado_id`; `documento_version_id`, que no existe; un stub que devolvía `[]`; un bloqueo extra del cargo; tipos UUID; `date` ausente en la API. A·R1 entró bien |
| 3 | B·R1: D1–D8 | 4125/4511 | 0,005719 | **PASS** en 18 de 19 bloques. El bloque 10 coincidía 3 veces porque el ancla del brief era una línea no única: se omitió y se reenvió en la llamada 4. Además, la cabecera pedida en el brief duplicó la constante `ETIQUETA_ESTADO` (defecto del brief, corregido en la llamada 4) |
| 4 | T004: pruebas PG (19) y 2 limpiezas | 9969/13411 | 0,016004 | **REJECT** en la sonda (tabla de abajo): 10/19. Las limpiezas sí entraron |
| 5 | T005: frontend completo | 12197/7 | 0,005312 | Sin propuesta: DeepSeek respondió «BRIEF_TRUNCADO» con el texto completo recibido. Las causas fueron los separadores «...» y extractos cortados a media expresión |
| 6 | Reenvío de T005 con separadores explícitos | 12317/7 | 0,005364 | Sin propuesta: otra vez «BRIEF_TRUNCADO» |
| 7 | Reenvío de T005 con extractos completos y sin centinela | — | — | Timeout de la API de DeepSeek, sin respuesta. Se cuenta como llamada |
| 8 | C·R1: 8 fallos de T004 (7 de prueba y 1 de producto) | 6522/5610 | 0,007718 | **AUDIT_PASS**: PG 19/19. El ancla 1c del brief empezaba una línea tarde y la línea original `r = _patch_m(` quedó duplicada. Claude quitó esa línea sobrante: no altera el REPLACE, lo sitúa donde debía apuntar el ancla (corrección de aplicación por defecto del brief) |
| 9 | T005a: API, dos pantallas, rutas y enlace en ContratoPage | 10368/15690 | 0,018160 | **AUDIT_PASS** a la primera: typecheck, lint, guardas authority-surfaces y query-contract, y ContratoPage.test |
| 10 | T005b: Vitest de las dos pantallas | 14231/5552 | 0,011021 | **REJECT** 18/21: un import sin usar, 2 selectores ambiguos y 1 aserción sin `ifMatch` (todos de la prueba) |
| 11 | T006: E2E (ayudante y spec) | 15024/628 | 0,006971 | Sin código: DeepSeek devolvió solo el informe de propuesta. Lo causó la instrucción de sistema que añadía el puente |
| 12 | Reenvío de T006 sin mensaje de sistema | 14741/16633 | 0,020883 | **REJECT** en la sonda E2E (tabla de abajo). Lint con 3 declaraciones sin usar |
| 13 | D·R1: 4 correcciones de Vitest | 635/422 | 0,000643 | **AUDIT_PASS**: 4 bloques exactos; Vitest de contratos 35/35 y completo 2076/2076 |
| 14 | E·R1: 10 correcciones de la E2E | 1229/1076 | 0,001471 | **AUDIT_PASS**: 10 bloques exactos; typecheck y lint limpios; E2E en verde (CIERRE.md) |

```text
DEEPSEEK_CALLS=14 (tope inicial 8; 6 extra con dos autorizaciones de la dueña)  GLOBAL_CAP_REACHED=1  OWNER_EXCEPTION_USED=2
DEEPSEEK_RETRIES=5 semánticos (A·R1, B·R1, C·R1, D·R1, E·R1)  REENVIOS_POR_TRANSPORTE_O_PROTOCOLO=5 (llamadas 5, 6, 7, 11 y 12)
MAX_RETRIES_SINGLE_SUBPROBLEM=1  TOKENS=131482/100343  COSTE_TOTAL=$0,144272
```

## Sonda de las pruebas PG (Claude, temporal y retirada)

Se usaron copias con correcciones temporales mínimas para destapar todos los fallos de una vez. Después se restauraron los ficheros exactos de DeepSeek, verificados por huella (`ebc7b778…`, `7492d3f5…`, `ed8cfc04…`).

| Fallo | Causa | Parte |
|---|---|---|
| ImportError de `User` | Se importaba de `government.models` | Prueba |
| F401 `_crear`, `_patch`, `_put` | Imports sin usar | Prueba |
| P1: el evento elegido era el del contrato | Faltaba filtrar por el título «Prórroga…» | Prueba |
| **P6: 500 en el PATCH** | `vigente_desde < fecha_instrumento` choca con el CHECK de la base; falta validarlo en el servicio | **Producto** (defecto del diseño de Claude) |
| P6: esperaba 422 en el PATCH por una fecha futura | Esa regla se aplica al formalizar | Prueba |
| 405 en la cobertura | Sufijo `"cobertura"` sin barra | Prueba |
| 405 al formalizar | `_put` en lugar de `_post` | Prueba |
| StopIteration en H2 | Usaba una ficha anterior a la creación del cargo | Prueba |

## Sonda E2E (Claude, temporal y retirada)

La E2E de DeepSeek se ejecutó contra la pila efímera con correcciones temporales hasta pasar entera (1/1 en 3,7 min). Después se restauraron los ficheros exactos de DeepSeek, verificados por huella (`d830e4b5…`, `9a937870…`).

| Fallo | Causa | Parte |
|---|---|---|
| 428 en la cobertura y al formalizar el contrato | Faltaba el If-Match | E2E |
| Modo estricto con 4 textos | Faltaba `.first()` | E2E |
| Región del control del firmante | Era un `aria-label`, no un texto; además faltaba `exact` | E2E |
| 401 del administrador | Tenant inventado «pruebas» | E2E |
| 3 declaraciones sin usar | Lint | E2E |

## Mutaciones (sonda de Claude, restauradas por huella)

Huellas restauradas: `0ee8c85c…` (servicio de modificaciones) y `9bdfef97…` (service_contratos).

| Mutación | Prueba que la mata |
|---|---|
| M1: no exigir cobertura al formalizar | `test_aumento_exige_cobertura_exacta` |
| M2: comparar el límite con el monto base en lugar del nuevo | `test_autoridad_contra_monto_efectivo_nuevo` |
| M3: sin guarda de compromisos al reducir | `test_reduccion_bloqueada_por_compromisos` |
| M4: el compromiso ajeno no descuenta | `test_cdp_sin_expediente_comprometida` |
| M5: moneda literal en la CDP (sin canonical) | `test_cdp_ved_cubre_contrato_ves` |
| M6: SIN_TASA tratado como dentro del límite | `test_firmante_usd_sobre_contrato_ves` |

## Implementado por Claude

Arqueología, fuentes, delta de CNT-01, Spec, plan, gate y tareas. También los briefs, la auditoría y la aplicación literal de los parches, la regeneración de las fixtures OpenAPI, las sondas temporales (retiradas), las mutaciones (restauradas), la evidencia y las matrices.

**Ninguna línea de producto, prueba, E2E ni migración es de Claude**, con una única excepción documentada: quitar una línea duplicada que dejó un ancla defectuosa del brief (llamada 8).
