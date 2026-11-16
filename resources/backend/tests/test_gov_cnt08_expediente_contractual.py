"""CNT-08 · expediente contractual: proyección, integridad y paquetes (GOV-CNT-008)."""

import hashlib
import io
import json
import zipfile
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.company_context import CompanyContext
from app.modules.documents.models import DocumentVersion, StoredFile
from app.modules.documents.storage import get_storage
from app.modules.government import service_expediente_contractual, service_expedientes
from app.modules.government.models import GovernmentContract, GovernmentProcurementFile
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.identity_access.models import User
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_cnt01_contratos import _cargo_firmante, _cdp, _ficha, _post, _preparado
from tests.test_gov_cnt02_modificaciones import (
    _compromiso,
    _formalizado,
    _formalizar_m,
    _lista,
    _put_m,
)
from tests.test_gov_cnt03_ejecucion import _d, _listo, _p
from tests.test_gov_cnt04_supervisor import _acto_designante, _designar, _supervisor
from tests.test_gov_ctl01_reglas import eventos
from tests.test_gov_proc10_garantias import HOY, _doc

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

EXPEDIENTE = "/gobierno/contratos/{cid}/expediente"
LISTA = "/gobierno/expedientes-contractuales"
PAQUETES = "/gobierno/contratos/{cid}/expediente/paquetes"

FUENTES_FUTURAS = ["CNT-05", "CNT-06", "TRE-04"]
MENSAJE_FUENTE_FUTURA = (
    "El módulo aún no está disponible: el expediente no puede afirmar si hubo "
    "actuaciones de este tipo."
)


def _formalizado_con_adenda(mundo, ocupacion) -> dict[str, Any]:
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    b = _lista(
        mundo, f, cid, "ADENDA", {"delta_monto": "10000.00"}, "doc-adenda"
    )
    firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
    cdp3 = _cdp(mundo, ocupacion, "15000.00", expediente_id=f["exp"]["id"])
    r = _put_m(
        mundo,
        cid,
        b["id"],
        [{"certificado_id": cdp3, "monto": "10000.00"}],
        b["version"],
    )
    assert r.status_code == 200
    b = r.json()
    r = _formalizar_m(mundo, cid, b["id"], firmante, b["version"])
    assert r.status_code == 200
    return {"contrato": f["contrato"], "exp": f["exp"], "cdp3": cdp3}


def _supervisor_designado(mundo, ocupacion, cid):
    sup = _supervisor(mundo, ocupacion)
    acto = _acto_designante(mundo, ocupacion)
    r = _designar(mundo, cid, sup, acto, HOY, motivo="Supervisión CNT-08")
    assert r.status_code == 201
    return sup, r.json()


def _escenario_completo(mundo, ocupacion) -> dict[str, Any]:
    f = _formalizado_con_adenda(mundo, ocupacion)
    cid = f["contrato"]["id"]
    sup, _ = _supervisor_designado(mundo, ocupacion, cid)
    doc_id, _ = _doc(mundo, f["exp"], "doc-compromiso")
    compromiso = _compromiso(
        mundo, ocupacion, f["cdp3"], "1000.00", f["exp"]["id"], doc_id
    )
    with mundo.factory() as db:
        contrato = db.get(GovernmentContract, cid)
        codigo = contrato.codigo
    return {
        "cid": cid,
        "exp_id": f["exp"]["id"],
        "sup": sup,
        "compromiso": compromiso,
        "codigo": codigo,
    }


def _rehacer(
    datos: bytes,
    cambios: dict[str, bytes | None] | None = None,
    extra: dict[str, bytes] | None = None,
) -> bytes:
    origen = zipfile.ZipFile(io.BytesIO(datos))
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zf:
        for info in origen.infolist():
            if cambios and info.filename in cambios:
                reemplazo = cambios[info.filename]
                if reemplazo is None:
                    continue
                zf.writestr(info, reemplazo)
            else:
                zf.writestr(info, origen.read(info.filename))
        for ruta, contenido in (extra or {}).items():
            zf.writestr(ruta, contenido)
    return salida.getvalue()


def _verificar(mundo, datos: bytes, usuario="ua", empresa=None):
    return mundo.client.post(
        f"/api/v1{LISTA}/paquetes/verificar",
        headers=mundo.como(usuario, empresa or mundo.company_a),
        files={"archivo": ("paquete.zip", datos, "application/zip")},
    )


