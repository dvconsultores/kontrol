# TRE-04 · Estado de pausa (2026-11-18)

**Sin publicar.** WIP en `~/.cache/kontrol-qa/ctl05` (HEAD `250227c`). Instantánea en `~/.cache/kontrol-qa/tre04/wip/`: `BASE`, `tracked.patch` y `untracked.tgz` con 22 ficheros.

## Hecho

- **Spec Kit:** `spec.md`, `plan.md` (gate PASS, PDD-TRE04-01..10), `tasks.md`, `evidence/N37_VALIDATION.md` y `ATTEMPT_LOG.md`.
- **Backend:**
  - 11 tablas y migración `0126_gov_tre04_pago`, que hay que reencadenar (ver Pendiente);
  - proyección única del pagado/en trámite, políticas y medios, el servicio del pago y sus transiciones;
  - API (20 rutas), permisos `gobierno_pagos` (6), MFA, 15 eventos de auditoría, CTL-01 TRE-04 y fronteras TRE-03.
- **Verificación backend:**
  - `tests/test_gov_tre04_pago.py` 32/32 en PG;
  - ruff 0 y mypy 157 (línea base);
  - mutaciones M1–M10 10/10 muertas;
  - migración ida, vuelta e ida en PG con modelos = migración.
- **Frontend:**
  - `api.ts` y 5 pantallas (Pagos, Nuevo/editar, Detalle, Políticas de pago, Ficha), router, menú y pantallas;
  - tsc 0, eslint 0, guardas 500/500;
  - fixtures regenerados con `qa/fixtures_de_frontend.py`.

## Pendiente, en orden

1. **Integrar P2.** `origin/develop` = `b65d598` (ORG-04 assignment policy), con su migración `0126_gov_assignment_policy`. Pasos:
   - fusión ordinaria;
   - `git mv` de la migración propia a `0127_gov_tre04_pago` (down `0126_gov_assignment_policy`), por encargo a DeepSeek;
   - sumar las fijaciones (auditoría, MFA, permisos, cabeza en 3 pruebas);
   - regenerar los fixtures del frontend;
   - revisar la resolución ORG-04 para el checker (§26).
2. **Vitest:** 5/18 con h1 fijado (`level: 1`). Los fallos restantes son de las pruebas: textos partidos, rótulos, montos formateados por `formatearMonto`, `getByLabelText` frente a rótulos con «(obligatorio)», y 3 llamadas mal tipadas. Diagnóstico en `~/.cache/kontrol-qa/tre04/`.
3. **E2E** (§49–§55):
   - helper con un `permisosExtra` opcional y `despId` en `prepararMundoOrdenes`;
   - cuenta TRE-01 por API (bancos → cuentas → acto → autorizados → activar);
   - 7 escenarios, Axe a 1280/390/320 y humo UAT (2 pantallas);
   - con el puerto 8000 ocupado por otro proyecto, usar `KONTROL_E2E_PUERTO_*=18000/15173/18010`.
4. **Cierre:** PG dirigida, PG completa, OpenAPI frente a origin, auditoría de hardcode, tarjeta UAT, matrices, DAG, commit, push y build-dev.

## DeepSeek

- **Consumo:** 17 de 28 llamadas (tope subido por la dueña dos veces: 12 → 20 → 28; `OWNER_EXCEPTION_USED=1`).
- **Excluidos del cómputo:** los cortes de transporte sin contenido no cuentan, por decisión de la dueña.
- **Coste:** acumulado de unos 0,21 USD (ver `ATTEMPT_LOG.md`).
