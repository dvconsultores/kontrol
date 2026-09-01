"""Empresas reales para las suites de dominio (ARCH-MC-001, fase N7).

Ocho suites usaban `COMPANY = "tenant-1"`: una cadena inventada que no es ni
una empresa ni un tenant. Pasaban porque `company_id` era texto suelto que la
base no contrastaba con nada — es decir, pasaban **por el mismo defecto** que
ARCH-MC-001 existe para corregir.

Con las claves foráneas de N7 esa cadena deja de ser aceptable, y eso es lo
correcto: una prueba que guarda datos bajo una empresa que no existe no está
comprobando el comportamiento multiempresa, está esquivándolo.

Esto no relaja nada. Al contrario: a partir de ahora las suites de dominio
operan sobre dos empresas que existen de verdad, con su tenant y su instalación,
y `OTRA` es una empresa real distinta en vez de otra cadena inventada.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

#: Identificadores fijos. Son constantes de módulo en las suites y se usan como
#: valores por defecto de sus ayudantes, que Python fija al **definir** la
#: función: si se generaran al sembrar, esos valores por defecto seguirían
#: apuntando a la cadena vacía.
EMPRESA_UNO = "company-uno"
EMPRESA_DOS = "company-dos"


def sembrar_empresas(db: Session) -> tuple[str, str]:
    """Crea instalación, tenant y dos empresas con identificadores conocidos.

    Idempotente: si ya existen, los reutiliza.
    """
    from app.modules.organization.models import Company, Installation, Tenant

    inst = db.query(Installation).first()
    if inst is None:
        import uuid

        inst = Installation(installation_uuid=str(uuid.uuid4()))
        db.add(inst)
        db.flush()

    tenant = db.query(Tenant).filter(Tenant.code == "T-DOM").one_or_none()
    if tenant is None:
        tenant = Tenant(installation_id=str(inst.id), code="T-DOM", name="Tenant de dominio",
                        plan="MULTI_COMPANY", status="ACTIVE")
        db.add(tenant)
        db.flush()

    for ident, code, nombre, rif in (
            (EMPRESA_UNO, "DOM-A", "Empresa Uno CA", "J-11111111-1"),
            (EMPRESA_DOS, "DOM-B", "Empresa Dos CA", "J-22222222-2")):
        if db.get(Company, ident) is None:
            db.add(Company(id=ident, tenant_id=str(tenant.id), code=code, legal_name=nombre,
                           rif=rif, legal_type="JURIDICA", functional_currency="VED",
                           status="ACTIVE"))
            db.flush()

    return EMPRESA_UNO, EMPRESA_DOS
