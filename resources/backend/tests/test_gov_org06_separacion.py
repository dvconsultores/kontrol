import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentPosition
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio
from tests.org04_ayudantes import post_asignacion
from tests.org06_ayudantes import D, I, accion, accion_vinculo, activa, acto_eficaz, consultar, crear_funcionario, crear_vinculo, cuenta, cuerpo, cuerpo_vinculo, nuevo_cargo, post_vinculo, titular_activo, vinculo_activo
from tests.org06_guarda import acto_borrador, contexto_de, cuenta_con_permisos, emitir, exigir_identidad, rol_de
from tests.test_gov_ctl01_reglas import cerrar_regla, regla_vigente
from tests.test_gov_ctl06_hallazgos import _post

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

PERMISOS_ACTOS = [("gobierno_actos", "view"), ("gobierno_actos", "edit"), ("gobierno_actos", "issue")]
PERMISOS_OCUPACION = [("gobierno_ocupacion", "view"), ("gobierno_ocupacion", "manage"), ("gobierno_ocupacion", "activate")]
PERMISOS_IDENTIDAD = [("gobierno_identidad", "view"), ("gobierno_identidad", "activate")]
MOTIVO_CIERRE = {"motivo": "Cierre del vínculo de prueba."}

def clasificar(mundo, nombre, categoria):
    return _post(mundo, f"{I}/categorias", "ua", mundo.company_a, {"role_id": rol_de(mundo, nombre), "categoria": categoria, "desde": D(1, 1).isoformat(), "motivo": "Clasificación del rol de prueba."})

def regla_categorias(mundo, a, b):
    return regla_vigente(mundo, proceso="ORG-06", accion_a=f"ORG06_CAT_{a}", accion_b=f"ORG06_CAT_{b}", bidireccional=True, nombre=f"Incompatibilidad {a} {b}")

def eventos(mundo, accion_auditada, entidad):
    with mundo.factory() as session:
        return list(session.scalars(select(AuditEvent).where(AuditEvent.action == accion_auditada, AuditEvent.entity_id == entidad)).all())

def acto_de(mundo, cargo_id, usuario):
    datos = {"tipo": "RESOLUCION", "numero": f"ORG06-{uuid.uuid4().hex[:10]}", "fecha": hoy_de_negocio().isoformat(), "lugar": "Naguanagua", "cargo_id": cargo_id, "competencia": {"accion": "APROBAR", "materia": "PRESUPUESTO"}, "fundamento_competencia": "Reglamento interno, art. 12", "funcionario": "Persona de prueba", "titularidad": "TITULAR", "caracter": "INTERNO", "destinatario": None, "asunto": "Asunto de prueba", "hechos": "Hechos de prueba", "fundamentos": "Fundamentos de prueba", "decision": "Decisión de prueba"}
    respuesta = _post(mundo, "/gobierno/actos", usuario, mundo.company_a, datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()

def test_s01_operativo(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_s01")
    r = clasificar(mundo, "org06_s01", "OPERATIVO")
    assert r.status_code == 201, r.text
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, crear_funcionario(mundo)["id"]))
    datos = contexto_de(mundo, vinculo)
    assert datos["categorias"] == ["OPERATIVO"]
    assert datos["conflictos"] == []

def test_s02_aprobador(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_s02")
    r = clasificar(mundo, "org06_s02", "APROBADOR")
    assert r.status_code == 201, r.text
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, crear_funcionario(mundo)["id"]))
    datos = contexto_de(mundo, vinculo)
    assert datos["categorias"] == ["APROBADOR"]
    assert datos["conflictos"] == []

def test_s03_operativo_y_aprobador_rechazado(mundo, gobierno, ocupacion):
    regla = regla_categorias(mundo, "OPERATIVO", "APROBADOR")
    try:
        user_id_a = cuenta(mundo, "org06_s03a")
        r1 = clasificar(mundo, "org06_s03a", "OPERATIVO")
        assert r1.status_code == 201, r1.text
        r2 = clasificar(mundo, "org06_s03a", "APROBADOR")
        assert r2.status_code == 201, r2.text
        vinculo = crear_vinculo(mundo, cuerpo_vinculo(user_id_a, crear_funcionario(mundo)["id"]))
        r3 = accion_vinculo(mundo, vinculo, "activar")
        assert r3.status_code == 409, r3.text
        assert r3.json()["code"] == "GOV_SOD_CONFLICT"
        assert len(eventos(mundo, "GOV_SOD_CONFLICT_BLOCKED", regla["id"])) >= 1

        user_id_b = cuenta(mundo, "org06_s03b")
        r4 = clasificar(mundo, "org06_s03b", "OPERATIVO")
        assert r4.status_code == 201, r4.text
        vinculo_activo(mundo, cuerpo_vinculo(user_id_b, crear_funcionario(mundo)["id"]))
        r5 = clasificar(mundo, "org06_s03b", "APROBADOR")
        assert r5.status_code == 409, r5.text
        assert r5.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        cerrar_regla(mundo, regla)

