"""Pruebas de carrera de la ocupación de cargos (ORG-04)."""
import os
import threading
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentAssignment

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

from tests.org04_ayudantes import (  # noqa: E402
    D,
    O,
    accion,
    acto_eficaz,
    crear,
    crear_funcionario,
    cuerpo,
    nuevo_cargo,
    titular_activo,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="la carrera se mide en PostgreSQL",
)


def _post_con(mundo, cabeceras, asig, verbo, cuerpo=None, version=None):
    version = asig["version"] if version is None else version
    return mundo.client.post(
        f"/api/v1{O}/asignaciones/{asig['id']}/{verbo}",
        headers={**cabeceras, "If-Match": str(version)},
        json=cuerpo,
    )


def _carrera(mundo, funciones):
    """Ejecuta dos funciones en hilos con barrera y devuelve sus resultados."""
    resultados = [None, None]
    vivos = [True, True]
    barrera = threading.Barrier(2, timeout=30)

    def envoltura(i, funcion):
        try:
            barrera.wait()
            resultados[i] = funcion(mundo)
        finally:
            vivos[i] = False

    hilos = [threading.Thread(target=envoltura, args=(i, f)) for i, f in enumerate(funciones)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(60)

    assert not any(vivos), "un hilo de carrera no terminó"
    assert all(r is not None for r in resultados), "una función de carrera no devolvió resultado"
    return resultados


def _activas(cargo_id, mundo):
    """Devuelve el número de asignaciones ACTIVO para el cargo."""
    with mundo.factory() as db:
        return db.scalar(
            select(func.count())
            .select_from(GovernmentAssignment)
            .where(
                GovernmentAssignment.position_id == cargo_id,
                GovernmentAssignment.status == "ACTIVO",
            )
        )


def test_c1_dos_titulares_simultaneos(mundo, gobierno, ocupacion):
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"], medio="GACETA")

    f1 = crear_funcionario(mundo)
    f2 = crear_funcionario(mundo)

    a1 = crear(mundo, cuerpo(f1, cargo_id, acto_id), usuario="ua")
    a2 = crear(mundo, cuerpo(f2, cargo_id, acto_id), usuario="ua")

    cabeceras = mundo.como("uab", mundo.company_a)
    resultados = _carrera(
        mundo,
        [
            lambda m: _post_con(m, cabeceras, a1, "activar", version=a1["version"]),
            lambda m: _post_con(m, cabeceras, a2, "activar", version=a2["version"]),
        ],
    )

    estados = sorted(r.status_code for r in resultados)
    assert estados == [200, 409]

    conflicto = next(r for r in resultados if r.status_code == 409)
    assert conflicto.json()["code"] == "GOV_ASSIGNMENT_OVERLAP"

    assert _activas(cargo_id, mundo) == 1


def test_c2_delegaciones_incompatibles(mundo, gobierno, ocupacion):
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="GACETA")

    competencias_a = [{"accion": "APROBAR", "materia": "PRESUPUESTO"}]
    competencias_b = [{"accion": "APROBAR", "materia": "PRESUPUESTO"}]

    a1 = crear(
        mundo,
        cuerpo(
            asig_d["funcionario"],
            delegante,
            acto,
            figura="DELEGACION_ATRIBUCIONES",
            cargo_origen_id=cargo_delegado,
            rendicion="Rendirá cuenta mensual ante el delegante.",
            declara_delegable=True,
            competencias=competencias_a,
        ),
        usuario="ua",
    )
    a2 = crear(
        mundo,
        cuerpo(
            asig_d["funcionario"],
            delegante,
            acto,
            figura="DELEGACION_ATRIBUCIONES",
            cargo_origen_id=cargo_delegado,
            rendicion="Rendirá cuenta mensual ante el delegante.",
            declara_delegable=True,
            competencias=competencias_b,
        ),
        usuario="ua",
    )

    cabeceras = mundo.como("uab", mundo.company_a)
    resultados = _carrera(
        mundo,
        [
            lambda m: _post_con(m, cabeceras, a1, "activar", version=a1["version"]),
            lambda m: _post_con(m, cabeceras, a2, "activar", version=a2["version"]),
        ],
    )

    estados = sorted(r.status_code for r in resultados)
    assert estados == [200, 409]

    conflicto = next(r for r in resultados if r.status_code == 409)
    assert conflicto.json()["code"] == "GOV_ASSIGNMENT_OVERLAP"

    with mundo.factory() as db:
        activas = db.scalar(
            select(func.count())
            .select_from(GovernmentAssignment)
            .where(
                GovernmentAssignment.position_id == delegante,
                GovernmentAssignment.status == "ACTIVO",
            )
        )
    assert activas == 1


