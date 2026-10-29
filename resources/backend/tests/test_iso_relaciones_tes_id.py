"""Pruebas hostiles (rojo primero) de aislamiento entre tenants para tesorería, notificaciones,
roles, sesiones, estructura de almacén, exportaciones y ayudantes de propiedad.

Rojo atribuible del ciclo 07; ajeno = inexistente (ADR-D0-014). Los casos hostiles deben fallar
con el producto actual; los controles positivos deben pasar.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from hostil_mundo import CasoHostil, MundoHostil, ejecutar_caso
from sqlalchemy import text

from app.core.errors import NotFoundError
from app.modules.fiscal.api import _owned as propiedad_fiscal
from app.modules.identity_access.models import Role
from app.modules.inventory.api import _get_owned as propiedad_inventario
from app.modules.master_data.models import CatalogItem, Supplier
from app.modules.organization.models import Warehouse, WarehouseZone
from app.modules.purchasing.api import _owned as propiedad_compras
from app.modules.regulatory.api import _owned as propiedad_regulatorio
from app.modules.reporting.models import ReportExport
from app.modules.sales.api import _owned as propiedad_ventas
from app.modules.treasury.api import _owned as propiedad_tesoreria
from app.modules.treasury.models import CashSession, Reconciliation

pytest_plugins = ("tests.hostil_mundo",)


@pytest.fixture(scope="module")
def prep(mundo_hostil: MundoHostil) -> dict[str, Any]:
    """Prepara filas ORM reales necesarias para los casos."""
    code = "ISO" + secrets.token_hex(4).upper()
    empresa_a1 = mundo_hostil.empresas["A1"]

    with mundo_hostil.factory() as db:
        cash_session = CashSession(company_id=empresa_a1, cashbox_id=mundo_hostil.recursos["A1"]["cashbox"])
        reconciliation = Reconciliation(
            company_id=empresa_a1, account_id=mundo_hostil.recursos["A1"]["bank_account"]
        )
        warehouse = Warehouse(
            company_id=empresa_a1,
            code=code,
            name="WZ",
            structure_levels={"zone": True, "aisle": False, "rack": False, "level": False},
        )
        db.add_all([cash_session, reconciliation, warehouse])
        db.flush()

        zonas: dict[str, str] = {}
        for empresa, clave in (("A1", "A1"), ("A2", "A2"), ("B1", "B1")):
            warehouse_id = (
                str(warehouse.id)
                if clave == "A1"
                else mundo_hostil.recursos[clave]["warehouse"]
            )
            db.execute(
                text(
                    "UPDATE warehouses SET structure_levels = "
                    ":niveles WHERE id = :id"
                ),
                {
                    "niveles": '{"zone": true, "aisle": false, "rack": false, "level": false}',
                    "id": warehouse_id,
                },
            )
            zona = WarehouseZone(
                company_id=mundo_hostil.empresas[empresa],
                warehouse_id=warehouse_id,
                code=code + f"-{clave}",
                name="Z",
            )
            db.add(zona)
            db.flush()
            zonas[empresa] = str(zona.id)

        rol_consulta_tb = db.query(Role).filter(Role.code == "R_ISO_CONSULTA_TB").one()
        rol_audit_tb = db.query(Role).filter(Role.code == "R_ISO_AUDIT_TB").one()
        rol_consulta_ta = db.query(Role).filter(Role.code == "R_ISO_CONSULTA_TA").one()
        rol_audit_ta = db.query(Role).filter(Role.code == "R_ISO_AUDIT_TA").one()

        db.commit()

        return {
            "code": code,
            "cash_session": str(cash_session.id),
            "reconciliation": str(reconciliation.id),
            "warehouse": str(warehouse.id),
            "zonas": zonas,
            "roles": {
                "tb": {
                    "consulta": str(rol_consulta_tb.id),
                    "audit": str(rol_audit_tb.id),
                },
                "ta": {
                    "consulta": str(rol_consulta_ta.id),
                    "audit": str(rol_audit_ta.id),
                },
            },
        }


@pytest.fixture(scope="module")
def uuid_nuevo() -> str:
    return str(uuid.uuid4())


def _codigo_nuevo() -> str:
    return "ISO" + secrets.token_hex(4).upper()


CASOS_TES = [
    pytest.param(
        "ISO-TES-01",
        "a1_op",
        "POST",
        "/treasury/cash-sessions/{ref}/movements",
        {"movement_type": "IN", "amount": "10.00", "instrument_id": "<origen>"},
        "INSTRUMENT_NOT_FOUND",
        id="ISO-TES-01",
    ),
    pytest.param(
        "ISO-TES-02",
        "a1_op",
        "POST",
        "/treasury/cash-sessions/{ref}/movements",
        {"movement_type": "IN", "amount": "10.00", "payment_id": "<origen>"},
        "PAYMENT_NOT_FOUND",
        id="ISO-TES-02",
    ),
    pytest.param(
        "ISO-TES-03",
        "a1_op",
        "POST",
        "/treasury/reconciliations/{ref}/lines",
        {"bank_transaction_id": "<origen>"},
        "BANK_TRANSACTION_NOT_FOUND",
        id="ISO-TES-03",
    ),
    pytest.param(
        "ISO-WH-01",
        "admin_a",
        "POST",
        "/organization/locations",
        {"warehouse_id": "<ref>", "zone_id": "<origen>"},
        "ZONE_NOT_FOUND",
        id="ISO-WH-01",
    ),
]


@pytest.mark.parametrize(
    "nombre,actor,metodo,ruta,cuerpo,codigo",
    CASOS_TES,
)
@pytest.mark.parametrize("origen", ["A2", "B1", "INEXISTENTE"])
def test_relaciones_tes_wh(
    mundo_hostil: MundoHostil,
    prep: dict[str, Any],
    uuid_nuevo: str,
    nombre: str,
    actor: str,
    metodo: str,
    ruta: str,
    cuerpo: dict[str, Any],
    codigo: str,
    origen: str,
) -> None:
    """Casos hostiles de relaciones de tesorería y estructura de almacén."""
    valores = dict(cuerpo)
    if "zone_id" in valores:
        valores["code"] = _codigo_nuevo()
        valores["name"] = "L"
    ref = prep["warehouse"] if "zone_id" in valores else (
        prep["cash_session"] if "cash-sessions" in ruta else prep["reconciliation"]
    )
    origen_id = (
        uuid_nuevo
        if origen == "INEXISTENTE"
        else (
            prep["zonas"][origen]
            if "zone_id" in valores
            else mundo_hostil.recursos[origen][
                "instrument" if "instrument_id" in valores else (
                    "payment" if "payment_id" in valores else "bank_transaction"
                )
            ]
        )
    )
    for clave in ("instrument_id", "payment_id", "bank_transaction_id", "zone_id"):
        if clave in valores:
            valores[clave] = origen_id
            break
    if "zone_id" in valores:
        valores["warehouse_id"] = prep["warehouse"]

    caso = CasoHostil(
        nombre,
        actor,
        metodo,
        ruta.replace("{ref}", ref),
        empresa_activa=mundo_hostil.empresas["A1"],
        json=valores,
        estado=404,
        codigo=codigo,
        tablas_inmutables=["cash_session_movements", "reconciliation_lines", "warehouse_locations"],
    )
    ejecutar_caso(mundo_hostil, caso)


@pytest.mark.parametrize("origen", ["B1", "INEXISTENTE"])
def test_iso_not_01(
    mundo_hostil: MundoHostil,
    prep: dict[str, Any],
    uuid_nuevo: str,
    origen: str,
) -> None:
    """Regla de notificación con rol ajeno o inexistente debe fallar."""
    rol = (
        uuid_nuevo
        if origen == "INEXISTENTE"
        else prep["roles"]["tb"]["audit"]
    )
    caso = CasoHostil(
        "ISO-NOT-01",
        "admin_a",
        "POST",
        "/notifications/rules",
        empresa_activa=mundo_hostil.empresas["A1"],
        json={
            "code": _codigo_nuevo(),
            "source": "APPROVAL",
            "event_type": "approval.step_opened",
            "effect": "TASK",
            "escalation_after_minutes": 30,
            "escalation_role_id": rol,
        },
        estado=422,
        codigo="NOTIFICATION_RULE_INVALID",
        tablas_inmutables=["notification_rules"],
    )
    respuesta = ejecutar_caso(mundo_hostil, caso)
    assert "ROLE_NOT_FOUND" in respuesta.text


def test_iso_rol_01(mundo_hostil: MundoHostil, prep: dict[str, Any]) -> None:
    """GET /roles no debe exponer roles del otro tenant."""
    respuesta = mundo_hostil.pedir("admin_a", "GET", "/roles")
    assert respuesta.status_code == 200
    assert "R_ISO_CONSULTA_TB" not in respuesta.text
    assert "R_ISO_AUDIT_TB" not in respuesta.text


@pytest.mark.parametrize("rol_id", ["B1", "INEXISTENTE"])
def test_iso_rol_02(
    mundo_hostil: MundoHostil,
    prep: dict[str, Any],
    uuid_nuevo: str,
    rol_id: str,
) -> None:
    """Asignar un rol ajeno o inexistente debe fallar."""
    rol = uuid_nuevo if rol_id == "INEXISTENTE" else prep["roles"]["tb"]["consulta"]
    caso = CasoHostil(
        "ISO-ROL-02",
        "admin_a",
        "POST",
        f"/users/{mundo_hostil.actores['a1_consulta'].user_id}/roles",
        json={"role_id": rol},
        estado=404,
        codigo="ROLE_NOT_FOUND",
        tablas_inmutables=["user_roles"],
    )
    ejecutar_caso(mundo_hostil, caso)


def test_iso_rol_03(mundo_hostil: MundoHostil, prep: dict[str, Any]) -> None:
    """Crear en TA un rol con código que solo existe en TB debe dar 201."""
    respuesta = mundo_hostil.pedir(
        "admin_a",
        "POST",
        "/roles",
        json={
            "code": "R_ISO_AUDIT_TB",
            "name": "Auditoría propia",
            "permissions": ["audit:view"],
        },
    )
    assert respuesta.status_code == 201
    assert mundo_hostil.contar("roles", code="R_ISO_AUDIT_TB") == 2


@pytest.mark.parametrize("sesion", ["ajena", "inexistente"])
def test_iso_ses_01(
    mundo_hostil: MundoHostil,
    prep: dict[str, Any],
    uuid_nuevo: str,
    sesion: str,
) -> None:
    """Eliminar una sesión de otro tenant o inexistente debe fallar."""
    if sesion == "inexistente":
        sesion_id = uuid_nuevo
    else:
        with mundo_hostil.factory() as db:
            sesion_id = str(
                db.execute(
                    text(
                        "SELECT id FROM sessions WHERE user_id = :usuario "
                        "ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"usuario": mundo_hostil.actores["admin_b"].user_id},
                ).scalar_one()
            )
    caso = CasoHostil(
        "ISO-SES-01",
        "a1_op",
        "DELETE",
        f"/auth/sessions/{sesion_id}",
        empresa_activa=mundo_hostil.empresas["A1"],
        estado=404,
        codigo="SESSION_NOT_FOUND",
        tablas_inmutables=["sessions"],
    )
    ejecutar_caso(mundo_hostil, caso)


CONTROLES_BASE = [
    pytest.param(
        "ISO-TES-01-POS", "a1_op", "POST", "/treasury/cash-sessions/{ref}/movements",
        {"movement_type": "IN", "amount": "10.00", "instrument_id": "<propio>"},
        id="control-tes-01",
    ),
    pytest.param(
        "ISO-TES-02-POS", "a1_op", "POST", "/treasury/cash-sessions/{ref}/movements",
        {"movement_type": "IN", "amount": "10.00", "payment_id": "<propio>"},
        id="control-tes-02",
    ),
    pytest.param(
        "ISO-TES-03-POS", "a1_op", "POST", "/treasury/reconciliations/{ref}/lines",
        {"bank_transaction_id": "<propio>"},
        id="control-tes-03",
    ),
    pytest.param(
        "ISO-WH-01-POS", "admin_a", "POST", "/organization/locations",
        {"warehouse_id": "<ref>", "code": "<codigo>", "name": "L", "zone_id": "<propio>"},
        id="control-wh-01",
    ),
]


@pytest.mark.parametrize(
    "nombre,actor,metodo,ruta,cuerpo_plantilla",
    CONTROLES_BASE,
)
def test_controles_positivos(
    mundo_hostil: MundoHostil,
    prep: dict[str, Any],
    nombre: str,
    actor: str,
    metodo: str,
    ruta: str,
    cuerpo_plantilla: dict[str, Any],
) -> None:
    """Controles positivos con recursos propios de A1."""
    cuerpo = dict(cuerpo_plantilla)
    if "instrument_id" in cuerpo_plantilla:
        cuerpo["instrument_id"] = mundo_hostil.recursos["A1"]["instrument"]
    elif "payment_id" in cuerpo_plantilla:
        cuerpo["payment_id"] = mundo_hostil.recursos["A1"]["payment"]
    elif "bank_transaction_id" in cuerpo_plantilla:
        cuerpo["bank_transaction_id"] = mundo_hostil.recursos["A1"]["bank_transaction"]
    elif "zone_id" in cuerpo_plantilla:
        cuerpo["code"] = _codigo_nuevo()
        cuerpo["zone_id"] = prep["zonas"]["A1"]
        cuerpo["warehouse_id"] = prep["warehouse"]

    ref = (
        prep["cash_session"]
        if "cash-sessions" in ruta
        else prep["reconciliation"] if "reconciliations" in ruta else prep["warehouse"]
    )
    respuesta = mundo_hostil.pedir(
        actor,
        metodo,
        ruta.replace("{ref}", ref),
        empresa=mundo_hostil.empresas["A1"],
        json=cuerpo,
    )
    assert respuesta.status_code in (200, 201), respuesta.text


def test_iso_not_01_positivo(mundo_hostil: MundoHostil, prep: dict[str, Any]) -> None:
    """Control positivo ISO-NOT-01 con rol propio de TA."""
    respuesta = mundo_hostil.pedir(
        "admin_a",
        "POST",
        "/notifications/rules",
        empresa=mundo_hostil.empresas["A1"],
        json={
            "code": _codigo_nuevo(),
            "source": "APPROVAL",
            "event_type": "approval.step_opened",
            "effect": "TASK",
            "escalation_after_minutes": 30,
            "escalation_role_id": prep["roles"]["ta"]["audit"],
        },
    )
    assert respuesta.status_code == 201, respuesta.text


def test_iso_rol_02_positivo(mundo_hostil: MundoHostil, prep: dict[str, Any]) -> None:
    """Control positivo ISO-ROL-02 con rol propio de TA."""
    respuesta = mundo_hostil.pedir(
        "admin_a",
        "POST",
        f"/users/{mundo_hostil.actores['a1_consulta'].user_id}/roles",
        json={"role_id": prep["roles"]["ta"]["audit"]},
    )
    assert respuesta.status_code == 200, respuesta.text


def test_iso_sto_01(
    mundo_hostil: MundoHostil,
    prep: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dos exportaciones con el mismo file_ref no pueden sobrescribirse."""
    from app.modules.reporting import service as reporting_service

    class _Fijo:
        @staticmethod
        def now(tz=None):
            return datetime(2026, 10, 29, 12, 0, tzinfo=UTC)

    monkeypatch.setattr(reporting_service.uuid, "uuid4", lambda: uuid.UUID(int=7))
    monkeypatch.setattr(reporting_service, "datetime", _Fijo)

    with mundo_hostil.factory() as db:
        actor = mundo_hostil.actores["a1_op"].user_id
        primera = reporting_service.create_export(
            db,
            company_id=mundo_hostil.empresas["A1"],
            report_key="operational_inventario",
            fmt="CSV",
            filters={},
            actor=actor,
        )
        fichero = reporting_service._exports_dir() / primera.file_ref
        fichero.write_bytes(b"MARCA-ISO")

        with pytest.raises(FileExistsError):
            reporting_service.create_export(
                db,
                company_id=mundo_hostil.empresas["A1"],
                report_key="operational_inventario",
                fmt="CSV",
                filters={},
                actor=actor,
            )

        assert fichero.read_bytes() == b"MARCA-ISO"
        db.rollback()


