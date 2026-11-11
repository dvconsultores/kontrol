import os
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="Requiere PostgreSQL",
)

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

from sqlalchemy import select  # noqa: E402

from app.modules.audit.models import AuditEvent  # noqa: E402
from app.modules.identity_access import authority  # noqa: E402
from app.modules.identity_access import service as identity_service  # noqa: E402
from app.modules.identity_access.models import Role, User, UserScope  # noqa: E402
from tests.conftest_multicompany import PASSWORD  # noqa: E402
from tests.org04_ayudantes import titular_activo  # noqa: E402
from tests.org06_ayudantes import cuerpo_vinculo, vinculo_activo  # noqa: E402
from tests.org06_guarda import (  # noqa: E402
    acto_borrador,
    cuenta_con_permisos,
    emitir,
    exigir_identidad,
)

API = "/api/v1"


def _sufijo() -> str:
    return uuid4().hex[:6]


def _tecnico_puro(mundo, nombre: str) -> str:
    db = mundo.factory()
    try:
        usuario = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username=nombre,
            email=None,
            password=PASSWORD,
            created_by=None,
        )
        user_id = str(usuario.id)
        db.add(UserScope(user_id=user_id, company_id=mundo.company_a))
        rol_admin = db.scalars(
            select(Role).where(
                Role.code == "ADMIN",
                Role.protected.is_(True),
                Role.company_id.is_(None),
            )
        ).one()
        ua_id = str(
            db.scalar(
                select(User.id).where(
                    User.username == "ua", User.tenant_id == mundo.t1
                )
            )
        )
        identity_service.assign_role_to_user(
            db,
            tenant_id=mundo.t1,
            user_id=user_id,
            role_id=str(rol_admin.id),
            company_id=None,
            actor=ua_id,
        )
        db.commit()
        return user_id
    finally:
        db.close()


def _dual(mundo, nombre: str) -> str:
    db = mundo.factory()
    try:
        usuario = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username=nombre,
            email=None,
            password=PASSWORD,
            created_by=None,
        )
        user_id = str(usuario.id)
        db.add(UserScope(user_id=user_id, company_id=mundo.company_a))
        ua_id = str(
            db.scalar(
                select(User.id).where(
                    User.username == "ua", User.tenant_id == mundo.t1
                )
            )
        )
        for code in ("ADMIN", "FUNCIONAL_COMPLETO"):
            rol = db.scalars(
                select(Role).where(
                    Role.code == code,
                    Role.protected.is_(True),
                    Role.company_id.is_(None),
                )
            ).one()
            identity_service.assign_role_to_user(
                db,
                tenant_id=mundo.t1,
                user_id=user_id,
                role_id=str(rol.id),
                company_id=None,
                actor=ua_id,
            )
        db.commit()
        return user_id
    finally:
        db.close()


def _proyeccion(mundo, usuario: str, empresa: str):
    return mundo.client.get(
        f"{API}/gobierno/control/separacion",
        headers=mundo.como(usuario, empresa),
    )


def _fila_por_usuario(payload: dict, username: str) -> dict | None:
    for fila in payload.get("administradores", []):
        if fila.get("usuario") == username:
            return fila
    return None


def test_sp01_integridad_y_actor_dual(mundo, gobierno):
    """SP-01 Integridad y actor dual de instalacion."""
    try:
        exigir_identidad(mundo, False)
        resp = _proyeccion(mundo, "ua", mundo.company_a)
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["integridad"]["integra"] is True
        assert payload["integridad"]["admin"]["fuera_de_lugar"] == []
        assert payload["integridad"]["funcional"]["fuera_de_lugar"] == []
        assert payload["exigencia_identidad"]["activa"] is False
        fila = _fila_por_usuario(payload, "ua")
        assert fila is not None
        assert fila["separacion"] == "TECNICO_Y_FUNCIONAL_SIN_AUTORIDAD"
        assert fila["identidad"]["motivo"] == "SIN_VINCULO"
        roles = {rol["codigo"]: rol for rol in fila["roles"]}
        assert roles["ADMIN"]["tipo"] == "TECNICO"
        assert roles["ADMIN"]["protegido"] is True
        assert roles["FUNCIONAL_COMPLETO"]["tipo"] == "FUNCIONAL"
    finally:
        exigir_identidad(mundo, False)


