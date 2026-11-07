"""Pruebas de acciones del proceso de ocupación de cargos (ORG-04).

Cubren revocación, finalización, aislamiento, permisos, auditoría y exportación.
"""


from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.government import service_sod
from app.modules.government.models import GovernmentAct, GovernmentOfficial
from app.modules.identity_access.models import User

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

from tests.org04_ayudantes import (  # noqa: E402
    ANIO,
    D,
    O,
    accion,
    activa,
    acto_eficaz,
    crear,
    crear_funcionario,
    cuerpo,
    nuevo_cargo,
    post_asignacion,
    titular_activo,
)
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos  # noqa: E402


def _get(mundo, ruta, usuario="ua", empresa=None, params=None):
    if empresa is None:
        empresa = mundo.company_a
    return mundo.client.get(
        f"/api/v1{O}{ruta}",
        headers=mundo.como(usuario, empresa),
        params=params or {},
    )


def test_f30_revocar_actualiza_estado_y_situacion(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo, acto, desde=D(2, 1).isoformat())
    asignacion = activa(mundo, datos)

    respuesta = accion(
        mundo,
        asignacion,
        "revocar",
        cuerpo={"acto_id": acto, "fecha": D(3, 1).isoformat(), "motivo": "Revocación de prueba"},
    )
    assert respuesta.status_code == 200
    detalle = respuesta.json()
    assert detalle["status"] == "REVOCADO"
    assert detalle["fin_efectivo"] == D(3, 1).isoformat()
    assert detalle["acto_revocacion"] is not None

    consulta_antes = _get(
        mundo,
        f"/asignaciones/{detalle['id']}",
        params={"fecha": D(2, 15).isoformat()},
    )
    assert consulta_antes.status_code == 200
    assert consulta_antes.json()["situacion"] == "VIGENTE"

    consulta_despues = _get(
        mundo,
        f"/asignaciones/{detalle['id']}",
        params={"fecha": D(3, 2).isoformat()},
    )
    assert consulta_despues.status_code == 200
    assert consulta_despues.json()["situacion"] == "REVOCADA"


def test_f31_revocar_con_acto_no_eficaz_y_fecha_anterior(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto_base = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(1, 20))
    datos = cuerpo(funcionario, cargo, acto_base, desde=D(1, 20).isoformat())
    asignacion = activa(mundo, datos)

    acto_no_eficaz = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(3, 1), status="EMITIDO")
    respuesta = accion(
        mundo,
        asignacion,
        "revocar",
        cuerpo={"acto_id": acto_no_eficaz, "fecha": D(3, 1).isoformat(), "motivo": "Revocación de prueba"},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "GOV_ASSIGNMENT_ACT_INVALID"

    acto_previo = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(1, 10))
    respuesta_anterior = accion(
        mundo,
        asignacion,
        "revocar",
        cuerpo={"acto_id": acto_previo, "fecha": D(1, 15).isoformat(), "motivo": "Revocación de prueba"},
    )
    assert respuesta_anterior.status_code == 422
    assert respuesta_anterior.json()["code"] == "GOV_ASSIGNMENT_INVALID"

    consulta = _get(mundo, f"/asignaciones/{asignacion['id']}")
    assert consulta.status_code == 200
    assert consulta.json()["status"] == "ACTIVO"


def test_f32_finalizar_y_repetir(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo, acto, desde=D(2, 1).isoformat())
    asignacion = activa(mundo, datos)

    respuesta = accion(
        mundo,
        asignacion,
        "finalizar",
        cuerpo={"fecha": D(3, 1).isoformat(), "motivo": "Finalización de prueba"},
    )
    assert respuesta.status_code == 200
    detalle = respuesta.json()
    assert detalle["status"] == "FINALIZADO"
    assert detalle["motivo_fin"] == "Finalización de prueba"

    respuesta_repetida = accion(
        mundo,
        detalle,
        "finalizar",
        cuerpo={"fecha": D(4, 1).isoformat(), "motivo": "Repetición de la finalización."},
    )
    assert respuesta_repetida.status_code == 409
    assert respuesta_repetida.json()["code"] == "GOV_ASSIGNMENT_INVALID_STATE"


