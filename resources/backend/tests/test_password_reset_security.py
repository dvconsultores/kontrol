import importlib
import json
import os
import stat
import threading
import uuid
from datetime import UTC, timedelta

import pytest
from mfa_apoyo import codigo_totp
from mfa_mundo import (
    API,
    CONTRASENA,
    alta_por_desafio,
    crear_usuario,
    entrar_con_totp,
    login,
    mundo_mfa,
    sesiones_de,
)

from app.core import clock
from app.core.errors import KontrolError
from app.core.security import sha256_hex
from app.modules.audit.models import AuditEvent
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import (
    MfaFactor,
    MfaRecoveryCode,
    PasswordReset,
    User,
)
from app.modules.identity_access.models import (
    Session as AuthSession,
)

pytest_plugins = ("mfa_apoyo",)


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


def _usuario_unico() -> str:
    return f"r_{uuid.uuid4().hex[:10]}"


def _emitir_token(m, user_id, source="SELF"):
    with m.factory() as db:
        user = db.get(User, user_id)
        token = identity_service.issue_password_reset_token(
            db, user=user, source=source, request_id=None
        )
        return token


def test_rst_a01_cuenta_existente_devuelve_202_sin_token(mundo):
    """Solicitud para cuenta existente responde 202 con cuerpo exacto y sin reset_token."""
    m = mundo
    user = _usuario_unico()
    crear_usuario(m, user)
    r = m.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "DEMO", "username": user},
    )
    assert r.status_code == 202
    assert r.json() == {"ok": True}
    assert "reset_token" not in r.text


def test_rst_a02_usuario_inexistente_devuelve_202(mundo):
    """Usuario inexistente responde 202 con el mismo cuerpo que una cuenta existente."""
    m = mundo
    r = m.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "DEMO", "username": _usuario_unico()},
    )
    assert r.status_code == 202
    assert r.json() == {"ok": True}
    assert "reset_token" not in r.text


def test_rst_a03_tenant_inexistente_devuelve_202(mundo):
    """Tenant inexistente responde 202 con el mismo cuerpo."""
    m = mundo
    r = m.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "NO_EXISTE", "username": _usuario_unico()},
    )
    assert r.status_code == 202
    assert r.json() == {"ok": True}
    assert "reset_token" not in r.text


def test_rst_a04_usuario_inactivo_devuelve_202(mundo):
    """Usuario inactivo responde 202 con el mismo cuerpo."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    with m.factory() as db:
        db_user = db.get(User, user_id)
        db_user.status = "INACTIVE"
        db.add(db_user)
        db.commit()
    r = m.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "DEMO", "username": user},
    )
    assert r.status_code == 202
    assert r.json() == {"ok": True}
    assert "reset_token" not in r.text


def test_rst_a05_cabeceras_coinciden_salvo_dinamicas(mundo):
    """Las cabeceras de cuenta existente e inexistente coinciden salvo date, x-request-id y content-length."""
    m = mundo
    user = _usuario_unico()
    crear_usuario(m, user)
    r1 = m.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "DEMO", "username": user},
    )
    r2 = m.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "DEMO", "username": _usuario_unico()},
    )
    ignoradas = {"date", "x-request-id", "content-length"}
    nombres_1 = {k.lower() for k in r1.headers.keys() if k.lower() not in ignoradas}
    nombres_2 = {k.lower() for k in r2.headers.keys() if k.lower() not in ignoradas}
    assert nombres_1 == nombres_2


def test_rst_a06_solicitud_no_crea_filas_y_audita_una_vez(mundo):
    """La solicitud no crea filas de password_resets y audita una sola vez por cuenta existente."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    with m.factory() as db:
        antes = db.query(PasswordReset).count()
        eventos_antes = db.query(AuditEvent).filter_by(action="PASSWORD_RESET_REQUESTED").count()
    m.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "DEMO", "username": user},
    )
    m.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "DEMO", "username": user},
    )
    with m.factory() as db:
        despues = db.query(PasswordReset).count()
        eventos_despues = db.query(AuditEvent).filter_by(action="PASSWORD_RESET_REQUESTED").count()
        solicitados = (
            db.query(AuditEvent)
            .filter_by(action="PASSWORD_RESET_REQUESTED", entity_id=user_id)
            .count()
        )
    assert despues == antes
    assert eventos_despues == eventos_antes + 1
    assert solicitados == 1
    m.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "DEMO", "username": _usuario_unico()},
    )
    with m.factory() as db:
        eventos_final = db.query(AuditEvent).filter_by(action="PASSWORD_RESET_REQUESTED").count()
    assert eventos_final == eventos_despues