def test_c3_finalizar_mas_alta(mundo, gobierno, ocupacion):
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])

    antigua, _ = titular_activo(mundo, ocupacion, cargo_id)

    f2 = crear_funcionario(mundo)
    nueva = crear(
        mundo,
        cuerpo(f2, cargo_id, acto_id, desde=D(3, 2).isoformat()),
        usuario="ua",
    )

    cabeceras = mundo.como("uab", mundo.company_a)
    resultados = _carrera(
        mundo,
        [
            lambda m: _post_con(
                m,
                cabeceras,
                antigua,
                "finalizar",
                cuerpo={"fecha": D(3, 1).isoformat(), "motivo": "Cese por reestructuración orgánica."},
                version=antigua["version"],
            ),
            lambda m: _post_con(m, cabeceras, nueva, "activar", version=nueva["version"]),
        ],
    )

    finalizar = next(r for r in resultados if r.request.method == "POST" and "finalizar" in str(r.request.url))
    activar_resp = next(r for r in resultados if r is not finalizar)

    assert finalizar.status_code == 200
    assert activar_resp.status_code in (200, 409)
    if activar_resp.status_code == 409:
        assert activar_resp.json()["code"] == "GOV_ASSIGNMENT_OVERLAP"

    with mundo.factory() as db:
        estado_nueva = db.scalar(
            select(GovernmentAssignment.status).where(GovernmentAssignment.id == nueva["id"])
        )
        estado_antigua = db.scalar(
            select(GovernmentAssignment.status).where(GovernmentAssignment.id == antigua["id"])
        )

    assert estado_antigua == "FINALIZADO"
    if activar_resp.status_code == 200:
        assert estado_nueva == "ACTIVO"
        assert _activas(cargo_id, mundo) == 1
    else:
        assert estado_nueva == "BORRADOR"
        assert _activas(cargo_id, mundo) == 0
        with mundo.factory() as db:
            finalizadas = db.scalar(
                select(func.count())
                .select_from(GovernmentAssignment)
                .where(
                    GovernmentAssignment.position_id == cargo_id,
                    GovernmentAssignment.status == "FINALIZADO",
                )
            )
        assert finalizadas == 1


def test_c4_revocar_mas_designacion(mundo, gobierno, ocupacion):
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])

    antigua, _ = titular_activo(mundo, ocupacion, cargo_id)

    f2 = crear_funcionario(mundo)
    nueva = crear(
        mundo,
        cuerpo(f2, cargo_id, acto_id, desde=D(3, 2).isoformat()),
        usuario="ua",
    )

    acto_rev = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(3, 1))
    cabeceras = mundo.como("uab", mundo.company_a)
    resultados = _carrera(
        mundo,
        [
            lambda m: _post_con(
                m,
                cabeceras,
                antigua,
                "revocar",
                cuerpo={
                    "acto_id": acto_rev,
                    "fecha": D(3, 1).isoformat(),
                    "motivo": "Revocación por nueva designación.",
                },
                version=antigua["version"],
            ),
            lambda m: _post_con(m, cabeceras, nueva, "activar", version=nueva["version"]),
        ],
    )

    revocar = next(r for r in resultados if r.request.method == "POST" and "revocar" in str(r.request.url))
    activar_resp = next(r for r in resultados if r is not revocar)

    assert revocar.status_code == 200
    assert activar_resp.status_code in (200, 409)
    if activar_resp.status_code == 409:
        assert activar_resp.json()["code"] == "GOV_ASSIGNMENT_OVERLAP"

    with mundo.factory() as db:
        estado_nueva = db.scalar(
            select(GovernmentAssignment.status).where(GovernmentAssignment.id == nueva["id"])
        )
        estado_antigua = db.scalar(
            select(GovernmentAssignment.status).where(GovernmentAssignment.id == antigua["id"])
        )

    assert estado_antigua == "REVOCADO"
    if activar_resp.status_code == 200:
        assert estado_nueva == "ACTIVO"
        assert _activas(cargo_id, mundo) == 1
    else:
        assert estado_nueva == "BORRADOR"
        assert _activas(cargo_id, mundo) == 0
        with mundo.factory() as db:
            revocadas = db.scalar(
                select(func.count())
                .select_from(GovernmentAssignment)
                .where(
                    GovernmentAssignment.position_id == cargo_id,
                    GovernmentAssignment.status == "REVOCADO",
                )
            )
        assert revocadas == 1


def test_c5_if_match_misma_version(mundo, gobierno, ocupacion):
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"], medio="GACETA")

    f1 = crear_funcionario(mundo)
    borrador = crear(mundo, cuerpo(f1, cargo_id, acto_id), usuario="ua")
    version = borrador["version"]

    cabeceras = mundo.como("uab", mundo.company_a)
    resultados = _carrera(
        mundo,
        [
            lambda m: _post_con(m, cabeceras, borrador, "activar", version=version),
            lambda m: _post_con(m, cabeceras, borrador, "activar", version=version),
        ],
    )

    estados = sorted(r.status_code for r in resultados)
    assert estados == [200, 409]

    conflicto = next(r for r in resultados if r.status_code == 409)
    codigo = conflicto.json()["code"]
    assert codigo in {"GOV_ASSIGNMENT_STALE", "GOV_ASSIGNMENT_INVALID_STATE"}

    with mundo.factory() as db:
        eventos = db.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.action == "GOV_ASSIGNMENT_ACTIVATED",
                AuditEvent.entity_id == borrador["id"],
            )
        )
    assert eventos == 1


def test_c6_exclusion_protege_sin_servicio(mundo, gobierno, ocupacion):
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"], medio="GACETA")

    f1 = crear_funcionario(mundo)
    f2 = crear_funcionario(mundo)

    a1 = crear(mundo, cuerpo(f1, cargo_id, acto_id), usuario="ua")
    a2 = crear(mundo, cuerpo(f2, cargo_id, acto_id), usuario="ua")

    r = accion(mundo, a1, "activar", usuario="uab")
    assert r.status_code == 200, r.text

    with pytest.raises(IntegrityError) as exc_info:
        with mundo.factory() as db:
            fila = db.get(GovernmentAssignment, a2["id"])
            fila.status = "ACTIVO"
            fila.activated_at = datetime.now(UTC)
            fila.activated_by = fila.created_by
            db.commit()

    assert "ex_gov_assignments_ocupacion" in str(exc_info.value)
