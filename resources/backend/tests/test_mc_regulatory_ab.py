"""Regulatorio con dos empresas del mismo tenant (ARCH-MC-001, N5).

Aquí no se toca ninguna capacidad SICA, SIGESAI ni SACS: solo se comprueba de
quién es cada permiso, vehículo y documento oficial. Un permiso es una
autorización nominal —la tiene una empresa concreta ante un organismo concreto—
y prestarlo a otra empresa del grupo es exactamente lo que la autoridad no
permite.
"""

from __future__ import annotations

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


def _autoridad(mundo, usuario, empresa, code):
    return mundo.crear("/regulatory/authorities", usuario, empresa,
                       {"code": code, "name": f"Autoridad {code}"})


def _tipo(mundo, usuario, empresa, code, autoridad):
    return mundo.crear("/regulatory/permit-types", usuario, empresa,
                       {"authority_id": autoridad, "code": code, "name": f"Tipo {code}"})


def _permiso(mundo, usuario, empresa, marca):
    aut = _autoridad(mundo, usuario, empresa, f"AUT-{marca}")
    tipo = _tipo(mundo, usuario, empresa, f"TP-{marca}", aut)
    return aut, tipo, mundo.crear("/regulatory/permits", usuario, empresa,
                                  {"permit_type_id": tipo, "number": f"PRM-{marca}"})


# --------------------------------------------------------------- permisos
def test_los_permisos_guardan_su_empresa(mundo):
    _, _, pa = _permiso(mundo, "ua", mundo.company_a, "A1")
    _, _, pb = _permiso(mundo, "ub", mundo.company_b, "B1")
    assert mundo.dueño("permit_instances", pa) == mundo.company_a
    assert mundo.dueño("permit_instances", pb) == mundo.company_b
    assert mundo.dueño("permit_instances", pa) != mundo.t1


def test_cada_empresa_lista_solo_sus_permisos(mundo):
    _permiso(mundo, "ua", mundo.company_a, "A2")
    _permiso(mundo, "ub", mundo.company_b, "B2")
    de_a = {p["id"] for p in mundo.get("/regulatory/permits", "ua", mundo.company_a).json()["items"]}
    de_b = {p["id"] for p in mundo.get("/regulatory/permits", "ub", mundo.company_b).json()["items"]}
    assert de_a and de_b and not (de_a & de_b)


def test_el_permiso_de_b_no_se_transiciona_desde_a(mundo):
    _, _, pb = _permiso(mundo, "ub", mundo.company_b, "B3")
    r = mundo.post(f"/regulatory/permits/{pb}/transition", "ua", mundo.company_a,
                   {"target": "SUSPENDED"})
    assert r.status_code == 404, f"A cambió el estado de un permiso de B: {r.text}"


def test_no_se_emite_un_permiso_con_un_tipo_de_otra_empresa(mundo):
    """§73: la relación tiene que ser de la misma empresa.

    Un tipo de permiso pertenece a la homologación que una empresa hizo ante una
    autoridad. Usarlo desde otra empresa produciría un permiso que en el registro
    del organismo no existe.
    """
    aut_b = _autoridad(mundo, "ub", mundo.company_b, "AUT-CRZ")
    tipo_b = _tipo(mundo, "ub", mundo.company_b, "TP-CRZ", aut_b)
    r = mundo.post("/regulatory/permits", "ua", mundo.company_a,
                   {"permit_type_id": tipo_b, "number": "PRM-CRUZADO"})
    assert r.status_code == 404, f"A emitió un permiso con el tipo de B: {r.text}"


def test_no_se_homologa_un_tipo_contra_la_autoridad_de_otra_empresa(mundo):
    aut_b = _autoridad(mundo, "ub", mundo.company_b, "AUT-CRZ2")
    r = mundo.post("/regulatory/permit-types", "ua", mundo.company_a,
                   {"authority_id": aut_b, "code": "TP-CRZ2", "name": "Cruzado"})
    assert r.status_code == 404, f"A homologó contra la autoridad de B: {r.text}"


# --------------------------------------------------------------- flota
def test_los_vehiculos_y_conductores_no_se_mezclan(mundo):
    va = mundo.crear("/regulatory/vehicles", "ua", mundo.company_a,
                     {"plate": "AA-001AA", "vehicle_type": "CAMION"})
    vb = mundo.crear("/regulatory/vehicles", "ub", mundo.company_b,
                     {"plate": "BB-001BB", "vehicle_type": "CAMION"})
    assert mundo.dueño("transport_vehicles", va) == mundo.company_a
    assert mundo.dueño("transport_vehicles", vb) == mundo.company_b

    de_a = {v["id"] for v in mundo.get("/regulatory/vehicles", "ua", mundo.company_a).json()["items"]}
    assert va in de_a and vb not in de_a


def test_no_se_despacha_con_el_vehiculo_de_otra_empresa(mundo):
    vb = mundo.crear("/regulatory/vehicles", "ub", mundo.company_b,
                     {"plate": "BB-002BB", "vehicle_type": "CAMION"})
    aut = _autoridad(mundo, "ua", mundo.company_a, "AUT-VEH")
    tipo = _tipo(mundo, "ua", mundo.company_a, "TP-VEH", aut)
    r = mundo.post("/regulatory/permits", "ua", mundo.company_a,
                   {"permit_type_id": tipo, "number": "PRM-VEH", "vehicle_id": vb})
    assert r.status_code == 404, f"el permiso de A salió con el vehículo de B: {r.text}"


# --------------------------------------------------------------- documentos
def test_los_documentos_oficiales_no_se_mezclan(mundo):
    da = mundo.crear("/regulatory/official-documents", "ua", mundo.company_a,
                     {"kind": "SICA", "number": "SICA-A-1"})
    db_ = mundo.crear("/regulatory/official-documents", "ub", mundo.company_b,
                      {"kind": "SICA", "number": "SICA-B-1"})
    assert mundo.dueño("official_documents", da) == mundo.company_a
    assert mundo.dueño("official_documents", db_) == mundo.company_b

    de_a = {d["id"] for d in mundo.get("/regulatory/official-documents", "ua", mundo.company_a).json()["items"]}
    assert da in de_a and db_ not in de_a


# --------------------------------------------------------------- otro tenant
def test_el_otro_tenant_no_ve_lo_regulatorio_de_t1(mundo):
    _permiso(mundo, "ua", mundo.company_a, "T1")
    assert mundo.get("/regulatory/permits", "uc", mundo.company_a, tenant="T2").status_code == 404


# --------------------------------------------------------------- la base
def test_ninguna_fila_regulatoria_pertenece_a_una_empresa_inexistente(mundo):
    tablas = ["regulatory_authorities", "permit_types", "official_registrations",
              "regulatory_profiles", "transport_vehicles", "transport_drivers",
              "permit_instances", "official_documents", "regulatory_evaluations",
              "regulatory_approval_requests", "regulatory_contingencies"]
    db = mundo.factory()
    try:
        for tabla in tablas:
            malas = db.execute(text(
                f"SELECT count(*) FROM {tabla} t WHERE t.company_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = t.company_id)"
            )).scalar_one()
            assert malas == 0, f"{tabla}: {malas} filas sin empresa real"
    finally:
        db.close()