def test_sp02_tecnico_puro(mundo, gobierno):
    """SP-02 Tecnico puro aparece solo en su empresa."""
    try:
        exigir_identidad(mundo, False)
        nombre = f"ctl03_tecnico_{_sufijo()}"
        _tecnico_puro(mundo, nombre)
        resp = _proyeccion(mundo, "ua", mundo.company_a)
        fila = _fila_por_usuario(resp.json(), nombre)
        assert fila is not None
        assert fila["separacion"] == "SOLO_TECNICO"
        assert len(fila["roles"]) == 1
        assert fila["roles"][0]["codigo"] == "ADMIN"
        assert fila["roles"][0]["origen"]["fuente"] == "ASIGNACION"
        assert fila["roles"][0]["origen"]["actor"] == "ua"
        resp_b = _proyeccion(mundo, "uab", mundo.company_b)
        assert _fila_por_usuario(resp_b.json(), nombre) is None
    finally:
        exigir_identidad(mundo, False)


def test_sp03_denegacion_rol_sombra(mundo, gobierno):
    """SP-03 Denegacion de rol sombra queda registrada."""
    try:
        exigir_identidad(mundo, False)
        nombre = f"ctl03_tecnico_{_sufijo()}"
        user_id = _tecnico_puro(mundo, nombre)
        db = mundo.factory()
        try:
            actor = db.scalars(select(User).where(User.id == user_id)).one()
            with pytest.raises(authority.PermissionDeniedError):
                authority.check_can_create_role(
                    db,
                    actor=actor,
                    code="ROOT_CTL03",
                    permissions=["gobierno_decision:decide"],
                    company_id=None,
                )
            assert (
                db.scalars(
                    select(Role).where(Role.code == "ROOT_CTL03")
                ).first()
                is None
            )
        finally:
            db.close()
        resp = _proyeccion(mundo, "ua", mundo.company_a)
        denegaciones = resp.json().get("denegaciones", [])
        encontrada = None
        for denegacion in denegaciones:
            if (
                denegacion.get("usuario") == nombre
                and denegacion.get("codigo") == "AUTHORITY_CEILING_EXCEEDED"
                and denegacion.get("rol") == "ROOT_CTL03"
            ):
                encontrada = denegacion
                break
        assert encontrada is not None
        assert encontrada["capacidades_excedidas"] == ["gobierno_decision:decide"]
        assert encontrada["en_bitacora"] is False
    finally:
        exigir_identidad(mundo, False)


def test_sp08_autoescalada_http_denegacion_persistida(mundo, gobierno):
    """SP-08 La autoescalada por HTTP se audita y aparece en la proyección."""
    try:
        exigir_identidad(mundo, False)
        nombre = f"ctl03_tecnico_{_sufijo()}"
        user_id = _tecnico_puro(mundo, nombre)

        # Obtener el ID del rol FUNCIONAL_COMPLETO
        db = mundo.factory()
        try:
            rol_funcional = db.scalars(
                select(Role).where(
                    Role.code == "FUNCIONAL_COMPLETO",
                    Role.protected.is_(True),
                    Role.company_id.is_(None),
                )
            ).one()
            role_id = str(rol_funcional.id)
        finally:
            db.close()

        # Cabeceras del usuario técnico puro
        headers = mundo.como(nombre, mundo.company_a)

        # Autoasignación por HTTP
        resp = mundo.client.post(
            f"{API}/users/{user_id}/roles",
            json={"role_id": role_id},
            headers=headers,
        )
        assert resp.status_code == 403
        assert resp.json().get("code") == "SELF_ESCALATION_FORBIDDEN"

        # Verificar el AuditEvent en BD
        db = mundo.factory()
        try:
            evento = db.scalars(
                select(AuditEvent).where(
                    AuditEvent.action == "AUTHORITY_DELEGATION_DENIED",
                    AuditEvent.reason == "SELF_ESCALATION_FORBIDDEN",
                    AuditEvent.user_id == user_id,
                )
            ).first()
            assert evento is not None, (
                "Capa A: evento no persistido en BD. "
                f"company_id={getattr(evento, 'company_id', None)}, evidence={evento.evidence if evento else None}"
            )
            evidence = evento.evidence or {}
            assert evidence.get("company_id") is None
            assert evidence.get("role_code") == "FUNCIONAL_COMPLETO"
            assert evidence.get("capabilities_excedidas")
        finally:
            db.close()

        # Proyección para company_a
        resp_a = _proyeccion(mundo, "ua", mundo.company_a)
        denegaciones_a = resp_a.json().get("denegaciones", [])
        encontrada_a = None
        for denegacion in denegaciones_a:
            if denegacion.get("usuario") == nombre and denegacion.get("codigo") == "SELF_ESCALATION_FORBIDDEN":
                encontrada_a = denegacion
                break
        assert encontrada_a is not None, (
            "Capa B: la proyección para company_a no contiene la denegación "
            f"esperada para {nombre}. Denegaciones actuales: {denegaciones_a}"
        )

        # Aislamiento: proyección para company_b no la contiene
        resp_b = _proyeccion(mundo, "uab", mundo.company_b)
        denegaciones_b = resp_b.json().get("denegaciones", [])
        encontrada_b = any(
            d.get("usuario") == nombre and d.get("codigo") == "SELF_ESCALATION_FORBIDDEN"
            for d in denegaciones_b
        )
        assert not encontrada_b, (
            "Capa B: la proyección para company_b contiene la denegación de "
            f"{nombre}, lo que viola el aislamiento (CROSS_COMPANY_LEAK)."
        )
    finally:
        exigir_identidad(mundo, False)