def test_rst_b01_token_servicio_confirma_y_cambia_password(mundo):
    """Un token emitido por servicio confirma, permite login con la nueva contraseña y no con la antigua."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    token = _emitir_token(m, user_id)
    r = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert login(m.client, user, tenant="DEMO", contrasena="NuevaClave2026x").status_code == 200
    assert login(m.client, user, tenant="DEMO", contrasena=CONTRASENA).status_code == 401


def test_rst_b02_politica_incumplida_no_consume_token(mundo):
    """Un token no se consume si la nueva contraseña incumple la política."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    token = _emitir_token(m, user_id)
    r = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "corta"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "PASSWORD_POLICY"
    r2 = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    )
    assert r2.status_code == 200


def test_rst_b03_reutilizar_token_consumido_devuelve_used(mundo):
    """Reutilizar un token ya consumido devuelve RESET_TOKEN_USED."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    token = _emitir_token(m, user_id)
    r1 = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    )
    assert r1.status_code == 200
    r2 = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "OtraClave2026xy"},
    )
    assert r2.status_code == 400
    assert r2.json()["code"] == "RESET_TOKEN_USED"


def test_rst_b04_token_alterado_o_aleatorio_devuelve_invalid(mundo):
    """Token alterado o aleatorio devuelve RESET_TOKEN_INVALID."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    token = _emitir_token(m, user_id)
    alterado = token[:-1] + ("0" if token[-1] != "0" else "1")
    r = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": alterado, "new_password": "NuevaClave2026x"},
    )
    assert r.status_code == 400
    assert r.json()["code"] == "RESET_TOKEN_INVALID"
    r2 = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": "token_aleatorio_invalido", "new_password": "NuevaClave2026x"},
    )
    assert r2.status_code == 400
    assert r2.json()["code"] == "RESET_TOKEN_INVALID"


