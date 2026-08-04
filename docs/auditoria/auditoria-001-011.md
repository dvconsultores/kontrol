# AUDITORÍA — SPECS 001 A 011 (KONTROL)

| Campo | Valor |
|---|---|
| Fecha de auditoría | 2026-08-04 |
| Rama | `feature/001-fundacion` |
| HEAD auditado | `7091451` (feat 011) · origin `d13632a` (feat 010) |
| Alcance | Iniciativas 001-fundacion … 011-homologacion-liberacion |
| Metodología | Especificación documental + ejecución de gates + convergencias + evidencia |
| Estado global | **Certificado al nivel local/automatizado; NO 100% certificado** (faltan Docker/CI/entrega y evidencias por spec) |
| Ruta | `docs/auditoria/auditoria-001-011.md` |

---

## 1. Resumen ejecutivo

La auditoría profunda de los specs 001-011 confirma que **el desarrollo está completo y los gates automatizados están en verde**, pero **la certificación formal al 100% NO se ha alcanzado** porque depende de criterios de **entorno Docker, CI en GitHub, E2E Playwright, migración contra PostgreSQL real y entrega (PR)** que no pueden ejecutarse en el sandbox actual, y porque **los specs 006-011 carecen de evidencia de pruebas** en su carpeta `evidence/`.

**Semáforo por bloque:**

| Bloque | Estado |
|---|---|
| Fase documental (spec/clarificaciones/plan/modelo/checklist/tareas/soporte/análisis) | 🟢 Completa en 11/11 |
| Backend automatizado (pytest 190, ruff, mypy 96) | 🟢 Verde |
| Frontend automatizado (tsc, eslint, vitest 16, build) | 🟢 Verde |
| Migración Alembic (head `0011_homologacion`, cadena 0001→0011) | 🟡 Validada offline (PostgreSQL); **no ejecutada contra PostgreSQL real** |
| E2E Playwright (smoke) | 🔴 No ejecutado |
| Docker (build, health, persistencia, backup) | 🔴 No ejecutado (checklist creado) |
| CI GitHub (ruff/mypy/pytest/migraciones/seguridad) | 🔴 No ejecutado (workflow existe) |
| PR `feature/001-fundacion → develop` | 🔴 No abierto |
| Evidencia por spec (`evidence/test-results.md`) | 🔴 Faltan en 006-011; falta test-results en 002 |
| Push a origin | 🟡 2 commits locales sin publicar |
| Decisiones de negocio (CL pendientes) | 🟡 Pendientes (no bloquean build, sí 100% producto) |

---

## 2. Metodología

1. Verificación de la fase documental: presencia de todos los artefactos SPEC KIT por spec.
2. Ejecución de los gates locales (backend y frontend) con los comandos del proyecto.
3. Lectura de los `convergence.md` y `analysis-report.md` para extraer brechas y pendientes.
4. Cruce con la **Definition of Done de 001** (`docs/governance/dod-001-fundacion.md`): criterios B5/C5/D1-D5/E3/F2/F3.
5. Comprobación de infraestructura (compose, Dockerfiles, CI, E2E, evidencias).

**Gates ejecutados en esta auditoría (2026-08-04):**

| Gate | Comando | Resultado |
|---|---|---|
| Backend pytest | `cd resources/backend && .venv/bin/python -m pytest` | ✔ **190/190** (13 archivos) |
| Backend ruff | `.venv/bin/ruff check .` | ✔ All checks passed |
| Backend mypy | `.venv/bin/mypy .` | ✔ 96 archivos, 0 issues |
| Alembic head | `alembic heads` (offline PostgreSQL) | ✔ `0011_homologacion` (head único) |
| Alembic cadena | `alembic upgrade head --sql` (dialecto PostgreSQL) | ✔ 0001→0011 genera SQL válido |
| OpenAPI | `app.openapi()['paths']` | ✔ **213 rutas** |
| Frontend tsc | `npx tsc -b` | ✔ 0 errores |
| Frontend eslint | `npx eslint . --max-warnings 0` | ✔ 0 problemas |
| Frontend vitest | `npx vitest run` | ✔ 16/16 |
| Frontend build | `npx vite build` | ✔ OK |

