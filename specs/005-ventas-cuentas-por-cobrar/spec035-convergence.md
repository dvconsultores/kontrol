# SPEC 035 · CONVERGENCIA

`SPEC 035 — COMPLETE / CONVERGED` (técnica y funcionalmente)

> 2026-09-07, sobre `255f039`. Ciclo completo desde `/speckit.specify`.

## El hallazgo

`validate_shipment` prometía en su docstring bloquear el despacho «si falta,
venció o no coincide un requisito». Su cuerpo entero era:

```python
shipment.validation_status = "APPROVED"
shipment.status = "READY"
```

**Aprobaba siempre.** Y `regulatory.evaluate_shipment` —que resuelve los perfiles
aplicables por producto y operación, comprueba los documentos oficiales
requeridos y devuelve `BLOCKED` con sus motivos— existía, funcionaba y nadie la
llamaba desde el despacho.

El ciclo no consistió en construir la compuerta. Consistió en **conectarla**.

## Dos defectos más, en la salida física

| Defecto | Consecuencia |
|---|---|
| `quantity=-line.quantity` | Despachar dos cajas de doce sacaba **2** unidades, no 24 |
| Sin estado de mercancía | Descontaba de `DISPONIBLE`, cuando la Spec 032 dejó la mercancía en `PREPARADO` |

Ninguno se veía porque el único camino probado creaba el despacho desde
existencia suelta. En cuanto la cadena existió entera, los dos se disparaban.

## Un tercer defecto, en la superficie

La compuerta quedó conectada pero solo era alcanzable llamando a la API. La
pantalla que existía seguía siendo la del despacho libre: ofrecía crear pick
lists —trabajo que la 031 y la 032 se llevaron—, dejaba elegir pedidos en
`RELEASED` o `PREPARING`, y **pedía la cantidad a mano**. Ese último campo es el
que produce exactamente el defecto que este ciclo corrigió en el backend: quien
escribe «2» donde hay dos cajas de doce saca dos unidades y deja veintidós
preparadas para siempre.

La pantalla nueva no tiene campo de cantidad. Sale lo que la Spec 032
consolidó, derivado del plan cerrado con su lote y su serie, y el almacén de
origen es el del pedido porque elegir otro describiría un traslado que no
ocurrió.

## Puerta

| Criterio | Resultado |
|---|---|
| Se despacha sin confirmación independiente | **no** |
| Se despacha con factura solo generada | **no** — el ¶95 y el ¶97 son dos actos |
| Se despacha sin decir destino ni responsable | **no** |
| Un requisito regulatorio faltante o vencido bloquea | **sí** |
| Los requisitos son concurrentes, no alternativos | **sí** |
| Se emiten permisos oficiales o se simula verificación en línea | **0** |
| La salida es en cantidad base | sí — 2 cajas ×12 salen 24 |
| La salida sale de `PREPARADO` | sí, desde el Área de Confirmación |
| `DESPACHADO → VENDIDO` activada | **no** — ningún evento del Proceso 9 la escribe |
| La salida consume la reserva | sí, `FULFILLED` |
| Quién puede despachar | **solo `INVOICED`** |
| El despacho es idempotente | sí |
| Un pedido se despacha dos veces | **no** — conflicto legible en el servicio, índice único en la base |
| La cantidad que sale se teclea | **no** — se deriva de lo consolidado |
| El vehículo o el conductor pueden ser de otra empresa | **no** |
| La cola trae pedidos sin factura emitida | **no** |
| Backend | 1226 pruebas · **1218 pasan · 8 saltos · 0 fallos · 0 errores** |
| Saltos esperados / reales | **8 / 8**, todos S3 |
| Saltos inesperados | **0** |
| Frontend | vitest 295/295 · `tsc`, ESLint y Ruff limpios · build correcto |
| E2E de la 035 | **24/24** en Chromium, Firefox y WebKit |
| Cadena operativa e2e | **126/126** en los tres navegadores |
| Guardias de arquitectura 031→035 | **103/103**, sin saltos |
| Fronteras posicionales frágiles | **0** |
| Migración `0053` | ida y vuelta sobre base limpia, verificada el 2026-09-07 |
| Trazabilidad | **100 %**, 34 requisitos funcionales, 0 huérfanos |
| Preguntas materiales nuevas | **0** |

## La deuda que este tramo dejó anotada, cerrada

