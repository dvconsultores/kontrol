# Firmas de estado (clasificación del ayudante, localizadores exactos)

Conteos: `activar` = `button[name="Activar" exact]`, `desactivar` = `button[name="Desactivar" exact]`, `activa` =
`button[name="Activa" exact]`, `compuerta` = `data-testid` `elegir-empresa-<código>` (o `/^elegir-empresa-/` sin código).

| Firma | Condición | Significado |
|---|---|---|
| `STATE_ACTIVE_SIGNATURE` (ACTIVA) | `desactivar == 1 ∧ activa == 1 ∧ compuerta == 0` (cualquier nº de `Activar`: las otras filas) | una empresa activa: la pareja `Activa`+`Desactivar` es **un** estado, no dos |
| `STATE_INACTIVE_SIGNATURE` (INACTIVA) | `desactivar == 0 ∧ activa == 0 ∧ compuerta == 0 ∧ activar ≥ 1` | tabla pintada sin activa; decidible si `activar == 1` |
| `STATE_GATE_SIGNATURE` (COMPUERTA) | `desactivar == 0 ∧ activa == 0 ∧ activar == 0 ∧ compuerta ≥ 1` | compuerta de selección; decidible si `compuerta == 1` |
| `NOT_PAINTED_SIGNATURE` (NO_LISTA) | los cuatro conteos a 0 | transitorio: cargando o sin pintar; **no es error** hasta agotar el tiempo |
| `AMBIGUOUS_SIGNATURE` (AMBIGUO) | cualquier otra combinación (p. ej. `desactivar ≠ activa`, `desactivar > 1`, tabla y compuerta a la vez) | contradictorio: falla al agotar el tiempo con el diagnóstico |

Decidibles: ACTIVA (idempotente: no pulsa), INACTIVA con `activar == 1`, COMPUERTA con `compuerta == 1`; con más de una
candidata o puerta y sin código, el ayudante sigue exigiendo el código (contrato previo). `STATE_SIGNATURES = PROVEN`.
