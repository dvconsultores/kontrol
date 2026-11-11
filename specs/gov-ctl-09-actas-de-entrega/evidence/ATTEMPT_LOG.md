# ATTEMPT_LOG · CTL-09 (2026-11-11)

Política §6: tope 8 llamadas por ciclo (objetivo 2–4) y 2 reintentos por subproblema.

```text
DEEPSEEK_CALLS_TOTAL=10
DEEPSEEK_CALLS_WITHIN_CAP=8
DEEPSEEK_CALLS_OWNER_AUTHORIZED_OVER_CAP=2   (K7, K8; decisiones de la dueña en este ciclo)
PROCESS_DEVIATION_GLOBAL_DEEPSEEK_CALLS=1    (autorizada; no oculta)
MAX_RETRIES_PER_SUBPROBLEM=1                 (backend: K1b -> C1 -> C2; E2E: K5 -> K6)
COST_USD≈0.0908
CLAUDE_AUTHORED_PRODUCT_CODE=0
```

| # | Encargo | Modelo | Tokens in/out | Coste USD | Bloques | Resultado |
|---|---|---|---|---|---|---|
| 1 | K1a backend: modelos, disparadores, migración, cableado | v4-pro | — | 0,0136 | 20 | 18 aplicados; 2 rechazados (anclas de cabeza mezcladas por el encargo) → K1b |
| 2 | K1b servicio, esquemas, API, pruebas ae01..ae08 | v4-pro | — /21.467 | 0,0236 | 10 | 10 aplicados (4 rutas sin prefijo `resources/backend/`, normalizadas y declaradas) |
| 3 | C1 corrección 1 de K1b (D1..D10) | v4-pro | 8.788/10.140 | 0,0126 | 38 | 36 aplicados; 12 y 17 omitidos porque se solapan con 13 y 18 (anclas solapadas del encargo); delimitadores convertidos (formato, declarado) |
| 4 | C2 reintento 1 (G1..G9) | v4-pro | 3.092/3.315 | 0,0042 | 14 | 14 aplicados; faltó el import de PermissionDeniedError (ancla no dada) → B1 en K3a |
| 5 | K3a frontend 1 + B1 | v4-pro | 10.714/9.409 | 0,0128 | 13 | 11 aplicados; rechazados 9 (SEARCH = REPLACE) y 10 (estructura inventada de EXENTOS) → K3b |
| 6 | K3b ficha + P1..P3 | v4-pro | 10.982/8.775 | 0,0124 | 8 | 8 aplicados |
| 7 | K5 E2E + Q1..Q3 | v4-pro | 7.842/4.857 | 0,0076 | 6 | 6 aplicados; la E2E falló en preparación (permisos) |
| 8 | K6 reintento 1 de la E2E (E1..E10) | v4-pro | 2.437/2.183 | 0,0030 | 9 | 9 aplicados; dejó una variable sin uso |
| 9 | K7 (9/8, autorizada) variable sin uso | v4-flash | 283/62 | 0,00006 | 1 | aplicado |
| 10 | K8 (10/8, autorizada) integración con Spec 021: migración 0101→0102 y 4 constantes | v4-flash | 795/462 | 0,00024 | 5 + RENAME | aplicado; `git mv` ejecuta la línea RENAME de DeepSeek (caso A) |

## Lo que hizo Claude (mecánico, declarado)

- **Formato:** `ruff --fix --select I001` sobre `main.py`, `api_actas.py` y `service_actas.py`. Solo ordena imports.
- **Normalización:** prefijo de ruta en 4 bloques de K1b y conversión de delimitadores en C1. El contenido de SEARCH/REPLACE
  no se tocó.
- **Diagnóstico fuera del repositorio:** venv 3.13 y *shims* de pytest; copias temporales de las pruebas y de la E2E,
  borradas tras cada corrida y nunca aplicadas ni confirmadas. Sirvieron para reunir todos los fallos en un solo encargo.
- **Git:** resolución `--ours` de 4 conflictos, sobrescrita después por K8; `git mv` según la línea RENAME.
- **Regeneración de instantáneas:** `qa/fixtures_de_frontend.py`.

## Defectos de encargo atribuibles a Claude

1. K1a agrupó tres anclas de cabeza en una sola etiqueta.
2. C1 dio ventanas de ancla solapadas.
3. C2 no incluyó el ancla del import.
4. K5 redactó de forma ambigua la lista de permisos («sin los de gobierno_rendicion»).
