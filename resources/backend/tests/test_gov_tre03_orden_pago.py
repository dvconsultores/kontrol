"""TRE-03 · Orden de pago (GOV-TRE-003) — pruebas backend sobre PostgreSQL."""
from __future__ import annotations

import threading
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentLink, DocumentType, DocumentVersion
from app.modules.government.models import (
    GovernmentPosition,
    GovernmentPositionCompetency,
    GovernmentPositionVersion,
)
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.identity_access.models import User, UserScope
from app.shared.clock import hoy_de_negocio
from tests import test_gov_bud08 as _bud08
from tests import test_gov_bud09_causado as _bud09
from tests.org04_ayudantes import (
    D,
    _codigo,
    acto_eficaz,
    crear_funcionario,
)
from tests.org06_guarda import cuenta_con_permisos, exigir_identidad
from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_bud08 import _cdp, _comprometer
from tests.test_gov_bud09_causado import (
    _activar_politica as _activar_politica_b09,
)
from tests.test_gov_bud09_causado import (
    _causar,
    _detalle,
    _formalizado,
    _post,
    _preparar,
    _tipo_documento_soporte,
)
from tests.test_gov_bud09_causado import (
    _cuentas as _cuentas_b09,
)
from tests.test_gov_bud09_causado import (
    _politica as _politica_b09,
)
from tests.test_gov_ctl01_reglas import activar_regla, cerrar_regla, crear_regla
from tests.test_gov_ctl06_hallazgos import _post as _post_ctl06

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

ORDENES = "/gobierno/tesoreria"
POLITICAS_OP = "/gobierno/tesoreria/politicas-orden-pago"
CONFIG_OP = "/gobierno/tesoreria/ordenes-pago/configuracion"

_CUENTAS_T03: dict[int, None] = {}
_PARTIDA_CICLO_T03: int = 0
_PARTIDAS_T03 = ["401.01", "402", "403", "404", "405", "406", "407"]


@pytest.fixture(scope="module", autouse=True)
def _aislar_caches_heredadas():
    """Limpia cachés por mundo de BUD-08/BUD-09 ya que el mundo es por módulo."""
    _bud08._ESTADO.clear()
    _bud09._CUENTAS.clear()
    _bud09._TIPO_SOPORTE.clear()
    _CUENTAS_T03.clear()
    yield
    _bud08._ESTADO.clear()
    _bud09._CUENTAS.clear()
    _bud09._TIPO_SOPORTE.clear()
    _CUENTAS_T03.clear()


def _get_op(mundo, ruta, usuario="ord_t03", empresa=None):
    return mundo.get(ruta, usuario, empresa or mundo.company_a)


def _put_op(mundo, ruta, usuario, cuerpo, version, empresa=None):
    return mundo.client.put(
        f"/api/v1{ruta}",
        headers={
            **mundo.como(usuario, empresa or mundo.company_a),
            "If-Match": str(version),
        },
        json=cuerpo,
    )


def _post_op(mundo, ruta, usuario, cuerpo, empresa=None, version=None):
    headers = mundo.como(usuario, empresa or mundo.company_a)
    if version is not None:
        headers["If-Match"] = str(version)
    return mundo.client.post(f"/api/v1{ruta}", headers=headers, json=cuerpo)


def _cuentas_t03(mundo) -> None:
    if id(mundo) in _CUENTAS_T03:
        return
    cuenta_con_permisos(
        mundo,
        "ord_t03",
        [
            ("gobierno_ordenes_pago", "view"),
            ("gobierno_ordenes_pago", "manage"),
            ("gobierno_ordenes_pago", "issue"),
            ("gobierno_ordenes_pago", "cancel"),
            ("gobierno_ordenes_pago", "policy"),
            ("gobierno_presupuesto", "view"),
        ],
    )
    cuenta_con_permisos(mundo, "ver_t03", [("gobierno_ordenes_pago", "view")])
    _cuentas_b09(mundo)
    _CUENTAS_T03[id(mundo)] = None


def _cargo_ordenar(
    mundo,
    ocupacion,
    tipo_limite="SIN_LIMITE",
    monto=None,
    moneda=None,
    valid_from=None,
    valid_to=None,
) -> str:
    structure_id = ocupacion["estructura"]
    unit_id = ocupacion["unidad_raiz"]
    with mundo.factory() as db:
        cargo = GovernmentPosition(
            company_id=mundo.company_a,
            structure_id=structure_id,
            unit_id=unit_id,
            code=_codigo("O"),
            name=f"Cargo ordenar {_codigo('N')}",
            status="INACTIVO" if valid_to is not None else "VIGENTE",
            valid_from=valid_from or D(1, 1),
            valid_to=valid_to,
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo)
        db.flush()

        comp = GovernmentPositionCompetency(
            position_id=cargo.id,
            company_id=mundo.company_a,
            action="ORDENAR_PAGO",
            subject="TESORERIA",
            limit_type=tipo_limite,
            limit_amount=monto,
            limit_currency=moneda,
            basis="Fundamento de prueba TRE-03",
        )
        db.add(comp)

        version = GovernmentPositionVersion(
            position_id=cargo.id,
            structure_id=structure_id,
            company_id=mundo.company_a,
            version=1,
            status="INACTIVO" if valid_to is not None else "VIGENTE",
            snapshot={
                "competencias": [
                    {
                        "accion": "ORDENAR_PAGO",
                        "materia": "TESORERIA",
                        "tipo_limite": tipo_limite,
                        "monto": monto,
                        "moneda": moneda,
                    }
                ]
            },
            reason=None,
            actor_id=None,
        )
        db.add(version)
        db.commit()
        return str(cargo.id)


