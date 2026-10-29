import secrets

from sqlalchemy import func, select

from app.modules.identity_access.models import (
    MfaFactor,
    MfaRecoveryCode,
    Role,
    User,
)
from app.modules.identity_access.models import (
    Session as SesionDeUsuario,
)

pytest_plugins = ("tests.hostil_mundo",)


def _password() -> str:
    return "Zz9!" + secrets.token_urlsafe(18)


def _ids_de_json(payload):
    if isinstance(payload, list):
        return {item.get("id") for item in payload if isinstance(item, dict)}
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return {item.get("id") for item in payload["items"] if isinstance(item, dict)}
    return set()


def test_iso_ten_01_users_no_cruzan_tenant(mundo_hostil):
    """ISO-TEN-01: GET /users no lista usuarios del tenant ajeno."""
    resp_a = mundo_hostil.pedir("admin_a", "GET", "/users")
    resp_b = mundo_hostil.pedir("admin_b", "GET", "/users")

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    usernames_a = {u["username"] for u in resp_a.json()}
    usernames_b = {u["username"] for u in resp_b.json()}

    usernames_ta = {
        actor.username
        for actor in mundo_hostil.actores.values()
        if actor.tenant == "TA"
    }
    usernames_tb = {
        actor.username
        for actor in mundo_hostil.actores.values()
        if actor.tenant == "TB"
    }

    assert usernames_b.isdisjoint(usernames_ta)
    assert usernames_a.isdisjoint(usernames_tb)


def test_iso_ten_02_roles_no_cruzan_tenant(mundo_hostil):
    """ISO-TEN-02: GET /roles no expone roles personalizados del tenant ajeno."""
    resp_b = mundo_hostil.pedir("admin_b", "GET", "/roles")
    resp_a = mundo_hostil.pedir("admin_a", "GET", "/roles")

    assert resp_b.status_code == 200
    assert resp_a.status_code == 200

    codes_b = {item["code"] for item in resp_b.json()["items"]}
    codes_a = {item["code"] for item in resp_a.json()["items"]}

    assert codes_b.isdisjoint({"R_ISO_CONSULTA_TA", "R_ISO_AUDIT_TA"})
    assert "R_ISO_CONSULTA_TA" in codes_a


def test_iso_ten_03_rol_homonimo_no_revela_duplicado(mundo_hostil):
    """ISO-TEN-03: crear rol con código del tenant ajeno no revela su existencia con 409."""
    resp = mundo_hostil.pedir(
        "admin_b",
        "POST",
        "/roles",
        json={
            "code": "R_ISO_CONSULTA_TA",
            "name": "Rol homónimo de TB",
            "permissions": [],
        },
    )

    assert resp.status_code == 201

    with mundo_hostil.factory() as db:
        ta_count = db.scalar(
            select(func.count()).select_from(Role).where(
                Role.code == "R_ISO_CONSULTA_TA",
                Role.tenant_id == mundo_hostil.tenants["TA"],
            )
        )
        tb_count = db.scalar(
            select(func.count()).select_from(Role).where(
                Role.code == "R_ISO_CONSULTA_TA",
                Role.tenant_id == mundo_hostil.tenants["TB"],
            )
        )

    assert ta_count == 1
    assert tb_count == 1


def test_iso_ten_04_usuario_homonimo_no_revela_duplicado(mundo_hostil):
    """ISO-TEN-04: crear usuario con username del tenant ajeno no revela su existencia con 409."""
    username = mundo_hostil.actores["a1_op"].username

    resp = mundo_hostil.pedir(
        "admin_b",
        "POST",
        "/users",
        json={
            "username": username,
            "password": _password(),
            "must_change_password": True,
        },
    )

    assert 200 <= resp.status_code < 300

    with mundo_hostil.factory() as db:
        ta_count = db.scalar(
            select(func.count()).select_from(User).where(
                User.username == username,
                User.tenant_id == mundo_hostil.tenants["TA"],
            )
        )
        tb_count = db.scalar(
            select(func.count()).select_from(User).where(
                User.username == username,
                User.tenant_id == mundo_hostil.tenants["TB"],
            )
        )

    assert ta_count == 1
    assert tb_count == 1


