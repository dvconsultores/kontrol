# PLAN — ARCH-MC-001

## Fases

| Fase | Contenido | Por qué va aquí |
|---|---|---|
| **N0** | Gobierno: ADR, matrices, plan de migración y de pruebas | Sin alcance canónico declarado, cada dominio decidiría el suyo |
| **N1** | `CompanyContext` en el backend | **Prerrequisito de todo.** Sin saber en qué empresa ocurre la petición no se puede escribir bien ni una fila |
| **N2** | Cortar la hemorragia | En cuanto haya contexto, ningún escritor puede seguir poniendo `tenant_id` en `company_id`. Cada día que pasa amplía el backfill |
| **N3** | Expandir el esquema | Columnas y relaciones nuevas **sin** destruir las heredadas |
| **N4** | Rellenar y verificar | Clasificación `MC-A`..`MC-E`, informe previo sin escribir, resolución manual auditable |
| **N5** | Migrar los dominios | Servicios, repositorios, API, consultas, eventos y auditoría, por olas |
| **N6** | Frontend | El contexto se propaga; la empresa **no** se añade a cada formulario |
| **N7** | Restringir | `NOT NULL`, FK, únicos e índices, una vez demostrada la integridad |
| **N8** | Contraer | Retirar columnas heredadas y ramas de compatibilidad. Sin modo dual permanente |

> **N1 antes que N2, y N2 antes que N3** no es preferencia. Migrar datos mientras
> se siguen escribiendo mal es rellenar un cubo agujereado.

## Olas de dominio en N5

Orden derivado de las FK reales, no impuesto:

| Ola | Dominio | Tablas | Depende de |
|---|---|---:|---|
| 1 | Organización y accesos | 8 | — |
| 2 | Maestros | 24 | 1 |
| 3 | **Fiscal** | 13 | 1, 2 |
| 4 | Compras | 21 | 2, 3 |
| 5 | Inventario | 13 | 2, 4 |
| 6 | Ventas | 14 | 2, 3, 5 |
| 7 | Tesorería | 15 | 3, 4, 6 |
| 8 | Regulatorio | 11 | 2, 5 |
| 9 | Transversales: auditoría, eventos, informes, documentos | 15 | todas |

Regla dura: **ninguna hija antes que su cabecera** (§106).

Fiscal va en la tercera ola pese a ser el riesgo mayor: necesita maestros
normalizados, y todo lo transaccional depende de sus series.

## Migraciones Alembic

Una por fase y dominio; **nunca** una monolítica para 82 tablas.

| Migración | Fase | Contenido |
|---|---|---|
| `00XX_mc_company_access` | N1 | Acceso usuario–empresa sobre la estructura existente |
| `00XX_mc_expand_<dominio>` | N3 | Columnas nuevas, anulables, sin tocar las heredadas |
| `00XX_mc_backfill_<dominio>` | N4 | Rellena y reporta; **aborta** con críticos sin resolver |
| `00XX_mc_constrain_<dominio>` | N7 | `NOT NULL`, FK, únicos |
| `00XX_mc_contract_<dominio>` | N8 | Retira lo heredado |

Cada `backfill` sigue el patrón de la `0024` de la Spec 046: lee, clasifica,
informa, comprueba sus invariantes y **se detiene** si las incumple.

## Módulos tocados

| Módulo | Naturaleza del cambio |
|---|---|
| `identity_access` | `CompanyContext`, resolución de acceso, dependencia de FastAPI |
| `organization` | Autoridad de empresa; imposición del plan |
| `licensing` | Límite de empresas según derechos |
| Los 8 de negocio | 100 escrituras y 75 lecturas reescritas |
| `documents` | `ResourceKind` declara alcance; 4 entradas nuevas |
| Frontend | Interceptor con la cabecera, selector, invalidación de caché |

## Lo que este plan **no** hace

Implementar la Spec 012, flujos nuevos, reglas fiscales nuevas, ni nada
intercompany. Corrige la propiedad de lo que ya existe.