def test_f33_acto_revocado_o_nulo_posterior(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo, acto, desde=D(2, 1).isoformat())
    asignacion = activa(mundo, datos)

    id_revocador = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(3, 1))
    with mundo.factory() as db:
        acto_db = db.execute(
            select(GovernmentAct).where(GovernmentAct.id == acto)
        ).scalar_one()
        acto_db.status = "REVOCADO"
        acto_db.revocado_por_id = id_revocador
        db.commit()

    consulta_sin_efecto = _get(
        mundo,
        f"/asignaciones/{asignacion['id']}",
        params={"fecha": D(3, 2).isoformat()},
    )
    assert consulta_sin_efecto.status_code == 200
    assert consulta_sin_efecto.json()["situacion"] == "SIN_EFECTO"

    consulta_vigente = _get(
        mundo,
        f"/asignaciones/{asignacion['id']}",
        params={"fecha": D(2, 15).isoformat()},
    )
    assert consulta_vigente.status_code == 200
    assert consulta_vigente.json()["situacion"] == "VIGENTE"

    # Segundo caso: acto nulo
    funcionario_2 = crear_funcionario(mundo)
    cargo_2 = nuevo_cargo(mundo, ocupacion)
    acto_2 = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    asignacion_2 = activa(mundo, cuerpo(funcionario_2, cargo_2, acto_2, desde=D(2, 1).isoformat()))

    id_anulador = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(3, 1))
    with mundo.factory() as db:
        acto_db_2 = db.execute(
            select(GovernmentAct).where(GovernmentAct.id == acto_2)
        ).scalar_one()
        acto_db_2.status = "NULO"
        acto_db_2.anulado_por_id = id_anulador
        db.commit()

    consulta_nula = _get(
        mundo,
        f"/asignaciones/{asignacion_2['id']}",
        params={"fecha": D(2, 15).isoformat()},
    )
    assert consulta_nula.status_code == 200
    assert consulta_nula.json()["situacion"] == "SIN_EFECTO"


def test_f34_avocar_sobre_delegacion_y_titular(mundo, gobierno, ocupacion):
    delegante = nuevo_cargo(mundo, ocupacion)
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="GACETA")
    datos_delegacion = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendirá cuenta mensual ante el delegante.",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )
    asignacion_delegada = activa(mundo, datos_delegacion)

    respuesta_avocar = accion(
        mundo,
        asignacion_delegada,
        "avocar",
        cuerpo={"acto_id": acto, "asunto": "Avocación de prueba"},
        usuario="uab",
    )
    assert respuesta_avocar.status_code == 200
    detalle_avocada = respuesta_avocar.json()
    assert detalle_avocada["status"] == "ACTIVO"
    assert len(detalle_avocada["avocaciones"]) > 0

    funcionario = crear_funcionario(mundo)
    cargo_titular = nuevo_cargo(mundo, ocupacion)
    acto_titular = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos_titular = cuerpo(funcionario, cargo_titular, acto_titular)
    asignacion_titular = activa(mundo, datos_titular)

    respuesta_titular = accion(
        mundo,
        asignacion_titular,
        "avocar",
        cuerpo={"acto_id": acto_titular, "asunto": "Avocación sobre titular"},
        usuario="uab",
    )
    assert respuesta_titular.status_code == 422
    assert respuesta_titular.json()["code"] == "GOV_ASSIGNMENT_INVALID"


def test_f35_descartar_borrador_y_activar_despues(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo, acto, desde=D(2, 1).isoformat())
    asignacion = crear(mundo, datos)

    respuesta_descartar = accion(
        mundo,
        asignacion,
        "descartar",
        cuerpo={"motivo": "Descartada en prueba"},
    )
    assert respuesta_descartar.status_code == 200
    assert respuesta_descartar.json()["status"] == "DESCARTADO"

    respuesta_activar = accion(mundo, respuesta_descartar.json(), "activar")
    assert respuesta_activar.status_code == 409
    assert respuesta_activar.json()["code"] == "GOV_ASSIGNMENT_INVALID_STATE"


