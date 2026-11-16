import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError
from app.modules.documents.models import Document, DocumentType
from app.modules.government import service_contratos_terminacion
from app.modules.government.models import (
    GovernmentAct,
    GovernmentBudgetCommitment,
    GovernmentContract,
    GovernmentGuaranteeInstrument,
    GovernmentNotification,
)
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from tests.concurrency import carrera
from tests.proc08_ayudantes import cargo_contrataciones
from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_cnt01_contratos import C, _cargo_firmante, _ficha, _garantia_fiel, _preparado, _put
from tests.test_gov_cnt04_supervisor import (
    _acto_designante,
    _designar,
    _formalizado,
    _supervisor,
)
from tests.test_gov_cnt08_expediente_contractual import _escenario_completo
from tests.test_gov_cnt09_alertas import _activas, _alertas, _rec, _sin_preaviso
from tests.test_gov_ctl01_reglas import eventos
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc10_garantias import HOY

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

T = "/gobierno/contratos/{cid}/terminacion"
MOTIVO = {
    "causal": "INTERES_DEL_CONTRATANTE",
    "hechos": "El ente decide no continuar con la contratación por razones presupuestarias.",
    "fundamento": "LCP art. 152 y RLCP arts. 190 y 191 aplicables.",
}

CABECERA_CSV = (
    "codigo_terminacion,codigo_contrato,contratista,documento_contratista,"
    "figura,causal,causal_referencia,fecha_acto,fecha_eficacia,acto,"
    "conclusion_hasta,monto_vigente,valuado_conformado,saldo_no_ejecutado,"
    "moneda,formalizado_en"
)


def clave_identificacion(valor: str) -> str:
    """Normaliza una identificación: mayúsculas, sin espacios, puntos ni guiones."""
    return valor.upper().replace(" ", "").replace(".", "").replace("-", "")