def test_rst_b05_confirmacion_con_campo_extra_devuelve_422(mundo):
    """La confirmación con un campo extra devuelve 422."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    token = _emitir_token(m, user_id)
    r = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x", "user_id": user_id},
    )
    assert r.status_code == 422


@pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="requiere PostgreSQL para concurrencia transaccional",
)
def test_rst_b06_dos_hilos_consumen_atomicamente(mundo):
    """Dos hilos concurrentes consumiendo el mismo token dejan exactamente un éxito y un RESET_TOKEN_USED."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    token = _emitir_token(m, user_id)
    barrier = threading.Barrier(2)
    resultados = []
    lock = threading.Lock()

    def consumir():
        with m.factory() as db:
            barrier.wait()
            try:
                identity_service.confirm_password_reset(
                    db, token=token, new_password="NuevaClave2026x", request_id=None
                )
                resultado = ("ok", None)
            except KontrolError as exc:
                resultado = ("error", exc.code)
            with lock:
                resultados.append(resultado)

    hilos = [threading.Thread(target=consumir) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    estados = sorted([r[0] for r in resultados])
    assert estados == ["error", "ok"]
    errores = [r for r in resultados if r[0] == "error"]
    assert len(errores) == 1
    assert errores[0][1] == "RESET_TOKEN_USED"


def test_rst_b07_emitir_dos_tokens_invalida_el_primero(mundo):
    """Emitir dos tokens para el mismo usuario invalida el primero."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    token1 = _emitir_token(m, user_id)
    token2 = _emitir_token(m, user_id)
    r1 = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token1, "new_password": "NuevaClave2026x"},
    )
    assert r1.status_code == 400
    assert r1.json()["code"] == "RESET_TOKEN_USED"
    r2 = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token2, "new_password": "NuevaClave2026x"},
    )
    assert r2.status_code == 200


def test_rst_b08_caducidad_de_token_con_reloj(mundo, reloj_mfa):
    """Un token emitido caduca a los 15 minutos y no antes de 14."""
    m = mundo
    u1 = _usuario_unico()
    u2 = _usuario_unico()
    id1 = crear_usuario(m, u1)
    id2 = crear_usuario(m, u2)
    token1 = _emitir_token(m, id1)
    token2 = _emitir_token(m, id2)
    reloj_mfa.avanzar(14 * 60)
    r1 = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token1, "new_password": "NuevaClave2026x"},
    )
    assert r1.status_code == 200
    reloj_mfa.avanzar(60 + 1)
    r2 = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token2, "new_password": "OtraClave2026xy"},
    )
    assert r2.status_code == 400
    assert r2.json()["code"] == "RESET_TOKEN_EXPIRED"


def test_rst_b09_fila_almacena_hash_y_no_token_claro(mundo):
    """La fila guarda el hash del token y el token en claro no aparece en ninguna columna."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    antes = clock.now()
    token = _emitir_token(m, user_id)
    despues = clock.now()
    with m.factory() as db:
        fila = db.query(PasswordReset).filter_by(user_id=user_id).first()
        assert fila is not None
        assert fila.token_hash == sha256_hex(token)
        expira = fila.expires_at
        expira = expira if expira.tzinfo else expira.replace(tzinfo=UTC)
        assert (
            antes + timedelta(minutes=15) - timedelta(seconds=2)
            <= expira
            <= despues + timedelta(minutes=15) + timedelta(seconds=2)
        )
        for columna in fila.__table__.columns:
            valor = getattr(fila, columna.name)
            assert token not in str(valor)


def test_rst_b10_token_de_usuario_desactivado_devuelve_invalid(mundo):
    """Un token emitido antes de desactivar al usuario devuelve RESET_TOKEN_INVALID."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    token = _emitir_token(m, user_id)
    with m.factory() as db:
        db_user = db.get(User, user_id)
        db_user.status = "INACTIVE"
        db.add(db_user)
        db.commit()
    r = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    )
    assert r.status_code == 400
    assert r.json()["code"] == "RESET_TOKEN_INVALID"


def test_rst_s01_reset_rechaza_sesion_previa(mundo):
    """Una sesión existente se rechaza tras un reset de contraseña."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    r_login = login(m.client, user, tenant="DEMO", contrasena=CONTRASENA)
    token_bearer = {"Authorization": f"Bearer {r_login.json()['access_token']}"}
    assert m.client.get(f"{API}/auth/mfa", headers=token_bearer).status_code == 200
    token = _emitir_token(m, user_id)
    r = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    )
    assert r.status_code == 200
    assert m.client.get(f"{API}/auth/mfa", headers=token_bearer).status_code == 401


def test_rst_s02_sello_rechaza_sesion_con_revoked_at_nulo(mundo):
    """Una sesión con sello antiguo y revoked_at nulo se rechaza tras el reset."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    r_login = login(m.client, user, tenant="DEMO", contrasena=CONTRASENA)
    token_bearer = {"Authorization": f"Bearer {r_login.json()['access_token']}"}
    assert m.client.get(f"{API}/auth/mfa", headers=token_bearer).status_code == 200
    token = _emitir_token(m, user_id)
    assert m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    ).status_code == 200
    with m.factory() as db:
        sesion = db.query(AuthSession).filter_by(user_id=user_id).first()
        sesion.revoked_at = None
        db.add(sesion)
        db.commit()
    assert m.client.get(f"{API}/auth/mfa", headers=token_bearer).status_code == 401


def test_rst_s03_refresh_con_cookie_previa_se_rechaza(mundo):
    """La renovación con la cookie de una sesión previa al reset se rechaza."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    r_login = login(m.client, user, tenant="DEMO", contrasena=CONTRASENA)
    m.client.cookies.set("kontrol_refresh", r_login.cookies.get("kontrol_refresh"))
    token = _emitir_token(m, user_id)
    assert m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    ).status_code == 200
    r = m.client.post(f"{API}/auth/refresh")
    assert r.status_code == 401


