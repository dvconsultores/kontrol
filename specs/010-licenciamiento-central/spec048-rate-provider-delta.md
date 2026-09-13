# SPEC 048 · DELTA DIRIGIDO — PROVEEDOR AUTOMÁTICO DE TASAS

> Iniciado el 2026-09-13, después del cierre formal de la Spec 013.
> Dueño: `specs/010-licenciamiento-central` (`spec-equivalence-map.md` línea 55:
> «048 Integraciones · `010-licenciamiento-central` (parcial)»). No se crea otra
> Spec.
>
> **Estado del delta: detenido en `/speckit.analyze` por pregunta material.**
> No hay implementación.

## 1. `/speckit.specify` — qué se pide

Un proveedor externo que entregue observaciones de tasa **ya normalizadas** a la
Spec 013, que las valida y persiste; la 038 las consume por su contrato de
siempre.

| La 048 hace | La 048 no hace |
|---|---|
| acceso externo, adaptador, transporte, tiempos de espera, reintentos técnicos | maestro de monedas ni observación canónica (013) |
| salud del proveedor, procedencia bruta, frontera de normalización | política de tasa, prioridad de fuente ni histórico (013) |
| sincronización programada técnica, deduplicación por identidad del proveedor | instantánea de tesorería, conversión ni saldos (038) |

Requisitos del delta: `Decimal` desde el texto externo sin pasar por `float`;
idempotencia por identidad estable; fallo del proveedor sin tasa inventada ni
fuente alternativa silenciosa; rechazo de cero, negativos, `NaN`, `Infinity`,
fechas mal formadas, moneda desconocida y par imposible; salud con último
intento, último éxito, último error y recuentos.

El contrato de recepción ya existe en la 013:
`ingest_provider_observations` (`app/modules/treasury/rates.py`).

## 2. `/speckit.clarify` — investigación de la fuente

Consultada la fuente oficial, el **Banco Central de Venezuela**, el 2026-09-13.
Solo lectura.

| Punto | Hallazgo |
|---|---|
| 1 · Fuente oficial disponible | Sí: portada de `www.bcv.org.ve` y publicación estadística «Tipo de cambio de referencia» |
| 2 · Mecanismo de acceso | HTTP sin autenticación. **No hay API**: `/api`, `/api/v1` y `/rest` responden 404 |
| 3 · Formato | Portada: HTML (`div#dolar … strong.strong-tb` con `842,20670000`, coma decimal, 8 decimales). Estadística: ficheros `.xls` (BIFF antiguo) trimestrales `2_1_2{a,b,c,d}{aa}_smc.xls`, una hoja por día de operación |
| 4 · Estabilidad | Sin contrato publicado. El XLS lo **editan personas** (metadatos de autor y de último guardado), el nombre del fichero rota cada trimestre y la portada es un tema de Drupal |
| 5 · Autenticación | Ninguna |
| 6 · Límite de peticiones | `robots.txt`: `Crawl-delay: 10`. Sin términos de consumo automatizado localizados |
| 7 · Marcas de tiempo | Cada hoja trae **Fecha Operación** y **Fecha Valor**, y no coinciden: operación 11/09/2026 → valor 15/09/2026. La portada muestra la Fecha Valor |
| 8 · Monedas | EUR, CNY, TRY, RUB, USD, CAD y otras en el XLS; USD, EUR, CNY, TRY y RUB en la portada |
| 9 · Semántica base/quote | Dos bloques por moneda: cotización M.E./US$ y **Bs./M.E.**, cada uno con **compra (BID)** y **venta (ASK)**. La portada publica la **venta** (USD 842,2067 = ASK del XLS) |
| 10 · Términos técnicos | TLS **no verifica**: el servidor envía un intermedio que no es el emisor de su certificado (`Verify return code: 21`). Consumirlo exige desactivar la verificación o fijar a mano el intermedio correcto |
| 11 · Automatización | Técnicamente posible por *scraping* de la portada o por lectura del XLS; ninguna de las dos tiene contrato |

El repositorio no tiene ni cliente de integración ni planificador de tareas:
`httpx` está en `requirements.txt` y solo lo usa el licenciamiento central; los
«trabajos asíncronos» de `reporting` no son un planificador periódico. Leer
`.xls` exigiría además una dependencia nueva.

## 3. Preguntas materiales

