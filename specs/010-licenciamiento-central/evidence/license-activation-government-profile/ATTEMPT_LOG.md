# Registro de intentos · activar licencia desde «Mi licencia» + perfil KONTROL Gobierno

Modelo: `deepseek-v4-pro` en todas las llamadas. Tope global del ciclo: 8 llamadas; objetivo 3..5. Máximo 2 reintentos por subproblema.
OWNER_EXCEPTION_INHERITED=0.

| # | Encargo | Subproblema | Tokens (entrada / salida) | USD | Resultado de la auditoría |
|---|---|---|---|---|---|
| 1 | D1 | Backend: `minimum_version` (5c), perfil, `/gobierno/modulo`, siembra QA, pruebas MINV/PERF | 9.476 / 6.565 | 0,0098 | 12/12 bloques aplicados. REJECT parcial: mypy `union-attr` (doble `fullmatch`), ruff I001/F401 en la prueba, import del servicio vía `government.api`, docstring larga, caso extra no pedido en PERF-05 |
| 2 | D2 | Frontend: superficies, `usePerfilDeInstalacion`, menú, `RutaDePerfil`, trampa de foco | 6.177 / 7.738 | 0,0094 | 18/19 (un bloque nulo, SEARCH = REPLACE, omitido). REJECT parcial: describe anidado con `});` sobrante (TS1128) y variable sin uso |
| 3 | D3 | Frontend: lib del paquete, `ActivarLicencia`, integración y pruebas LICACT | 10.028 / 14.694 | 0,0171 | 8/8 aplicados. REJECT parcial: `Mock` sin uso. 38 pruebas fallaban por `File.prototype.text`, que jsdom 25 no tiene (diagnóstico de Claude) |
| 4 | D12b | Reintento 1 de D1 + reintento 1 de D2 | 3.913 / 3.596 | 0,0048 | Salió sin rutas ni saltos entre bloques (formato normalizado por contenido). Bloque 5 RECHAZADO: tocaba otra prueba y dejaba otra variable sin uso. `User` siguió sin quitarse |
| 5 | D13c | Reintento 2 de D1, reintento 2 de D2, reintento 1 de D3 | 4.558 / 2.032 | 0,0038 | 12/12 aplicados. Defectos: reemplazó un import en vez de añadirlo (TS2304); la expectativa de LICACT-08 sin el punto; el foco inicial destapó un bucle del efecto del diálogo |
| 6 | D4 | E2E `licencia-perfil.spec.ts`, helper de reauth de interfaz, proyecto dependiente | 5.033 / 3.707 | 0,0054 | 5/5 aplicados. Defecto: `toBeVisible` sin `expect` (TS2339) |
| 7 | D5 | Reintento 2 de D3, **tarea dividida** del diálogo (D2 sin reintentos), reintento 1 de D4 | 1.976 / 672 | 0,0014 | 7/7. Un bloque coincidía 2 veces (`onCancel();`): aplicado a ambas apariciones de forma mecánica, sin efecto funcional distinto |
| 8 | D6 | Tareas divididas: contraste de los `<dt>` (Axe 2,56), pantalla de Gobierno de la E2E, añadir `licencia-perfil` a `qa/e2e_corrida.py` | 1.439 / 1.149 | 0,0016 | 19 bloques. Varios SEARCH idénticos y solapados: se aplicó el bloque 1 a todas sus apariciones, que equivale exactamente a los 17 reemplazos pedidos; verificado: 0 `text-text-400` y 17 `text-text-500` |
| 9 | D7 | **Excepción 1 de la dueña**: aserción final de la E2E (en base nueva, 404 `GOV_ENTITY_NOT_FOUND`, no 403 `MODULE_NOT_ENTITLED`) | 870 / 346 | 0,0007 | PASS. E2E 1/1 |
| 10 | D8 | **Excepción 2 de la dueña**: tres guardas de arquitectura (inventario de `ejecutarPython`, puerta propia en `ActivarLicencia`, `as unknown as` prohibido en E2E) | 1.456 / 573 | 0,0011 | PASS. Vitest 2256/2256 |
| 11 | D9 | **Excepción 3 de la dueña**: la guarda `test_e2ecorrida_14` fijaba la orden canónica sin `--project=licencia-perfil` (regresión hallada en la PG completa) | 911 / 453 | 0,0008 | PASS. 1/1 bloque; `test_e2e_corrida.py` sobre PG |

**Total (11 llamadas; 8 del tope y 3 autorizadas por la dueña):** 45.837 tokens de entrada, 41.525 de salida, **USD 0,0560**.
OWNER_EXCEPTION_USED=3.

Defectos de diseño de Claude hallados en la verificación:
- el `as unknown as` del encargo D4;
- no prever las guardas de inventario y de cobertura de puertas;
- suponer que una pantalla de Gobierno respondería 200 en una base sin ente;
- no prever que el ejecutor canónico enumera los proyectos;
- no prever que `test_e2ecorrida_14` fija esa enumeración.

## Diagnósticos de Claude (causa raíz, sin escribir código)

- `minimum_version`: el contrato de licencia lo exige antes de aplicar, y no había ninguna comparación. Se valida en el paso 5c, después del anti-retroceso, para que REVC-08 siga dando `LICENSE_REVISION_CONFLICT`.
- Conflicto entre el perfil y la E2E canónica: escalado a la dueña. OD-LICACT-01 = A.
- jsdom 25 sin `File.prototype.text`: polyfill solo de prueba; el producto usa `file.text()`, como pide el encargo.
- `ConfirmationDialog`:
  - defecto previo: `confirmRef` nunca se conectaba, porque `AsyncButton` no reenviaba `ref`, así que el foco inicial no existía;
  - al corregirlo apareció un bucle: el efecto dependía de `onCancel`, y `ReauthProvider` pasa uno nuevo en cada render, de modo que el foco saltaba a la contraseña con cada tecla. Se ató el efecto solo a `open`.
- La E2E canónica enumera sus proyectos en `qa/e2e_corrida.py`: el proyecto `licencia-perfil` no corría sin añadirlo allí.

## Retoques de formato de Claude (FORMAT_ONLY_EDITS)

1. D12b: rutas asignadas por contenido y saltos de línea entre bloques.
2. D5: un SEARCH con dos coincidencias, aplicado a ambas.
3. Egreso: en D1 se sustituyó un literal sintético de contraseña de pruebas por la importación de `mfa_mundo.CONTRASENA`. En D3 se describieron los marcadores PEM en vez de citarlos. En D4, las 9 alertas `ENV_FILES` eran falsos positivos (`process.env.<NOMBRE>`, sin valores).

CLAUDE_SEMANTIC_CODE_WRITTEN=0 · CLAUDE_SEMANTIC_TESTS_WRITTEN=0 · CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0 · CLAUDE_SEMANTIC_QA_WRITTEN=0
