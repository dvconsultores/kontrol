# ruff: noqa: E402, F811, F401, I001
import copy
import os
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.modules.government.service_comision_regla import (
    REGLA_LEGADO,
    evaluar_decision,
    evaluar_quorum,
    umbral,
)

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

from tests.org04_ayudantes import D, acto_eficaz, crear_funcionario, titular_activo
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_ctl06_hallazgos import _post

P = "/gobierno/contrataciones/politicas-comision"
_CLAVES_REQUISITO_ENTRADA = (
    "etiqueta", "funcion", "condicion", "tipo", "area", "position_id", "unit_id",
    "competencia_accion", "competencia_materia", "official_id", "minimo", "maximo",
)
C = "/gobierno/contrataciones/comisiones"


def _politica(mundo, **cambios):
    """Crea y activa una política BORRADOR → VIGENTE con base LCP_ART14."""
    codigo = f"POL-{uuid.uuid4().hex[:6]}"
    cuerpo = {
        "codigo": codigo,
        "nombre": f"Política {codigo}",
        "base_normativa": "LCP_ART14",
        "fundamento": "Fundamento legal y técnico de la política de comisiones",
        "vigente_desde": D(1, 1).isoformat(),
        "min_principales": 3,
        "max_principales": 5,
        "exige_impar": True,
        "suplente_por_principal": True,
        "exige_secretario": True,
        "exige_suplente_secretario": True,
        "quorum": {"tipo": "SIMPLE_MAJORITY"},
        "decision": {"tipo": "SIMPLE_MAJORITY", "base": "ASISTENTES_CON_VOTO"},
        "requisitos": [
            {
                "etiqueta": "Principal técnico",
                "funcion": "MIEMBRO",
                "condicion": "PRINCIPAL",
                "tipo": "AREA",
                "area": "TECNICA",
                "minimo": 1,
            }
        ],
    }
    cuerpo.update(cambios)
    r = _post(mundo, P, "ua", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    pol = r.json()
    r = _post(mundo, f"{P}/{pol['id']}/activar", "uab", mundo.company_a, {}, version=pol["version"])
    assert r.status_code == 200, r.text
    return r.json()


def _activar_politica(mundo, politica):
    r = _post(
        mundo,
        f"{P}/{politica['id']}/activar",
        "uab",
        mundo.company_a,
        {},
        version=politica["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()


def _crear_politica_borrador(mundo, **cambios):
    codigo = f"POL-{uuid.uuid4().hex[:6]}"
    cuerpo = {
        "codigo": codigo,
        "nombre": f"Política {codigo}",
        "base_normativa": "NINGUNA",
        "fundamento": "Fundamento legal y técnico de la política de comisiones",
        "vigente_desde": D(1, 1).isoformat(),
        "min_principales": 3,
        "max_principales": 5,
        "exige_impar": False,
        "suplente_por_principal": False,
        "exige_secretario": False,
        "exige_suplente_secretario": False,
        "quorum": {"tipo": "SIMPLE_MAJORITY"},
        "decision": {"tipo": "SIMPLE_MAJORITY", "base": "ASISTENTES_CON_VOTO"},
        "requisitos": [],
    }
    cuerpo.update(cambios)
    r = _post(mundo, P, "ua", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _comision(mundo, ocupacion, politica_id, **cambios):
    cuerpo = {
        "nombre": "Comisión permanente de prueba",
        "tipo": "PERMANENTE",
        "desde": D(1, 10).isoformat(),
        "hasta": None,
        "objeto": None,
        "acto_id": acto_eficaz(mundo, ocupacion["cargo_emisor"], medio="GACETA"),
        "politica_id": politica_id,
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


def _oficial_de(asignacion):
    if "official_id" in asignacion:
        return asignacion["official_id"]
    return asignacion["funcionario"]["id"]


def _completa_con(mundo, ocupacion, politica_id, tecnico_id=None):
    comision = _comision(mundo, ocupacion, politica_id)
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
    tecnico_asignado = False
    for area, calidad in areas:
        if area == "TECNICA" and calidad == "PRINCIPAL" and tecnico_id is not None and not tecnico_asignado:
            funcionario_id = tecnico_id
            tecnico_asignado = True
        else:
            funcionario = crear_funcionario(mundo, usuario="ua")
            funcionario_id = funcionario["id"]
        if area == "SECRETARIO":
            datos_miembro = {
                "funcionario_id": funcionario_id,
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
                "funcionario_id": funcionario_id,
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
                "funcionario_id": funcionario_id,
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
                if m["funcionario"]["id"] == funcionario_id
            )
            ids_principales[area] = fila["id"]
        comision = detalle
    return comision


def _miembro_puro(idx):
    return SimpleNamespace(
        id=f"P{idx}",
        funcion="MIEMBRO",
        condicion="PRINCIPAL",
        suplente_de_id=None,
        fin_efectivo=None,
        preside=idx == 1,
    )


def _suplente(idx, principal_id):
    return SimpleNamespace(
        id=f"S{idx}",
        funcion="MIEMBRO",
        condicion="SUPLENTE",
        suplente_de_id=principal_id,
        fin_efectivo=None,
        preside=False,
    )


def test_politica_ciclo_y_aislamiento(mundo, gobierno, ocupacion):
    pol = _crear_politica_borrador(mundo)
    assert pol["estado"] == "BORRADOR"
    assert len(pol["regla"]["requisitos"]) == 0

    r = mundo.client.get(
        f"/api/v1{P}/{pol['id']}",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_COMMISSION_POLICY_NOT_FOUND"

    r = mundo.client.get(
        f"/api/v1{P}",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert r.status_code == 200, r.text
    assert all(item["id"] != pol["id"] for item in r.json()["items"])

    pol = _activar_politica(mundo, pol)
    assert pol["estado"] == "VIGENTE"

    cuerpo = {
        "codigo": pol["codigo"],
        "nombre": "Cambio no permitido",
        "base_normativa": pol["base_normativa"],
        "fundamento": pol["fundamento"],
        "vigente_desde": pol["vigente_desde"],
        "min_principales": pol["regla"]["min_principales"],
        "max_principales": pol["regla"]["max_principales"],
        "exige_impar": pol["regla"]["exige_impar"],
        "suplente_por_principal": pol["regla"]["suplente_por_principal"],
        "exige_secretario": pol["regla"]["exige_secretario"],
        "exige_suplente_secretario": pol["regla"]["exige_suplente_secretario"],
        "quorum": pol["regla"]["quorum"],
        "decision": pol["regla"]["decision"],
        "requisitos": pol["regla"]["requisitos"],
        "documentos": pol["regla"].get("documentos", []),
    }
    r = mundo.client.put(
        f"/api/v1{P}/{pol['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(pol["version"])},
        json=cuerpo,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_COMMISSION_POLICY_NOT_DRAFT"

    eventos = [h["evento"] for h in pol.get("historia", [])]
    assert "CREADA" in eventos
    assert "ACTIVADA" in eventos


def test_piso_lcp_no_se_rebaja(mundo, gobierno, ocupacion):
    pol = _crear_politica_borrador(mundo, base_normativa="LCP_ART14", exige_impar=False)
    r = _post(
        mundo,
        f"{P}/{pol['id']}/activar",
        "uab",
        mundo.company_a,
        {},
        version=pol["version"],
    )
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["code"] == "GOV_COMMISSION_POLICY_INVALID"
    motivos = " ".join(cuerpo["details"]["motivos"])
    assert "La base LCP art. 14 exige" in motivos

    pol = _crear_politica_borrador(mundo, base_normativa="NINGUNA")
    pol = _activar_politica(mundo, pol)
    assert pol["estado"] == "VIGENTE"


def test_nueva_version_sustituye(mundo, gobierno, ocupacion):
    pol = _politica(mundo)
    v1_id = pol["id"]
    v1_version = pol["version"]

    r = _post(mundo, f"{P}/{v1_id}/nueva-version", "ua", mundo.company_a, {}, version=v1_version)
    assert r.status_code == 201, r.text
    v2 = r.json()
    assert v2["estado"] == "BORRADOR"
    assert v2["numero_version"] == 2

    r = _post(mundo, f"{P}/{v1_id}/nueva-version", "ua", mundo.company_a, {}, version=v1_version)
    assert r.status_code == 409, r.text
    assert r.json()["code"] in (
        "GOV_COMMISSION_POLICY_NOT_VERSIONABLE",
        "GOV_COMMISSION_POLICY_DRAFT_EXISTS",
    )

    v2 = _activar_politica(mundo, v2)
    r = mundo.client.get(
        f"/api/v1{P}/{v1_id}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    v1 = r.json()
    assert v1["estado"] == "CERRADA"
    assert v1["motivo_cierre"] == "Sustituida por la versión 2"
    eventos = [h["evento"] for h in v1.get("historia", [])]
    assert "SUSTITUIDA" in eventos


def test_historia_inmutable_pg(mundo):
    if not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"):
        pytest.skip("solo PostgreSQL valida la inmutabilidad de la historia")
    pol = _politica(mundo)
    with mundo.factory() as session:
        primer_id = session.execute(
            text("SELECT id FROM gov_commission_policy_history WHERE policy_id = :p LIMIT 1"),
            {"p": pol["id"]},
        ).scalar_one()
    with pytest.raises(Exception) as excinfo:
        with mundo.factory() as session:
            session.execute(
                text("UPDATE gov_commission_policy_history SET evento = 'ALTERADA' WHERE id = :id"),
                {"id": primer_id},
            )
            session.commit()
    assert "GOV_COMMISSION_POLICY_HISTORY_IMMUTABLE" in str(excinfo.value)


def test_validacion_responde_422(mundo, gobierno, ocupacion):
    codigo = f"POL-{uuid.uuid4().hex[:6]}"
    cuerpo_invalido_quorum = {
        "codigo": codigo,
        "nombre": "Quorum inválido",
        "base_normativa": "NINGUNA",
        "fundamento": "Fundamento legal y técnico de la política de comisiones",
        "vigente_desde": D(1, 1).isoformat(),
        "min_principales": 3,
        "max_principales": 5,
        "exige_impar": False,
        "suplente_por_principal": False,
        "exige_secretario": False,
        "exige_suplente_secretario": False,
        "quorum": {"tipo": "QUALIFIED_MAJORITY", "numerador": 1, "denominador": 3},
        "decision": {"tipo": "SIMPLE_MAJORITY", "base": "ASISTENTES_CON_VOTO"},
        "requisitos": [],
    }
    r = _post(mundo, P, "ua", mundo.company_a, cuerpo_invalido_quorum)
    assert r.status_code == 422, r.text
    cuerpo_respuesta = r.json()
    assert cuerpo_respuesta["code"] == "GOV_COMMISSION_POLICY_INVALID"
    assert "quorum" in cuerpo_respuesta["field_errors"]

    codigo2 = f"POL-{uuid.uuid4().hex[:6]}"
    cuerpo_invalido = {
        "codigo": codigo2,
        "nombre": "Requisito sin cargo",
        "base_normativa": "NINGUNA",
        "fundamento": "Fundamento legal y técnico de la política de comisiones",
        "vigente_desde": D(1, 1).isoformat(),
        "min_principales": 3,
        "max_principales": 5,
        "exige_impar": False,
        "suplente_por_principal": False,
        "exige_secretario": False,
        "exige_suplente_secretario": False,
        "quorum": {"tipo": "SIMPLE_MAJORITY"},
        "decision": {"tipo": "SIMPLE_MAJORITY", "base": "ASISTENTES_CON_VOTO"},
        "requisitos": [
            {
                "etiqueta": "Director de presupuesto",
                "funcion": "MIEMBRO",
                "condicion": "PRINCIPAL",
                "tipo": "CARGO",
                "position_id": None,
                "minimo": 1,
            }
        ],
    }
    r = _post(mundo, P, "ua", mundo.company_a, cuerpo_invalido)
    assert r.status_code == 422, r.text
    cuerpo_respuesta = r.json()
    assert cuerpo_respuesta["code"] == "GOV_COMMISSION_POLICY_INVALID"
    assert "requisitos" in cuerpo_respuesta["field_errors"]


def test_umbral_quorum_decision():
    assert umbral("SIMPLE_MAJORITY", None, None, None, 3) == 2
    assert umbral("SIMPLE_MAJORITY", None, None, None, 4) == 3
    assert umbral("QUALIFIED_MAJORITY", None, 2, 3, 3) == 2
    assert umbral("QUALIFIED_MAJORITY", None, 2, 3, 5) == 4
    assert umbral("UNANIMITY", None, None, None, 5) == 5
    assert umbral("ABSOLUTE_COUNT", 2, None, None, 9) == 2
    assert umbral("SIMPLE_MAJORITY", None, None, None, 0) == 1

    p1 = SimpleNamespace(
        id="P1",
        funcion="MIEMBRO",
        condicion="PRINCIPAL",
        suplente_de_id=None,
        fin_efectivo=None,
        preside=False,
    )
    p2 = SimpleNamespace(
        id="P2",
        funcion="MIEMBRO",
        condicion="PRINCIPAL",
        suplente_de_id=None,
        fin_efectivo=None,
        preside=False,
    )
    p3 = SimpleNamespace(
        id="P3",
        funcion="MIEMBRO",
        condicion="PRINCIPAL",
        suplente_de_id=None,
        fin_efectivo=None,
        preside=True,
    )
    s1 = SimpleNamespace(
        id="S1",
        funcion="MIEMBRO",
        condicion="SUPLENTE",
        suplente_de_id="P1",
        fin_efectivo=None,
        preside=False,
    )
    s2 = SimpleNamespace(
        id="S2",
        funcion="MIEMBRO",
        condicion="SUPLENTE",
        suplente_de_id="P2",
        fin_efectivo=None,
        preside=False,
    )
    miembros = [p1, p2, p3, s1, s2]

    regla = copy.deepcopy(REGLA_LEGADO)
    regla["quorum"] = {
        "tipo": "SIMPLE_MAJORITY",
        "cantidad": None,
        "numerador": None,
        "denominador": None,
    }
    resultado = evaluar_quorum(regla, miembros, presentes={"P1", "S2"}, inhibidos=())
    assert resultado["miembros_con_voto"] == 3
    assert resultado["asistentes_con_voto"] == 2
    assert resultado["quorum_requerido"] == 2
    assert resultado["hay_quorum"] is True

    resultado = evaluar_quorum(regla, miembros, presentes={"P1", "S1"}, inhibidos={"P1"})
    assert resultado["asistentes_con_voto"] == 1
    assert resultado["hay_quorum"] is False

    resultado = evaluar_quorum(regla, miembros, presentes={"S1"}, inhibidos={"S1"})
    assert resultado["asistentes_con_voto"] == 0

    regla_presidente_sin_voto = copy.deepcopy(REGLA_LEGADO)
    regla_presidente_sin_voto["quorum"] = {
        "tipo": "SIMPLE_MAJORITY",
        "cantidad": None,
        "numerador": None,
        "denominador": None,
    }
    regla_presidente_sin_voto["presidente_vota"] = False
    regla_presidente_sin_voto["presidente_dirimente"] = False
    resultado = evaluar_quorum(
        regla_presidente_sin_voto,
        [p1, p2, p3],
        presentes={"P1", "P2", "P3"},
        inhibidos=(),
    )
    assert resultado["miembros_con_voto"] == 2

    regla_decision = copy.deepcopy(REGLA_LEGADO)
    regla_decision["quorum"] = {
        "tipo": "SIMPLE_MAJORITY",
        "cantidad": None,
        "numerador": None,
        "denominador": None,
    }
    regla_decision["decision"] = {
        "tipo": "SIMPLE_MAJORITY",
        "cantidad": None,
        "numerador": None,
        "denominador": None,
        "base": "ASISTENTES_CON_VOTO",
    }
    resultado = evaluar_decision(
        regla_decision,
        [p1, p2, p3],
        presentes={"P1", "P2", "P3"},
        a_favor={"P1", "P2"},
        inhibidos=(),
    )
    assert resultado["aprobada"] is True

    p2_preside = SimpleNamespace(
        id="P2",
        funcion="MIEMBRO",
        condicion="PRINCIPAL",
        suplente_de_id=None,
        fin_efectivo=None,
        preside=True,
    )
    regla_dirimente = copy.deepcopy(REGLA_LEGADO)
    regla_dirimente["quorum"] = {
        "tipo": "SIMPLE_MAJORITY",
        "cantidad": None,
        "numerador": None,
        "denominador": None,
    }
    regla_dirimente["decision"] = {
        "tipo": "SIMPLE_MAJORITY",
        "cantidad": None,
        "numerador": None,
        "denominador": None,
        "base": "MIEMBROS_CON_VOTO",
    }
    regla_dirimente["presidente_vota"] = True
    regla_dirimente["presidente_dirimente"] = True
    resultado = evaluar_decision(
        regla_dirimente,
        [p1, p2_preside],
        presentes={"P1", "P2"},
        a_favor={"P2"},
        inhibidos=(),
    )
    assert resultado["aprobada"] is True
    assert resultado["dirimente_usado"] is True


def test_comision_exige_politica_vigente(mundo, gobierno, ocupacion):
    r = _post(
        mundo,
        C,
        "ua",
        mundo.company_a,
        {
            "nombre": "Comisión sin política",
            "tipo": "PERMANENTE",
            "desde": D(1, 10).isoformat(),
            "acto_id": None,
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_COMMITTEE_POLICY_REQUIRED"

    pol = _crear_politica_borrador(mundo)
    r = _post(
        mundo,
        f"{P}/{pol['id']}/cerrar",
        "uab",
        mundo.company_a,
        {"motivo": "Cierre de prueba"},
        version=pol["version"],
    )
    assert r.status_code == 200, r.text
    r = _post(
        mundo,
        C,
        "ua",
        mundo.company_a,
        {
            "nombre": "Comisión con política cerrada",
            "tipo": "PERMANENTE",
            "desde": D(1, 10).isoformat(),
            "acto_id": None,
            "politica_id": pol["id"],
        },
    )
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["code"] == "GOV_COMMITTEE_POLICY_NOT_APPLICABLE"
    assert "politica_id" in cuerpo["field_errors"]


def test_maximo_de_principales(mundo, gobierno, ocupacion):
    pol = _politica(mundo, max_principales=3)
    comision = _complete_and_add_extra_principales(mundo, ocupacion, pol["id"], extra=2)

    r = mundo.client.get(
        f"/api/v1{C}/{comision['id']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    faltantes = " ".join(cuerpo.get("faltantes", []))
    assert "Se admiten como máximo 3 miembros principales" in faltantes
    assert "(política " + pol["codigo"] + ")" in faltantes


def test_requisito_de_competencia(mundo, gobierno, ocupacion):
    pol = _politica(
        mundo,
        requisitos=[
            {
                "etiqueta": "Competencia presupuestaria",
                "funcion": "MIEMBRO",
                "condicion": "PRINCIPAL",
                "tipo": "COMPETENCIA",
                "competencia_accion": "FIRMAR",
                "competencia_materia": "PRESUPUESTO",
                "minimo": 1,
            }
        ],
    )
    comision = _completa_con(mundo, ocupacion, pol["id"])
    faltantes = comision.get("faltantes", [])
    assert "Competencia presupuestaria: se requieren al menos 1; cumplen 0" in faltantes

    asignacion, _ = titular_activo(mundo, ocupacion)
    tecnico_id = _oficial_de(asignacion)
    comision = _completa_con(mundo, ocupacion, pol["id"], tecnico_id=tecnico_id)
    faltantes = comision.get("faltantes", [])
    assert "Competencia presupuestaria: se requieren al menos 1; cumplen 0" not in faltantes


def test_documento_de_constitucion(mundo, gobierno, ocupacion):
    from app.modules.documents.models import Document, DocumentLink, DocumentType

    codigo_doc = f"DOC-CONST-{uuid.uuid4().hex[:6]}"
    with mundo.factory() as session:
        doc_type = DocumentType(
            company_id=mundo.company_a,
            code=codigo_doc,
            name="Acta de constitución",
        )
        session.add(doc_type)
        session.commit()
        doc_type_id = doc_type.id

    pol = _politica(
        mundo,
        documentos=[
            {
                "document_type_id": doc_type_id,
                "etapa": "CONSTITUCION",
                "obligatorio": True,
            }
        ],
    )
    comision = _comision(mundo, ocupacion, pol["id"])
    faltantes = comision.get("faltantes", [])
    assert "Falta el documento «Acta de constitución» de la etapa de constitución" in faltantes

    with mundo.factory() as session:
        documento = Document(
            company_id=mundo.company_a,
            document_type_id=doc_type_id,
            title="Acta de constitución firmada",
            status="ACTIVE",
        )
        session.add(documento)
        session.flush()
        session.add(
            DocumentLink(
                document_id=documento.id,
                company_id=mundo.company_a,
                resource_type="GovernmentProcurementCommittee",
                resource_id=comision["id"],
            )
        )
        session.commit()

    r = mundo.client.get(
        f"/api/v1{C}/{comision['id']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    faltantes = r.json().get("faltantes", [])
    assert "Falta el documento «Acta de constitución» de la etapa de constitución" not in faltantes


def test_regla_congelada(mundo, gobierno, ocupacion):
    pol_v1 = _politica(mundo)
    comision = _completa_con(mundo, ocupacion, pol_v1["id"])
    r = _post(
        mundo,
        f"{C}/{comision['id']}/activar",
        "uab",
        mundo.company_a,
        {},
        version=comision["version"],
    )
    assert r.status_code == 200, r.text
    comision_activa = r.json()
    assert comision_activa["regla_congelada"] is True
    assert comision_activa["regla"]["politica_version"] == 1
    min_original = comision_activa["regla"]["min_principales"]

    r = _post(mundo, f"{P}/{pol_v1['id']}/nueva-version", "ua", mundo.company_a, {}, version=pol_v1["version"])
    assert r.status_code == 201, r.text
    v2 = r.json()
    cuerpo = {
        "codigo": v2["codigo"],
        "nombre": v2["nombre"],
        "base_normativa": v2["base_normativa"],
        "fundamento": v2["fundamento"],
        "vigente_desde": v2["vigente_desde"],
        "min_principales": 5,
        "max_principales": v2["regla"]["max_principales"],
        "exige_impar": v2["regla"]["exige_impar"],
        "suplente_por_principal": v2["regla"]["suplente_por_principal"],
        "exige_secretario": v2["regla"]["exige_secretario"],
        "exige_suplente_secretario": v2["regla"]["exige_suplente_secretario"],
        "quorum": v2["regla"]["quorum"],
        "decision": v2["regla"]["decision"],
        "requisitos": [
            {k: r[k] for k in _CLAVES_REQUISITO_ENTRADA} for r in v2["regla"]["requisitos"]
        ],
        "documentos": [
            {k: d[k] for k in ("document_type_id", "etapa", "obligatorio", "condicion")}
            for d in v2["regla"].get("documentos", [])
        ],
    }
    r = mundo.client.put(
        f"/api/v1{P}/{v2['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(v2["version"])},
        json=cuerpo,
    )
    assert r.status_code == 200, r.text
    v2 = r.json()
    v2 = _activar_politica(mundo, v2)
    assert v2["regla"]["min_principales"] == 5

    r = mundo.client.get(
        f"/api/v1{C}/{comision_activa['id']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert detalle["regla_congelada"] is True
    assert detalle["regla"]["politica_version"] == 1
    assert detalle["regla"]["min_principales"] == min_original


def test_presidencia_unica(mundo, gobierno, ocupacion):
    pol = _politica(mundo)
    comision = _completa_con(mundo, ocupacion, pol["id"])
    r = _post(
        mundo,
        f"{C}/{comision['id']}/activar",
        "uab",
        mundo.company_a,
        {},
        version=comision["version"],
    )
    assert r.status_code == 200, r.text
    comision_activa = r.json()

    principales = [
        m for m in comision_activa["miembros"]
        if m["funcion"] == "MIEMBRO" and m["condicion"] == "PRINCIPAL"
    ]
    presidente_a = principales[0]["id"]
    presidente_b = principales[1]["id"]

    r = _post(
        mundo,
        f"{C}/{comision_activa['id']}/presidencia",
        "ua",
        mundo.company_a,
        {"miembro_id": presidente_a},
        version=comision_activa["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    miembro_a = next(m for m in detalle["miembros"] if m["id"] == presidente_a)
    assert miembro_a["preside"] is True

    r = _post(
        mundo,
        f"{C}/{comision_activa['id']}/presidencia",
        "ua",
        mundo.company_a,
        {"miembro_id": presidente_b},
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    miembro_a = next(m for m in detalle["miembros"] if m["id"] == presidente_a)
    miembro_b = next(m for m in detalle["miembros"] if m["id"] == presidente_b)
    assert miembro_a["preside"] is False
    assert miembro_b["preside"] is True

    tercero = crear_funcionario(mundo, usuario="ua")
    r = _post(
        mundo,
        f"{C}/{comision_activa['id']}/miembros",
        "ua",
        mundo.company_a,
        {
            "funcionario_id": tercero["id"],
            "funcion": "MIEMBRO",
            "area": "TECNICA",
            "condicion": "PRINCIPAL",
            "suplente_de_id": None,
            "certificacion_snc": None,
            "desde": None,
            "acto_id": None,
            "preside": True,
        },
        version=detalle["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_COMMITTEE_PRESIDENT_TAKEN"


def test_inhibicion_con_expediente_ajeno(mundo, gobierno, ocupacion):
    pol = _politica(mundo)
    comision = _completa_con(mundo, ocupacion, pol["id"])
    r = _post(
        mundo,
        f"{C}/{comision['id']}/activar",
        "uab",
        mundo.company_a,
        {},
        version=comision["version"],
    )
    assert r.status_code == 200, r.text
    comision_activa = r.json()
    miembro = comision_activa["miembros"][0]
    r = _post(
        mundo,
        f"{C}/{comision_activa['id']}/inhibiciones",
        "ua",
        mundo.company_a,
        {
            "miembro_id": miembro["id"],
            "asunto": "Conflicto de intereses",
            "causal": "INTERES",
            "descripcion": "Tiene interés directo en el contrato evaluado",
            "fecha": D(1, 11).isoformat(),
            "soporte": None,
            "expediente_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_COMMITTEE_CONFLICT_INVALID"


def test_permisos_de_configuracion(mundo):
    cuenta_con_permisos(mundo, "politica_lector", [("gobierno_comisiones", "view")])
    r = mundo.client.get(
        f"/api/v1{P}",
        headers=mundo.como("politica_lector", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    r = _post(mundo, P, "politica_lector", mundo.company_a, {})
    assert r.status_code == 403, r.text


def _complete_and_add_extra_principales(mundo, ocupacion, politica_id, extra=0):
    """Completa una comisión base y añade principales extra."""
    comision = _completa_con(mundo, ocupacion, politica_id)
    for _ in range(extra):
        funcionario = crear_funcionario(mundo, usuario="ua")
        datos_miembro = {
            "funcionario_id": funcionario["id"],
            "funcion": "MIEMBRO",
            "area": "TECNICA",
            "condicion": "PRINCIPAL",
            "suplente_de_id": None,
            "certificacion_snc": None,
            "desde": None,
            "acto_id": None,
        }
        comision = _miembro(mundo, comision, datos_miembro)
    return comision
