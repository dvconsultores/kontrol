"""Pruebas de comportamiento final del proceso de ocupación de cargos (ORG-04)."""


pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

from sqlalchemy import select  # noqa: E402

from tests.org04_ayudantes import (  # noqa: E402
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


def _fecha_iso(dia, mes):
    """Formatea una fecha del año actual como ISO."""
    return D(mes, dia).isoformat()


def _get_cargo_detalle(mundo, cargo_id, fecha=None):
    """Obtiene el detalle de un cargo en una fecha dada."""
    params = {"fecha": fecha} if fecha else None
    r = mundo.client.get(
        f"/api/v1{O}/cargos/{cargo_id}",
        headers=mundo.como("ua", mundo.company_a),
        params=params,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _get_asignacion_detalle(mundo, asig_id, fecha=None):
    """Obtiene el detalle de una asignación en una fecha dada."""
    params = {"fecha": fecha} if fecha else None
    r = mundo.client.get(
        f"/api/v1{O}/asignaciones/{asig_id}",
        headers=mundo.como("ua", mundo.company_a),
        params=params,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _crear_cargo_y_acto(mundo, ocupacion, unidad="unidad_raiz", status="VIGENTE"):
    """Crea un cargo nuevo y un acto eficaz asociado."""
    cargo_id = nuevo_cargo(mundo, ocupacion, unidad=unidad, status=status)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    return cargo_id, acto_id


def _asignacion_base(
    mundo,
    ocupacion,
    figura="TITULAR",
    unidad="unidad_raiz",
    funcionario=None,
    **kwargs,
):
    """Crea un cuerpo de asignación con datos básicos."""
    func = funcionario or crear_funcionario(mundo)
    cargo_id = kwargs.pop("cargo_id", None)
    if cargo_id is None:
        cargo_id, acto_id = _crear_cargo_y_acto(mundo, ocupacion, unidad=unidad)
    else:
        acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    return cuerpo(func, cargo_id, acto_id, figura=figura, **kwargs)


def test_org04_f13_segundo_titular_solapado(mundo, gobierno, ocupacion):
    """Segundo titular solapado: activar devuelve 409 GOV_ASSIGNMENT_OVERLAP."""
    cargo_id = nuevo_cargo(mundo, ocupacion)
    # Primer titular activo
    datos1 = cuerpo(crear_funcionario(mundo), cargo_id, acto_eficaz(mundo, ocupacion["cargo_emisor"]))
    activa(mundo, datos1)

    # Segundo titular con mismo cargo, fechas solapadas
    datos2 = cuerpo(
        crear_funcionario(mundo, nombre="Segundo Titular"),
        cargo_id,
        acto_eficaz(mundo, ocupacion["cargo_emisor"]),
    )
    asig2 = crear(mundo, datos2)
    r = accion(mundo, asig2, "activar")

    assert r.status_code == 409
    assert r.json()["code"] == "GOV_ASSIGNMENT_OVERLAP"


def test_org04_f14_titular_sucesivo_tras_finalizar(mundo, gobierno, ocupacion):
    """Titular sucesivo: el primero finaliza D(3,1); el segundo desde D(3,2) activa bien."""
    cargo_id = nuevo_cargo(mundo, ocupacion)

    # Primer titular
    datos1 = cuerpo(
        crear_funcionario(mundo),
        cargo_id,
        acto_eficaz(mundo, ocupacion["cargo_emisor"]),
        hasta=D(3, 1).isoformat(),
    )
    asig1 = activa(mundo, datos1)

    # Finalizar el primero en D(3,1)
    r_fin = accion(
        mundo,
        asig1,
        "finalizar",
        cuerpo={"fecha": D(3, 1).isoformat(), "motivo": "Cumplimiento de período"},
    )
    assert r_fin.status_code == 200

    # Segundo titular desde D(3,2)
    datos2 = cuerpo(
        crear_funcionario(mundo, nombre="Sucesor"),
        cargo_id,
        acto_eficaz(mundo, ocupacion["cargo_emisor"]),
        desde=D(3, 2).isoformat(),
    )
    asig2 = activa(mundo, datos2)
    assert asig2["status"] == "ACTIVO"


def test_org04_f15_encargaduria_sin_hasta_cargo_vacante(mundo, gobierno, ocupacion):
    """Encargaduría sin hasta, cargo sin titular: activa; GET cargos/{id} muestra titular None, ejerce con figura ENCARGADURIA."""
    cargo_id = nuevo_cargo(mundo, ocupacion)

    # Encargaduría sin hasta
    datos = _asignacion_base(
        mundo,
        ocupacion,
        figura="ENCARGADURIA",
        unidad="unidad_raiz",
        cargo_id=cargo_id,
    )
    activa(mundo, datos)

    # Consultar cargo
    detalle = _get_cargo_detalle(mundo, cargo_id, D(2, 5).isoformat())
    assert detalle["titular"] is None
    assert detalle["ejerce"]["figura"] == "ENCARGADURIA"
    assert detalle["vacante"] is False


def test_org04_f16_suplencia_sin_titular_activo(mundo, gobierno, ocupacion):
    """Suplencia sin titular activo: 422 GOV_ASSIGNMENT_INVALID."""
    cargo_suplido = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_suplente = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    # Suplente activo en su cargo
    asig_suplente, _ = titular_activo(mundo, ocupacion, cargo_suplente)

    # Acto de suplencia sin titular activo en cargo_suplido
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(
        asig_suplente["funcionario"],
        cargo_suplido,
        acto,
        figura="SUPLENCIA",
        cargo_origen_id=cargo_suplente,
        hasta=D(2, 10).isoformat(),
    )
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_ASSIGNMENT_INVALID"


def test_org04_f17_suplencia_valida_alternancia(mundo, gobierno, ocupacion):
    """Suplencia válida: alterna ejerce/titular según la fecha."""
    cargo_suplido = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_suplente = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    # Titular activo en cargo_suplido
    asig_titular, _ = titular_activo(mundo, ocupacion, cargo_suplido)

    # Suplente activo en cargo_suplente
    asig_suplente, _ = titular_activo(mundo, ocupacion, cargo_suplente)

    # Acto de suplencia del mismo cargo suplido permitido
    acto = acto_eficaz(mundo, cargo_suplido)
    datos = cuerpo(
        asig_suplente["funcionario"],
        cargo_suplido,
        acto,
        figura="SUPLENCIA",
        cargo_origen_id=cargo_suplente,
        hasta=D(2, 10).isoformat(),
    )
    activa(mundo, datos)

    # En D(2,5): ejerce es el suplente; titular sigue siendo titular
    detalle_cargo = _get_cargo_detalle(mundo, cargo_suplido, D(2, 5).isoformat())
    assert detalle_cargo["ejerce"]["funcionario"]["id"] == asig_suplente["funcionario"]["id"]
    assert detalle_cargo["titular"]["funcionario"]["id"] == asig_titular["funcionario"]["id"]

    detalle_titular = _get_asignacion_detalle(
        mundo, asig_titular["id"], D(2, 5).isoformat()
    )
    assert detalle_titular["ejerce"] is False

    # En D(2,20): ejerce vuelve al titular
    detalle_cargo_20 = _get_cargo_detalle(mundo, cargo_suplido, D(2, 20).isoformat())
    assert detalle_cargo_20["ejerce"]["funcionario"]["id"] == asig_titular["funcionario"]["id"]


def test_org04_f18_suplencia_maxima_autoridad_15_dias_autorizacion(mundo, gobierno, ocupacion):
    """Suplencia máxima autoridad >15 días sin autorización: 422; con autorización pasa a BORRADOR."""
    cargo_suplido = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_suplente = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    # Titular máxima autoridad

    # Crear cargo con competencias de máxima autoridad
    with mundo.factory() as db:
        from app.modules.government.models import (
            GovernmentPosition,
            GovernmentPositionVersion,
        )

        # Actualizar cargo suplido para ser máxima autoridad
        cargo = db.execute(
            select(GovernmentPosition).where(
                GovernmentPosition.id == cargo_suplido,
                GovernmentPosition.company_id == mundo.company_a,
            )
        ).scalar_one()
        cargo.is_max_authority = True
        db.flush()
        db.add(
            GovernmentPositionVersion(
                position_id=cargo.id,
                structure_id=cargo.structure_id,
                company_id=mundo.company_a,
                version=2,
                status="VIGENTE",
                snapshot={"is_max_authority": True},
                reason="Máxima autoridad",
                actor_id=None,
            )
        )
        db.commit()

    # Titular máximo autoridad activo
    asig_titular, _ = titular_activo(mundo, ocupacion, cargo_suplido)

    # Suplente activo
    asig_suplente, _ = titular_activo(mundo, ocupacion, cargo_suplente)

    # Suplencia de más de 15 días sin autorización
    acto = acto_eficaz(mundo, cargo_suplido)
    datos = cuerpo(
        asig_suplente["funcionario"],
        cargo_suplido,
        acto,
        figura="SUPLENCIA",
        cargo_origen_id=cargo_suplente,
        maxima_autoridad=True,
        desde=D(2, 1).isoformat(),
        hasta=D(2, 20).isoformat(),
    )
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_ASSIGNMENT_LIMIT_EXCEEDED"

    # Con autorización
    datos["autorizacion_concejo"] = "Acuerdo del Concejo Municipal N.º 12"
    r2 = post_asignacion(mundo, datos)
    assert r2.status_code == 201
    asig = r2.json()
    assert asig["status"] == "BORRADOR"


def test_org04_f19_suplencia_maxima_autoridad_mas_90_dias(mundo, gobierno, ocupacion):
    """Suplencia máxima autoridad >90 días: 422 GOV_ASSIGNMENT_LIMIT_EXCEEDED incluso con autorización."""
    cargo_suplido = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_suplente = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    # Marcar cargo suplido como máxima autoridad
    with mundo.factory() as db:
        from app.modules.government.models import GovernmentPosition, GovernmentPositionVersion
        cargo = db.execute(
            select(GovernmentPosition).where(
                GovernmentPosition.id == cargo_suplido,
                GovernmentPosition.company_id == mundo.company_a,
            )
        ).scalar_one()
        cargo.is_max_authority = True
        db.flush()
        db.add(
            GovernmentPositionVersion(
                position_id=cargo.id,
                structure_id=cargo.structure_id,
                company_id=mundo.company_a,
                version=2,
                status="VIGENTE",
                snapshot={"is_max_authority": True},
                reason="Máxima autoridad",
                actor_id=None,
            )
        )
        db.commit()

    # Titular y suplente activos
    asig_titular, _ = titular_activo(mundo, ocupacion, cargo_suplido)
    asig_suplente, _ = titular_activo(mundo, ocupacion, cargo_suplente)

    # Suplencia de más de 90 días con autorización
    acto = acto_eficaz(mundo, cargo_suplido)
    datos = cuerpo(
        asig_suplente["funcionario"],
        cargo_suplido,
        acto,
        figura="SUPLENCIA",
        cargo_origen_id=cargo_suplente,
        maxima_autoridad=True,
        desde=D(2, 1).isoformat(),
        hasta=D(6, 1).isoformat(),
        autorizacion_concejo="Acuerdo del Concejo Municipal N.º 12",
    )
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_ASSIGNMENT_LIMIT_EXCEEDED"


def test_org04_f20_comision_de_servicio_30_dias(mundo, gobierno, ocupacion):
    """Comisión de servicio: sin cargo_origen activo 422; con titular activo activa bien."""
    cargo_comision = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_origen = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    # Funcionario sin cargo activo
    funcionario = crear_funcionario(mundo, nombre="Sin Cargo Activo")
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(
        funcionario,
        cargo_comision,
        acto,
        figura="COMISION_SERVICIO",
        cargo_origen_id=cargo_origen,
        desde=D(2, 1).isoformat(),
        hasta=D(3, 2).isoformat(),
    )
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_ASSIGNMENT_INVALID"

    # Hacerlo titular activo de cargo_origen
    asig_origen, _ = titular_activo(mundo, ocupacion, cargo_origen)
    datos2 = cuerpo(
        asig_origen["funcionario"],
        cargo_comision,
        acto,
        figura="COMISION_SERVICIO",
        cargo_origen_id=cargo_origen,
        desde=D(2, 1).isoformat(),
        hasta=D(3, 2).isoformat(),
    )
    asig_comision = activa(mundo, datos2)
    assert asig_comision["status"] == "ACTIVO"


def test_org04_f21_dos_temporales_solapados(mundo, gobierno, ocupacion):
    """Dos temporales solapados: 409 GOV_ASSIGNMENT_OVERLAP."""
    cargo_id = nuevo_cargo(mundo, ocupacion)

    # Primera temporal
    datos1 = cuerpo(
        crear_funcionario(mundo),
        cargo_id,
        acto_eficaz(mundo, ocupacion["cargo_emisor"]),
        desde=D(2, 1).isoformat(),
        hasta=D(2, 10).isoformat(),
    )
    activa(mundo, datos1)

    # Segunda temporal solapada
    datos2 = cuerpo(
        crear_funcionario(mundo, nombre="Temporal 2"),
        cargo_id,
        acto_eficaz(mundo, ocupacion["cargo_emisor"]),
        desde=D(2, 5).isoformat(),
        hasta=D(2, 15).isoformat(),
    )
    asig2 = crear(mundo, datos2)
    r = accion(mundo, asig2, "activar")

    assert r.status_code == 409
    assert r.json()["code"] == "GOV_ASSIGNMENT_OVERLAP"


def test_org04_f22_delegacion_atribuciones_valida(mundo, gobierno, ocupacion):
    """Delegación de atribuciones válida: competencias copian límite, autoridad igual."""
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    # Delegado titular activo en cargo_delegado
    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)

    # Acto del delegante, medio GACETA
    acto = acto_eficaz(mundo, delegante, medio="GACETA")

    # No es necesario crear competencias manualmente; nuevo_cargo ya las crea
    # Las competencias FIRMAR PRESUPUESTO SIN_LIMITE y APROBAR PRESUPUESTO MONTO 1000.00 VES ya existen

    datos = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendirá cuenta mensual ante el delegante.",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )
    asig_delegacion = activa(mundo, datos)

    # Verificar competencias
    assert len(asig_delegacion["competencias"]) == 1
    comp = asig_delegacion["competencias"][0]
    assert comp["accion"] == "APROBAR"
    assert comp["materia"] == "PRESUPUESTO"
    assert comp["tipo_limite"] == "MONTO"
    assert comp["monto"] == "1000.00"
    assert comp["moneda"] == "VES"

    # Autoridad igual a competencias
    assert len(asig_delegacion["autoridad"]) == 1
    assert asig_delegacion["autoridad"][0]["accion"] == "APROBAR"
    assert asig_delegacion["autoridad"][0]["materia"] == "PRESUPUESTO"


def test_org04_f23_delegacion_firma_valida(mundo, gobierno, ocupacion):
    """Delegación de firma válida con FIRMAR PRESUPUESTO."""
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="GACETA")

    # No es necesario crear competencias manualmente; nuevo_cargo ya las crea
    # La competencia FIRMAR PRESUPUESTO SIN_LIMITE ya existe

    datos = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_FIRMA",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendición de firma.",
        declara_delegable=True,
        competencias=[{"accion": "FIRMAR", "materia": "PRESUPUESTO"}],
    )
    asig_firma = activa(mundo, datos)
    assert asig_firma["status"] == "ACTIVO"
    assert asig_firma["competencias"][0]["accion"] == "FIRMAR"


