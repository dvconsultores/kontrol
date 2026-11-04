import io

from sqlalchemy import select

from app.modules.documents.storage import get_storage
from app.modules.government.models import GovernmentAuditPackage
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos
from tests.test_gov_doc08_paquete import M, P, _generar

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.test_gov_doc08_paquete")


def _vista_previa(mundo, muestra_id: str, usuario: str, empresa: str):
    return mundo.get(f"{M}/{muestra_id}/paquete/vista-previa", usuario, empresa)


def _generado(mundo, escenario, usuario: str = "ua") -> dict:
    r = _generar(mundo, escenario["muestra_id"], usuario=usuario)
    assert r.status_code == 201, r.text
    return r.json()


class TestGovDoc08Alcance:
    def test_da01_generar_sin_permiso_documental(self, mundo, gobierno, escenario):
        _crear_usuario_con_permisos(
            mundo, "paq_gen", [("gobierno_paquetes", "view"), ("gobierno_paquetes", "generate")], mundo.company_a
        )
        r = _vista_previa(mundo, escenario["muestra_id"], "paq_gen", mundo.company_a)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        por_id = {d["id"]: d for d in cuerpo["documentos"]}
        for d in (escenario["d1"], escenario["d2"], escenario["d3"]):
            assert por_id[d]["estado"] == "EXCLUIDO"
            assert por_id[d]["motivo"] == "SIN_PERMISO"
        assert cuerpo["documentos_incluidos"] == 0
        paquete = _generado(mundo, escenario, usuario="paq_gen")
        assert paquete["documentos_incluidos"] == 0
        assert paquete["documentos_excluidos"] == 3
        d = mundo.get(f"{P}/{paquete['id']}/descargar", "paq_gen", mundo.company_a)
        assert d.status_code == 403
        assert d.json()["code"] == "GOV_PACKAGE_DOCUMENTS_FORBIDDEN"

    def test_da02_descargar_sin_leer_los_documentos(self, mundo, gobierno, escenario):
        paquete = _generado(mundo, escenario)
        incluidos = {d["id"] for d in paquete["contenido"]["documentos"] if d["estado"] == "INCLUIDO"}
        assert incluidos == {escenario["d1"], escenario["d3"]}
        _crear_usuario_con_permisos(
            mundo, "paq_doc", [("gobierno_paquetes", "view"), ("documentos", "download")], mundo.company_a
        )
        r = mundo.get(f"{P}/{paquete['id']}", "paq_doc", mundo.company_a)
        assert r.status_code == 200
        d = mundo.get(f"{P}/{paquete['id']}/descargar", "paq_doc", mundo.company_a)
        assert d.status_code == 403
        assert d.json()["code"] == "GOV_PACKAGE_DOCUMENTS_FORBIDDEN"
        m = mundo.get(f"{P}/{paquete['id']}/manifiesto", "paq_doc", mundo.company_a)
        assert m.status_code == 403
        assert m.json()["code"] == "GOV_PACKAGE_DOCUMENTS_FORBIDDEN"

    def test_da03_otra_empresa_y_otro_tenant(self, mundo, gobierno, escenario):
        paquete = _generado(mundo, escenario)
        r = mundo.get(f"{P}/{paquete['id']}", "ub", mundo.company_b)
        assert r.status_code == 404
        assert r.json()["code"] == "GOV_PACKAGE_NOT_FOUND"
        d = mundo.get(f"{P}/{paquete['id']}/descargar", "ub", mundo.company_b)
        assert d.status_code == 404
        vp = _vista_previa(mundo, escenario["muestra_id"], "ub", mundo.company_b)
        assert vp.status_code == 404
        assert vp.json()["code"] == "GOV_AUDIT_SAMPLE_NOT_FOUND"
        g = _generar(mundo, escenario["muestra_id"], usuario="ub", empresa=mundo.company_b)
        assert g.status_code == 404
        listado = mundo.get(P, "ub", mundo.company_b)
        assert listado.status_code == 200
        ids = {i["id"] for i in listado.json()["items"]}
        assert paquete["id"] not in ids
        t = mundo.get(f"{P}/{paquete['id']}", "uc", mundo.company_c, tenant="T2")
        assert t.status_code == 404

    def test_da04_almacenamiento_alterado(self, mundo, gobierno, escenario):
        paquete = _generado(mundo, escenario)
        with mundo.factory() as db:
            clave = db.scalar(
                select(GovernmentAuditPackage.clave_almacenamiento).where(GovernmentAuditPackage.id == paquete["id"])
            )
        assert clave
        get_storage().put(clave, io.BytesIO(b"contenido sustituido"))
        r = mundo.get(f"{P}/{paquete['id']}/descargar", "ua", mundo.company_a)
        assert r.status_code == 500
        assert r.json()["code"] == "STORAGE_HASH_MISMATCH"