def test_s04_control_interno(mundo, gobierno, ocupacion):
    detalle, cargo = titular_activo(mundo, ocupacion)
    user_id = cuenta_con_permisos(mundo, "org06_s04", PERMISOS_ACTOS)
    r1 = clasificar(mundo, "org06_s04", "OPERATIVO")
    assert r1.status_code == 201, r1.text
    r2 = clasificar(mundo, "org06_s04", "CONTROL_INTERNO")
    assert r2.status_code == 201, r2.text
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, detalle["funcionario"]["id"]))
    ids = [item["vinculo_id"] for item in consultar(mundo, "/conflictos").json()["items"]]
    assert vinculo["id"] not in ids
    regla = regla_categorias(mundo, "OPERATIVO", "CONTROL_INTERNO")
    try:
        ids = [item["vinculo_id"] for item in consultar(mundo, "/conflictos").json()["items"]]
        assert vinculo["id"] in ids
        exigir_identidad(mundo)
        r3 = emitir(mundo, acto_borrador(mundo, cargo), "org06_s04")
        assert r3.status_code == 409, r3.text
        assert r3.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        exigir_identidad(mundo, False)
        cerrar_regla(mundo, regla)

def test_s05_auditoria_configurable(mundo, gobierno, ocupacion):
    user_id_a = cuenta(mundo, "org06_s05a")
    r1 = clasificar(mundo, "org06_s05a", "OPERATIVO")
    assert r1.status_code == 201, r1.text
    r2 = clasificar(mundo, "org06_s05a", "AUDITORIA")
    assert r2.status_code == 201, r2.text
    vinculo_activo(mundo, cuerpo_vinculo(user_id_a, crear_funcionario(mundo)["id"]))

    regla = regla_categorias(mundo, "OPERATIVO", "AUDITORIA")
    cerrada = False
    try:
        user_id_b = cuenta(mundo, "org06_s05b")
        r3 = clasificar(mundo, "org06_s05b", "OPERATIVO")
        assert r3.status_code == 201, r3.text
        r4 = clasificar(mundo, "org06_s05b", "AUDITORIA")
        assert r4.status_code == 201, r4.text
        vb = crear_vinculo(mundo, cuerpo_vinculo(user_id_b, crear_funcionario(mundo)["id"]))
        r5 = accion_vinculo(mundo, vb, "activar")
        assert r5.status_code == 409, r5.text
        assert r5.json()["code"] == "GOV_SOD_CONFLICT"
        cerrar_regla(mundo, regla)
        cerrada = True
        r6 = accion_vinculo(mundo, vb, "activar")
        assert r6.status_code == 200, r6.text
    finally:
        if not cerrada:
            cerrar_regla(mundo, regla)

def test_s06_administracion_tecnica(mundo, gobierno, ocupacion):
    cuenta_con_permisos(mundo, "org06_s06", PERMISOS_ACTOS)
    r1 = clasificar(mundo, "org06_s06", "ADMINISTRACION_TECNICA")
    assert r1.status_code == 201, r1.text
    r2 = consultar(mundo, "/mi-contexto", usuario="org06_s06")
    assert r2.status_code == 200, r2.text
    datos = r2.json()
    assert datos["tiene_autoridad"] is False
    assert datos["motivo_sin_autoridad"] == "SIN_VINCULO"
    assert "ADMINISTRACION_TECNICA" in datos["categorias"]
    _, cargo = titular_activo(mundo, ocupacion)
    exigir_identidad(mundo)
    try:
        r3 = emitir(mundo, acto_borrador(mundo, cargo), "ua")
        assert r3.status_code == 403, r3.text
        assert r3.json()["code"] == "GOV_IDENTITY_LINK_REQUIRED"
    finally:
        exigir_identidad(mundo, False)

