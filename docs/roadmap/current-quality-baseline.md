# LÍNEA BASE DE CALIDAD ACTUAL

> Cifras medidas en esta auditoría (2026-08-29), no tomadas de reportes previos.

## Resumen por área

| Área | Nota | Fundamento |
|---|---|---|
| Frontend | **B+** | 78 rutas sin huérfanas, design system uniforme, axe 19/19, responsive 198/198, bundle 375 KB con 87 chunks. Sin pruebas de página; sin protección de cambios sin guardar |
| Backend | **B** | 275 endpoints, máquinas de estado explícitas, idempotencia y concurrencia probadas. Auditoría incompleta; 2 tablas muertas |
| Base de datos | **B−** | 144 tablas, cadena lineal de 14 migraciones, head único, 0 dinero en Float. **Nunca ejecutada contra PostgreSQL**; FKs faltantes en 4 relaciones críticas |
| Integraciones | **D** | Una sola con contrato y sin red real; el resto inexistente |
| QA | **B** | 223 pytest + 210 vitest + E2E 20/20 + crawler 71/71 + axe + responsive + cross-browser. Cobertura frontend concentrada en 7 archivos de componente |
| UX | **B+** | Estándar de pantalla cumplido salvo unsaved-changes |
| Seguridad | **B−** | Aislamiento multi-tenant probado, RBAC, lockout, CSP/HSTS, CVE 0. Sin SBOM, sin rate limiting global, sin política de uploads |
| Infraestructura | **C** | Compose completo y nunca validado E2E; backup/restore no ejecutado; `latest` por defecto |

## Métricas verificadas

| Métrica | Valor | Método |
|---|---:|---|
| pytest | **223 passed / 0 failed** | `pytest tests/ -q` ejecutado |
| vitest | **210 passed / 7 archivos** | `npm run test` ejecutado |
| Archivos de prueba frontend | 7 | `find -name '*.test.ts*'` |
| Endpoints backend | 275 | conteo de decoradores `@router.*` |
| Rutas frontend | 78 | `path:` en `router.tsx` |
| Páginas | 77 | `*Page.tsx` |
| Ítems de menú | 72 | `Sidebar.tsx` |
| Tablas | 144 | `__tablename__` |
| Migraciones | 14, cadena lineal, head único `0014` | `down_revision` |
| LOC backend / frontend | 14.820 / 15.356 | `wc -l` |
| Módulos con auditoría instrumentada | **7 de 9** | conteo de `_audit(` |
| Columnas de dinero en Float | **0** | ADR-012 + migración 0014 |
| Tablas sin ningún consumidor | **2** (`outbox_events`, `feature_flags`) | grep sin coincidencias fuera del modelo |

## Cobertura de pruebas por tipo

| Tipo | Existe | Alcance real |
|---|---|---|
| Unit backend | ✔ | 223 casos sobre 15 módulos |
| Unit frontend | ✔ | 12 casos sobre 5 componentes del design system |
| **Página / pantalla** | **✖** | **Ninguna prueba de las 77 páginas** |
| Contract (menú↔ruta↔API) | ✔ | 5 puertas G1-G4 |
| Integration API | ✔ | 20/20 E2E in-process |
| E2E navegador | ✔ | crawler 71/71 chromium, 65/65 firefox, 2/2 webkit |
| Accesibilidad | ✔ | axe 19/19 (18 páginas + login) |
| Responsive | ✔ | 198/198 (33 rutas × 6 viewports) |
| Idempotencia / concurrencia | ✔ | 6/6 |
| Seguridad | ✔ | 8 casos (401, RBAC, tenant, IDOR, SQLi/XSS) |
| Rendimiento | ◐ | smoke 12/12 sobre base vacía — no concluyente |
| Migraciones | ◐ | 3 casos offline en dialecto PG; **sin PG real** |
| Carga / estrés | ✖ | — |
| Dispositivos reales | ✖ | — |

## Clasificación de validación de navegadores

| Nivel | Aplicación |
|---|---|
| `REAL_VALIDATION_EXISTS` | chromium, firefox, webkit (motores locales de Playwright) |
| `SIMULATED_ONLY` | viewports responsive (emulación, no dispositivo) |
| `NO_COVERAGE` | Edge, Opera, Samsung Internet, Safari en dispositivo iOS |

## Índice global de integración (referencia)

**GLOBAL_INTEGRATION_INDEX = 62 / 100**

Se publica solo como referencia y **no debe usarse para ocultar brechas**. Debe leerse siempre junto a:

- Procesos rotos o incompletos: **12 de 21**
- Bloqueantes abiertos: **7**
- Specs no iniciadas: **5**
- Specs parciales o esqueleto: **26**
- Specs en M5 (production-ready): **0**
