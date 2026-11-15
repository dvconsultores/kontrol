# ATTEMPT LOG · BUD-08

DeepSeek: deepseek-v4-pro, 8 llamadas (tope 8; ninguna excepción de la dueña).

| # | Encargo | Ficheros | Resultado | Tokens in/out | USD |
|---|---|---|---|---|---|
| 1 | C1 datos, 0113, permiso, auditoría, esquemas, router y fijaciones | 15 | AUDIT_PASS 19/19 bloques; un import sin uso, corregido en C7 | 11.737 / 10.186 | 0,01397 |
| 2 | C2a fórmula única de BUD-06 sin doble conteo y guarda de CDP en uso | 1 | AUDIT_PASS 8/8 | 5.267 / 4.837 | 0,00650 |
| 3 | C2b servicio de compromisos | 1 | Aplicado tal cual. Defectos: imports de módulos inexistentes, firma de `_usuarios_por_ids`, «» en lugar de None y un Decimal(generador) inválido | 9.277 / 9.735 | 0,01251 |
| 4 | C3 pruebas PG (13) | 1 | Llegó sin envoltura; se envolvió como fichero nuevo (formato). Defectos: motivos de menos de 10 caracteres y un respaldo `return 0.00` | 6.855 / 7.654 | 0,00964 |
| 5 | C4 pantalla, columnas de BUD-06 y Vitest | 6 | Llegó con cercas y sin rutas; se atribuyeron por contenido (formato). 20/20 aplicados | 11.125 / 11.121 | 0,01452 |
| 6 | C5 E2E | 1 | AUDIT_PASS; 1/1 al primer intento | 6.812 / 5.895 | 0,00809 |
| 7 | C7 corrección 1 (C2b, esquema y pruebas) | 3 | 22 aplicados. El bloque 10 (SEARCH == REPLACE) se omitió por no tener efecto. Los bloques 12 y 13 se rechazaron por SEARCH no único | 4.921 / 3.355 | 0,00506 |
| 8 | C8 corrección 2 (JSON en DISTINCT, claves de expediente, moneda VES de prueba, agotamiento del crédito 407, frontend) | 5 | AUDIT_PASS 16/16 | 3.632 / 2.026 | 0,00334 |
| 9 | C9 aislamiento: require_module como último parámetro en las 4 rutas GET. **Autorizada por la dueña** tras el tope de 8 | 4 | AUDIT_PASS 4/4. Llegó sin línea de ruta; se añadió la del único fichero objetivo (formato) | 1.839 / 943 | 0,00162 |

**Total:** 61.465 de entrada / 55.752 de salida · USD 0,0752. Fueron 9 llamadas: el tope era 8 y la 9.ª la autorizó la dueña solo para este ciclo.

**Ajustes de formato de Claude (sin contenido):**
- envoltura de C3;
- rutas y cercas de C4;
- línea de ruta de C2b;
- línea de ruta de C9;
- `ruff --fix --select I` (orden de imports) en service_presupuesto_compromiso.py.

**Bloques rechazados:** C7 #12 y #13 (SEARCH no único). Se corrigieron en C8.

**Diagnóstico:**
- copia temporal `tests/test_diag_b08.py` (ente en VES), borrada después;
- un intento de shim sobre código de producto fue denegado y no se hizo.

CLAUDE_SEMANTIC_*_WRITTEN = 0.
