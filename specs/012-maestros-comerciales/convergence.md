# CONVERGENCIA DOCUMENTAL — SPEC 012

## Qué se comparó

`spec.md`, `clarifications.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, `checklist.md`, `tasks.md`, `traceability-matrix.md`, la matriz de
dependencias y la baseline final de ARCH-MC-001.

## Puerta de convergencia

| Invariante | Resultado |
|---|---:|
| Alcance completo | 11 / 11 |
| Alcance indeterminado | 0 |
| Autoridad completa | 11 / 11 |
| Seguridad de rutas hijas | 5 / 5 rutas con contrato |
| Unicidad definida | 11 / 11 |
| Contradicción sobre Tercero | 0 |
| Contradicción sobre Producto | 0 |
| Contradicción sobre Moneda | 0 |
| Contradicción sobre unidades | 0 |
| Contradicción sobre presentación | 0 |
| Duplicación del motor de aprobación | 0 |
| Contradicción con OpenAPI | 0 |
| Contradicción de contexto en el frontend | 0 |
| Requisitos huérfanos | 0 |
| Tareas huérfanas | 0 |
| Preguntas abiertas materiales | 0 |
| Trazabilidad | 100% |
| **Cambios en código productivo** | **0** |

## Las cuatro contradicciones que se cerraron

**Nueve entidades contra once.** `spec.md` listaba nueve e incluía una
`PriceRule` que ningún artefacto define; `data-model.md` describía once. Se
reconcilia en once y se retira el nombre sobrante: lo que `PriceRule` iba a
hacer lo hace `PricePrecedence`.

**La empresa en el cuerpo.** Dos contratos —resolver precio y validar
descuento— la declaraban en su carga útil. Es la vulnerabilidad que la Spec 045
estrenó y que N5 cerró. Se retira de los dos.

**Una categoría sin tabla.** El modelo decía «o categoría» y no existe ninguna
`item_categories`. La categoría de un artículo es `taxonomy_nodes`, de empresa.
Se nombra.

**La unidad de plataforma.** `units_of_measure.company_id` es anulable y el nulo
significa unidad de la plataforma. Un `PriceListItem` que comprobara igualdad
estricta rechazaría una unidad legítima. La comprobación es «propia o de
plataforma».

## Deriva documental

**0.** Los diez artefactos dicen lo mismo sobre el alcance de cada entidad, sobre
la autoridad de cada petición y sobre quién posee cada maestro.

## Veredicto

`SPEC 012 — DOCUMENTALLY UPDATED / CONVERGED / READY FOR IMPLEMENTATION AUTHORIZATION`

No se implementó nada. El próximo ciclo requiere autorización expresa.
