import itertools
import os
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentType
from app.modules.government.models import (
    GovernmentAct,
    GovernmentBankAccountHistory,
    GovernmentPosition,
)
from app.modules.identity_access.mfa_policy import SENSITIVE, STANDARD, classify
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from app.shared.audit_catalog import catalog
from app.shared.clock import hoy_de_negocio
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos, _post

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

T = "/gobierno/tesoreria"
HOY = hoy_de_negocio()
ANIO = HOY.year
_codigos = itertools.count(1001)
_numeros = itertools.count(1)


def nuevo_acto(mundo, company_id, cargo_id, status="EMITIDO", fecha=None) -> str:
    """Inserta un acto en el estado pedido, con su documento, y devuelve su id."""
    with mundo.factory() as db:
        tipo = db.scalar(select(DocumentType).where(DocumentType.company_id == company_id, DocumentType.code == "GOV-TRE-T"))
        if tipo is None:
            tipo = DocumentType(company_id=company_id, code="GOV-TRE-T", name="Acto de prueba de Tesorería")
            db.add(tipo)
            db.flush()
        documento = Document(company_id=company_id, document_type_id=tipo.id, title="Acto de prueba", status="ACTIVE")
        db.add(documento)
        db.flush()
        marca = uuid4().hex[:12].upper()
        acto = GovernmentAct(
            company_id=company_id, tipo="RESOLUCION", numero=f"T-{marca}", numero_clave=f"T-{marca}",
            fecha=fecha or HOY, lugar="Caracas", cargo_id=cargo_id, competencia_accion="APROBAR",
            competencia_materia="TESORERIA", fundamento_competencia="Reglamento interno de prueba",
            funcionario="Funcionario de prueba", titularidad="TITULAR", caracter="INTERNO",
            asunto=f"Acto {marca}", status="BORRADOR" if status == "BORRADOR" else "EMITIDO", version=1,
        )
        if status != "BORRADOR":
            acto.documento_acto_id = documento.id
            acto.emitido_en = datetime.now(UTC)
        if status == "EFICAZ":
            acto.status = "EFICAZ"
            acto.fecha_eficacia = HOY
        db.add(acto)
        db.commit()
        return str(acto.id)


def dejar_sin_efecto(mundo, acto_id, company_id, cargo_id, status="REVOCADO") -> None:
    """Deja el acto REVOCADO o NULO, referenciando otro acto emitido."""
    otro = nuevo_acto(mundo, company_id, cargo_id)
    with mundo.factory() as db:
        acto = db.get(GovernmentAct, acto_id)
        acto.status = status
        if status == "REVOCADO":
            acto.revocado_por_id = otro
        else:
            acto.anulado_por_id = otro
        db.commit()


def segundo_cargo(mundo, cargo_id) -> str:
    """Crea otro cargo VIGENTE en la misma estructura y unidad que `cargo_id`."""
    with mundo.factory() as db:
        base = db.get(GovernmentPosition, cargo_id)
        marca = uuid4().hex[:8].upper()
        cargo = GovernmentPosition(
            company_id=base.company_id, structure_id=base.structure_id, unit_id=base.unit_id, code=f"C-{marca}",
            name=f"Cargo {marca}", status="VIGENTE", valid_from=base.valid_from, activated_at=datetime.now(UTC), version=1,
        )
        db.add(cargo)
        db.commit()
        return str(cargo.id)


def crear_banco(mundo, usuario="ua", empresa=None, codigo=None, nombre=None) -> dict:
    empresa = empresa or mundo.company_a
    codigo = codigo or f"{next(_codigos):04d}"
    r = _post(mundo, f"{T}/bancos", usuario, empresa, {"codigo": codigo, "nombre": nombre or f"Banco {codigo}"})
    assert r.status_code == 201, r.text
    return r.json()


def numero_de(banco: dict) -> str:
    return f"{banco['codigo']}{next(_numeros):016d}"


def cuerpo_cuenta(banco: dict, **cambios) -> dict:
    cuerpo = {
        "denominacion": "Fondos de funcionamiento",
        "banco_id": banco["id"],
        "tipo": "CORRIENTE",
        "numero": numero_de(banco),
        "moneda": "VES",
        "vigente_desde": HOY.isoformat(),
    }
    cuerpo.update(cambios)
    return cuerpo


