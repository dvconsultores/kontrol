# SPEC 038 · TESORERÍA

> Ciclo completo dentro de la Spec 038 existente. Estado de entrada:
> `PARTIALLY_IMPLEMENTED`, desbloqueada por dependencia, con dos preguntas
> materiales que el owner del producto acaba de decidir.

## 1. Checkpoint

| | |
|---|---|
| `HEAD` | `287f9e2` |
| Padre | `187d8f3` |
| Árbol | limpio |
| Spec 037 | `COMPLETE / CONVERGED` |
| Máster 56 | 17 convergidas · 28 parciales · suma 56 |
| `D0-07` | **abierto** |
| PostgreSQL real | **16.2** · objetivo documentado 18.6 · `ENVIRONMENT_BASELINE_DEVIATION` |

## 2. Las dos decisiones del owner, y la comprobación de conflicto

`OWNER-DECISION-038-01` — el reembolso de un crédito a favor **se soporta**:
explícito, con reserva del crédito, aprobación y ejecución desde tesorería.
`OWNER-DECISION-038-02` — la política cambiaria es **parametrizable**, la
conversión **explícita** y la diferencia cambiaria un hecho aparte.

**`AUTHORITY_CONFLICT = 0`**, y conviene decir por qué cada una:

| Decisión | Qué dicen las fuentes | Veredicto |
|---|---|---|
| Reembolso | Ninguna fuente lo menciona, ni para permitirlo ni para prohibirlo. La 037 no lo construyó por eso mismo | La decisión **llena un vacío**; no contradice nada |
| Política cambiaria | Arq. funcional §9: «Diferencias cambiarias: se calculan al aplicar o valorar **según política**; no alteran el IVA original por sí solas» | La decisión **es** esa política, y respeta la segunda mitad al pie de la letra |

La fuente deja explícitamente el hueco —«según política»— y la decisión lo
llena sin tocar lo que la fuente sí fija.

## 3. Auditoría de lo que ya existe

La 038 no está vacía: quince modelos, cuarenta y dos servicios y treinta y ocho
rutas. Lo primero era ver qué hay, para no construir encima.

| Capacidad | Artefacto | ¿Existe? | Acción |
|---|---|---|---|
| Bancos, cuentas y cajas | `FinancialBank`, `FinancialAccount`, `Cashbox` | **sí** | reutilizar |
| Métodos e instrumentos | `PaymentMethod`, `TreasuryInstrument` | **sí** | reutilizar |
| Monedas y tasas | `Currency`, `ExchangeRate` | **sí** | reutilizar como maestro |
| Sesión de caja, arqueo y cierre | `CashSession`, `CashSessionMovement` | **sí** | reutilizar |
| Movimiento bancario | `BankTransaction` | **sí** | es el libro de hechos de facto |
| Transferencia entre cuentas | `TreasuryTransfer` | **sí** | reutilizar |
| Conciliación con propuesta de cruce | `Reconciliation`, `propose_matches` | **sí** | reutilizar |
| Ejecución de pago y de cobro | `execute_payment`, `execute_collection` | **sí** | corregir, no rehacer |
| IGTF | `FiscalRule`, `IgftEvent` | **sí**, aquí | **no se extiende**: su dueña es la 041 |
| **Reembolso** | — | **no** | construir |
| **Conversión FX explícita** | — | **no** | construir |
| **Política cambiaria versionada** | — | **no** | construir |
| **Instantánea de tasa con procedencia** | columna suelta `rate_snapshot` | **no** | construir |
| **Posición de caja** | — | **no** | construir |
| **Proyección de liquidez** | — | **no** | construir |

## 4. Cuatro defectos que la auditoría destapó

### 4.1 · La tasa se inventa en silencio

```python
def _rate_snapshot(db, company_id, currency) -> float:
    if currency in ("VED", "VES"):
        return 1.0
    cur = ...
    if not cur:
        return 1.0          # ← moneda desconocida
    row = ...
    return row.rate if row else 1.0   # ← sin tasa registrada
```

Si la moneda no está en el maestro, o si no hay ninguna tasa cargada, la función
devuelve **uno**. Un pago en dólares se registraría con tasa 1,0 y nadie se
enteraría. Es exactamente lo que §78 y §79 prohíben: «no rate invention», «no
fallback rate». Y toma la tasa **más reciente** sin mirar la fecha de la
operación, así que no hay base de fecha efectiva ninguna.

### 4.2 · La ejecución no mira la moneda de la cuenta

`execute_payment` resuelve la cuenta comprobando **solo la empresa** y luego
escribe el movimiento con `currency=payment.currency`. Un pago en dólares se
ejecuta contra una cuenta en bolívares y queda un movimiento en dólares dentro de
una cuenta que no lo es, sin ningún hecho de conversión. Es el caso que la regla
12 de `OWNER-DECISION-038-02` nombra: «Moneda A → Moneda B no puede ocultarse
dentro de una Application como simple cambio numérico».

