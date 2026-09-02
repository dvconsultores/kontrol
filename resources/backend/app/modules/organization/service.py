"""Servicios del módulo de organización (001).

Incluye helpers de alcance compartidos por los módulos de negocio.
"""

from __future__ import annotations

from app.modules.organization.models import Warehouse

# Aquí vivían `company_in_tenant`, `branch_in_tenant` y `warehouse_in_tenant`.
#
# Los tres respondían a la misma pregunta —«¿es de una empresa de este
# tenant?»— y se usaban donde la pregunta correcta era «¿es de **esta**
# empresa?». N8 retiró `warehouse_in_tenant_scope` del producto por ese motivo;
# N10 encontró el último llamante, en la creación de establecimientos, y con él
# los tres se quedaron sin uso.
#
# No se conservan «por si acaso». Un ayudante que solo sirve para el patrón que
# esta remediación retiró es una invitación a reutilizarlo: la comprobación por
# empresa se hace contra `ctx.company_id`, que es la autoridad de la petición.


def warehouse_belongs_to(company_id: str, warehouse: Warehouse) -> bool:
    """¿Es este almacén de esta empresa?

    Sustituye a `warehouse_in_tenant_scope`, que reconciliaba el identificador
    del tenant con el de la empresa porque los módulos de negocio usaban el
    primero como alcance. Su docstring lo describía como diseño vigente y su
    segunda rama buscaba las empresas del tenant.

    Desde N2 los cuatro llamantes pasan la empresa real, así que aquella
    reconciliación era código muerto que funcionaba por accidente: si algún día
    un identificador de empresa hubiera coincidido con uno de tenant, habría
    aceptado el almacén equivocado. El nombre, además, invitaba a reintroducir
    la confusión que ARCH-MC-001 vino a corregir.

    Lo que hace falta comprobar es una sola cosa, y es esta.
    """
    return warehouse.company_id == company_id