def crear_cuenta(mundo, banco=None, usuario="ua", empresa=None, **cambios) -> dict:
    empresa = empresa or mundo.company_a
    banco = banco or crear_banco(mundo, usuario=usuario, empresa=empresa)
    r = _post(mundo, f"{T}/cuentas", usuario, empresa, cuerpo_cuenta(banco, **cambios))
    assert r.status_code == 201, r.text
    return r.json()


def vincular(mundo, cuenta: dict, acto_id: str, usuario="ua", empresa=None) -> dict:
    r = _post(mundo, f"{T}/cuentas/{cuenta['id']}/acto", usuario, empresa or mundo.company_a, {"acto_id": acto_id}, version=cuenta["version"])
    assert r.status_code == 200, r.text
    return r.json()


def autorizar(mundo, cuenta: dict, cargo_id: str, acto_id: str, usuario="ua", empresa=None) -> dict:
    r = _post(
        mundo, f"{T}/cuentas/{cuenta['id']}/autorizados", usuario, empresa or mundo.company_a,
        {"cargo_id": cargo_id, "acto_id": acto_id, "vigente_desde": cuenta["vigente_desde"]}, version=cuenta["version"],
    )
    assert r.status_code == 201, r.text
    return r.json()


def activar(mundo, cuenta: dict, usuario="ua", empresa=None) -> dict:
    r = _post(mundo, f"{T}/cuentas/{cuenta['id']}/activar", usuario, empresa or mundo.company_a, {}, version=cuenta["version"])
    assert r.status_code == 200, r.text
    return r.json()


def cuenta_lista(mundo, cargo_id, usuario="ua", empresa=None, **cambios) -> dict:
    """Cuenta en BORRADOR con acto y un autorizado, lista para activar."""
    empresa = empresa or mundo.company_a
    acto = nuevo_acto(mundo, empresa, cargo_id)
    cuenta = crear_cuenta(mundo, usuario=usuario, empresa=empresa, **cambios)
    cuenta = vincular(mundo, cuenta, acto, usuario, empresa)
    return autorizar(mundo, cuenta, cargo_id, acto, usuario, empresa)


def cuenta_vigente(mundo, cargo_id, usuario="ua", empresa=None, **cambios) -> dict:
    return activar(mundo, cuenta_lista(mundo, cargo_id, usuario, empresa, **cambios), usuario, empresa)


def eventos(mundo, accion, entity_id) -> list:
    with mundo.factory() as db:
        return list(db.scalars(
            select(AuditEvent).where(AuditEvent.action == accion, AuditEvent.entity_id == entity_id).order_by(AuditEvent.event_time.asc())
        ).all())


def patch(mundo, ruta, usuario, empresa, cuerpo, version=None):
    cabeceras = mundo.como(usuario, empresa)
    if version is not None:
        cabeceras["If-Match"] = str(version)
    return mundo.client.patch(f"/api/v1{ruta}", headers=cabeceras, json=cuerpo)


def test_cb01_permisos_y_catalogo():
    """CB-01: permisos del módulo y catálogo de auditoría."""
    assert CATALOGO_DE_PERMISOS["gobierno_cuentas"] == ["view", "manage", "activate"]
    assert classify(["gobierno_cuentas:activate"]) == SENSITIVE
    assert classify(["gobierno_cuentas:view"]) == STANDARD
    assert classify(["gobierno_cuentas:manage"]) == STANDARD

    catalogo = catalog()
    acciones_banco = {
        ("GOV_BANK_CREATED", "GovernmentBank"),
        ("GOV_BANK_UPDATED", "GovernmentBank"),
    }
    acciones_cuenta = {
        ("GOV_BANK_ACCOUNT_CREATED", "GovernmentBankAccount"),
        ("GOV_BANK_ACCOUNT_UPDATED", "GovernmentBankAccount"),
        ("GOV_BANK_ACCOUNT_ACT_LINKED", "GovernmentBankAccount"),
        ("GOV_BANK_ACCOUNT_ACTIVATED", "GovernmentBankAccount"),
        ("GOV_BANK_ACCOUNT_DEACTIVATED", "GovernmentBankAccount"),
        ("GOV_BANK_ACCOUNT_REACTIVATED", "GovernmentBankAccount"),
        ("GOV_BANK_ACCOUNT_CLOSED", "GovernmentBankAccount"),
        ("GOV_BANK_ACCOUNT_NUMBER_VIEWED", "GovernmentBankAccount"),
        ("GOV_BANK_AUTHORIZATION_ADDED", "GovernmentBankAccount"),
        ("GOV_BANK_AUTHORIZATION_ENDED", "GovernmentBankAccount"),
    }
    for clave in acciones_banco | acciones_cuenta:
        assert clave in catalogo, f"Falta {clave}"
        assert catalogo[clave].owner_spec == "gov-tre-01"


