# Delta 002 · TERCEROS-SELECTORES-E-INTEGRIDAD-DE-ROL

Spec dueña: 002 Maestros (FR-002-001, FR-002-004, FR-002-005, US-002-010). Consumidoras: 004, 005, 007 y 008. Árbol de partida `814afc1`.

**Estado: `PARTIAL`.** Selectores e integridad de rol y estado implementados y certificados en local, pero queda un hueco interno de producto: la pantalla de Terceros no permite crear terceros, asignar roles ni desactivar (ver «Hueco que impide cerrar»).

## Problemas demostrados

| Causa | Estado | Evidencia |
|---|---|---|
| RC-UI: la primera página como universo de terceros | PROVEN | 14 selectores en 11 pantallas; `tercerosSelectores.test.tsx`, 57 de 57 en rojo antes del cambio. Órdenes y facturas filtraban el rol en cliente **sobre esos 20** |
| RC-BACKEND-ROLE: el rol no se valida en la frontera | PROVEN | Sin error al usar un PROVEEDOR como cliente o un CLIENTE como proveedor |
| RC-BACKEND-STATUS: un inactivo se acepta en documentos nuevos | PROVEN | Sin error en cotización, orden, factura y anticipo |
| Aislamiento: `create_driver` y `create_vehicle` no validaban el tercero | PROVEN | Aceptaban un tercero de otra empresa |

## Decisión

Matriz en `evidence/terceros-selectores/PROCESS_CONTRACT.md`. Invariantes en `ROLE_STATUS_INVARIANTS.md`. Inventario en `DISCOVERY.md`.

- **Backend, autoridad única:** `master_data.service.require_eligible_party`. Inexistente u otra empresa: 404 `PARTY_NOT_FOUND`. Sin el rol: 409 `PARTY_ROLE_REQUIRED`. Inactivo cuando se exige activo: 409 `PARTY_INACTIVE`.
- **API:** `GET /maestros/terceros` gana `role` (opcional, `^[A-Za-z_]{1,32}$`, sin distinguir mayúsculas, compara contra el JSON de roles). Compatible: sin `role` nada cambia. 709 operaciones antes y después.
- **Frontend, autoridad única:** `SelectorDeTercero` sobre `AsyncCombobox`, que gana la prop compatible `extraParams` (forma parte de la clave).
- **Historia:** ninguna regla se aplica a documentos existentes. La etiqueta de un inactivo se resuelve por id.
- `EstadoDeCuentaPage` y `ReembolsosPage` cargan todas las páginas en bucle: no truncan (`LOAD_ALL_VALID`) y quedan como deuda de escala.

## Evidencia

| Gate | Resultado |
|---|---|
| SQLite completa con ClamAV | 4983 recogidas: 3123 pasadas, 0 fallos, 0 errores, 1860 saltadas (solo PostgreSQL) |
| Ruff · Mypy | Ruff limpio. Mypy 154 antes y 154 después |
| Vitest | 1712 de 1712 en 146 ficheros, dos corridas seguidas, sin errores no controlados |
| TSC · ESLint · build | RC 0 |
| Pruebas dirigidas | Backend: `test_terceros_elegibilidad` 48, `test_terceros_http` 7, `test_terceros_supervivientes` 6. Frontend: `tercerosSelectores` 57, `SelectorDeTercero` 24 |
| Mutaciones | Terceros: 28 de frontend y 31 de backend, todas muertas. Catálogo: 23 de 23 preservadas |
| PostgreSQL | No disponible. Las 1860 pruebas saltadas y las E2E se auditaron **solo por lectura**: declaran el rol correcto. Sin ejecutar |
| E2E `e2e/terceros-selectores.spec.ts` | Preparada; **sin ejecutar**. No cubre el cambio de empresa: no hay ayudante de UI para ello, y queda cubierto a nivel de componente (TS-15 a TS-17) |

## Hueco que impide cerrar

`TERCEROS-MANTENIMIENTO-SIN-UI` (preexistente, `3183ab5`). `TercerosPage` es un listado de solo lectura: ningún módulo del frontend hace `POST /maestros/terceros`, `.../roles/{role}` ni `.../deactivate`, y el enlace «Ver» apunta a `/maestros/terceros/{id}`, sin ruta en `router.tsx`. La Spec 002 pide «formularios de tercero» (§7) y US-002-001. La integridad nueva agrava el hueco: un tercero con el rol equivocado queda rechazado y no se puede corregir desde la interfaz.

Antes de publicar esta regla hace falta además, con PostgreSQL, el escaneo de los terceros existentes sin rol elegible: si hay datos así, dejarían de poder usarse en documentos nuevos.
