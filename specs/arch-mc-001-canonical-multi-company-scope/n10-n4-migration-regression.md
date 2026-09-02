# N10 — REGRESIÓN DEL MARCO DE MIGRACIÓN DE LEGADO

El clasificador de N4 se reejecutó completo sobre el fixture hostil versionado
(`qa/n4-legacy-hostile-seed.py`, esquema `0032`).

| Clase | Estado |
|---|---|
| MC-A determinista | PASS |
| MC-B reconstruible | PASS |
| MC-C ambigua | PASS |
| MC-D no reconstruible | PASS |
| MC-E crítica | PASS |
| `INVALID_LEGACY_SCOPE` | PASS |
| `CROSS_TENANT` | PASS |
| `MASTER_ASSIGN` | PASS |
| `MASTER_CLONE` | PASS |
| `MASTER_DERIVE` | PASS |
| `MASTER_MANUAL_REVIEW` | PASS |

| Propiedad | Resultado |
|---|---|
| Escrituras del clasificador | **0** |
| Repetibilidad (diferencia semántica entre dos pasadas) | **0** |
| MC-D como cajón de sastre | No: cada clase tiene semilla propia y su prueba falla si se retira |

## Independencia del ORM vigente

El clasificador decide qué revisar a partir del **esquema de origen**, no del
modelo final. Es lo que le permite seguir siendo útil con una instalación
heredada cuyo esquema no se parece al actual.

N10 lo comprobó de la única forma que vale: `0039` retiró cinco columnas del
esquema vigente y el clasificador siguió clasificando el fixture hostil, que
vive en `0032` y todavía las tiene.

## Backfill real

`NOT_APPLICABLE — NO DEPLOYED LEGACY INSTALLATIONS`. Sin cambios en N10.
