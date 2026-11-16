# Cierre · «Mi licencia» real, activación visible, perfil fail-closed y frontera del backend por perfil

Delta de la Spec 010: `spec004-license-ui-ux-profile-security-delta.md`.

**Estado:** COMPLETE en código y en pruebas. OWNER_UAT_READY se declara solo cuando una pila UAT nueva, levantada desde el SHA publicado, sirve un frontend que contiene `ActivarLicencia`. OWNER_ACCEPTED queda pendiente de la dueña.

Es un delta de licenciamiento: GOVERNMENT_PROCESS_INCREMENT=0.

## Base

- Entrada: 2f2ce4c (alembic 0121_gov_cnt09_alertas). `origin/develop` no avanzó durante el ciclo.
- MIGRATION_REQUIRED=0, ALEMBIC_HEAD_COUNT=1.

## Causa raíz

**ROOT_CAUSE = D + A.** La dueña no veía dónde cargar la licencia por dos causas:

- **D.** Las pilas UAT 16773 y 16873 se levantaron desde commits anteriores al delta de activación. El `MiLicenciaPage.tsx` que sirven tiene 0 referencias a `ActivarLicencia`.
- **A.** Ambas pilas están en FULL_ACCESS. En el HEAD 2f2ce4c, `MODOS_DE_ACTIVACION` excluía ese modo, así que aun reconstruyendo la pila la activación seguiría oculta.

## Verificación

| Comprobación | Resultado |
|---|---|
| PG completa, una vez (`qa/suite_tiempos.py --motor postgres --con-analizador`, run r20261116t142510p3096782n9a6ca7) | 5663 pasan / 6 fallan / 18 omitidas |
| Fallos de línea base | 5: imb_07 pip check, n10 ORM↔base, guard_d01 y 2 de spec019 receipt. Los mismos que en la corrida de 742882f |
| Regresión del ciclo | 1: `test_oas_14`. La guarda OpenAPI prohibía dependencias de inclusión. Corregida con las llamadas 9 y 10, autorizadas por la dueña. `test_openapi_security.py` da 46/46 |
| PG dirigida tras la corrección: OpenAPI, versión mínima, reglas y estado de reverificación | 102/102 |
| SQLite dirigida: las mismas, más gov0_ente | verde |
| Mutaciones del backend | 5/5 muertas: sin PRODUCT_PROFILE_DENIED, sin la comprobación por módulo (MIXTO), FAILURES sin MINIMUM_VERSION_*, versión en ejecución ignorada, ventas sin frontera de inclusión |
| Mutaciones del frontend | FM1–FM6 muertas |
| Vitest | 2304/2304 |
| tsc, eslint y build | 0 errores, build OK |
| ruff | limpio |
| mypy (`app`) | 157 errores, igual que la base 2f2ce4c |
| E2E `licencia-perfil` (run r20261116t142245p3093732n066c3b) | 4/4 con 0 reintentos. LICUX-E2E-01..04: PENDING autorizado, reemplazo en FULL_ACCESS, sin `license:create` y perfil fail-closed. Axe y desbordamiento comprobados a 1280/390/320 |

## Evidencia visual

`capturas/`: 12 PNG, de los estados PENDING autorizado, vista previa, sin permiso y Gobierno tras activar (FULL_ACCESS), cada uno a 1280, 390 y 320 px.

## DeepSeek

- 10 llamadas, todas a `deepseek-v4-pro`: 8 del tope y 2 autorizadas por la dueña.
- 39.503 tokens de entrada y 37.296 de salida, USD 0,0489. OWNER_EXCEPTION_USED=2.
- Detalle en ATTEMPT_LOG.md.
- CLAUDE_SEMANTIC_CODE_WRITTEN=0.

## Deudas

| Deuda | Estado |
|---|---|
| LIC-PROFILE-BACKEND-ENTERPRISE-01 | CLOSED para GOBIERNO y MIXTO |
| LIC-MINVER-REVERIFY-01 | CLOSED |
| LIC-PROFILE-ENTERPRISE-MODULE-01 | Nueva, baja (OD-LICUX-01). En EMPRESA no se exige el derecho por módulo |
| OBS-LICUX-UI-EMPRESAS-01 | Nueva, baja. El menú «Empresas» se clasifica ENTERPRISE en la interfaz y su API es SHARED |

## Seguridad

SECRET_EXPOSURE=0 · PRIVATE_KEY_READ=0 · PACKAGE_PERSISTED_IN_BROWSER=0 · SNAT_TOUCHED=0 · PRODUCTION_TOUCHED=0. Las credenciales no se registran.
