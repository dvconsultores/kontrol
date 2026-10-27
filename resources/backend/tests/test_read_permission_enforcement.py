"""Pruebas de enforcement de lectura para el alcance T01 (spec 003)."""
import uuid
from types import SimpleNamespace

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, login, mundo_mfa
from sqlalchemy import select

from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Role, UserRole
from app.modules.master_data.models import Party
from app.modules.organization.models import Company

pytest_plugins = ("mfa_apoyo",)


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


@pytest.fixture(scope="module")
def escenario(mundo):
    db = mundo.factory()
    try:
        d2 = Company(
            tenant_id=mundo.tenant_id,
            code="RPE-D2",
            legal_name="Read Permission Enforcement D2",
            rif="J-44444444-4",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(d2)
        db.flush()

        roles = {}
        definiciones = {
            "R_RPE_ORG": ["organization:view"],
            "R_RPE_MAE": ["maestros:view"],
            "R_RPE_DASH": ["dashboard:view"],
            "R_RPE_DASH_VEN": ["dashboard:view", "ventas:view"],
            "R_RPE_REP": ["reportes:view", "reportes:export"],
            "R_RPE_REP_VEN": ["reportes:view", "reportes:export", "ventas:view"],
            "R_RPE_AUD": ["audit:view"],
            "R_RPE_FIS": ["fiscal:view"],
            "R_RPE_HOM": ["homologacion:view"],
        }
        sufijo = uuid.uuid4().hex[:8]
        for code, permissions in definiciones.items():
            roles[code] = identity_service.create_role(
                db,
                tenant_id=mundo.tenant_id,
                code=f"{code}-{sufijo}",
                name=code,
                company_id=None,
                permissions=permissions,
                actor=mundo.admin_id,
            )["id"]

        p1 = Party(
            company_id=mundo.company_id,
            code=f"RPE-P1-{uuid.uuid4().hex[:12]}",
            name="Read Permission Party D1",
            person_type="JURIDICA",
            roles=["CLIENTE"],
            status="ACTIVE",
        )
        db.add(p1)
        db.flush()

        p2 = Party(
            company_id=d2.id,
            code=f"RPE-P2-{uuid.uuid4().hex[:12]}",
            name="Read Permission Party D2",
            person_type="JURIDICA",
            roles=["CLIENTE"],
            status="ACTIVE",
        )
        db.add(p2)

        db.commit()
        return SimpleNamespace(
            roles=roles,
            d1=mundo.company_id,
            d2=d2.id,
            p1=p1.id,
            p1_code=p1.code,
            p2=p2.id,
            p2_code=p2.code,
        )
    finally:
        db.close()


def _nombre():
    return f"rpe{uuid.uuid4().hex[:12]}"


def _dar(mundo, user_id, role_id, company_id):
    db = mundo.factory()
    try:
        db.add(
            UserRole(
                user_id=user_id,
                role_id=role_id,
                company_id=company_id,
            )
        )
        db.commit()
    finally:
        db.close()


def _entrar(mundo, reloj, nombre):
    r = login(mundo.client, nombre)
    assert r.status_code == 200, r.text
    if r.json().get("status") == "AUTHENTICATED":
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return alta_por_desafio(mundo.client, reloj, nombre).cabeceras


def _actor(mundo, reloj, role_id, company_id):
    nombre = _nombre()
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, role_id, company_id)
    cabeceras = _entrar(mundo, reloj, nombre)
    return user_id, cabeceras


def _h(cabeceras, empresa):
    copia = dict(cabeceras)
    copia["X-Kontrol-Company"] = str(empresa)
    return copia


def test_rpe_01_lista_sin_capacidad_maestros_es_403(mundo, escenario, reloj_mfa):
    """RPE-01"""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_ORG"], escenario.d1)
    r = mundo.client.get(f"{API}/maestros/terceros", headers=_h(cabeceras, escenario.d1))
    print(r.text)
    assert r.status_code == 403
    assert r.json()["code"] == "PERMISSION_DENIED"
    assert escenario.p1_code not in r.text