def test_cb02_banco_alta_y_validaciones(mundo, gobierno):
    """CB-02: alta de banco y validaciones de código."""
    empresa = mundo.company_a
    r = _post(mundo, f"{T}/bancos", "ua", empresa, {"codigo": "1111", "nombre": "Banco Uno"})
    assert r.status_code == 201, r.text
    banco = r.json()
    assert banco["estado"] == "ACTIVO"
    assert banco["version"] == 1

    r = _post(mundo, f"{T}/bancos", "ua", empresa, {"codigo": "1111", "nombre": "Banco Uno Repetido"})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_BANK_CODE_DUPLICATE"

    r = _post(mundo, f"{T}/bancos", "ub", mundo.company_b, {"codigo": "1111", "nombre": "Banco Uno B"})
    assert r.status_code == 201, r.text

    for codigo in ("123", "12345", "12a4"):
        r = _post(mundo, f"{T}/bancos", "ua", empresa, {"codigo": codigo, "nombre": f"Banco {codigo}"})
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"

    evs = eventos(mundo, "GOV_BANK_CREATED", banco["id"])
    assert len(evs) == 1


def test_cb03_banco_editar_e_inactivar(mundo, gobierno):
    """CB-03: edición e inactivación de banco."""
    banco = crear_banco(mundo)

    r = patch(mundo, f"{T}/bancos/{banco['id']}", "ua", mundo.company_a, {"nombre": "Otro nombre"})
    assert r.status_code == 428, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_IF_MATCH_REQUIRED"

    r = patch(mundo, f"{T}/bancos/{banco['id']}", "ua", mundo.company_a, {"nombre": "Otro nombre"}, version=banco["version"] - 1)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_STALE"

    r = patch(mundo, f"{T}/bancos/{banco['id']}", "ua", mundo.company_a, {"estado": "INACTIVO"}, version=banco["version"])
    assert r.status_code == 200, r.text
    banco = r.json()
    assert banco["estado"] == "INACTIVO"
    assert banco["version"] == 2

    r = mundo.get(f"{T}/bancos?estado=ACTIVO", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    ids = [b["id"] for b in r.json()["items"]]
    assert banco["id"] not in ids

    r = mundo.get(f"{T}/opciones", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    ids_bancos = [b["id"] for b in r.json()["bancos"]]
    assert banco["id"] not in ids_bancos

    r = _post(mundo, f"{T}/cuentas", "ua", mundo.company_a, cuerpo_cuenta(banco))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"

    r = patch(mundo, f"{T}/bancos/{banco['id']}", "ua", mundo.company_a, {"codigo": "9999"}, version=banco["version"])
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "VALIDATION_ERROR"

    r = patch(mundo, f"{T}/bancos/{uuid4()}", "ua", mundo.company_a, {"nombre": "No existe"}, version=1)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_BANK_NOT_FOUND"


def test_cb04_cuenta_alta(mundo, gobierno):
    """CB-04: alta de cuenta en BORRADOR."""
    banco = crear_banco(mundo)
    numero = numero_de(banco)
    cuenta = crear_cuenta(mundo, banco, numero=numero)

    assert cuenta["estado"] == "BORRADOR"
    assert re.fullmatch(rf"CB-{ANIO}-\d{{4}}", cuenta["codigo"])
    assert cuenta["version"] == 1
    assert cuenta["en_vigor"] is False
    assert cuenta["acto"] is None
    assert cuenta["autorizados"] == []
    assert cuenta["autorizados_en_vigor"] == 0
    assert cuenta["acto_sin_efecto"] is False
    assert cuenta["registrada_por"] == "ua"
    assert [h["tipo"] for h in cuenta["historia"]] == ["CREADA"]
    assert "numero" not in cuenta
    assert cuenta["numero_enmascarado"] == "••••" + numero[-4:]

    evs = eventos(mundo, "GOV_BANK_ACCOUNT_CREATED", cuenta["id"])
    assert len(evs) == 1
    after = evs[0].after
    assert after["numero_enmascarado"] == "••••" + numero[-4:]
    assert "numero" not in after


def test_cb05_numero_invalido_no_se_repite(mundo, gobierno):
    """CB-05: el número inválido no aparece en el mensaje de error."""
    banco = crear_banco(mundo)
    casos = [
        banco["codigo"] + "7" * 15,
        banco["codigo"] + "7" * 17,
        banco["codigo"] + "7" * 15 + "a",
        "9999" + "7" * 16,
    ]
    for numero in casos:
        r = _post(mundo, f"{T}/cuentas", "ua", mundo.company_a, cuerpo_cuenta(banco, numero=numero))
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"
        assert numero not in r.text


def test_cb06_validaciones_de_campos(mundo, gobierno):
    """CB-06: validaciones de esquema y de vigencia."""
    banco = crear_banco(mundo)
    base = cuerpo_cuenta(banco)

    casos = [
        {"tipo": "NOMINA"},
        {"moneda": "GBP"},
        {"denominacion": "ab"},
        {"company_id": mundo.company_a},
    ]
    for cambios in casos:
        cuerpo = base | cambios
        r = _post(mundo, f"{T}/cuentas", "ua", mundo.company_a, cuerpo)
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "VALIDATION_ERROR"

    cuerpo = base | {"vigente_hasta": (HOY - timedelta(days=1)).isoformat()}
    r = _post(mundo, f"{T}/cuentas", "ua", mundo.company_a, cuerpo)
    assert r.status_code == 422, r.text
    assert r.json()["code"] in ("VALIDATION_ERROR", "GOV_BANK_ACCOUNT_INVALID")


def test_cb07_duplicada(mundo, gobierno):
    """CB-07: número duplicado en el mismo banco."""
    banco = crear_banco(mundo)
    numero = numero_de(banco)
    crear_cuenta(mundo, banco, numero=numero)

    r = _post(mundo, f"{T}/cuentas", "ua", mundo.company_a, cuerpo_cuenta(banco, numero=numero))
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_DUPLICATE"
    assert numero not in r.text

    banco_b = crear_banco(mundo, usuario="ub", empresa=mundo.company_b, codigo=banco["codigo"])
    r = _post(mundo, f"{T}/cuentas", "ub", mundo.company_b, cuerpo_cuenta(banco_b, numero=numero))
    assert r.status_code == 201, r.text


def test_cb08_listado_y_filtros(mundo, gobierno, siembra):
    """CB-08: listado, filtros y resumen por estado."""
    cargo_id = siembra["cargo_vigente"]
    cuenta_usd = crear_cuenta(mundo, moneda="USD")
    cuenta_vig = cuenta_vigente(mundo, cargo_id, moneda="VES")

    def ids(r):
        return {c["id"] for c in r.json()["items"]}

    r = mundo.get(f"{T}/cuentas", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    todos = ids(r)
    assert cuenta_usd["id"] in todos
    assert cuenta_vig["id"] in todos
    resumen_base = r.json()["resumen"]
    assert resumen_base["borradores"] >= 1
    assert resumen_base["vigentes"] >= 1
    for item in r.json()["items"]:
        assert "numero" not in item
        assert "numero_enmascarado" in item
        assert "banco_nombre" in item
        assert "autorizados_en_vigor" in item

    r = mundo.get(f"{T}/cuentas?estado=VIGENTE", "ua", mundo.company_a)
    vigentes = ids(r)
    assert cuenta_vig["id"] in vigentes
    assert cuenta_usd["id"] not in vigentes
    assert r.json()["resumen"] == resumen_base

    r = mundo.get(f"{T}/cuentas?moneda=USD", "ua", mundo.company_a)
    usd = ids(r)
    assert cuenta_usd["id"] in usd
    assert cuenta_vig["id"] not in usd

    r = mundo.get(f"{T}/cuentas?banco_id={cuenta_usd['banco_id']}", "ua", mundo.company_a)
    por_banco = ids(r)
    assert cuenta_usd["id"] in por_banco
    assert cuenta_vig["id"] not in por_banco

    r = mundo.get(f"{T}/cuentas?cargo_id={cargo_id}", "ua", mundo.company_a)
    por_cargo = ids(r)
    assert cuenta_vig["id"] in por_cargo
    assert cuenta_usd["id"] not in por_cargo


def test_cb09_editar_borrador(mundo, gobierno, siembra):
    """CB-09: edición de cuenta en BORRADOR y bloqueo en otros estados."""
    cargo_id = siembra["cargo_vigente"]
    banco = crear_banco(mundo)
    numero_viejo = numero_de(banco)
    cuenta = crear_cuenta(mundo, banco, numero=numero_viejo)

    r = patch(mundo, f"{T}/cuentas/{cuenta['id']}", "ua", mundo.company_a, {"denominacion": "Otro"})
    assert r.status_code == 428, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_IF_MATCH_REQUIRED"

    r = patch(mundo, f"{T}/cuentas/{cuenta['id']}", "ua", mundo.company_a, {"denominacion": "Otro"}, version=cuenta["version"] - 1)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_STALE"

    numero_nuevo = numero_de(banco)
    r = patch(
        mundo, f"{T}/cuentas/{cuenta['id']}", "ua", mundo.company_a,
        {"denominacion": "Fondos de inversión", "numero": numero_nuevo}, version=cuenta["version"],
    )
    assert r.status_code == 200, r.text
    cuenta = r.json()
    assert cuenta["denominacion"] == "Fondos de inversión"
    assert cuenta["numero_enmascarado"] == "••••" + numero_nuevo[-4:]
    assert cuenta["historia"][-1]["tipo"] == "EDITADA"
    assert "denominacion" in cuenta["historia"][-1]["detalle"]["campos"]
    assert "numero" in cuenta["historia"][-1]["detalle"]["campos"]

    evs = eventos(mundo, "GOV_BANK_ACCOUNT_UPDATED", cuenta["id"])
    assert len(evs) == 1
    assert numero_viejo not in str(evs[0].after)
    assert numero_nuevo not in str(evs[0].after)
    assert numero_viejo not in str(cuenta["historia"][-1]["detalle"])
    assert numero_nuevo not in str(cuenta["historia"][-1]["detalle"])

    cuenta_vig = cuenta_vigente(mundo, cargo_id)
    r = patch(mundo, f"{T}/cuentas/{cuenta_vig['id']}", "ua", mundo.company_a, {"denominacion": "No se puede"}, version=cuenta_vig["version"])
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID_STATE"


def test_cb10_ver_numero_completo(mundo, gobierno):
    """CB-10: ver el número completo solo con permiso manage."""
    banco = crear_banco(mundo)
    numero = numero_de(banco)
    cuenta = crear_cuenta(mundo, banco, numero=numero)

    r = mundo.get(f"{T}/cuentas/{cuenta['id']}/numero", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert r.json() == {"numero": numero}

    evs = eventos(mundo, "GOV_BANK_ACCOUNT_NUMBER_VIEWED", cuenta["id"])
    assert len(evs) == 1
    assert evs[0].after["numero_enmascarado"] == "••••" + numero[-4:]
    assert numero not in str(evs[0].after)

    _crear_usuario_con_permisos(mundo, "tre_vista", [("gobierno_cuentas", "view")], mundo.company_a)
    r = mundo.get(f"{T}/cuentas/{cuenta['id']}/numero", "tre_vista", mundo.company_a)
    assert r.status_code == 403, r.text


def test_cb11_permisos(mundo, gobierno, siembra):
    """CB-11: control de acceso a la API."""
    _crear_usuario_con_permisos(mundo, "tre_consulta", [("gobierno_cuentas", "view")], mundo.company_a)
    _crear_usuario_con_permisos(
        mundo, "tre_gestor", [("gobierno_cuentas", "view"), ("gobierno_cuentas", "manage")], mundo.company_a
    )
    _crear_usuario_con_permisos(mundo, "tre_ajeno", [("gobierno_hallazgos", "view")], mundo.company_a)

    r = mundo.get(f"{T}/cuentas", "tre_consulta", mundo.company_a)
    assert r.status_code == 200, r.text
    r = _post(mundo, f"{T}/bancos", "tre_consulta", mundo.company_a, {"codigo": "2222", "nombre": "Banco Dos"})
    assert r.status_code == 403, r.text
    r = _post(mundo, f"{T}/cuentas", "tre_consulta", mundo.company_a, cuerpo_cuenta(crear_banco(mundo)))
    assert r.status_code == 403, r.text

    r = _post(mundo, f"{T}/bancos", "tre_gestor", mundo.company_a, {"codigo": "2223", "nombre": "Banco Tres"})
    assert r.status_code == 201, r.text
    banco = r.json()
    r = _post(mundo, f"{T}/cuentas", "tre_gestor", mundo.company_a, cuerpo_cuenta(banco))
    assert r.status_code == 201, r.text
    cuenta = r.json()
    r = _post(mundo, f"{T}/cuentas/{cuenta['id']}/activar", "tre_gestor", mundo.company_a, {}, version=cuenta["version"])
    assert r.status_code == 403, r.text

    r = mundo.get(f"{T}/cuentas", "tre_ajeno", mundo.company_a)
    assert r.status_code == 403, r.text
    r = mundo.get(f"{T}/bancos", "tre_ajeno", mundo.company_a)
    assert r.status_code == 403, r.text
    r = mundo.get(f"{T}/opciones", "tre_ajeno", mundo.company_a)
    assert r.status_code == 403, r.text


def test_cb12_alcance_por_empresa(mundo, gobierno, siembra):
    """CB-12: aislamiento por empresa."""
    banco_a = crear_banco(mundo)
    cuenta_a = crear_cuenta(mundo, banco_a)

    r = mundo.get(f"{T}/cuentas/{cuenta_a['id']}", "ub", mundo.company_b)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_NOT_FOUND"

    r = mundo.get(f"{T}/cuentas/{cuenta_a['id']}/numero", "ub", mundo.company_b)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_NOT_FOUND"

    r = patch(mundo, f"{T}/cuentas/{cuenta_a['id']}", "ub", mundo.company_b, {"denominacion": "Otra"}, version=cuenta_a["version"])
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_NOT_FOUND"

    r = _post(mundo, f"{T}/cuentas/{cuenta_a['id']}/activar", "ub", mundo.company_b, {}, version=cuenta_a["version"])
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_NOT_FOUND"

    r = mundo.get(f"{T}/cuentas", "ub", mundo.company_b)
    assert r.status_code == 200, r.text
    assert cuenta_a["id"] not in {c["id"] for c in r.json()["items"]}

    r = _post(mundo, f"{T}/cuentas", "ub", mundo.company_b, cuerpo_cuenta(banco_a))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"

    r = patch(mundo, f"{T}/bancos/{banco_a['id']}", "ub", mundo.company_b, {"nombre": "Otro"}, version=banco_a["version"])
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_BANK_NOT_FOUND"

    r = mundo.get(f"{T}/cuentas?banco_id={banco_a['id']}", "ub", mundo.company_b)
    assert r.status_code == 200, r.text
    assert r.json()["items"] == []


def test_cb13_opciones(mundo, gobierno, siembra):
    """CB-13: opciones para los selectores."""
    banco_activo = crear_banco(mundo)
    banco_inactivo = crear_banco(mundo)
    r = patch(mundo, f"{T}/bancos/{banco_inactivo['id']}", "ua", mundo.company_a, {"estado": "INACTIVO"}, version=banco_inactivo["version"])
    assert r.status_code == 200, r.text

    acto_emitido = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"], status="EMITIDO")
    acto_eficaz = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"], status="EFICAZ")
    acto_borrador = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"], status="BORRADOR")
    acto_revocado = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"], status="EMITIDO")
    dejar_sin_efecto(mundo, acto_revocado, mundo.company_a, siembra["cargo_vigente"], status="REVOCADO")
    acto_otra = nuevo_acto(mundo, mundo.company_b, siembra["cargo_otra"], status="EMITIDO")

    r = mundo.get(f"{T}/opciones", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    body = r.json()

    ids_bancos = {b["id"] for b in body["bancos"]}
    assert banco_activo["id"] in ids_bancos
    assert banco_inactivo["id"] not in ids_bancos

    ids_cargos = {c["id"] for c in body["cargos"]}
    assert siembra["cargo_vigente"] in ids_cargos
    assert siembra["cargo_borrador"] not in ids_cargos
    assert siembra["cargo_anterior"] not in ids_cargos
    assert siembra["cargo_otra"] not in ids_cargos

    ids_actos = {a["id"] for a in body["actos"]}
    assert acto_emitido in ids_actos
    assert acto_eficaz in ids_actos
    assert acto_borrador not in ids_actos
    assert acto_revocado not in ids_actos
    assert acto_otra not in ids_actos


def test_cb14_inmutabilidad_postgresql(mundo, gobierno, siembra):
    """CB-14: inmutabilidad de la historia en PostgreSQL."""
    if not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"):
        pytest.skip("solo PostgreSQL")

    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco)
    with mundo.factory() as db:
        history_id = db.scalar(select(GovernmentBankAccountHistory.id).where(GovernmentBankAccountHistory.account_id == cuenta["id"]))
        assert history_id is not None

    with mundo.factory() as db:
        with pytest.raises(DBAPIError):
            db.execute(text(f"UPDATE gov_bank_account_history SET detalle = detalle WHERE id = '{history_id}'"))
            db.commit()
        db.rollback()

    with mundo.factory() as db:
        with pytest.raises(DBAPIError):
            db.execute(text(f"DELETE FROM gov_bank_account_history WHERE id = '{history_id}'"))
            db.commit()
        db.rollback()

    with mundo.factory() as db:
        with pytest.raises(DBAPIError):
            db.execute(text(f"DELETE FROM gov_bank_accounts WHERE id = '{cuenta['id']}'"))
            db.commit()
        db.rollback()


def test_cb15_numero_no_se_filtra_en_todo_el_ciclo(mundo, gobierno, siembra):
    """CB-15: el número completo nunca se filtra en el ciclo de vida."""
    cargo_id = siembra["cargo_vigente"]
    banco = crear_banco(mundo)
    numero = numero_de(banco)
    cuenta = crear_cuenta(mundo, banco, numero=numero)
    acto = nuevo_acto(mundo, mundo.company_a, cargo_id)
    cuenta = vincular(mundo, cuenta, acto)
    cuenta = autorizar(mundo, cuenta, cargo_id, acto)
    cuenta = activar(mundo, cuenta)

    motivo = "Motivo de inactivación"
    r = _post(mundo, f"{T}/cuentas/{cuenta['id']}/inactivar", "ua", mundo.company_a, {"motivo": motivo}, version=cuenta["version"])
    assert r.status_code == 200, r.text
    cuenta = r.json()

    r = _post(mundo, f"{T}/cuentas/{cuenta['id']}/reactivar", "ua", mundo.company_a, {"motivo": motivo}, version=cuenta["version"])
    assert r.status_code == 200, r.text
    cuenta = r.json()

    r = _post(mundo, f"{T}/cuentas/{cuenta['id']}/cerrar", "ua", mundo.company_a, {"motivo": motivo, "fecha_cierre": HOY.isoformat()}, version=cuenta["version"])
    assert r.status_code == 200, r.text
    cuenta = r.json()

    r = mundo.get(f"{T}/cuentas/{cuenta['id']}", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert numero not in r.text

    r = mundo.get(f"{T}/cuentas", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert numero not in r.text

    with mundo.factory() as db:
        evs = db.scalars(select(AuditEvent).where(AuditEvent.entity_id == cuenta["id"])).all()
        assert len(evs) >= 7
        for ev in evs:
            assert numero not in str(ev.before)
            assert numero not in str(ev.after)
            assert numero not in str(ev.reason)
