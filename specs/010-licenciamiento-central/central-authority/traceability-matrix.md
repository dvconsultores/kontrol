# Trazabilidad — Autoridad Central Fase 1

| FR-010 | Prueba o evidencia | Mutación |
|---|---|---|
| 267–270 independencia, base propia, sin compartir | CLA-14 (grafo de importación), CLA-18 (compose e imagen), CLA-PG-03 (sin tablas del cliente) | — |
| 271–274 custodia de la clave; prod cerrado; no se genera | CLA-01, 01b, 02, 17 | M-05 |
| 275–276 registro único | CLA-03, 03b, 04 | M-07 |
| 277–278 libro inmutable | CLA-08 | — |
| 279–287 paquete firmado, `revision` ≥ 1 firmada, 1 → 2 → 3, concurrentes distintas, sin reutilización, reinicio por período | CLA-05, 06, 07, 09; CLA-PG-01, 02; REV-01..07 | M-01, M-02, M-03, M-04, M-10 |
| 288–294 ni `kid` ni fecha ni llegada; derechos libres; `kid` intacto; una clave; sin rotación | CLA-05, 06, 07 | M-06 |
| 295–296 CLI; sin API admin pública | CLA-16, 15 | — |
| 297–299 sync solo con auth; aislamiento; desconocida sin fuga | CLA-15 (sync no expuesto), CLA-04 | — |
| 300–301 health mínimo | CLA-15 | M-09 |
| 302–306 frontera, esquema cliente intacto, migraciones, instalación limpia, constraints | CLA-18, CLA-PG-03; suites del cliente | M-10 |
| 307–309 transacción, concurrencia, artefacto reproducible | CLA-09, CLA-PG-01, CLA-08 | M-01, M-04 |
| 310–311 `issued_at` técnico; `America/Caracas` | CLA-07 (hitos del contrato en `-04:00`) | — |
| 312–313 canonicalización; sin `revision: null` | CLA-12, REV-05, 06 | M-08 |
| 314–316 firmante sintético explícito; sin material en registros | `tests/central/conftest.py`, CLA-17 | — |
| 317–318 contrato con el cliente; compatibilidad | CLA-11, 13 | M-08 |
| 319–321 D0-06, MASTER56, NEXT SPEC | ADR-D0-006, `D0-final-resolution.md`, hoja de ruta | — |
