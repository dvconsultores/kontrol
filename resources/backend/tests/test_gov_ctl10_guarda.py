from datetime import UTC, date, datetime, timedelta
from itertools import count

import pytest
from sqlalchemy import text

from app.modules.government.models import GovernmentStructure
from app.shared.clock import hoy_de_negocio
from tests.ctl10_ayudantes import (
    MOTIVO,
    activar,
    acto_emitido,
    anadir_control,
    crear_politica,
    politica_vigente,
    politicas_limpias,  # noqa: F401  # noqa: F401
    retirar,
)
from tests.test_gov_ctl06_hallazgos import _cuerpo_independiente, _post
from tests.test_gov_tre01_cuentas import eventos
from tests.tre02_ayudantes import (
    accion,
    cerrar_regla,
    programa_vigente,
    regla_sod_vigente,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

ANIO = hoy_de_negocio().year
_pasados = count(2000)
_futuros = count(ANIO + 20)
_ejercicios = count(ANIO - 15)


def _estructura_vigente(mundo, ejercicio):
    with mundo.factory() as db:
        entidad = db.execute(
            text("SELECT id FROM gov_entities WHERE company_id = :c"),
            {"c": mundo.company_a},
        ).scalar_one()
        estructura = GovernmentStructure(
            company_id=mundo.company_a,
            entity_id=entidad,
            exercise=ejercicio,
            status="VIGENTE",
            published_at=datetime.now(UTC),
            published_by=None,
        )
        db.add(estructura)
        db.commit()
        db.refresh(estructura)
        return estructura


def _cerrar_estructura(mundo, ejercicio, version=1):
    cabeceras = {**mundo.como("ua", mundo.company_a), "If-Match": str(version)}
    return mundo.client.post(
        f"/api/v1/gobierno/estructuras/{ejercicio}/cerrar",
        headers=cabeceras,
    )


def _hallazgo_pendiente(mundo, riesgo="ALTO", empresa=None):
    empresa = empresa or mundo.company_a
    usuario = "ua" if empresa == mundo.company_a else "ub"
    r = _post(mundo, "/gobierno/hallazgos", usuario, empresa, _cuerpo_independiente(riesgo=riesgo))
    assert r.status_code == 201, r.text
    return r.json()


def _evento_after(mundo, accion, entity_id) -> list:
    return [e.after for e in eventos(mundo, accion, entity_id)]


def test_ga01_estructura_hallazgo_alto_bloquea(mundo, gobierno, siembra):
    politica = politica_vigente(
        mundo,
        "ORG02_CERRAR_ESTRUCTURA",
        "HALLAZGOS_ABIERTOS",
        riesgo_minimo="ALTO",
    )
    ejercicio = next(_ejercicios)
    estructura = _estructura_vigente(mundo, ejercicio)
    hallazgo = _hallazgo_pendiente(mundo, riesgo="ALTO")

    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"
    details = r.json()["details"]
    assert details["politica_codigo"] == politica["codigo"]
    assert details["proceso"] == "ORG02_CERRAR_ESTRUCTURA"
    assert details["objeto_codigo"] == f"EST-{ejercicio}"
    assert details["total"] == 1
    assert details["dueno"] == "Control Interno"
    control = details["controles"][0]
    assert control["tipo"] == "HALLAZGOS_ABIERTOS"
    assert control["etiqueta"]
    assert control["materialidad"]
    assert control["pendientes"] == 1
    assert control["muestra"][0]["ruta"] == f"/gobierno/hallazgos/{hallazgo['id']}"

    with mundo.factory() as db:
        fila = db.query(GovernmentStructure).filter_by(id=estructura.id).one()
        assert fila.status == "VIGENTE"
        assert fila.version == estructura.version


def test_ga02_tras_cerrar_hallazgo_cierra_y_audita_allow(mundo, gobierno, siembra):
    politica = politica_vigente(
        mundo,
        "ORG02_CERRAR_ESTRUCTURA",
        "HALLAZGOS_ABIERTOS",
        riesgo_minimo="ALTO",
    )
    ejercicio = next(_ejercicios)
    estructura = _estructura_vigente(mundo, ejercicio)
    hallazgo = _hallazgo_pendiente(mundo, riesgo="ALTO")

    with mundo.factory() as db:
        db.execute(
            text("UPDATE gov_findings SET estado='CERRADO' WHERE id = :i"),
            {"i": hallazgo["id"]},
        )
        db.commit()

    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    assert r.status_code == 200, r.text

    with mundo.factory() as db:
        fila = db.query(GovernmentStructure).filter_by(id=estructura.id).one()
        assert fila.status == "CERRADA"

    assert _evento_after(mundo, "GOV_MATERIAL_CLOSE_ALLOWED", politica["id"])


def test_ga03_bloqueo_audita_blocked_y_no_cierra(mundo, gobierno, siembra):
    politica = politica_vigente(
        mundo,
        "ORG02_CERRAR_ESTRUCTURA",
        "HALLAZGOS_ABIERTOS",
        riesgo_minimo="ALTO",
    )
    ejercicio = next(_ejercicios)
    estructura = _estructura_vigente(mundo, ejercicio)
    _hallazgo_pendiente(mundo, riesgo="ALTO")

    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    assert r.status_code == 409, r.text
    eventos_blocked = _evento_after(mundo, "GOV_MATERIAL_CLOSE_BLOCKED", politica["id"])
    assert eventos_blocked
    after = eventos_blocked[0]
    assert after["politica_version"] == politica["version"]
    assert after["objeto_tipo"] == "GovernmentStructure"
    assert after["objeto_id"] == str(estructura.id)
    assert after["controles"]
    assert after["total"] == 1
    assert not _evento_after(mundo, "GOV_STRUCTURE_CLOSED", estructura.id)


@pytest.mark.parametrize(
    ("riesgo_hallazgo", "riesgo_minimo", "bloquea"),
    [
        ("MEDIO", "ALTO", False),
        ("ALTO", "MEDIO", True),
        ("MEDIO", "MEDIO", True),
        ("ALTO", "BAJO", True),
        ("MEDIO", "BAJO", True),
        ("BAJO", "BAJO", True),
    ],
)
def test_ga04_umbral_riesgo(mundo, gobierno, siembra, riesgo_hallazgo, riesgo_minimo, bloquea):
    politica_vigente(
        mundo,
        "ORG02_CERRAR_ESTRUCTURA",
        "HALLAZGOS_ABIERTOS",
        riesgo_minimo=riesgo_minimo,
    )
    ejercicio = next(_ejercicios)
    estructura = _estructura_vigente(mundo, ejercicio)
    _hallazgo_pendiente(mundo, riesgo=riesgo_hallazgo)

    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    if bloquea:
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"
    else:
        assert r.status_code == 200, r.text


def test_ga05_hallazgo_cerrado_no_cuenta(mundo, gobierno, siembra):
    politica_vigente(
        mundo,
        "ORG02_CERRAR_ESTRUCTURA",
        "HALLAZGOS_ABIERTOS",
        riesgo_minimo="ALTO",
    )
    ejercicio = next(_ejercicios)
    estructura = _estructura_vigente(mundo, ejercicio)
    hallazgo = _hallazgo_pendiente(mundo, riesgo="ALTO")
    with mundo.factory() as db:
        db.execute(
            text("UPDATE gov_findings SET estado='CERRADO' WHERE id = :i"),
            {"i": hallazgo["id"]},
        )
        db.commit()

    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    assert r.status_code == 200, r.text


def test_ga06_hallazgo_otra_empresa_no_cuenta(mundo, gobierno, siembra):
    politica_vigente(
        mundo,
        "ORG02_CERRAR_ESTRUCTURA",
        "HALLAZGOS_ABIERTOS",
        riesgo_minimo="ALTO",
    )
    ejercicio = next(_ejercicios)
    estructura = _estructura_vigente(mundo, ejercicio)
    _hallazgo_pendiente(mundo, riesgo="ALTO", empresa=mundo.company_b)

    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    assert r.status_code == 200, r.text


def test_ga07_programa_acto_emitido_bloquea(mundo, gobierno, siembra):
    politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "ACTOS_SIN_EFICACIA")
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    acto = acto_emitido(mundo, siembra, date(ejercicio, 6, 1))

    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"
    control = r.json()["details"]["controles"][0]
    assert control["tipo"] == "ACTOS_SIN_EFICACIA"
    assert control["muestra"][0]["ruta"] == f"/gobierno/actos/{acto}"