**Rutas por módulo (OpenAPI):** sales 27 · treasury 27 · inventory 25 · fiscal 23 · purchasing 32 · regulatory 15 · maestros 12 · licensing 10 · license 6 · reporting 7 · homologation 8 · auth 8 · organization 5 · health 2 · setup 2 · audit 1 · users 1 · system 1 · root 1 = **213**.

---

## 3. Estado por spec (tabla resumen)

| Spec | Documental | Backend | Frontend | Evidencia `evidence/` | Convergencia | 100% certificado |
|---|---|---|---|---|---|---|
| 001-fundacion | ✔ | ✔ 25 base | ✔ | ✔ (README + test-results) | Parcial (CVG-01..11) | 🔴 faltan B5/C5/D1-D5/E3/F2 |
| 002-maestros | ✔ | ✔ 12 | ✔ | 🟡 solo README (falta test-results) | ✔ | 🔴 depende de 001 |
| 003-inventario | ✔ | ✔ 20 | ✔ | ✔ | ✔ | 🔴 depende de 001 |
| 004-compras | ✔ | ✔ 17 | ✔ | ✔ | ✔ | 🔴 depende de 001 |
| 005-ventas | ✔ | ✔ 11 | ✔ | ✔ | ✔ | 🔴 depende de 001 |
| 006-tesoreria | ✔ | ✔ 24 | ✔ | 🔴 sin evidence | ✔ | 🔴 depende de 001 |
| 007-fiscal | ✔ | ✔ 21 | ✔ | 🔴 sin evidence | ✔ | 🔴 depende de 001 |
| 008-regulatorio | ✔ | ✔ 15 | ✔ | 🔴 sin evidence | ✔ | 🔴 depende de 001 |
| 009-reportes | ✔ | ✔ 13 | ✔ | 🔴 sin evidence | ✔ | 🔴 depende de 001 |
| 010-licenciamiento | ✔ | ✔ 15 | ✔ | 🔴 sin evidence | ✔ | 🔴 depende de 001 |
| 011-homologacion | ✔ | ✔ 17 | ✔ | 🔴 sin evidence | ✔ | 🔴 depende de 001 |

> Pruebas por archivo: `test_services` 6, `test_security` 8, `test_license` 11, `test_maestros` 12, `test_inventory` 20, `test_purchasing` 17, `test_sales` 11, `test_treasury` 24, `test_fiscal` 21, `test_regulatory` 15, `test_reporting` 13, `test_licensing_central` 15, `test_homologation` 17 = **190**.

---

## 4. Hallazgos y brechas (todo lo que falta para el 100%)

### A. Bloqueantes de certificación formal (entorno Docker/CI/entrega) — aplican a TODOS los specs

| ID | Hallazgo | Detalle | Fuente |
|---|---|---|---|
| AUD-001 | Migración Alembic contra **PostgreSQL real** no ejecutada | `0001` usa `create_unique_constraint` (no soportado en SQLite). Solo se validó offline con `--sql`. Criterio **B5** | DoD 001 / checklist Docker #4-5 |
| AUD-002 | **E2E Playwright smoke** no ejecutado | `resources/frontend/e2e/smoke.spec.ts` + `playwright.config.ts` existen; no se instalaron browsers ni se corrió. Criterio **C5** | DoD 001 |
| AUD-003 | **Docker** no validado | `docker compose config/build/up`, health checks, persistencia de `installation_uuid`, backup/restore/diagnóstico no ejecutados. Criterios **D1-D5** | DoD 001 / `docs/evidence/docker-validation-checklist.md` |
| AUD-004 | **CI de GitHub** nunca ejecutado | `.github/workflows/ci.yml` existe (backend, frontend, migrations, security) pero no corre: requiere push + secret `KONTROL_TEST_SECRET_KEY`. Criterio **E3** | DoD 001 / `ci.yml` |
| AUD-005 | **PR `feature/001-fundacion → develop`** no abierto | Documentado en `docs/evidence/pr-001-fundacion.md`; requiere GitHub autenticado. Criterio **F2** | DoD 001 / CVG-11 |
| AUD-006 | Convergencia 001 no cerrada | CVG-01..11: CVG-01/02 hechos; CVG-03..11 pendientes. Criterio **F3** | `specs/001-fundacion/convergence.md` |