def _acto(mundo, cargo_id, fecha, fecha_eficacia, empresa=None) -> str:
    """Crea un acto decisorio de terminación con los requisitos de CNT-07."""
    company_id = empresa if empresa is not None else mundo.company_a
    with mundo.factory() as db:
        tipo = db.execute(
            select(DocumentType).where(
                DocumentType.company_id == company_id,
                DocumentType.code == "GOV-ORG04",
            )
        ).scalar_one_or_none()
        if tipo is None:
            tipo = DocumentType(
                company_id=company_id,
                code="GOV-ORG04",
                name="Acto de prueba ORG-04",
            )
            db.add(tipo)
            db.flush()

        doc = Document(
            company_id=company_id,
            document_type_id=tipo.id,
            title="Acto CNT-07",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()

        numero = uuid.uuid4().hex[:12]
        acto = GovernmentAct(
            company_id=company_id,
            tipo="RESOLUCION",
            denominacion_tipo="",
            denominacion_clave="",
            numero=numero,
            numero_clave=numero,
            fecha=fecha,
            lugar="Naguanagua",
            cargo_id=cargo_id,
            competencia_accion="APROBAR",
            competencia_materia="CONTRATACIONES",
            fundamento_competencia="Fundamento de prueba",
            funcionario="Funcionario de prueba",
            titularidad="TITULAR",
            caracter="PARTICULAR",
            asunto="Terminación de contrato",
            destinatario="Contratista",
            hechos="Hechos de la terminación de prueba",
            fundamentos="LCP art. 152",
            decision="Se rescinde el contrato",
            status="EFICAZ",
            documento_acto_id=doc.id,
            emitido_en=datetime.now(UTC),
            medio="PERSONAL",
            referencia_publicacion="Ref. prueba",
            fecha_publicacion_notificacion=fecha_eficacia,
            fecha_eficacia=fecha_eficacia,
        )
        db.add(acto)
        db.commit()
        return str(acto.id)


def _notificar(mundo, acto_id, nombre, identificacion, fecha) -> None:
    """Crea una notificación NOTIFICADA para un acto."""
    with mundo.factory() as db:
        notificacion = GovernmentNotification(
            company_id=mundo.company_a,
            act_id=acto_id,
            tipo_persona="JURIDICA",
            nombre=nombre,
            identificacion=identificacion,
            identificacion_clave=clave_identificacion(identificacion),
            domicilio="Av. Principal, Caracas",
            recursos="Recurso de reconsideración (LOPA art. 94)",
            status="NOTIFICADA",
            fecha_notificacion=fecha,
            medio_notificacion="PERSONAL",
        )
        db.add(notificacion)
        db.commit()


def _escenario(mundo, ocupacion) -> dict:
    """Prepara un contrato formalizado y devuelve sus datos base."""
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    with mundo.factory() as db:
        contrato = db.get(GovernmentContract, cid)
        codigo = contrato.codigo
        documento = contrato.contratista_documento
        monto = contrato.monto
    cargo = cargo_contrataciones(mundo, ocupacion)
    return {
        "cid": cid,
        "exp": f["exp"],
        "codigo": codigo,
        "documento": documento,
        "monto": monto,
        "cargo": cargo,
    }


def _acto_notificado(mundo, esc, fecha=HOY) -> str:
    """Crea un acto decisorio eficaz y notificado al contratista."""
    acto = _acto(mundo, esc["cargo"], fecha, fecha)
    _notificar(mundo, acto, "Contratista", esc["documento"], fecha)
    return acto


def _borrador(mundo, cid, **campos) -> dict:
    """Crea un borrador de terminación y devuelve el diccionario del borrador."""
    cuerpo = {"figura": "RESCISION_NO_IMPUTABLE", **campos}
    r = _post(mundo, T.format(cid=cid), "ua", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    return r.json()["borrador"]


def _patch(mundo, cid, version, cuerpo):
    """PATCH del borrador con la cabecera If-Match si version no es None."""
    headers = mundo.como("ua", mundo.company_a)
    if version is not None:
        headers["If-Match"] = str(version)
    return mundo.client.patch(
        f"/api/v1{T.format(cid=cid)}/borrador", headers=headers, json=cuerpo
    )


def _formalizar(mundo, cid, version):
    """POST de formalización del borrador con If-Match."""
    headers = mundo.como("ua", mundo.company_a)
    if version is not None:
        headers["If-Match"] = str(version)
    return mundo.client.post(
        f"/api/v1{T.format(cid=cid)}/formalizar", headers=headers
    )


def _listo(mundo, esc, figura="RESCISION_NO_IMPUTABLE", **extra) -> dict:
    """Prepara un borrador completo y válido, y devuelve su diccionario."""
    acto = _acto_notificado(mundo, esc)
    b = _borrador(mundo, esc["cid"], figura=figura)
    r = _patch(
        mundo,
        esc["cid"],
        b["version"],
        {**MOTIVO, "act_id": acto, **extra},
    )
    assert r.status_code == 200, r.text
    return r.json()["borrador"]


@ONLY_PG
def test_catalogo_situacion_y_contrato_no_formalizado(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    r = mundo.client.get(
        f"/api/v1{T.format(cid=esc['cid'])}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200
    datos = r.json()
    assert datos["situacion"]["estado"] == "VIGENTE"
    figuras = [f["codigo"] for f in datos["catalogo"]["figuras"]]
    assert figuras == [
        "RESCISION_NO_IMPUTABLE",
        "RESOLUCION_MUTUO_ACUERDO",
        "RESCISION_IMPUTABLE",
    ]
    imputable = datos["catalogo"]["figuras"][2]
    assert len(imputable["causales"]) == 10
    assert imputable["causales"][0]["codigo"] == "LCP_155_1"
    assert datos["permisos"]["terminar"] is True

    prep = _preparado(mundo, ocupacion)
    r = _post(mundo, T.format(cid=prep["contrato"]["id"]), "ua", mundo.company_a, {"figura": "RESCISION_NO_IMPUTABLE"})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_TERMINATION_NOT_FORMALIZED"

    headers_b = mundo.como("ua", mundo.company_b)
    r = mundo.client.get(f"/api/v1{T.format(cid=esc['cid'])}", headers=headers_b)
    assert r.status_code == 404
    r = mundo.client.post(
        f"/api/v1{T.format(cid=esc['cid'])}",
        headers=headers_b,
        json={"figura": "RESCISION_NO_IMPUTABLE"},
    )
    assert r.status_code == 404


@ONLY_PG
def test_borrador_if_match_y_validaciones(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    ruta = T.format(cid=esc["cid"])

    r = _post(mundo, ruta, "ua", mundo.company_a, {"figura": "CADUCIDAD"})
    assert r.status_code == 422
    assert r.json()["details"]["motivo"] == "FIGURA"

    b = _borrador(mundo, esc["cid"])
    r = _post(mundo, ruta, "ua", mundo.company_a, {"figura": "RESCISION_NO_IMPUTABLE"})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_TERMINATION_DRAFT_EXISTS"

    r = _patch(mundo, esc["cid"], None, {"causal": MOTIVO["causal"]})
    assert r.status_code == 428

    r = _patch(mundo, esc["cid"], b["version"] - 1, {"causal": MOTIVO["causal"]})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_TERMINATION_STALE"
    assert "version_actual" in r.json()["details"]

    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 422
    assert r.json()["details"]["motivo"] == "CAUSAL"

    r = _patch(mundo, esc["cid"], b["version"], {"causal": MOTIVO["causal"]})
    assert r.status_code == 200
    b = r.json()["borrador"]
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 422
    assert r.json()["details"]["motivo"] == "MOTIVACION"

    acto_emitido = _acto(mundo, esc["cargo"], HOY, HOY)
    with mundo.factory() as db:
        a = db.get(GovernmentAct, acto_emitido)
        a.status = "EMITIDO"
        a.fecha_eficacia = None
        db.commit()
    r = _patch(
        mundo,
        esc["cid"],
        b["version"],
        {"hechos": MOTIVO["hechos"], "fundamento": MOTIVO["fundamento"], "act_id": acto_emitido},
    )
    assert r.status_code == 200
    b = r.json()["borrador"]
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 422
    assert r.json()["details"]["motivo"] == "ACTO_EFICAZ"

    acto_general = _acto(mundo, esc["cargo"], HOY, HOY)
    with mundo.factory() as db:
        acto_general_db = db.get(GovernmentAct, acto_general)
        acto_general_db.caracter = "GENERAL"
        acto_general_db.destinatario = None
        db.commit()
    r = _patch(mundo, esc["cid"], b["version"], {**MOTIVO, "act_id": acto_general})
    assert r.status_code == 200, r.text
    b = r.json()["borrador"]
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 422, r.text
    assert r.json()["details"]["motivo"] == "ACTO_EFICAZ"

    r = mundo.client.delete(
        f"/api/v1{ruta}/borrador",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(b["version"])},
    )
    assert r.status_code == 204
    r = mundo.client.get(f"/api/v1{ruta}", headers=mundo.como("ua", mundo.company_a))
    assert r.json()["borrador"] is None


@ONLY_PG
def test_causales_por_figura(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    acto = _acto_notificado(mundo, esc)
    b = _borrador(mundo, esc["cid"], figura="RESCISION_IMPUTABLE")
    r = _patch(
        mundo,
        esc["cid"],
        b["version"],
        {**MOTIVO, "act_id": acto},
    )
    assert r.status_code == 200
    b = r.json()["borrador"]
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 422
    assert r.json()["details"]["motivo"] == "CAUSAL"
    b = _patch(mundo, esc["cid"], b["version"], {"figura": "RESOLUCION_MUTUO_ACUERDO"}).json()["borrador"]
    r = _patch(
        mundo,
        esc["cid"],
        b["version"],
        {**MOTIVO, "causal": "CLAUSULA_CONTRATO", "act_id": acto},
    )
    assert r.status_code == 200
    b = r.json()["borrador"]
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 422
    assert r.json()["details"]["motivo"] == "CAUSAL"


@ONLY_PG
def test_autoridad_y_notificaciones(mundo, gobierno, ocupacion):
    from tests.org04_ayudantes import nuevo_cargo

    esc = _escenario(mundo, ocupacion)
    cargo_sin = nuevo_cargo(mundo, ocupacion)
    acto_sin = _acto(mundo, cargo_sin, HOY, HOY)
    _notificar(mundo, acto_sin, "Contratista", esc["documento"], HOY)
    b = _borrador(mundo, esc["cid"])
    r = _patch(mundo, esc["cid"], b["version"], {**MOTIVO, "act_id": acto_sin})
    assert r.status_code == 200
    b = r.json()["borrador"]
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 422
    assert r.json()["details"]["motivo"] == "AUTORIDAD"
    assert len(eventos(mundo, "GOV_CONTRACT_TERMINATION_BLOCKED", esc["exp"]["id"])) == 1

    acto_tercero = _acto(mundo, esc["cargo"], HOY, HOY)
    _notificar(mundo, acto_tercero, "Tercero", "J-11111111-1", HOY)
    b = _patch(mundo, esc["cid"], b["version"], {"figura": "RESCISION_NO_IMPUTABLE"}).json()["borrador"]
    r = _patch(mundo, esc["cid"], b["version"], {**MOTIVO, "act_id": acto_tercero})
    assert r.status_code == 200
    b = r.json()["borrador"]
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 422
    assert r.json()["details"]["motivo"] == "NOTIFICACION_CONTRATISTA"


@ONLY_PG
def test_rescision_no_imputable_formalizada(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    with mundo.factory() as db:
        compromisos_antes = db.scalar(
            select(func.count()).select_from(GovernmentBudgetCommitment)
        )
    b = _listo(mundo, esc)
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200, r.text
    datos = r.json()
    formalizada = datos["formalizada"]
    assert formalizada["codigo"] == f"{esc['codigo']}/TER"
    assert formalizada["estado"] == "FORMALIZADA"
    assert formalizada["fecha_eficacia"] == HOY.isoformat()
    assert len(formalizada["huella"]) == 64
    assert datos["situacion"]["estado"] == "EXTINGUIDO"
    assert datos["situacion"]["figura"] == "RESCISION_NO_IMPUTABLE"

    cons = datos["consecuencias"]
    assert cons["monto_vigente"] == f"{esc['monto']:.2f}"
    monto_vigente = Decimal(esc["monto"])
    valuado = Decimal(cons["valuado_conformado"])
    saldo = Decimal(cons["saldo_no_ejecutado"])
    assert saldo == monto_vigente - valuado
    assert cons["indemnizacion"]["estado"] == "CONSECUENCIA_PENDIENTE_CNT06"
    assert "no crea pagos" in cons["efectos"]
    obligaciones = [o["codigo"] for o in datos["obligaciones"]]
    assert "EVALUACION_DESEMPENO_SNC" in obligaciones

    r = mundo.client.get(
        f"/api/v1/gobierno/contratos/{esc['cid']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200
    assert r.json()["situacion"]["estado"] == "EXTINGUIDO"

    assert len(eventos(mundo, "GOV_CONTRACT_TERMINATION_FORMALIZED", esc["exp"]["id"])) == 1

    r = _post(mundo, T.format(cid=esc["cid"]), "ua", mundo.company_a, {"figura": "RESCISION_NO_IMPUTABLE"})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_TERMINATION_ALREADY_EXISTS"

    with mundo.factory() as db:
        compromisos_despues = db.scalar(
            select(func.count()).select_from(GovernmentBudgetCommitment)
        )
    assert compromisos_despues == compromisos_antes


@ONLY_PG
def test_inmutable(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    b = _listo(mundo, esc)
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200
    tid = r.json()["formalizada"]["id"]

    with mundo.factory() as db:
        with pytest.raises(DBAPIError) as exc_info:
            db.execute(
                text("UPDATE gov_contract_terminations SET hechos = 'x' WHERE id = :id"),
                {"id": tid},
            )
        assert "GOV_CONTRACT_TERMINATION_IMMUTABLE" in str(exc_info.value)
        db.rollback()

        with pytest.raises(DBAPIError) as exc_info:
            db.execute(
                text("DELETE FROM gov_contract_terminations WHERE id = :id"),
                {"id": tid},
            )
        assert "GOV_CONTRACT_TERMINATION_IMMUTABLE" in str(exc_info.value)
        db.rollback()


@ONLY_PG
def test_guardas_posteriores(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    b = _listo(mundo, esc)
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200

    r = _post(
        mundo,
        f"/gobierno/contratos/{esc['cid']}/ejecucion/hitos",
        "ua",
        mundo.company_a,
        {
            "descripcion": "Hito tardío",
            "fecha_prevista": (HOY + timedelta(days=1)).isoformat(),
            "monto_previsto": "1000.00",
            "obligatorio": True,
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_TERMINATED"
    assert r.json()["details"]["fecha_limite"] == HOY.isoformat()

    r = _post(
        mundo,
        f"/gobierno/contratos/{esc['cid']}/ejecucion/hitos",
        "ua",
        mundo.company_a,
        {
            "descripcion": "Hito anterior",
            "fecha_prevista": HOY.isoformat(),
            "monto_previsto": "1000.00",
            "obligatorio": False,
        },
    )
    assert r.status_code == 201

    sup = _supervisor(mundo, ocupacion)
    acto_des = _acto_designante(mundo, ocupacion)
    r = _designar(mundo, esc["cid"], sup, acto_des, HOY + timedelta(days=1))
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_TERMINATED"

    from app.modules.government import situacion_contractual

    with mundo.factory() as db:
        with pytest.raises(ConflictError) as exc_info:
            situacion_contractual.exigir_vigente_para_modificacion(
                db, mundo.company_a, esc["cid"], HOY
            )
    assert exc_info.value.code == "GOV_CONTRACT_TERMINATED"


@ONLY_PG
def test_hechos_posteriores_impiden_formalizar(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    r = _post(
        mundo,
        f"/gobierno/contratos/{esc['cid']}/ejecucion/hitos",
        "ua",
        mundo.company_a,
        {
            "descripcion": "Hito futuro",
            "fecha_prevista": (HOY + timedelta(days=10)).isoformat(),
            "monto_previsto": "1000.00",
            "obligatorio": False,
        },
    )
    assert r.status_code == 201
    b = _listo(mundo, esc)
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_TERMINATION_LATER_FACTS"
    hechos = r.json()["details"]["hechos"]
    assert any(h["proceso"] == "CNT-03" and h["tipo"] == "HITO" for h in hechos)


@ONLY_PG
def test_conclusion_autorizada(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    b = _listo(
        mundo,
        esc,
        conclusion_alcance="Concluir el tramo 2 ya iniciado",
        conclusion_hasta=(HOY + timedelta(days=5)).isoformat(),
    )
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200
    assert r.json()["situacion"]["fecha_limite_ejecucion"] == (HOY + timedelta(days=5)).isoformat()

    r = _post(
        mundo,
        f"/gobierno/contratos/{esc['cid']}/ejecucion/hitos",
        "ua",
        mundo.company_a,
        {
            "descripcion": "Hito dentro",
            "fecha_prevista": (HOY + timedelta(days=3)).isoformat(),
            "monto_previsto": "1000.00",
            "obligatorio": False,
        },
    )
    assert r.status_code == 201

    r = _post(
        mundo,
        f"/gobierno/contratos/{esc['cid']}/ejecucion/hitos",
        "ua",
        mundo.company_a,
        {
            "descripcion": "Hito fuera",
            "fecha_prevista": (HOY + timedelta(days=6)).isoformat(),
            "monto_previsto": "1000.00",
            "obligatorio": False,
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_TERMINATED"


@ONLY_PG
def test_rescision_imputable_con_apertura(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    acto = _acto_notificado(mundo, esc)
    b = _borrador(mundo, esc["cid"], figura="RESCISION_IMPUTABLE")
    r = _patch(
        mundo,
        esc["cid"],
        b["version"],
        {
            "causal": "LCP_155_8",
            "hechos": MOTIVO["hechos"],
            "fundamento": MOTIVO["fundamento"],
            "act_id": acto,
        },
    )
    assert r.status_code == 200
    b = r.json()["borrador"]
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 422
    assert r.json()["details"]["motivo"] == "APERTURA"

    apertura = _acto(mundo, esc["cargo"], HOY - timedelta(days=10), HOY - timedelta(days=5))
    r = _patch(mundo, esc["cid"], b["version"], {"apertura_act_id": apertura})
    assert r.status_code == 200
    b = r.json()["borrador"]
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200
    assert r.json()["formalizada"]["apertura"]["id"] == apertura
    obligaciones = [o["codigo"] for o in r.json()["obligaciones"]]
    assert "PUBLICACION_SNC" in obligaciones


@ONLY_PG
def test_concurrencia_formalizacion(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    b = _listo(mundo, esc)
    uid = _uid(mundo)

    def ctx_de(s):
        return CompanyContext(
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            company=s.get(Company, mundo.company_a),
            user_id=uid,
        )

    def op(s):
        return service_contratos_terminacion.formalizar(
            s, ctx_de(s), s.get(User, uid), esc["cid"], b["version"]
        )

    r1, r2 = carrera(mundo.factory, op, op)
    ok = sum(isinstance(r, dict) for r in (r1, r2))
    assert ok == 1
    err = next(r for r in (r1, r2) if isinstance(r, KontrolError))
    assert err.code in (
        "GOV_CONTRACT_TERMINATION_STALE",
        "GOV_CONTRACT_TERMINATION_NOT_FOUND",
        "GOV_CONTRACT_TERMINATION_ALREADY_EXISTS",
    )

    with mundo.factory() as db:
        filas = db.scalar(
            select(func.count()).where(
                text("gov_contract_terminations.contract_id = :cid AND gov_contract_terminations.estado = 'FORMALIZADA'").bindparams(cid=esc["cid"]),
            ).select_from(text("gov_contract_terminations")),
        )
    assert filas == 1


@ONLY_PG
def test_reporte_csv(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    b = _listo(mundo, esc)
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200

    r = mundo.client.get(
        "/api/v1/gobierno/contratos/terminaciones/reporte.csv",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.strip().splitlines()
    assert lineas[0] == CABECERA_CSV
    assert any(linea.startswith(f"{esc['codigo']}/TER,") for linea in lineas[1:])

    r = mundo.client.get(
        "/api/v1/gobierno/contratos/terminaciones/reporte.csv?figura=RESCISION_IMPUTABLE",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200
    lineas = r.text.strip().splitlines()
    assert lineas[0] == CABECERA_CSV
    assert not any(linea.startswith(f"{esc['codigo']}/TER,") for linea in lineas[1:])


@ONLY_PG
def test_alerta_acto_base_revocado(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    b = _listo(mundo, esc)
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200
    acto_base = r.json()["formalizada"]["acto"]["id"]
    revocador = _acto(mundo, esc["cargo"], HOY, HOY)
    with mundo.factory() as db:
        acto = db.get(GovernmentAct, acto_base)
        acto.status = "REVOCADO"
        acto.revocado_por_id = revocador
        db.commit()
    r = mundo.client.get(
        f"/api/v1{T.format(cid=esc['cid'])}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200
    datos = r.json()
    assert datos["situacion"]["estado"] == "EXTINGUIDO"
    assert datos["situacion"]["alerta_acto_base"]["estado"] == "REVOCADO"


def _uid(mundo, nombre="ua") -> str:
    with mundo.factory() as db:
        return db.scalar(select(User.id).where(User.username == nombre))


def test_permiso_terminate_sensible(mundo, gobierno, ocupacion):
    assert classify("gobierno_contratos:terminate") == SENSITIVE
    assert "terminate" in CATALOGO_DE_PERMISOS["gobierno_contratos"]


@ONLY_PG
def test_eficacia_juridica_no_es_fecha_de_registro(mundo, gobierno, ocupacion, monkeypatch):
    esc = _escenario(mundo, ocupacion)
    b = _listo(mundo, esc)
    monkeypatch.setattr(service_contratos_terminacion, "hoy_de_negocio", lambda: HOY + timedelta(days=3))
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200, r.text
    formalizada = r.json()["formalizada"]
    assert formalizada["fecha_eficacia"] == HOY.isoformat()
    assert formalizada["fecha_acto"] == HOY.isoformat()


@ONLY_PG
def test_garantes_y_garantia_no_se_ejecuta(mundo, gobierno, ocupacion):
    prep = _preparado(mundo, ocupacion)
    cid = prep["contrato"]["id"]
    garantia_id = _garantia_fiel(mundo, prep["exp"], prep["ofertas"][0])
    ficha = _ficha(mundo, cid).json()
    r = _put(mundo, cid, "/garantias", {"instrumento_ids": [garantia_id]}, ficha["version"])
    assert r.status_code == 200, r.text
    firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
    r = _post(mundo, f"{C}/{cid}/formalizar", "ua", mundo.company_a,
              {"firmante_cargo_id": firmante}, version=_ficha(mundo, cid).json()["version"])
    assert r.status_code == 200, r.text
    with mundo.factory() as db:
        contrato = db.get(GovernmentContract, cid)
        codigo = contrato.codigo
        documento = contrato.contratista_documento
        monto = contrato.monto
    cargo = cargo_contrataciones(mundo, ocupacion)
    esc = {"cid": cid, "codigo": codigo, "documento": documento, "monto": monto, "cargo": cargo}
    acto = _acto_notificado(mundo, esc)
    b = _borrador(mundo, cid, figura="RESCISION_NO_IMPUTABLE")
    r = _patch(mundo, cid, b["version"], {**MOTIVO, "act_id": acto})
    assert r.status_code == 200, r.text
    b = r.json()["borrador"]
    r = _formalizar(mundo, cid, b["version"])
    assert r.status_code == 422, r.text
    assert r.json()["details"]["motivo"] == "NOTIFICACION_GARANTES"
    _notificar(mundo, acto, "Garante", "J-22222222-2", HOY)
    r = _formalizar(mundo, cid, b["version"])
    assert r.status_code == 200, r.text
    assert "REVISAR_GARANTIAS_PROC10" in [o["codigo"] for o in r.json()["obligaciones"]]
    with mundo.factory() as db:
        instrumento = db.get(GovernmentGuaranteeInstrument, garantia_id)
        assert instrumento.estado == "REGISTRADA"


@ONLY_PG
def test_compromiso_presupuestario_no_se_anula(mundo, gobierno, ocupacion):
    d = _escenario_completo(mundo, ocupacion)
    cid = d["cid"]
    with mundo.factory() as db:
        contrato = db.get(GovernmentContract, cid)
        documento = contrato.contratista_documento
        monto = contrato.monto
    cargo = cargo_contrataciones(mundo, ocupacion)
    esc = {"cid": cid, "codigo": d["codigo"], "documento": documento, "monto": monto, "cargo": cargo}
    acto = _acto_notificado(mundo, esc)
    b = _borrador(mundo, cid, figura="RESCISION_NO_IMPUTABLE")
    r = _patch(mundo, cid, b["version"], {**MOTIVO, "act_id": acto})
    assert r.status_code == 200, r.text
    r = _formalizar(mundo, cid, r.json()["borrador"]["version"])
    assert r.status_code == 200, r.text
    vista = r.json()
    assert "REVISAR_COMPROMISO_BUD08" in [o["codigo"] for o in vista["obligaciones"]]
    assert any(item["estado"] == "VIGENTE" for item in vista["consecuencias"]["compromisos"])
    with mundo.factory() as db:
        compromisos = db.execute(
            select(GovernmentBudgetCommitment).where(
                GovernmentBudgetCommitment.procurement_file_id == d["exp_id"]
            )
        ).scalars().all()
        assert compromisos
        assert all(c.estado == "VIGENTE" for c in compromisos)


@ONLY_PG
def test_expediente_cnt08_proyecta_la_terminacion(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    b = _listo(mundo, esc)
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200, r.text
    r = mundo.get(f"/gobierno/contratos/{esc['cid']}/expediente", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["terminacion"]["actuacion"]["codigo"] == f"{esc['codigo']}/TER"
    assert "CNT-07" not in [f["proceso"] for f in cuerpo["fuentes_futuras"]]
    r = mundo.get(f"/gobierno/contratos/{esc['cid']}/expediente/cronologia?proceso=CNT-07", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert any(item.get("tipo") == "TERMINACION_FORMALIZADA" for item in r.json()["items"])

@ONLY_PG
def test_alertas_cnt09_se_reconcilian(mundo, gobierno, ocupacion):
    esc = _escenario(mundo, ocupacion)
    _sin_preaviso(mundo)
    r = _post(mundo, f"/gobierno/contratos/{esc['cid']}/ejecucion/hitos", "ua", mundo.company_a,
              {"descripcion": "Hito de prueba", "fecha_prevista": HOY.isoformat(),
               "monto_previsto": "1000.00", "obligatorio": True})
    assert r.status_code == 201, r.text
    _rec(mundo, HOY)
    assert _activas(mundo, esc["cid"])
    b = _listo(mundo, esc)
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200, r.text
    _rec(mundo, HOY)
    assert _activas(mundo, esc["cid"]) == []
    assert all(a["status"] == "RESOLVED" for a in _alertas(mundo, esc["cid"]))

