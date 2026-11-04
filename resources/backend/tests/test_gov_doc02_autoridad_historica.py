"""Suite de backend para DOC-02: validación histórica de autoridad y competencias del acto."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.modules.government.models import (
    GovernmentEntity,
    GovernmentPosition,
    GovernmentPositionVersion,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseEntitlementSnapshot
from app.shared.clock import hoy_de_negocio

pytest_plugins = ("tests.conftest_multicompany",)

ANIO = hoy_de_negocio().year
ANT = ANIO - 1
TZ_CARACAS = ZoneInfo("America/Caracas")
ESTADO: dict = {}


@pytest.fixture(scope="module")
def gobierno(mundo):
    """Garantiza el entitlement `gobierno` en la snapshot sincronizada."""
    with mundo.factory() as db:
        inst = licensing_service.get_installation(db)
        snapshot = db.scalar(
            select(LicenseEntitlementSnapshot).where(
                LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                LicenseEntitlementSnapshot.version == "doc02-historica",
            )
        )
        if snapshot is None:
            snapshot = LicenseEntitlementSnapshot(
                installation_id=inst.installation_uuid,
                modules={"gobierno": True},
                version="doc02-historica",
                taken_at=datetime.now(UTC),
            )
            db.add(snapshot)
        else:
            snapshot.modules = {"gobierno": True}
        db.commit()


def _ente(mundo, company_id):
    """Crea un GovernmentEntity ACTIVO para la empresa."""
    with mundo.factory() as db:
        ente = GovernmentEntity(
            company_id=company_id,
            denominacion=f"Ente activo {company_id}",
            status="ACTIVO",
            version=1,
            activated_at=datetime.now(UTC),
        )
        db.add(ente)
        db.commit()
        return ente.id


def _crear_estructura(
    mundo,
    company_id,
    ente_id,
    ejercicio,
    status,
    *,
    published=True,
    closed=False,
):
    """Crea una estructura para una empresa y ejercicio."""
    with mundo.factory() as db:
        estructura = GovernmentStructure(
            company_id=company_id,
            entity_id=ente_id,
            exercise=ejercicio,
            status=status,
            version=1,
        )
        if published:
            estructura.published_at = datetime(ejercicio, 1, 1, 12, 0, tzinfo=TZ_CARACAS)
        if closed:
            estructura.closed_at = datetime(ejercicio, 12, 31, 12, 0, tzinfo=TZ_CARACAS)
        db.add(estructura)
        db.flush()
        db.commit()
        return estructura.id


def _unidad(mundo, company_id, structure_id, code, name):
    with mundo.factory() as db:
        unidad = GovernmentUnit(
            company_id=company_id,
            structure_id=structure_id,
            code=code,
            name=name,
            unit_type="UNIDAD_ADMINISTRATIVA",
            status="ACTIVA",
            valid_from=date(ANIO, 1, 1),
            version=1,
        )
        db.add(unidad)
        db.commit()
        return unidad.id


def _version_snapshot(
    *,
    codigo,
    denominacion,
    unidad_id,
    unidad_codigo,
    estado,
    vigente_desde,
    vigente_hasta,
    competencias,
):
    return {
        "codigo": codigo,
        "denominacion": denominacion,
        "unidad_id": unidad_id,
        "unidad_codigo": unidad_codigo,
        "estado": estado,
        "vigente_desde": vigente_desde,
        "vigente_hasta": vigente_hasta,
        "competencias": competencias,
    }


def _competencia(
    *,
    action,
    subject,
    limit_type,
    amount=None,
    currency=None,
    basis=None,
):
    return {
        "accion": action,
        "materia": subject,
        "tipo_limite": limit_type,
        "monto": amount,
        "moneda": currency,
        "fundamento": basis,
    }


def _crear_cargo_y_versiones(
    mundo,
    *,
    company_id,
    structure_id,
    unit_id,
    code,
    denominacion,
    status,
    valid_from,
    versiones,
):
    """Crea un cargo y únicamente sus versiones históricas (no materializa competencias actuales)."""
    with mundo.factory() as db:
        cargo = GovernmentPosition(
            company_id=company_id,
            structure_id=structure_id,
            unit_id=unit_id,
            code=code,
            name=denominacion,
            status=status,
            valid_from=valid_from,
            activated_at=datetime.now(UTC),
            version=len(versiones),
        )
        db.add(cargo)
        db.commit()
        cargo_id = cargo.id

        for numero, version in enumerate(versiones, start=1):
            db.add(
                GovernmentPositionVersion(
                    position_id=cargo_id,
                    structure_id=structure_id,
                    company_id=company_id,
                    version=numero,
                    status=version["status"],
                    snapshot=version["snapshot"],
                    reason=version.get("reason"),
                    actor_id=None,
                    created_at=version["created_at"],
                )
            )
            db.commit()

        return str(cargo_id)


def _cuerpo(**cambios) -> dict:
    """Cuerpo base válido de alta con cargo_id inyectado."""
    cuerpo = {
        "tipo": "RESOLUCION",
        "numero": "DA-001-ACTOS-HISTORICA",
        "fecha": hoy_de_negocio().isoformat(),
        "lugar": "Caracas",
        "cargo_id": "",
        "competencia": {"accion": "APROBAR", "materia": "CONTRATACIONES"},
        "fundamento_competencia": "Reglamento interno, art. 12",
        "funcionario": "Ana Pérez",
        "titularidad": "TITULAR",
        "caracter": "PARTICULAR",
        "destinatario": "Proveedor Ejemplo, C.A.",
        "asunto": "Adjudicación de servicio",
        "hechos": "Hechos de prueba",
        "fundamentos": "Fundamentos de prueba",
        "decision": "Decisión de prueba",
    }
    cuerpo.update(cambios)
    return cuerpo


@pytest.fixture(scope="module")
def escenario(mundo, gobierno):
    """Crea directamente con modelos el escenario histórico de DOC-02."""
    ente_a = _ente(mundo, mundo.company_a)
    ente_b = _ente(mundo, mundo.company_b)

    estructura_ant_a = _crear_estructura(mundo, mundo.company_a, ente_a, ANT, "VIGENTE")
    estructura_hoy_a = _crear_estructura(mundo, mundo.company_a, ente_a, ANIO, "VIGENTE")
    estructura_ant_b = _crear_estructura(mundo, mundo.company_b, ente_b, ANT, "VIGENTE")

    unidad_dir_adm = _unidad(mundo, mundo.company_a, estructura_ant_a, "DIR-ADM", "Dirección Administrativa")
    unidad_hoy = _unidad(mundo, mundo.company_a, estructura_hoy_a, "HOY", "Unidad Hoy")
    unidad_b = _unidad(mundo, mundo.company_b, estructura_ant_b, "B-UNIDAD", "Unidad B")

    def snapshot(codigo, competencias):
        return _version_snapshot(
            codigo=codigo,
            denominacion=f"Cargo {codigo}",
            unidad_id=unidad_dir_adm if codigo != "HOY-01" else unidad_hoy,
            unidad_codigo="DIR-ADM" if codigo != "HOY-01" else "HOY",
            estado="VIGENTE",
            vigente_desde=date(ANT, 1, 1).isoformat(),
            vigente_hasta=None,
            competencias=competencias,
        )

    # HIS-01
    his_01_v1 = snapshot(
        "HIS-01",
        [
            _competencia(action="APROBAR", subject="CONTRATACIONES", limit_type="SIN_LIMITE"),
        ],
    )
    his_01_v2 = snapshot(
        "HIS-01",
        [
            _competencia(action="FIRMAR", subject="EXPEDIENTE", limit_type="SIN_LIMITE"),
        ],
    )
    his_01_id = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_a,
        structure_id=estructura_ant_a,
        unit_id=unidad_dir_adm,
        code="HIS-01",
        denominacion="Cargo HIS-01",
        status="VIGENTE",
        valid_from=date(ANT, 1, 1),
        versiones=[
            {"status": "VIGENTE", "snapshot": his_01_v1, "created_at": datetime(ANT, 1, 10, 12, 0, tzinfo=TZ_CARACAS)},
            {"status": "VIGENTE", "snapshot": his_01_v2, "created_at": datetime(ANT, 3, 1, 12, 0, tzinfo=TZ_CARACAS)},
        ],
    )

    # HIS-02
    his_02_snap_feb = snapshot(
        "HIS-02",
        [
            _competencia(action="FIRMAR", subject="EXPEDIENTE", limit_type="SIN_LIMITE"),
        ],
    )
    his_02_snap_abr = snapshot(
        "HIS-02",
        [
            _competencia(action="FIRMAR", subject="EXPEDIENTE", limit_type="SIN_LIMITE"),
            _competencia(action="AUDITAR", subject="PRESUPUESTO", limit_type="SIN_LIMITE"),
        ],
    )
    his_02_id = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_a,
        structure_id=estructura_ant_a,
        unit_id=unidad_dir_adm,
        code="HIS-02",
        denominacion="Cargo HIS-02",
        status="VIGENTE",
        valid_from=date(ANT, 1, 1),
        versiones=[
            {"status": "VIGENTE", "snapshot": his_02_snap_feb, "created_at": datetime(ANT, 1, 10, 12, 0, tzinfo=TZ_CARACAS)},
            {"status": "VIGENTE", "snapshot": his_02_snap_abr, "created_at": datetime(ANT, 3, 1, 12, 0, tzinfo=TZ_CARACAS)},
        ],
    )

    # HOY-01
    hoy_01_snap = snapshot(
        "HOY-01",
        [
            _competencia(action="APROBAR", subject="CONTRATACIONES", limit_type="SIN_LIMITE"),
        ],
    )
    hoy_01_id = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_a,
        structure_id=estructura_hoy_a,
        unit_id=unidad_hoy,
        code="HOY-01",
        denominacion="Cargo HOY-01",
        status="VIGENTE",
        valid_from=date(ANIO, 1, 1),
        versiones=[
            {"status": "VIGENTE", "snapshot": hoy_01_snap, "created_at": datetime.now(UTC) - timedelta(minutes=5)},
        ],
    )

    # B-HIS
    b_his_snap = _version_snapshot(
        codigo="B-HIS",
        denominacion="Cargo B-HIS",
        unidad_id=unidad_b,
        unidad_codigo="B-UNIDAD",
        estado="VIGENTE",
        vigente_desde=date(ANT, 1, 1).isoformat(),
        vigente_hasta=None,
        competencias=[
            _competencia(action="APROBAR", subject="CONTRATACIONES", limit_type="SIN_LIMITE"),
        ],
    )
    b_his_id = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_b,
        structure_id=estructura_ant_b,
        unit_id=unidad_b,
        code="B-HIS",
        denominacion="Cargo B-HIS",
        status="VIGENTE",
        valid_from=date(ANT, 1, 1),
        versiones=[
            {"status": "VIGENTE", "snapshot": b_his_snap, "created_at": datetime(ANT, 1, 10, 12, 0, tzinfo=TZ_CARACAS)},
        ],
    )

    return {
        "his_01_id": his_01_id,
        "his_02_id": his_02_id,
        "hoy_01_id": hoy_01_id,
        "b_his_id": b_his_id,
        "estructura_ant_a": estructura_ant_a,
        " estructura_hoy_a": estructura_hoy_a,
    }


def test_gh_01_his01_competencia_historica_vigente(mundo, escenario):
    """HIS-01, fecha ANT-02-01: APROBAR/CONTRATACIONES estaba vigente aunque hoy no."""
    resp = mundo.post(
        "/gobierno/actos",
        "ua",
        mundo.company_a,
        _cuerpo(
            numero="DA-001-HIS-01",
            fecha=date(ANT, 2, 1).isoformat(),
            cargo_id=escenario["his_01_id"],
            competencia={"accion": "APROBAR", "materia": "CONTRATACIONES"},
        ),
    )
    assert resp.status_code == 201, resp.text
    ESTADO["gh01_id"] = resp.json()["id"]


def test_gh_02_his02_competencia_auditar_no_vigente_en_febrero(mundo, escenario):
    """HIS-02, fecha ANT-02-01: AUDITAR/PRESUPUESTO aún no estaba vigente."""
    resp = mundo.post(
        "/gobierno/actos",
        "ua",
        mundo.company_a,
        _cuerpo(
            numero="DA-002-HIS-02-FEB",
            fecha=date(ANT, 2, 1).isoformat(),
            cargo_id=escenario["his_02_id"],
            competencia={"accion": "AUDITAR", "materia": "PRESUPUESTO"},
        ),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_COMPETENCY"
    assert "competencia" in resp.json()["field_errors"]


def test_gh_03_his02_competencia_auditar_vigente_en_abril(mundo, escenario):
    """HIS-02, fecha ANT-04-01: AUDITAR/PRESUPUESTO ya estaba vigente."""
    resp = mundo.post(
        "/gobierno/actos",
        "ua",
        mundo.company_a,
        _cuerpo(
            numero="DA-003-HIS-02-ABR",
            fecha=date(ANT, 4, 1).isoformat(),
            cargo_id=escenario["his_02_id"],
            competencia={"accion": "AUDITAR", "materia": "PRESUPUESTO"},
        ),
    )
    assert resp.status_code == 201, resp.text


def test_gh_04_hoy01_competencia_actual(mundo, escenario):
    """HOY-01: APROBAR/CONTRATACIONES está vigente hoy."""
    resp = mundo.post(
        "/gobierno/actos",
        "ua",
        mundo.company_a,
        _cuerpo(
            numero="DA-004-HOY-01",
            fecha=hoy_de_negocio().isoformat(),
            cargo_id=escenario["hoy_01_id"],
            competencia={"accion": "APROBAR", "materia": "CONTRATACIONES"},
        ),
    )
    assert resp.status_code == 201, resp.text


def test_gh_05_cargo_de_otra_empresa_rechazado(mundo, escenario):
    """B-HIS de company_b desde company_a no es una autoridad válida."""
    resp = mundo.post(
        "/gobierno/actos",
        "ua",
        mundo.company_a,
        _cuerpo(
            numero="DA-005-B-HIS",
            fecha=date(ANT, 2, 1).isoformat(),
            cargo_id=escenario["b_his_id"],
            competencia={"accion": "APROBAR", "materia": "CONTRATACIONES"},
        ),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_AUTHORITY"


def test_gh_06_instantanea_del_acto_no_cambia_con_nueva_version(mundo, escenario):
    """Al añadir una versión reciente sin APROBAR/CONTRATACIONES, el acto GH-01 conserva su instantánea."""
    with mundo.factory() as db:
        cargo_id = escenario["his_01_id"]
        cargo = db.scalar(
            select(GovernmentPosition).where(GovernmentPosition.id == cargo_id)
        )
        assert cargo is not None

        snapshot = _version_snapshot(
            codigo="HIS-01",
            denominacion="Cargo HIS-01",
            unidad_id=cargo.unit_id,
            unidad_codigo="DIR-ADM",
            estado="VIGENTE",
            vigente_desde=date(ANT, 1, 1).isoformat(),
            vigente_hasta=None,
            competencias=[
                _competencia(action="FIRMAR", subject="EXPEDIENTE", limit_type="SIN_LIMITE"),
            ],
        )
        db.add(
            GovernmentPositionVersion(
                position_id=cargo_id,
                structure_id=cargo.structure_id,
                company_id=mundo.company_a,
                version=3,
                status="VIGENTE",
                snapshot=snapshot,
                reason="Prueba GH-06",
                actor_id=None,
                created_at=datetime.now(UTC),
            )
        )
        db.commit()

    acto_id = ESTADO["gh01_id"]
    resp = mundo.get(f"/gobierno/actos/{acto_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["competencia"] == {"accion": "APROBAR", "materia": "CONTRATACIONES"}


def test_gh_07_autoridades_y_matriz_coinciden(mundo, escenario):
    """GET autoridades para ANT-02-01 devuelve competencias históricas coherentes con la matriz."""
    fecha = date(ANT, 2, 1).isoformat()

    resp_autoridades = mundo.get(f"/gobierno/actos/autoridades?fecha={fecha}", "ua", mundo.company_a)
    assert resp_autoridades.status_code == 200, resp_autoridades.text
    autoridades = resp_autoridades.json()["items"]

    his_01 = next(a for a in autoridades if a["codigo"] == "HIS-01")
    his_02 = next(a for a in autoridades if a["codigo"] == "HIS-02")
    assert his_01["competencias"] == [{"accion": "APROBAR", "materia": "CONTRATACIONES"}]
    assert his_02["competencias"] == [{"accion": "FIRMAR", "materia": "EXPEDIENTE"}]

    resp_matriz = mundo.get(f"/gobierno/autoridad/{ANT}?fecha={fecha}", "ua", mundo.company_a)
    assert resp_matriz.status_code == 200, resp_matriz.text
    filas = resp_matriz.json()["items"]

    matriz_his_01 = [(f["accion"], f["materia"]) for f in filas if f["cargo_codigo"] == "HIS-01"]
    matriz_his_02 = [(f["accion"], f["materia"]) for f in filas if f["cargo_codigo"] == "HIS-02"]

    assert [
        (c["accion"], c["materia"]) for c in his_01["competencias"]
    ] == matriz_his_01
    assert [
        (c["accion"], c["materia"]) for c in his_02["competencias"]
    ] == matriz_his_02