def test_f36_patch_borrador_y_activa(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo, acto, desde=D(2, 1).isoformat())
    asignacion = crear(mundo, datos)

    respuesta_sin_if_match = mundo.client.patch(
        f"/api/v1{O}/asignaciones/{asignacion['id']}",
        headers=mundo.como("ua", mundo.company_a),
        json=datos,
    )
    assert respuesta_sin_if_match.status_code == 428
    assert respuesta_sin_if_match.json()["code"] == "GOV_ASSIGNMENT_IF_MATCH_REQUIRED"

    respuesta_version_vieja = mundo.client.patch(
        f"/api/v1{O}/asignaciones/{asignacion['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "0"},
        json=datos,
    )
    assert respuesta_version_vieja.status_code == 409
    assert respuesta_version_vieja.json()["code"] == "GOV_ASSIGNMENT_STALE"

    respuesta_valida = mundo.client.patch(
        f"/api/v1{O}/asignaciones/{asignacion['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(asignacion["version"])},
        json=datos,
    )
    assert respuesta_valida.status_code == 200
    detalle_patch = respuesta_valida.json()
    assert detalle_patch["fundamento"] == datos["fundamento"]
    historia = detalle_patch["historia"]
    ultima_historia = historia[-1]
    assert ultima_historia["tipo"] == "EDITADA"
    assert "antes" in ultima_historia["detalle"] and "despues" in ultima_historia["detalle"]

    activada = accion(mundo, detalle_patch, "activar")
    detalle_activada = activada.json()
    respuesta_patch_activa = mundo.client.patch(
        f"/api/v1{O}/asignaciones/{detalle_activada['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(detalle_activada["version"])},
        json=datos,
    )
    assert respuesta_patch_activa.status_code == 409
    assert respuesta_patch_activa.json()["code"] == "GOV_ASSIGNMENT_INVALID_STATE"


def test_f37_aislamiento_entre_empresas(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo_a = nuevo_cargo(mundo, ocupacion)
    acto_a = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(funcionario, cargo_a, acto_a)
    asignacion = crear(mundo, datos)

    respuesta_get_asignacion = _get(
        mundo,
        f"/asignaciones/{asignacion['id']}",
        usuario="ub",
        empresa=mundo.company_b,
    )
    assert respuesta_get_asignacion.status_code == 404

    respuesta_get_funcionario = _get(
        mundo,
        f"/funcionarios/{funcionario['id']}",
        usuario="ub",
        empresa=mundo.company_b,
    )
    assert respuesta_get_funcionario.status_code == 404

    respuesta_get_cargo = _get(
        mundo,
        f"/cargos/{cargo_a}",
        usuario="ub",
        empresa=mundo.company_b,
    )
    assert respuesta_get_cargo.status_code == 404

    datos_b = cuerpo(funcionario, ocupacion["cargo_b"], acto_a)
    respuesta_crear_b = post_asignacion(mundo, datos_b)
    assert respuesta_crear_b.status_code == 404
    assert respuesta_crear_b.json()["code"] == "GOV_ASSIGNMENT_POSITION_NOT_FOUND"

    acto_b = acto_eficaz(mundo, ocupacion["cargo_b"], empresa=mundo.company_b)
    datos_acto_b = cuerpo(funcionario, cargo_a, acto_b)
    respuesta_acto_b = post_asignacion(mundo, datos_acto_b)
    assert respuesta_acto_b.status_code == 404
    assert respuesta_acto_b.json()["code"] == "GOV_ASSIGNMENT_ACT_NOT_FOUND"

    funcionario_b = crear_funcionario(mundo, usuario="ub", empresa=mundo.company_b)
    datos_funcionario_b = cuerpo(funcionario_b, cargo_a, acto_a)
    respuesta_funcionario_b = post_asignacion(mundo, datos_funcionario_b)
    assert respuesta_funcionario_b.status_code == 404
    assert respuesta_funcionario_b.json()["code"] == "GOV_OFFICIAL_NOT_FOUND"


def test_f38_company_id_en_cuerpo_es_rechazado(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(funcionario, cargo, acto)
    datos["company_id"] = mundo.company_a
    respuesta = post_asignacion(mundo, datos)
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "VALIDATION_ERROR"


def test_f39_permisos_lectura_y_creacion(mundo, gobierno, ocupacion):
    _crear_usuario_con_permisos(
        mundo,
        "solo_lectura",
        [("gobierno_ocupacion", "view")],
        mundo.company_a,
    )
    respuesta_lectura = _get(
        mundo,
        "/cargos",
        usuario="solo_lectura",
        params={"ejercicio": ANIO, "fecha": D(2, 1).isoformat()},
    )
    assert respuesta_lectura.status_code == 200

    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(funcionario, cargo, acto)
    respuesta_crear = post_asignacion(mundo, datos, usuario="solo_lectura")
    assert respuesta_crear.status_code == 403

    _crear_usuario_con_permisos(mundo, "sin_permisos", [], mundo.company_a)
    respuesta_sin_permiso = _get(
        mundo,
        "/cargos",
        usuario="sin_permisos",
        params={"ejercicio": ANIO, "fecha": D(2, 1).isoformat()},
    )
    assert respuesta_sin_permiso.status_code == 403


def test_f40_administrador_tecnico_sin_funcional_completo(mundo, gobierno, ocupacion):
    from app.modules.identity_access.authority import TECHNICAL_CAPABILITIES

    for capability in TECHNICAL_CAPABILITIES:
        assert not capability.startswith("gobierno_ocupacion")


def test_f41_mfa_permisos_sensibles_y_estandar(mundo, gobierno, ocupacion):
    from app.modules.identity_access.mfa_policy import SENSITIVE_PERMISSIONS, STANDARD_PERMISSIONS

    assert "gobierno_ocupacion:activate" in SENSITIVE_PERMISSIONS
    assert "gobierno_ocupacion:revoke" in SENSITIVE_PERMISSIONS
    assert "gobierno_ocupacion:view" in STANDARD_PERMISSIONS
    assert "gobierno_ocupacion:manage" in STANDARD_PERMISSIONS


def test_f42_auditoria_activacion_y_revocacion(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo, acto, desde=D(2, 1).isoformat())
    asignacion = activa(mundo, datos)

    with mundo.factory() as db:
        user_uab = db.execute(select(User).where(User.username == "uab")).scalar_one()
        evento_activacion = db.execute(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_ASSIGNMENT_ACTIVATED",
                AuditEvent.entity_id == str(asignacion["id"]),
            )
        ).scalar_one()
        assert evento_activacion.user_id == user_uab.id
        assert evento_activacion.before["status"] == "BORRADOR"
        assert evento_activacion.after["status"] == "ACTIVO"
        assert evento_activacion.after["cargo_id"] == cargo

        acto_revocador = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(3, 1))
        respuesta_revocar = accion(
            mundo,
            asignacion,
            "revocar",
            cuerpo={"acto_id": acto_revocador, "fecha": D(3, 1).isoformat(), "motivo": "Prueba auditoría"},
        )
        assert respuesta_revocar.status_code == 200

        evento_revocacion = db.execute(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_ASSIGNMENT_REVOKED",
                AuditEvent.entity_id == str(asignacion["id"]),
            )
        ).scalar_one()
        assert evento_revocacion.before["status"] == "ACTIVO"
        assert evento_revocacion.after["status"] == "REVOCADO"