def test_ga08_tras_hacer_eficaz_acto_cierra(mundo, gobierno, siembra):
    politica = politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "ACTOS_SIN_EFICACIA")
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    acto = acto_emitido(mundo, siembra, date(ejercicio, 6, 1))
    with mundo.factory() as db:
        db.execute(
            text("UPDATE gov_acts SET status='EFICAZ', fecha_eficacia=fecha WHERE id = :i"),
            {"i": acto},
        )
        db.commit()

    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 200, r.text
    assert _evento_after(mundo, "GOV_MATERIAL_CLOSE_ALLOWED", politica["id"])


def test_ga09_acto_emitido_otro_ejercicio_no_bloquea(mundo, gobierno, siembra):
    politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "ACTOS_SIN_EFICACIA")
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    acto_emitido(mundo, siembra, date(ANIO - 15, 6, 1))

    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 200, r.text


def test_ga10_politica_org02_no_afecta_tre02_y_viceversa(mundo, gobierno, siembra):
    politica_vigente(
        mundo,
        "ORG02_CERRAR_ESTRUCTURA",
        "HALLAZGOS_ABIERTOS",
        riesgo_minimo="ALTO",
    )
    politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "ACTOS_SIN_EFICACIA")
    ejercicio_estructura = next(_pasados)
    estructura = _estructura_vigente(mundo, ejercicio_estructura)
    _hallazgo_pendiente(mundo, riesgo="ALTO")

    ejercicio_programa = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio_programa)
    acto_emitido(mundo, siembra, date(ejercicio_programa, 6, 1))

    r = _cerrar_estructura(mundo, ejercicio_estructura, version=estructura.version)
    assert r.status_code == 409, r.text
    assert r.json()["details"]["proceso"] == "ORG02_CERRAR_ESTRUCTURA"

    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409, r.text
    assert r.json()["details"]["proceso"] == "TRE02_CERRAR_PROGRAMA"