@pytest.mark.parametrize(
    "ayudante",
    [
        pytest.param(propiedad_inventario, id="inventario"),
        pytest.param(propiedad_compras, id="compras"),
        pytest.param(propiedad_ventas, id="ventas"),
        pytest.param(propiedad_tesoreria, id="tesoreria"),
        pytest.param(propiedad_regulatorio, id="regulatorio"),
        pytest.param(propiedad_fiscal, id="fiscal"),
    ],
)
def test_iso_hlp_01(
    mundo_hostil: MundoHostil,
    prep: dict[str, Any],
    ayudante: Any,
) -> None:
    """Los ayudantes de propiedad fallan cerrado sin columna company_id."""
    with mundo_hostil.factory() as db:
        with pytest.raises(TypeError):
            ayudante(
                db,
                Supplier,
                mundo_hostil.recursos["B1"]["supplier"],
                mundo_hostil.empresas["A1"],
                "SUPPLIER_NOT_FOUND",
                "Proveedor no encontrado",
            )


def test_iso_tes_04_una_ejecucion_de_otra_empresa_no_cuenta(mundo_hostil, prep):
    """Id ISO-TES-04: una ejecución registrada en otra empresa con el mismo payment_id no debe contar.

    _find_execution debe filtrar por empresa; de lo contrario un dato histórico de otra
    empresa haría que el pago se diera por ejecutado sin ejecutarse.
    """
    from app.modules.treasury import service as treasury_service
    from app.modules.treasury.models import BankTransaction, CashSessionMovement

    with mundo_hostil.factory() as db:
        db.add(
            CashSessionMovement(
                session_id=prep["cash_session"],
                movement_type="IN",
                amount=1,
                payment_id=mundo_hostil.recursos["B1"]["payment"],
            )
        )
        db.flush()

        assert (
            treasury_service._find_execution(
                db,
                mundo_hostil.recursos["B1"]["payment"],
                company_id=mundo_hostil.empresas["B1"],
            )
            is None
        )
        assert (
            treasury_service._find_execution(
                db,
                mundo_hostil.recursos["B1"]["payment"],
                company_id=mundo_hostil.empresas["A1"],
            )
            is not None
        )

        db.add(
            BankTransaction(
                company_id=mundo_hostil.empresas["A1"],
                account_id=mundo_hostil.recursos["A1"]["bank_account"],
                amount=1,
                payment_id=mundo_hostil.recursos["B2"]["payment"],
            )
        )
        db.flush()

        assert (
            treasury_service._find_execution(
                db,
                mundo_hostil.recursos["B2"]["payment"],
                company_id=mundo_hostil.empresas["B2"],
            )
            is None
        )

        db.rollback()