@ONLY_PG
def test_expediente_completo(mundo, gobierno, ocupacion):
    esc = _escenario_completo(mundo, ocupacion)
    cid = esc["cid"]
    r = mundo.get(EXPEDIENTE.format(cid=cid), "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["contrato"]["estado"] == "FORMALIZADO"
    assert cuerpo["resumen"]["monto_original"] == "50000.00"
    assert cuerpo["resumen"]["monto_vigente"] == "60000.00"
    assert cuerpo["instrumento"]["original"]["monto"] == "50000.00"
    assert cuerpo["instrumento"]["vigente"]["monto"] == "60000.00"
    assert cuerpo["modificaciones"]["cantidad"] == 1
    hist = cuerpo["modificaciones"]["historial"][0]
    assert hist["enlace"] == f"/gobierno/contratos/{cid}/modificaciones/{hist['id']}"
    assert cuerpo["supervision"]["vigente"]["referencia"] == "SUP-01"
    assert cuerpo["resumen"]["supervisor_actual"]["referencia"] == "SUP-01"
    codigos_compromisos = [c["codigo"] for c in cuerpo["presupuesto"]["compromisos"]]
    assert any(codigo for codigo in codigos_compromisos if codigo)
    assert "no crea" in cuerpo["presupuesto"]["efectos"]
    tipos_documentos = {d["tipo"] for d in cuerpo["documentos"]}
    assert {"INSTRUMENTO", "MODIFICACION", "COMPROBANTE_CDP", "COMPROBANTE_COMPROMISO"} <= tipos_documentos
    assert cuerpo["ejecucion"]["estado"] == "DISPONIBLE"
    assert cuerpo["ejecucion"]["estado_ejecucion"] == "SIN_INICIAR"
    assert cuerpo["resumen"]["ejecucion"]["estado"] == "SIN_INICIAR"
    assert [f["proceso"] for f in cuerpo["fuentes_futuras"]] == FUENTES_FUTURAS
    assert all(f["estado"] == "SOURCE_PROCESS_NOT_AVAILABLE" for f in cuerpo["fuentes_futuras"])
    assert all(f["mensaje"] == MENSAJE_FUENTE_FUTURA for f in cuerpo["fuentes_futuras"])
    referencias_documentos = {d["referencia"] for d in cuerpo["documentos"]}
    assert cid not in referencias_documentos
    assert cuerpo["permisos"]["auditoria"] is True
    assert cuerpo["permisos"]["ver_paquetes"] is True
    assert cuerpo["permisos"]["generar_paquete"] is True
    assert cuerpo["origen"]["expediente"]["id"] == esc["exp_id"]
    assert esc["exp_id"] in cuerpo["adjudicacion"]["enlace"]
    ficha = _ficha(mundo, cid)
    assert ficha.status_code == 200
    assert ficha.json()["monto"] == "50000.00"


@ONLY_PG
def test_borrador_y_aislamiento(mundo, gobierno, ocupacion):
    prep = _preparado(mundo, ocupacion)
    cid = prep["contrato"]["id"]
    r = mundo.get(EXPEDIENTE.format(cid=cid), "ua", mundo.company_a)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_DOSSIER_NOT_FORMALIZED"

    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    with mundo.factory() as db:
        contrato = db.get(GovernmentContract, cid)
        codigo = contrato.codigo

    for ruta in (
        EXPEDIENTE.format(cid=cid),
        EXPEDIENTE.format(cid=cid) + "/cronologia",
        EXPEDIENTE.format(cid=cid) + "/integridad",
        EXPEDIENTE.format(cid=cid) + "/auditoria",
        PAQUETES.format(cid=cid),
    ):
        r = mundo.get(ruta, "ub", mundo.company_b)
        assert r.status_code == 404, r.text

    r = mundo.get(LISTA, "ub", mundo.company_b)
    assert r.status_code == 200
    assert all(item["codigo"] != codigo for item in r.json()["items"])


@ONLY_PG
def test_cronologia_orden_filtros_y_paginacion(mundo, gobierno, ocupacion):
    esc = _escenario_completo(mundo, ocupacion)
    cid = esc["cid"]
    r = mundo.get(EXPEDIENTE.format(cid=cid) + "/cronologia?limit=200", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    items = cuerpo["items"]
    assert [i["orden"] for i in items] == list(range(1, len(items) + 1))
    fechas = [i["fecha"] for i in items]
    assert fechas == sorted(fechas)
    procesos = {i["proceso"] for i in items}
    assert {"PROC-03", "CNT-01", "CNT-02", "CNT-04", "BUD-06"} <= procesos
    assert not any(i["proceso"] == "PROC-03" and i["tipo"] in {"CONTRATO", "GARANTIA"} for i in items)

    r = mundo.get(EXPEDIENTE.format(cid=cid) + "/cronologia?proceso=CNT-02", "ua", mundo.company_a)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"] == 1
    assert all(i["proceso"] == "CNT-02" for i in cuerpo["items"])
    assert cuerpo["items"][0]["tipo"] == "MODIFICACION_FORMALIZADA"
    assert cuerpo["items"][0]["fecha_efectiva"] is not None

    r = mundo.get(EXPEDIENTE.format(cid=cid) + "/cronologia?limit=2&offset=1", "ua", mundo.company_a)
    assert r.status_code == 200
    cuerpo = r.json()
    assert [i["orden"] for i in cuerpo["items"]] == [items[1]["orden"], items[2]["orden"]]
    assert cuerpo["total"] == len(items)

    futuro = (HOY + timedelta(days=365)).isoformat()
    r = mundo.get(EXPEDIENTE.format(cid=cid) + f"/cronologia?desde={futuro}", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["total"] == 0

    r = mundo.get(EXPEDIENTE.format(cid=cid) + "/cronologia?limit=201", "ua", mundo.company_a)
    assert r.status_code == 422


@ONLY_PG
def test_auditoria_acotada_y_permiso(mundo, gobierno, ocupacion):
    esc = _escenario_completo(mundo, ocupacion)
    cid = esc["cid"]
    r = mundo.get(EXPEDIENTE.format(cid=cid) + "/auditoria", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    acciones = {i["accion"] for i in cuerpo["items"]}
    assert "GOV_CONTRACT_AMENDMENT_FORMALIZED" in acciones
    assert all(i["enlace"] == f"/gobierno/auditoria?evento={i['id']}" for i in cuerpo["items"])

    cuenta_con_permisos(mundo, "cnt08_lector", [("gobierno_contratos", "view")])
    r = mundo.get(EXPEDIENTE.format(cid=cid) + "/auditoria", "cnt08_lector", mundo.company_a)
    assert r.status_code == 403
    r = mundo.get(EXPEDIENTE.format(cid=cid), "cnt08_lector", mundo.company_a)
    assert r.status_code == 200
    assert all(v is False for v in r.json()["permisos"].values())
    r = _post(
        mundo,
        PAQUETES.format(cid=cid),
        "cnt08_lector",
        mundo.company_a,
        {"proposito": "Propósito de prueba"},
    )
    assert r.status_code == 403


@ONLY_PG
def test_integridad(mundo, gobierno, ocupacion):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    doc_id, _ = _doc(mundo, f["exp"], "doc-compromiso")
    _compromiso(mundo, ocupacion, f["cdps"][0], "1000.00", f["exp"]["id"], doc_id)

    r = mundo.get(EXPEDIENTE.format(cid=cid) + "/integridad", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert set(cuerpo["resumen"].keys()) == {"VERIFIED", "MISSING", "MISMATCH", "NOT_APPLICABLE"}
    por_tipo = {d["tipo"]: d for d in cuerpo["documentos"]}
    assert por_tipo["INSTRUMENTO"]["resultado"] == "VERIFIED"
    assert por_tipo["COMPROBANTE_COMPROMISO"]["resultado"] == "MISSING"

    with mundo.factory() as db:
        contrato = db.get(GovernmentContract, cid)
        version_id = contrato.document_version_id
        version = db.get(DocumentVersion, version_id)
        stored = db.get(StoredFile, version.stored_file_id)
        clave = stored.storage_key
    get_storage()._resolve(clave).write_bytes(b"alterado")

    r = mundo.get(EXPEDIENTE.format(cid=cid) + "/integridad", "ua", mundo.company_a)
    assert r.status_code == 200
    por_tipo = {d["tipo"]: d for d in r.json()["documentos"]}
    assert por_tipo["INSTRUMENTO"]["resultado"] == "MISMATCH"


@ONLY_PG
def test_listado_filtros_y_paginacion(mundo, gobierno, ocupacion):
    f1 = _formalizado(mundo, ocupacion)
    f2 = _formalizado(mundo, ocupacion)
    c1, c2 = f1["contrato"]["id"], f2["contrato"]["id"]
    with mundo.factory() as db:
        codigo1 = db.get(GovernmentContract, c1).codigo
        codigo2 = db.get(GovernmentContract, c2).codigo

    r = mundo.get(LISTA + "?limit=1", "ua", mundo.company_a)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
    assert r.json()["total"] >= 2

    r = mundo.get(LISTA + f"?codigo={codigo1}", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["monto_vigente"] == "50000.00"
    assert r.json()["items"][0]["moneda"] == "USD"

    r = mundo.get(LISTA + "?contratista=texto-inexistente-xyz", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["total"] == 0

    r = mundo.get(LISTA + "?vigencia=VENCIDO", "ua", mundo.company_a)
    assert r.status_code == 200
    assert all(i["codigo"] not in {codigo1, codigo2} for i in r.json()["items"])

    sup, _ = _supervisor_designado(mundo, ocupacion, c1)
    r = mundo.get(LISTA + f"?supervisor={sup['nombre']}", "ua", mundo.company_a)
    assert r.status_code == 200
    codigos = {i["codigo"] for i in r.json()["items"]}
    assert codigo1 in codigos
    assert codigo2 not in codigos

    r = mundo.get(LISTA + "?limit=101", "ua", mundo.company_a)
    assert r.status_code == 422


@ONLY_PG
def test_paquete_generar_descargar_verificar(mundo, gobierno, ocupacion):
    esc = _escenario_completo(mundo, ocupacion)
    cid = esc["cid"]
    ruta = PAQUETES.format(cid=cid)
    r = mundo.client.post(
        f"/api/v1{ruta}",
        headers={**mundo.como("ua", mundo.company_a), "Idempotency-Key": "cnt08-k1"},
        json={"proposito": "Propósito de paquete CNT-08"},
    )
    assert r.status_code == 201, r.text
    paquete = r.json()
    assert paquete["codigo"].startswith("EC-")
    pid = paquete["id"]

    r = mundo.client.post(
        f"/api/v1{ruta}",
        headers={**mundo.como("ua", mundo.company_a), "Idempotency-Key": "cnt08-k1"},
        json={"proposito": "Propósito de paquete CNT-08"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == pid

    f2 = _formalizado(mundo, ocupacion)
    r = mundo.client.post(
        f"/api/v1{PAQUETES.format(cid=f2['contrato']['id'])}",
        headers={**mundo.como("ua", mundo.company_a), "Idempotency-Key": "cnt08-k1"},
        json={"proposito": "Propósito distinto"},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_DOSSIER_PACKAGE_IDEMPOTENCY_CONFLICT"

    r = mundo.get(ruta, "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = mundo.client.get(
        f"/api/v1{LISTA}/paquetes/{pid}/descargar",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    datos = r.content
    zf = zipfile.ZipFile(io.BytesIO(datos))
    nombres = set(zf.namelist())
    fijos = {
        "manifest.json",
        "SHA256SUMS",
        "LEEME.txt",
        "expediente.json",
        "cronologia.csv",
        "indice.csv",
        "referencias.json",
    }
    assert fijos <= nombres
    sumas = zf.read("SHA256SUMS").decode().splitlines()
    for linea in sumas:
        digest, ruta_zip = linea.split("  ")
        assert hashlib.sha256(zf.read(ruta_zip)).hexdigest() == digest

    manifiesto = json.loads(zf.read("manifest.json"))
    assert manifiesto["formato"] == "kontrol-gobierno-expediente-contractual"
    assert manifiesto["contract_code"] == esc["codigo"]
    assert len(manifiesto["excluded_sources"]) == 3
    assert manifiesto["hash_algorithm"] == "SHA-256"
    lineas_csv = zf.read("cronologia.csv").decode().splitlines()
    assert manifiesto["event_count"] == len(lineas_csv) - 1
    incluidos = [d for d in manifiesto["documentos"] if d["estado"] == "INCLUIDO"]
    assert manifiesto["document_count"] == len(incluidos)
    expediente_json = json.loads(zf.read("expediente.json"))
    assert expediente_json["modificaciones"]["cantidad"] == 1

    r = _verificar(mundo, datos)
    assert r.status_code == 200, r.text
    assert r.json()["resultado"] == "VALIDO"
    assert r.json()["identico"] is True

    alterado = _rehacer(datos, {"expediente.json": b'{"roto": true}'})
    r = _verificar(mundo, alterado)
    assert r.json()["resultado"] == "INVALIDO"
    assert any(m["codigo"] == "ARCHIVO_ALTERADO" for m in r.json()["motivos"])

    incompleto = _rehacer(datos, {"cronologia.csv": None})
    r = _verificar(mundo, incompleto)
    assert r.json()["resultado"] == "INCOMPLETO"
    assert any(m["codigo"] == "ARCHIVO_AUSENTE" for m in r.json()["motivos"])

    manifiesto_alterado = _rehacer(
        datos,
        {
            "manifest.json": json.dumps(
                {**json.loads(zipfile.ZipFile(io.BytesIO(datos)).read("manifest.json")), "generated_by": "alterado"}
            ).encode()
        },
    )
    r = _verificar(mundo, manifiesto_alterado)
    assert r.json()["resultado"] == "INVALIDO"
    assert any(m["codigo"] == "MANIFIESTO_ALTERADO" for m in r.json()["motivos"])

    r = _verificar(mundo, datos, usuario="ub", empresa=mundo.company_b)
    assert r.status_code == 200
    assert r.json()["resultado"] != "VALIDO"
    assert any(m["codigo"] == "PAQUETE_NO_REGISTRADO" for m in r.json()["motivos"])
    assert r.json()["paquete"] is None

    acciones: set[str] = set()
    for accion in [
        "GOV_CONTRACT_DOSSIER_PACKAGE_GENERATED",
        "GOV_CONTRACT_DOSSIER_PACKAGE_DOWNLOADED",
        "GOV_CONTRACT_DOSSIER_PACKAGE_VERIFIED",
        "GOV_CONTRACT_DOSSIER_PACKAGE_VERIFICATION_FAILED",
    ]:
        acciones.update(e.action for e in eventos(mundo, accion, pid))
    assert {"GOV_CONTRACT_DOSSIER_PACKAGE_GENERATED"} <= acciones
    assert "GOV_CONTRACT_DOSSIER_PACKAGE_DOWNLOADED" in acciones
    assert "GOV_CONTRACT_DOSSIER_PACKAGE_VERIFIED" in acciones
    assert "GOV_CONTRACT_DOSSIER_PACKAGE_VERIFICATION_FAILED" in acciones

    with mundo.factory() as db:
        with pytest.raises(DBAPIError) as excinfo:
            db.execute(
                text("UPDATE gov_contract_dossier_packages SET proposito = 'x' WHERE id = :id"),
                {"id": pid},
            )
            db.commit()
    assert "GOV_CONTRACT_DOSSIER_PACKAGE_IMMUTABLE" in str(excinfo.value)


@ONLY_PG
def test_paquete_snapshot_consistente(mundo, gobierno, ocupacion, monkeypatch):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    exp_id = f["exp"]["id"]
    original = service_expediente_contractual.cronologia_completa
    llamadas = {"n": 0}

    def envoltorio(db, ctx, c):
        resultado = original(db, ctx, c)
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            with mundo.factory() as otra:
                uid = otra.scalar(select(User.id).where(User.username == "ua"))
                ctx2 = CompanyContext(
                    tenant_id=mundo.t1,
                    company_id=mundo.company_a,
                    company=None,
                    user_id=uid,
                )
                expediente = otra.get(GovernmentProcurementFile, exp_id)
                service_expedientes._evento(
                    otra,
                    ctx2,
                    expediente,
                    "ACTUACION",
                    HOY,
                    "Actuación concurrente CNT-08",
                )
                otra.commit()
        return resultado

    monkeypatch.setattr(service_expediente_contractual, "cronologia_completa", envoltorio)

    r = _post(
        mundo,
        PAQUETES.format(cid=cid),
        "ua",
        mundo.company_a,
        {"proposito": "Snapshot REPEATABLE READ"},
    )
    assert r.status_code == 201, r.text
    paquete = r.json()
    datos = mundo.client.get(
        f"/api/v1{LISTA}/paquetes/{paquete['id']}/descargar",
        headers=mundo.como("ua", mundo.company_a),
    ).content
    archivos = zipfile.ZipFile(io.BytesIO(datos))
    csv = archivos.read("cronologia.csv").decode()
    assert "Actuación concurrente CNT-08" not in csv

    manifest = json.loads(archivos.read("manifest.json").decode())
    expediente_json = json.loads(archivos.read("expediente.json").decode())
    assert expediente_json["cronologia_total"] == manifest["event_count"]

    r = mundo.get(
        EXPEDIENTE.format(cid=cid) + "/cronologia?proceso=PROC-03",
        "ua",
        mundo.company_a,
    )
    titulos = [i["titulo"] for i in r.json()["items"]]
    assert "Actuación concurrente CNT-08" in titulos

@ONLY_PG
def test_mfa_y_permisos_reutilizados():
    assert classify("gobierno_paquetes:generate") == SENSITIVE
    assert "gobierno_expediente_contractual" not in CATALOGO_DE_PERMISOS


@ONLY_PG
def test_documento_sellado_sin_descarga_individual(mundo, gobierno, ocupacion):
    contrato = _formalizado(mundo, ocupacion)
    cid = contrato["contrato"]["id"]
    expediente = mundo.client.get(
        f"/api/v1/gobierno/contratos/{cid}/expediente", headers=mundo.como("ua", mundo.company_a)
    ).json()["documentos"]

    instrumento = next(
        entrada for entrada in expediente if entrada["tipo"] == "INSTRUMENTO"
    )
    comprobantes = [
        entrada for entrada in expediente if entrada["tipo"] == "COMPROBANTE_CDP"
    ]
    assert instrumento["sellado"] is True
    assert instrumento["descarga"] is None
    assert comprobantes
    for comprobante in comprobantes:
        assert comprobante["sellado"] is False
        assert comprobante["descarga"].startswith("/gobierno/presupuesto/ejercicios/")

    respuesta = mundo.client.get(
        f"/api/v1/documentos/{instrumento['document_id']}/versiones/{instrumento['version_id']}/descargar",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert respuesta.status_code == 404

    paquete = _post(
        mundo,
        f"/gobierno/contratos/{cid}/expediente/paquetes",
        "ua",
        mundo.company_a,
        {"proposito": "Paquete con documento sellado"},
    )
    assert paquete.status_code == 201
    paquete_id = paquete.json()["id"]

    zip_respuesta = mundo.client.get(
        f"/api/v1/gobierno/expedientes-contractuales/paquetes/{paquete_id}/descargar",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert zip_respuesta.status_code == 200
    with zipfile.ZipFile(io.BytesIO(zip_respuesta.content)) as archivo:
        manifiesto = json.loads(archivo.read("manifest.json"))
    entrada_manifiesto = next(
        entrada
        for entrada in manifiesto["documentos"]
        if entrada["clave"] == instrumento["clave"]
    )
    assert entrada_manifiesto["estado"] == "EXCLUIDO"
    assert entrada_manifiesto["motivo"] == "SELLADO"


@ONLY_PG
def test_ejecucion_cnt03_integrada(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    resp = _p(
        mundo,
        datos["cid"],
        "/inicio",
        {"fecha": HOY.isoformat(), "documento_id": _d(mundo, datos["exp"], "inicio-cnt08")},
        datos["usuario"],
    )
    assert resp.status_code == 201
    resp = _p(
        mundo,
        datos["cid"],
        "/hitos",
        {
            "descripcion": "Hito del expediente",
            "fecha_prevista": HOY.isoformat(),
            "monto_previsto": "1000.00",
            "obligatorio": True,
        },
        datos["usuario"],
    )
    assert resp.status_code == 201

    resp = mundo.get(f"/gobierno/contratos/{datos['cid']}/expediente", "ua", mundo.company_a)
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["ejecucion"]["estado_ejecucion"] == "EN_EJECUCION"
    assert any(h["descripcion"] == "Hito del expediente" for h in cuerpo["ejecucion"]["hitos"])
    assert cuerpo["ejecucion"]["enlace"].endswith("/ejecucion")

    resp = mundo.get(f"/gobierno/contratos/{datos['cid']}/expediente/cronologia?proceso=CNT-03", "ua", mundo.company_a)
    assert resp.status_code == 200
    tipos = [n["tipo"] for n in resp.json()["items"]]
    assert "EJECUCION_INICIO" in tipos
    assert "EJECUCION_HITO" in tipos

    resp = _post(mundo, f"/gobierno/contratos/{datos['cid']}/expediente/paquetes", "ua", mundo.company_a, {"proposito": "Paquete con ejecucion CNT-03"})
    assert resp.status_code == 201
    paquete_id = resp.json()["id"]
    contenido = mundo.client.get(f"/api/v1/gobierno/expedientes-contractuales/paquetes/{paquete_id}/descargar", headers=mundo.como("ua", mundo.company_a)).content
    manifest = json.loads(zipfile.ZipFile(io.BytesIO(contenido)).read("manifest.json"))
    assert "CNT-03" in manifest["included_sources"]
    assert len(manifest["excluded_sources"]) == 3
