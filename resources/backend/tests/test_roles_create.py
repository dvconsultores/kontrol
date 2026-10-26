"""ROLE · Alta de roles personalizados con sus permisos por `POST /roles` (ROLES-SIN-API-DE-ALTA; FR-001-040,
043, 072). Autoridad en el backend: sesión + `roles:create`; tenant del actor; `company_id` opcional del mismo
tenant; permisos como `recurso:accion` que deben existir; `protected`/`status` del servidor; identidad
`(code, company_id)` con 409 también bajo concurrencia; rol y permisos en una sola transacción; auditoría
`ROLE_CREATED`; ningún usuario queda asignado. Mundo sintético con dos tenants; SQLite o PostgreSQL.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.modules.audit.models import AuditEvent
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, User, UserRole
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine
from tests.test_system_access import PASSWORD, _usuario

ROLES = "/api/v1/roles"
PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")

_CLIENT: TestClient
_FACTORY: sessionmaker
_EMPRESA_A: str
_EMPRESA_T2: str


@pytest.fixture(scope="module", autouse=True)
def _mundo() -> Iterator[None]:
    """DEMO (admin con todo; `operador` sin `roles:create`; `lector` sin `roles:view`) y un segundo tenant T2 con su empresa."""
    global _CLIENT, _FACTORY, _EMPRESA_A, _EMPRESA_T2
    import app.core.database as dm

    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine, dm._SessionLocal = engine, factory  # type: ignore[attr-defined]
    with factory() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
        empresa = db.execute(select(Company).where(Company.tenant_id == tenant.id)).scalars().one()
        _EMPRESA_A = str(empresa.id)
        _usuario(db, str(tenant.id), str(empresa.id), "operador", sin={"roles:create"})
        _usuario(db, str(tenant.id), str(empresa.id), "lector", sin={"roles:view", "roles:create"})
        inst = db.execute(select(Installation)).scalars().first()
        t2 = Tenant(installation_id=str(inst.id), code="T2", name="Tenant Dos")
        db.add(t2)
        db.flush()
        c2 = Company(tenant_id=str(t2.id), code="C2", legal_name="Otra C.A.", rif="J-99999999-9")
        db.add(c2)
        db.flush()
        _EMPRESA_T2 = str(c2.id)
        db.commit()
    from app.main import create_app

    app = create_app()

    def _db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    _CLIENT, _FACTORY = TestClient(app), factory
    yield


def _sesion(username: str = "admin") -> dict[str, str]:
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _crear(cuerpo: dict, quien: str = "admin"):
    return _CLIENT.post(ROLES, json=cuerpo, headers=_sesion(quien))


def _roles(code: str) -> list[Role]:
    with _FACTORY() as db:
        return list(db.execute(select(Role).where(Role.code == code)).scalars().all())


def _permisos_de(role_id: str) -> set[str]:
    with _FACTORY() as db:
        filas = db.execute(select(Permission.resource, Permission.action).join(RolePermission, RolePermission.permission_id == Permission.id)
                           .where(RolePermission.role_id == role_id)).all()
        return {f"{r}:{a}" for r, a in filas}


def _asignaciones() -> int:
    with _FACTORY() as db:
        return int(db.execute(select(func.count()).select_from(UserRole)).scalar_one())


# ---------------------------------------------------------------- ROLE-01..04 · autenticación, permiso, alta, respuesta
def test_role_01_sin_sesion_401_auth_required():
    r = _CLIENT.post(ROLES, json={"code": "X", "name": "X"})
    assert r.status_code == 401 and r.json()["code"] == "AUTH_REQUIRED"
    assert _roles("X") == []


def test_role_02_con_sesion_pero_sin_roles_create_403_y_nada_creado():
    r = _crear({"code": "VENDEDOR-OP", "name": "Vendedor"}, quien="operador")
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED", r.text
    assert _roles("VENDEDOR-OP") == []


def test_role_03_04_el_alta_autorizada_crea_el_rol_con_sus_permisos_y_responde_el_esquema_canonico():
    antes = _asignaciones()
    r = _crear({"code": "VENDEDOR", "name": "Vendedor de mostrador", "permissions": ["roles:view", "users:view", "roles:view"]})
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert set(cuerpo) == {"id", "code", "name", "protected", "status", "company_id", "permissions"}
    assert cuerpo["code"] == "VENDEDOR" and cuerpo["protected"] is False and cuerpo["status"] == "ACTIVE" and cuerpo["company_id"] is None
    assert cuerpo["permissions"] == ["roles:view", "users:view"]  # ordenados y sin repetidos
    assert _permisos_de(cuerpo["id"]) == {"roles:view", "users:view"}
    assert _asignaciones() == antes  # ROLE-17: no se asigna a nadie
    listado = _CLIENT.get(ROLES, headers=_sesion()).json()["items"]
    assert any(x["id"] == cuerpo["id"] and x["permissions"] == ["roles:view", "users:view"] for x in listado)
    with _FACTORY() as db:
        rol = db.get(Role, cuerpo["id"])
        assert rol is not None and rol.created_by is not None  # el servidor fija el autor


# ---------------------------------------------------------------- ROLE-05..07 · alcance y tenant
def test_role_05_un_rol_acotado_a_una_empresa_del_tenant_se_crea_con_ese_alcance():
    r = _crear({"code": "CAJERO", "name": "Cajero", "company_id": _EMPRESA_A, "permissions": []})
    assert r.status_code == 201 and r.json()["company_id"] == _EMPRESA_A and r.json()["permissions"] == []


def test_role_06_07_una_empresa_de_otro_tenant_o_inexistente_no_vale_como_alcance():
    for empresa in (_EMPRESA_T2, "00000000-0000-0000-0000-000000000000"):
        r = _crear({"code": "AJENO", "name": "Ajeno", "company_id": empresa})
        assert r.status_code == 404 and r.json()["code"] == "COMPANY_NOT_FOUND", r.text
    assert _roles("AJENO") == []


# ---------------------------------------------------------------- ROLE-08..09 · permisos
def test_role_08_un_permiso_desconocido_rechaza_el_alta_entera_sin_crear_nada():
    r = _crear({"code": "RARO", "name": "Raro", "permissions": ["roles:view", "nave:despegar", "users:volar"]})
    assert r.status_code == 422 and r.json()["code"] == "PERMISSION_UNKNOWN", r.text
    assert r.json()["field_errors"]["permissions"] == ["nave:despegar", "users:volar"]
    assert _roles("RARO") == []
    with _FACTORY() as db:  # el alta no crea permisos
        assert db.execute(select(Permission).where(Permission.resource == "nave")).scalars().first() is None


# ---------------------------------------------------------------- ROLE-10..11 · campos del servidor
@pytest.mark.parametrize("campo", [{"protected": True}, {"status": "ACTIVE"}, {"created_by": "yo"}, {"tenant_id": "x"}, {"id": "x"}])
def test_role_10_11_los_campos_internos_en_el_cuerpo_son_422_y_no_crean_nada(campo: dict):
    r = _crear({"code": "INTERNO", "name": "Interno", **campo})
    assert r.status_code == 422, r.text
    assert _roles("INTERNO") == []


def test_role_10b_un_rol_creado_por_la_api_nunca_nace_protegido():
    r = _crear({"code": "NORMAL", "name": "Normal"})
    assert r.status_code == 201 and r.json()["protected"] is False
    with _FACTORY() as db:
        assert db.get(Role, r.json()["id"]).protected is False


# ---------------------------------------------------------------- ROLE-12 · duplicado
def test_role_12_el_mismo_codigo_en_el_mismo_alcance_es_409_y_en_otro_alcance_no():
    assert _crear({"code": "DUP", "name": "Uno"}).status_code == 201
    r = _crear({"code": "DUP", "name": "Dos"})
    assert r.status_code == 409 and r.json()["code"] == "ROLE_DUPLICATE"
    assert len(_roles("DUP")) == 1
    assert _crear({"code": "DUP", "name": "Tres", "company_id": _EMPRESA_A}).status_code == 201  # otro alcance: identidad distinta
    assert _crear({"code": "ADMIN", "name": "Suplantar"}).status_code == 409  # el protegido del arranque también cuenta


@pytest.mark.parametrize("cuerpo", [{"code": "", "name": "x"}, {"code": "con espacio", "name": "x"}, {"code": "x" * 65, "name": "x"},
                                    {"code": "OK", "name": ""}, {"code": "OK"}, {"name": "x"}, {"code": "OK", "name": "x", "permissions": "roles:view"}])
def test_role_12b_cuerpos_invalidos_son_422_sin_crear_nada(cuerpo: dict):
    assert _crear(cuerpo).status_code == 422
    assert _roles("OK") == []


# ---------------------------------------------------------------- ROLE-13 · concurrencia (PostgreSQL)
@pytest.mark.skipif(not PG, reason="la exactitud del duplicado bajo concurrencia se certifica en PostgreSQL")
def test_role_13_altas_simultaneas_del_mismo_codigo_dejan_exactamente_una_fila():
    cabeceras = _sesion()
    resultados: list[int] = []
    cerrojo, barrera = threading.Lock(), threading.Barrier(12)

    def pedir() -> None:
        barrera.wait()
        r = _CLIENT.post(ROLES, json={"code": "CARRERA", "name": "Carrera", "permissions": ["roles:view"]}, headers=cabeceras)
        with cerrojo:
            resultados.append(r.status_code)

    hilos = [threading.Thread(target=pedir) for _ in range(12)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(resultados) == [201] + [409] * 11, resultados
    assert len(_roles("CARRERA")) == 1


# ---------------------------------------------------------------- ROLE-16 · atomicidad
def test_role_16_si_falla_la_asociacion_de_permisos_no_queda_rol_a_medias(monkeypatch):
    class Rota(Exception):
        pass

    def explota(*args, **kwargs):
        raise Rota("asociación de permisos rota")

    monkeypatch.setattr(identity_service, "RolePermission", explota)
    with _FACTORY() as db, pytest.raises(Rota):
        admin = db.execute(select(User).where(User.username == "admin")).scalars().one()
        identity_service.create_role(db, tenant_id=str(admin.tenant_id), code="MEDIAS", name="A medias", company_id=None, permissions=["roles:view"], actor=str(admin.id))
    assert _roles("MEDIAS") == []
    with _FACTORY() as db:  # tampoco queda auditoría de un alta que no ocurrió
        eventos = db.execute(select(AuditEvent).where(AuditEvent.action == "ROLE_CREATED")).scalars().all()
        assert all((e.after or {}).get("code") != "MEDIAS" for e in eventos)


# ---------------------------------------------------------------- ROLE-19..21 · auditoría, lectura, roles protegidos intactos
def test_role_19_el_alta_se_audita_sin_secretos():
    r = _crear({"code": "AUDITADO", "name": "Auditado", "permissions": ["roles:view"]})
    assert r.status_code == 201
    with _FACTORY() as db:
        evento = db.execute(select(AuditEvent).where(AuditEvent.action == "ROLE_CREATED", AuditEvent.entity_id == r.json()["id"])).scalars().one()
        assert evento.entity_type == "Role" and evento.user_id is not None
        assert evento.after == {"code": "AUDITADO", "name": "Auditado", "company_id": None, "permissions": ["roles:view"]}
        assert "Bearer" not in str(evento.after) and "eyJ" not in str(evento.after)


def test_role_20_el_listado_sigue_exigiendo_roles_view_y_los_protegidos_siguen_igual():
    assert _CLIENT.get(ROLES, headers=_sesion("lector")).status_code == 403
    with _FACTORY() as db:
        admin = db.execute(select(Role).where(Role.code == "ADMIN", Role.company_id.is_(None))).scalars().one()
        assert admin.protected is True and admin.status == "ACTIVE"
