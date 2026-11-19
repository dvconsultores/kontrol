# Plan · ORG-07-EFFECTIVE-AUTHORITY-MATRIX

## Backend

1. **ORG-04 (`service_ocupacion.py`):** función pública `autoridad_efectiva_en(db, ctx, cargo_ids, fecha) -> dict[cargo_id, {"ejerce": fuente | None, "delegaciones": [fuente + competencias]}]`, construida sobre `_vigentes_en` y `_competencias_de`. Cada fuente lleva figura, etiqueta, asignación, vigencia, funcionario, titular sustituido (solo en las temporales), cargo de origen, acto y avocaciones registradas hasta la fecha.
2. **ORG-07 (`service_autoridad.py`):** `_filas_filtradas(..., ver_personas)` consume esa función con importación diferida, porque ORG-04 ya importa `competencias_en_vigor` de ORG-07. Añade `fuente` y `origen` a las filas del cargo y crea las filas de delegación. Sin `ver_personas`, reserva a las personas (OD-EA-01). El texto libre busca por la persona solo si es visible. La ordenación queda así: unidad, cargo, acción y materia; dentro de cada una, primero el cargo y después las delegaciones por código.
3. **CSV:** columnas nuevas al final: `figura`, `persona_codigo`, `persona`, `sustituye_a`, `asignacion`, `asignacion_desde`, `asignacion_hasta`, `acto` y `cargo_origen`.
4. **API (`api_autoridad.py`):** `ver_personas` se calcula con `gobierno_ocupacion:view`, siguiendo el patrón de `_puede_publicar`.
5. **Esquemas:** `MatrizFuente`, `MatrizPersona`, `MatrizCargoRef` y `MatrizActoRef`; `MatrizFila.fuente` es opcional y `origen` pasa a texto.

## Frontend

- `api.ts` o los tipos de la matriz: tipos nuevos.
- `MatrizAutoridadPage.tsx`:
  - se quita el aviso y se pone uno neutro que explica las fuentes;
  - columna «Ejerce» con persona y fuente, y etiqueta de `origen`;
  - sección «Fuente de autoridad» en el detalle del cargo o de la fila.
- Vitest de la pantalla.

## Pruebas

- **PG:** `tests/test_gov_org07_efectiva.py`, con las fixtures de ORG-04, que cubren los 20 puntos del §29.
- **Mutaciones:** M1–M8 (§30).
- **E2E:** `e2e/gobierno-autoridad-efectiva.spec.ts` (efectiva, histórica, CSV y Axe).
- **Regresión:** `test_gov_org07_autoridad.py`, `gobierno-autoridad.spec.ts` y el humo UAT.

## Sin migración

Cabeza `0127_gov_handover_policy`.