def _politica_op(mundo, **cambios) -> dict:
    codigo = "OP" + uuid4().hex[:12].upper()
    cuerpo = {
        "codigo": codigo,
        "nombre": "Política de orden de pago de prueba",
        "vigente_desde": hoy_de_negocio().isoformat(),
        "fundamento": "Fundamento de la política de orden de pago.",
        "requiere_expediente_completo": False,
        "competencia_accion": "ORDENAR_PAGO",
        "competencia_materia": "TESORERIA",
    }
    cuerpo.update(cambios)
    r = _post_op(mundo, POLITICAS_OP, "ord_t03", cuerpo)
    assert r.status_code == 201, r.text
    politica = r.json()
    r2 = _post_op(
        mundo,
        f"{POLITICAS_OP}/{politica['id']}/activar",
        "ord_t03",
        {"fundamento": "Fundamento suficiente para activar la política de orden de pago."},
        version=politica["version"],
    )
    assert r2.status_code == 200, r2.text
    return r2.json()


def _partida_rotante() -> str:
    global _PARTIDA_CICLO_T03
    partida = _PARTIDAS_T03[_PARTIDA_CICLO_T03 % len(_PARTIDAS_T03)]
    _PARTIDA_CICLO_T03 += 1
    return partida


def _causado_formalizado(
    mundo,
    s,
    monto="100.00",
    beneficiario="Proveedor Uno C.A.",
    usuario="caus_b09",
    **cambios,
) -> dict:
    partida = _partida_rotante()
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, partida, monto)["id"], "monto": monto}],
    )
    assert r.status_code == 201, r.text
    compromiso = r.json()
    politica = _politica_b09(mundo)
    politica = _activar_politica_b09(mundo, politica)
    causado = _causar(
        mundo,
        s,
        compromiso,
        s["cargo_causar"],
        politica,
        monto=monto,
        beneficiario=beneficiario,
        **cambios,
    )
    _formalizado(mundo, causado["id"], causado["version"])
    detalle = _detalle(mundo, causado["id"])
    detalle["compromiso_id"] = compromiso["id"]
    detalle["politica_id"] = politica["id"]
    return detalle


def _causado_formalizado_usuario(
    mundo,
    s,
    usuario,
    monto="50.00",
    beneficiario="Proveedor Uno C.A.",
) -> dict:
    partida = _partida_rotante()
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, partida, monto)["id"], "monto": monto}],
    )
    assert r.status_code == 201, r.text
    compromiso = r.json()
    politica = _politica_b09(mundo)
    politica = _activar_politica_b09(mundo, politica)
    causado = _causar(
        mundo,
        s,
        compromiso,
        s["cargo_causar"],
        politica,
        monto=monto,
        beneficiario=beneficiario,
    )
    _formalizado(mundo, causado["id"], causado["version"])
    detalle = _detalle(mundo, causado["id"])
    detalle["compromiso_id"] = compromiso["id"]
    detalle["politica_id"] = politica["id"]
    return detalle


def _borrador(
    mundo,
    s,
    politica,
    lineas,
    cargo,
    fecha=None,
    documentos=None,
    usuario="ord_t03",
):
    cuerpo = {
        "policy_id": politica["id"],
        "fecha_orden": fecha.isoformat() if isinstance(fecha, date) else hoy_de_negocio().isoformat(),
        "concepto": "Orden de pago de prueba TRE-03",
        "lineas": lineas,
        "autoridad_cargo_id": cargo,
    }
    if documentos:
        cuerpo["documentos"] = documentos
    return _post_op(
        mundo,
        f"{ORDENES}/ejercicios/{s['year_id']}/ordenes-pago",
        usuario,
        cuerpo,
    )


def _emitir(mundo, orden, usuario="ord_t03"):
    return _post_op(
        mundo,
        f"{ORDENES}/ordenes-pago/{orden['id']}/emitir",
        usuario,
        {},
        version=orden["version"],
    )


def _anular(
    mundo,
    orden,
    cargo,
    motivo="Anulación de prueba de la orden",
    usuario="ord_t03",
):
    return _post_op(
        mundo,
        f"{ORDENES}/ordenes-pago/{orden['id']}/anular",
        usuario,
        {"motivo": motivo, "cargo_id": cargo},
        version=orden["version"],
    )


def _eventos(mundo, accion, entity_id):
    with mundo.factory() as db:
        return db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.company_id == mundo.company_a,
                AuditEvent.entity_id == entity_id,
                AuditEvent.action == accion,
            )
            .order_by(AuditEvent.created_at)
        ).all()


