# PROC-10 · Evidencia de cierre (2026-11-10)

Producto integrado con merge ordinario sobre `e22a394` (PROC-08 + Spec 015 de P2) y conservando `e3004a8` (cierre de la deuda de
matriz de PROC-06). La migración nació como `0095_gov_proc10_garantias`; al integrar, la cabeza pública pasó a ser
`0095_fusion_gov_planning`, y la revisión inédita se reposicionó como `0096_gov_proc10_garantias` encima de ella, sin migración de
fusión. Cabeza única.

| Comprobación | Resultado |
|---|---|
| E2E `e2e/gobierno-garantias.spec.ts` (Chromium, PostgreSQL efímero, Alembic, analizador real) | 1/1 PASS |
| E2E de regresión PROC-08 `e2e/gobierno-decision.spec.ts` | 1/1 PASS |
| Backend PostgreSQL: PROC-10 (6), PROC-08 (decisión y recomendación), guardas (catálogo, cabeza de Alembic, URL de migraciones, Spec 018, MFA, delegación) | 181/181 |
| Alembic en PostgreSQL nuevo: upgrade head, downgrade `0095_fusion_gov_planning` (0 tablas de garantías), upgrade head | PASS |
| Paridad modelos/migración (4 tablas `gov_guarantee_*`): columnas, tipos, nulabilidad, UNIQUE, índices, destinos de FK | 0 diferencias materiales |
| Paridad: nombres | CHECK con el mismo recuento por tabla; nombres truncados por PostgreSQL a 63 caracteres con hash. Nombres de FK por convención, como PROC-08 (cosmético) |
| tsc, ESLint (`eslint . --max-warnings 0`), build | PASS |
| Vitest completo | 1874 PASS; 18 rojas preexistentes reproducidas en `e22a394` limpio (importaciones 9, requisiciones 8, terceros 1), fuera de Gobierno |
| ruff (ficheros de PROC-10 y registros) | limpio |
| mypy `app` | 154 = línea base pública; 0 nuevos |
| OpenAPI frente a `e22a394` | solo añadidos: 7 rutas de garantías, 7 esquemas; 0 cambiados, 0 quitados |
| Fixtures de frontend (`qa/fixtures_de_frontend.py`) | regenerados: rutas y 4 capacidades `gobierno_garantias` (solo añadidos) |
| Catálogo de auditoría | 460 (453 públicas + 7) |

## Lo que recorre la E2E en el navegador

Menú → expediente adjudicado → «Garantías y cauciones»:
1. Resumen textual y adjudicación vigente; garantía de fiel cumplimiento al 20 % «Suficiencia: No evaluable» con
   «BASE_MONETARIA_NO_DISPONIBLE» (no se calcula con cero).
2. Emisor por la interfaz (aseguradora con RIF).
3. Requisito de mantenimiento de oferta con monto fijo en VES y vigencia mínima, con su documento.
4. Garantía del oferente no adjudicado: «Insuficiente» por «Vigencia mínima: No cumple»; estado «Vigente».
5. Renovación: GAR-03 encadenada, GAR-02 «Renovada», GAR-03 «Suficiente»; historial Registro y Renovación.
6. Liberación con acto DOC-02 y confirmación «La liberación no se puede deshacer.»; «Liberada»; precondición «Verificada».
7. Sustitución de la garantía de fiel cumplimiento: GAR-04 nueva, GAR-01 «Sustituida» y conservada; historial «GAR-01 → GAR-04».
8. Ejecución de GAR-04 con acto DOC-02 y confirmación; 1.000,00 de 5.000,00 USD; «Ejecutada»; historial con el monto.
9. Cronología del expediente: liberación, sustitución y ejecución con los títulos del servicio.
10. Axe sin violaciones en 6 puntos (inicial, formulario de requisito, renovación, confirmación de liberación, confirmación de
    ejecución, estado final con historial abierto); 390 y 320 px sin desborde en la sección y en la cronología.

El MFA es de sesión (el usuario inicia sesión con MFA); no hay un paso de MFA por acción.
Negativas materiales, aislamiento, inmutabilidad en PostgreSQL, concurrencia forzada y SoD: `test_gov_proc10_garantias`.

## Defectos hallados al ejecutar y corregidos

- Producto: el formulario de requisito decidía los campos por el tipo de garantía en lugar de la forma de cálculo; por la
  interfaz no se podía registrar ningún requisito porcentual ni de monto fijo. Corregido (`regla.forma`).
- Prueba: ayudante de documentos de la E2E con campos y rutas que no son los de la API; localizadores ambiguos; apertura del
  historial no idempotente (OBS-PROC10-E2E-DETAILS-01, cerrada).

## Gaps declarados

- OBS-PROC08-MONTO-01 y OBS-PROC08-PARCIAL-01 siguen abiertos (la plataforma no registra presupuesto, monto de oferta ni de
  contrato; por eso las exigencias porcentuales son NO_EVALUABLE).
- OBS-VITEST-P2-01: 18 pruebas Vitest rojas ya en `e22a394`, ajenas a PROC-10.

## UAT

Pendiente del push.
