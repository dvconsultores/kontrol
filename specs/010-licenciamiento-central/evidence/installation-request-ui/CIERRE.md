# Cierre · Solicitud de activación en «Mi licencia» (2026-11-16)

- Base: 7ac62f9 = origin/develop. P2 (CNT-08) no publicó nada durante el delta. P1_P2_OVERLAP=0.
- El backend no cambia y no hay migración. ALEMBIC_HEAD_COUNT=1.
- Las métricas de Gobierno no cambian: 420/1268 gates y 41/122 OWNER_UAT_READY.

## Ficheros

| Fichero | Cambio |
|---|---|
| `src/api/types.ts` | `InstallationRequest` |
| `src/lib/solicitud-de-activacion.ts` | Nuevo: validación, serialización, nombre seguro y descarga con Blob |
| `src/pages/MiLicenciaPage.tsx` | Sección PENDING y dos acciones con estado común |
| `src/pages/MiLicenciaPage.test.tsx` | LICREQ-01..17 y pruebas unitarias |
| `src/tests/architecture-company.test.ts` | Lista cerrada `DESCARGAS_DE_CONTENIDO_LOCAL`, con prueba de que esos ficheros no hablan con la API |
| `e2e/licencia.spec.ts` | E2E-LIC-11 |

## Verificación

| Prueba | Resultado |
|---|---|
| Vitest dirigido (MiLicenciaPage) | 23/23 |
| Vitest completo (Node 22) | 2109/2109 |
| tsc -b y eslint | 0 errores |
| build | OK |
| E2E `e2e/licencia.spec.ts` (`qa/e2e-run.py --con-analizador`, `--retries=0`, run r20261115t233107p2423903nc7a4f8) | 11/11, incluida E2E-LIC-11 |
| Backend dirigido: `test_license_access` + `test_license_trust_anchor` (PG) | 72/72 |

E2E-LIC-11:
- detalle simulado como PENDING;
- descarga real de `/license/installation-request`;
- nombre seguro;
- JSON del archivo igual a la respuesta;
- `installation_id` y `public_key` presentes;
- sin «PRIVATE KEY».

La E2E se corrió antes de L3–L5, que solo tocan una prueba unitaria de arquitectura.

La adaptación responsive (1280/390/320) se resuelve por diseño de clases (`flex-col sm:flex-row`, `w-full sm:w-auto`). No se midió en la E2E.

## DeepSeek (deepseek-v4-pro)

| Llamada | Encargo | Entrada/salida | USD | Auditoría |
|---|---|---|---|---|
| L1 | Tipo, lib, página, Vitest y E2E | 7.223 / 12.197 | 0,0138 | Tipo, lib y página PASS. Pruebas REJECT (esperaban en el DOM notificaciones simuladas; `toThrow` con cadena). E2E REJECT (SEARCH sin coincidencia y sin import) |
| L2 | Reintento 1: pruebas y E2E | 8.052 / 6.673 | 0,0093 | PASS |
| L3 | Subproblema nuevo: prueba de arquitectura de descargas | — | — | Perdida por caída de red de la estación (EAI_AGAIN), sin respuesta |
| L3 bis | Reenvío de L3 | 975 / 879 | 0,0008 | Aplicada. Falla por un defecto de diseño de Claude: `"/api/"` casaba con el alias `@/api/` |
| L4 | Reintento 1 de L3 | 374 / 87 | 0,0002 | REJECT: el SEARCH tenía 8 espacios porque así lo dictó Claude; el fichero tiene 6 |
| L5 | Reintento 2: L4 con la sangría real | 386 / 87 | 0,0002 | PASS |

- **5 llamadas con respuesta** y 1 perdida. Coste: 17.010 / 19.923 tokens, **USD 0,0243**.
- El objetivo era de 1 a 3 llamadas y se superó. El tope duro de 8 se respetó y no hubo excepción de la dueña.
- Reintentos por subproblema: como máximo 2.
- CLAUDE_SEMANTIC_CODE_WRITTEN=0. FORMAT_ONLY_EDITS=0: los dos ficheros completos se aplicaron borrando el anterior, que es aplicación mecánica.

## Seguridad

```
PRIVATE_KEY_READ=0  PRIVATE_KEY_EXPOSED=0  LOCAL_STORAGE_WRITE=0  SESSION_STORAGE_WRITE=0
FULL_PAYLOAD_LOGGED=0  NEW_ENDPOINT_CREATED=0  API_CONTRACT_CHANGED=0
```