@pytest.mark.parametrize(
    "ayudante",
    [
        pytest.param(propiedad_inventario, id="inventario"),
        pytest.param(propiedad_compras, id="compras"),
        pytest.param(propiedad_ventas, id="ventas"),
        pytest.param(propiedad_tesoreria, id="tesoreria"),
        pytest.param(propiedad_regulatorio, id="regulatorio"),
        pytest.param(propiedad_fiscal, id="fiscal"),
    ],
)
def test_iso_hlp_02_los_ayudantes_rechazan_el_objeto_de_otra_empresa(
    mundo_hostil, ayudante
):
    """ISO-HLP-02: los ayudantes de propiedad rechazan objetos de otra empresa."""
    with mundo_hostil.factory() as db:
        with pytest.raises(NotFoundError) as excinfo:
            ayudante(
                db,
                CatalogItem,
                mundo_hostil.recursos["B1"]["product"],
                mundo_hostil.empresas["A1"],
                code="PRODUCT_NOT_FOUND",
                message="Producto no encontrado",
            )
        assert excinfo.value.code == "PRODUCT_NOT_FOUND"

        obj = ayudante(
            db,
            CatalogItem,
            mundo_hostil.recursos["A1"]["product"],
            mundo_hostil.empresas["A1"],
            code="PRODUCT_NOT_FOUND",
            message="Producto no encontrado",
        )
        assert str(obj.id) == mundo_hostil.recursos["A1"]["product"]


def test_iso_sto_02_una_exportacion_de_otra_empresa_no_se_sirve(mundo_hostil):
    """ISO-STO-02: una exportación de otra empresa no se sirve."""
    from app.modules.reporting import service as reporting_service

    with mundo_hostil.factory() as db:
        export = ReportExport(
            company_id=mundo_hostil.empresas["B1"],
            report_key="operational_inventario",
            format="CSV",
            file_ref=None,
            status="DONE",
        )
        db.add(export)
        db.flush()

        with pytest.raises(NotFoundError) as excinfo:
            reporting_service.get_export_file(
                db,
                export_id=export.id,
                company_id=mundo_hostil.empresas["A1"],
            )
        assert excinfo.value.code == "EXPORT_NOT_FOUND"

        with pytest.raises(NotFoundError) as excinfo:
            reporting_service.get_export_file(
                db,
                export_id=export.id,
                company_id=mundo_hostil.empresas["B1"],
            )
        assert excinfo.value.code == "EXPORT_FILE_MISSING"

        db.rollback()
