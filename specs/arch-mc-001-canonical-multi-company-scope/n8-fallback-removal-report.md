# EL ÚLTIMO REPLIEGUE — N8

## 1. Qué era

```python
def warehouse_in_tenant_scope(db, tenant_id, warehouse) -> bool:
    """¿Pertenece el almacén a una empresa del tenant?

    Los módulos de negocio (ventas, compras, inventario) usan el `tenant_id`
    del usuario como alcance (`company_id`) […]

    En el modelo MONO_COMPANY el tenant tiene una sola empresa, por lo que
    este helper reconcilia ambos identificadores […]
    """
    if warehouse.company_id == tenant_id:
        return True
    companies = db.execute(select(Company.id).where(Company.tenant_id == tenant_id)).scalars().all()
    return warehouse.company_id in companies
```

Su docstring describe la confusión como **diseño vigente**. Lo era cuando se
escribió.

## 2. Por qué sobrevivió a N2, N5 y N7

Desde N2 sus cuatro llamantes —inventario, compras, ventas y tesorería— pasan la
empresa real. Con un `company_id` en el parámetro:

- la primera rama hace la comprobación correcta;
- la segunda busca las empresas de un «tenant» que en realidad es una empresa,
  no encuentra ninguna y devuelve falso.

Es decir: **funcionaba por accidente**. Las pruebas A/B de N5 lo confirmaron sin
poder verlo, porque su comportamiento observable ya era el correcto.

## 3. Qué habría pasado

Si algún identificador de empresa hubiera coincidido con uno de tenant, la
primera rama habría aceptado el almacén equivocado. Improbable con UUID, pero la
garantía era la aleatoriedad, no el diseño.

Y el nombre invitaba a reintroducir la confusión: quien buscara «cómo se
comprueba el alcance de un almacén» encontraba una función que le decía que el
tenant sirve de empresa.

## 4. Qué es ahora

```python
def warehouse_belongs_to(company_id: str, warehouse: Warehouse) -> bool:
    """¿Es este almacén de esta empresa?"""
    return warehouse.company_id == company_id
```

Sin sesión de base de datos, porque no hacía falta consultar nada. Cuatro
llamantes actualizados.

## 5. Comprobación

Una prueba de arquitectura recorre el código productivo buscando el nombre
retirado y los patrones `company_id = tenant_id`, `company_id or tenant_id`. El
módulo de migración queda excluido a propósito: ahí hablar del legado es su
trabajo.

**Repliegues activos: 0.**
