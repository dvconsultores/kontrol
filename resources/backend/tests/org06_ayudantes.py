from sqlalchemy import select

from app.modules.identity_access.models import User
from tests.org04_ayudantes import (
    D,
    O,  # noqa: F401
    accion,  # noqa: F401
    activa,  # noqa: F401
    acto_eficaz,  # noqa: F401
    crear_funcionario,  # noqa: F401
    cuerpo,  # noqa: F401
    nuevo_cargo,  # noqa: F401
    titular_activo,  # noqa: F401
)
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos, _post

I = "/gobierno/identidad"  # noqa: E741
MOTIVO = "Vinculación de la cuenta institucional."


def cuenta(mundo, nombre, empresa=None) -> str:
    _crear_usuario_con_permisos(mundo, nombre, [], empresa or mundo.company_a)
    with mundo.factory() as session:
        user = session.execute(select(User).where(User.username == nombre)).scalar_one()
        return user.id


def cuerpo_vinculo(user_id, official_id, desde=None, hasta=None, **cambios) -> dict:
    datos = {
        "user_id": user_id,
        "official_id": official_id,
        "desde": desde or D(1, 10).isoformat(),
        "hasta": hasta,
        "motivo": MOTIVO,
    }
    datos.update(cambios)
    return datos


def post_vinculo(mundo, datos, usuario="ua", empresa=None):
    return _post(mundo, f"{I}/vinculos", usuario, empresa or mundo.company_a, datos)


def crear_vinculo(mundo, datos, usuario="ua", empresa=None) -> dict:
    response = post_vinculo(mundo, datos, usuario, empresa)
    assert response.status_code == 201, response.text
    return response.json()


def accion_vinculo(mundo, vinculo, verbo, cuerpo_accion=None, usuario="uab", empresa=None, version=None):
    return _post(
        mundo,
        f"{I}/vinculos/{vinculo['id']}/{verbo}",
        usuario,
        empresa or mundo.company_a,
        cuerpo_accion or {},
        version or vinculo["version"],
    )


def vinculo_activo(mundo, datos) -> dict:
    creado = crear_vinculo(mundo, datos)
    response = accion_vinculo(mundo, creado, "activar")
    assert response.status_code == 200, response.text
    return response.json()


def consultar(mundo, ruta, usuario="ua", empresa=None, params=None):
    return mundo.client.get(
        f"/api/v1{I}{ruta}",
        headers=mundo.como(usuario, empresa or mundo.company_a),
        params=params or {},
    )