def test_rpe_02_detalle_sin_capacidad_maestros_es_403(mundo, escenario, reloj_mfa):
    """RPE-02"""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_ORG"], escenario.d1)
    r = mundo.client.get(
        f"{API}/maestros/terceros/{escenario.p1}",
        headers=_h(cabeceras, escenario.d1),
    )
    print(r.text)
    assert r.status_code == 403
    assert r.json()["code"] == "PERMISSION_DENIED"


def test_rpe_03_busqueda_sin_capacidad_maestros_es_403(mundo, escenario, reloj_mfa):
    """RPE-03"""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_ORG"], escenario.d1)
    r = mundo.client.get(
        f"{API}/maestros/catalogos/items/search",
        params={"q": "RPE"},
        headers=_h(cabeceras, escenario.d1),
    )
    print(r.text)
    assert r.status_code == 403
    assert r.json()["code"] == "PERMISSION_DENIED"


def test_rpe_04_agregados_sin_capacidad_son_403(mundo, escenario, reloj_mfa):
    """RPE-04"""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_ORG"], escenario.d1)

    r1 = mundo.client.get(f"{API}/purchasing/aging", headers=_h(cabeceras, escenario.d1))
    print(r1.text)
    assert r1.status_code == 403
    assert r1.json()["code"] == "PERMISSION_DENIED"

    r2 = mundo.client.get(f"{API}/inventory/valuation", headers=_h(cabeceras, escenario.d1))
    print(r2.text)
    assert r2.status_code == 403
    assert r2.json()["code"] == "PERMISSION_DENIED"


def test_rpe_05_empresa_cruzada_maestros_scope_forbidden(mundo, escenario, reloj_mfa):
    """RPE-05"""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_MAE"], escenario.d2)

    r1 = mundo.client.get(f"{API}/maestros/terceros", headers=_h(cabeceras, escenario.d1))
    print(r1.text)
    assert r1.status_code == 403
    assert r1.json()["code"] == "COMPANY_SCOPE_FORBIDDEN"

    r2 = mundo.client.get(f"{API}/maestros/terceros", headers=_h(cabeceras, escenario.d2))
    print(r2.text)
    assert r2.status_code == 200
    assert escenario.p2_code in r2.text
    assert escenario.p1_code not in r2.text


def test_rpe_06_empresa_inexistente_es_404(mundo, escenario, reloj_mfa):
    """RPE-06"""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_MAE"], escenario.d1)
    r = mundo.client.get(
        f"{API}/maestros/terceros",
        headers=_h(cabeceras, str(uuid.uuid4())),
    )
    print(r.text)
    assert r.status_code == 404
    assert r.json()["code"] == "COMPANY_NOT_FOUND"


def test_rpe_07_idor_detalle_tercero_otra_empresa_es_404(mundo, escenario, reloj_mfa):
    """RPE-07"""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_MAE"], escenario.d1)

    r1 = mundo.client.get(
        f"{API}/maestros/terceros/{escenario.p2}",
        headers=_h(cabeceras, escenario.d1),
    )
    print(r1.text)
    assert r1.status_code == 404
    assert r1.json()["code"] == "PARTY_NOT_FOUND"

    r2 = mundo.client.get(
        f"{API}/maestros/terceros/{escenario.p1}",
        headers=_h(cabeceras, escenario.d1),
    )
    print(r2.text)
    assert r2.status_code == 200


def test_rpe_08_tablero_filtra_indicadores_por_capacidad(mundo, escenario, reloj_mfa):
    """RPE-08"""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_DASH_VEN"], escenario.d1)
    r = mundo.client.get(f"{API}/reporting/dashboard", headers=_h(cabeceras, escenario.d1))
    print(r.text)
    assert r.status_code == 200
    body = r.json()
    assert set(body["indicators"]) == {"ventas", "cxc"}
    assert body["vencimientos"] == {}


def test_rpe_09_tablero_admin_tecnico_sin_indicadores_y_lector_denegado(mundo, escenario, reloj_mfa):
    """RPE-09"""
    nombre_admin = _nombre()
    crear_usuario(mundo, nombre_admin, admin=True)
    cabeceras_admin = _entrar(mundo, reloj_mfa, nombre_admin)

    r_admin = mundo.client.get(
        f"{API}/reporting/dashboard",
        headers=_h(cabeceras_admin, escenario.d1),
    )
    print(r_admin.text)
    assert r_admin.status_code == 200
    body = r_admin.json()
    assert body["indicators"] == {}
    assert body["vencimientos"] == {}

    _, cabeceras_org = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_ORG"], escenario.d1)
    r_org = mundo.client.get(
        f"{API}/reporting/dashboard",
        headers=_h(cabeceras_org, escenario.d1),
    )
    print(r_org.text)
    assert r_org.status_code == 403
    assert r_org.json()["code"] == "PERMISSION_DENIED"


