"""Spec 003 · protección del último administrador de seguridad (DLA)."""

import os
import threading
from uuid import uuid4

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, eventos, mundo_mfa
from sqlalchemy import func, select

from app.modules.identity_access import authority
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole
from tests.conftest import motor_para_hilos

pytest_plugins = ("mfa_apoyo",)

PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")
solo_postgresql = pytest.mark.skipif(
    not PG, reason="la carrera del último administrador se certifica sobre PostgreSQL (INV-DEL-12; P21)"
)

PLAZO = 15


@pytest.fixture
def mundo():
    with motor_para_hilos("delegacion-ultimo-admin") as engine:
        with mundo_mfa(engine=engine) as m:
            yield m


def _nombre():
    return uuid4().hex[:10]


def _id_rol(mundo, code):
    db = mundo.factory()
    try:
        roles = identity_service.list_roles(db)
        for rol in roles:
            if rol["code"] == code:
                return rol["id"]
        raise AssertionError(f"rol {code} no encontrado")
    finally:
        db.close()


def _filas(mundo, user_id, role_id):
    db = mundo.factory()
    try:
        return db.execute(
            select(func.count()).select_from(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        ).scalar_one()
    finally:
        db.close()


def _dar(mundo, user_id, role_id):
    db = mundo.factory()
    try:
        db.add(UserRole(user_id=user_id, role_id=role_id, company_id=None))
        db.commit()
    finally:
        db.close()


def _quitar(mundo, cab, user_id, role_id):
    return mundo.client.delete(f"{API}/users/{user_id}/roles/{role_id}", headers=cab)


def _denegaciones(mundo, actor_id):
    return [
        e
        for e in eventos(mundo, "LAST_ADMIN_OPERATION_DENIED")
        if e.user_id == actor_id and e.reason == "LAST_SECURITY_ADMIN_REQUIRED"
    ]


def _en_hilos(*trabajos):
    barrera = threading.Barrier(len(trabajos), timeout=PLAZO)
    hilos = []
    resultados = []
    errores = []

    def envoltorio(fn, idx):
        def run():
            try:
                barrera.wait(timeout=PLAZO)
                resultados[idx] = fn()
            except Exception as exc:
                errores.append(f"{type(exc).__name__}: {exc}")

        return run

    for idx, trabajo in enumerate(trabajos):
        resultados.append(None)
        hilo = threading.Thread(target=envoltorio(trabajo, idx))
        hilos.append(hilo)

    for hilo in hilos:
        hilo.start()

    for hilo in hilos:
        hilo.join(PLAZO)
        assert not hilo.is_alive(), f"hilo {hilo.name} sigue vivo tras {PLAZO}s"

    assert errores == [], errores
    assert all(resultado is not None for resultado in resultados), resultados
    return resultados


def test_dla_l01_se_queda_sin_administradores_de_seguridad(mundo, reloj_mfa):
    """DLA-L01: quitar el rol ADMIN al único administrador de seguridad debe denegarse con LAST_SECURITY_ADMIN_REQUIRED."""
    j_nombre = _nombre()
    J = crear_usuario(mundo, j_nombre, admin=True)
    cab = alta_por_desafio(mundo.client, reloj_mfa, j_nombre).cabeceras
    admin_role_id = _id_rol(mundo, "ADMIN")

    r = _quitar(mundo, cab, mundo.admin_id, admin_role_id)
    assert r.status_code == 200, r.text

    r = _quitar(mundo, cab, J, admin_role_id)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "LAST_SECURITY_ADMIN_REQUIRED", r.text
    assert _filas(mundo, J, admin_role_id) == 1
    denegaciones = _denegaciones(mundo, J)
    assert len(denegaciones) == 1


def test_dla_l02_rol_no_protegido_con_capacidades_cuenta_como_admin(mundo, reloj_mfa):
    """DLA-L02: un rol no protegido con capacidades de administrador de seguridad cuenta para el mínimo."""
    db = mundo.factory()
    try:
        identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code="R_DLA_SEG",
            name="R_DLA_SEG",
            company_id=None,
            permissions=["users:view", "users:create", "roles:view", "roles:edit", "users:mfa_reset"],
            actor=mundo.admin_id,
        )
    finally:
        db.close()

    k_nombre = _nombre()
    k_id = crear_usuario(mundo, k_nombre, rol="R_DLA_SEG", admin=False)
    cab_k = alta_por_desafio(mundo.client, reloj_mfa, k_nombre).cabeceras

    j_nombre = _nombre()
    J = crear_usuario(mundo, j_nombre, admin=True)
    cab = alta_por_desafio(mundo.client, reloj_mfa, j_nombre).cabeceras

    admin_role_id = _id_rol(mundo, "ADMIN")

    r = _quitar(mundo, cab, mundo.admin_id, admin_role_id)
    assert r.status_code == 200, r.text
    r = _quitar(mundo, cab, J, admin_role_id)
    assert r.status_code == 200, r.text

    rol_seg_id = _id_rol(mundo, "R_DLA_SEG")
    r = _quitar(mundo, cab_k, k_id, rol_seg_id)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "LAST_SECURITY_ADMIN_REQUIRED", r.text
    assert _filas(mundo, k_id, rol_seg_id) == 1


