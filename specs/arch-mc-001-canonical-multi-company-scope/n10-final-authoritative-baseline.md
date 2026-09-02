# ARCH-MC-001 — BASELINE FINAL AUTORITATIVA

> Medida el 2026-09-02 contra el código, la base y el contrato vigentes.
> Ningún número de este documento procede de un informe anterior.
> **Esta es la única baseline vigente de ARCH-MC-001.** Toda cifra anterior que
> discrepe queda `SUPERSEDED_BY_ARCH_MC_001_FINAL_BASELINE`.

## Cómo se midió

| Magnitud | Fuente |
|---|---|
| Modelos, alcances, rutas derivadas | `Base.registry.mappers` tras `init_models()` |
| Tablas, FK, uniques, nulabilidad | Catálogo de PostgreSQL 18.6 sobre instalación limpia migrada a `head` |
| Rutas y operaciones | `app.openapi()` en ejecución |
| Cabecera de empresa | Parámetro `X-Kontrol-Company` declarado en la operación |

## Cifras

| Magnitud | Valor |
|---|---:|
| PostgreSQL | 18.6 · UTC |
| Revisión de Alembic en cabeza | `0039_n10_scope_reconciliation` |
| Modelos ORM | 166 |
| Tablas funcionales | 166 |
| Tablas en la base (con `alembic_version`) | 167 |
| Alcance COMPANY | 136 |
| Alcance TENANT | 8 |
| Alcance INSTALLATION | 18 |
| Alcance GLOBAL | 4 |
| **Sin alcance (`UNKNOWN`)** | **0** |
| COMPANY con columna propia | 100 |
| COMPANY por ruta derivada | 36 |
| TENANT con columna propia | 4 |
| TENANT por ruta derivada | 4 |
| INSTALLATION por ruta derivada | 1 |
| Rutas derivadas declaradas | 41 |
| Columnas `company_id` | 107 |
| Columnas `company_id` obligatorias | 96 |
| Columnas `tenant_id` | 5 |
| Claves foráneas (restricciones) | 331 |
| Restricciones únicas | 80 |
| Índices únicos | 214 |
| Rutas HTTP | 294 |
| Operaciones HTTP | 404 |
| Operaciones que declaran la empresa | 342 |
| Operaciones fuera del ámbito de empresa | 62 |
| Operaciones de alcance indeterminado | **0** |
| `ResourceKind` registrados | 23 |
| Migraciones | 39 |
| `legacy_scope_id` / `scope_backfill_class` en ejecución | 0 |

Las cifras de FK, `company_id`, `tenant_id` y rutas derivadas cambian respecto de
N9: la reconciliación de N10 retiró cinco columnas `tenant_id` abandonadas,
añadió cinco rutas de derivación que faltaban por declarar y dio contexto de
empresa a diez operaciones que no lo pedían. El apartado de reconciliación
histórica lo detalla.

## Regresión

| | |
|---|---:|
| Backend: fallos | **0** |
| Backend: saltos | **8** (todos S3, P1 externa) |
| Frontend: Vitest | **278 / 278** |
| Frontend: `tsc -b`, ESLint, build | limpios |