def _crear_documento_ejercicio(mundo, s, tipo_documento_id=None) -> str:
    with mundo.factory() as db:
        if tipo_documento_id is None:
            tipo = DocumentType(
                company_id=mundo.company_a,
                code=f"T03-{_codigo('T')}",
                name=f"Tipo documental TRE-03 {_codigo('N')}",
                status="ACTIVE",
            )
            db.add(tipo)
            db.flush()
            tipo_documento_id = str(tipo.id)
        documento = Document(
            company_id=mundo.company_a,
            document_type_id=tipo_documento_id,
            title=f"Documento TRE-03 {_codigo('N')}",
            status="ACTIVE",
        )
        db.add(documento)
        db.flush()
        db.add(
            DocumentLink(
                company_id=mundo.company_a,
                document_id=str(documento.id),
                resource_type="GovernmentBudgetYear",
                resource_id=s["year_id"],
            )
        )
        db.commit()
        return str(documento.id)


def _version_documento(mundo, documento_id):
    with mundo.factory() as db:
        documento = db.get(Document, documento_id)
        assert documento is not None
        version = DocumentVersion(
            document_id=documento_id,
            company_id=mundo.company_a,
            version_number=1,
            sha256=_sha256_prueba(),
            status="ACTIVE",
        )
        db.add(version)
        db.flush()
        documento.current_version_id = version.id
        db.commit()
        return str(version.id)


def _sha256_prueba() -> str:
    return uuid4().hex + uuid4().hex


def _expect_montos_orden_detalle(detalle: dict, monto_ordenado: str, pendiente: str) -> None:
    assert detalle.get("monto_ordenado") == monto_ordenado
    assert detalle.get("pendiente_de_ordenar") == pendiente


@ONLY_PG
def test_t03_01_causado_formalizado_elegible(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s)
    _politica_op(mundo)
    _cargo_ordenar(mundo, ocupacion)

    r = _get_op(mundo, f"{ORDENES}/ejercicios/{s['year_id']}/ordenes-pago/opciones")
    assert r.status_code == 200, r.text
    obligaciones = r.json()["obligaciones"]
    assert any(o["id"] == causado["id"] for o in obligaciones)
    for obligacion in obligaciones:
        if obligacion["id"] == causado["id"]:
            assert obligacion["pendiente_de_ordenar"] == causado["monto"]
            assert obligacion["elegible"] is True


@ONLY_PG
def test_t03_02_causado_borrador_no_elegible(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    partida = _partida_rotante()
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, partida, "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    politica_b09 = _politica_b09(mundo)
    politica_b09 = _activar_politica_b09(mundo, politica_b09)
    causado = _causar(
        mundo, s, compromiso, s["cargo_causar"], politica_b09, monto="100.00"
    )
    politica_op = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r2 = _borrador(
        mundo,
        s,
        politica_op,
        [{"cause_id": causado["id"], "monto": "100.00"}],
        cargo,
    )
    assert r2.status_code == 422
    assert r2.json()["code"] == "GOV_PAYMENT_ORDER_CAUSE_NOT_ELIGIBLE"


@ONLY_PG
def test_t03_03_causado_anulado_no_elegible(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s)
    r_anular = _post(
        mundo,
        f"/gobierno/presupuesto/causados/{causado['id']}/anular",
        "caus_b09",
        mundo.company_a,
        {"motivo": "Anulación de prueba"},
        version=causado["version"],
    )
    assert r_anular.status_code == 200, r_anular.text
    politica_op = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r = _borrador(
        mundo,
        s,
        politica_op,
        [{"cause_id": causado["id"], "monto": "100.00"}],
        cargo,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_PAYMENT_ORDER_CAUSE_NOT_ELIGIBLE"


@ONLY_PG
def test_t03_04_orden_parcial_proyecta_bud09(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="100.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "30.00"}],
        cargo,
    )
    assert borrador.status_code == 201, borrador.text
    emitida = _emitir(mundo, borrador.json())
    assert emitida.status_code == 200, emitida.text

    detalle = _detalle(mundo, causado["id"])
    _expect_montos_orden_detalle(detalle, "30.00", "70.00")


@ONLY_PG
def test_t03_05_multiples_ordenes_y_sobre_orden_borrador(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="100.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r1 = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "30.00"}], cargo
    )
    assert r1.status_code == 201, r1.text
    emitida1 = _emitir(mundo, r1.json())
    assert emitida1.status_code == 200, emitida1.text

    r2 = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], cargo
    )
    assert r2.status_code == 201, r2.text
    emitida2 = _emitir(mundo, r2.json())
    assert emitida2.status_code == 200, emitida2.text

    detalle = _detalle(mundo, causado["id"])
    _expect_montos_orden_detalle(detalle, "80.00", "20.00")

    r3 = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "21.00"}], cargo
    )
    assert r3.status_code == 422
    assert r3.json()["code"] == "GOV_PAYMENT_ORDER_OVER_ORDER"


@ONLY_PG
def test_t03_06_agotamiento_exacto(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="100.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "100.00"}],
        cargo,
    )
    assert borrador.status_code == 201, borrador.text
    emitida = _emitir(mundo, borrador.json())
    assert emitida.status_code == 200, emitida.text

    detalle = _detalle(mundo, causado["id"])
    _expect_montos_orden_detalle(detalle, "100.00", "0.00")

    r = _get_op(mundo, f"{ORDENES}/ejercicios/{s['year_id']}/ordenes-pago/opciones")
    assert r.status_code == 200
    assert all(o["id"] != causado["id"] for o in r.json()["obligaciones"])


