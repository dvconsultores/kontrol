"""Pruebas hostiles de aislamiento para recuento paginado y concurrencia de alcance.

Estas pruebas fijan comportamiento que ya es correcto y que no debe degradarse:

- La autoridad (empresa activa, alcance y capacidades) se evalúa en CADA
  petición contra la base de datos; no se congela en el token de sesión. Quitar
  un alcance o un rol con la sesión viva debe surtir efecto de inmediato.
- El recuento total de un listado paginado debe contar solo las filas del
  alcance del actor; las filas de otras empresas no deben filtrarse ni alterar
  el total ni el número de páginas.
"""

import math
import secrets

from hostil_mundo import MundoHostil
from sqlalchemy import select

from app.modules.identity_access.models import Role, UserRole, UserScope
from app.modules.master_data.models import Party

pytest_plugins = ("tests.hostil_mundo",)


def _unico(prefijo: str) -> str:
    return prefijo + secrets.token_hex(4).upper()


def _paginas(resp, total):
    """Devuelve el número de páginas derivado del total si la respuesta lo expone."""
    datos = resp.json()
    page_size = datos.get("page_size")
    if page_size:
        return math.ceil(total / page_size)
    return None


def test_iso_pag_01_el_total_no_cuenta_filas_ajenas(mundo_hostil: MundoHostil):
    """C07-T13 / pag-01: el total paginado no incluye filas de empresas ajenas."""
    a1 = mundo_hostil.empresas["A1"]
    a2 = mundo_hostil.empresas["A2"]
    b1 = mundo_hostil.empresas["B1"]

    primera = mundo_hostil.pedir(
        "a1_op",
        "GET",
        "/maestros/terceros",
        empresa=a1,
        params={"page_size": 1},
    )
    assert primera.status_code == 200
    t0 = primera.json()["total"]

    u = _unico("ISO")
    with mundo_hostil.factory() as db:
        for _ in range(3):
            db.add(Party(company_id=a2, code=u, name=u))
        for _ in range(3):
            db.add(Party(company_id=b1, code=u, name=u))
        db.commit()

    segunda = mundo_hostil.pedir(
        "a1_op",
        "GET",
        "/maestros/terceros",
        empresa=a1,
        params={"page_size": 1},
    )
    assert segunda.status_code == 200
    assert segunda.json()["total"] == t0

    paginas_antes = _paginas(primera, t0)
    paginas_despues = _paginas(segunda, t0)
    assert paginas_antes == paginas_despues

    with mundo_hostil.factory() as db:
        db.add(Party(company_id=a1, code=u, name=u))
        db.commit()

    tercera = mundo_hostil.pedir(
        "a1_op",
        "GET",
        "/maestros/terceros",
        empresa=a1,
        params={"page_size": 1},
    )
    assert tercera.status_code == 200
    assert tercera.json()["total"] == t0 + 1


def test_iso_con_01_quitar_el_alcance_con_la_sesion_viva_cierra_la_empresa(
    mundo_hostil: MundoHostil,
):
    """C07-T13 / con-01: quitar el alcance con la sesión viva cierra la empresa (AC-MC-16)."""
    a1 = mundo_hostil.empresas["A1"]
    a2 = mundo_hostil.empresas["A2"]
    usuario = mundo_hostil.actores["a12_op"].user_id

    previa = mundo_hostil.pedir("a12_op", "GET", "/maestros/terceros", empresa=a2)
    assert previa.status_code == 200

    with mundo_hostil.factory() as db:
        fila = db.execute(
            select(UserScope).where(
                UserScope.user_id == usuario,
                UserScope.company_id == a2,
            )
        ).scalar_one()
        db.delete(fila)
        db.commit()

    try:
        cerrada = mundo_hostil.pedir(
            "a12_op", "GET", "/maestros/terceros", empresa=a2
        )
        assert cerrada.status_code == 404
        assert cerrada.json().get("code") == "COMPANY_NOT_FOUND"

        abierta = mundo_hostil.pedir(
            "a12_op", "GET", "/maestros/terceros", empresa=a1
        )
        assert abierta.status_code == 200
    finally:
        with mundo_hostil.factory() as db:
            db.add(UserScope(user_id=usuario, company_id=a2))
            db.commit()


def test_iso_con_02_quitar_el_rol_con_la_sesion_viva_retira_la_capacidad(
    mundo_hostil: MundoHostil,
):
    """C07-T13 / con-02: quitar el rol con la sesión viva retira la capacidad."""
    a1 = mundo_hostil.empresas["A1"]
    usuario = mundo_hostil.actores["a1_consulta"].user_id

    previa = mundo_hostil.pedir(
        "a1_consulta", "GET", "/inventory/movement-types", empresa=a1
    )
    assert previa.status_code == 200

    with mundo_hostil.factory() as db:
        rol = db.execute(
            select(Role).where(Role.code == "R_ISO_CONSULTA_TA")
        ).scalar_one()
        fila = db.execute(
            select(UserRole).where(
                UserRole.user_id == usuario,
                UserRole.role_id == rol.id,
            )
        ).scalar_one()
        db.delete(fila)
        db.commit()

    try:
        denegada = mundo_hostil.pedir(
            "a1_consulta", "GET", "/inventory/movement-types", empresa=a1
        )
        assert denegada.status_code == 403
        assert denegada.json().get("code") in (
            "PERMISSION_DENIED",
            "COMPANY_SCOPE_FORBIDDEN",
        )
    finally:
        with mundo_hostil.factory() as db:
            rol = db.execute(
                select(Role).where(Role.code == "R_ISO_CONSULTA_TA")
            ).scalar_one()
            db.add(UserRole(user_id=usuario, role_id=rol.id))
            db.commit()