### B. Evidencia de pruebas por spec (regla: "una Spec no se declara terminada sin evidencia")

| ID | Hallazgo | Specs afectados | Acción |
|---|---|---|---|
| AUD-007 | Carpeta `evidence/` **inexistente** | 006, 007, 008, 009, 010, 011 | Crear `evidence/README.md` + `evidence/test-results.md` con salida real de `pytest`/gates |
| AUD-008 | `evidence/` **sin `test-results.md`** | 002 | Generar `evidence/test-results.md` |

### C. Repositorio / entrega

| ID | Hallazgo | Detalle |
|---|---|---|
| AUD-009 | **2 commits sin push** | `3796132` (spec 011) y `7091451` (feat 011). `origin` en `d13632a` |
| AUD-010 | Secretos de CI | CI usa `secrets.KONTROL_TEST_SECRET_KEY`; debe existir en GitHub (Settings → Secrets) antes de E3 |
| AUD-011 | `pip-audit` blando en CI | Job security: `pip-audit 2>/dev/null || echo "no disponible"` puede pasar en silencio; sustituir por verificación real |

### D. Decisiones de negocio pendientes (CL) — no bloquean el build, sí el 100% de producto

| Spec | Pendiente | Referencia |
|---|---|---|
| 002 | Catálogo semilla global; atributos obligatorios por rubro | CVG-002-01/02 (CL-002-11/12) |
| 003 | Política de costeo por defecto; vencidos; ubicaciones/picking; job `expire_reservations` | CVG-003-01/02/03/04 |
| 004 | Umbrales de aprobación por monto; tolerancias de recepción/sobrefacturación | CVG-004-01/02 |
| 005 | Política de crédito y límites; días de vencimiento por condición | CVG-005-01/02 |
| 006 | Reglas de match configurables por banco; política de cierres de caja; integración de ingresos 005 al estado de cuenta; flujo de anticipos en UI | CVG-006-01/02/03/04/05 |
| 007 | Formatos de libros/PDF; alícuotas exactas del ejercicio; retenciones unificadas; contingencia de facturación en UI | CVG-007-01/02/05/06 |
| 008 | Matrices oficiales por organismo; contingencias con regla oficial en UI; guía fiscal SENIAT con 007 | CVG-008-01/03/04 |
| 009 | Plantillas PDF y marca; política de retención de exportaciones; jobs con cola externa; listado de jobs en UI | CVG-009-01/02/03/05 |
| 010 | Servidor central real (externo); días de gracia por plan; scheduler; contrato v2 (revocación) | CVG-010-01/02/03/04 |
| 011 | Integración CI/CD de gates; plantilla oficial del acto formal; firma/estampa de eventos; vínculo versión liberada en "Acerca de" | CVG-011-01/02/03/04 |

### E. Diferidos cross-cutting (fuera del alcance actual, registrados)

| ID | Diferido | Referencia |
|---|---|---|
| AUD-012 | Contrato SMTP/notificaciones (envío real de correo) | CVG-06 (001) |
| AUD-013 | MFA completo (campo `mfa_enabled` preparado) | CVG-09 (001) |
| AUD-014 | Integración con organismos (SICA/SIGESAI/SENIAT) | CVG-07 (001), CVG-007-03, CVG-008-02 |
| AUD-015 | Contabilidad formal (mayor, partidas dobles, cierre) | CVG-009-04 |
| AUD-016 | Jobs asíncronos con cola externa (celery/worker) | CVG-009-03 |