def test_org04_f24_firma_con_aprobar_y_atribuciones_con_firmar_no_delegable(mundo, gobierno, ocupacion):
    """Firma con APROBAR: 422; Atribuciones con FIRMAR: 422 GOV_ASSIGNMENT_NOT_DELEGABLE."""
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="GACETA")

    # Competencia requerida no delegable para firma
    datos1 = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_FIRMA",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendición.",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )
    r1 = post_asignacion(mundo, datos1)
    assert r1.status_code == 422
    assert r1.json()["code"] == "GOV_ASSIGNMENT_NOT_DELEGABLE"

    # Atribuciones con FIRMAR
    datos2 = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendición.",
        declara_delegable=True,
        competencias=[{"accion": "FIRMAR", "materia": "PRESUPUESTO"}],
    )
    r2 = post_asignacion(mundo, datos2)
    assert r2.status_code == 422
    assert r2.json()["code"] == "GOV_ASSIGNMENT_NOT_DELEGABLE"


def test_org04_f25_competencia_no_disponible_en_cargo(mundo, gobierno, ocupacion):
    """Competencia PAGAR TESORERIA que el cargo no tiene: 422 GOV_ASSIGNMENT_NOT_DELEGABLE."""
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="GACETA")

    datos = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendición.",
        declara_delegable=True,
        competencias=[{"accion": "PAGAR", "materia": "TESORERIA"}],
    )
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_ASSIGNMENT_NOT_DELEGABLE"