def test_rpe_10_vista_previa_reporte_exige_capacidad_del_reporte(mundo, escenario, reloj_mfa):
    """RPE-10"""
    _, cab_rep = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_REP"], escenario.d1)
    r1 = mundo.client.get(
        f"{API}/reporting/reports/executive_ventas",
        headers=_h(cab_rep, escenario.d1),
    )
    print(r1.text)
    assert r1.status_code == 403
    assert r1.json()["code"] == "PERMISSION_DENIED"

    _, cab_rep_ven = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_REP_VEN"], escenario.d1)
    r2 = mundo.client.get(
        f"{API}/reporting/reports/executive_ventas",
        headers=_h(cab_rep_ven, escenario.d1),
    )
    print(r2.text)
    assert r2.status_code == 200

    r3 = mundo.client.get(
        f"{API}/reporting/reports/no_existe",
        headers=_h(cab_rep_ven, escenario.d1),
    )
    print(r3.text)
    assert r3.status_code == 404
    assert r3.json()["code"] == "REPORT_NOT_FOUND"

    _, cab_org = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_ORG"], escenario.d1)
    r4 = mundo.client.get(
        f"{API}/reporting/reports/executive_ventas",
        headers=_h(cab_org, escenario.d1),
    )
    print(r4.text)
    assert r4.status_code == 403
    assert r4.json()["code"] == "PERMISSION_DENIED"


def test_rpe_11_exportacion_y_descarga_exigen_capacidad_del_reporte(mundo, escenario, reloj_mfa):
    """RPE-11"""
    _, cab_rep_ven = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_REP_VEN"], escenario.d1)
    payload = {"report_key": "executive_ventas", "format": "CSV", "filters": {}}

    r_create = mundo.client.post(
        f"{API}/reporting/exports",
        json=payload,
        headers=_h(cab_rep_ven, escenario.d1),
    )
    print(r_create.text)
    assert r_create.status_code == 200
    export_id = r_create.json()["id"]

    _, cab_rep = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_REP"], escenario.d1)

    r_download = mundo.client.get(
        f"{API}/reporting/exports/{export_id}/download",
        headers=_h(cab_rep, escenario.d1),
    )
    print(r_download.text)
    assert r_download.status_code == 403
    assert r_download.json()["code"] == "PERMISSION_DENIED"

    r_create_denied = mundo.client.post(
        f"{API}/reporting/exports",
        json=payload,
        headers=_h(cab_rep, escenario.d1),
    )
    print(r_create_denied.text)
    assert r_create_denied.status_code == 403
    assert r_create_denied.json()["code"] == "PERMISSION_DENIED"

    r_download_ok = mundo.client.get(
        f"{API}/reporting/exports/{export_id}/download",
        headers=_h(cab_rep_ven, escenario.d1),
    )
    print(r_download_ok.text)
    assert r_download_ok.status_code == 200


def test_rpe_12_linea_auditoria_exige_capacidad(mundo, escenario, reloj_mfa):
    """RPE-12"""
    _, cab_org = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_ORG"], escenario.d1)
    r1 = mundo.client.get(
        f"{API}/reporting/audit/timeline",
        headers=_h(cab_org, escenario.d1),
    )
    print(r1.text)
    assert r1.status_code == 403
    assert r1.json()["code"] == "PERMISSION_DENIED"

    _, cab_aud = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_AUD"], escenario.d1)
    r2 = mundo.client.get(
        f"{API}/reporting/audit/timeline",
        headers=_h(cab_aud, escenario.d1),
    )
    print(r2.text)
    assert r2.status_code == 200