@ONLY_PG
def test_t03_07_sobre_orden_en_emision(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="100.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador1 = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "60.00"}], cargo
    )
    assert borrador1.status_code == 201, borrador1.text
    borrador2 = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "60.00"}], cargo
    )
    assert borrador2.status_code == 201, borrador2.text

    emitida1 = _emitir(mundo, borrador1.json())
    assert emitida1.status_code == 200, emitida1.text

    emitida2 = _emitir(mundo, borrador2.json())
    assert emitida2.status_code == 409
    assert emitida2.json()["code"] == "GOV_PAYMENT_ORDER_OVER_ORDER"


@ONLY_PG
def test_t03_08_orden_multi_causado(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    c1 = _causado_formalizado(mundo, s, monto="50.00")
    c2 = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador = _borrador(
        mundo,
        s,
        politica,
        [
            {"cause_id": c1["id"], "monto": "50.00"},
            {"cause_id": c2["id"], "monto": "50.00"},
        ],
        cargo,
    )
    assert borrador.status_code == 201, borrador.text
    emitida = _emitir(mundo, borrador.json())
    assert emitida.status_code == 200, emitida.text
    assert emitida.json()["monto"] == "100.00"
    assert len(emitida.json()["lineas"]) == 2

    detalle1 = _detalle(mundo, c1["id"])
    detalle2 = _detalle(mundo, c2["id"])
    _expect_montos_orden_detalle(detalle1, "50.00", "0.00")
    _expect_montos_orden_detalle(detalle2, "50.00", "0.00")


@ONLY_PG
def test_t03_09_beneficiario_distinto_incompatible(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    c1 = _causado_formalizado(mundo, s, monto="50.00", beneficiario="Proveedor Uno C.A.")
    c2 = _causado_formalizado(mundo, s, monto="50.00", beneficiario="Proveedor Dos S.A.")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r = _borrador(
        mundo,
        s,
        politica,
        [
            {"cause_id": c1["id"], "monto": "50.00"},
            {"cause_id": c2["id"], "monto": "50.00"},
        ],
        cargo,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_PAYMENT_ORDER_INCOMPATIBLE"


@ONLY_PG
def test_t03_10_causado_de_otro_ejercicio(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": str(uuid4()), "monto": "10.00"}],
        cargo,
    )
    assert r.status_code in (404, 422)
    if r.status_code == 422:
        assert r.json()["code"] == "GOV_PAYMENT_ORDER_CAUSE_NOT_FOUND"


@ONLY_PG
def test_t03_11_aislamiento_entre_empresas(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r_b = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "50.00"}],
        cargo,
        usuario="ord_t03",
    )
    assert r_b.status_code == 201, r_b.text

    r_consulta_b = mundo.get(
        f"{ORDENES}/ordenes-pago/{r_b.json()['id']}",
        "ver_t03",
        mundo.company_b,
    )
    assert r_consulta_b.status_code == 404

    r_consulta_a = mundo.get(
        f"/gobierno/presupuesto/causados/{causado['id']}",
        "caus_b09",
        mundo.company_b,
    )
    assert r_consulta_a.status_code == 404


@ONLY_PG
def test_t03_11b_sin_escritura_entre_empresas(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    orden = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "30.00"}],
        cargo,
        usuario="ord_t03",
    )
    assert orden.status_code == 201, orden.text
    orden_id = orden.json()["id"]
    version_inicial = orden.json()["version"]

    with mundo.factory() as db:
        usuario = db.scalar(select(User).where(User.username == "ord_t03"))
        db.add(UserScope(user_id=usuario.id, company_id=mundo.company_b))
        db.commit()

    r_put = _put_op(
        mundo,
        f"{ORDENES}/ordenes-pago/{orden_id}",
        "ord_t03",
        {"concepto": "Intento desde otra empresa"},
        version_inicial,
        empresa=mundo.company_b,
    )
    assert r_put.status_code == 404, r_put.text

    r_emitir = _post_op(
        mundo,
        f"{ORDENES}/ordenes-pago/{orden_id}/emitir",
        "ord_t03",
        {},
        empresa=mundo.company_b,
        version=version_inicial,
    )
    assert r_emitir.status_code == 404, r_emitir.text

    r_anular = _post_op(
        mundo,
        f"{ORDENES}/ordenes-pago/{orden_id}/anular",
        "ord_t03",
        {"motivo": "Intento de anulación cruzada", "cargo_id": cargo},
        empresa=mundo.company_b,
        version=version_inicial,
    )
    assert r_anular.status_code == 404, r_anular.text

    r_consulta = _get_op(mundo, f"{ORDENES}/ordenes-pago/{orden_id}")
    assert r_consulta.status_code == 200, r_consulta.text
    assert r_consulta.json()["estado"] == "BORRADOR"
    assert r_consulta.json()["version"] == version_inicial
    assert r_consulta.json()["concepto"] == "Orden de pago de prueba TRE-03"

    opciones = _get_op(
        mundo,
        f"{ORDENES}/ejercicios/{s['year_id']}/ordenes-pago/opciones",
    )
    assert opciones.status_code == 200, opciones.text
    obligacion = next(
        obligacion
        for obligacion in opciones.json()["obligaciones"]
        if obligacion["id"] == causado["id"]
    )
    assert obligacion["monto_ordenado"] == "0.00"


