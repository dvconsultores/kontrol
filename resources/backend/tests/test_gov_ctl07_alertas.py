"""Pruebas de backend para las alertas de operaciones atípicas de Gobierno (CTL-07)."""

import json
import os
import re
from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError
from app.modules.government.models import GovernmentAtypicalAlertReview, GovernmentProcurementOffer
from app.modules.government.service_alertas import revisar_alerta
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.shared.audit import record_audit
from tests.concurrency import carrera
from tests.org04_ayudantes import O, crear_funcionario
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc03_expedientes import E, _base

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="CTL-07 se verifica sobre PostgreSQL",
)

A = "/gobierno/control/alertas"
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _marca() -> str:
    return uuid4().hex[:8]


def _uid(mundo, username: str) -> str:
    with mundo.factory() as db:
        return db.execute(select(User).where(User.username == username)).scalar_one().id


def _expediente(mundo, ocupacion, objeto: str, unidad: str = "unidad_raiz") -> dict:
    funcionario = crear_funcionario(mundo)
    cuerpo = {
        "numero": f"EX-{uuid4().hex[:8]}",
        **_base(mundo, ocupacion, funcionario["id"]),
        "objeto": objeto,
        "unidad_id": ocupacion[unidad],
    }
    r = _post(mundo, E, "ua", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _descartar(mundo, exp: dict) -> None:
    r = _post(mundo, f"{E}/{exp['id']}/descartar", "ua", mundo.company_a, {"motivo": "Descartado en la prueba"}, version=exp["version"])
    assert r.status_code == 200, r.text


def _funcionario_con_documento(mundo, nombre: str, numero: str) -> str:
    r = _post(
        mundo,
        f"{O}/funcionarios",
        "ua",
        mundo.company_a,
        {"nombre": nombre, "tipo_documento": "V", "numero_documento": numero},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _oferta(mundo, exp: dict, oferente_nombre: str, documento: str, receptor_id: str) -> str:
    with mundo.factory() as db:
        oferta = GovernmentProcurementOffer(
            company_id=mundo.company_a,
            file_id=exp["id"],
            numero=1,
            oferente_nombre=oferente_nombre,
            oferente_documento=documento,
            representante=None,
            tipo_sobre="UNICO",
            canal="UNIDAD_CONTRATANTE",
            recibida_en=datetime.now(UTC),
            official_id=receptor_id,
            receptor_etiqueta="Receptor de la prueba",
            condicion_sobre="Sobre cerrado",
            confidencial=True,
            fundamento_confidencialidad="Prueba",
            modalidad_al_recibir=None,
        )
        db.add(oferta)
        db.commit()
        return str(oferta.id)


def _evento_sod(mundo, user_id: str, empresa: str, marca: str, rol: bool = False) -> str:
    with mundo.factory() as db:
        if not rol:
            evento = record_audit(
                db,
                action="GOV_SOD_CONFLICT_BLOCKED",
                entity_type="GovernmentSoDRule",
                entity_id=str(uuid4()),
                tenant_id=mundo.t1,
                company_id=empresa,
                user_id=user_id,
                after={
                    "accion": "CTL06_VERIFICAR",
                    "accion_previa": "CTL06_VERIFICAR",
                    "proceso": "CTL-06",
                    "regla_codigo": f"SOD-{marca}",
                },
            )
        else:
            evento = record_audit(
                db,
                action="GOV_SOD_ROLE_CONFLICT_BLOCKED",
                entity_type="GovernmentProcurementFile",
                entity_id=str(uuid4()),
                tenant_id=mundo.t1,
                company_id=empresa,
                user_id=user_id,
                after={
                    "expediente_numero": f"EX-{marca}",
                    "funcion": "SOLICITANTE",
                    "funcion_previa": "RECEPTOR",
                    "regla_codigo": f"SODF-{marca}",
                },
            )
        db.commit()
        return str(evento.id)


def _alertas(mundo, usuario: str = "ua", empresa: str | None = None, **filtros) -> dict:
    query = urlencode({k: v for k, v in filtros.items() if v is not None})
    r = mundo.get(f"{A}?{query}" if query else A, usuario, empresa or mundo.company_a)
    assert r.status_code == 200, r.text
    return r.json()


def _con_marca(datos: dict, tipo: str, marca: str) -> list[dict]:
    return [
        alerta
        for alerta in datos["alertas"]
        if alerta["tipo"] == tipo and marca in json.dumps(alerta, ensure_ascii=False)
    ]


def _revisar(mundo, clave: str, usuario: str = "ua", empresa: str | None = None, resultado: str = "SIN_OBSERVACION", observacion: str = "Revisada sin observaciones relevantes."):
    return _post(
        mundo,
        f"{A}/revisiones",
        usuario,
        empresa or mundo.company_a,
        {"clave": clave, "resultado": resultado, "observacion": observacion},
    )


def _filas(mundo) -> int:
    with mundo.factory() as db:
        return db.execute(text("SELECT count(*) FROM gov_atypical_alert_reviews")).scalar_one()


def _auditorias(mundo) -> int:
    with mundo.factory() as db:
        return db.execute(text("SELECT count(*) FROM audit_events WHERE action = 'GOV_ATYPICAL_ALERT_REVIEWED'")).scalar_one()


def test_duplicidad_por_par(mundo, gobierno, ocupacion):
    """Detecta únicamente la duplicidad entre dos expedientes activos de la misma unidad y objeto normalizado."""
    marca = _marca()
    objeto = f"Adquisición de papelería {marca}"
    e1 = _expediente(mundo, ocupacion, objeto)
    e2 = _expediente(mundo, ocupacion, f"  adquisicion de PAPELERÍA   {marca} ")
    e3 = _expediente(mundo, ocupacion, objeto, unidad="unidad_otra")
    e4 = _expediente(mundo, ocupacion, objeto)
    _descartar(mundo, e4)

    datos = _alertas(mundo)
    alertas = _con_marca(datos, "DUPLICIDAD", marca)
    assert len(alertas) == 1
    alerta = alertas[0]
    assert alerta["clave"].startswith("DUPLICIDAD:")
    assert str(e1["id"]) in alerta["clave"]
    assert str(e2["id"]) in alerta["clave"]
    assert str(e3["id"]) not in alerta["clave"]
    assert str(e4["id"]) not in alerta["clave"]
    sujetos_expediente = [s["valor"] for s in alerta["sujetos"] if s["etiqueta"] == "Expediente"]
    assert e1["numero"] in " ".join(sujetos_expediente)
    assert e2["numero"] in " ".join(sujetos_expediente)
    assert alerta["estado"] == "PENDIENTE"
    assert alerta["vigente"] is True
    for texto in [alerta["titulo"], alerta["detalle"], *[s["valor"] for s in alerta["sujetos"]]]:
        assert not UUID_RE.search(texto)


def test_proveedor_relacionado_con_documento_enmascarado(mundo, gobierno, ocupacion):
    """El proveedor relacionado enmascara el documento y no crea falsas alertas con documentos distintos."""
    marca = _marca()
    numero = f"{uuid4().int % 10**8:08d}"
    funcionario_id = _funcionario_con_documento(mundo, f"Funcionaria {marca}", numero)
    exp = _expediente(mundo, ocupacion, f"Papelería proveedor {marca}")
    receptor = crear_funcionario(mundo)["id"]
    _oferta(mundo, exp, f"Oferente {marca}", "V" + numero, receptor)

    datos = _alertas(mundo)
    alertas = _con_marca(datos, "PROVEEDOR_RELACIONADO", marca)
    assert len(alertas) == 1
    alerta = alertas[0]
    assert funcionario_id in alerta["clave"]
    sujeto_funcionario = [s["valor"] for s in alerta["sujetos"] if s["etiqueta"] == "Funcionario"]
    assert any(f"V-******{numero[-2:]}" in valor for valor in sujeto_funcionario)
    assert numero not in json.dumps(alerta, ensure_ascii=False)
    assert alerta["es_sujeto"] is False

    exp2 = _expediente(mundo, ocupacion, f"Otro expediente proveedor {marca}")
    _oferta(mundo, exp2, f"Otro oferente {marca}", "V99999999", receptor)

    datos = _alertas(mundo)
    alertas = _con_marca(datos, "PROVEEDOR_RELACIONADO", marca)
    assert len(alertas) == 1


def test_autoaprobacion_desde_eventos_sod(mundo, gobierno, ocupacion):
    """Las alertas de autoaprobación nacen de eventos SOD y su es_sujeto depende del usuario consultante."""
    marca = _marca()
    uid_uab = _uid(mundo, "uab")
    uid_ub = _uid(mundo, "ub")
    _evento_sod(mundo, uid_uab, mundo.company_a, marca)
    _evento_sod(mundo, uid_uab, mundo.company_a, marca, rol=True)
    _evento_sod(mundo, uid_ub, mundo.company_b, marca)

    datos_a = _alertas(mundo, "ua", mundo.company_a)
    alertas_a = _con_marca(datos_a, "AUTOAPROBACION", marca)
    assert len(alertas_a) == 2
    titulos = {alerta["titulo"] for alerta in alertas_a}
    assert titulos == {"Intento bloqueado por segregación de funciones", "Intento bloqueado por funciones incompatibles"}
    sujetos = [s for alerta in alertas_a for s in alerta["sujetos"] if s["etiqueta"] == "Usuario"]
    assert all(s["valor"] == "uab" for s in sujetos)
    assert all(alerta["es_sujeto"] is False for alerta in alertas_a)

    datos_uab = _alertas(mundo, "uab", mundo.company_a)
    alertas_uab = _con_marca(datos_uab, "AUTOAPROBACION", marca)
    assert len(alertas_uab) == 2
    assert all(alerta["es_sujeto"] is True for alerta in alertas_uab)

    datos_b = _alertas(mundo, "ub", mundo.company_b)
    alertas_b = _con_marca(datos_b, "AUTOAPROBACION", marca)
    assert len(alertas_b) == 1
    assert all(s["valor"] == "ub" for alerta in alertas_b for s in alerta["sujetos"] if s["etiqueta"] == "Usuario")


def test_tipos_y_aviso(mundo, gobierno, ocupacion):
    """La respuesta incluye el aviso institucional y los cinco tipos en el orden y con la disponibilidad esperados."""
    datos = _alertas(mundo)
    assert datos["aviso"] == "Una alerta es una señal para revisar; no es una acusación ni una conclusión."
    assert [t["codigo"] for t in datos["tipos"]] == [
        "DUPLICIDAD",
        "PROVEEDOR_RELACIONADO",
        "AUTOAPROBACION",
        "FRACCIONAMIENTO",
        "OVERRIDE_FRECUENTE",
    ]
    no_disponibles = {t["codigo"]: t for t in datos["tipos"] if not t["disponible"]}
    assert set(no_disponibles) == {"FRACCIONAMIENTO", "OVERRIDE_FRECUENTE"}
    for codigo in ("FRACCIONAMIENTO", "OVERRIDE_FRECUENTE"):
        assert no_disponibles[codigo]["motivo_no_disponible"]
        assert no_disponibles[codigo]["requisito_habilitante"]
        assert no_disponibles[codigo]["total"] == 0
    for tipo in datos["tipos"]:
        if tipo["codigo"] not in no_disponibles:
            assert tipo["disponible"] is True
    assert not any(alerta["tipo"] in no_disponibles for alerta in datos["alertas"])


def test_revision_valida_y_auditada(mundo, gobierno, ocupacion):
    """Una revisión válida persiste, audita y filtra por estado."""
    marca = _marca()
    uid_uab = _uid(mundo, "uab")
    clave_deteccion = _evento_sod(mundo, uid_uab, mundo.company_a, marca)
    datos = _alertas(mundo)
    alerta = [a for a in datos["alertas"] if a["clave"] == f"AUTOAPROBACION:{clave_deteccion}"][0]

    filas_antes = _filas(mundo)
    auditorias_antes = _auditorias(mundo)
    observacion = "Revisar con la unidad la causa del intento."
    r = _revisar(mundo, alerta["clave"], "ua", mundo.company_a, "REQUIERE_SEGUIMIENTO", observacion)
    assert r.status_code == 201, r.text
    revisada = r.json()
    assert revisada["estado"] == "REVISADA"
    assert revisada["revision"]["resultado"] == "REQUIERE_SEGUIMIENTO"
    assert revisada["revision"]["resultado_etiqueta"] == "Requiere seguimiento"
    assert revisada["revision"]["revisada_por"] == "ua"
    assert revisada["revision"]["observacion"] == observacion

    assert _filas(mundo) == filas_antes + 1
    assert _auditorias(mundo) == auditorias_antes + 1
    with mundo.factory() as db:
        fila = db.execute(
            text("SELECT id FROM gov_atypical_alert_reviews WHERE clave = :c"),
            {"c": alerta["clave"]},
        ).scalar_one()
        total = db.execute(
            text("SELECT count(*) FROM audit_events WHERE action = 'GOV_ATYPICAL_ALERT_REVIEWED' AND entity_id = :id"),
            {"id": fila},
        ).scalar_one()
        assert total == 1

    assert _con_marca(_alertas(mundo, estado="REVISADA"), "AUTOAPROBACION", marca)
    assert not _con_marca(_alertas(mundo, estado="PENDIENTE"), "AUTOAPROBACION", marca)


def test_rechazos_no_escriben(mundo, gobierno, ocupacion):
    """Los rechazos de validación o de clave no dejan filas ni auditorías."""
    marca = _marca()
    uid_uab = _uid(mundo, "uab")
    _evento_sod(mundo, uid_uab, mundo.company_a, marca)
    datos = _alertas(mundo)
    clave_real = [a for a in datos["alertas"] if a["tipo"] == "AUTOAPROBACION" and marca in json.dumps(a, ensure_ascii=False)][0]["clave"]

    filas_antes = _filas(mundo)
    auditorias_antes = _auditorias(mundo)

    r = _revisar(mundo, "DUPLICIDAD:no:existe")
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_ALERT_NOT_FOUND"

    r = _revisar(mundo, "FRACCIONAMIENTO:x")
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_ALERT_NOT_FOUND"

    r = _revisar(mundo, clave_real, resultado="OTRO")
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_ALERT_REVIEW_INVALID"

    r = _revisar(mundo, clave_real, observacion="corta")
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_ALERT_REVIEW_INVALID"

    r = _revisar(mundo, clave_real, observacion="x" * 2001)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_ALERT_REVIEW_INVALID"

    r = mundo.get(f"{A}?tipo=INVENTADO", "ua", mundo.company_a)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_ALERT_FILTER_INVALID"

    assert _filas(mundo) == filas_antes
    assert _auditorias(mundo) == auditorias_antes


def test_autorrevision_y_doble_revision(mundo, gobierno, ocupacion):
    """No se permite revisar la propia alerta ni revisar dos veces la misma alerta."""
    marca = _marca()
    uid_ua = _uid(mundo, "ua")
    _evento_sod(mundo, uid_ua, mundo.company_a, marca)
    datos = _alertas(mundo)
    clave = [a for a in datos["alertas"] if a["tipo"] == "AUTOAPROBACION" and marca in json.dumps(a, ensure_ascii=False)][0]["clave"]

    filas_antes = _filas(mundo)
    r = _revisar(mundo, clave, usuario="ua")
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_ALERT_SELF_REVIEW"

    r = _revisar(mundo, clave, usuario="uab")
    assert r.status_code == 201, r.text

    r = _revisar(mundo, clave, usuario="ua")
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_ALERT_ALREADY_REVIEWED"

    assert _filas(mundo) == filas_antes + 1


def test_permisos(mundo, gobierno, ocupacion):
    """Solo la capacidad de vista permite consultar y la de revisión es necesaria para escribir."""
    marca = _marca()
    uid_uab = _uid(mundo, "uab")
    _evento_sod(mundo, uid_uab, mundo.company_a, marca)
    clave = [a for a in _alertas(mundo)["alertas"] if a["tipo"] == "AUTOAPROBACION" and marca in json.dumps(a, ensure_ascii=False)][0]["clave"]

    nombre_ver = f"solo_ver_{marca}"
    cuenta_con_permisos(mundo, nombre_ver, [("gobierno_alertas", "view")])
    r = mundo.get(A, nombre_ver, mundo.company_a)
    assert r.status_code == 200, r.text
    r = _post(mundo, f"{A}/revisiones", nombre_ver, mundo.company_a, {"clave": clave, "resultado": "SIN_OBSERVACION", "observacion": "Observación válida para la prueba."})
    assert r.status_code == 403, r.text

    nombre_sin = f"sin_permisos_{marca}"
    cuenta_con_permisos(mundo, nombre_sin, [])
    r = mundo.get(A, nombre_sin, mundo.company_a)
    assert r.status_code == 403, r.text


def test_aislamiento_entre_empresas(mundo, gobierno, ocupacion):
    """Las alertas de una empresa no son visibles para usuarios de otra ni siquiera compartiendo tenencia."""
    marca = _marca()
    e1 = _expediente(mundo, ocupacion, f"Papelería aislada {marca}")
    e2 = _expediente(mundo, ocupacion, f"papeleria aislada {marca}")
    datos_a = _alertas(mundo, "ua", mundo.company_a)
    alerta_a = [a for a in datos_a["alertas"] if a["tipo"] == "DUPLICIDAD" and str(e1["id"]) in a["clave"] and str(e2["id"]) in a["clave"]][0]

    datos_b = _alertas(mundo, "ub", mundo.company_b)
    assert not _con_marca(datos_b, "DUPLICIDAD", marca)

    r = _revisar(mundo, alerta_a["clave"], usuario="ub", empresa=mundo.company_b)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_ALERT_NOT_FOUND"

    datos_uab_b = _alertas(mundo, "uab", mundo.company_b)
    assert not _con_marca(datos_uab_b, "DUPLICIDAD", marca)


def test_carrera_de_revisiones(mundo, gobierno, ocupacion):
    """La concurrencia al revisar la misma alerta produce un ConflictError para la segunda transacción."""
    marca = _marca()
    uid_uab = _uid(mundo, "uab")
    _evento_sod(mundo, uid_uab, mundo.company_a, marca)
    clave = [a for a in _alertas(mundo)["alertas"] if a["tipo"] == "AUTOAPROBACION" and marca in json.dumps(a, ensure_ascii=False)][0]["clave"]
    uid_ua = _uid(mundo, "ua")

    def primero(s):
        s.add(
            GovernmentAtypicalAlertReview(
                company_id=mundo.company_a,
                clave=clave,
                tipo="AUTOAPROBACION",
                resultado="SIN_OBSERVACION",
                observacion="Primera revisión de la carrera.",
                resumen="Resumen",
                revisada_por=uid_ua,
                revisada_en=datetime.now(UTC),
                created_by=uid_ua,
            )
        )

    def segundo(s):
        ctx = CompanyContext(
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            company=s.get(Company, mundo.company_a),
            user_id=uid_ua,
        )
        return revisar_alerta(
            s,
            ctx,
            usuario_id=uid_ua,
            clave=clave,
            resultado="SIN_OBSERVACION",
            observacion="Segunda revisión de la carrera.",
        )

    r1, r2 = carrera(mundo.factory, primero, segundo)
    assert isinstance(r2, ConflictError)
    assert r2.code == "GOV_ALERT_ALREADY_REVIEWED"

    with mundo.factory() as db:
        fila = db.execute(
            text("SELECT observacion FROM gov_atypical_alert_reviews WHERE clave = :c"),
            {"c": clave},
        ).scalar_one()
        assert fila == "Primera revisión de la carrera."
        total = db.execute(text("SELECT count(*) FROM gov_atypical_alert_reviews WHERE clave = :c"), {"c": clave}).scalar_one()
        assert total == 1


def test_revision_inmutable(mundo, gobierno, ocupacion):
    """Las revisiones no admiten UPDATE ni DELETE y conservan su contenido original."""
    marca = _marca()
    uid_uab = _uid(mundo, "uab")
    _evento_sod(mundo, uid_uab, mundo.company_a, marca)
    clave = [a for a in _alertas(mundo)["alertas"] if a["tipo"] == "AUTOAPROBACION" and marca in json.dumps(a, ensure_ascii=False)][0]["clave"]
    r = _revisar(mundo, clave)
    assert r.status_code == 201, r.text

    with mundo.factory() as db:
        with pytest.raises(DBAPIError) as exc_info:
            db.execute(
                text("UPDATE gov_atypical_alert_reviews SET observacion = 'Cambiada en la prueba' WHERE clave = :c"),
                {"c": clave},
            )
        assert "GOV_ATYPICAL_ALERT_REVIEW_IMMUTABLE" in str(exc_info.value)
        db.rollback()

    with mundo.factory() as db:
        with pytest.raises(DBAPIError) as exc_info:
            db.execute(text("DELETE FROM gov_atypical_alert_reviews WHERE clave = :c"), {"c": clave})
        assert "GOV_ATYPICAL_ALERT_REVIEW_IMMUTABLE" in str(exc_info.value)
        db.rollback()

    with mundo.factory() as db:
        resultado, observacion = db.execute(
            text("SELECT resultado, observacion FROM gov_atypical_alert_reviews WHERE clave = :c"),
            {"c": clave},
        ).one()
        assert resultado == "SIN_OBSERVACION"
        assert observacion == "Revisada sin observaciones relevantes."


def test_revisada_que_ya_no_se_detecta(mundo, gobierno, ocupacion):
    """Una revisión permanece listada como REVISADA aunque su detección desaparezca."""
    marca = _marca()
    e1 = _expediente(mundo, ocupacion, f"Papelería revisada {marca}")
    e2 = _expediente(mundo, ocupacion, f"papeleria revisada {marca}")
    datos = _alertas(mundo)
    alerta = [a for a in datos["alertas"] if a["tipo"] == "DUPLICIDAD" and str(e1["id"]) in a["clave"] and str(e2["id"]) in a["clave"]][0]

    r = _revisar(mundo, alerta["clave"])
    assert r.status_code == 201, r.text

    e2_actual = mundo.get(f"{E}/{e2['id']}", "ua", mundo.company_a).json()
    _descartar(mundo, e2_actual)

    clave = alerta["clave"]
    datos = _alertas(mundo)
    persistente = [a for a in datos["alertas"] if a["clave"] == clave]
    assert len(persistente) == 1
    assert persistente[0]["estado"] == "REVISADA"
    assert persistente[0]["vigente"] is False