### 4.3 · La ejecución no mira el saldo

Ni para cuenta ni para caja se comprueba que haya dinero. §71 lo pide explícito:
sin política de descubierto declarada, un egreso que deja la cuenta en negativo
se bloquea. No existe tal política, así que no se inventa: se bloquea.

### 4.4 · El arqueo calcula dinero en coma flotante

```python
session.difference = round(float(counted_amount) - float(expected), 6)
```

Misma familia que `KQA-100`, que `ADR-D0-001` registra como defecto CRÍTICO y
que el delta de la Spec 028 corrigió en el motor de saldos. El arqueo de caja
nunca lo recibió, y es dinero contado a mano contra dinero esperado: el sitio
donde una diferencia falsa de céntimos se convierte en una discusión con el
cajero.

## 5. Fronteras

La 038 **ejecuta y registra dinero**. No decide qué se debe —eso es de la 028—,
ni qué se cobra —de la 037—, ni cuánto impuesto corresponde —de la 041 y las
fiscales—, ni aprueba por su cuenta —de la 045—. No llama a ninguna web para
buscar una tasa: consume la que el maestro tenga registrada.

El IGTF ya vive en este módulo por historia. **No se amplía ni se le añade
lógica**: su dueña es la Spec 041 y ese traslado es de su ciclo, no de éste.

## 6. Lo que este ciclo construye

1. **Política cambiaria versionada**, con vigencia y procedencia.
2. **Instantánea de tasa** con moneda origen y destino, tasa, fuente, tipo,
   fecha y versión de política, congelada en la operación.
3. **Conversión FX explícita**, como hecho propio, con su diferencia cambiaria.
4. **Reembolso**: solicitud, reserva del crédito en la 037, aprobación,
   ejecución y liquidación, sin que el mismo importe pueda gastarse dos veces.
5. Los cuatro defectos de §4, corregidos.
6. **Posición de caja** y **proyección de liquidez**, como lecturas que no
   mueven dinero.

## 7. La separación que hay que conservar

`D0-07` sigue abierto. Este ciclo certifica la tesorería **técnica y
funcionalmente**. **No** afirma homologación fiscal ni liberación legal, y
ninguna regla legal venezolana se escribe en el código: se configura, se versiona
y se deja con su referencia de autoridad.

## 8. Lo implementado

### 8.1 · Migración `0055_spec038_treasury`

Cadena `0054 → 0055`. Crea `treasury_fx_policies`, `treasury_rate_snapshots`,
`treasury_fx_conversions` y `treasury_refunds`; añade `refund_reserved` y
`refunded` a `sales_credit_notes`, y `rate_snapshot_id` a `bank_transactions`.
Sube y baja limpia.

### 8.2 · La tasa dejó de inventarse

`_rate_snapshot` devolvía `1.0` cuando la moneda no estaba registrada o cuando
no había tasa del día. Un pago en divisa quedaba valorado al cambio uno a uno y
nada en pantalla lo decía. Ahora devuelve `None`, y `capture_rate_snapshot`
rechaza con `RATE_NOT_AVAILABLE`. La tasa manual existe pero exige que la
política la permita y que se escriba el motivo (`MANUAL_RATE_NOT_ALLOWED`).

La búsqueda es **con fecha** (`<= día`), no «la más reciente»: una tasa de hoy
no revalúa una operación de ayer. La instantánea guarda tasa, fuente, tipo,
fecha, origen (`REGISTERED` / `MANUAL`), versión de política y la fila de la que
salió, y queda congelada: una tasa posterior no la mueve.

### 8.3 · El reembolso, en tres actos

`OWNER-DECISION-038-01`. Solicitar **reserva** el crédito; aprobar no paga;
ejecutar saca el dinero y convierte la reserva en devuelto. Denegar libera la
reserva. Lo reservado deja de ser imputable en el acto, que es lo que impide
gastar dos veces el mismo dinero.

Ejecutar es **idempotente a propósito**: un reintento por corte de red no puede
convertirse en un segundo pago. Por eso la prueba no exige un código de rechazo
sino que el dinero no se mueva: mismo saldo, mismo movimiento, mismo importe
devuelto.

### 8.4 · Dos cifras donde antes había una (delta dirigido a la Spec 037)

Al aparecer el reembolso, «crédito disponible» dejó de ser una sola cosa:

- **Imputable** a documentos: `amount − applied − refund_reserved − refunded`.
- **Debido** al cliente: `amount − applied − refunded`. Una reserva sin ejecutar
  se sigue debiendo; solo cambió la forma en que se pagará.

`customer_credits` ofrecía como disponible un crédito ya reservado —el mismo
dinero contado dos veces, y una imputación que el servicio rechazaba después— y
`customer_balance` calculaba el saldo con la resta equivocada. Ambas se
corrigieron **en su dueña**, la Spec 037, no con una copia en tesorería. Antes
de la 038 las dos restas coincidían porque reservado y devuelto eran siempre
cero: ninguna cifra ya certificada cambia de valor.