@ONLY_PG
def test_t03_12_sin_beneficiario_control_y_emision(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00", beneficiario=None)
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], cargo
    )
    assert r.status_code == 201, r.text
    borrador = r.json()
    assert any(
        control["codigo"] == "FALTA_BENEFICIARIO" and not control["cumplido"]
        for control in borrador["controles"]["controles"]
    )

    emitida = _emitir(mundo, borrador)
    assert emitida.status_code == 422
    assert emitida.json()["code"] == "GOV_PAYMENT_ORDER_BENEFICIARY_REQUIRED"


@ONLY_PG
def test_t03_13_documento_obligatorio(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(
        mundo,
        documentos=[
            {
                "document_type_id": _tipo_documento_soporte(mundo, s["soporte"]),
                "obligatorio": True,
                "etapa": "EMISION",
            }
        ],
    )
    cargo = _cargo_ordenar(mundo, ocupacion)

    r_sin_doc = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], cargo
    )
    assert r_sin_doc.status_code == 201, r_sin_doc.text
    borrador = r_sin_doc.json()
    assert any(
        control["codigo"] == "FALTA_DOCUMENTO" and not control["cumplido"]
        for control in borrador["controles"]["controles"]
    )
    emitida_sin_doc = _emitir(mundo, borrador)
    assert emitida_sin_doc.status_code == 422
    assert emitida_sin_doc.json()["code"] == "GOV_PAYMENT_ORDER_DOCUMENT_MISSING"

    r_con_doc = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "50.00"}],
        cargo,
        documentos=[s["soporte"]],
    )
    assert r_con_doc.status_code == 201, r_con_doc.text
    emitida = _emitir(mundo, r_con_doc.json())
    assert emitida.status_code == 200, emitida.text


@ONLY_PG
def test_t03_14_expediente_completo_con_evidencia(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo, requiere_expediente_completo=True)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], cargo
    )
    assert r.status_code == 201, r.text
    borrador = r.json()
    assert any(
        control["codigo"] == "FALTA_EVIDENCIA" and control["cumplido"]
        for control in borrador["controles"]["controles"]
    )
    emitida = _emitir(mundo, borrador)
    assert emitida.status_code == 200, emitida.text


@ONLY_PG
def test_t03_15_autoridad_invalida(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    _cargo_ordenar(mundo, ocupacion)

    r_sin = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], None
    )
    assert r_sin.status_code == 201, r_sin.text
    emitida_sin = _emitir(mundo, r_sin.json())
    assert emitida_sin.status_code == 422
    assert emitida_sin.json()["code"] == "GOV_PAYMENT_ORDER_AUTHORITY_REQUIRED"

    cargo_causar = _cargo_ordenar(mundo, ocupacion, tipo_limite="SIN_LIMITE")
    with mundo.factory() as db:
        cargo_obj = db.get(GovernmentPosition, cargo_causar)
        for competencia in db.scalars(
            select(GovernmentPositionCompetency).where(
                GovernmentPositionCompetency.position_id == cargo_obj.id
            )
        ):
            db.delete(competencia)
        db.flush()
        for version in db.scalars(
            select(GovernmentPositionVersion).where(
                GovernmentPositionVersion.position_id == cargo_obj.id
            )
        ):
            db.delete(version)
        db.commit()

    with mundo.factory() as db:
        cargo_sin_comp = GovernmentPosition(
            company_id=mundo.company_a,
            structure_id=ocupacion["estructura"],
            unit_id=ocupacion["unidad_raiz"],
            code=_codigo("X"),
            name=f"Cargo sin competencia {_codigo('N')}",
            status="VIGENTE",
            valid_from=D(1, 1),
            valid_to=None,
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo_sin_comp)
        db.flush()
        cargo_invalido = str(cargo_sin_comp.id)
        version = GovernmentPositionVersion(
            position_id=cargo_sin_comp.id,
            structure_id=ocupacion["estructura"],
            company_id=mundo.company_a,
            version=1,
            status="VIGENTE",
            snapshot={"competencias": []},
            reason=None,
            actor_id=None,
        )
        db.add(version)
        db.commit()

    r_invalido = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "50.00"}],
        cargo_invalido,
    )
    assert r_invalido.status_code == 201, r_invalido.text
    emitida_invalido = _emitir(mundo, r_invalido.json())
    assert emitida_invalido.status_code == 422
    assert emitida_invalido.json()["code"] == "GOV_PAYMENT_ORDER_AUTHORITY_INVALID"

    cargo_vencido = _cargo_ordenar(
        mundo, ocupacion, valid_from=D(1, 1), valid_to=D(1, 2)
    )
    r_vencido = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "50.00"}],
        cargo_vencido,
    )
    assert r_vencido.status_code == 201, r_vencido.text
    emitida_vencido = _emitir(mundo, r_vencido.json())
    assert emitida_vencido.status_code == 422
    assert emitida_vencido.json()["code"] == "GOV_PAYMENT_ORDER_AUTHORITY_INVALID"