def test_rpe_13_catalogos_globales_exigen_capacidad_propia(mundo, escenario, reloj_mfa):
    """RPE-13"""
    _, cab_org = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_ORG"], escenario.d1)

    r1 = mundo.client.get(f"{API}/fiscal/legal-sources", headers=cab_org)
    print(r1.text)
    assert r1.status_code == 403
    assert r1.json()["code"] == "PERMISSION_DENIED"

    r2 = mundo.client.get(f"{API}/homologation/records", headers=cab_org)
    print(r2.text)
    assert r2.status_code == 403
    assert r2.json()["code"] == "PERMISSION_DENIED"

    _, cab_fis = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_FIS"], escenario.d1)
    r3 = mundo.client.get(f"{API}/fiscal/legal-sources", headers=cab_fis)
    print(r3.text)
    assert r3.status_code == 200

    _, cab_hom = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_HOM"], escenario.d1)
    r4 = mundo.client.get(f"{API}/homologation/records", headers=cab_hom)
    print(r4.text)
    assert r4.status_code == 200


def test_rpe_14_funcional_completo_no_es_todas_las_empresas(mundo, escenario, reloj_mfa):
    """RPE-14"""
    db = mundo.factory()
    try:
        funcional_role_id = db.execute(
            select(Role.id).where(
                Role.code == "FUNCIONAL_COMPLETO",
                Role.protected.is_(True),
                Role.company_id.is_(None),
            )
        ).scalar_one()

        nombre = _nombre()
        user_id = crear_usuario(mundo, nombre)
        db.add(
            UserRole(
                user_id=user_id,
                role_id=funcional_role_id,
                company_id=escenario.d1,
            )
        )
        db.commit()
    finally:
        db.close()

    cabeceras = _entrar(mundo, reloj_mfa, nombre)

    r1 = mundo.client.get(f"{API}/sales/orders", headers=_h(cabeceras, escenario.d2))
    print(r1.text)
    assert r1.status_code == 403
    assert r1.json()["code"] == "COMPANY_SCOPE_FORBIDDEN"

    r2 = mundo.client.get(f"{API}/sales/orders", headers=_h(cabeceras, escenario.d1))
    print(r2.text)
    assert r2.status_code == 200


def test_rpe_15_admin_tecnico_no_lee_negocio(mundo, escenario, reloj_mfa):
    """RPE-15"""
    nombre = _nombre()
    crear_usuario(mundo, nombre, admin=True)
    cabeceras = _entrar(mundo, reloj_mfa, nombre)

    r1 = mundo.client.get(f"{API}/sales/orders", headers=_h(cabeceras, escenario.d1))
    print(r1.text)
    assert r1.status_code == 403
    assert r1.json()["code"] == "PERMISSION_DENIED"

    r2 = mundo.client.get(f"{API}/maestros/terceros", headers=_h(cabeceras, escenario.d1))
    print(r2.text)
    assert r2.status_code == 403
    assert r2.json()["code"] == "PERMISSION_DENIED"


def test_rpe_16_trabajos_de_reporte_exigen_capacidad_del_reporte(mundo, escenario, reloj_mfa):
    """RPE-16"""
    _, cab_rep_ven = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_REP_VEN"], escenario.d1)
    payload = {"report_key": "executive_ventas"}

    r_create = mundo.client.post(
        f"{API}/reporting/jobs",
        json=payload,
        headers=_h(cab_rep_ven, escenario.d1),
    )
    print(r_create.text)
    assert r_create.status_code == 200
    job_id = r_create.json()["id"]

    _, cab_rep = _actor(mundo, reloj_mfa, escenario.roles["R_RPE_REP"], escenario.d1)

    r_create_denied = mundo.client.post(
        f"{API}/reporting/jobs",
        json=payload,
        headers=_h(cab_rep, escenario.d1),
    )
    print(r_create_denied.text)
    assert r_create_denied.status_code == 403
    assert r_create_denied.json()["code"] == "PERMISSION_DENIED"

    r_run_denied = mundo.client.post(
        f"{API}/reporting/jobs/{job_id}/run",
        headers=_h(cab_rep, escenario.d1),
    )
    print(r_run_denied.text)
    assert r_run_denied.status_code == 403
    assert r_run_denied.json()["code"] == "PERMISSION_DENIED"

    r_run_ok = mundo.client.post(
        f"{API}/reporting/jobs/{job_id}/run",
        headers=_h(cab_rep_ven, escenario.d1),
    )
    print(r_run_ok.text)
    assert r_run_ok.status_code == 200