### 8.5 · Posición de caja sin total

Por cuenta y por moneda, y **sin un número único**. Sumar bolívares con dólares
exige una tasa, y aplicar una tasa es convertir: un acto explícito con su
instantánea y su política. Un total general aquí sería una conversión que nadie
autorizó, hecha a un cambio que nadie eligió.

### 8.6 · API y pantallas

Doce rutas nuevas bajo `/treasury`, con los tres permisos del catálogo ya
existente (`tesoreria:view` / `create` / `approve`): no se inventaron permisos
nuevos. Tres pantallas —**Cambio de moneda**, **Reembolsos**, **Posición de
caja**— registradas en el router y en el menú, y el contrato OpenAPI
regenerado.

Ninguna regla legal venezolana está escrita en el código de estas pantallas: la
política se configura, se versiona y guarda de qué autoridad viene.

## 9. Evidencia

| Puerta | Resultado |
| --- | --- |
| `test_spec038_treasury.py` | 33 pruebas |
| Suites 036 + 037 + 038 | 80 pruebas |
| Mutaciones M5–M9 | cada una falla donde debe |
| Frontend (vitest) | 303 pruebas, 12 ficheros |
| Puertas de completitud | 235 (6 nuevas por las tres pantallas) |
| e2e tesorería (3 navegadores) | 30 |
| Cadena e2e de 8 suites | 183 |
| Regresión completa del backend | **1344 · 1336 pasan · 8 saltos · 0 fallos · 0 errores** |
| Saltos esperados / reales | **8 / 8**, todos S3 en `test_documents_storage.py` |

La regresión corre con `addopts = "-q"` más `-q` en la línea de órdenes, es
decir `-qq`, que suprime la línea final de resumen. La evidencia es el código de
salida —`0`, que pytest solo devuelve sin fallos ni errores— y la franja de
progreso completa: 1344 caracteres, 1336 puntos y 8 eses, ninguna `F` ni `E`.
Dos pasadas independientes dan el mismo recuento.

### 9.1 · Las mutaciones

| # | Mutación | Efecto |
| --- | --- | --- |
| M5 | el crédito reservado vuelve a ser imputable | 1 fallo |
| M6 | la tasa vuelve a inventarse como `1.0` | 1 fallo |
| M7 | ejecutar no consume la reserva | 2 fallos |
| M8 | no se comprueba el saldo de la cuenta | 2 fallos |
| M9 | la política se mira antes que el dueño del crédito | 3 fallos |

## 10. Defectos encontrados en las propias pruebas

Tres, y los tres se corrigieron antes de dar nada por bueno:

1. **Moneda no única.** `marca().slice(0, 2)` parecía aleatorio y no lo era:
   `Date.now()` en base 36 no cambia sus primeros caracteres en años, así que
   todas las pruebas compartían código de moneda. Se toma de la cola aleatoria,
   y la posición de caja se mide como **diferencia**, no como absoluto, porque
   la base de e2e es compartida.
2. **Mundo contaminado.** Una prueba creaba una segunda empresa para comprobar
   el aislamiento; con dos empresas el shell pasa a pedir «Seleccione una
   empresa» al entrar, y eso cambiaba el arranque de **todas** las demás suites.
   Se retiró de e2e —el aislamiento se comprueba en el backend, con dos empresas
   reales— y se borró la fila que había quedado.
3. **Fila ajena.** La tabla lista los reembolsos de toda la empresa; quedarse
   con la primera «Solicitado» operaba sobre el reembolso de otra prueba que
   corría a la vez. La fila se identifica por su propia nota.
4. **Dos requisitos sin prueba.** Al levantar la matriz de trazabilidad
   aparecieron dos filas que apuntaban a pruebas inexistentes: ejecutar un
   reembolso sin fondos, y el orden entre la comprobación de dueño y la de
   política. En vez de retirar los requisitos se escribieron las pruebas, y
   cada una se verificó con su mutación (**M8**, **M9**).

## 11. Lo que queda abierto

- `D0-07` sigue **abierto**. Este ciclo no afirma homologación fiscal ni
  liberación legal.
- El **IGTF** no se tocó: su dueña es la Spec 041.
- `BankTransactionCreate.amount` sigue declarado como `float` en el borde de la
  API de la Spec 019. No es un defecto vivo —la columna es `Numeric` y el valor
  se convierte al escribir—, pero es de la misma familia que `KQA-100` y queda
  **anotado para su dueña**, no corregido aquí por estar fuera del alcance.
- El **arqueo de caja** (§4.4) sigue restando en coma flotante. Mismo caso:
  defecto real, dueña distinta, delta que corresponde a su ciclo.
