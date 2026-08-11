# CERTIFICACIÓN INTERNA DE PRUEBA FUNCIONAL — KONTROL

RUN ID: `KONTROL-QA-20260810-234937`
Fecha: 2026-08-11
URL: https://kontrol.globaldv.net
Ambiente: Producción pública
Versión visible: no expuesta (bundle `index-k-41vOMJ.js`)

> Esta es una **CERTIFICACIÓN TÉCNICA INTERNA DE QA**. NO es homologación SENIAT,
> ni certificación legal, fiscal externa o de terceros.

## Equipo participante (simulado)
Dirección de producto, administración, contabilidad/finanzas, fiscal Venezuela,
tecnología (arquitectura, backend, frontend, BD, infra, seguridad) y QA
(funcional, backend, frontend, API, BD, E2E, integración, seguridad, responsive,
accesibilidad, cross-browser, Playwright, Pytest, Vitest).

## Resultado de la ejecución
| Métrica | Valor |
|---|---|
| Pruebas ejecutadas | 4 (preflight disponibilidad, login, API, conciliación general) + 5 viewports responsive + login Chromium |
| PASS | 2 (responsive login; login render Chromium) |
| FAIL | 4 (disponibilidad, login, API, conciliación general) |
| BLOCKED | 50+ fases funcionales |
| NOT_IMPLEMENTED | 0 (no evaluable) |
| BLOCKER | 1 (KQA-001) |
| CRITICAL | 0 |
| HIGH | 1 (KQA-002) |
| MEDIUM | 0 |
| LOW | 0 |
| Navegadores | Chromium real (login OK); Firefox/Edge/Opera/Safari/WebKit/móviles: NOT_EXECUTED |
| Responsive | Login sin scroll horizontal 320–1920 (PASS); resto BLOCKED |
| Accesibilidad | Login con labels accesibles (PARCIAL); axe completo NOT_EXECUTED |
| Fiscal | Nada emitido (BLOCKED_FISCAL_PRODUCTION_SAFETY); no se consumieron correlativos |

## Conclusión
**NO CERTIFICABLE — REQUIERE REMEDIACIÓN.**

Motivo principal (BLOCKER): la API del backend está caída (**502 Bad Gateway** en
todos los `/api/v1/*`), por lo que el login y TODOS los procesos funcionales no
pueden ejecutarse. Hallazgo adicional HIGH: `/health/live` y `/health/ready`
devuelven el SPA en lugar del estado del backend (KQA-002), lo que enmascara la caída.

Condición para re-certificar: restaurar el backend (KQA-001), corregir el health
check de nginx (KQA-002) y re-ejecutar la prueba funcional integral completa.