### F. Observaciones / riesgos de la auditoría (a verificar antes de producción)

| ID | Observación | Acción sugerida |
|---|---|---|
| AUD-017 | **Python**: local 3.11 (venv) vs CI/Docker 3.13 (`target-version py313`) | Ejecutar gates con 3.13 en CI (ya configurado); verificar que no hay incompatibilidades |
| AUD-018 | `ruff format --check` en CI no verificado localmente | Ejecutar `ruff format --check app tests` antes del push |
| AUD-019 | Playwright requiere instalar browsers (`npx playwright install`) | Incluir en el checklist E2E |
| AUD-020 | `alembic.ini` referenciado en Dockerfile | Confirmar que existe y apunta al script `alembic/` (✔ existe) |
| AUD-021 | Secretos: el sandbox no puede hacer push (EPERM en socket git) | El usuario publica manualmente; documentar en la entrega |
| AUD-022 | `docs/evidence/hashes-documental.txt` presente | Verificar que los hashes están al día tras los últimos commits |

---

## 5. Plan de ejecución paso a paso para el 100%

> Orden recomendado. Cada paso termina con criterio verificable. Ejecutar en un entorno con **Docker, acceso a GitHub y la rama `develop`**.

### Fase 1 — Cierre de evidencia y repositorio (sin Docker)

1. **Pushear los commits pendientes**
   ```bash
   git push origin feature/001-fundacion   # sube 3796132 (spec 011) y 7091451 (feat 011)
   git --no-pager log --oneline origin/feature/001-fundacion..HEAD | wc -l   # esperado: 0
   ```

2. **Generar evidencia de pruebas para 006-011 (y test-results de 002)**
   ```bash
   cd resources/backend && .venv/bin/python -m pytest -q > ../docs/evidence/pytest-001-011.txt 2>&1
   # Crear specs/0XX-*/evidence/README.md + evidence/test-results.md con:
   #   fecha, comando, resultado (pytest N/N, ruff, mypy, alembic head, OpenAPI N rutas,
   #   tsc/eslint/vitest/build), y el archivo de salida referenciado
   ```
   Criterio: **AUD-007/AUD-008 resueltos**; cada spec 002-011 tiene `evidence/test-results.md`.

3. **Verificar formato ruff** (requisito del CI)
   ```bash
   cd resources/backend && .venv/bin/ruff format --check app tests
   ```
   Si falla: `ruff format app tests` y revisar el diff (evitar `--fix` masivo en tests).

4. **Commit y push** de la evidencia:
   ```bash
   git add -A && git commit -m "docs(audit): evidencia de pruebas specs 002-011 y formato ruff" && git push
   ```

### Fase 2 — Validación Docker (AUD-001, AUD-003)

5. **Ejecutar el checklist Docker** (`docs/evidence/docker-validation-checklist.md`) con Docker real:
   ```bash
   docker compose -f compose.yaml config --quiet && echo "config OK"
   docker compose -f compose.yaml build
   cp .env.example .env   # completar valores
   docker compose -f compose.yaml up -d
   curl -fsS http://localhost:8080/healthz.json
   curl -fsS http://localhost:8000/api/v1/health/live
   curl -fsS http://localhost:8000/api/v1/health/ready
   docker compose -f compose.yaml exec backend alembic upgrade head   # PostgreSQL real (B5)
   docker compose -f compose.yaml exec backend alembic downgrade base
   docker compose -f compose.yaml exec backend alembic upgrade head
   docker compose -f compose.yaml stop backend && docker compose -f compose.yaml start backend
   ./scripts/diagnose.sh
   ```
   Completar la tabla "Registro de resultados" del checklist.
   Criterio: criterios 1-8 del checklist en ✔ (incluye persistencia de `installation_uuid` y backup/restore — AUD-003).

