# BLOQUEOS ACTIVOS

| Bloqueo | Tipo | Specs afectadas | Responsable | Qué hace falta |
|---|---|---|---|---|
| **D0-07** validación legal fiscal | Legal | 039, 040, 041, 042, 043, 056 | Negocio / asesoría fiscal | Confirmación normativa venezolana antes de emitir |
| **D0-06** hosting y licencia central | Negocio | 004, y parcialmente 052, 055 | Negocio | Decidir modelo de licenciamiento |
| **022 Put-away** ausente | Dependencia | 031, 032 | Ingeniería | Existencia ubicada: escribir `location_id` en el saldo y ofrecer cantidad por ubicación |
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

| **Reservado frente a ubicación** (`OQ-022-01`) | **Decisión de producto** | 022, 031, 032 | Negocio (ventas y almacén) | `lock_balance` filtra `location_id IS NULL` y `get_available` lee esa fila. Ubicar la mercancía la haría invendible y dejaría reservas sin respaldo físico. `POL-D0-002` §7 dice que la reserva no se dimensiona por ubicación, pero no dice dónde vive el contador cuando el stock se reparte (2026-09-04) |
| **Semántica de la capacidad de una ubicación** (`OQ-022-02`) | **Decisión de producto** | 022 | Negocio (almacén) | Existen `capacity_units`, `capacity_weight` y `capacity_uom`; no existe la regla que diga si superarla bloquea o solo advierte, ni contra cuál se compara (2026-09-04) |
| **Cómo se determina la ubicación destino** (`OQ-022-03`) | **Decisión de producto** | 022 | Negocio (almacén) | La clasificación del proceso exige familia, tamaño, peso, rotación y volumen: cinco atributos que el maestro no tiene, sobre zonas que el DOCX marca como preliminares. La ubicación manual sí es implementable hoy (2026-09-04) |