def test_ga11_sin_politica_ambos_cierres_funcionan(mundo, gobierno, siembra):
    ejercicio = next(_pasados)
    estructura = _estructura_vigente(mundo, ejercicio)
    _hallazgo_pendiente(mundo, riesgo="ALTO")
    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    assert r.status_code == 200, r.text

    ejercicio_programa = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio_programa)
    acto_emitido(mundo, siembra, date(ejercicio_programa, 6, 1))
    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 200, r.text


def test_ga12_politica_borrador_no_bloquea(mundo, gobierno, siembra):
    crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    ejercicio = next(_pasados)
    estructura = _estructura_vigente(mundo, ejercicio)
    _hallazgo_pendiente(mundo, riesgo="ALTO")

    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    assert r.status_code == 200, r.text


def test_ga13_politica_futura_no_bloquea(mundo, gobierno, siembra):
    politica = crear_politica(
        mundo,
        "ORG02_CERRAR_ESTRUCTURA",
        vigente_desde=date(ANIO + 1, 1, 1).isoformat(),
    )
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")
    r = activar(mundo, politica)
    assert r.status_code == 200, r.text
    ejercicio = next(_pasados)
    estructura = _estructura_vigente(mundo, ejercicio)
    _hallazgo_pendiente(mundo, riesgo="ALTO")

    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    assert r.status_code == 200, r.text


def test_ga14_politica_vencida_no_bloquea(mundo, gobierno, siembra):
    politica = crear_politica(
        mundo,
        "ORG02_CERRAR_ESTRUCTURA",
        vigente_desde="2020-01-01",
        vigente_hasta="2021-01-01",
    )
    r = activar(mundo, politica)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID"


def test_ga15_politica_retirada_no_bloquea(mundo, gobierno, siembra):
    politica = politica_vigente(
        mundo,
        "ORG02_CERRAR_ESTRUCTURA",
        "HALLAZGOS_ABIERTOS",
        riesgo_minimo="ALTO",
    )
    r = retirar(mundo, politica)
    assert r.status_code == 200, r.text
    ejercicio = next(_pasados)
    estructura = _estructura_vigente(mundo, ejercicio)
    _hallazgo_pendiente(mundo, riesgo="ALTO")

    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    assert r.status_code == 200, r.text


