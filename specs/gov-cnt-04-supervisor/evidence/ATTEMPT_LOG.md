# ATTEMPT_LOG · CNT-04 supervisor / responsable del contrato (2026-11-15)

- Modelo: deepseek-v4-pro en todas las llamadas, sin session_id ni thinking.
- Tope: 8 llamadas. La dueña autorizó la 9.ª y la 10.ª durante el ciclo.
- Se usaron **10**. OWNER_EXCEPTION_USED=1 (las dos llamadas extra).

| Llamada | Encargo | Entrada/salida (tokens) | USD | Resultado de la auditoría |
|---|---|---|---|---|
| 1 | C1 backend completo: modelo y guard, 0117, servicio, API, permiso, MFA, auditoría, SoD y fijaciones | 8.835 / 12.048 | 0,014325 | 19 bloques aplicados. Rutas con barra inicial: normalizadas (solo formato). Defectos: `date` sin importar en la API (F821), relación inexistente `sustituye`, mypy union-attr y type-var, 2 F841 |
| 2 | C2 corrección de C1 (K1–K7) + pruebas PG | 4.521 / 6.480 | 0,007604 | App y K7 PASS. Pruebas REJECT. La sonda en PG (sin aplicar) dio 9/11 rojos y destapó 2 defectos de app: clave de auditoría `funcionario` fuera de la lista blanca, y códigos SoD de más de 32 caracteres (error de diseño de Claude) |
| 3 | C3 pantalla y Vitest | 3.981 / 8.497 | 0,009124 | Componente PASS. Vitest REJECT: rótulos obligatorios, texto duplicado y caso c fuera de contrato |
| 4 | C4a corrección de app (A1 auditoría, A2 códigos SoD) + pruebas PG reescritas | 6.587 / 10.975 | 0,012414 | A1 y A2 PASS; formato SEARCH:/REPLACE: convertido al estándar (solo formato). Pruebas: 7/11; la sonda destapó la FK `sustituida_por_id` no diferida (defecto de diseño de Claude) y una asignación a un str |
| 5 | C4b Vitest reescrito | 4.811 / 4.168 | 0,005719 | 16/17 (caso b) |
| 6 | C6 FK diferida + designación programada (decisión de diseño de Claude) + pruebas | 7.330 / 7.844 | 0,010013 | 16 bloques PASS. REJECT: el bloque de `supervision()` (SEARCH con tramos no consecutivos) y la prueba programada (anidada, firmas inventadas). Caso b otra vez rojo |
| 7 | C7 `supervision()`, prueba programada, mensaje de éxito, caso b (dividido) y E2E | 3.619 / 3.880 | 0,004950 | 4 bloques PASS. REJECT: prueba programada (fechas del año 201) y E2E (botón buscado en el diálogo; variable sin uso) |
| 8 | C8 corrección de los rechazos de C7 | 3.925 / 3.200 | 0,004491 | PASS; faltaban las rutas de cabecera: añadidas por orden de TARGET FILES (solo formato) |
| 9 | C9 (autorizada) cierre del diálogo tras el éxito + tipo del filtro de Axe | 760 / 289 | 0,000582 | PASS; formato desordenado y reordenado (solo formato). La E2E pasó completa. La aserción de Vitest que Claude dictó era errónea |
| 10 | C10 (autorizada) aserción de Vitest | 308 / 90 | 0,000212 | PASS |
| **Total** | | **44.677 / 57.471** | **0,069434** | |

## Reintentos y causas

- Reintentos semánticos: 6 (C2, C4a, C4b, C6, C7 y C8).
- Ninguna causa raíz pasó de 2 reintentos, salvo el caso b de Vitest. Tras dos intentos fallidos por el mismo localizador se aplicó STOP → REDIAGNOSE → DIVIDE: una sola línea en C7. Después falló por otra causa (texto de la columna) y se corrigió en C8.
- C9 corrigió defectos nuevos que halló la E2E.
- C10 corrigió un error de especificación de Claude, no de DeepSeek.
- Defectos de diseño de Claude encontrados en la verificación:
  - códigos SoD de más de 32 caracteres;
  - FK no diferida en la sustitución;
  - sustitución imposible en un mismo día, resuelta con la designación programada;
  - la aserción de C9.

## Integración mecánica de Claude (sin semántica)

- Formato: normalicé la cabecera y los delimitadores de los bloques en C1, C4a, C8 y C9; el contenido no se tocó. FORMAT_ONLY_EDITS=4.
- Pruebas rechazadas:
  - las saqué del árbol para reemplazarlas por la versión corregida;
  - ejecuté dos veces, como sonda de diagnóstico, una versión rechazada, que luego borré;
  - coloqué como base, para aplicarle bloques pequeños, la versión de C4a, que es código de DeepSeek.

CLAUDE_SEMANTIC_CODE_WRITTEN=0, CLAUDE_SEMANTIC_TESTS_WRITTEN=0, CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0, CLAUDE_SEMANTIC_QA_WRITTEN=0.
