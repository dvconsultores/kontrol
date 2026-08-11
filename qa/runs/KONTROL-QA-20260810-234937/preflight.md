# PRE-FLIGHT — PRUEBA FUNCIONAL INTEGRAL E2E — KONTROL

RUN ID: `KONTROL-QA-20260810-234937`
Fecha: 2026-08-11 (UTC 2026-08-10 23:49)
URL: https://kontrol.globaldv.net
Ambiente: Producción (instancia pública kontrol.globaldv.net)
Navegador principal: Chromium (navegador integrado / motor real)
Herramienta: VS Code + Playwright (smoke) + navegador integrado

## 1. Disponibilidad
- El sitio responde (el SPA se sirve por nginx) ✅
- La página `/login` carga y renderiza correctamente ✅

## 2. Estado de la instancia (LO QUE IMPIDE LA PRUEBA)
- **BLOCKER KQA-001**: TODO `/api/v1/*` devuelve **502 Bad Gateway** (openresty).
  - Verificado en: `/api/v1/setup/status`, `/api/v1/license/status`, `/api/v1/auth/refresh`,
    `/api/v1/auth/login`, `/api/v1/organization/companies`.
  - Reproducido 3 veces en ~18 s, siempre 502 (no transitorio).
  - **Consecuencia**: el login es imposible → ninguna prueba funcional autenticada puede ejecutarse.
- **KQA-002**: `/health/live` y `/health/ready` devuelven **200 con el HTML del SPA** (no el JSON de salud del backend).
  Indica que nginx captura `/health/*` con el fallback SPA (try_files → index.html) y no enruta al backend.

## 3. Registro pre-flight
| Ítem | Resultado |
|---|---|
| Fecha/hora | 2026-08-11 00:24 UTC |
| Versión visible | No expuesta en UI (bundle `index-k-41vOMJ.js`) |
| Navegador | Chromium (real, integrado) |
| Ambiente | Producción pública |
| Licencia | No consultable (API 502) — `LICENSE_STATUS_UNAVAILABLE` |
| Backend | **CAÍDO** (502 en toda la API) |
| Frontend | SPA se sirve correctamente |
| Login | **FALLA** (KQA-001) |
| Permisos disponibles | No verificables (requiere login) |
| Empresas existentes | No consultables (API 502) |
| GLOBAL DV | No verificable |
| Datos reales | No accesibles (API 502) |
| Modo QA/sandbox | No detectable |
| Perfil fiscal QA | No verificable |
| Documentos fiscales | No se emitirán (la prueba está bloqueada antes) |

## 4. Conclusión pre-flight
La instancia NO es ejecutable funcionalmente en este momento por caída del backend (502).
La prueba se documenta con el hallazgo BLOCKER y las validaciones independientes ejecutadas.
No se modificó ningún dato.
