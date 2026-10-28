# Inventario temporal del frontend · medido en `4c94906` (2026-10-28)

Barrido de `resources/frontend/src` (sin `*.test.ts(x)`) y de `e2e/`. Patrones buscados:
- `new Date(`, `Date.now(`, `Date.parse(`, `toISOString(`;
- `slice(0, 10|16|19)`;
- `toLocaleDateString`, `toLocaleString`, `toLocaleTimeString`, `Intl.DateTimeFormat`;
- `get*()` y `set*()` de `Date`;
- inputs `type="date"`, `datetime-local` y `month`;
- `timeZone` y los formateadores de `format.ts` e `i18n`.

## Módulos de apoyo

| Módulo | API | `timeZone` | Uso |
|---|---|---|---|
| `src/lib/fecha-de-negocio.ts` | `ZONA_DE_NEGOCIO`, `hoyDeNegocio(instante = new Date()): "AAAA-MM-DD"` | sí | `ListasPrecioPage:96` (`valid_from`) y `MaestrosPage:123` (`rate_date`): correcto |
| `src/i18n/index.ts:35` `formatearFecha(iso)` | `new Date(iso).toLocaleString("es-VE")` | **no** | Notificaciones (alertas, tareas, centro) y Auditoría |
| `src/lib/format.ts` `formatDate` | `new Date(value)` + date-fns | **no** | Sin usos en producción; con «AAAA-MM-DD» desplazaría el día |
| `src/components/DateInput.tsx` | `<input type="date">` | — | Sin usos |

## DISPLAY de instantes en la zona del navegador (F1)

| Fichero:línea | Campo |
|---|---|
| `aprobaciones/politicas/PoliticasPage.tsx:91,93` | `valid_from`, `valid_to` (`toLocaleDateString`) |
| `aprobaciones/delegaciones/DelegacionesPage.tsx:109` | `valid_to` |
| `aprobaciones/bandeja/BandejaPage.tsx:128` | `due_at` |
| `homologacion/timeline/TimelinePage.tsx:41` | `created_at` |
| `homologacion/versiones/VersionesPage.tsx:119` | `released_at` |
| `licenciamiento/renovacion/RenovacionPage.tsx:70` | `created_at` |
| `licenciamiento/eventos/EventosPage.tsx:36` | `created_at` |
| `licenciamiento/entitlements/EntitlementsPage.tsx:75` | `taken_at` |
| `licenciamiento/configuracion/ConfiguracionCentralPage.tsx:129` | `last_sync.ran_at` |
| `inventario/movimientos/MovimientosPage.tsx:106` | `occurred_at` |
| `inventario/kardex/KardexPage.tsx:27` | `occurred_at` |
| `seguridad/mfa/MiMfaPage.tsx:165` | `activated_at` |
| `seguridad/sesiones/SesionesPage.tsx:67` | `expires_at` |
| `pages/MiLicenciaPage.tsx:88,90,96` | `period_start`, `period_end`, `read_only_start` (F6) |
| `notificaciones/alertas/AlertasPage.tsx:86,88` | `created_at`, `resolved_at` (`formatearFecha`) |
| `notificaciones/tareas/TareasPage.tsx:140` | `due_at` |
| `notificaciones/tareas/TareaDetallePage.tsx:149,226` | `due_at`, `occurred_at` |
| `notificaciones/centro/CentroNotificacionesPage.tsx:106` | `created_at` |
| `pages/AuditoriaPage.tsx:21` | `event_time` |

## Día UTC por `slice(0, 10)` sobre instantes (F2)