def test_dla_l03_quitar_rol_que_no_hace_perder_condicion_es_200(mundo, reloj_mfa):
    """DLA-L03: quitar un rol que no otorga las capacidades críticas no rompe el mínimo."""
    db = mundo.factory()
    try:
        identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code="R_DLA_TEC",
            name="R_DLA_TEC",
            company_id=None,
            permissions=["dashboard:view"],
            actor=mundo.admin_id,
        )
    finally:
        db.close()

    rol_tec_id = _id_rol(mundo, "R_DLA_TEC")
    j_nombre = _nombre()
    J = crear_usuario(mundo, j_nombre, admin=True)
    _dar(mundo, J, rol_tec_id)
    cab = alta_por_desafio(mundo.client, reloj_mfa, j_nombre).cabeceras

    admin_role_id = _id_rol(mundo, "ADMIN")
    r = _quitar(mundo, cab, mundo.admin_id, admin_role_id)
    assert r.status_code == 200, r.text

    r = _quitar(mundo, cab, J, rol_tec_id)
    assert r.status_code == 200, r.text


def _dos_admins_unicos(mundo) -> tuple[str, str, str]:
    """Crea A y B como únicos administradores y devuelve (A, B, id del rol ADMIN)."""
    admin_role_id = _id_rol(mundo, "ADMIN")

    A = crear_usuario(mundo, _nombre(), admin=True)
    B = crear_usuario(mundo, _nombre(), admin=True)

    db = mundo.factory()
    try:
        identity_service.remove_role_from_user(
            db,
            tenant_id=mundo.tenant_id,
            user_id=mundo.admin_id,
            role_id=admin_role_id,
            actor=A,
        )
    finally:
        db.close()

    return A, B, admin_role_id


def _quitar_por_servicio(mundo, actor, objetivo, role_id) -> str:
    """Ejecuta remove_role_from_user y devuelve 'ok' o el código del error."""
    db = mundo.factory()
    try:
        identity_service.remove_role_from_user(
            db,
            tenant_id=mundo.tenant_id,
            user_id=objetivo,
            role_id=role_id,
            actor=actor,
        )
        return "ok"
    except Exception as exc:
        return getattr(exc, "code", type(exc).__name__)
    finally:
        db.close()


@solo_postgresql
def test_dla_l04_carrera_renuncia_simultanea_ultimo_admin(mundo):
    """DLA-L04: A y B, únicos administradores, renuncian a la vez a su propio ADMIN: exactamente una renuncia gana y la otra recibe LAST_SECURITY_ADMIN_REQUIRED."""
    A, B, admin_role_id = _dos_admins_unicos(mundo)

    resultados = _en_hilos(
        lambda: _quitar_por_servicio(mundo, A, A, admin_role_id),
        lambda: _quitar_por_servicio(mundo, B, B, admin_role_id),
    )
    assert sorted(resultados) == ["LAST_SECURITY_ADMIN_REQUIRED", "ok"], resultados

    filas_admin = [usuario_id for usuario_id in (A, B) if _filas(mundo, usuario_id, admin_role_id) == 1]
    assert len(filas_admin) == 1


@solo_postgresql
def test_dla_l05_carrera_cruzada_deja_un_administrador(mundo):
    """DLA-L05: A y B se quitan a la vez el ADMIN el uno al otro: una gana y la otra se deniega (techo o último administrador); queda un administrador."""
    A, B, admin_role_id = _dos_admins_unicos(mundo)

    resultados = _en_hilos(
        lambda: _quitar_por_servicio(mundo, A, B, admin_role_id),
        lambda: _quitar_por_servicio(mundo, B, A, admin_role_id),
    )
    assert resultados.count("ok") == 1, resultados
    assert set(resultados) - {"ok"} <= {"AUTHORITY_CEILING_EXCEEDED", "LAST_SECURITY_ADMIN_REQUIRED"}, resultados

    filas_admin = [usuario_id for usuario_id in (A, B) if _filas(mundo, usuario_id, admin_role_id) == 1]
    assert len(filas_admin) == 1


@solo_postgresql
def test_dla_l06_carrera_forzada_entre_comprobacion_y_borrado(mundo, monkeypatch):
    """DLA-L06: aunque las dos renuncias comprueben a la vez, el candado por tenant impide que ambas pasen: una gana y la otra recibe
    LAST_SECURITY_ADMIN_REQUIRED."""
    A, B, admin_role_id = _dos_admins_unicos(mundo)
    original = authority.check_last_security_admin
    ambos = threading.Barrier(2, timeout=2)

    def comprobar_y_esperar(*args, **kwargs):
        original(*args, **kwargs)
        # Con el candado, el otro hilo está bloqueado antes de comprobar; la barrera vence a los 2 s y este sigue; sin candado, los dos comprueban antes de borrar.
        try:
            ambos.wait()
        except threading.BrokenBarrierError:
            pass

    monkeypatch.setattr(authority, "check_last_security_admin", comprobar_y_esperar)

    resultados = _en_hilos(lambda: _quitar_por_servicio(mundo, A, A, admin_role_id), lambda: _quitar_por_servicio(mundo, B, B, admin_role_id))
    assert sorted(resultados) == ["LAST_SECURITY_ADMIN_REQUIRED", "ok"], resultados

    filas_admin = [usuario_id for usuario_id in (A, B) if _filas(mundo, usuario_id, admin_role_id) == 1]
    assert len(filas_admin) == 1
