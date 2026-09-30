"""AUD-TENANT · El listado de auditoría no cruza tenants (FR-001-032/033, ARCH-MC-001).

`GET /api/v1/audit/events` devolvía la bitácora entera de la instalación a
cualquiera con `audit:view`: medido, un evento de `DEMO2` entregado a un
administrador de `DEMO`. El alcance del listado es de **tenant** —matriz de
alcance por endpoint de ARCH-MC-001, guarda N10— y el tenant sale del usuario
autenticado, nunca de la consulta ni del cuerpo.

Dos tenants, cada uno con su administrador, y eventos **de contenido idéntico**
en ambos: si la única diferencia entre EVENT_A y EVENT_B es el tenant, lo único
que puede separarlos es el filtro que se está probando.

SQLite en memoria por defecto; sobre PostgreSQL con `KONTROL_TEST_DB_URL`.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from conftest import make_engine
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.company_context import COMPANY_HEADER
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.audit.models import AuditEvent
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole, UserScope
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize
from app.shared.audit import record_audit

PASSWORD = "Kontrol2026Segura!"
_FACTORY: sessionmaker | None = None
_CLIENT: TestClient | None = None
#: Identificadores del mundo: tenants, empresas y usuarios.
W: dict[str, str] = {}


def _import_license(db: Session) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    now = datetime.now(UTC)
    payload = {
        "issuer": "K", "license_id": "LIC-AUD-TENANT", "installation_id": inst.installation_uuid,
        "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-12345678-9",
        "period_start": (now - timedelta(days=30)).isoformat(),
        "period_end": (now + timedelta(days=120)).isoformat(),
        "critical_warning_start": (now + timedelta(days=180)).isoformat(),
        "read_only_start": (now + timedelta(days=200)).isoformat(),
        "entitlements": {"companies": 5, "users": 25, "modules": ["*"]},
        "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
    }
    sig = key.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hex()
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
    get_settings.cache_clear()
    try:
        licensing_service.import_license(db, payload=payload, signature_hex=sig, source="MANUAL")
    finally:
        os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
        get_settings.cache_clear()


def _usuario(db: Session, tenant_id: str, username: str, *, empresas: list[str] | None,
             con_rol: bool = True) -> str:
    user = identity_service.create_user(
        db, tenant_id=tenant_id, username=username, email=f"{username}@aud.test",
        password=PASSWORD, created_by=None)
    if con_rol:
        rol = _bootstrap_roles(db, tenant_id, str(user.id))
        db.add(UserRole(user_id=str(user.id), role_id=str(rol.id), company_id=None))
    for c in empresas or []:
        db.add(UserScope(user_id=str(user.id), company_id=c))
    db.flush()
    return str(user.id)


@pytest.fixture(scope="module", autouse=True)
def _mundo():
    """Dos tenants: DEMO (empresas D1 y D2) y DEMO2 (empresa E1)."""
    global _FACTORY, _CLIENT
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    initialize(db, SetupRequest(
        tenant_code="DEMO", tenant_name="Tenant A", company_code="D1",
        company_legal_name="Empresa D1 CA", company_rif="J-12345678-9",
        admin_username="admin", admin_password=PASSWORD))
    _import_license(db)

    t_a = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
    d1 = db.execute(select(Company).where(Company.tenant_id == str(t_a.id))).scalars().one()
    d2 = Company(tenant_id=str(t_a.id), code="D2", legal_name="Empresa D2 CA", rif="J-22222222-2",
                 legal_type="JURIDICA", functional_currency="VED", status="ACTIVE")
    db.add(d2)
    db.flush()

    inst = db.execute(select(Installation).limit(1)).scalars().first()
    t_b = Tenant(installation_id=str(inst.id), code="DEMO2", name="Tenant B",
                 plan="MONO_COMPANY", status="ACTIVE")
    db.add(t_b)
    db.flush()
    e1 = Company(tenant_id=str(t_b.id), code="E1", legal_name="Empresa E1 CA", rif="J-33333333-3",
                 legal_type="JURIDICA", functional_currency="VED", status="ACTIVE")
    db.add(e1)
    db.flush()

    W.update(tenant_a=str(t_a.id), tenant_b=str(t_b.id), d1=str(d1.id), d2=str(d2.id), e1=str(e1.id))
    W["admin_b"] = _usuario(db, str(t_b.id), "admin2", empresas=None)
    W["ua"] = _usuario(db, str(t_a.id), "ua", empresas=[str(d1.id)])
    W["sinrol"] = _usuario(db, str(t_a.id), "sinrol", empresas=None, con_rol=False)
    db.commit()
    db.close()

    from app.main import create_app

    app = create_app()

    def _db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    _FACTORY, _CLIENT = factory, TestClient(app)
    yield


# --------------------------------------------------------------------------- #
# Ayudantes
# --------------------------------------------------------------------------- #
def _login(tenant: str, username: str) -> dict:
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": tenant, "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _como_a() -> dict:
    return _login("DEMO", "admin")


def _como_b() -> dict:
    return _login("DEMO2", "admin2")


def _listar(h: dict, **params) -> dict:
    r = _CLIENT.get("/api/v1/audit/events", headers=h, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _ids(body: dict) -> set[str]:
    return {i["id"] for i in body["items"]}


def _marca() -> str:
    return f"aud-{uuid.uuid4().hex[:12]}"


def _evento(tenant_id: str | None, *, entity_id: str, action: str = "AUDTEN_PROBE",
            entity_type: str = "Probe", company_id: str | None = None) -> str:
    """Un evento de contenido fijo; lo único que cambia entre llamadas es el dueño."""
    db = _FACTORY()
    try:
        ev = record_audit(db, action=action, entity_type=entity_type, entity_id=entity_id,
                          tenant_id=tenant_id, company_id=company_id, source="QA",
                          request_id="mismo-request", after={"marca": entity_id})
        db.commit()
        return str(ev.id)
    finally:
        db.close()


def _fila(event_id: str) -> AuditEvent:
    db = _FACTORY()
    try:
        return db.get(AuditEvent, event_id)
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# AUD-TENANT-01/02/03 · listado hostil, inverso y de contenido idéntico
# --------------------------------------------------------------------------- #
def test_aud_tenant_01_el_administrador_de_a_no_recibe_eventos_de_b():
    m = _marca()
    ea = _evento(W["tenant_a"], entity_id=m)
    eb = _evento(W["tenant_b"], entity_id=m)

    body = _listar(_como_a(), entity_id=m)
    assert ea in _ids(body), "el evento propio debe verse"
    assert eb not in _ids(body), "un evento de otro tenant se devolvió a un administrador"
    assert body["total"] == 1

    # Ni la consulta ni el rol amplían el tenant: son datos del cliente.
    forzado = _listar(_como_a(), entity_id=m, tenant_id=W["tenant_b"], company_id=W["e1"])
    assert _ids(forzado) == {ea}
    assert forzado["total"] == 1


def test_aud_tenant_02_inverso_el_administrador_de_b_no_recibe_eventos_de_a():
    m = _marca()
    ea = _evento(W["tenant_a"], entity_id=m)
    eb = _evento(W["tenant_b"], entity_id=m)

    body = _listar(_como_b(), entity_id=m)
    assert _ids(body) == {eb}
    assert ea not in _ids(body)
    assert body["total"] == 1


def test_aud_tenant_03_dos_eventos_identicos_solo_se_separan_por_el_tenant():
    """Si la prueba pasara por una diferencia de contenido, no probaría el filtro."""
    m = _marca()
    ea, eb = _fila(_evento(W["tenant_a"], entity_id=m)), _fila(_evento(W["tenant_b"], entity_id=m))
    iguales = ("action", "entity_type", "entity_id", "request_id", "source", "company_id", "user_id")
    assert all(getattr(ea, c) == getattr(eb, c) for c in iguales)
    assert ea.tenant_id != eb.tenant_id

    assert _ids(_listar(_como_a(), entity_id=m)) == {str(ea.id)}
    assert _ids(_listar(_como_b(), entity_id=m)) == {str(eb.id)}


# --------------------------------------------------------------------------- #
# AUD-TENANT-04/05/06 · total, paginación y filtros dentro del tenant
# --------------------------------------------------------------------------- #
def test_aud_tenant_04_el_total_cuenta_solo_el_tenant_propio():
    m = _marca()
    propios = {_evento(W["tenant_a"], entity_id=m) for _ in range(3)}
    for _ in range(2):
        _evento(W["tenant_b"], entity_id=m)

    body_a = _listar(_como_a(), entity_id=m)
    assert body_a["total"] == 3 and _ids(body_a) == propios
    body_b = _listar(_como_b(), entity_id=m)
    assert body_b["total"] == 2 and not (_ids(body_b) & propios)


def test_aud_tenant_05_la_paginacion_recorre_solo_el_tenant_propio():
    """Un recorte global seguido de un filtro dejaría páginas cortas o vacías."""
    m = _marca()
    propios = {_evento(W["tenant_a"], entity_id=m) for _ in range(23)}
    ajenos = {_evento(W["tenant_b"], entity_id=m) for _ in range(23)}

    vistos: list[str] = []
    tamaños: list[int] = []
    for page in (1, 2, 3):
        body = _listar(_como_a(), entity_id=m, page=page, page_size=10)
        assert body["total"] == 23
        tamaños.append(len(body["items"]))
        vistos += [i["id"] for i in body["items"]]
    assert tamaños == [10, 10, 3]
    assert set(vistos) == propios and len(vistos) == 23
    assert not (set(vistos) & ajenos)
    assert _listar(_como_a(), entity_id=m, page=4, page_size=10)["items"] == []


def test_aud_tenant_06_los_filtros_funcionales_actuan_dentro_del_tenant():
    m = _marca()
    ea = _evento(W["tenant_a"], entity_id=m, action="AUDTEN_FILTRO", entity_type="Filtro")
    _evento(W["tenant_a"], entity_id=m, action="AUDTEN_OTRA", entity_type="Filtro")
    _evento(W["tenant_b"], entity_id=m, action="AUDTEN_FILTRO", entity_type="Filtro")

    body = _listar(_como_a(), entity_id=m, action="AUDTEN_FILTRO", entity_type="Filtro")
    assert _ids(body) == {ea} and body["total"] == 1
    body_b = _listar(_como_b(), action="AUDTEN_FILTRO", entity_type="Filtro", entity_id=m)
    assert ea not in _ids(body_b) and body_b["total"] == 1


# --------------------------------------------------------------------------- #
# AUD-TENANT-07 · el permiso sigue mandando; el alcance no lo sustituye
# --------------------------------------------------------------------------- #
def test_aud_tenant_07_sin_audit_view_no_hay_listado_ni_dentro_del_tenant():
    r = _CLIENT.get("/api/v1/audit/events", headers=_login("DEMO", "sinrol"))
    assert r.status_code == 403, r.text
    assert _CLIENT.get("/api/v1/audit/events", headers=_como_a()).status_code == 200


# --------------------------------------------------------------------------- #
# AUD-TENANT-08 · camino de escritura: cada tenant firma lo suyo
# --------------------------------------------------------------------------- #
def _ultimo(action: str, user_id: str) -> AuditEvent:
    db = _FACTORY()
    try:
        return db.execute(select(AuditEvent).where(AuditEvent.action == action, AuditEvent.entity_id == user_id)
                          .order_by(AuditEvent.event_time.desc()).limit(1)).scalars().one()
    finally:
        db.close()


def test_aud_tenant_08_los_escritores_persisten_el_tenant_del_contexto_autenticado():
    # Evento de tenant (sin empresa): el inicio de sesión.
    ha, hb = _como_a(), _como_b()
    admin_a = _CLIENT.get("/api/v1/auth/me", headers=ha).json()["user"]["id"]
    assert _ultimo("LOGIN_SUCCESS", admin_a).tenant_id == W["tenant_a"]
    assert _ultimo("LOGIN_SUCCESS", W["admin_b"]).tenant_id == W["tenant_b"]

    # Evento de empresa: el tenant se deduce de la empresa validada por el contexto.
    r = _CLIENT.post("/api/v1/organization/warehouses", headers={**ha, COMPANY_HEADER: W["d2"]},
                     json={"company_id": W["d2"], "branch_id": None, "code": "ALM-AUD-A", "name": "Almacén A"})
    assert r.status_code == 200, r.text
    db = _FACTORY()
    try:
        ev = db.execute(select(AuditEvent).where(AuditEvent.entity_id == r.json()["id"])).scalars().first()
        assert ev is not None and ev.tenant_id == W["tenant_a"] and ev.company_id == W["d2"]
    finally:
        db.close()

    r = _CLIENT.post("/api/v1/organization/warehouses", headers=hb,
                     json={"company_id": W["e1"], "branch_id": None, "code": "ALM-AUD-B", "name": "Almacén B"})
    assert r.status_code == 200, r.text
    db = _FACTORY()
    try:
        ev = db.execute(select(AuditEvent).where(AuditEvent.entity_id == r.json()["id"])).scalars().first()
        assert ev is not None and ev.tenant_id == W["tenant_b"] and ev.company_id == W["e1"]
    finally:
        db.close()

    # Y lo que cada uno acaba de escribir solo lo lee su tenant.
    assert not any(i["entity_id"] == r.json()["id"] for i in _listar(ha, page_size=100)["items"])


# --------------------------------------------------------------------------- #
# AUD-TENANT-09 · empresa dentro del tenant: contrato ARCH-MC-001
# --------------------------------------------------------------------------- #
def test_aud_tenant_09_el_listado_es_de_tenant_y_la_vista_por_empresa_es_la_de_reportes():
    """`/audit/events` es `TENANT/INSTALLATION` (matriz de alcance, guarda N10):
    un usuario del tenant con `audit:view` ve la bitácora del tenant entero,
    incluidas las empresas en las que no opera. La vista acotada por empresa
    es `/reporting/audit/timeline`, y esa sí valida la empresa contra el
    acceso del usuario: ajena o de otro tenant, 404 sin revelar que existe."""
    m = _marca()
    en_d2 = _evento(W["tenant_a"], entity_id=m, company_id=W["d2"])
    en_e1 = _evento(W["tenant_b"], entity_id=m, company_id=W["e1"])

    h_ua = _login("DEMO", "ua")                      # solo opera en D1
    body = _listar(h_ua, entity_id=m)
    assert _ids(body) == {en_d2}, "la bitácora del tenant incluye sus otras empresas"
    assert en_e1 not in _ids(body)

    linea = _CLIENT.get("/api/v1/reporting/audit/timeline", headers={**h_ua, COMPANY_HEADER: W["d2"]})
    assert linea.status_code == 404, linea.text
    assert linea.json()["code"] == "COMPANY_NOT_FOUND"
    linea = _CLIENT.get("/api/v1/reporting/audit/timeline", headers={**h_ua, COMPANY_HEADER: W["d1"]})
    assert linea.status_code == 200 and en_d2 not in {i["id"] for i in linea.json()["items"]}

    cruzada = _CLIENT.get("/api/v1/reporting/audit/timeline", headers={**_como_b(), COMPANY_HEADER: W["d2"]})
    assert cruzada.status_code == 404, cruzada.text


# --------------------------------------------------------------------------- #
# AUD-TENANT-10 · un evento sin tenant no es de nadie
# --------------------------------------------------------------------------- #
def test_aud_tenant_10_un_evento_sin_tenant_no_lo_lee_ningun_tenant():
    """Ningún escritor produce tenant nulo y la Spec no define eventos globales
    de auditoría; si una fila así existiera, no tiene lector en este listado.
    `tenant_id IS NULL OR …` la habría regalado a todos."""
    m = _marca()
    huerfano = _evento(None, entity_id=m)
    assert _fila(huerfano).tenant_id is None
    assert huerfano not in _ids(_listar(_como_a(), entity_id=m))
    assert huerfano not in _ids(_listar(_como_b(), entity_id=m))
    assert _listar(_como_a(), entity_id=m)["total"] == 0


# --------------------------------------------------------------------------- #
# AUD-TENANT-11 · inventario de superficies y forma del contrato
# --------------------------------------------------------------------------- #
def test_aud_tenant_11_la_superficie_publica_de_auditoria_y_su_contrato_no_cambian():
    """El aislamiento es una regla de contexto, no un parámetro: el contrato no
    gana `tenant_id` ni cabecera de empresa. Y hoy la única superficie bajo
    `/audit` es el listado: si alguien añade detalle o exportación, esta prueba
    le recuerda que nacen con el mismo alcance."""
    spec = _CLIENT.app.openapi()
    rutas = {r for r in spec["paths"] if r.startswith("/api/v1/audit")}
    assert rutas == {"/api/v1/audit/events"}
    op = spec["paths"]["/api/v1/audit/events"]["get"]
    nombres = {p["name"] for p in op.get("parameters", [])}
    assert nombres == {"page", "page_size", "entity_type", "entity_id", "action"}
    assert COMPANY_HEADER.lower() not in {n.lower() for n in nombres}