@ONLY_PG
def test_t03_16_limite_de_monto(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="100.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion, tipo_limite="MONTO", monto="50.00", moneda="VES")

    r_alto = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "60.00"}], cargo
    )
    assert r_alto.status_code == 201, r_alto.text
    controles_alto = _get_op(mundo, f"{ORDENES}/ordenes-pago/{r_alto.json()['id']}/controles")
    assert controles_alto.status_code == 200, controles_alto.text
    control_limite_alto = next(c for c in controles_alto.json()["controles"] if c["codigo"] == "LIMITE")
    assert control_limite_alto["cumplido"] is False
    assert controles_alto.json()["completo"] is False
    emitida_alto = _emitir(mundo, r_alto.json())
    assert emitida_alto.status_code == 422
    assert emitida_alto.json()["code"] == "GOV_PAYMENT_ORDER_AUTHORITY_LIMIT_EXCEEDED"

    r_bajo = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "40.00"}], cargo
    )
    assert r_bajo.status_code == 201, r_bajo.text
    controles_bajo = _get_op(mundo, f"{ORDENES}/ordenes-pago/{r_bajo.json()['id']}/controles")
    assert controles_bajo.status_code == 200, controles_bajo.text
    control_limite_bajo = next(c for c in controles_bajo.json()["controles"] if c["codigo"] == "LIMITE")
    assert control_limite_bajo["cumplido"] is True
    assert controles_bajo.json()["completo"] is True
    emitida_bajo = _emitir(mundo, r_bajo.json())
    assert emitida_bajo.status_code == 200, emitida_bajo.text


@ONLY_PG
def test_t03_17_autoridad_delegada_con_identidad(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)
    nombre = "ord_t03_delegado"
    user_id = cuenta_con_permisos(
        mundo,
        nombre,
        [
            ("gobierno_ordenes_pago", "view"),
            ("gobierno_ordenes_pago", "manage"),
            ("gobierno_ordenes_pago", "issue"),
            ("gobierno_presupuesto", "view"),
        ],
    )
    funcionario = crear_funcionario(mundo, usuario="ua")
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    from tests.org04_ayudantes import cuerpo as cuerpo_asignacion
    from tests.org04_ayudantes import post_asignacion
    from tests.org06_ayudantes import accion as accion_asignacion

    datos = cuerpo_asignacion(funcionario, cargo, acto, figura="ENCARGADURIA")
    asig = post_asignacion(mundo, datos)
    assert asig.status_code == 201, asig.text
    activa = accion_asignacion(mundo, asig.json(), "activar", usuario="uab")
    assert activa.status_code == 200, activa.text

    from tests.org06_ayudantes import cuerpo_vinculo, vinculo_activo

    vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))
    exigir_identidad(mundo)

    try:
        r = _borrador(
            mundo,
            s,
            politica,
            [{"cause_id": causado["id"], "monto": "50.00"}],
            cargo,
            usuario=nombre,
        )
        assert r.status_code == 201, r.text
        emitida = _emitir(mundo, r.json(), usuario=nombre)
        assert emitida.status_code == 200, emitida.text
    finally:
        exigir_identidad(mundo, False)


@ONLY_PG
def test_t03_18_sod_configurada(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    usuario_sod = "causord_t03"
    cuenta_con_permisos(
        mundo,
        usuario_sod,
        [
            ("gobierno_presupuesto", "view"),
            ("gobierno_presupuesto", "cause"),
            ("gobierno_ordenes_pago", "view"),
            ("gobierno_ordenes_pago", "manage"),
            ("gobierno_ordenes_pago", "issue"),
        ],
    )
    regla = crear_regla(
        mundo,
        proceso="TRE-03",
        accion_a="TRE03_CAUSAR",
        accion_b="TRE03_ORDENAR",
        nombre="SoD TRE-03",
    )
    regla = activar_regla(mundo, regla)

    try:
        partida = _partida_rotante()
        r_comp = _comprometer(
            mundo,
            s,
            [{"certificado_id": _cdp(mundo, s, partida, "50.00")["id"], "monto": "50.00"}],
        )
        assert r_comp.status_code == 201, r_comp.text
        compromiso = r_comp.json()
        politica_b09 = _politica_b09(mundo)
        politica_b09 = _activar_politica_b09(mundo, politica_b09)
        causado = _causar(
            mundo,
            s,
            compromiso,
            s["cargo_causar"],
            politica_b09,
            monto="50.00",
            beneficiario="Proveedor SoD C.A.",
        )
        r_formalizar = _post_ctl06(
            mundo,
            f"/gobierno/presupuesto/causados/{causado['id']}/formalizar",
            usuario_sod,
            mundo.company_a,
            {},
            version=causado["version"],
        )
        assert r_formalizar.status_code == 200, r_formalizar.text
        detalle = _detalle(mundo, causado["id"])
        detalle["compromiso_id"] = compromiso["id"]
        detalle["politica_id"] = politica_b09["id"]

        politica = _politica_op(mundo)
        cargo = _cargo_ordenar(mundo, ocupacion)

        r = _borrador(
            mundo,
            s,
            politica,
            [{"cause_id": causado["id"], "monto": "50.00"}],
            cargo,
            usuario=usuario_sod,
        )
        assert r.status_code == 201, r.text
        emitida = _emitir(mundo, r.json(), usuario=usuario_sod)
        assert emitida.status_code == 409
        assert emitida.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        cerrar_regla(mundo, regla)


@ONLY_PG
def test_t03_19_sin_sod_emite(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    usuario_sod = "causord19_t03"
    cuenta_con_permisos(
        mundo,
        usuario_sod,
        [
            ("gobierno_presupuesto", "view"),
            ("gobierno_presupuesto", "cause"),
            ("gobierno_ordenes_pago", "view"),
            ("gobierno_ordenes_pago", "manage"),
            ("gobierno_ordenes_pago", "issue"),
        ],
    )
    partida = _partida_rotante()
    r_comp = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, partida, "50.00")["id"], "monto": "50.00"}],
    )
    assert r_comp.status_code == 201, r_comp.text
    compromiso = r_comp.json()
    politica_b09 = _politica_b09(mundo)
    politica_b09 = _activar_politica_b09(mundo, politica_b09)
    causado = _causar(
        mundo,
        s,
        compromiso,
        s["cargo_causar"],
        politica_b09,
        monto="50.00",
        beneficiario="Proveedor SoD C.A.",
    )
    r_formalizar = _post_ctl06(
        mundo,
        f"/gobierno/presupuesto/causados/{causado['id']}/formalizar",
        usuario_sod,
        mundo.company_a,
        {},
        version=causado["version"],
    )
    assert r_formalizar.status_code == 200, r_formalizar.text

    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "50.00"}],
        cargo,
        usuario=usuario_sod,
    )
    assert r.status_code == 201, r.text
    emitida = _emitir(mundo, r.json(), usuario=usuario_sod)
    assert emitida.status_code == 200, emitida.text