def test_ga16_politica_dos_controles_suma_total(mundo, gobierno, siembra):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")
    politica = anadir_control(mundo, politica, "ACTOS_SIN_EFICACIA")
    r = activar(mundo, politica)
    assert r.status_code == 200, r.text

    ejercicio = next(_pasados)
    estructura = _estructura_vigente(mundo, ejercicio)
    _hallazgo_pendiente(mundo, riesgo="ALTO")
    acto_emitido(mundo, siembra, date(ejercicio, 6, 1))

    r = _cerrar_estructura(mundo, ejercicio, version=estructura.version)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"
    details = r.json()["details"]
    assert details["total"] == 2
    assert len(details["controles"]) == 2


def test_ga17_evaluacion_despues_del_estado(mundo, gobierno, siembra):
    politica = politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "ACTOS_SIN_EFICACIA")
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    acto_emitido(mundo, siembra, date(ejercicio, 6, 1))

    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"

    r = retirar(mundo, politica)
    assert r.status_code == 200, r.text

    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 200, r.text

    politica2 = politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "ACTOS_SIN_EFICACIA")
    programa_cerrado = r.json()

    r = accion(mundo, programa_cerrado, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409, r.text
    assert r.json()["code"] != "GOV_MATERIAL_CLOSE_BLOCKED"
    assert _evento_after(mundo, "GOV_MATERIAL_CLOSE_BLOCKED", politica2["id"]) == []


def test_ga18_sod_prevalece(mundo, gobierno, siembra):
    politica = politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "ACTOS_SIN_EFICACIA")
    regla = regla_sod_vigente(
        mundo,
        "TRE02_ACTIVAR",
        "TRE02_CERRAR",
        "Regla SoD cierre",
        proceso="TRE-02",
    )
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    acto_emitido(mundo, siembra, date(ejercicio, 6, 1))

    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_SOD_CONFLICT"
    assert not _evento_after(mundo, "GOV_MATERIAL_CLOSE_BLOCKED", politica["id"])
    cerrar_regla(mundo, regla)


def test_ga19_acto_de_otra_empresa_no_bloquea(mundo, gobierno, siembra):
    politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "ACTOS_SIN_EFICACIA")
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    acto_id = acto_emitido(mundo, siembra, date(ejercicio, 6, 1))
    with mundo.factory() as db:
        db.execute(
            text("UPDATE gov_acts SET company_id = :c WHERE id = :i"),
            {"c": mundo.company_b, "i": acto_id},
        )
        db.commit()
    response = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert response.status_code == 200


def test_ga20_acto_del_ejercicio_siguiente_no_bloquea(mundo, gobierno, siembra):
    politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "ACTOS_SIN_EFICACIA")
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    acto_emitido(mundo, siembra, date(ejercicio + 1, 1, 15))
    response = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert response.status_code == 200


def test_ga21_politica_vencida_real_no_bloquea(mundo, gobierno, siembra, monkeypatch):
    hoy = hoy_de_negocio()
    politica = crear_politica(
        mundo,
        "TRE02_CERRAR_PROGRAMA",
        vigente_desde=hoy.isoformat(),
        vigente_hasta=hoy.isoformat(),
    )
    politica = anadir_control(mundo, politica, "ACTOS_SIN_EFICACIA")
    assert activar(mundo, politica).status_code == 200
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    acto_emitido(mundo, siembra, date(ejercicio, 6, 1))
    monkeypatch.setattr(
        "app.modules.government.service_cierres.hoy_de_negocio",
        lambda: hoy + timedelta(days=1),
    )
    response = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert response.status_code == 200


def test_ga22_politica_de_estructura_no_toca_programa(mundo, gobierno, siembra):
    politica_vigente(
        mundo, "ORG02_CERRAR_ESTRUCTURA", "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO"
    )
    _hallazgo_pendiente(mundo, riesgo="ALTO")
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    response = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert response.status_code == 200