def test_s07_autoasignacion(mundo, gobierno, ocupacion):
    with mundo.factory() as session:
        ua_id = session.scalars(select(User.id).where(User.username == "ua")).one()
    r1 = post_vinculo(mundo, cuerpo_vinculo(ua_id, crear_funcionario(mundo)["id"]), usuario="ua")
    assert r1.status_code == 403, r1.text
    assert r1.json()["code"] == "GOV_IDENTITY_SELF_LINK"

    idb = cuenta_con_permisos(mundo, "org06_s07b", PERMISOS_IDENTIDAD)
    vb = crear_vinculo(mundo, cuerpo_vinculo(idb, crear_funcionario(mundo)["id"]))
    r2 = accion_vinculo(mundo, vb, "activar", usuario="org06_s07b")
    assert r2.status_code == 403, r2.text
    assert r2.json()["code"] == "GOV_IDENTITY_SELF_LINK"

    idc = cuenta_con_permisos(mundo, "org06_s07c", PERMISOS_OCUPACION)
    fc = crear_funcionario(mundo)
    vinculo_activo(mundo, cuerpo_vinculo(idc, fc["id"]))
    datos = cuerpo(fc, nuevo_cargo(mundo, ocupacion), acto_eficaz(mundo, ocupacion["cargo_emisor"]))
    r3 = post_asignacion(mundo, datos, usuario="org06_s07c")
    assert r3.status_code == 403, r3.text
    assert r3.json()["code"] == "GOV_ASSIGNMENT_SELF_AUTHORITY"
    r4 = post_asignacion(mundo, datos, usuario="ua")
    assert r4.status_code == 201, r4.text
    r5 = accion(mundo, r4.json(), "activar", usuario="org06_s07c")
    assert r5.status_code == 403, r5.text
    assert r5.json()["code"] == "GOV_ASSIGNMENT_SELF_AUTHORITY"

def test_s08_dos_cuentas_mismo_funcionario(mundo, gobierno, ocupacion):
    id1 = cuenta_con_permisos(mundo, "org06_s08a", PERMISOS_OCUPACION)
    id2 = cuenta_con_permisos(mundo, "org06_s08b", PERMISOS_OCUPACION)
    f = crear_funcionario(mundo)
    v1 = vinculo_activo(mundo, cuerpo_vinculo(id1, f["id"]))
    otro = crear_funcionario(mundo)
    datos = cuerpo(otro, nuevo_cargo(mundo, ocupacion), acto_eficaz(mundo, ocupacion["cargo_emisor"]))
    r1 = post_asignacion(mundo, datos, usuario="org06_s08a")
    assert r1.status_code == 201, r1.text
    asig = r1.json()
    r2 = accion_vinculo(mundo, v1, "cerrar", {"fecha": D(3, 1).isoformat(), **MOTIVO_CIERRE})
    assert r2.status_code == 200, r2.text
    vinculo_activo(mundo, cuerpo_vinculo(id2, f["id"], desde=D(3, 2).isoformat()))
    r3 = accion(mundo, asig, "activar", usuario="org06_s08b")
    assert r3.status_code == 403, r3.text
    assert r3.json()["code"] == "GOV_ASSIGNMENT_SELF_ACTIVATION"

def test_s09_sod_por_actor_institucional(mundo, gobierno, ocupacion):
    regla = regla_vigente(mundo, proceso="DOC-02", accion_a="DOC02_REGISTRAR", accion_b="DOC02_EMITIR", nombre="Quien registra no emite")
    try:
        id1 = cuenta_con_permisos(mundo, "org06_s09a", PERMISOS_ACTOS)
        id2 = cuenta_con_permisos(mundo, "org06_s09b", PERMISOS_ACTOS)
        f = crear_funcionario(mundo)
        v1 = vinculo_activo(mundo, cuerpo_vinculo(id1, f["id"]))
        r1 = accion_vinculo(mundo, v1, "cerrar", {"fecha": D(3, 1).isoformat(), **MOTIVO_CIERRE})
        assert r1.status_code == 200, r1.text
        vinculo_activo(mundo, cuerpo_vinculo(id2, f["id"], desde=D(3, 2).isoformat()))
        _, cargo = titular_activo(mundo, ocupacion)
        acto = acto_de(mundo, cargo, "org06_s09a")
        r2 = emitir(mundo, acto, "org06_s09b")
        assert r2.status_code == 409, r2.text
        assert r2.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        cerrar_regla(mundo, regla)