@ONLY_PG
def test_t03_20_borrador_no_consume(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="100.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "40.00"}], cargo
    )
    assert r.status_code == 201, r.text
    borrador = r.json()
    assert borrador["lineas"][0]["monto_ordenado"] == "0.00"
    assert borrador["lineas"][0]["monto_asignado"] == "40.00"

    detalle = _detalle(mundo, causado["id"])
    _expect_montos_orden_detalle(detalle, "0.00", "100.00")


@ONLY_PG
def test_t03_21_emitir_consume_y_anular_restaura(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="100.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "40.00"}], cargo
    )
    assert borrador.status_code == 201, borrador.text
    emitida = _emitir(mundo, borrador.json())
    assert emitida.status_code == 200, emitida.text

    detalle_emitida = _detalle(mundo, causado["id"])
    _expect_montos_orden_detalle(detalle_emitida, "40.00", "60.00")

    anulada = _anular(mundo, emitida.json(), cargo)
    assert anulada.status_code == 200, anulada.text
    assert anulada.json()["estado"] == "ANULADA"
    assert anulada.json()["motivo_anulacion"] == "Anulación de prueba de la orden"

    detalle_anulada = _detalle(mundo, causado["id"])
    _expect_montos_orden_detalle(detalle_anulada, "0.00", "100.00")


@ONLY_PG
def test_t03_22_concurrencia_real_emision(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="100.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador1 = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "70.00"}], cargo
    )
    assert borrador1.status_code == 201, borrador1.text
    borrador2 = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "70.00"}], cargo
    )
    assert borrador2.status_code == 201, borrador2.text

    versiones = [borrador1.json()["version"], borrador2.json()["version"]]
    ids = [borrador1.json()["id"], borrador2.json()["id"]]

    barrera = threading.Barrier(2, timeout=30)
    resultados: list[int] = []
    ganadores: list[str] = []

    cabeceras = mundo.como("ord_t03", mundo.company_a)

    def emitir_hilo(order_id, version):
        barrera.wait()
        r = mundo.client.post(
            f"/api/v1{ORDENES}/ordenes-pago/{order_id}/emitir",
            headers={**cabeceras, "If-Match": str(version)},
        )
        resultados.append(r.status_code)
        if r.status_code == 200:
            ganadores.append(order_id)

    hilos = [
        threading.Thread(target=emitir_hilo, args=(ids[i], versiones[i]))
        for i in range(2)
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=35)

    assert sorted(resultados) == [200, 409]
    assert len(ganadores) == 1

    detalle = _detalle(mundo, causado["id"])
    _expect_montos_orden_detalle(detalle, "70.00", "30.00")


@ONLY_PG
def test_t03_23_instantanea_historica_e_inmutabilidad(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], cargo
    )
    assert borrador.status_code == 201, borrador.text
    version_congelada = politica["version"]
    emitida = _emitir(mundo, borrador.json())
    assert emitida.status_code == 200, emitida.text
    orden_emitida = emitida.json()

    r_cerrar = _post_op(
        mundo,
        f"{POLITICAS_OP}/{politica['id']}/cerrar",
        "ord_t03",
        {"motivo": "Cierre para probar instantánea histórica"},
        version=politica["version"],
    )
    assert r_cerrar.status_code == 200, r_cerrar.text
    _politica_op(mundo)

    detalle = _get_op(mundo, f"{ORDENES}/ordenes-pago/{orden_emitida['id']}").json()
    assert detalle["policy"]["id"] == str(politica["id"])
    assert detalle["policy"]["version"] == version_congelada
    assert detalle["huella"]
    assert detalle["emitida_en"]

    with mundo.factory() as db:
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "UPDATE government_payment_orders SET monto = '1.00' "
                    "WHERE id = :order_id"
                ),
                {"order_id": orden_emitida["id"]},
            )
            db.commit()


