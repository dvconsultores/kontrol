# OBS-PROC08-TZ-01 · preflight acotado (2026-11-12)

## Qué se dijo

La PG completa de REP-10 dejó 14 rojas en PROC-08/PROC-10 «que fallan igual en `3cf7ed0`», atribuidas al ayudante
`tests/proc08_ayudantes.py`: envía la fecha del acto en UTC y, entre las 20:00 y las 24:00 de Caracas, esa fecha es
«futura» para la API.

## Reproducción

La ventana real dura cuatro horas al día, así que se reprodujo en determinista moviendo **solo el ayudante** al valor
que produce esa ventana: `hoy_de_negocio() + 1` día (lo que devuelve `datetime.now(UTC).date()` a las 22:00 de Caracas).

| Paso | Comando / dato | Resultado |
|---|---|---|
| Línea base (fuera de la ventana) | `pytest tests/test_gov_proc08_decision.py tests/test_gov_proc08_recomendacion.py tests/test_gov_proc10_garantias.py` sobre PG | 19/19 PASS |
| Reproducción | mismo conjunto con el ayudante enviando la fecha UTC del proceso | 14 FAIL, exactamente los de la observación |
| Mensaje | `POST /gobierno/actos` | `VALIDATION_ERROR · field_errors.fecha: «La fecha del acto no puede ser futura»` |

## Comparación de las dos orillas

| Orilla | Valor a las 22:00 de Caracas del 11-11-2026 | Quién lo usa |
|---|---|---|
| Día civil de negocio | `2026-11-11` | producto: `app.shared.clock.hoy_de_negocio()` (`America/Caracas`, OD-TIME-01/ADR-020) |
| Día UTC del proceso | `2026-11-12` | ayudante de pruebas: `datetime.now(UTC).date()` |

El producto está **correcto**: rechaza una fecha de acto futura comparando con el día de negocio. El defecto está en el
arnés, que pregunta el día civil a un instante UTC. Es el mismo patrón que ya se corrigió en el núcleo temporal y que
vigila `tests/test_business_clock_guard.py`.

## Clasificación

```
OBS_PROC08_TZ_ROOT_CAUSE=FECHA_CIVIL_DERIVADA_DE_UN_INSTANTE_UTC_EN_EL_AYUDANTE_DE_PRUEBAS
TEST_INFRASTRUCTURE_ONLY=1
PRODUCT_TIME_BUG=0
OBS_PROC08_TZ_01=CLOSED_TEST_INFRA
```

## Corrección (solo mantenimiento del arnés)

- `tests/proc08_ayudantes.py`: las dos fechas de acto se piden a `app.shared.clock.hoy_de_negocio()`. Sin cambios de
  semántica de producto.
- `tests/test_business_clock_guard.py`: guarda nueva que prohíbe `datetime.now(...).date()` en los ayudantes de prueba.
  La guarda es estática (`ast`) y falla nombrando el fichero y la línea, para que el patrón no vuelva.

## Pruebas dirigidas

| Comprobación | Resultado |
|---|---|
| `tests/test_gov_proc08_decision.py` + `test_gov_proc08_recomendacion.py` + `test_gov_proc10_garantias.py` (PG) | 19/19 PASS |
| Tras la corrección, el ayudante ya no lee el reloj del proceso: la guarda estática lo impide aunque se ejecute en la ventana | PASS |
| `test_business_clock_guard.py` + `test_business_clock.py` + `test_business_civil_date_documents.py` | PASS |
| `test_gov_proc07_evaluacion.py` + `test_gov_proc03_expedientes.py` (superficie vecina) | PASS |

Las catorce rojas de la PG completa desaparecen por la misma causa raíz, sin tocar producto.
