# Quickstart: validar TRE-02

Requisitos: PostgreSQL de QA, licencia con `gobierno`, ente activo, una cuenta vigente de TRE-01.

1. Backend: `tests/test_gov_tre02_*.py` sobre PostgreSQL con el mundo multiempresa.
2. Frontend: `vitest run src/modules/gobierno/tesoreria/programacion`.
3. E2E: `qa/e2e-run.py --con-analizador -- e2e/gobierno-programacion.spec.ts e2e/gobierno-tesoreria-revocacion.spec.ts --project=chromium --project=firefox --project=webkit`.
4. Resultado esperado por la interfaz: disponibilidad inicial 1.000,00; ingresos 500,00 y desembolsos 300,00 en el primer mes; final 1.200,00, que abre el mes siguiente.
5. Integridad: `qa/e2e-gobierno-regresion.sh` con los controles del grupo CAJA.

La tarjeta completa de la dueña está en `evidence/OWNER_UAT_CARD.md`.
