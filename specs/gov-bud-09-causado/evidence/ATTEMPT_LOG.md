# BUD-09 · Registro de intentos de DeepSeek (2026-11-17)

- **Llamadas:** vía el subagente `deepseek-executor`, sin `session_id` ni `thinking`, `stream: true` y `max_tokens` explícito. `deepseek-v4-pro` para la lógica; `deepseek-v4-flash` para las correcciones puntuales.
- **Egreso:** antes de cada llamada, `EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0` con `herramientas/egress.py`. Solo salieron código y datos sintéticos.
- **Topes:** el inicial era 8. La dueña lo amplió cuatro veces, con el diagnóstico listo: hasta 14, 20, 26 y 29. Se usaron 27.
- **Autoría:** DeepSeek escribió todo el código y todas las pruebas. Claude diseñó, redactó los encargos, auditó, aplicó tal cual y verificó; no escribió código de producto.

| N.º | Encargo | Modelo | Tokens (entrada/salida) | Coste (USD) | Auditoría |
|---|---|---|---|---|---|
| 1 | C1 · T002: modelos, migración 0123, CTL-01, auditoría, permisos, MFA y guarda de BUD-08 | pro | 11773/17173 | 0,020062 | **REJECT** parcial: nombres de restricción de más de 63 caracteres y literales de competencia inventados (defectos del encargo); disparadores registrados en la tabla equivocada |
| 2 | C2 · T003: servicio, esquemas y API | pro | 8651/28102 | 0,028212 | **REJECT**: 134 errores de mypy y uno de sintaxis. Causa: el encargo prometía columnas sin incluirlas (defecto de Claude) |
| 3 | C2r1 · T003 con el código real del modelo (varios mensajes) | pro | 19818/32000 | 0,036350 | **PASS** con correcciones posteriores; respuesta truncada por longitud pero utilizable |
| 4 | C3 · T004: pruebas backend | pro | 6765/12344 | 0,013682 | **REJECT**: vallas, guardas ausentes, GET hecho con POST |
| 5 | C3r1 · T004 | pro | 9643/13850 | 0,016134 | Aplicado; el diagnóstico halló defectos de prueba (imports, `activated_at`, patrón de código, tipo de gasto compartido, saldos agotados, línea sin id, usuario de otra empresa) |
| 6 | C4 · correcciones de modelo, migración y pruebas (5 mensajes) | pro | 26987/20062 | 0,029083 | **PASS** parcial: registro de disparadores por tabla; literales de competencia reales |
| 7 | C5 · condición del disparador hijo, Literal de SoD, pruebas | pro | 6850/7497 | 0,009392 | **PASS** parcial |
| 8 | C6 · servicio: completitud solo al formalizar, documentos, R3 | pro | 3547/2076 | 0,003239 | **PASS** parcial |
| 9 | C7 · funcionario y unidad antes de la instantánea | pro | 2289/1830 | 0,002588 | **PASS** parcial (quedó el autoflush de la unidad) |
| 10 | C8 · frontend A: api.ts, políticas, numeración | pro | 7178/14499 | 0,015737 | **REJECT** parcial: 9 errores de TS (Checkbox inexistente, `loading` en AsyncButton, `status` como objeto, null frente a undefined) |
| 11 | C9 · F1–F4 frontend + B1 (unidad) + B2 (`func.max`) | pro | 2712/1780 | 0,002728 | 12/13 bloques **PASS**; bloque 3 **REJECT** (no corregía el tipo del parámetro) |
| 12 | C9r1 · tipo del parámetro de `convertirDocumentos` | flash | 600/179 | 0,000134 | **PASS** |
| 13 | C11 · disparador PG `json = json`, MFA en hilos, versión de la regla SoD | flash | 1234/860 | 0,000414 | **PASS** (4/4) |
| 14 | C10 · frontend B completo | pro | 4929/3094 | 0,004725 | **REJECT**: 1 de 6 ficheros; rutas de importación inventadas |
| 15 | C10r1 · lista + registro + tipo + prueba de carrera | pro | 5270/4777 | 0,006338 | **PASS** (7/7): backend 24/24 en PG |
| 16 | C10b · nuevo/editar | pro | 4042/7406 | 0,008091 | Aplicado para diagnóstico: 9 importaciones sin uso, interfaces duplicadas, `split(":")`, errores de campo mal ubicados |
| 17 | C10c · detalle + correcciones B1–B6 de C10b | pro | 4809/7256 | 0,008294 | 13/13 **PASS**; queda `onConfirm` sin Promise |
| 18 | C12 · Vitest (3 mensajes) + `onConfirm` | pro | 19966/10164 | 0,017417 | Aplicado para diagnóstico: 12 de 26 en rojo (firma de ApiError, `<option>` prematuro, rótulos duplicados, `type` acumulativo, rama de mock) |
| 19 | C12r1 · correcciones de Vitest | pro | 2148/1699 | 0,002413 | **REJECT**: bloques sin ruta, SEARCH con líneas no contiguas, ApiError sin importar, solapes |
| 20 | C12r2 · ídem (último reintento) | pro | 2972/2717 | 0,003546 | **PASS** (18/18; un bloque redundante omitido): 19/26 |
| 21 | C13 · rótulo de «Concepto» (accesibilidad) + consultas de rótulos | flash | 1296/636 | 0,000360 | **PASS**: 25/26 |
| 22 | C13r1 · consulta por aria-label + prueba que mata M2 | flash | 1612/1372 | 0,000592 | **PASS** en Vitest (26/26); la prueba backend nueva falla por diseño del encargo (DOCUMENTARY sin documentos, defecto de Claude) |
| 23 | C13r2 · disparador de la prueba 25 | flash | 778/424 | 0,000210 | **PASS**: PG 25/25; M2 muerto |
| 24 | C14 · E2E y humo | pro | 6269/6518 | 0,008287 | Aplicado para diagnóstico: `strict mode` y `goto` contra la API |
| 25 | C15 · localizadores del E2E, fecha de negocio, estrechamiento de tipo | flash | 1675/1105 | 0,000526 | 6/8 **PASS**; 2 **REJECT** (sangría de 8 espacios frente a 4) |
| 26 | C15r1 · los 2 bloques rechazados | flash | 865/273 | 0,000180 | **PASS**: E2E 1/1 |
| 27 | C16 · `__scope__` en 7 modelos + recuentos de catálogo (permisos 177, SoD con BUD-09), hallados por la PG completa | flash | 947/832 | 0,000366 | **PASS** (10/10): guardas en verde |