**OQ-048-01 · Fuente automatizable autorizada.** Las únicas vías son *scraping*
de la portada o lectura de un XLS editado a mano con nombre rotatorio. El
criterio del delta (§26 del prompt maestro) prohíbe presentar cualquiera de las
dos como «integración con el BCV» sin autorización: ¿se autoriza una de ellas
—y cuál—, se designa un proveedor alternativo, o se mantiene la carga manual e
importación de la 013 como única vía?

**OQ-048-02 · Tratamiento del TLS roto.** ¿Se autoriza fijar el intermedio
correcto en el adaptador (con su caducidad y su renovación a cargo de alguien) o
se prohíbe consumir la fuente mientras no verifique? Desactivar la verificación
no se propone.

**OQ-048-03 · Qué número es la tasa oficial.** Compra o venta, y **Fecha
Operación o Fecha Valor** como `effective_at`. Cambia las cifras contables de
toda operación en divisa. Toca terreno normativo: si hay regla, es de `D0-07`,
que sigue abierto; el repositorio no la contiene.

Las tres son materiales: cualquier respuesta cambia lo que se construye o el
número que se registra. Ninguna se resuelve con autoridad existente.

## 4. `/speckit.plan` — lo que se construiría con las respuestas

1. Contrato `ExternalRateProvider` (código, `fetch_rates(pares, ventana)`) en la
   frontera de la 048, devolviendo observaciones normalizadas con identidad del
   proveedor y huella del contenido bruto.
2. Adaptador de la fuente autorizada, con transporte a través de `httpx`, tiempo
   de espera, reintentos acotados y respeto del `Crawl-delay`.
3. Sincronización idempotente y observable sobre un mecanismo de ejecución que
   hoy **no existe**: se decidiría con la respuesta a OQ-048-01, sin crear un
   planificador paralelo si el despliegue ya ofrece uno.
4. Salud del proveedor sobre los campos que la 013 ya tiene
   (`last_sync_at`, `last_success_at`, `last_error`), más recuentos.
5. Flujos: 013 recibe → valida → persiste; 038 bloquea sin tasa, sincroniza y
   usa la tasa exacta en su instantánea. Instalación limpia obligatoria (P24).

## 5. Compuerta constitucional

| Principio | Estado |
|---|---|
| P19 · reglas normativas con fuente | **no satisfecho**: OQ-048-03 no tiene fuente |
| P20 · no sustitución de organismos oficiales | **no satisfecho**: presentar *scraping* como integración oficial lo vulneraría sin OQ-048-01 |
| P13 · integridad transaccional | planificable: idempotencia por identidad y captura estrecha (P25) |
| P21 · paridad del motor | planificable |
| P24 · instalación limpia | planificable |

## 6. `/speckit.checklist` y `/speckit.tasks`

Preparadas y **no iniciadas**: contrato, adaptador, normalización `Decimal`,
idempotencia, fallo controlado, salud, sincronización, integración 013,
consumo 038, instalación limpia, y las mutaciones M048-RATE-01 a 07 del prompt
maestro. Todas dependen de OQ-048-01; el adaptador y su TLS, de OQ-048-02; el
mapeo a `effective_at` y a la columna, de OQ-048-03.

## 7. `/speckit.analyze`

| | |
|---|---|
| BLOCKER | 1 — no hay fuente autorizada (OQ-048-01) |
| CRITICAL | 1 — la cifra oficial no está definida (OQ-048-03) |
| CONTRADICTIONS | 0 |
| MATERIAL OQ | **3** |
| UNKNOWN | 0 |
| TRACEABILITY | los requisitos del §1 están trazados a tareas del §6; ninguno a código, porque no se implementa |

**Veredicto: `SPEC048 · delta de proveedor de tasas — BLOCKED BY MATERIAL
DECISION`.** La autorización expresa no se consume: exige `MATERIAL OQ = 0`.

## 8. Lo que sigue funcionando mientras tanto

La Spec 013 opera por **carga manual** e **importación de fichero**, con el
contrato de proveedor definido. Ninguna operación de tesorería queda sin camino:
sin tasa se bloquea con `RATE_NOT_AVAILABLE`, como debe.

La Spec 048 global sigue en `PARTIALLY_IMPLEMENTED`. `D0-07` sigue abierto: una
integración con el BCV, si llega, tampoco lo cerraría.