def test_n01_solape(mundo, gobierno, ocupacion):
    user_id_a = cuenta(mundo, "org06_n01a")
    f1 = crear_funcionario(mundo)
    f2 = crear_funcionario(mundo)
    vinculo_activo(mundo, cuerpo_vinculo(user_id_a, f1["id"]))
    v2 = crear_vinculo(mundo, cuerpo_vinculo(user_id_a, f2["id"]))
    r1 = accion_vinculo(mundo, v2, "activar")
    assert r1.status_code == 409, r1.text
    assert r1.json()["code"] == "GOV_IDENTITY_OVERLAP"

    user_id_b = cuenta(mundo, "org06_n01b")
    v3 = crear_vinculo(mundo, cuerpo_vinculo(user_id_b, f1["id"]))
    r2 = accion_vinculo(mundo, v3, "activar")
    assert r2.status_code == 409, r2.text
    assert r2.json()["code"] == "GOV_IDENTITY_OVERLAP"

def test_n02_ocupacion_futura(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    futuro = (hoy_de_negocio() + timedelta(days=10)).isoformat()
    activa(mundo, cuerpo(funcionario, cargo, acto_eficaz(mundo, ocupacion["cargo_emisor"]), desde=futuro))
    user_id = cuenta_con_permisos(mundo, "org06_n02", PERMISOS_ACTOS)
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))
    datos = contexto_de(mundo, vinculo)
    assert datos["ocupaciones"] == []
    assert datos["motivo_sin_autoridad"] == "SIN_OCUPACION"
    exigir_identidad(mundo)
    try:
        r = emitir(mundo, acto_borrador(mundo, cargo), "org06_n02")
        assert r.status_code == 403, r.text
        assert r.json()["code"] == "GOV_FUNCTIONAL_AUTHORITY_REQUIRED"
    finally:
        exigir_identidad(mundo, False)

def test_n03_ocupacion_revocada(mundo, gobierno, ocupacion):
    detalle, cargo = titular_activo(mundo, ocupacion)
    user_id = cuenta_con_permisos(mundo, "org06_n03", PERMISOS_ACTOS)
    vinculo_activo(mundo, cuerpo_vinculo(user_id, detalle["funcionario"]["id"]))
    exigir_identidad(mundo)
    try:
        r1 = emitir(mundo, acto_borrador(mundo, cargo), "org06_n03")
        assert r1.status_code == 200, r1.text
        ayer = (hoy_de_negocio() - timedelta(days=1)).isoformat()
        r2 = accion(mundo, detalle, "revocar", cuerpo={"acto_id": acto_eficaz(mundo, ocupacion["cargo_emisor"]), "fecha": ayer, "motivo": "Revocación de prueba"})
        assert r2.status_code == 200, r2.text
        r3 = emitir(mundo, acto_borrador(mundo, cargo), "org06_n03")
        assert r3.status_code == 403, r3.text
        assert r3.json()["code"] == "GOV_FUNCTIONAL_AUTHORITY_REQUIRED"
    finally:
        exigir_identidad(mundo, False)

def test_n04_cargo_cerrado(mundo, gobierno, ocupacion):
    detalle, cargo = titular_activo(mundo, ocupacion)
    user_id = cuenta(mundo, "org06_n04")
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, detalle["funcionario"]["id"]))
    with mundo.factory() as session:
        pos = session.get(GovernmentPosition, cargo)
        pos.valid_to = hoy_de_negocio() - timedelta(days=1)
        pos.status = "INACTIVO"
        session.commit()
    datos = contexto_de(mundo, vinculo)
    assert datos["ocupaciones"] == []

def test_n05_historia_inmutable(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_n05")
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, crear_funcionario(mundo)["id"]))
    with mundo.factory() as session:
        with pytest.raises(DBAPIError):
            session.execute(text("DELETE FROM gov_user_official_link_history WHERE link_id = :i"), {"i": vinculo["id"]})
        session.rollback()
        with pytest.raises(DBAPIError):
            session.execute(text("UPDATE gov_user_official_links SET desde = desde - 1 WHERE id = :i"), {"i": vinculo["id"]})
        session.rollback()
        with pytest.raises(DBAPIError):
            session.execute(text("DELETE FROM gov_user_official_links WHERE id = :i"), {"i": vinculo["id"]})
        session.rollback()