@ONLY_PG
def test_t03_24_bud09_rechaza_anular_causado_con_orden(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], cargo
    )
    assert borrador.status_code == 201, borrador.text
    emitida = _emitir(mundo, borrador.json())
    assert emitida.status_code == 200, emitida.text

    r = _post(
        mundo,
        f"/gobierno/presupuesto/causados/{causado['id']}/anular",
        "caus_b09",
        mundo.company_a,
        {"motivo": "Intento de anulación con orden emitida"},
        version=causado["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_CAUSE_HAS_PAYMENT_ORDERS"


@ONLY_PG
def test_t03_25_auditoria_de_la_orden(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], cargo
    )
    assert borrador.status_code == 201, borrador.text
    emitida = _emitir(mundo, borrador.json())
    assert emitida.status_code == 200, emitida.text
    anulada = _anular(mundo, emitida.json(), cargo)
    assert anulada.status_code == 200, anulada.text

    entity_id = borrador.json()["id"]
    assert _eventos(mundo, "GOV_PAYMENT_ORDER_DRAFT_CREATED", entity_id)
    assert _eventos(mundo, "GOV_PAYMENT_ORDER_ISSUED", entity_id)
    assert _eventos(mundo, "GOV_PAYMENT_ORDER_CANCELLED", entity_id)


@ONLY_PG
def test_t03_26_permisos_y_clasificacion(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    r = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "50.00"}],
        cargo,
        usuario="ver_t03",
    )
    assert r.status_code == 403

    assert classify(["gobierno_ordenes_pago:issue"]) == SENSITIVE
    assert classify(["gobierno_ordenes_pago:cancel"]) == SENSITIVE
    assert classify(["gobierno_ordenes_pago:policy"]) == SENSITIVE
    assert classify(["gobierno_ordenes_pago:view"]) == "STANDARD"


@ONLY_PG
def test_t03_27_fecha_invalida(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    fecha_efectiva = date.fromisoformat(causado["fecha_efectiva"])
    fecha_pasada = fecha_efectiva - timedelta(days=1)
    r_pasada = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "50.00"}],
        cargo,
        fecha=fecha_pasada,
    )
    assert r_pasada.status_code == 422
    assert r_pasada.json()["code"] == "GOV_PAYMENT_ORDER_DATE_INVALID"

    fecha_futura = hoy_de_negocio() + timedelta(days=1)
    r_futura = _borrador(
        mundo,
        s,
        politica,
        [{"cause_id": causado["id"], "monto": "50.00"}],
        cargo,
        fecha=fecha_futura,
    )
    assert r_futura.status_code == 422
    assert r_futura.json()["code"] == "GOV_PAYMENT_ORDER_DATE_INVALID"


@ONLY_PG
def test_t03_28_numeracion_personalizada(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    r_conf = _get_op(mundo, CONFIG_OP, usuario="ord_t03")
    assert r_conf.status_code == 200, r_conf.text
    configuracion = r_conf.json()
    patron_anterior = configuracion["patron"]

    try:
        r_upd = _put_op(
            mundo,
            CONFIG_OP,
            "ord_t03",
            {"patron": "OP-{ANIO}-{NUMERO:4}"},
            configuracion["version"],
        )
        assert r_upd.status_code == 200, r_upd.text

        s = _preparar(mundo, ocupacion)
        causado = _causado_formalizado(mundo, s, monto="50.00")
        politica = _politica_op(mundo)
        cargo = _cargo_ordenar(mundo, ocupacion)

        borrador = _borrador(
            mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], cargo
        )
        assert borrador.status_code == 201, borrador.text
        emitida = _emitir(mundo, borrador.json())
        assert emitida.status_code == 200, emitida.text
        assert emitida.json()["codigo"].startswith("OP-")
        assert len(emitida.json()["codigo"]) >= len("OP-2025-0001")
    finally:
        r_rest = _get_op(mundo, CONFIG_OP, usuario="ord_t03")
        assert r_rest.status_code == 200, r_rest.text
        _put_op(
            mundo,
            CONFIG_OP,
            "ord_t03",
            {"patron": patron_anterior},
            r_rest.json()["version"],
        )


@ONLY_PG
def test_t03_29_csv_contiene_codigos(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], cargo
    )
    assert borrador.status_code == 201, borrador.text
    emitida = _emitir(mundo, borrador.json())
    assert emitida.status_code == 200, emitida.text

    r = _get_op(
        mundo,
        f"{ORDENES}/ejercicios/{s['year_id']}/ordenes-pago/reporte.csv",
    )
    assert r.status_code == 200, r.text
    assert emitida.json()["codigo"] in r.text
    assert causado["codigo"] in r.text


@ONLY_PG
def test_t03_30_frontera_tre04(mundo, gobierno, ocupacion):
    _cuentas_t03(mundo)
    s = _preparar(mundo, ocupacion)
    causado = _causado_formalizado(mundo, s, monto="50.00")
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)

    borrador = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": "50.00"}], cargo
    )
    assert borrador.status_code == 201, borrador.text
    emitida = _emitir(mundo, borrador.json())
    assert emitida.status_code == 200, emitida.text

    detalle = emitida.json()
    assert detalle["monto_pagado"] == "0.00"
    assert detalle["pendiente_de_pagar"] == "50.00"
