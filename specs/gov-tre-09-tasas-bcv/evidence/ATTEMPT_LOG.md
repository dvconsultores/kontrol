# ATTEMPT_LOG · TRE-09 (deepseek-v4-pro)

| # | Encargo | Bloques | Resultado de la auditoría | Tokens in / out | USD |
|---|---|---|---|---|---|
| 1 | C1 monedas, modelo, 0114, capacidades, MFA, auditoría, ResourceKind, esquemas, router, fijaciones | 22 | 21 aplicados. Rechazado el #4 (setup/api.py: SEARCH con el orden de líneas invertido) | 11.348 / 11.866 | 0,01515 |
| 2 | C2 service_tasas, consumidor BUD-08, vista previa, normalización BUD-01/06/08 | 19 | 19 aplicados. Defectos: `tenant_id` en el constructor (columna inexistente), imports sin uso, PDF sin la procedencia | 10.871 / 10.661 | 0,01389 |
| 3 | C3 pruebas PG (12) + ajuste de BUD-08 | 2 | Aplicados. Defectos: preparación con formas de respuesta inexistentes, variable sin uso, filtros sin guarda de None | 6.027 / 8.972 | 0,01043 |
| 4 | C6 corrección 1 de C1/C2 | 8 | AUDIT_PASS 8/8 (setup/api, tenant_id, imports, UP037, `date` en N9, PDF con la tasa) | 2.229 / 1.431 | 0,00222 |
| 5 | C4 pantalla Tasas oficiales, menú, conversión en Compromisos, Vitest | 31 (dos borradores) | Se tomó solo el borrador final, con cercas y sin rutas (atribución por contenido = formato). 15 aplicados; rechazado el #16 (SEARCH inválido). Defectos: onChange, ErrorState, hook tras return, bloque dentro del FormField, prueba con contextos inexistentes | 8.879 / 28.906 | 0,02901 |
| 6 | C7 corrección de la preparación de las pruebas PG | 7 | AUDIT_PASS 7/7 | 3.745 / 2.358 | 0,00368 |
| 7 | C5 E2E y humo UAT | 3 | Aplicados. Desviaciones: partida 401.01 con nivel 1, aserción con arrayContaining | 8.344 / 8.107 | 0,01057 |
| 8 | C8 corrección final (pruebas PG, página, hook, Vitest) | 25 | 23 aplicados; rechazados #9 y #11 (SEARCH idéntico, no único). **Último dentro del tope de 8** | 10.839 / 6.970 | 0,01067 |
| 9 | C9 **autorizada por la dueña**: bloque dentro del FormField, cabeceras de concurrencia, Vitest, E2E | 15 | 15 aplicados; el #6 se aplicó al final porque su SEARCH era prefijo de otro (orden de aplicación, sin cambiar el contenido) | 4.191 / 3.045 | 0,00447 |
| 10 | C10 **autorizada**: presentación de tasas (formatMoney ignora los decimales en un string) | 5 | AUDIT_PASS 5/5 | 2.182 / 1.089 | 0,00190 |
| 11 | C11 **autorizada**: concurrencia FOR SHARE en tasa_aplicable + selector de la E2E | 3 | AUDIT_PASS 3/3 | 1.103 / 767 | 0,00115 |

**Total:** 69.758 de entrada / 84.172 de salida · USD 0,1031.

**Llamadas:** 11. El tope era 8; la dueña autorizó las 9 a 12 en dos decisiones. La 12, de reserva, no se usó.

**Reintentos:** 6 llamadas correctivas (C6 a C11). Excedieron el máximo de 2 por subproblema:
- las pruebas PG: C7, C8 y C9;
- el frontend: C8, C9 y C10.

Ambas desviaciones quedaron cubiertas por las autorizaciones expresas.

**Ajustes de formato de Claude (sin contenido):**
- prefijo de ruta en las fijaciones de C1;
- elección del borrador final de C4, retirada de cercas y rutas;
- `ruff --select I` (orden de imports) en main.py y service_presupuesto_compromiso.py;
- orden de aplicación del #6 de C9.

**Retiro mecánico:** se retiró la prueba de página de C4 para que C8 la reescribiera como fichero nuevo.

**Diagnóstico:** copias temporales `tests/test_diag_t09.py` (usuario de compromiso; impresión del 422 de la carrera), borradas después.

CLAUDE_SEMANTIC_*_WRITTEN = 0.
