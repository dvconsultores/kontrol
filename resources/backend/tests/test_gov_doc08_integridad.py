import io
import os

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.modules.government import service_paquetes
from app.modules.government.models import GovernmentAuditSampleItem
from app.modules.identity_access.mfa_policy import SENSITIVE, STANDARD, classify
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseEntitlementSnapshot
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from app.shared.audit_catalog import catalog
from tests.test_gov_doc08_paquete import M, P, _activar_gobierno, _generar

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.test_gov_doc08_paquete")


class TestGovDoc08Alcance:
    def test_da05_inmutabilidad_poste_postgresql(self, mundo, gobierno, escenario):
        if not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"):
            pytest.skip("solo PostgreSQL")

        muestra_id = escenario["muestra_id"]
        generacion = _generar(mundo, muestra_id, usuario="ua")
        assert generacion.status_code == 201
        paquete_id = generacion.json()["id"]

        descarga = mundo.get(f"{P}/{paquete_id}/descargar", "ua", mundo.company_a)
        assert descarga.status_code == 200

        verificacion = mundo.client.post(
            f"/api/v1{P}/verificar",
            headers=mundo.como("ua", mundo.company_a),
            files={"archivo": ("p.zip", io.BytesIO(descarga.content), "application/zip")},
        )
        assert verificacion.status_code == 200

        with mundo.factory() as db:
            with pytest.raises(DBAPIError, match="GOV_AUDIT_PACKAGE_IMMUTABLE"):
                db.execute(
                    text("UPDATE gov_audit_packages SET proposito = 'otro' WHERE id = :i"),
                    {"i": paquete_id},
                )
            db.rollback()

        with mundo.factory() as db:
            with pytest.raises(DBAPIError, match="GOV_AUDIT_PACKAGE_IMMUTABLE"):
                db.execute(
                    text("DELETE FROM gov_audit_packages WHERE id = :i"),
                    {"i": paquete_id},
                )
            db.rollback()

        with mundo.factory() as db:
            with pytest.raises(DBAPIError, match="GOV_AUDIT_PACKAGE_IMMUTABLE"):
                db.execute(
                    text(
                        "UPDATE gov_audit_package_verifications "
                        "SET resultado = 'INVALIDO' WHERE package_id = :i"
                    ),
                    {"i": paquete_id},
                )
            db.rollback()

        with mundo.factory() as db:
            with pytest.raises(DBAPIError, match="GOV_AUDIT_PACKAGE_IMMUTABLE"):
                db.execute(
                    text("DELETE FROM gov_audit_package_verifications WHERE package_id = :i"),
                    {"i": paquete_id},
                )
            db.rollback()

    def test_da06_limites_documentos(self, mundo, gobierno, escenario, monkeypatch):
        monkeypatch.setattr(service_paquetes, "MAX_DOCUMENTOS", 1)

        muestra_id = escenario["muestra_id"]
        vista_previa = mundo.get(f"{M}/{muestra_id}/paquete/vista-previa", "ua", mundo.company_a)
        assert vista_previa.status_code == 200
        assert vista_previa.json()["excede_limite"] is True
        assert vista_previa.json()["motivo_limite"]

        generacion = _generar(mundo, muestra_id, usuario="ua")
        assert generacion.status_code == 422
        assert generacion.json()["code"] == "GOV_PACKAGE_TOO_LARGE"

    def test_da07_la_muestra_no_se_altera(self, mundo, gobierno, escenario):
        muestra_id = escenario["muestra_id"]

        def _estado_muestra():
            with mundo.factory() as db:
                cantidad = db.scalar(
                    select(func.count())
                    .select_from(GovernmentAuditSampleItem)
                    .where(GovernmentAuditSampleItem.sample_id == muestra_id)
                )
            detalle = mundo.get(f"{M}/{muestra_id}", "ua", mundo.company_a)
            return cantidad, detalle.json()

        cantidad_antes, detalle_antes = _estado_muestra()
        assert cantidad_antes > 0
        assert "codigo" in detalle_antes
        assert "eventos" in detalle_antes

        generacion = _generar(mundo, muestra_id, usuario="ua")
        assert generacion.status_code == 201

        cantidad_despues, detalle_despues = _estado_muestra()
        assert cantidad_despues == cantidad_antes
        assert detalle_despues["codigo"] == detalle_antes["codigo"]
        assert [evento["id"] for evento in detalle_despues["eventos"]] == [
            evento["id"] for evento in detalle_antes["eventos"]
        ]

    def test_da08_modulo_apagado(self, mundo, gobierno):
        def _modulo(activo: bool) -> None:
            with mundo.factory() as db:
                inst = licensing_service.get_installation(db)
                for snapshot in db.scalars(
                    select(LicenseEntitlementSnapshot).where(
                        LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                    )
                ):
                    snapshot.modules = {**(snapshot.modules or {}), "gobierno": activo}
                db.commit()

        _modulo(False)
        try:
            respuesta = mundo.get(P, "ua", mundo.company_a)
            assert respuesta.status_code == 403
            assert respuesta.json()["code"] == "MODULE_NOT_ENTITLED"
        finally:
            _modulo(True)
            _activar_gobierno(mundo)

    def test_da09_catalogo_y_mfa(self):
        assert classify(["gobierno_paquetes:generate"]) == SENSITIVE
        assert classify(["gobierno_paquetes:view"]) == STANDARD

        assert CATALOGO_DE_PERMISOS["gobierno_paquetes"] == ["view", "generate"]

        for accion in (
            "GOV_AUDIT_PACKAGE_GENERATED",
            "GOV_AUDIT_PACKAGE_DOWNLOADED",
            "GOV_AUDIT_PACKAGE_VERIFIED",
            "GOV_AUDIT_PACKAGE_VERIFICATION_FAILED",
        ):
            assert catalog()[(accion, "GovernmentAuditPackage")].owner_spec == "gov-doc-08"