def test_sp04_permiso_no_es_autoridad(mundo, gobierno, ocupacion):
    """SP-04 Permiso funcional sin vinculo es denegado y queda en bitacora."""
    try:
        asig, cargo = titular_activo(mundo, ocupacion)
        exigir_identidad(mundo, True)
        resp = emitir(mundo, acto_borrador(mundo, cargo), "ua")
        assert resp.status_code == 403
        assert resp.json().get("code") == "GOV_IDENTITY_LINK_REQUIRED"
        payload = _proyeccion(mundo, "ua", mundo.company_a).json()
        denegacion = None
        for item in payload.get("denegaciones", []):
            if (
                item.get("accion") == "GOV_IDENTITY_GUARD_BLOCKED"
                and item.get("codigo") == "GOV_IDENTITY_LINK_REQUIRED"
                and item.get("usuario") == "ua"
            ):
                denegacion = item
                break
        assert denegacion is not None
        assert denegacion["en_bitacora"] is True
        payload_b = _proyeccion(mundo, "uab", mundo.company_b).json()
        ids_b = {item["id"] for item in payload_b.get("denegaciones", [])}
        assert denegacion["id"] not in ids_b
    finally:
        exigir_identidad(mundo, False)


def test_sp05_actor_legitimo(mundo, gobierno, ocupacion):
    """SP-05 Actor con vinculo emite y no es administrador."""
    try:
        asig, cargo = titular_activo(mundo, ocupacion)
        nombre = f"ctl03_legitimo_{_sufijo()}"
        emisor_id = cuenta_con_permisos(
            mundo, nombre, [("gobierno_actos", "issue"), ("gobierno_actos", "view")]
        )
        vinculo_activo(
            mundo, cuerpo_vinculo(emisor_id, asig["funcionario"]["id"])
        )
        exigir_identidad(mundo, True)
        resp = emitir(mundo, acto_borrador(mundo, cargo), nombre)
        assert resp.status_code == 200
        payload = _proyeccion(mundo, "ua", mundo.company_a).json()
        assert _fila_por_usuario(payload, nombre) is None
    finally:
        exigir_identidad(mundo, False)


def test_sp06_dual_con_cargo(mundo, gobierno, ocupacion):
    """SP-06 Dual con cargo tiene separacion con autoridad."""
    try:
        exigir_identidad(mundo, False)
        nombre = f"ctl03_dual_{_sufijo()}"
        user_id = _dual(mundo, nombre)
        asig, _ = titular_activo(mundo, ocupacion)
        vinculo_activo(
            mundo, cuerpo_vinculo(user_id, asig["funcionario"]["id"])
        )
        resp = _proyeccion(mundo, "ua", mundo.company_a)
        fila = _fila_por_usuario(resp.json(), nombre)
        assert fila is not None
        assert fila["separacion"] == "TECNICO_Y_FUNCIONAL_CON_AUTORIDAD"
        assert fila["identidad"]["funcionario"]
        assert any(
            ocupacion.get("competencias")
            for ocupacion in fila["identidad"]["ocupaciones"]
        )
    finally:
        exigir_identidad(mundo, False)


def test_sp07_permisos(mundo, gobierno):
    """SP-07 Sin permiso de gobierno la proyeccion es 403."""
    try:
        exigir_identidad(mundo, False)
        nombre = f"ctl03_sin_{_sufijo()}"
        cuenta_con_permisos(mundo, nombre, [("gobierno_actos", "view")])
        assert _proyeccion(mundo, nombre, mundo.company_a).status_code == 403
        tecnico = f"ctl03_tecnico_{_sufijo()}"
        _tecnico_puro(mundo, tecnico)
        assert _proyeccion(mundo, tecnico, mundo.company_a).status_code == 403
    finally:
        exigir_identidad(mundo, False)