def test_rst_s04_cambio_propio_rota_sesiones_e_invalida_tokens(mundo):
    """El cambio propio mantiene la sesión actual, revoca las demás e invalida tokens de reset."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    r_a = login(m.client, user, tenant="DEMO", contrasena=CONTRASENA)
    r_b = login(m.client, user, tenant="DEMO", contrasena=CONTRASENA)
    bearer_a = {"Authorization": f"Bearer {r_a.json()['access_token']}"}
    bearer_b = {"Authorization": f"Bearer {r_b.json()['access_token']}"}
    token_reset = _emitir_token(m, user_id)
    r = m.client.post(
        f"{API}/auth/change-password",
        headers=bearer_a,
        json={"current_password": CONTRASENA, "new_password": "NuevaClave2026x"},
    )
    assert r.status_code == 200
    assert m.client.get(f"{API}/auth/mfa", headers=bearer_a).status_code == 200
    assert m.client.get(f"{API}/auth/mfa", headers=bearer_b).status_code == 401
    r_token = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token_reset, "new_password": "OtraClave2026xy"},
    )
    assert r_token.status_code == 400
    assert r_token.json()["code"] == "RESET_TOKEN_USED"


def test_rst_m01_reset_no_toca_mfa(mundo, reloj_mfa):
    """El reset no altera el factor MFA ni los códigos de recuperación."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user, admin=True)
    alta = alta_por_desafio(m.client, reloj_mfa, user, tenant="DEMO")
    entrar_con_totp(m.client, reloj_mfa, user, alta.clave_manual)
    with m.factory() as db:
        factor_antes = db.query(MfaFactor).filter_by(user_id=user_id).first()
        factores_antes = db.query(MfaFactor).filter_by(user_id=user_id).count()
        recovery_antes = (
            db.query(MfaRecoveryCode)
            .filter_by(factor_id=factor_antes.id, used_at=None)
            .count()
        )
        usuario_antes = db.get(User, user_id)
        estado_mfa_antes = usuario_antes.mfa_enabled
    token = _emitir_token(m, user_id)
    assert m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    ).status_code == 200
    with m.factory() as db:
        factor_despues = db.query(MfaFactor).filter_by(user_id=user_id).first()
        factores_despues = db.query(MfaFactor).filter_by(user_id=user_id).count()
        recovery_despues = (
            db.query(MfaRecoveryCode)
            .filter_by(factor_id=factor_despues.id, used_at=None)
            .count()
        )
        usuario_despues = db.get(User, user_id)
        estado_mfa_despues = usuario_despues.mfa_enabled
    assert factores_antes == factores_despues
    assert factor_antes.id == factor_despues.id
    assert factor_antes.status == factor_despues.status
    assert recovery_antes == recovery_despues
    assert estado_mfa_antes is True
    assert estado_mfa_despues is True


def test_rst_m02_reset_de_mfa_requiere_segundo_factor(mundo, reloj_mfa):
    """Tras el reset de un usuario MFA, el login con la nueva contraseña exige segundo factor."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user, admin=True)
    alta = alta_por_desafio(m.client, reloj_mfa, user, tenant="DEMO")
    entrar_con_totp(m.client, reloj_mfa, user, alta.clave_manual)
    token = _emitir_token(m, user_id, source="SELF")
    assert m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    ).status_code == 200
    r = login(m.client, user, tenant="DEMO", contrasena="NuevaClave2026x")
    assert r.status_code == 200
    assert r.json()["status"] == "MFA_REQUIRED"
    assert "access_token" not in r.json()


def test_rst_l01_token_no_aparece_en_auditoria_ni_logs(mundo, caplog):
    """El token emitido no aparece en eventos de auditoría ni en logs DEBUG."""
    caplog.set_level("DEBUG")
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    with m.factory() as db:
        ids_antes = {e.id for e in db.query(AuditEvent).all()}
    m.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "DEMO", "username": user},
    )
    token = _emitir_token(m, user_id)
    m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    )
    with m.factory() as db:
        eventos_nuevos = [
            e for e in db.query(AuditEvent).all() if e.id not in ids_antes
        ]
    for evento in eventos_nuevos:
        for campo in evento.__table__.columns:
            assert token not in str(getattr(evento, campo.name))
    assert token not in caplog.text


def test_rst_l02_source_cli_para_emision_cli(mundo, tmp_path):
    """La emisión realizada por la CLI guarda source CLI en password_resets."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    modulo_cli = importlib.import_module("app.modules.identity_access.password_breakglass")
    salida = tmp_path / "salida_cli.txt"
    codigo = modulo_cli.main(
        [
            "--tenant",
            "DEMO",
            "--username",
            user,
            "--confirm",
            user,
            "--salida",
            str(salida),
        ]
    )
    assert codigo == 0
    with m.factory() as db:
        fila = db.query(PasswordReset).filter_by(user_id=user_id).first()
        assert fila is not None
        assert fila.source == "CLI"


