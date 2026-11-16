# Cierre · OWNER-UAT-LICENSE-PROFILE-MENU-01

Delta: `spec004-owner-uat-license-profile-menu-delta.md`. **Entrada:** e3f8412. **Estado:** corregido, verificado y **aceptado por la dueña** (2026-11-16): «ya entré, configuré y todo bien», en kontrol-gob.globaldv.net con c3b0a9c y licencia real solo-Gobierno.

```text
OWNER_UAT_LICENSE_PROFILE=PASS
OWNER_ACCEPTED=YES
```

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

- La dueña prueba en **kontrol-gob.globaldv.net**, su ambiente de desarrollo. Watchtower lo actualiza cada 60 s desde `kontrol-{backend,frontend,clamd}:latest`.
- El build de e3f8412 falló por un corte de red al bajar la clave PGDG. Como `:latest` no cambió, el servidor siguió en ≈2f2ce4c (huella del bundle) hasta que el build de c3b0a9c terminó bien.
- El flujo UAT formal (runner autohospedado y `deploy-uat`) sigue sin activar, por decisión de la dueña.
- **Decisión de la dueña (2026-11-16):**
  - entregar ya una pila local;
  - el runner se instala solo después de alinear la pila con el runbook. Watchtower y el runner no conviven, y hay que migrar de PG 17 a 18;
  - `UAT_DEPLOY_ENABLED` no se activa todavía.
- El servidor necesita además una licencia solo-Gobierno firmada por la Autoridad Central real para la instalación KTL-VE-35BFBE13-3E0D.

## DeepSeek

3 llamadas `deepseek-v4-pro`, 10.753 / 7.142 tokens, USD 0,0108. OWNER_EXCEPTION_USED=0. CLAUDE_SEMANTIC_CODE_WRITTEN=0.

## Seguridad

SECRET_EXPOSURE=0 · PRIVATE_KEY_READ=0 · PRODUCTION_TOUCHED=0 · el servidor kontrol-gob solo se consultó con lecturas públicas (health, estado de licencia y bundle).

## Aceptación (2026-11-16)

- La dueña repitió la prueba en kontrol-gob.globaldv.net, que ya servía c3b0a9c. Es el ambiente de desarrollo de la dueña: Watchtower lo actualiza solo desde las imágenes `:latest`.
- Comprobación externa previa:
  - el bundle contiene la clasificación corregida;
  - la API Enterprise responde 403 `PRODUCT_PROFILE_DENIED` con perfil KONTROL Gobierno.
- Abiertas:
  - OBS-LICUX-ANON-403-01 (baja): un anónimo recibe la denegación de perfil antes del 401;
  - el flujo UAT formal (runner, `uat-<sha>`, candidato, smoke), pendiente de la dueña.
