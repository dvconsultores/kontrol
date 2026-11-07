from datetime import UTC, datetime
from itertools import count
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.modules.documents.models import Document, DocumentType
from app.modules.government.models import GovernmentAct
from app.shared.clock import hoy_de_negocio
from tests.test_gov_ctl06_hallazgos import _post


@pytest.fixture(autouse=True)
def politicas_limpias(mundo):
    with mundo.factory() as db:
        db.execute(
            text(
                "UPDATE gov_closure_policies SET estado = 'RETIRADA', "
                "retirada_en = CURRENT_TIMESTAMP, "
                "motivo_retiro = 'Limpieza de la prueba.', "
                "retirada_por = 'prueba' WHERE estado = 'VIGENTE'"
            )
        )
        db.execute(text("UPDATE gov_findings SET estado = 'CERRADO' WHERE estado <> 'CERRADO'"))
        db.execute(
            text(
                "UPDATE gov_acts SET status = 'EFICAZ', fecha_eficacia = fecha "
                "WHERE status = 'EMITIDO'"
            )
        )
        db.commit()
    yield

C = "/gobierno/cierres"
MOTIVO = "Motivo de retiro de la política con la longitud suficiente para ser válido."
_codigos = count(1001)

HOY = hoy_de_negocio()


def _empresa(empresa, mundo):
    return empresa or mundo.company_a


def _cabeceras(mundo, usuario, empresa, version=None):
    cabeceras = mundo.como(usuario, empresa)
    if version is not None:
        cabeceras["If-Match"] = str(version)
    return cabeceras


def cuerpo_politica(accion_cierre="ORG02_CERRAR_ESTRUCTURA", **cambios):
    cuerpo = {
        "nombre": f"Política de cierre {next(_codigos)}",
        "accion_cierre": accion_cierre,
        "fundamento": "Fundamento de control interno con longitud mayor a diez caracteres.",
        "vigente_desde": HOY.isoformat(),
    }
    cuerpo.update(cambios)
    return cuerpo


def post_politica(mundo, accion_cierre="ORG02_CERRAR_ESTRUCTURA", usuario="ua", empresa=None, **cambios):
    return _post(
        mundo,
        f"{C}/politicas",
        usuario,
        _empresa(empresa, mundo),
        cuerpo_politica(accion_cierre=accion_cierre, **cambios),
    )


def crear_politica(mundo, accion_cierre="ORG02_CERRAR_ESTRUCTURA", usuario="ua", empresa=None, **cambios) -> dict:
    r = post_politica(mundo, accion_cierre=accion_cierre, usuario=usuario, empresa=empresa, **cambios)
    assert r.status_code == 201, r.text
    return r.json()


def post_control(mundo, politica, tipo, riesgo_minimo=None, usuario="ua", empresa=None):
    cuerpo = {
        "tipo": tipo,
        "materialidad": "Este control evidencia la materialidad del riesgo pendiente.",
    }
    if riesgo_minimo is not None:
        cuerpo["riesgo_minimo"] = riesgo_minimo
    return _post(
        mundo,
        f"{C}/politicas/{politica['id']}/controles",
        usuario,
        _empresa(empresa, mundo),
        cuerpo,
        version=politica["version"],
    )


def anadir_control(mundo, politica, tipo, riesgo_minimo=None, usuario="ua", empresa=None) -> dict:
    r = post_control(mundo, politica, tipo, riesgo_minimo=riesgo_minimo, usuario=usuario, empresa=empresa)
    assert r.status_code == 201, r.text
    return r.json()


def activar(mundo, politica, usuario="ua", empresa=None, version=None):
    version = politica["version"] if version is None else version
    cabeceras = _cabeceras(mundo, usuario, _empresa(empresa, mundo), version)
    return mundo.client.post(f"/api/v1{C}/politicas/{politica['id']}/activar", headers=cabeceras)


def retirar(mundo, politica, motivo=MOTIVO, usuario="ua", empresa=None, version=None):
    version = politica["version"] if version is None else version
    cabeceras = _cabeceras(mundo, usuario, _empresa(empresa, mundo), version)
    return mundo.client.post(
        f"/api/v1{C}/politicas/{politica['id']}/retirar",
        headers=cabeceras,
        json={"motivo": motivo},
    )


def acto_emitido(mundo, siembra, fecha) -> str:
    """Crea y devuelve el id de un acto emitido para pruebas de cierres."""
    company_id = mundo.company_a
    with mundo.factory() as db:
        tipo = db.execute(
            select(DocumentType).where(
                DocumentType.company_id == company_id,
                DocumentType.code == "GOV-CIERRE",
            )
        ).scalar_one_or_none()
        if tipo is None:
            tipo = DocumentType(company_id=company_id, code="GOV-CIERRE", name="Acto de prueba")
            db.add(tipo)
            db.flush()

        doc = Document(
            company_id=company_id,
            document_type_id=tipo.id,
            title="Acto",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()

        numero = uuid4().hex[:12]
        acto = GovernmentAct(
            company_id=company_id,
            tipo="RESOLUCION",
            denominacion_tipo="",
            denominacion_clave="",
            numero=numero,
            numero_clave=numero,
            fecha=fecha,
            lugar="Caracas",
            cargo_id=siembra["cargo_vigente"],
            competencia_accion="APROBAR",
            competencia_materia="PRESUPUESTO",
            fundamento_competencia="Fundamento de prueba",
            funcionario="Funcionario de prueba",
            titularidad="TITULAR",
            caracter="GENERAL",
            asunto="Acto de prueba para cierre",
            status="EMITIDO",
            documento_acto_id=doc.id,
            emitido_en=datetime.now(UTC),
        )
        db.add(acto)
        db.commit()
        return str(acto.id)


def politica_vigente(mundo, accion_cierre, tipo, riesgo_minimo=None, usuario="ua", empresa=None) -> dict:
    politica = crear_politica(mundo, accion_cierre=accion_cierre, usuario=usuario, empresa=empresa)
    politica = anadir_control(mundo, politica, tipo, riesgo_minimo=riesgo_minimo, usuario=usuario, empresa=empresa)
    r = activar(mundo, politica, usuario=usuario, empresa=empresa)
    assert r.status_code == 200, r.text
    return r.json()
