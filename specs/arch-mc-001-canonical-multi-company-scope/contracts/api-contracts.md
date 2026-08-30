# CONTRATOS DE API — ARCH-MC-001

## 1. La cabecera

```
X-Kontrol-Company: <uuid de la empresa>
```

Obligatoria en las **276 operaciones** de alcance de empresa. Ignorada en las 49
de tenant o instalación. En las 79 mixtas —organización y unidades— la empresa ya
viaja explícita y **se valida** contra los accesos del usuario.

## 2. Resolución

| Situación | Resultado |
|---|---|
| Cabecera válida y accesible | `CompanyContext` resuelto |
| Sin cabecera, una sola empresa accesible | Resuelta automáticamente |
| Sin cabecera, varias accesibles | **400 `COMPANY_CONTEXT_REQUIRED`** |
| Empresa inexistente, de otro tenant o sin acceso | **404 `COMPANY_NOT_FOUND`** |
| Empresa desactivada | **409 `COMPANY_INACTIVE`** |
| Acceso perdido con la sesión viva | **404** en la siguiente operación |

> Empresa de otro tenant y empresa sin acceso responden **lo mismo**. Distinguirlas
> confirmaría su existencia.

## 3. Códigos

| Código | HTTP | Cuándo |
|---|---:|---|
| `COMPANY_CONTEXT_REQUIRED` | 400 | Varias empresas y ninguna indicada |
| `COMPANY_NOT_FOUND` | 404 | No existe, no es del tenant o sin acceso |
| `COMPANY_INACTIVE` | 409 | Desactivada |
| `COMPANY_MISMATCH` | 409 | El cuerpo trae una empresa distinta del contexto |
| `COMPANY_LIMIT_REACHED` | 409 | La licencia no permite otra |
| `CROSS_COMPANY_OPERATION` | 409 | Se intenta relacionar entidades de empresas distintas |

## 4. Escritura

El servidor establece la propiedad. Un `company_id` en el cuerpo distinto del
contexto da **409 `COMPANY_MISMATCH`**; no se acepta ni se ignora en silencio
(`FR-MC-023`, `FR-MC-024`).

Excepción: las rutas administrativas de organización, donde la empresa es el
objeto de la operación y llega explícita.

## 5. Operaciones entre empresas

Relacionar entidades de empresas distintas —aplicar un pago de A a una factura de
B, transferir stock entre almacenes de A y B— responde **409
`CROSS_COMPANY_OPERATION`**.

No es una limitación temporal: lo intercompany es una capacidad futura con reglas
contables propias. Permitirlo por omisión sería simularlo mezclando datos.

## 6. Trabajos sin petición

Un trabajo de fondo abre su contexto explícitamente:

```python
with company_context(tenant_id=…, company_id=…, actor=…):
    ...
```

Sin contexto, un servicio de alcance de empresa **falla**; no toma uno por defecto
(`FR-MC-019`).

## 7. Auditoría

Toda operación de empresa registra tenant, empresa, usuario, acción y entidad
(`FR-MC-040`). El campo de empresa lleva la empresa, no el tenant.

## 8. `ResourceKind` de la Spec 046

Tras normalizar, cada tipo declara su alcance y su resolutor:

```python
ResourceKind("Payment", "app.modules.purchasing.models", "Payment",
             scope=Scope.COMPANY, scope_resolver="company_id",
             permission="compras:view", consumers=("028",))
```

`scope_resolver` es explícito. **No se infiere del nombre de la columna**: fue esa
inferencia la que rompió el registro (`FR-MC-072`).
