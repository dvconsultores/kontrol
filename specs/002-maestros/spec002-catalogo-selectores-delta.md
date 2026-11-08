# Delta 002 · CATALOGO-SELECTORES-PRIMERA-PAGINA

Spec dueña: 002 Maestros (FR-002-043, búsqueda asíncrona de catálogo). Ciclo `CATALOGO-SELECTORES-PRIMERA-PAGINA-01`,
árbol de partida `ea22171`. Solo cambia el frontend: `BACKEND_CHANGE_REQUIRED = 0` y la OpenAPI no se mueve.

## Problema

14 pantallas pedían `GET /maestros/catalogos/items?status=ACTIVE` sin paginar. El backend devuelve 20 artículos, así que
el artículo 21 en adelante no se podía elegir y nada avisaba del corte. Las pantallas afectadas:

- **Inventario (7):** transferencias, seriales, ajustes, conteos, lotes, reservas y movimientos.
- **Ventas (3):** facturas, cotizaciones y órdenes.
- **Compras (4):** cotizaciones, facturas de proveedor, devoluciones y órdenes.

La primitiva `AsyncCombobox` tenía tres defectos propios:
- mostraba el UUID tras elegir;
- cortaba en 20 coincidencias;
- no incluía la empresa en la clave de caché.

Reproducción: 43 de 43 en rojo antes del cambio (`evidence/catalogo-selectores/CATALOG_SELECTOR_DISCOVERY.md`).

## Decisión

Opción A. Se mejora `AsyncCombobox` de forma compatible y `SelectorDeArticulo` queda como única autoridad de frontend
para elegir artículos.

- **Búsqueda en servidor:** `GET /maestros/catalogos/items/search` con `q`, `page` y `page_size=20`.
- **Sin truncado silencioso:** «Cargar más resultados» mientras queden páginas, junto con «Mostrando N de M».
- **Errores separados:** un fallo de la primera página sustituye la lista; el fallo de una página posterior la conserva y
  avisa.
- **Etiqueta legible:** `code · name`, atada al id elegido. Un id inicial se resuelve con
  `GET /maestros/catalogos/items/{id}`.
- **Empresa:** forma parte de todas las claves de consulta, y cambiar de empresa vacía la selección.
- **Tipos de artículo por proceso** (`CATALOG_SELECTOR_PROCESS_CONTRACT.md`):
  - inventario usa `itemType="PRODUCT"`, en línea con `inventory._require_product`;
  - compras y ventas no filtran, porque admiten líneas de producto y de servicio (FR-005-034).
- **Accesibilidad:** cada opción es un `button role="option"` y `FormField` enlaza la etiqueta y la descripción.

Consumidores de `AsyncCombobox`: `SelectorDeArticulo` y el Rubro de `ProductoNuevoPage`. El endpoint de taxonomía
tiene la misma forma (`items` y `total`, con `page` y `page_size`), así que el Rubro gana la paginación sin cambiar.
**ProductoNuevoPage no tiene prueba propia:** su compatibilidad se verificó por contrato, no por ejecución.

## Fuera de alcance

- `ProductosPage` y `ServiciosPage` son listados con búsqueda, no selectores.
- `RecepcionesPage` solo resuelve un nombre por id; Recepciones queda intacta.
- Government no consume `AsyncCombobox`.
- Los selectores de terceros y almacenes quedan fuera de este delta.

## Evidencia

| Gate | Resultado |
|---|---|
| Vitest completo | 1618 de 1618 pruebas, 142 ficheros, RC 0, sin errores no controlados, **dos corridas seguidas** con el árbol final |
| `AsyncComboboxCanonico.test.tsx` | 18 de 18 (CC-01 a CC-20). CC-18 era inestable con la máquina cargada y se corrigió con una excepción de la dueña |
| `catalogoSelectores.test.tsx` | 43 de 43: 14 pantallas, artículo 25, PRODUCT en inventario, servicios en comerciales, guarda de fuente |
| `catalogoSupervivientes.test.tsx` | 5 de 5 (S-04, S-07, S-13, S-14, S-17) |
| TSC (`npm run typecheck`, incluye `e2e/`) · ESLint · build | RC 0 |
| Mutaciones | 19; mueren 18. **Superviviente aceptado: M4** (clave de caché sin empresa); S-04 no lo mata |
| E2E `e2e/catalogo-selectores.spec.ts` | Preparada (compra, venta y movimiento con más de 20 artículos); **sin ejecutar**: no hay PostgreSQL |
| Backend · OpenAPI · SQLite | Sin cambios. `NOT_REQUIRED_FOR_FRONTEND_ONLY_CHANGE` |

Registro de intentos: `evidence/catalogo-selectores/ATTEMPT_LOG.md`.

## Deuda que deja

- `CATALOGO-SELECTOR-CACHE-EMPRESA-SIN-PRUEBA` (LOW): la empresa sí está en la clave de caché, pero ninguna prueba lo
  demuestra (M4).
- `ASYNC-COMBOBOX-REABRIR-TRAS-ESCAPE` (LOW): tras Escape, un clic sobre el campo, que conserva el foco, no reabre la
  lista. Hay que escribir o salir del campo.
- `COMPRAS-DEVOLUCION-LINEA-SIN-VALIDAR-PRODUCTO` (MEDIUM propuesta, 004): `add_return_line` no valida el producto.
  Es un hallazgo lateral y no se absorbe en este delta.
- `CATALOGO-SELECTORES-E2E-PENDIENTE`: la E2E se ejecutará en la próxima certificación con PostgreSQL.
