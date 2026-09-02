# SPEC 012 — MATRIZ DE DEPENDENCIAS

Cada dependencia con lo que la 012 necesita de ella, su estado hoy y si bloquea.
Ninguna se declara por costumbre.

| Spec | Capacidad requerida | Estado | ¿Bloquea? | Contrato |
|---|---|---|---|---|
| **ARCH-MC-001** | `CompanyContext`, alcance canónico, seguridad de rutas hijas | `COMPLETE / GLOBALLY CONVERGED` | **No** | Autoridad única de empresa. La 012 la consume; no la redefine |
| **009** Terceros | `parties`, `customers` con empresa real | Vigente, COMPANY | **No** | `customer_commercial_terms` extiende por FK; no duplica |
| **010** Productos | `catalog_items`, `taxonomy_nodes` | Vigente, COMPANY | **No** | `price_list_items` referencia artículo **o** categoría |
| **011** Unidades | `units_of_measure`, `presentations`, conversión física | Vigente | **No** | La 012 usa presentación comercial; **no** redefine el factor físico |
| **045** Aprobaciones | Solicitud cuando se supera el límite de descuento | `COMPLETE` | **No** | `FR-012-023`. La 012 **no** crea un segundo motor |
| **Núcleo fiscal** (039–043) | Perfil de impuesto del artículo | Vigente, separado por instalación | **No** | La 012 fija precio; **no** calcula impuesto |
| **029 / 034 / 037** consumidoras | `resolve_price`, validación de descuento, condición y crédito | No empezadas | **No** — al revés: la 012 las habilita | `FR-012-070..072` |
| **046** Documentos | — | `RECONVERGED` | **No** | **Ninguna dependencia.** No se declara |
| **047** Notificaciones | — | — | **No** | `FR-012-073`: la 012 **no** emite eventos ni notifica |

## Dos dependencias que la Spec 012 no tiene

Se dicen en voz alta porque la costumbre es añadirlas.

**046 — Gestión documental.** Una lista de precios no lleva adjuntos en el
alcance de esta Spec. Si algún día se quisiera adjuntar el archivo del que se
cargó la lista, `FR-012-008` ya guarda su procedencia como texto, y el vínculo
documental sería una capacidad nueva, no una dependencia de hoy.

**047 — Notificaciones.** `FR-012-073` es explícito: la 012 no emite eventos.
Quien notifica que un descuento superó el límite es la Spec 045 al abrir la
solicitud, no la 012 al detectarlo.

## Dos maestros que la Spec 012 sí posee

Verificado por medición, no por reparto:

**`PaymentTerm`.** Ninguna otra Spec lo declara. `013` es un análisis de
brechas, no un maestro financiero, y no reclama la condición de pago. La 012 lo
posee.

**`SalesCommissionPolicy`.** Queda **reservada** en el modelo y sin implementar
(`FR-012-090`). La 012 no calcula comisión ni toca nómina (`FR-012-091`).
Reservar la tabla evita que añadirla luego obligue a rediseñar; implementarla
sería una capacidad nueva de otro ciclo.

## Lo que la Spec 012 no debe duplicar

| No crear | Porque ya existe |
|---|---|
| `CommercialCompanyContext` | `get_company_context` es la autoridad canónica |
| `CommercialApproval` | Spec 045 |
| Un segundo motor de unidades | Spec 011 |
| Un segundo maestro de monedas | `currencies`, de empresa |
| Un segundo redondeo monetario | La autoridad financiera vigente |
| Una segunda tabla de zona | `warehouse_zones` es física; `commercial_zones` es territorio de ventas. Comparten el nombre y nada más (`FR-012-041`) |
