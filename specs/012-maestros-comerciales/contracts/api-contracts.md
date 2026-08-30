# CONTRATOS DE API — SPEC 012

Prefijo: `/api/v1/comercial`.

## 1. Maestros

| Método | Ruta | Permiso |
|---|---|---|
| `GET` `POST` | `/condiciones-pago` | `comercial:view` / `comercial:create` |
| `PATCH` | `/condiciones-pago/{id}` | `comercial:edit` |
| `GET` `POST` | `/zonas` | ídem |
| `GET` `POST` | `/canales` | ídem |
| `GET` `POST` | `/politicas-descuento` | `comercial:manage_policies` |
| `GET` `POST` | `/politicas-credito` | ídem |

## 2. Listas de precios

| Método | Ruta | Nota |
|---|---|---|
| `GET` `POST` | `/listas-precio` | — |
| `GET` | `/listas-precio/{id}` | con sus versiones |
| `POST` | `/listas-precio/{id}/versiones` | correlativo **del servidor** |
| `POST` | `/listas-precio/{id}/versiones/{vid}/activar` | valida solapamiento |
| `GET` `POST` | `/listas-precio/{id}/versiones/{vid}/items` | items de una versión `DRAFT` |
| `DELETE` | `/listas-precio/{id}/versiones/{vid}` | **409** si está referenciada |

## 3. Resolución — la razón de ser de la Spec

```
POST /comercial/precio/resolver
{
  "company_id": "...", "customer_id": "...", "item_id": "...",
  "presentation_id": "...", "quantity": "10", "currency": "VED",
  "as_of": "2026-08-30"
}
```

Respuesta:

```json
{
  "resolved": true,
  "unit_price": "125.4000",
  "currency": "VED",
  "price_list_id": "...",
  "price_source_version_id": "...",
  "price_source_item_id": "...",
  "precedence_applied": "CUSTOMER_LIST",
  "precedence_order": ["CUSTOMER_CONTRACT", "CUSTOMER_LIST", "SEGMENT_LIST", "COMPANY_LIST"]
}
```

Sin lista aplicable (`FR-012-016`):

```json
{ "resolved": false, "reason": "NO_APPLICABLE_PRICE_LIST", "unit_price": null }
```

**Nunca** devuelve un precio inventado, ni cero, ni el último conocido.

Empate irresoluble (`FR-012-013`) → **422**:

```json
{ "code": "PRICE_PRECEDENCE_TIE",
  "message": "Dos reglas de la misma precedencia son aplicables y no se pueden desempatar",
  "details": { "candidates": ["...", "..."] } }
```

## 4. Validación de descuento

```
POST /comercial/descuento/validar
{ "company_id":"...", "scope":"LINE", "item_id":"...", "percent":"25.00", "role":"VENDEDOR" }
```

```json
{ "allowed": false, "max_percent": "15.00",
  "requires_approval": true, "policy_id": "...", "policy_version": 3 }
```

`requires_approval: true` **no bloquea**: el consumidor abre la solicitud con el
motor de la Spec 045. 012 **no** crea aprobaciones (`CL-012-09`).

## 5. Códigos de error

| Código | HTTP | Cuándo |
|---|---:|---|
| `PRICE_LIST_VERSION_OVERLAP` | 409 | Dos versiones solapan vigencia |
| `PRICE_LIST_VERSION_IN_USE` | 409 | Se intenta borrar una versión referenciada |
| `PRICE_PRECEDENCE_TIE` | 422 | Empate irresoluble |
| `NO_APPLICABLE_PRICE_LIST` | 200 con `resolved:false` | No hay lista — **no es un error** |
| `DISCOUNT_ABOVE_LIMIT` | 200 con `requires_approval` | Supera el máximo — **no es un error** |
| `PAYMENT_TERM_IN_USE` | 409 | Se intenta borrar una condición en uso |
| `COMMERCIAL_TERM_NOT_FOUND` | 404 | Incluye el caso de otra empresa |

> «Sin precio» y «descuento excesivo» **no son errores**: son respuestas. Un 500
> ahí obligaría al consumidor a tratar lo normal como excepción.

## 6. Lo que estos contratos no hacen

- No cotizan, no piden, no facturan.
- No emiten eventos (`FR-012-073`).
- No calculan comisiones.
- No exponen precedencia como código: la devuelven como **dato**, para que la
  interfaz pueda explicar de dónde salió el precio.
