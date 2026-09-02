# MATRIZ DE DEPENDENCIAS POR CAPACIDAD

> Una Spec consumidora se desbloquea cuando existe la **capacidad** que
> necesita, no cuando la Spec proveedora alcanza `COMPLETE`. Confundir las dos
> cosas infla el grafo y bloquea trabajo que ya podría hacerse.
>
> Y al revés: que una capacidad esté satisfecha no vuelve `COMPLETE` a la
> consumidora. Son dos afirmaciones distintas y aquí van en columnas distintas.

| Consumidora | Capacidad requerida | Proveedora | Estado de la proveedora | Estado de la capacidad | Otros bloqueos | Veredicto |
|---|---|---|---|---|---|---|
| 018 Importaciones | Expediente documental | 046 | RECONVERGED | **satisfecha** | — | dependencias completas |
| 018 | Proveedor con empresa real | 009 | PARCIAL | **satisfecha** | — | ídem |
| 018 | Orden de compra | 017 | PARCIAL | **satisfecha** | — | ídem |
| 019 Recepción | Estructura de ubicaciones | 008 | COMPLETE | **satisfecha** | — | la usa a medias: no coloca |
| 019 | Unidad y presentación en línea | 011 | COMPLETE | **satisfecha** | — | — |
| 020 Incidencias | Recepción con rechazo | 019 | PARCIAL | **satisfecha** (`quantity_rejected`) | — | dependencias completas |
| 020 | Adjunto probatorio | 046 | RECONVERGED | **satisfecha** | — | ídem |
| 021 Confirmación | Compuerta de calidad | 019 | PARCIAL | **satisfecha** (`quality_status`) | 020 | falta la incidencia |
| 022 Put-away | Ubicaciones ordenadas | 008 | COMPLETE | **satisfecha** (`/locations/ordered`) | 021 | la estructura espera |
| 022 | Movimiento con ubicación | 023 | PARCIAL | **satisfecha** (`location_id` admitido) | 021 | nadie la escribe |
| 029 Cotización/pedido | Tercero de empresa | 009 | PARCIAL | **satisfecha** | — | — |
| 029 | Artículo de empresa | 010 | PARCIAL | **satisfecha** | — | — |
| 029 | Unidad y presentación | 011 | COMPLETE | **satisfecha** | — | — |
| 029 | **Resolución de precio con versión** | **012** | **COMPLETE** | **satisfecha** (`resolve_price`) | **ninguno** | **lista** |
| 029 | Disponibilidad de inventario | 023 | PARCIAL | **satisfecha** (`qty_available`) | — | — |
| 030 Crédito/reserva | Política de crédito | 012 | COMPLETE | **satisfecha** | **D0-03** | decisión de negocio |
| 030 | Motor de aprobaciones | 045 | COMPLETE | **satisfecha** | D0-03 | ídem |
| 031 Cola de picking | Orden físico determinista | 008 | COMPLETE | **satisfecha** | **022** | la línea no tiene ubicación |
| 032 Picking | Ubicación en la línea | 022 | NOT_STARTED | **no satisfecha** | — | bloqueada |
| 033 Confirmación de pedido | Picking consolidado | 032 | BLOQUEADA | **no satisfecha** | — | bloqueada |
| 034 Facturación | Compuerta de confirmación | 033 | NOT_STARTED | **no satisfecha** | 039–042 | doble bloqueo |
| 034 | Snapshot comercial | 012 | COMPLETE | **satisfecha** | 033 | contrato listo, sin consumidor |
| 035 Despacho | Guía y expediente | 046 | RECONVERGED | **satisfecha** | 034 | — |
| 035 | Registro regulatorio | 044 | EXTERNO | **parcial** | 034 | v1 registra, no emite |
| 036 Devoluciones | Maestros comerciales | 012 | COMPLETE | **satisfecha** | — | dependencias completas |
| 037 CxC | Facturación | 034 | PARCIAL | **parcial** | — | opera sobre lo que hay |
| 038 Tesorería | Comprobante documental | 046 | RECONVERGED | **satisfecha** | — | — |
| 038 | Tasa de cambio | 013 | PARCIAL | **satisfecha** (manual) | 048 para BCV | automática pendiente |
| 026 Costos | Costo de importación | 018 | NOT_STARTED | **no satisfecha** | — | sin *landed cost* |
| 028 CxP | Comprobante de pago | 046 | RECONVERGED | **satisfecha** (N9) | 040 | retenciones |
| 047 Notificaciones | Canal de salida | 048 | PARCIAL | **no satisfecha** | — | bloqueada |
| 013 Tasa BCV | Integración externa | 048 | PARCIAL | **no satisfecha** | — | tasa manual entretanto |

## Las tres capacidades que más trabajo desbloquean, y su estado

| Capacidad | Proveedora | Estado | Desbloquea |
|---|---|---|---|
| Resolución de precio con versión | 012 | **satisfecha** | 029, 030, 034, 036 |
| Ubicación escrita en el movimiento | 022 | **no satisfecha** | 031, 032 y la calidad de 023 |
| Canal de integración saliente | 048 | no satisfecha | 013 (BCV), 047 |