| Fichero:línea | Campo |
|---|---|
| `documentos/DocumentoDetallePage.tsx:271` | `version.created_at` |
| `maestros/presentaciones/PresentacionesPage.tsx:211,215` | `valid_from`, `valid_to` |
| `ventas/ordenes/OrdenesVentasPage.tsx:388` | `expires_at` de la reserva |
| `inventario/reservas/ReservasPage.tsx:124` | `expires_at` |
| `tesoreria/reembolsos/ReembolsosPage.tsx:328` | `requested_at` |
| `ventas/estado-de-cuenta/EstadoDeCuentaPage.tsx:329` | `date`, que mezcla tipos (B5) |
| `tesoreria/fuentes/FuentesPage.tsx:385` | `created_at` del lote |
| `compras/recepciones/RecepcionesPage.tsx:225` | `record_issued_at` |

Excepción legítima: `regulatorio/permisos/PermisosPage.tsx:74` corta un **hash** (TECHNICAL_STAMP).

## Hora UTC presentada como local o ISO crudo (F3)

| Patrón | Sitios |
|---|---|
| `slice(0,16\|19).replace("T"," ")` | `DespachoPage:342` (`dispatched_at`), `DevolucionesVentasPage:467` (`reentered_at`), `PreparacionPage:218` (`released_at`), `ConfirmacionPedidoPage:136,247` (`updated_at`, `checked_at`), `RecepcionesPage:212,326` (`arrival_at`, `inspected_at`), `FuentesPage:238` (`last_success_at`), `TasasPage:430,527` (`effective_at`) |
| ISO crudo de un instante | `ExportacionesPage:88` (`exported_at`), `IgftPage:89` (`evaluated_at`, que es Date: correcto como texto), `CajasPage:121` (`opened_at`, Date: correcto como texto) |
| BUSINESS_DATE en crudo «AAAA-MM-DD» (aceptable, sin conversión) | `due_date`, `validity_until`, `need_date`, `value_date`, `txn_date`, `statement_date`, `expiry_date`, `effective_from`, `rate_date`, `issued_at`/`expiration_date` de documentos |

## Entradas

| Pantalla | Campo | Tipo | Por defecto | Envío | Estado |
|---|---|---|---|---|---|
| Delegaciones | `valid_to` (DateTime en el backend) | date | «» | `new Date(D).toISOString()` = 00:00 UTC | **F4 defecto** |
| Tasas | `effective_at` | datetime-local | `ahoraLocal()` del navegador | `new Date(v).toISOString()` en la zona del navegador | **F5 defecto** |
| Recepciones | `unloading_scheduled_at` | datetime-local | «» | ídem | **F5 defecto** |
| Biblioteca | `expiring_before`, `expiration_date` | date | «» | tal cual | correcto |
| Cotizaciones de compra | `validity_until` | date | «» | tal cual | correcto |
| CxP | `due_date` | date | «» | tal cual | correcto |
| Recepciones, línea | `expiry_date` | date | «» | tal cual | correcto |
| Fuentes | `effective_from` | date | «» | tal cual | correcto |
| Cambio | `effective_from` | date | «» | tal cual | correcto |
| Regulatorio | `deadline` | date | «» | tal cual | correcto |
| Lotes | `expiry_date` | date | «» | tal cual | correcto |
| Centro / Libros / Lotes de declaración | `period`, `period_key` | text | «» → «0» | tal cual | F8 |

No hay ningún `type="month"`.

## E2E

- **Ningún proyecto ni spec fija `timezoneId`**: el navegador hereda la zona del anfitrión (en la estación, `Europe/Amsterdam`).
- `helpers/ventas.ts:63 hoy()` usa Caracas.
- `auditoria-fecha.spec.ts:63,70` espera la zona del navegador (`toLocaleString` evaluado en la página): consagra la convención sin zona → T16.
- Las specs de licencia calculan el año contractual con `getUTC*`; su comentario reconoce el cruce de Caracas. Se revisa en la regresión.
- `uom-conversion.spec.ts:168,174` usa `new Date("2026-06-01").toISOString()` (medianoche UTC).

**Totales:** 61 apariciones en producción · 14 entradas de fecha o período · 0 `timezoneId`.
