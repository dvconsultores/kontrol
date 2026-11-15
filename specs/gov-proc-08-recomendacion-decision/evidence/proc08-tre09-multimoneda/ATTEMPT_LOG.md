# ATTEMPT_LOG · delta X08 (PROC-08 × TRE-09 multimoneda), 2026-11-15

Modelo: deepseek-v4-pro en todas las llamadas, sin session_id ni thinking. Tope: 8 llamadas; objetivo 3–5; se usaron **7**. OWNER_EXCEPTION_USED=0.

| Llamada | Encargo | Entrada/salida (tokens) | USD | Resultado de la auditoría |
|---|---|---|---|---|
| 1 | C1 backend: columna + 0115, evaluación multimoneda, instantánea, auditoría, salida, fijaciones | 5.855 / 5.999 | 0,007766 | 14/15 bloques PASS. Bloque 8 REJECT: línea partida («str(ofe» / «rta_id))») que rompía la sintaxis. mypy +2 [index] |
| 2 | C2 pruebas PG + reintento 1 de C1 (bloque 8 y mypy) | 5.925 / 6.834 | 0,008413 | PASS al aplicar. En PG: `_control` inventó `?acto_id=` (422); el evento ISSUED perdía `conversion` (2.ª lista blanca en service_expedientes) |
| 3 | C3 pantalla: conversión en el panel y en la ficha + Vitest | 4.235 / 2.482 | 0,004002 | PASS; tsc, eslint y Vitest limpios a la primera |
| 4 | C4 E2E + reintento de C2 (K1, K3) + corrección de C1 (K2, lista blanca de auditoría) | 3.037 / 2.545 | 0,003535 | K1–K3 PASS. Bloques E2E 2 y 3 REJECT: adjuntarDocumentoApi sin tipo.id, `estructura.unidadId` inexistente y axe con import dinámico en lugar de AxeBuilder |
| 5 | C5 reintento 1 de la E2E (bloques 2 y 3) | 3.365 / 1.831 | 0,003057 | PASS; tsc: `admin` redeclarado (TS2451) |
| 6 | C6 reintento 2 de la E2E (TS2451) + corrección de C1 (conversion None en SIN_TASA, que pedía el encargo) | 533 / 230 | 0,000432 | PASS; PG 46/46, E2E 1/1 |
| 7 | C7 corrección de integración tras fusionar CNT-01 (P2): `ESTADOS_LIMITE` recupera `MONEDA_DISTINTA` para el firmante de CNT-01 | 777 / 264 | 0,000568 | PASS (1 bloque); CNT-01 + PROC-08 34/34; E2E decisión + contratos 2/2 |
| **Total** | | **23.727 / 20.185** | **0,027773** | |

Reintentos por subproblema (máx. 2 por causa raíz): C1 3 correcciones de tres causas distintas (sintaxis/mypy, lista blanca de auditoría, SIN_TASA);
C2 1 (helper con parámetro inventado); E2E 2 (firmas y axe; redeclaración). Ninguna causa raíz necesitó un tercer intento. C7 es un subproblema nuevo (regresión de fusión), resuelto al primer intento.

Claude no escribió código, pruebas, migración ni QA: solo aplicó bloques auditados. Los bloques rechazados se omitieron con `--omitir` y se reenviaron
corregidos por DeepSeek. CLAUDE_SEMANTIC_*_WRITTEN=0. FORMAT_ONLY_EDITS=0.
