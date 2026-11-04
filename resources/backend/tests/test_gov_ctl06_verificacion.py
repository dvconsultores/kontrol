"""Suite de backend CTL-06 (GOV-CTL-008): verificacion."""
from sqlalchemy import select

from app.modules.documents.models import DocumentLink
from tests.test_gov_ctl06_hallazgos import (
    H,
    _doc_vinculado,
    _hallazgo_en_remediacion,
    _post,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_gh6_18_maker_checker_self_verification(mundo, gobierno, siembra):
    """GH6-18: quien presentó o registró avances no puede verificar ni devolver."""
    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    accion_id = detalle["acciones"][0]["id"]
    version = detalle["version"]

    documento_id = _doc_vinculado(mundo, mundo.company_a, accion_id)
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance del 100 % con evidencia.", "porcentaje": 100, "documento_id": documento_id},
        version=version,
    )
    assert response.status_code == 201, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/presentar",
        "ua",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/verificar",
        "ua",
        mundo.company_a,
        {"nota": "Verificación con conflicto de maker-checker."},
        version=version,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "GOV_FINDING_SELF_VERIFICATION"

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/devolver",
        "ua",
        mundo.company_a,
        {"motivo": "Devolución con conflicto de maker-checker."},
        version=version,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "GOV_FINDING_SELF_VERIFICATION"


def test_gh6_19_devolucion_y_cierre_con_historia(mundo, gobierno, siembra):
    """GH6-19: devolución, nuevo avance, presentación y verificación; DocumentLink congelado e historia completa."""
    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    accion_id = detalle["acciones"][0]["id"]
    version = detalle["version"]

    documento_id = _doc_vinculado(mundo, mundo.company_a, accion_id)
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance inicial al cien por cien.", "porcentaje": 100, "documento_id": documento_id},
        version=version,
    )
    assert response.status_code == 201, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/presentar",
        "ua",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/devolver",
        "uab",
        mundo.company_a,
        {"motivo": "La evidencia requiere una aclaración adicional."},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    assert detalle["estado"] == "EN_REMEDIACION"
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Segundo avance al cien por cien tras la devolución.", "porcentaje": 100, "documento_id": documento_id},
        version=version,
    )
    assert response.status_code == 201, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/presentar",
        "ua",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/verificar",
        "uab",
        mundo.company_a,
        {"nota": "Evidencia validada y hallazgo cerrado."},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    assert detalle["estado"] == "CERRADO"
    assert detalle["verificado_por"] == "uab"

    tipos = [fila["tipo"] for fila in detalle["historia"]]
    assert tipos[-5:] == ["PRESENTADO", "DEVUELTO", "AVANCE", "PRESENTADO", "VERIFICADO"]

    with mundo.factory() as db:
        link = db.scalar(
            select(DocumentLink).where(
                DocumentLink.document_id == documento_id,
                DocumentLink.resource_type == "GovernmentCorrectiveAction",
                DocumentLink.resource_id == accion_id,
            )
        )
        assert link is not None
        assert link.is_frozen is True


def test_gh6_20_escritura_bloqueada_en_cerrado(mundo, gobierno, siembra):
    """GH6-20: en CERRADO, ejecución, presentación y avances devuelven GOV_FINDING_INVALID_STATE."""
    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    accion_id = detalle["acciones"][0]["id"]
    version = detalle["version"]

    documento_id = _doc_vinculado(mundo, mundo.company_a, accion_id)
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance para completar la acción.", "porcentaje": 100, "documento_id": documento_id},
        version=version,
    )
    assert response.status_code == 201, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/presentar",
        "ua",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/verificar",
        "uab",
        mundo.company_a,
        {"nota": "Cierre del hallazgo para comprobar bloqueos de escritura."},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/ejecucion",
        "ua",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "GOV_FINDING_INVALID_STATE"

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/presentar",
        "ua",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "GOV_FINDING_INVALID_STATE"

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance posterior al cierre.", "porcentaje": 100, "documento_id": documento_id},
        version=version,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "GOV_FINDING_INVALID_STATE"
