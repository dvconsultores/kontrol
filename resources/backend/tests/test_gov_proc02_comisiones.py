from tests.org04_ayudantes import D, acto_eficaz, crear_funcionario
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_ctl01_reglas import cerrar_regla, regla_vigente
from tests.test_gov_ctl06_hallazgos import _post

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

C = "/gobierno/contrataciones/comisiones"


def _comision(mundo, ocupacion, **cambios):
    cuerpo = {
        "nombre": "Comisión permanente de prueba",
        "tipo": "PERMANENTE",
        "desde": D(1, 10).isoformat(),
        "hasta": None,
        "objeto": None,
        "acto_id": acto_eficaz(mundo, ocupacion["cargo_emisor"], medio="GACETA"),
    }
    cuerpo.update(cambios)
    r = _post(mundo, C, "ua", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _miembro(mundo, comision, datos):
    r = _post(
        mundo,
        f"{C}/{comision['id']}/miembros",
        "ua",
        mundo.company_a,
        datos,
        version=comision["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()


def _patch_comision(mundo, comision, cambios):
    cuerpo = {
        "nombre": comision["nombre"],
        "tipo": comision["tipo"],
        "objeto": comision["objeto"],
        "desde": comision["desde"],
        "hasta": comision["hasta"],
        "acto_id": (comision["acto"] or {}).get("id"),
    }
    cuerpo.update(cambios)
    r = mundo.client.patch(
        f"/api/v1{C}/{comision['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(comision["version"])},
        json=cuerpo,
    )
    return r


def _completa(mundo, ocupacion):
    comision = _comision(mundo, ocupacion)
    areas = [
        ("TECNICA", "PRINCIPAL"),
        ("JURIDICA", "PRINCIPAL"),
        ("ECONOMICO_FINANCIERA", "PRINCIPAL"),
        ("TECNICA", "SUPLENTE"),
        ("JURIDICA", "SUPLENTE"),
        ("ECONOMICO_FINANCIERA", "SUPLENTE"),
        ("SECRETARIO", "PRINCIPAL"),
        ("SECRETARIO", "SUPLENTE"),
    ]
    ids_principales = {}
    for area, calidad in areas:
        funcionario = crear_funcionario(mundo, usuario="ua")
        if area == "SECRETARIO":
            datos_miembro = {
                "funcionario_id": funcionario["id"],
                "funcion": "SECRETARIO",
                "area": None,
                "condicion": calidad,
                "suplente_de_id": None,
                "certificacion_snc": None,
                "desde": None,
                "acto_id": None,
            }
        elif calidad == "PRINCIPAL":
            datos_miembro = {
                "funcionario_id": funcionario["id"],
                "funcion": "MIEMBRO",
                "area": area,
                "condicion": "PRINCIPAL",
                "suplente_de_id": None,
                "certificacion_snc": None,
                "desde": None,
                "acto_id": None,
            }
        else:
            datos_miembro = {
                "funcionario_id": funcionario["id"],
                "funcion": "MIEMBRO",
                "area": None,
                "condicion": "SUPLENTE",
                "suplente_de_id": ids_principales[area],
                "certificacion_snc": None,
                "desde": None,
                "acto_id": None,
            }
        detalle = _miembro(mundo, comision, datos_miembro)
        if calidad == "PRINCIPAL" and area != "SECRETARIO":
            fila = next(
                m for m in detalle["miembros"]
                if m["funcionario"]["id"] == funcionario["id"]
            )
            ids_principales[area] = fila["id"]
        comision = detalle
    return comision


def _activar(mundo, comision, usuario="uab"):
    return _post(
        mundo,
        f"{C}/{comision['id']}/activar",
        usuario,
        mundo.company_a,
        {},
        version=comision["version"],
    )


def test_flujo_completo(mundo, gobierno, ocupacion):
    comision = _completa(mundo, ocupacion)
    r = _activar(mundo, comision)
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert detalle["status"] == "VIGENTE"
    assert detalle["situacion"] == "EN_VIGOR"
    assert detalle["regla_version"] == "LCP-2014+RLCP-2009"
    comision = detalle

    r = mundo.client.get(f"/api/v1{C}", headers=mundo.como("ua", mundo.company_a))
    assert r.status_code == 200, r.text
    lista = r.json()
    assert any(item["id"] == detalle["id"] for item in lista["items"])
    item = next(item for item in lista["items"] if item["id"] == detalle["id"])
    assert item["miembros_principales"] == 3
    assert item["miembros_total"] == 8

    miembro = detalle["miembros"][0]
    datos_inhibicion = {
        "miembro_id": miembro["id"],
        "asunto": "Contrato objeto de la comisión",
        "causal": "INTERES",
        "descripcion": "Tiene interés directo en el contrato evaluado",
        "fecha": D(1, 11).isoformat(),
        "soporte": None,
    }
    r = _post(
        mundo,
        f"{C}/{comision['id']}/inhibiciones",
        "ua",
        mundo.company_a,
        datos_inhibicion,
    )
    assert r.status_code == 200, r.text
    detalle_con_inhibicion = r.json()
    comision = detalle_con_inhibicion
    inhibicion = detalle_con_inhibicion["inhibiciones"][0]
    inhibicion_id = inhibicion["id"]

    r = _post(
        mundo,
        f"{C}/{comision['id']}/inhibiciones/{inhibicion_id}/resolver",
        "uab",
        mundo.company_a,
        {"decision": "ACEPTADA", "motivo": "Se acepta la inhibición declarada"},
        version=inhibicion["version"],
    )
    assert r.status_code == 200, r.text
    final = r.json()
    comision = final
    assert final["inhibiciones"][0]["estado"] == "ACEPTADA"

    historial = final.get("historia", [])
    assert len(historial) > 8


def test_activar_exige_la_ley(mundo, gobierno, ocupacion):
    comision = _comision(mundo, ocupacion)
    funcionario = crear_funcionario(mundo, usuario="ua")
    comision = _miembro(
        mundo,
        comision,
        {
            "funcionario_id": funcionario["id"],
            "funcion": "MIEMBRO",
            "area": "TECNICA",
            "condicion": "PRINCIPAL",
            "suplente_de_id": None,
            "certificacion_snc": None,
            "desde": None,
            "acto_id": None,
        },
    )
    r = _activar(mundo, comision)
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["code"] == "GOV_COMMITTEE_INCOMPLETE"
    faltantes = " ".join(cuerpo.get("details", {}).get("faltantes", []))
    assert "área" in faltantes
    assert "suplente" in faltantes
    assert "secretario" in faltantes

    comision = _completa(mundo, ocupacion)
    acto_personal = acto_eficaz(mundo, ocupacion["cargo_emisor"], medio="PERSONAL")
    r = _patch_comision(mundo, comision, {"acto_id": acto_personal})
    assert r.status_code == 200, r.text
    comision = r.json()
    r = _activar(mundo, comision)
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    faltantes = " ".join(cuerpo.get("details", {}).get("faltantes", []))
    assert "gaceta" in faltantes


def test_quien_registra_no_activa(mundo, gobierno, ocupacion):
    comision = _completa(mundo, ocupacion)
    r = _activar(mundo, comision, usuario="ua")
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "GOV_COMMITTEE_SELF_ACTIVATION"


def test_otro_ente_no_ve_ni_modifica(mundo, gobierno, ocupacion):
    comision = _completa(mundo, ocupacion)
    r = mundo.client.get(
        f"/api/v1{C}/{comision['id']}",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert r.status_code == 404, r.text

    r = _post(
        mundo,
        f"{C}/{comision['id']}/activar",
        "ub",
        mundo.company_b,
        {},
        version=comision["version"],
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_COMMITTEE_NOT_FOUND"


def test_miembro_de_otro_ente(mundo, gobierno, ocupacion):
    comision = _comision(mundo, ocupacion)
    funcionario = crear_funcionario(mundo, usuario="ub", empresa=mundo.company_b)
    r = _post(
        mundo,
        f"{C}/{comision['id']}/miembros",
        "ua",
        mundo.company_a,
        {
            "funcionario_id": funcionario["id"],
            "funcion": "MIEMBRO",
            "area": "TECNICA",
            "condicion": "PRINCIPAL",
            "suplente_de_id": None,
            "certificacion_snc": None,
            "desde": None,
            "acto_id": None,
        },
        version=comision["version"],
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_OFFICIAL_NOT_FOUND"


def test_la_historia_no_cambia(mundo, gobierno, ocupacion):
    comision = _completa(mundo, ocupacion)
    comision = _activar(mundo, comision).json()
    principal = next(
        m for m in comision["miembros"]
        if m["condicion"] == "PRINCIPAL" and m["funcion"] == "MIEMBRO"
    )
    r = _post(
        mundo,
        f"{C}/{comision['id']}/miembros/{principal['id']}/terminar",
        "uab",
        mundo.company_a,
        {
            "fecha": D(3, 1).isoformat(),
            "causa": "RETIRO_RENUNCIA_REMOCION",
            "motivo": "Renuncia presentada por el miembro titular",
        },
        version=comision["version"],
    )
    assert r.status_code == 200, r.text
    comision = r.json()

    r = mundo.client.get(
        f"/api/v1{C}/{comision['id']}?fecha={D(2, 1).isoformat()}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    detalle_antes = r.json()
    assert any(m["id"] == principal["id"] for m in detalle_antes.get("composicion", []))

    r = mundo.client.get(
        f"/api/v1{C}/{comision['id']}?fecha={D(4, 1).isoformat()}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    detalle_despues = r.json()
    assert not any(m["id"] == principal["id"] for m in detalle_despues.get("composicion", []))
    miembro = next(m for m in detalle_despues["miembros"] if m["id"] == principal["id"])
    assert miembro["fin_efectivo"] is not None


def test_sin_capacidad_403(mundo, gobierno, ocupacion):
    cuenta_con_permisos(mundo, "proc02_lector", [("gobierno_comisiones", "view")])
    r = mundo.client.get(f"/api/v1{C}", headers=mundo.como("proc02_lector", mundo.company_a))
    assert r.status_code == 200, r.text
    r = _post(mundo, C, "proc02_lector", mundo.company_a, {})
    assert r.status_code == 403, r.text


def test_sod_entre_activar_y_cerrar(mundo, gobierno, ocupacion):
    regla = regla_vigente(
        mundo, proceso="PROC-02", accion_a="PROC02_ACTIVAR", accion_b="PROC02_CERRAR"
    )
    try:
        comision = _completa(mundo, ocupacion)
        comision = _activar(mundo, comision).json()
        r = _post(
            mundo,
            f"{C}/{comision['id']}/cerrar",
            "uab",
            mundo.company_a,
            {"fecha": D(5, 1).isoformat(), "motivo": "Cierre por finalización del proceso"},
            version=comision["version"],
        )
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        cerrar_regla(mundo, regla)


def test_version_vieja_409(mundo, gobierno, ocupacion):
    comision = _comision(mundo, ocupacion)
    version_inicial = comision["version"]
    cuerpo = {
        "nombre": comision["nombre"],
        "tipo": comision["tipo"],
        "objeto": comision["objeto"],
        "desde": comision["desde"],
        "hasta": comision["hasta"],
        "acto_id": (comision["acto"] or {}).get("id"),
    }
    r = mundo.client.patch(
        f"/api/v1{C}/{comision['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_inicial)},
        json=cuerpo,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.patch(
        f"/api/v1{C}/{comision['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_inicial)},
        json=cuerpo,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_COMMITTEE_STALE"
