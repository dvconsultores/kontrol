"""El almacén de una recepción debe ser de la empresa (FR-004-030, I-039)."""
from types import SimpleNamespace

import pytest

from app.core.errors import NotFoundError
from app.modules.purchasing import service

EMPRESA_A = "00000000-0000-0000-0000-00000000000a"
EMPRESA_B = "00000000-0000-0000-0000-00000000000b"


@pytest.fixture(autouse=True)
def _orden_aprobada(monkeypatch):
    monkeypatch.setattr(
        service,
        "_require_order",
        lambda db, company_id, order_id: SimpleNamespace(status="APPROVED"),
    )


class _Base:
    def __init__(self, almacen):
        self._almacen = almacen

    def get(self, modelo, id_):
        return self._almacen

    def add(self, obj):
        raise AssertionError("no debe escribir")

    def flush(self):
        raise AssertionError("no debe escribir")


def _crear(db, warehouse_id):
    return service.create_receipt(
        db,
        company_id=EMPRESA_A,
        code="REC-1",
        order_id="o1",
        warehouse_id=warehouse_id,
    )


def test_almacen_de_otra_empresa_no_sirve():
    db = _Base(SimpleNamespace(company_id=EMPRESA_B))

    with pytest.raises(NotFoundError) as excinfo:
        _crear(db, "w-1")

    assert excinfo.value.code == "WAREHOUSE_NOT_FOUND"


def test_un_codigo_no_sirve_como_identificador():
    db = _Base(None)

    with pytest.raises(NotFoundError) as excinfo:
        _crear(db, "W1")

    assert excinfo.value.code == "WAREHOUSE_NOT_FOUND"


def test_identificador_vacio_no_sirve():
    db = _Base(None)

    with pytest.raises(NotFoundError) as excinfo:
        _crear(db, "")

    assert excinfo.value.code == "WAREHOUSE_NOT_FOUND"