Al cerrar la Spec 034 quedó dicho que `CONFIRMED → SHIPPED` seguía abierta y que
cerrarla era la compuerta de la 035. Se ha cerrado, y no solo comprobándola: las
aristas `RELEASED → SHIPPED`, `PREPARING → SHIPPED`, `PREPARED → SHIPPED` y
`CONFIRMED → SHIPPED` **se quitaron de la máquina**. Hoy solo `INVOICED` puede
despachar, que es lo que dice el ¶103.

## Lo que se midió, no se supuso

Dos mutaciones. Quitando la compuerta regulatoria, la prueba del permiso
faltante falla. Y la segunda mutación **destapó un defecto en mi propia prueba**:
al principio pasaba la cantidad base en los dos campos de la línea de despacho,
de modo que cambiar `base_quantity` por `quantity` no cambiaba nada. Corregida
la prueba para llevar la comercial en `quantity` y la base en `base_quantity`
—como la lleva la línea del pedido—, la mutación falla como debía.

## Guardias actualizadas con su razón

Cuatro pruebas afirmaban lo contrario de lo que ahora es cierto, porque se
escribieron cuando la cadena no existía:

| Prueba | Qué afirmaba | Qué afirma |
|---|---|---|
| `test_sales.py::test_shipment_validate_and_confirm` | que un pedido recién liberado se podía despachar | que no se puede, y por qué |
| `test_spec030_reservation.py::…_despachar_consume` | despachaba desde `RELEASED` para probar el consumo | que despachar desde ahí está bloqueado; el consumo lo prueba la 035 |
| `test_spec030_architecture.py::test_la_maquina_de_estados_es_la_de_d0_03` | cuatro estados podían despachar | solo `INVOICED` |
| `test_sales.py::test_shipment_requires_validation` | creaba el despacho desde `RELEASED` para probar que sin validar no se confirma | que desde ahí no hay despacho que crear; la cadena entera la prueba la 035 |

## Las dos separaciones que hay que conservar

**Certificación técnica ≠ homologación legal.** `D0-07` sigue abierto y las Specs
039-043 siguen en `BLOCKED_BY_LEGAL_VALIDATION`. Este ciclo certifica el
despacho **técnica y funcionalmente** contra el motor fiscal existente. **No**
afirma homologación fiscal ni liberación legal para producción.

**Validar ≠ emitir.** La Spec 044 sigue `BLOCKED_BY_EXTERNAL_SERVICE`: sin API
oficial, KONTROL registra el permiso, valida contra lo registrado, adjunta la
evidencia y bloquea. **No emite ninguno y no dice haber verificado en línea lo
que no puede verificar.**

## Un hallazgo ajeno, medido y arreglado en su dueña

La cadena operativa e2e dejó seis pruebas rojas de la Spec 031, y no por nada de
este ciclo. El selector de almacén de `PreparacionPage` pide
`/organization/warehouses?limit=500`; la base de e2e tiene **564** almacenes
acumulados de cientos de corridas, y la respuesta se corta:

```
limit=500  total=564  devueltos=500  último=WP-MTPWKP5AHCPN
limit=1000 total=564  devueltos=564  último=WP-MTQOAZ73GGOT
```

Los 64 que faltan incluyen el que cada prueba acaba de crear, así que la opción
no existe y `selectOption` falla. El selector **descarta almacenes en silencio**,
sin decirlo ni ofrecer búsqueda.

El defecto es de la Spec 031, no de esta, así que se arregla **en su dueña** y
como delta dirigido: la página pide tandas hasta agotar `total` en vez de
confiar en un tope. Subir 500 a 2000 habría movido el acantilado y escrito un
número que ya se sabe equivocado. Con el delta, las seis pruebas pasan —24/24 en
los tres navegadores— y fallaban por la razón correcta.

Lo que **no** se absorbe es el patrón: el mismo selector está en otras ocho
pantallas y siete ni siquiera declaran límite, con lo que se quedan en los 50
por defecto. Eso es del módulo de organización y queda anotado con su medida.

## El defecto de test que llegó hasta la regresión, y su clase

La primera regresión completa acabó con un solo fallo:
`test_spec034_architecture.py::test_facturar_no_despacha`, acusando a la Spec 034
de haber absorbido el despacho. No lo había hecho. El guardia delimitaba su
bloque como «desde mi cabecera hasta `def create_shipment(`», y la 035 había
puesto delante de esa función cuatro auxiliares suyos —`_live_shipment`,
`_require_vehicle`, `_require_driver`, `_lineas_consolidadas`—. El guardia los
contó como código de la 034.