def test_iso_ten_05_mfa_reset_ajeno_404(mundo_hostil):
    """ISO-TEN-05: reset de MFA de usuario ajeno devuelve 404 USER_NOT_FOUND sin efectos."""
    a1_user_id = mundo_hostil.actores["a1_op"].user_id

    with mundo_hostil.factory() as db:
        before_factors = db.scalar(
            select(func.count()).select_from(MfaFactor).where(
                MfaFactor.user_id == a1_user_id
            )
        )
        before_recovery = db.scalar(
            select(func.count()).select_from(MfaRecoveryCode).where(
                MfaRecoveryCode.user_id == a1_user_id
            )
        )

    resp = mundo_hostil.pedir(
        "admin_b", "POST", f"/users/{a1_user_id}/mfa/reset"
    )

    assert resp.status_code == 404
    assert resp.json().get("code") == "USER_NOT_FOUND"

    with mundo_hostil.factory() as db:
        after_factors = db.scalar(
            select(func.count()).select_from(MfaFactor).where(
                MfaFactor.user_id == a1_user_id
            )
        )
        after_recovery = db.scalar(
            select(func.count()).select_from(MfaRecoveryCode).where(
                MfaRecoveryCode.user_id == a1_user_id
            )
        )

    assert after_factors == before_factors
    assert after_recovery == before_recovery


def test_iso_ten_06_sessions_no_cruzan_tenant(mundo_hostil):
    """ISO-TEN-06: GET /auth/sessions no devuelve sesiones del usuario ajeno."""
    a1_user_id = mundo_hostil.actores["a1_op"].user_id

    with mundo_hostil.factory() as db:
        a1_session_ids = set(
            db.scalars(
                select(SesionDeUsuario.id).where(
                    SesionDeUsuario.user_id == a1_user_id
                )
            )
        )

    resp = mundo_hostil.pedir("b1_op", "GET", "/auth/sessions")

    assert resp.status_code == 200
    returned_ids = _ids_de_json(resp.json())
    assert returned_ids.isdisjoint(a1_session_ids)


def test_iso_ten_07_rutas_propias_ignoran_ids_ajenos(mundo_hostil):
    """ISO-TEN-07: rutas propias no actúan sobre usuario/tenant ajenos aunque se inyecten."""
    a1_user_id = mundo_hostil.actores["a1_op"].user_id
    tenant_ta = mundo_hostil.tenants["TA"]

    with mundo_hostil.factory() as db:
        before_hash = db.scalar(
            select(User.password_hash).where(User.id == a1_user_id)
        )
        before_factors = db.scalar(
            select(func.count()).select_from(MfaFactor).where(
                MfaFactor.user_id == a1_user_id
            )
        )
        before_recovery = db.scalar(
            select(func.count()).select_from(MfaRecoveryCode).where(
                MfaRecoveryCode.user_id == a1_user_id
            )
        )
        before_sessions = db.scalar(
            select(func.count()).select_from(SesionDeUsuario).where(
                SesionDeUsuario.user_id == a1_user_id
            )
        )

    resp_me = mundo_hostil.pedir(
        "b1_op", "GET", "/auth/me", params={"user_id": a1_user_id}
    )
    if resp_me.status_code == 200:
        assert resp_me.json().get("username") == mundo_hostil.actores["b1_op"].username
    assert mundo_hostil.actores["a1_op"].username not in resp_me.text

    for ruta in ("/auth/operations", "/auth/mfa"):
        resp = mundo_hostil.pedir("b1_op", "GET", ruta)
        assert mundo_hostil.fugas("b1_op", resp.text) == []
        assert mundo_hostil.actores["a1_op"].username not in resp.text

    payload_base = {"user_id": a1_user_id, "tenant_id": tenant_ta}
    rutas_con_cuerpo = [
        ("POST", "/auth/mfa/recovery-codes", dict(payload_base)),
        ("DELETE", "/auth/mfa", dict(payload_base)),
        ("POST", "/auth/reauth", dict(payload_base)),
        (
            "POST",
            "/auth/change-password",
            {
                **payload_base,
                "current_password": _password(),
                "new_password": _password(),
            },
        ),
    ]

    for metodo, ruta, cuerpo in rutas_con_cuerpo:
        mundo_hostil.pedir("b1_op", metodo, ruta, json=cuerpo)

    with mundo_hostil.factory() as db:
        after_hash = db.scalar(
            select(User.password_hash).where(User.id == a1_user_id)
        )
        after_factors = db.scalar(
            select(func.count()).select_from(MfaFactor).where(
                MfaFactor.user_id == a1_user_id
            )
        )
        after_recovery = db.scalar(
            select(func.count()).select_from(MfaRecoveryCode).where(
                MfaRecoveryCode.user_id == a1_user_id
            )
        )
        after_sessions = db.scalar(
            select(func.count()).select_from(SesionDeUsuario).where(
                SesionDeUsuario.user_id == a1_user_id
            )
        )

    assert after_hash == before_hash
    assert after_factors == before_factors
    assert after_recovery == before_recovery
    assert after_sessions == before_sessions