def test_n06_permisos(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_n06")
    r1 = post_vinculo(mundo, cuerpo_vinculo(user_id, crear_funcionario(mundo)["id"]), usuario="org06_n06")
    assert r1.status_code == 403, r1.text
    assert r1.json()["code"] == "PERMISSION_DENIED"
    r2 = consultar(mundo, "/vinculos", usuario="org06_n06")
    assert r2.status_code == 403, r2.text
    assert r2.json()["code"] == "PERMISSION_DENIED"
    r3 = consultar(mundo, "/mi-contexto", usuario="org06_n06")
    assert r3.status_code == 200, r3.text

def test_n07_auditoria(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_n07")
    vinculo = crear_vinculo(mundo, cuerpo_vinculo(user_id, crear_funcionario(mundo)["id"]))
    r1 = accion_vinculo(mundo, vinculo, "activar")
    assert r1.status_code == 200, r1.text
    filas = eventos(mundo, "GOV_IDENTITY_LINK_ACTIVATED", vinculo["id"])
    assert len(filas) >= 1
    ev = filas[-1]
    assert ev.before["estado"] == "BORRADOR"
    assert ev.after["estado"] == "ACTIVO"
    assert "actor_institucional" in ev.after

def test_c01_categoria_e_historia(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_c01")
    f = crear_funcionario(mundo)
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, f["id"], desde=D(1, 2).isoformat()))
    r1 = clasificar(mundo, "org06_c01", "OPERATIVO")
    assert r1.status_code == 201, r1.text
    cat = r1.json()
    r2 = clasificar(mundo, "org06_c01", "OPERATIVO")
    assert r2.status_code == 409, r2.text
    assert r2.json()["code"] == "GOV_ROLE_CATEGORY_DUPLICATE"
    r3 = _post(mundo, f"{I}/categorias", "ua", mundo.company_a, {"role_id": "00000000-0000-0000-0000-000000000000", "categoria": "OPERATIVO", "desde": D(1, 1).isoformat(), "motivo": "Rol inexistente de prueba."})
    assert r3.status_code == 404, r3.text
    assert r3.json()["code"] == "GOV_ROLE_NOT_FOUND"
    hoy = hoy_de_negocio()
    ruta = f"{I}/categorias/{cat['id']}/retirar"
    body = {"fecha": hoy.isoformat(), "motivo": "Retiro de la categoría de prueba."}
    r4 = _post(mundo, ruta, "ua", mundo.company_a, body)
    assert r4.status_code == 428, r4.text
    assert r4.json()["code"] == "GOV_IDENTITY_IF_MATCH_REQUIRED"
    r5 = _post(mundo, ruta, "ua", mundo.company_a, body, version=99)
    assert r5.status_code == 409, r5.text
    assert r5.json()["code"] == "GOV_IDENTITY_STALE"
    r6 = _post(mundo, ruta, "ua", mundo.company_a, body, version=cat["version"])
    assert r6.status_code == 200, r6.text
    assert r6.json()["status"] == "RETIRADA"
    datos = contexto_de(mundo, vinculo, fecha=hoy)
    assert "OPERATIVO" in datos["categorias"]
    manana = hoy + timedelta(days=1)
    datos = contexto_de(mundo, vinculo, fecha=manana)
    assert "OPERATIVO" not in datos["categorias"]

def test_p01_politica(mundo, gobierno, ocupacion):
    politica = consultar(mundo, "/politica").json()
    ruta = f"{I}/politica"
    datos = {"exige_identidad": True, "motivo": "Activación de la exigencia de prueba."}
    r1 = _post(mundo, ruta, "ua", mundo.company_a, datos)
    assert r1.status_code == 428, r1.text
    assert r1.json()["code"] == "GOV_IDENTITY_IF_MATCH_REQUIRED"
    r2 = _post(mundo, ruta, "ua", mundo.company_a, datos, version=99)
    assert r2.status_code == 409, r2.text
    assert r2.json()["code"] == "GOV_IDENTITY_STALE"
    try:
        r3 = _post(mundo, ruta, "ua", mundo.company_a, datos, version=politica["version"])
        assert r3.status_code == 200, r3.text
        nueva = r3.json()
        assert nueva["exige_identidad"] is True
        assert nueva["version"] > politica["version"]
        assert len(nueva["historia"]) == len(politica["historia"]) + 1
    finally:
        exigir_identidad(mundo, False)