| | |
|---|---|
| Clasificación | `TEST_DEFECT` |
| Defecto de producto | **no** |
| Regresión de la 034 | **no** |
| Regresión de la 035 | **no** |
| Causa raíz | frontera de propiedad **posicional** |
| Arreglo | cabecera semántica de Spec, y un helper compartido que la aplica |

El código de negocio **no** se deformó para satisfacer el test: ningún auxiliar
se movió, se renombró ni se escondió, y no se añadió ningún `xfail`, `skip` ni
assertion debilitada.

### La clase de defecto, no solo el caso

Era la quinta vez en el tramo. La auditoría de los guardias 031→035 encontró
**cuatro fronteras posicionales más, todas vivas y ninguna fallando todavía**:
la 032, la 033 (dos veces) y la 034 delimitaban su bloque de `api.py` como
«desde mi primer modelo hasta `@router.post("/shipments"`». Las dos rutas nuevas
del despacho —`/despacho/pendientes` y `/despacho/{order_id}/despacho`— quedaron
justo antes de esa marca y **ya estaban dentro** de los tres bloques ajenos. No
saltó nada porque esos guardias solo comprueban que los permisos usados existan
en el catálogo, y `ventas:view` existe. Habría sido la sexta repetición, esta
vez silenciosa.

Se corrigieron las cinco, más otras dos ventanas accidentales de la 031 —«desde
mi cabecera hasta el final del fichero» y «los 2000 caracteres siguientes a
`class PickList`»—.

| | |
|---|---:|
| Ficheros de guardias auditados | 6 |
| Fronteras semánticas | **todas** |
| Fronteras posicionales frágiles | **0** |
| Helper compartido | `tests/spec_blocks.py` |

### La invariante, escrita para que no vuelva

> Las Specs son fronteras semánticas, no posiciones accidentales dentro de un
> archivo. Los architecture guards deben reconocer explícitamente al owner
> siguiente mediante un marcador estable de Spec, módulo o namespace, y nunca
> inferir la frontera por la siguiente función o clase.

Es una **invariante transversal de los tests de arquitectura**, no un requisito
de negocio. Vive en `tests/test_architecture_boundaries.py`, que reproduce el
defecto exacto sobre una fuente de mentira, demuestra que el recorte viejo sí lo
produce, comprueba que la frontera no depende del nombre ni del sitio de la
función pública, exige cabecera única por Spec en `service.py` y en `api.py`, y
—lo que mata la clase entera— prohíbe por parametrización que cualquiera de los
cinco guardias vuelva a recortar el texto de un módulo a mano.

Mutación: devolver el corte a `def create_shipment(` hace fallar a la vez la
invariante y el test original. Restaurado, verde.

Dos regresiones completas, en serie y nunca en paralelo. La primera, sobre el
arreglo de la frontera 034→035: **1209 · 1201 pasan · 8 saltos · 0 fallos**. La
segunda, ya con las cuatro fronteras de `api.py` corregidas, el helper
compartido y las 17 pruebas nuevas de invariante: **1226 · 1218 pasan · 8 saltos
· 0 fallos · 0 errores**.

## Deuda anotada, no absorbida

| Hallazgo | Dueño |
|---|---|
| Selector de almacén truncado sin aviso en otras 8 pantallas (7 en los 50 por defecto) | organización / Spec 008 |
| `PICKING → DISPONIBLE`: deshacer una preparación rechazada | Spec 032 |
| `DESPACHADO → DEVUELTO`: el reingreso | Spec 036 |
| Verificación en línea de permisos | Spec 044, sin API oficial |
| Homologación fiscal | `D0-07` |
| `calculate_tax` en `float` | Spec 039 |

## Estado resultante

| | |
|---|---|
| Spec 035 | **COMPLETE / CONVERGED** (técnica y funcional) |
| Specs 005, 023, 030 | con sus deltas dirigidos convergidos |
| Spec 036 | **desbloqueada por dependencia**; contrato en `spec035-spec036-handoff-contract.md`. **No** `READY_FOR_IMPLEMENTATION`: el proceso fuente acaba en el ¶107 y sus cuatro preguntas siguen siendo materiales. **No implementada.** |