def test_rst_cli01_confirm_distinto_no_genera_salida_ni_filas(mundo, tmp_path):
    """La CLI con --confirm distinto devuelve código distinto de cero y no genera fichero ni filas."""
    m = mundo
    user = _usuario_unico()
    crear_usuario(m, user)
    modulo_cli = importlib.import_module("app.modules.identity_access.password_breakglass")
    with m.factory() as db:
        antes = db.query(PasswordReset).count()
    ruta = tmp_path / "no_debe_existir.txt"
    codigo = modulo_cli.main(
        [
            "--tenant",
            "DEMO",
            "--username",
            user,
            "--confirm",
            "otra_cosa",
            "--salida",
            str(ruta),
        ]
    )
    assert codigo != 0
    assert not ruta.exists()
    with m.factory() as db:
        despues = db.query(PasswordReset).count()
    assert despues == antes


def test_rst_cli02_exito_genera_fichero_permisos_y_audita(mundo, capsys, tmp_path):
    """La CLI exitosa escribe solo el token con permisos 600, no lo imprime y audita."""
    m = mundo
    user = _usuario_unico()
    crear_usuario(m, user)
    modulo_cli = importlib.import_module("app.modules.identity_access.password_breakglass")
    ruta = tmp_path / "token_cli.txt"
    codigo = modulo_cli.main(
        [
            "--tenant",
            "DEMO",
            "--username",
            user,
            "--confirm",
            user,
            "--salida",
            str(ruta),
        ]
    )
    assert codigo == 0
    assert ruta.exists()
    contenido = ruta.read_text(encoding="utf-8")
    assert contenido.strip() == contenido
    assert "\n" not in contenido
    assert " " not in contenido
    assert stat.S_IMODE(ruta.stat().st_mode) == 0o600
    captura = capsys.readouterr()
    assert contenido not in captura.out
    assert contenido not in captura.err
    r = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": contenido, "new_password": "NuevaClave2026x"},
    )
    assert r.status_code == 200
    with m.factory() as db:
        assert db.query(AuditEvent).filter_by(action="PASSWORD_RESET_ADMIN_INITIATED").count() >= 1
    codigo2 = modulo_cli.main(
        [
            "--tenant",
            "DEMO",
            "--username",
            user,
            "--confirm",
            user,
            "--salida",
            str(ruta),
        ]
    )
    assert codigo2 != 0


def test_rst_cli03_tenant_distinto_falla(mundo, tmp_path):
    """La CLI falla si el tenant no coincide con el del usuario."""
    m = mundo
    user = _usuario_unico()
    crear_usuario(m, user)
    modulo_cli = importlib.import_module("app.modules.identity_access.password_breakglass")
    with m.factory() as db:
        antes = db.query(PasswordReset).count()
    ruta = tmp_path / "no_debe_existir_tenant.txt"
    codigo = modulo_cli.main(
        [
            "--tenant",
            "DEMO2",
            "--username",
            user,
            "--confirm",
            user,
            "--salida",
            str(ruta),
        ]
    )
    assert codigo != 0
    assert not ruta.exists()
    with m.factory() as db:
        despues = db.query(PasswordReset).count()
    assert despues == antes


def test_rst_cli04_usuario_inactivo_falla(mundo, tmp_path):
    """La CLI falla si el usuario está inactivo."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    with m.factory() as db:
        db_user = db.get(User, user_id)
        db_user.status = "INACTIVE"
        db.add(db_user)
        db.commit()
    modulo_cli = importlib.import_module("app.modules.identity_access.password_breakglass")
    with m.factory() as db:
        antes = db.query(PasswordReset).count()
    ruta = tmp_path / "no_debe_existir_inactivo.txt"
    codigo = modulo_cli.main(
        [
            "--tenant",
            "DEMO",
            "--username",
            user,
            "--confirm",
            user,
            "--salida",
            str(ruta),
        ]
    )
    assert codigo != 0
    assert not ruta.exists()
    with m.factory() as db:
        despues = db.query(PasswordReset).count()
    assert despues == antes


def test_rst_oas01_openapi_202_sin_reset_token(mundo):
    """La especificación OpenAPI declara 202, no 200, y no menciona reset_token."""
    m = mundo
    especificacion = m.client.app.openapi()
    ruta = especificacion["paths"]["/api/v1/auth/password-reset/request"]["post"]["responses"]
    assert "202" in ruta
    assert "200" not in ruta
    assert "reset_token" not in json.dumps(especificacion)


def test_rst_s05_el_reset_revoca_las_filas_de_sesion(mundo):
    """El reset de contraseña revoca todas las filas de sesión del usuario."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    login(m.client, user, tenant="DEMO", contrasena=CONTRASENA)
    login(m.client, user, tenant="DEMO", contrasena=CONTRASENA)
    token = _emitir_token(m, user_id)
    r = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    )
    assert r.status_code == 200
    sesiones = sesiones_de(m, user_id)
    assert len(sesiones) >= 2
    assert all(sesion.revoked_at is not None for sesion in sesiones)