def test_org04_f26_acto_firmado_por_delegacion(mundo, gobierno, ocupacion):
    """Acto con titularidad DELEGACION: 422 GOV_ASSIGNMENT_NOT_DELEGABLE."""
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)

    # Acto con titularidad DELEGACION emitido por el cargo delegante
    acto = acto_eficaz(
        mundo,
        delegante,
        titularidad="DELEGACION",
        medio="GACETA",
    )

    datos = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendición.",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_ASSIGNMENT_NOT_DELEGABLE"


def test_org04_f27_acto_sin_gaceta_medio_personal(mundo, gobierno, ocupacion):
    """Acto sin GACETA (medio PERSONAL): 422 GOV_ASSIGNMENT_ACT_INVALID."""
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="PERSONAL")

    datos = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendición.",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_ASSIGNMENT_ACT_INVALID"


def test_org04_f28_acto_de_otro_cargo_como_emisor(mundo, gobierno, ocupacion):
    """Acto de otro cargo como emisor: 422 GOV_ASSIGNMENT_ISSUER_INVALID."""
    cargo_delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    cargo_otro = nuevo_cargo(mundo, ocupacion, unidad="unidad_otra")

    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    # Acto emitido por un cargo distinto del delegante
    acto = acto_eficaz(mundo, cargo_otro, medio="GACETA")

    datos = cuerpo(
        asig_d["funcionario"],
        cargo_delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendición.",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_ASSIGNMENT_ISSUER_INVALID"


def test_org04_f29_delegado_en_otra_rama(mundo, gobierno, ocupacion):
    """Delegado en otra rama (unidad_otra): 422 GOV_ASSIGNMENT_INVALID."""
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_otra")

    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="GACETA")

    datos = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendición.",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_ASSIGNMENT_INVALID"
