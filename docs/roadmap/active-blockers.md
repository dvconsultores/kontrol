# BLOQUEOS ACTIVOS

| Bloqueo | Tipo | Specs afectadas | Responsable | Qué hace falta |
|---|---|---|---|---|
| **D0-07** validación legal fiscal | Legal | 039, 040, 041, 042, 043, 056 | Negocio / asesoría fiscal | Confirmación normativa venezolana antes de emitir |
| **D0-06** hosting y licencia central | Negocio | 004, y parcialmente 052, 055 | Negocio | Decidir modelo de licenciamiento |
| ~~**OQ-031-1**~~ | **RESUELTO 2026-09-05** | — | — | `D0-15`: la cola se ordena por `released_at ASC` con desempate `id ASC` (`R-D0-15-1..4`). La autoridad estaba en el propio código: `_a_released` documenta que ahí «el pedido entra en la cola de 031» |
| ~~**OQ-031-2**~~ | **RESUELTO 2026-09-05** | — | — | `D0-15`: asignación parcial solo en `DRAFT`, con remanente explícito; `CONFIRMED` exige el 100 % (`R-D0-15-5..9`) |
| ~~**OQ-031-3**~~ | **RESUELTO 2026-09-05** | — | — | `D0-15`: cinco estados; `CANCELLED` e `INVALIDATED` liberan las asignaciones operativas sin tocar la reserva comercial (`R-D0-15-10..19`) |
| ~~**022 Put-away** ausente~~ | **RESUELTO 2026-09-04** | — | — | La Spec 022 quedó `COMPLETE / CONVERGED / EVIDENCE SEALED`: existencia con ubicación física real y procedencia reconstruible desde el ledger |
| ~~**Grafo de transiciones de estado de mercancía**~~ (`OQ-D010-01`) | **RESUELTO 2026-09-03** | — | — | `ADR-D0-010` v2 declara nueve transiciones activas con evidencia y deny-by-default para el resto. `R-D0-10-7` pasa de vinculante-inimplementable a ejecutable |
| ~~**Reservado frente a reclasificación**~~ (`OQ-D010-02`) | **RESUELTO 2026-09-03** | — | — | Invariante `R-D0-10-9`; liberación automática y reasignación rechazadas por autoridad. Ninguna transición activa sale de `DISPONIBLE`, así que el conflicto no es alcanzable; `R-D0-10-10` fija quién y cuándo lo decidirá |
| ~~**El movimiento de inventario no lleva estado**~~ | **RESUELTO 2026-09-04** | — | — | `InventoryMovement` guarda `source_state` y `target_state` (migración `0046`) y `recompute_balances` reconstruye por estado y en cantidad base. La cadena de entrada queda **sin bloqueos**: 019, 020 y la capacidad multiestado de 023 cerradas; la 021 pasa a `READY_FOR_IMPLEMENTATION` |
| **033 Confirmación** ausente | Dependencia | 034, 035 | Ingeniería | Compuerta independiente antes de facturar |
| **018 Importaciones** ausente | Dependencia | 026 (*landed cost*) | Ingeniería | Expediente de importación |
| **048 Integraciones** parcial | Dependencia | 013 (tasa BCV), 047 | Ingeniería | Canal saliente |
| **044** sin API oficial | Externo | 044, y en parte 035 | Organismo emisor | Especificación oficial de SICA/SIGESAI/SACS |
| **S3 sin servicio real** | Externo P1 | **046 únicamente** | Infraestructura | Un servicio compatible en el entorno |
| Planificador de retención | P1 | 052 | Spec de instalación | Disparador periódico |
| Deuda responsive residual | P1 | 005, 054 | Ingeniería frontend | Reauditar rutas afectadas |

## Lo que estos bloqueos **no** bloquean

Se dice explícitamente porque la costumbre es propagarlos.

**S3 no bloquea nada fuera de 046.** Los ocho saltos son de
`test_documents_storage.py` y de ningún otro fichero. El almacenamiento en disco
está verificado, y toda Spec que necesite adjuntar un documento puede hacerlo
hoy.

**La validación legal fiscal no bloquea los módulos no fiscales.** Separa
«arquitectura fiscal construible» de «liberación legal»: 039–043 pueden
construirse; lo que no puede es emitirse sin confirmación normativa. Compras,
inventario, picking y despacho no dependen de esa confirmación.

**D0-06 no bloquea el desarrollo operativo.** Afecta al modelo de licenciamiento
y a la instalación, no a que una empresa registre una recepción.

**El vacío de 044 no bloquea 035 entero.** El contrato v1 registra, valida,
adjunta, bloquea y audita permisos oficiales; lo que no hace es emitirlos, y eso
es correcto sin API oficial.

| ~~OQ-022-01~~ | **RESUELTO 2026-09-04** | — | — | `D0-14`: reserva de almacén, no de ubicación (`R-D0-14-1..5`) |
| ~~OQ-022-02~~ | **RESUELTO 2026-09-04** | — | — | `D0-14`: capacidad informativa en V1 (`R-D0-14-6/7`) |
| ~~OQ-022-03~~ | **RESUELTO 2026-09-04** | — | — | `D0-14`: ubicación manual con filtro de backend (`R-D0-14-8/9/10`) |
| ~~**El disponible se leía de la fila de ubicación nula**~~ | **RESUELTO 2026-09-04** | — | — | La Spec 022 lo sustituyó por `warehouse_sellable_on_hand`, que suma lo vendible del almacén sobre todas las ubicaciones. Era el defecto que habría vuelto invendible la mercancía ubicada |