def test_rst_s06_la_renovacion_rechaza_una_sesion_con_sello_antiguo(mundo):
    """La renovación rechaza una sesión con sello antiguo aunque revoked_at sea nulo."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    r_login = login(m.client, user, tenant="DEMO", contrasena=CONTRASENA)
    cookie_refresh = r_login.cookies.get("kontrol_refresh")
    token = _emitir_token(m, user_id)
    assert m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    ).status_code == 200
    with m.factory() as db:
        sesiones = db.query(AuthSession).filter_by(user_id=user_id).all()
        assert len(sesiones) >= 1
        for sesion in sesiones:
            sesion.revoked_at = None
            db.add(sesion)
        db.commit()
    m.client.cookies.set("kontrol_refresh", cookie_refresh)
    r = m.client.post(f"{API}/auth/refresh")
    assert r.status_code == 401


def test_rst_b11_la_reutilizacion_queda_auditada_como_usada(mundo):
    """La reutilización de un token de reset queda auditada como fallo USED."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    token = _emitir_token(m, user_id)
    assert m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    ).status_code == 200
    r = m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "OtraClave2026xy"},
    )
    assert r.status_code == 400
    assert r.json()["code"] == "RESET_TOKEN_USED"
    with m.factory() as db:
        evento = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.action == "PASSWORD_RESET_FAILED",
                AuditEvent.entity_id == user_id,
                AuditEvent.reason == "USED",
            )
            .first()
        )
        assert evento is not None


def test_rst_s07_una_sesion_nacida_de_un_desafio_anterior_al_reset_no_vale(mundo, reloj_mfa):
    """Un desafío MFA previo al reset no puede convertirse en una sesión válida."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user, admin=True)
    alta = alta_por_desafio(m.client, reloj_mfa, user)
    r_login = login(m.client, user)
    assert r_login.json()["status"] == "MFA_REQUIRED"
    challenge_token = r_login.json()["challenge_token"]
    token = _emitir_token(m, user_id)
    assert m.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "NuevaClave2026x"},
    ).status_code == 200
    reloj_mfa.siguiente_paso()
    r_verify = m.client.post(
        f"{API}/auth/mfa/verify",
        json={"challenge_token": challenge_token, "code": codigo_totp(alta.clave_manual, reloj_mfa.ahora())},
    )
    if r_verify.status_code == 200:
        bearer = {"Authorization": f"Bearer {r_verify.json()['access_token']}"}
        assert m.client.get(f"{API}/auth/mfa", headers=bearer).status_code == 401
    else:
        assert r_verify.status_code == 401


def test_rst_s08_el_cambio_propio_rota_el_sello(mundo):
    """El cambio propio rota el sello y rechaza una sesión con revoked_at nulo."""
    m = mundo
    user = _usuario_unico()
    user_id = crear_usuario(m, user)
    r_a = login(m.client, user, tenant="DEMO", contrasena=CONTRASENA)
    r_b = login(m.client, user, tenant="DEMO", contrasena=CONTRASENA)
    bearer_a = {"Authorization": f"Bearer {r_a.json()['access_token']}"}
    bearer_b = {"Authorization": f"Bearer {r_b.json()['access_token']}"}
    assert m.client.post(
        f"{API}/auth/change-password",
        headers=bearer_a,
        json={"current_password": CONTRASENA, "new_password": "NuevaClave2026x"},
    ).status_code == 200
    with m.factory() as db:
        sesion = db.query(AuthSession).filter(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.isnot(None),
        ).one()
        sesion.revoked_at = None
        db.add(sesion)
        db.commit()
    assert m.client.get(f"{API}/auth/mfa", headers=bearer_b).status_code == 401
    assert m.client.get(f"{API}/auth/mfa", headers=bearer_a).status_code == 200
