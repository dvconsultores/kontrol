# BLOQUEOS ACTIVOS

| Bloqueo | Tipo | Specs afectadas | Responsable | Qué hace falta |
|---|---|---|---|---|
| **D0-07** validación legal fiscal | Legal | 039, 040, 041, 042, 043, 056 | Negocio / asesoría fiscal | Confirmación normativa venezolana antes de emitir |
| **D0-06** hosting y licencia central | Negocio | 004, y parcialmente 052, 055 | Negocio | Decidir modelo de licenciamiento |
| **022 Put-away** ausente | Dependencia | 031, 032 | Ingeniería | Existencia ubicada: escribir `location_id` en el saldo y ofrecer cantidad por ubicación |
| **Saldo solo escribible en `DISPONIBLE`** | Capacidad | 021, 022, 032 | Ingeniería (Spec 023) | Admitir el estado de mercancía como parámetro del movimiento y del saldo, con el catálogo de `ADR-D0-010`. *(La Spec 019 corrigió aparte que el saldo acumulaba la cantidad tecleada en vez de la base.)* |
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
