# Clasificación de defectos · CTL-05 sobre `b73c171`

## mypy: 27 errores en `service_rendicion.py` y `api_rendicion.py`, más 4 ajenos

| Clase | Nº | Errores | Efecto en ejecución |
|---|---|---|---|
| PRODUCT_ERROR | 5 | `_CatalogSpec` sin definir (2 veces); `GovernmentEntity.name` (el atributo real es `denominacion`); `.label` sobre un posible dict vacío; `sr._usuarios_por_ids` | Respectivamente: NameError; AttributeError; AttributeError; AttributeError en el historial |
| TYPE_CONTRACT_ERROR | 22 | UUID frente a str en variables e ids (`_ordinales_provisionales`, `_snapshot_responsable`, asignaciones) | Ninguno en ejecución (los ids ya son str en la base); rompe la compuerta mypy |
| TEST_ERROR | 0 | — | — |
| PREEXISTING_UNRELATED | 4 | `documents/scanning.py` 83 y 111; `core/company_context.py` 83 y 84 | Fuera de alcance; ya estaban en la línea base |

**Sobre `sr._usuarios_por_ids`:** este error lo **introdujo el retoque mecánico de Claude** (`ruff --fix` F401), que quitó del servicio un import que la API usa a través del módulo del servicio. Se declara. La corrección la escribe DeepSeek: la API debe importarlo de `service_auditoria`.

## Suite PostgreSQL: 11/11 en rojo

Las 11 pruebas son **TEST_DEFECT** con una misma causa raíz:
- **Ayudante de la prueba.** `_crear_expediente` y rn01 usan `titular_activo(...)["id"]`, pero `titular_activo` devuelve la tupla `(asignacion, cargo_id)` (tests/org04_ayudantes.py:444).
- **Dato inventado.** `_incorporar_eventos` lee `f["evento_id"]`, y `crear_funcionario` devuelve el funcionario, sin ese campo (tests/org04_ayudantes.py:287).
- **Período incompatible.** rn01 pide el período 2024, pero la ocupación de prueba es del ejercicio en curso. Daría 422 RESPONSIBLE_INVALID, que es correcto según el contrato.

El producto no llega a ejecutarse. **Ningún PRODUCT_DEFECT está demostrado todavía por pruebas**; se medirá cuando la prueba sea válida.

## Justificación del nuevo ciclo (regla de reintentos)

- **NEW_TECHNICAL_BOUNDARY:** la publicación de P2 invalida la revisión 0098 de CTL-05 y obliga a renumerar (0099) y a actualizar las cabezas.
- **NEW_ROOT_CAUSE (pruebas):** contrato de ayudantes mal usado (tupla y campo inexistente). No se había diagnosticado antes porque la suite no arrancaba.
- **mypy residual:** lo dejaron los 8 bloques de C3 rechazados por SEARCH no único. Ahora el SEARCH es el fragmento completo y verificado como único. La dueña autorizó ampliar el presupuesto (+6 llamadas).
