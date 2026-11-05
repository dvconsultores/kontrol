# API: /api/v1/gobierno/tesoreria

Guardas: permiso → empresa → módulo `gobierno`. Campos extra rechazados. Escrituras con If-Match sobre `version` del programa o del rubro y bloqueo de fila. Las respuestas de escritura de programa devuelven el detalle.

| # | Método y ruta | Permiso | Estado | Respuesta |
|---|---|---|---|---|
| 1 | GET `/rubros` (`estado?`, `tipo?`) | gobierno_caja:view | — | `{items}` |
| 2 | POST `/rubros` | manage | — | 201 rubro |
| 3 | PATCH `/rubros/{id}` | manage | — | rubro |
| 4 | GET `/programas` (`ejercicio?`, `moneda?`, `estado?`) | view | — | `{items, resumen}` |
| 5 | POST `/programas` | manage | — | 201 detalle |
| 6 | GET `/programas/{id}` (`version?`) | view | — | detalle |
| 7 | GET `/programas/{id}/opciones` | manage | — | `{cuentas, rubros}` |
| 8 | POST `/programas/{id}/declaraciones` | manage | programa BORRADOR | 201 detalle |
| 9 | DELETE `/programas/{id}/declaraciones/{did}` | manage | programa BORRADOR | detalle |
| 10 | POST `/programas/{id}/lineas` | manage | versión BORRADOR | 201 detalle |
| 11 | PATCH `/programas/{id}/lineas/{lid}` | manage | versión BORRADOR | detalle |
| 12 | DELETE `/programas/{id}/lineas/{lid}` | manage | versión BORRADOR | detalle |
| 13 | POST `/programas/{id}/activar` | activate | versión BORRADOR | detalle |
| 14 | POST `/programas/{id}/reprogramar` | manage | VIGENTE | 201 detalle |
| 15 | POST `/programas/{id}/descartar` | manage | versión BORRADOR | detalle |
| 16 | POST `/programas/{id}/cerrar` | activate | VIGENTE | detalle |

**Entradas** (todas prohíben campos extra): `RubroIn {codigo, nombre, tipo}`; `RubroCambios {nombre?, estado?}`; `ProgramaIn {ejercicio, moneda, mes_inicial}`; `DeclaracionIn {cuenta_id, monto, fecha_corte, fundamento}`; `LineaIn {rubro_id, mes, monto}`; `LineaCambios {monto}`; `MotivoIn {motivo}` (reprogramar y cerrar). Activar y descartar sin cuerpo.

**Listado:** `{items: [{id, codigo, ejercicio, moneda, mes_inicial, estado, version, version_vigente, disponibilidad_inicial}], resumen: {borradores, vigentes, cerrados}}`; `resumen` no se filtra.

**Rubro:** `id, codigo, nombre, tipo, estado, version`.

**Opciones:** `{cuentas: [{id, codigo, denominacion, banco_nombre}], rubros: [{id, codigo, nombre, tipo}]}`: cuentas VIGENTE de la moneda del programa y rubros ACTIVO.

**Código del programa:** `PF-<ejercicio>-<moneda>`, por ejemplo `PF-2026-VES`.

**Detalle:** `id, codigo, ejercicio, moneda, mes_inicial, estado, version, version_vista, version_vigente, borrador_numero, cerrado_por, cerrado_en, motivo_cierre, registrado_por, registrado_en, declaraciones[id, cuenta_id, cuenta_codigo, cuenta_denominacion, banco_nombre, monto, fecha_corte, fundamento, declarado_por, declarado_en], disponibilidad_inicial, lineas[id, rubro_id, rubro_codigo, rubro_nombre, tipo, mes, monto], meses[mes, inicial, ingresos, desembolsos, final, deficit], hay_deficit, versiones[numero, estado, motivo, activada_por, activada_en, registrado_por, registrado_en], historia[version_numero, tipo, detalle, registrado_por, registrado_en]`. Importes como cadena decimal.

**Errores:** 404 `GOV_CASH_PROGRAM_NOT_FOUND`, `GOV_CASH_ITEM_NOT_FOUND`, `GOV_CASH_LINE_NOT_FOUND`; 409 `GOV_CASH_PROGRAM_STALE`, `_INVALID_STATE`, `_DUPLICATE`, `_NOT_READY` (`details.faltan`: declaracion, linea), `_PAST_MONTH`, `_DRAFT_OPEN`, `_EXERCISE_ENDED`, `GOV_CASH_ITEM_DUPLICATE`, `GOV_CASH_LINE_DUPLICATE`, `GOV_CASH_DECLARATION_DUPLICATE`; 422 `GOV_CASH_PROGRAM_INVALID`; 428 `GOV_CASH_PROGRAM_IF_MATCH_REQUIRED`. Cuenta o rubro ajeno, de otra moneda o no utilizable: 422 con un solo mensaje.

**Auditoría** (`owner_spec` gov-tre-02, entidad `GovernmentCashProgram` salvo rubros, `GovernmentCashItem`): GOV_CASH_ITEM_CREATED, _UPDATED; GOV_CASH_PROGRAM_CREATED, _UPDATED, _ACTIVATED, _REVISED, _DISCARDED, _CLOSED. Ocho acciones, sin números de cuenta.

**SoD:** proceso TRE-02: TRE02_REGISTRAR (crea), TRE02_ACTIVAR, TRE02_REPROGRAMAR, TRE02_CERRAR. **CTL-04:** proceso TRE-02 con rastreo a `/gobierno/tesoreria/programacion/{id}`.