def test_f43_historia_creacion_activacion_revocacion(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo, acto, desde=D(2, 1).isoformat())
    asignacion = crear(mundo, datos)

    historia_creada = asignacion["historia"]
    assert any(h["tipo"] == "CREADA" for h in historia_creada)

    activada = accion(mundo, asignacion, "activar")
    detalle_activada = activada.json()
    historia_activada = detalle_activada["historia"]
    assert any(h["tipo"] == "ACTIVADA" for h in historia_activada)
    for h in historia_activada:
        if h["tipo"] == "ACTIVADA":
            assert h["actor"] == "uab"

    acto_revocador = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(3, 1))
    revocada = accion(
        mundo,
        detalle_activada,
        "revocar",
        cuerpo={"acto_id": acto_revocador, "fecha": D(3, 1).isoformat(), "motivo": "Prueba historia"},
    )
    detalle_revocada = revocada.json()
    historia_revocada = detalle_revocada["historia"]
    assert any(h["tipo"] == "REVOCADA" for h in historia_revocada)

    tipos_ordenados = [h["tipo"] for h in historia_revocada if h["tipo"] in ("CREADA", "ACTIVADA", "REVOCADA")]
    assert tipos_ordenados == ["CREADA", "ACTIVADA", "REVOCADA"]


def test_f44_listado_filtra_por_figura_y_fecha(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo, acto, desde=D(2, 1).isoformat(), figura="TITULAR")
    asignacion = activa(mundo, datos)

    respuesta = _get(
        mundo,
        "/asignaciones",
        params={"figura": "TITULAR", "fecha": D(2, 5).isoformat()},
    )
    assert respuesta.status_code == 200
    detalle = respuesta.json()
    assert isinstance(detalle, dict)
    assert "items" in detalle
    ids = [item["id"] for item in detalle["items"]]
    assert asignacion["id"] in ids

    respuesta_otra_figura = _get(
        mundo,
        "/asignaciones",
        params={"figura": "DELEGACION_ATRIBUCIONES", "fecha": D(2, 5).isoformat()},
    )
    assert respuesta_otra_figura.status_code == 200
    ids_otra = [item["id"] for item in respuesta_otra_figura.json()["items"]]
    assert asignacion["id"] not in ids_otra


