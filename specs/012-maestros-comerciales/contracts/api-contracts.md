# CONTRATOS DE API — SPEC 012

Prefijo: `/api/v1/comercial`.

## 0. Contrato de empresa — antes que cualquier ruta

Toda operación de este prefijo es de empresa. Sin excepciones: no hay maestro
comercial de tenant, de instalación ni global.

Por tanto **todas** declaran `X-Kontrol-Company` en OpenAPI, con el contrato
vigente de ARCH-MC-001:

| Situación | Comportamiento |
|---|---|
| El usuario alcanza una sola empresa | Se resuelve automáticamente |
| Alcanza varias y no envía la cabecera | Error contractual vigente |
| Envía una empresa que no alcanza | `404`, sin distinguir de inexistente |
| Envía una empresa de otro tenant | `404` |

La cabecera la declara la dependencia `get_company_context`, de modo que la ruta
que la exige es exactamente la que la publica. No hay una segunda lista que
mantener sincronizada.

**Ninguna ruta acepta la empresa en el cuerpo.** Si el cuerpo la trae, o se
ignora o se contrasta con el contexto y se rechaza si difiere; nunca se obedece.

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

### Las cinco rutas hijas, y lo que cada una debe comprobar

Estas cinco tienen la forma exacta del defecto que N10 encontró nueve veces:
identificador del padre en la URL, y un servicio que lo usa tal cual.

Cada una resuelve **primero** el padre acotado por `CompanyContext`, y con tres
niveles hay que comprobar los tres eslabones, no solo el primero:

| Ruta | Qué resolver, en orden |
|---|---|
| `POST /listas-precio/{id}/versiones` | lista `{id}` bajo el contexto |
| `POST /listas-precio/{id}/versiones/{vid}/activar` | lista `{id}`; versión `{vid}` **de esa lista** |
| `GET` `POST` `/listas-precio/{id}/versiones/{vid}/items` | lista `{id}`; versión `{vid}` de esa lista |
| `DELETE /listas-precio/{id}/versiones/{vid}` | lista `{id}`; versión `{vid}` de esa lista |

Una versión legítima que cuelga de una lista de otra empresa **no** es
alcanzable comprobando solo `{vid}`. El detalle está en
`nested-resource-security-contract.md`, casos N-01 a N-09.

## 3. Resolución — la razón de ser de la Spec

```
POST /comercial/precio/resolver
X-Kontrol-Company: <empresa activa>

{
  "customer_id": "...", "item_id": "...",
  "presentation_id": "...", "quantity": "10", "currency": "VED",
  "as_of": "2026-08-30"
}
```

> **`company_id` se retira del cuerpo.** Lo declaraba, y era exactamente la
> vulnerabilidad que la Spec 045 estrenó y que N5 cerró: operando en A se
> declaraba B en el cuerpo y el resultado salía de B. El cliente elegía en qué
> empresa opera.
>
> La empresa la pone el contexto. Y `customer_id`, `item_id` y
> `presentation_id` se resuelven **dentro** de esa empresa: un cliente de otra
> empresa no es un cliente para esta petición.

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
X-Kontrol-Company: <empresa activa>

{ "scope":"LINE", "item_id":"...", "percent":"25.00", "role":"VENDEDOR" }
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

---

## 6. Errores

| Código | Cuándo |
|---|---|
| `404` | El recurso no existe **o** es de otra empresa. No se distingue |
| `404` | El padre de una ruta hija no es alcanzable desde el contexto |
| `409` | Se intenta borrar una versión referenciada por un documento aprobado |
| `409` | Dos versiones `ACTIVE` de la misma lista solaparían vigencia |
| `422` | Empate de precedencia irresoluble: **error de configuración**, no azar |

El `404` de la primera y la segunda fila es deliberado. Un `403` sobre un
recurso ajeno confirma que existe, y con identificadores adivinables eso es un
inventario ajeno servido de a un bit por petición.

## 7. Permisos

| Permiso | Operaciones |
|---|---|
| `comercial:view` | Leer cualquier maestro comercial |
| `comercial:create` | Crear maestros y versiones en borrador |
| `comercial:edit` | Modificar maestros y borradores |
| `comercial:manage_policies` | Políticas de descuento y de crédito |
| `comercial:publish` | Activar una versión: es irreversible |
| `comercial:archive` | Archivar; **nunca** borrar lo referenciado |

Tener el permiso **no** es tener acceso a la empresa (`FR-012-MC-036`).
`comercial:create` dice que el usuario puede crear maestros comerciales; no dice
en cuál empresa. Quien lo decide es `accessible_company_ids`, y `UserRole` no
amplía ese alcance (`FR-012-MC-037`).
