# Quickstart: validar CTL-10

Requisitos: PostgreSQL de QA con `ktest`, licencia con `gobierno`, ente activo, una estructura VIGENTE de un ejercicio pasado (ORG-02), un hallazgo ABIERTO (CTL-06) y un programa VIGENTE (TRE-02).

1. Backend: `tests/test_gov_ctl10_*.py` sobre PostgreSQL con el mundo multiempresa, y SQLite.
2. Frontend: `vitest run src/modules/gobierno/cierres`.
3. E2E: `qa/e2e-run.py --con-analizador -- e2e/gobierno-cierres.spec.ts --project=chromium --project=firefox --project=webkit`.
4. Resultado esperado: con la política vigente de HALLAZGOS_ABIERTOS, cerrar la estructura muestra el panel de bloqueo con el hallazgo y su enlace; tras cerrar el hallazgo, el cierre procede.
5. Integridad: `qa/gobierno_integridad.py` con los controles de CTL-10.

La tarjeta de la dueña estará en `evidence/OWNER_UAT_CARD.md` al certificar.