def test_f45_ocupacion_por_cargo_incluye_titular_y_vacante(mundo, gobierno, ocupacion):
    cargo_con_titular = nuevo_cargo(mundo, ocupacion)
    cargo_vacante = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    funcionario = crear_funcionario(mundo)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo_con_titular, acto, desde=D(2, 1).isoformat())
    activa(mundo, datos)

    respuesta = _get(
        mundo,
        "/cargos",
        params={"ejercicio": ANIO, "fecha": D(2, 5).isoformat()},
    )
    assert respuesta.status_code == 200
    cargos = respuesta.json()["items"]
    cargo_encontrado = next(c for c in cargos if c["cargo"]["id"] == cargo_con_titular)
    assert cargo_encontrado["vacante"] is False
    assert cargo_encontrado["titular"] is not None

    cargo_vacante_encontrado = next(c for c in cargos if c["cargo"]["id"] == cargo_vacante)
    assert cargo_vacante_encontrado["vacante"] is True
    assert cargo_vacante_encontrado["titular"] is None


def test_f46_csv_exportacion_y_auditoria(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo, acto, desde=D(2, 1).isoformat())
    asignacion = activa(mundo, datos)

    with mundo.factory() as db:
        numero = db.execute(
            select(GovernmentOfficial.numero_documento).where(GovernmentOfficial.id == funcionario["id"])
        ).scalar_one()

    respuesta = _get(mundo, "/asignaciones.csv")
    assert respuesta.status_code == 200
    assert "text/csv" in respuesta.headers.get("content-type", "")
    texto = respuesta.text
    assert asignacion["codigo"] in texto
    assert numero not in texto

    with mundo.factory() as db:
        evento = db.execute(
            select(AuditEvent).where(AuditEvent.action == "GOV_ASSIGNMENTS_EXPORTED")
        ).scalar_one_or_none()
        assert evento is not None


def test_f47_catalogo_y_opciones(mundo, gobierno, ocupacion):
    respuesta_catalogo = _get(mundo, "/catalogo")
    assert respuesta_catalogo.status_code == 200
    catalogo = respuesta_catalogo.json()
    assert len(catalogo["figuras"]) == 6
    for figura in catalogo["figuras"]:
        assert figura["base_legal"]

    codigos = [i["codigo"] for i in catalogo["instrumentos"]]
    assert "DECRETO" in codigos
    assert "RESOLUCION" in codigos

    respuesta_opciones = _get(mundo, "/opciones", params={"ejercicio": ANIO})
    assert respuesta_opciones.status_code == 200
    opciones = respuesta_opciones.json()
    assert "funcionarios" in opciones


def test_f48_pii_no_expone_documento_completo(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo)
    cargo = nuevo_cargo(mundo, ocupacion)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(2, 1))
    datos = cuerpo(funcionario, cargo, acto, desde=D(2, 1).isoformat())
    asignacion = activa(mundo, datos)

    with mundo.factory() as db:
        numero = db.execute(
            select(GovernmentOfficial.numero_documento).where(GovernmentOfficial.id == funcionario["id"])
        ).scalar_one()

    respuesta_detalle = _get(mundo, f"/asignaciones/{asignacion['id']}")
    assert respuesta_detalle.status_code == 200
    assert numero not in respuesta_detalle.text
    assert funcionario["documento"] in respuesta_detalle.text

    respuesta_listado = _get(mundo, "/asignaciones")
    assert respuesta_listado.status_code == 200
    assert numero not in respuesta_listado.text

    respuesta_funcionario = _get(mundo, f"/funcionarios/{funcionario['id']}")
    assert respuesta_funcionario.status_code == 200
    assert numero not in respuesta_funcionario.text


def test_f49_sod_incluye_org04_activar(mundo, gobierno, ocupacion):
    acciones = service_sod.CATALOGO_SOD["ORG-04"]["acciones"]
    assert "ORG04_ACTIVAR" in acciones
