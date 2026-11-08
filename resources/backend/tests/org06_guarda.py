import uuid

from sqlalchemy import select

from app.modules.identity_access.models import Role, User
from app.shared.clock import hoy_de_negocio
from tests.org06_ayudantes import I, consultar, cuerpo_vinculo, vinculo_activo
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos, _post
from tests.test_gov_doc02_actos import _doc_con_version


def cuenta_con_permisos(mundo, nombre, permisos) -> str:
    _crear_usuario_con_permisos(mundo, nombre, permisos, mundo.company_a)
    with mundo.factory() as session:
        return session.execute(select(User).where(User.username == nombre)).scalar_one().id


def rol_de(mundo, nombre):
    with mundo.factory() as session:
        return session.execute(select(Role).where(Role.code == f"R_{nombre.upper()}")).scalar_one().id


def exigir_identidad(mundo, exige=True) -> dict:
    version = consultar(mundo, "/politica").json()["version"]
    response = _post(
        mundo,
        f"{I}/politica",
        "ua",
        mundo.company_a,
        {"exige_identidad": exige, "motivo": "Cambio de la exigencia de identidad."},
        version,
    )
    assert response.status_code == 200, response.text
    return response.json()


def acto_borrador(mundo, cargo_id, accion="APROBAR", materia="PRESUPUESTO") -> dict:
    cuerpo = {
        "tipo": "RESOLUCION",
        "numero": f"ORG06-{uuid.uuid4().hex[:10]}",
        "fecha": hoy_de_negocio().isoformat(),
        "lugar": "Naguanagua",
        "cargo_id": cargo_id,
        "competencia": {"accion": accion, "materia": materia},
        "fundamento_competencia": "Reglamento interno, art. 12",
        "funcionario": "Persona de prueba",
        "titularidad": "TITULAR",
        "caracter": "INTERNO",
        "destinatario": None,
        "asunto": "Asunto de prueba",
        "hechos": "Hechos de prueba",
        "fundamentos": "Fundamentos de prueba",
        "decision": "Decisión de prueba",
    }
    response = _post(mundo, "/gobierno/actos", "ua", mundo.company_a, cuerpo)
    assert response.status_code == 201, response.text
    return response.json()


def emitir(mundo, acto, usuario):
    doc = _doc_con_version(mundo, mundo.company_a, resource_id=acto["id"])
    return _post(
        mundo,
        f"/gobierno/actos/{acto['id']}/emitir",
        usuario,
        mundo.company_a,
        {"documento_acto_id": doc},
        acto["version"],
    )


def emisor_vinculado(mundo, nombre, official_id) -> str:
    user_id = cuenta_con_permisos(
        mundo, nombre, [("gobierno_actos", "issue"), ("gobierno_actos", "view")]
    )
    vinculo_activo(mundo, cuerpo_vinculo(user_id, official_id))
    return user_id


def contexto_de(mundo, vinculo, fecha=None) -> dict:
    params = {"fecha": fecha.isoformat()} if fecha else None
    response = consultar(mundo, f"/vinculos/{vinculo['id']}", params=params)
    assert response.status_code == 200, response.text
    return response.json()["contexto"]
