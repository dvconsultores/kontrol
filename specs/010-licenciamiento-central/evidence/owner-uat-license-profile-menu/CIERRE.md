# Cierre · OWNER-UAT-LICENSE-PROFILE-MENU-01

Delta: `spec004-owner-uat-license-profile-menu-delta.md`. **Entrada:** e3f8412. **Estado:** corregido y verificado. OWNER_ACCEPTED=NO hasta que la dueña repita la prueba.

## Verificación

| Comprobación | Resultado |
|---|---|
| PG completa (run r20261116t173127p28931nbf9653) | 5668 pasan / 5 fallan / 18 omitidas. Los 5 son exactamente la línea base: imb_07, n10, guard_d01 y 2 de spec019 receipt. OAS-14 ya no falla |
| SQLite dirigida: licencia, versión mínima, OpenAPI, reverificación, gov0 | 108 pasan / 13 omitidas |
| Vitest | 2308/2308 |
| tsc, eslint y build | OK |
| ruff | limpio |
| mypy (`app`) | 157, igual que la base |
| E2E `licencia-perfil` (run r20261116t172813p23439nee16a6) | 5/5, 0 reintentos, LICUX-E2E-05 incluida |
| Mutación: homologación y aprobaciones de nuevo SHARED | LICUX-E2E-05 falla («sin recargar: ENTERPRISE_LINKS_VISIBLE») → detectada |

## Hallazgo fuera del código: el entorno que usa la dueña

- La dueña prueba en **kontrol-gob.globaldv.net**. Ese servidor corre a mano una imagen anterior (≈2f2ce4c, identificada por la huella del bundle).
- `deploy-uat` se salta: no hay runner autohospedado registrado ni `UAT_DEPLOY_ENABLED`.
- El build de e3f8412 falló por un corte de red al bajar la clave PGDG.
- **Decisión de la dueña (2026-11-16):**
  - entregar ya una pila local;
  - instalar el runner en el servidor según el runbook §4;
  - después, Claude activa `UAT_DEPLOY_ENABLED` y verifica el despliegue.
- El servidor necesita además una licencia solo-Gobierno firmada por la Autoridad Central real para la instalación KTL-VE-35BFBE13-3E0D.

## DeepSeek

3 llamadas `deepseek-v4-pro`, 10.753 / 7.142 tokens, USD 0,0108. OWNER_EXCEPTION_USED=0. CLAUDE_SEMANTIC_CODE_WRITTEN=0.

## Seguridad

SECRET_EXPOSURE=0 · PRIVATE_KEY_READ=0 · PRODUCTION_TOUCHED=0 · el servidor kontrol-gob solo se consultó con lecturas públicas (health, estado de licencia y bundle).