```text
DEEPSEEK_CALLS=27 (tope inicial 8; ampliado por la dueña a 14, 20, 26 y 29)   OWNER_EXCEPTION_USED=4
DEEPSEEK_RETRIES=12   PATCHES_REJECTED=8 (total o parcial)   COSTE_TOTAL_USD=0,239100
CLAUDE_PRODUCT_CODE_LINES=0
```

## Correcciones de forma (FORMAT_ONLY), registradas

- Marcadores SEARCH/REPLACE sueltos o con vallas ```text, normalizados a los literales de 7 caracteres.
- División de bloques con líneas no contiguas, ampliación del SEARCH de la API con el `]` colgante, y `--todas` en líneas idénticas repetidas cuando el encargo lo pedía.
- Omisión de bloques redundantes contenidos en otro bloque del mismo envío (C12r2 bloque 10) y de bloques rechazados (C9 bloque 3; C15 bloques 2 y 3, reenviados en C15r1).
- `ruff --fix --select I001` (orden de importaciones en `main.py` y en el servicio) y `ruff --fix --unsafe-fixes --select F841` en la prueba.
- Parches temporales de diagnóstico aplicados al árbol y restaurados byte a byte (`cmp`); prueba temporal `test_zz_diag_b09.py` creada y borrada.

## Defectos de diseño de Claude (encargos)

1. C1: nombres de restricción por encima de 63 caracteres y literales de competencia que no existen en el modelo.
2. C2: el encargo prometía definiciones de columnas que no incluía.
3. C10b: indicaba «envolver varios hijos en un `<div>`» dentro de `FormField`, que inyecta su `id` en su único hijo. Rompió el rótulo de «Concepto» (lo corrigió C13).
4. C13r1: pidió una política DOCUMENTARY con `documentos=[]`, combinación que el dominio rechaza por diseño.
5. Nombres de variables de puertos del runner E2E equivocados en la primera corrida: no afectó al código, solo a una corrida que no llegó a empezar (RC 70).
6. No pedir `__scope__` en el encargo de modelos (C1/C4), aunque el patrón hermano lo declara: lo destapó la PG completa (C16).