6. **Commit del checklist completado** con resultados y fecha.

### Fase 3 — E2E Playwright (AUD-002)

7. **Instalar browsers y ejecutar el smoke E2E**
   ```bash
   cd resources/frontend
   npx playwright install --with-deps
   npm run test:e2e          # requiere backend+frontend vivos (compose.dev o CI)
   ```
   Criterio: smoke E2E pasa (login visible y accesible). Guardar captura/evidencia.

### Fase 4 — CI de GitHub en verde (AUD-004, AUD-010, AUD-011)

8. **Preparar secrets de GitHub** (Settings → Secrets → Actions):
   - `KONTROL_TEST_SECRET_KEY` (≥32 caracteres, distinta de la de producción).

9. **Crear la rama `develop`** si no existe y abrir el **PR `feature/001-fundacion → develop`** (AUD-005).

10. **Ejecutar y corregir CI** hasta que todos los jobs pasen:
    - backend (ruff lint+format, mypy, pytest 190)
    - frontend (eslint, typecheck, vitest 16, build)
    - migrations (upgrade head + downgrade base contra PostgreSQL 18 — valida **AUD-001/B5** en CI)
    - security (gitleaks, npm audit, pip-audit real — revisar **AUD-011**)
    Criterio: **E3 en verde**; los checks aparecen en el PR.

11. **Revisar el PR** (al menos 1 reviewer) y **mergear a `develop`**.

### Fase 5 — Cierre de convergencia y DoD (AUD-006)

12. **Actualizar `specs/001-fundacion/convergence.md`**: marcar CVG-05, CVG-08, CVG-10, CVG-11 y el criterio "Convergencia final (100% certificado)" a ✔, con fechas y evidencia.

13. **Actualizar `docs/governance/dod-001-fundacion.md`**: marcar B5, C5, D1-D5, E3, F2, F3 en ✔ y actualizar el "Resultado" a **CERTIFICADO 100%**.

14. **Propagar la certificación** a los `convergence.md` de 002-011 (línea "Certificación … Pendiente — depende de 001 certificada" → ✔) ahora que 001 está certificada.

15. **Commit final y push**:
    ```bash
    git add -A && git commit -m "cert(001-011): cierre de convergencia y DoD 100% certificado" && git push
    ```

### Fase 6 — Decisiones de negocio (para 100% de producto, no bloquean la certificación técnica)

16. Resolver, en orden de impacto, los CL pendientes de la tabla **D** (policy de costeo, umbrales, crédito, conciliación, formatos, matrices, plantillas PDF, licenciamiento central real, acto formal). Cada decisión se documenta como **nuevo spec/CR** y se implementa con su propio ciclo SPEC KIT.

17. Implementar los diferidos cross-cutting (**E**) cuando apliquen: MFA completo, SMTP, contabilidad formal, jobs async, integración con organismos.

---

## 6. Conclusión

- **Desarrollo**: 001-011 implementados de extremo a extremo (backend + frontend), con documentación completa y gates automatizados en verde (190 pytest, 16 vitest, ruff, mypy, tsc, eslint, build, 213 rutas OpenAPI, head Alembic `0011_homologacion`).
- **Certificación 100%**: **NO alcanzada** por 6 bloqueantes de entorno/entrega (PostgreSQL real, E2E, Docker, CI GitHub, PR, convergencia) + **evidencia de pruebas faltante** en 006-011 (y test-results en 002) + **2 commits sin push**.
- **El plan de la sección 5** lleva el proyecto al 100% en ~6 fases, todas con comandos y criterios verificables.

> Esta auditoría quedó registrada el 2026-08-04 y debe re-ejecutarse tras cada fase para confirmar el cierre.
