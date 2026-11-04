import pytest

from tests.test_gov_ctl01_reglas import cerrar_regla, eventos, regla_vigente
from tests.test_gov_doc02_actos import (
    ANIO,
    HOY,
    A,
    _crear_cargo_y_competencias,
    _ente,
    _publicar_estructura,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_doc02_actos")

PREP: dict = {}


@pytest.fixture
def preparado(mundo, gobierno):
    """Prepara una sola vez ente, estructura publicada y un cargo con competencia APROBAR/CONTRATACIONES."""
    if not PREP:
        _ente(mundo, mundo.company_a, "ACTIVO")
        r = mundo.post("/gobierno/estructuras", "ua", mundo.company_a, {"ejercicio": ANIO})
        assert r.status_code == 201, r.text
        estructura_id = r.json()["id"]
        r = mundo.post(f"/gobierno/estructuras/{ANIO}/unidades", "ua", mundo.company_a,
                       {"codigo": "DA-01", "denominacion": "Dirección de Administración", "tipo": "UNIDAD_ADMINISTRATIVA"})
        assert r.status_code == 201, r.text
        unidad_id = r.json()["id"]
        _publicar_estructura(mundo, mundo.company_a, estructura_id, "ua")
        cargo = _crear_cargo_y_competencias(mundo, mundo.company_a, unidad_id, "DIR-ADM", "Director de Administración", [("APROBAR", "CONTRATACIONES")])
        PREP["cargo"] = cargo["id"]
    return PREP


def _cuerpo_acto(numero: str) -> dict:
    return {
        "tipo": "RESOLUCION",
        "numero": numero,
        "fecha": HOY.isoformat(),
        "lugar": "Caracas",
        "cargo_id": PREP["cargo"],
        "competencia": {"accion": "APROBAR", "materia": "CONTRATACIONES"},
        "fundamento_competencia": "Reglamento interno, art. 12",
        "funcionario": "Ana Pérez",
        "titularidad": "TITULAR",
        "caracter": "PARTICULAR",
        "destinatario": "Proveedor Ejemplo, C.A.",
        "asunto": "Asunto inicial",
        "hechos": "Hechos de prueba",
        "fundamentos": "Fundamentos de prueba",
        "decision": "Decisión de prueba",
    }


def _editar(mundo, acto_id, usuario, version, asunto):
    return mundo.client.patch(
        f"/api/v1{A}/{acto_id}",
        headers={**mundo.como(usuario, mundo.company_a), "If-Match": str(version)},
        json={"asunto": asunto},
    )


def test_sd01_guarda_preventiva_doc02_edicion_mismo_usuario(mundo, preparado):
    """SD-01: La regla DOC-02 activa bloquea la edición del autor del acto y permite la de otro usuario."""
    regla = regla_vigente(mundo, proceso="DOC-02", accion_a="DOC02_REGISTRAR", accion_b="DOC02_EDITAR")
    try:
        r = mundo.post(A, "ua", mundo.company_a, _cuerpo_acto(f"SOD-DA-01-{ANIO}"))
        assert r.status_code == 201, r.text
        acto_id = r.json()["id"]
        version = r.json()["version"]
        assert r.json()["asunto"] == "Asunto inicial", r.text

        r = _editar(mundo, acto_id, "ua", version, "Asunto cambiado por el autor")
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "GOV_SOD_CONFLICT", r.text
        details = r.json()["details"]
        assert details["regla_codigo"] == regla["codigo"], r.text
        assert details["accion"] == "DOC02_EDITAR", r.text
        assert details["accion_etiqueta"] == "Editar el borrador del acto", r.text
        assert details["accion_previa"] == "DOC02_REGISTRAR", r.text
        assert details["objeto_tipo"] == "GovernmentAct", r.text
        assert details["objeto_id"] == acto_id, r.text

        r = mundo.get(f"{A}/{acto_id}", "ua", mundo.company_a)
        assert r.status_code == 200, r.text
        assert r.json()["asunto"] == "Asunto inicial", r.text
        assert r.json()["version"] == version, r.text

        eventos_bloqueo = eventos(mundo, "GOV_SOD_CONFLICT_BLOCKED", regla["id"])
        assert len(eventos_bloqueo) == 1, eventos_bloqueo
        assert eventos_bloqueo[0].after["objeto_tipo"] == "GovernmentAct", eventos_bloqueo
        assert eventos_bloqueo[0].after["objeto_id"] == acto_id, eventos_bloqueo

        eventos_acto = eventos(mundo, "GOV_ACT_UPDATED", acto_id)
        assert eventos_acto == [], eventos_acto

        r = _editar(mundo, acto_id, "uab", version, "Asunto cambiado por otro usuario")
        assert r.status_code == 200, r.text
        assert r.json()["asunto"] == "Asunto cambiado por otro usuario", r.text
    finally:
        cerrar_regla(mundo, regla)


def test_sd02_guarda_preventiva_doc02_regla_cerrada_permite_edicion(mundo, preparado):
    """SD-02: La regla DOC-02 cerrada no bloquea la edición del autor del acto."""
    regla = regla_vigente(mundo, proceso="DOC-02", accion_a="DOC02_REGISTRAR", accion_b="DOC02_EDITAR")
    cerrar_regla(mundo, regla)

    r = mundo.post(A, "ua", mundo.company_a, _cuerpo_acto(f"SOD-DA-02-{ANIO}"))
    assert r.status_code == 201, r.text
    acto_id = r.json()["id"]
    version = r.json()["version"]

    r = _editar(mundo, acto_id, "ua", version, "Asunto editado con regla cerrada")
    assert r.status_code == 200, r.text
    assert r.json()["asunto"] == "Asunto editado con regla cerrada", r.text
