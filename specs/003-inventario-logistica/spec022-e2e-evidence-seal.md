# SPEC 022 · SELLO DE EVIDENCIA E2E

> 2026-09-04, sobre `18609af` más el delta de este sello. Cierra la deuda que quedó abierta al
> converger la implementación: la e2e propia del put-away no se había ejecutado.

## Regla que gobierna esta suite

**Un aviso de éxito no prueba nada.** Cada acción de interfaz se comprueba después contra el
dominio —movimiento, saldos, reservas, disponible—, porque lo que la Spec promete no es que la
pantalla diga que sí, sino que la mercancía quede ubicada **sin dejar de poder venderse**.

## Certificación por navegador

| Navegador | Casos | Resultado |
|---|---:|---|
| Chromium | 9 | **PASS** |
| Firefox | 9 | **PASS** |
| WebKit | 9 | **PASS** |
| **Total** | **27** | **27 pasadas · 0 fallos · 0 saltadas** |

Esperadas 27, ejecutadas 27. **Saltos inesperados: 0.** El contrato funcional es el mismo en los
tres: ninguno corre una versión reducida.

## Qué demuestra cada caso

| Caso | Qué prueba, y contra qué |
|---|---|
| El operario ubica la mercancía y el dominio lo confirma | Flujo completo por interfaz. Después: el saldo sin ubicar baja a cero, el de la ubicación sube a 100, el físico total no cambia, y el movimiento registra origen nulo, destino real, cantidad base y el mismo estado a ambos lados |
| Una ubicación inactiva se rechaza aunque se fuerce por API | La interfaz no es autoridad: `409 LOCATION_NOT_ELIGIBLE` y el saldo intacto |
| Una ubicación de otro almacén se rechaza aunque se fuerce por API | `409 LOCATION_OTHER_WAREHOUSE`. El put-away no traslada entre almacenes |
| Una ubicación desactivada **después** de listarla ya no sirve | TOCTOU real: se lista como candidata, se desactiva, y el envío con la pantalla vieja se rechaza sin mover nada |
| Dos envíos del mismo put-away no duplican el traslado | Dos peticiones en paralelo: **una** mueve existencia; el total sigue siendo 100 |
| Ubicar no cambia lo reservado ni lo disponible del almacén | La invariante 100/30/70 de `D0-14`, por API real: el compromiso sigue en 30 y el número de reservas activas no varía |
| **La mercancía ubicada sigue pudiéndose reservar** | La frase que bloqueó la Spec un ciclo entero, convertida en prueba: tras ubicar las 100 en `L1`, reservar 30 **funciona** |
| Una capacidad menor que la cantidad no impide ubicar | `R-D0-14-6`: la API declara `"enforced": false` y colocar 100 en una ubicación que declara capacidad 5 procede |
| Ubicar no crea nada de picking | Las listas de preparación antes y después: delta cero. Y ninguna reserva lleva ubicación |

## Lo que esta suite **no** certifica, y quién lo hace

**El aislamiento entre empresas.** La base de e2e tiene una sola empresa, y crear otra habría
alterado el `companies[0]` del que dependen las demás suites. Lo certifica la suite multiempresa del
backend —`test_spec022_putaway.py`—, que corre sobre el arnés real de dos tenants y tres empresas y
cubre empresa ajena, almacén ajeno y usuario AB fuera de contexto. Decirlo es más honesto que montar
aquí una versión pobre de lo que allí está bien probado.

## Tres defectos que la e2e encontró

Ninguno habría aparecido en las pruebas de servicio.

### 1 · La API ocultaba la procedencia del movimiento

`movement_dict` no devolvía `source_state`, `target_state`, `source_location_id`,
`target_location_id` ni `base_quantity`. El ledger los guardaba desde las Specs 023 y 022, pero
nadie podía leerlos: **ni una prueba de extremo a extremo ni un auditor**. Lo descubrió la e2e al no
poder verificar su propio traslado. Corregido, con un guardia estructural que lo impide en adelante.

### 2 · Dos acciones distintas se llamaban igual

La tabla tenía un botón «Ubicar» por fila y el panel otro «Ubicar» para confirmar. Mismo nombre
accesible para dos cosas distintas en la misma pantalla: quien navegue por voz no puede distinguirlas,
y la prueba tampoco pudo. Ahora son «Elegir ubicación» y «Confirmar ubicación».

### 3 · El selector de almacenes truncaba en silencio

Pedía `/organization/warehouses` sin límite y el endpoint devuelve 50 por defecto. Con más almacenes,
los siguientes simplemente no aparecían —sin aviso, sin paginación, sin nada—. Se pide un límite
explícito. **Queda dicho el techo:** por encima de 500 haría falta un selector con búsqueda, y eso es
de la Spec 008, no de esta.

## El entorno se perdió a mitad, y eso invalidó una corrida

Durante el ciclo, el proceso que sostenía el entorno murió y el scratchpad quedó vacío: PostgreSQL
—binarios y datos— y ClamAV desaparecieron. Una regresión de backend llegó a completarse **en esas
condiciones** y dio 32 fallos y **499 saltos** en vez de 8: sin `KONTROL_TEST_DB_URL` todo lo que
depende de PostgreSQL se saltaba, y sin antivirus la suite documental fallaba entera.

Esa corrida **no se usó como evidencia**. Se reconstruyó el entorno completo —PostgreSQL 18.6 en UTC,
ClamAV 1.4.3 con su firma verificada, las cuatro bases, la siembra hostil y la base de e2e migrada y
sembrada— y se repitió todo. Las cifras de este sello son las de la corrida sobre el entorno
reconstruido, con **8 saltos declarados**, que es la línea base de siempre.

Un recuento de saltos que se dispara de 8 a 499 no es ruido: es la señal de que el entorno no está.
Por eso el conteo de saltos es parte del sello y no una nota al pie.

## Clasificación de fallos

| Clasificación | Casos |
|---|---:|
| `NEW_REGRESSION_SPEC022` | **0** |
| `TEST_DEFECT` (corregidos en la propia suite) | 3 — fila equivocada, ruta de picking que sí existía, aserción sobre toda la tabla |
| Defectos de producto encontrados y corregidos | 3 — los de arriba |
| `PREEXISTING_SEALED` | 0 |
| `EXTERNAL_ENVIRONMENT` | 1 — la pérdida del entorno descrita arriba; corrida descartada y repetida |
| `UNKNOWN` | **0** |

## Veredicto

`SPEC 022 — COMPLETE / CONVERGED / EVIDENCE SEALED`
