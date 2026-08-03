# API Contracts — 002-MAESTROS

| Campo | Valor |
|---|---|
| Fuente | DOC-03 §14 (convenciones) |
| Ruta | `specs/002-maestros/contracts/api-contracts.md` |

## Terceros (`/api/v1/maestros`)

| Método | Ruta | Uso |
|---|---|---|
| GET/POST | `/terceros` | Listar (q, status, page, page_size) / crear `Party` |
| GET/PATCH | `/terceros/{id}` | Consultar / editar |
| POST | `/terceros/{id}/activate` | Activar |
| POST | `/terceros/{id}/deactivate` | Desactivar |
| GET | `/terceros/{id}/audit` | Timeline de auditoría |
| POST | `/terceros/{id}/addresses` | Direcciones |
| POST | `/terceros/{id}/contacts` | Contactos |
| POST | `/terceros/{id}/bank-accounts` | Cuentas bancarias |
| POST | `/terceros/{id}/roles/{role}/approve` | Aprobar proveedor (bancaria/fiscal) |

## Catálogo

| Método | Ruta | Uso |
|---|---|---|
| GET/POST | `/catalogos/taxonomia` | Nodos de taxonomía |
| GET/POST | `/catalogos/atributos` | AttributeDefinition |
| POST | `/catalogos/atributos/{id}/aplicabilidad` | AttributeApplicability |
| GET/POST | `/catalogos/items` | CatalogItem (producto/servicio) |
| GET | `/catalogos/items/{id}` | Detalle (incluye perfiles y presentaciones) |
| POST | `/catalogos/items/{id}/presentaciones` | Presentaciones |
| POST | `/catalogos/items/{id}/codigos-barras` | Barcodes |
| GET | `/catalogos/items/search?q=` | Búsqueda asíncrona backend |
| GET/POST | `/catalogos/unidades` | UnitOfMeasure |
| POST | `/catalogos/unidades/{id}/conversiones` | UnitConversion |

## Perfiles

| Método | Ruta | Uso |
|---|---|---|
| GET/POST | `/perfiles` | ProfileVersion (inventario/trazabilidad/fiscal/regulatorio) |
| GET/PATCH | `/perfiles/{id}` | Consultar / editar versión |
| POST | `/perfiles/{id}/approve` | Aprobar versión |

## Ejemplo de respuesta con allowed_actions

```json
{
  "allowed_actions": {
    "view": true,
    "edit": true,
    "activate": false,
    "deactivate": true,
    "delete": false,
    "approve": true,
    "audit": true
  }
}
```

## Búsqueda asíncrona

`GET /api/v1/maestros/catalogos/items/search?q=arroz&status=ACTIVE&page=1&page_size=20`

```json
{
  "items": [{"id": "...", "code": "P-001", "name": "Arroz", "type": "PRODUCT"}],
  "total": 123,
  "page": 1,
  "page_size": 20
}
```
