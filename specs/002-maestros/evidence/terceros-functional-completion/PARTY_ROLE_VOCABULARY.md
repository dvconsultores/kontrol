# Vocabulario de roles

`PARTY_ROLES = CLIENTE, PROVEEDOR, VENDEDOR, TRANSPORTISTA, CONDUCTOR, BENEFICIARIO` (Spec 002 §1: cliente, proveedor, vendedor, transportista, conductor, beneficiario).

Autoridad única: `party_service.normalize_roles`: mayúsculas, sin duplicados, orden estable. Fuera de vocabulario: 422 `PARTY_ROLE_INVALID`. Lista vacía: 422 `PARTY_ROLE_REQUIRED_ONE`.

## Duplicidad por RIF y empresa (CL-002-04, SU-002-03, EDGE-002-01)

| Existente | Nuevo | Resultado |
|---|---|---|
| CLIENTE | CLIENTE | 409 `PARTY_DUPLICATE_TAX_ID` |
| PROVEEDOR | PROVEEDOR | 409 `PARTY_DUPLICATE_TAX_ID` |
| CLIENTE | [PROVEEDOR, CLIENTE] | 409 `PARTY_DUPLICATE_TAX_ID` |
| CLIENTE+PROVEEDOR | PROVEEDOR | 409 `PARTY_DUPLICATE_TAX_ID` |
| CLIENTE | PROVEEDOR | 409 `PARTY_TAX_ID_EXISTS` con `details` {party_id, code, name, roles}: la UI lleva al tercero existente para **añadir el rol**; no crea otro Party |
| RIF en otra empresa | cualquiera | Permitido |

Se comparan **todos** los terceros con ese RIF, no solo el primero, porque pueden existir duplicados históricos. Editar el RIF hacia uno existente: 409 `PARTY_TAX_ID_EXISTS`. La creación serializa por empresa con bloqueo de fila; el índice único parcial que pide SU-002-03 **no se crea** hasta escanear los datos reales con PostgreSQL (`TERCEROS-RIF-INDICE-UNICO`, puerta externa).

## Extensiones

Añadir CLIENTE crea `Customer`; PROVEEDOR, `Supplier` con PENDING_APPROVAL; TRANSPORTISTA, `Carrier`; CONDUCTOR, `Driver`. Es idempotente y reutiliza la fila si ya existe: quitar y volver a añadir un rol **no reinicia** la aprobación ni pierde datos. Si un tercero histórico tiene el rol sin fila, la extensión se crea al consultarla.

## Quitar rol

`DELETE /terceros/{id}/roles/{role}`: 409 `PARTY_ROLE_IN_USE` con documentos activos de ese rol; 409 `PARTY_LAST_ROLE` si es el único rol. La fila de extensión se conserva.
