"""Máquina de estados de la recepción completa (FR-004-031, FR-019-025 a FR-019-030)."""
from __future__ import annotations

import pytest

from app.core.errors import ConflictError, KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.inventory.models import InventoryMovement
from app.modules.purchasing import service as ap_service
from tests.test_recepcion_linea_integridad import (
    COMPANY,
    db_session,  # noqa: F401
    mundo,  # noqa: F401
)


def _linea(db, m, *, linea=None, recibido=10.0, aceptado=10.0, producto=None):
    linea = linea or m.linea_a
    if producto is None:
        producto = m.producto_a if linea is m.linea_a else m.producto_b
    return ap_service.add_receipt_line(
        db,
        company_id=COMPANY,
        receipt_id=str(m.recepcion.id),
        order_line_id=str(linea.id),
        product_id=str(producto.id),
        quantity_received=recibido,
        quantity_accepted=aceptado,
        quantity_rejected=recibido - aceptado,
    )


def _a_calidad(db, m):
    ap_service.confirm_receipt(db, receipt=m.recepcion, actor=None)
    ap_service.enviar_a_calidad(db, receipt=m.recepcion, actor=None)


def _aceptada(db, m, aceptado=10.0):
    _linea(db, m, aceptado=aceptado)
    _a_calidad(db, m)
    ap_service.registrar_conformidad(
        db, receipt=m.recepcion, quality_status="APPROVED", actor=None
    )
    ap_service.accept_receipt(db, receipt=m.recepcion, actor=None)


def _eventos(db, accion):
    return (
        db.query(AuditEvent)
        .filter(AuditEvent.action == accion)
        .order_by(AuditEvent.created_at)
        .all()
    )


def test_la_maquina_es_la_de_fr004031():
    assert ap_service.RECEIPT_TRANSITIONS == {
        "DRAFT": {"CONFIRMED", "CANCELLED"},
        "CONFIRMED": {"QUALITY_PENDING"},
        "QUALITY_PENDING": {"ACCEPTED", "PARTIALLY_ACCEPTED", "REJECTED"},
        "ACCEPTED": {"CLOSED"},
        "PARTIALLY_ACCEPTED": {"CLOSED"},
        "REJECTED": {"CLOSED"},
        "CLOSED": set(),
        "CANCELLED": set(),
    }


def test_qp01_confirmada_entra_en_calidad(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    ap_service.confirm_receipt(db_session, receipt=mundo.recepcion, actor=None)
    ap_service.enviar_a_calidad(db_session, receipt=mundo.recepcion, actor=None)
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "QUALITY_PENDING"


def test_qp02_borrador_no_entra_en_calidad(db_session, mundo):  # noqa: F811
    with pytest.raises(ConflictError) as exc:
        ap_service.enviar_a_calidad(db_session, receipt=mundo.recepcion, actor=None)
    assert exc.value.code == "INVALID_STATE_TRANSITION"
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "DRAFT"


def test_qp_sin_lineas_no_entra_en_calidad(db_session, mundo):  # noqa: F811
    ap_service.confirm_receipt(db_session, receipt=mundo.recepcion, actor=None)
    with pytest.raises(ConflictError) as exc:
        ap_service.enviar_a_calidad(db_session, receipt=mundo.recepcion, actor=None)
    assert exc.value.code == "RECEIPT_EMPTY"


def test_qp04_entrar_en_calidad_queda_auditado(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    _a_calidad(db_session, mundo)
    eventos = _eventos(db_session, "RECEIPT_TRANSITIONED")
    transiciones = [
        e for e in eventos
        if e.after and e.after.get("source") == "CONFIRMED"
        and e.after.get("target") == "QUALITY_PENDING"
    ]
    assert len(transiciones) == 1


def test_qp07_veredicto_fuera_de_calidad(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    ap_service.confirm_receipt(db_session, receipt=mundo.recepcion, actor=None)
    with pytest.raises(ConflictError) as exc:
        ap_service.registrar_conformidad(
            db_session, receipt=mundo.recepcion, quality_status="APPROVED", actor=None
        )
    assert exc.value.code == "QUALITY_NOT_PENDING"
    assert _eventos(db_session, "RECEIPT_QUALITY_RECORDED") == []


def test_qp08_no_se_acepta_sin_pasar_por_calidad(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    ap_service.confirm_receipt(db_session, receipt=mundo.recepcion, actor=None)
    mundo.recepcion.quality_status = "APPROVED"
    db_session.flush()
    with pytest.raises(ConflictError) as exc:
        ap_service.accept_receipt(db_session, receipt=mundo.recepcion, actor=None)
    assert exc.value.code == "INVALID_STATE_TRANSITION"
    assert db_session.query(InventoryMovement).count() == 0


def test_qp09_en_calidad_no_se_anaden_lineas(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    _a_calidad(db_session, mundo)
    with pytest.raises(ConflictError) as exc:
        _linea(db_session, mundo, linea=mundo.linea_b, producto=mundo.producto_b)
    assert exc.value.code == "RECEIPT_NOT_OPEN"


def test_pa01_todo_aceptado_es_aceptada(db_session, mundo):  # noqa: F811
    _aceptada(db_session, mundo, aceptado=10.0)
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "ACCEPTED"
    eventos = [
        e for e in _eventos(db_session, "RECEIPT_ACCEPTED")
        if e.after and e.after.get("status") == "ACCEPTED"
    ]
    assert len(eventos) == 1


def test_pa02_parte_aceptada_es_parcial(db_session, mundo):  # noqa: F811
    _aceptada(db_session, mundo, aceptado=7.0)
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "PARTIALLY_ACCEPTED"
    eventos = [
        e for e in _eventos(db_session, "RECEIPT_ACCEPTED")
        if e.after and e.after.get("status") == "PARTIALLY_ACCEPTED"
    ]
    assert len(eventos) == 1
    total = sum(m.quantity for m in db_session.query(InventoryMovement).all())
    assert total == 7
    db_session.refresh(mundo.linea_a)
    assert mundo.linea_a.quantity_received == 7


def test_pa02b_una_linea_parcial_basta(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo, linea=mundo.linea_a, producto=mundo.producto_a, recibido=10.0, aceptado=10.0)
    _linea(db_session, mundo, linea=mundo.linea_b, producto=mundo.producto_b, recibido=10.0, aceptado=5.0)
    _a_calidad(db_session, mundo)
    ap_service.registrar_conformidad(
        db_session, receipt=mundo.recepcion, quality_status="APPROVED", actor=None
    )
    ap_service.accept_receipt(db_session, receipt=mundo.recepcion, actor=None)
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "PARTIALLY_ACCEPTED"


def test_pa03_nada_aceptado_no_se_acepta(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo, recibido=10.0, aceptado=0.0)
    _a_calidad(db_session, mundo)
    ap_service.registrar_conformidad(
        db_session, receipt=mundo.recepcion, quality_status="APPROVED", actor=None
    )
    with pytest.raises(ConflictError) as exc:
        ap_service.accept_receipt(db_session, receipt=mundo.recepcion, actor=None)
    assert exc.value.code == "RECEIPT_NOTHING_ACCEPTED"
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "QUALITY_PENDING"
    assert db_session.query(InventoryMovement).count() == 0


def test_rechazo_de_calidad_es_rechazo_de_la_recepcion(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    _a_calidad(db_session, mundo)
    ap_service.registrar_conformidad(
        db_session, receipt=mundo.recepcion, quality_status="REJECTED", actor=None
    )
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "REJECTED"
    assert db_session.query(InventoryMovement).count() == 0


def test_cl01_aceptada_y_confirmada_se_cierra(db_session, mundo):  # noqa: F811
    _aceptada(db_session, mundo, aceptado=10.0)
    movimientos = db_session.query(InventoryMovement).count()
    mundo.recepcion.confirmation_status = "CONFIRMADA"
    db_session.flush()
    ap_service.cerrar_recepcion(db_session, receipt=mundo.recepcion, actor=None)
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "CLOSED"
    assert db_session.query(InventoryMovement).count() == movimientos
    eventos = [
        e for e in _eventos(db_session, "RECEIPT_TRANSITIONED")
        if e.after and e.after.get("target") == "CLOSED"
    ]
    assert len(eventos) == 1


def test_cl02_parcial_y_confirmada_se_cierra(db_session, mundo):  # noqa: F811
    _aceptada(db_session, mundo, aceptado=7.0)
    mundo.recepcion.confirmation_status = "CONFIRMADA"
    db_session.flush()
    ap_service.cerrar_recepcion(db_session, receipt=mundo.recepcion, actor=None)
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "CLOSED"


def test_cl03_rechazada_se_cierra(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    _a_calidad(db_session, mundo)
    ap_service.registrar_conformidad(
        db_session, receipt=mundo.recepcion, quality_status="REJECTED", actor=None
    )
    ap_service.cerrar_recepcion(db_session, receipt=mundo.recepcion, actor=None)
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "CLOSED"


def test_cl03b_rechazada_con_incidencia_viva_no_se_cierra(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    _a_calidad(db_session, mundo)
    ap_service.registrar_conformidad(
        db_session, receipt=mundo.recepcion, quality_status="REJECTED", actor=None
    )
    ap_service.registrar_incidencia(
        db_session,
        company_id=COMPANY,
        receipt_id=str(mundo.recepcion.id),
        code="INC-1",
        incident_type="DIFERENCIA_DOCUMENTAL",
        description="Falta un documento",
    )
    with pytest.raises(ConflictError) as exc:
        ap_service.cerrar_recepcion(db_session, receipt=mundo.recepcion, actor=None)
    assert exc.value.code == "RECEIPT_INCIDENTS_OPEN"
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "REJECTED"


def test_cl04_aceptada_sin_conciliar_no_se_cierra(db_session, mundo):  # noqa: F811
    _aceptada(db_session, mundo, aceptado=10.0)
    with pytest.raises(ConflictError) as exc:
        ap_service.cerrar_recepcion(db_session, receipt=mundo.recepcion, actor=None)
    assert exc.value.code == "RECEIPT_NOT_RECONCILED"
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "ACCEPTED"


def test_cl04b_confirmada_no_se_cierra(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    ap_service.confirm_receipt(db_session, receipt=mundo.recepcion, actor=None)
    with pytest.raises(ConflictError) as exc:
        ap_service.cerrar_recepcion(db_session, receipt=mundo.recepcion, actor=None)
    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_cl06_cerrar_no_cambia_cantidades(db_session, mundo):  # noqa: F811
    _aceptada(db_session, mundo, aceptado=7.0)
    db_session.refresh(mundo.linea_a)
    recibido_antes = mundo.linea_a.quantity_received
    mundo.recepcion.confirmation_status = "CONFIRMADA"
    db_session.flush()
    ap_service.cerrar_recepcion(db_session, receipt=mundo.recepcion, actor=None)
    db_session.refresh(mundo.linea_a)
    assert mundo.linea_a.quantity_received == recibido_antes


def test_cl08_cerrar_dos_veces_es_seguro(db_session, mundo):  # noqa: F811
    _aceptada(db_session, mundo, aceptado=10.0)
    mundo.recepcion.confirmation_status = "CONFIRMADA"
    db_session.flush()
    ap_service.cerrar_recepcion(db_session, receipt=mundo.recepcion, actor=None)
    with pytest.raises(ConflictError) as exc:
        ap_service.cerrar_recepcion(db_session, receipt=mundo.recepcion, actor=None)
    assert exc.value.code == "INVALID_STATE_TRANSITION"
    eventos = [
        e for e in _eventos(db_session, "RECEIPT_TRANSITIONED")
        if e.after and e.after.get("target") == "CLOSED"
    ]
    assert len(eventos) == 1


def test_cerrada_no_admite_incidencias(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    _a_calidad(db_session, mundo)
    ap_service.registrar_conformidad(
        db_session, receipt=mundo.recepcion, quality_status="REJECTED", actor=None
    )
    ap_service.cerrar_recepcion(db_session, receipt=mundo.recepcion, actor=None)
    with pytest.raises(ConflictError) as exc:
        ap_service.registrar_incidencia(
            db_session,
            company_id=COMPANY,
            receipt_id=str(mundo.recepcion.id),
            code="INC-2",
            incident_type="DIFERENCIA_DOCUMENTAL",
            description="Tarde",
        )
    assert exc.value.code == "RECEIPT_CLOSED"


def test_cn01_borrador_se_anula_con_motivo(db_session, mundo):  # noqa: F811
    ap_service.anular_recepcion(
        db_session, receipt=mundo.recepcion, reason="Creada por error", actor=None
    )
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "CANCELLED"
    eventos = [
        e for e in _eventos(db_session, "RECEIPT_TRANSITIONED")
        if e.after and e.after.get("target") == "CANCELLED"
    ]
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento.reason == "Creada por error"
    assert evento.after["reason"] == "Creada por error"


@pytest.mark.parametrize("motivo", ["", "   "])
def test_cn02_sin_motivo_no_se_anula(db_session, mundo, motivo):  # noqa: F811
    with pytest.raises(KontrolError) as exc:
        ap_service.anular_recepcion(
            db_session, receipt=mundo.recepcion, reason=motivo, actor=None
        )
    assert exc.value.code == "REASON_REQUIRED"
    assert exc.value.status_code == 422
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "DRAFT"
    assert _eventos(db_session, "RECEIPT_TRANSITIONED") == []


def test_cn07_confirmada_no_se_anula(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    ap_service.confirm_receipt(db_session, receipt=mundo.recepcion, actor=None)
    with pytest.raises(ConflictError) as exc:
        ap_service.anular_recepcion(
            db_session, receipt=mundo.recepcion, reason="Creada por error", actor=None
        )
    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_cn08_borrador_con_incidencia_viva_no_se_anula(db_session, mundo):  # noqa: F811
    ap_service.registrar_incidencia(
        db_session,
        company_id=COMPANY,
        receipt_id=str(mundo.recepcion.id),
        code="INC-1",
        incident_type="DIFERENCIA_DOCUMENTAL",
        description="Falta un documento",
    )
    with pytest.raises(ConflictError) as exc:
        ap_service.anular_recepcion(
            db_session, receipt=mundo.recepcion, reason="Creada por error", actor=None
        )
    assert exc.value.code == "RECEIPT_INCIDENTS_OPEN"
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "DRAFT"
    assert _eventos(db_session, "RECEIPT_TRANSITIONED") == []


def test_cn04_anular_no_mueve_inventario(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    ap_service.anular_recepcion(
        db_session, receipt=mundo.recepcion, reason="Creada por error", actor=None
    )
    assert db_session.query(InventoryMovement).count() == 0


def test_au01_confirmar_queda_auditado(db_session, mundo):  # noqa: F811
    _linea(db_session, mundo)
    ap_service.confirm_receipt(db_session, receipt=mundo.recepcion, actor="u-1")
    eventos = [
        e for e in _eventos(db_session, "RECEIPT_TRANSITIONED")
        if e.after and e.after.get("source") == "DRAFT"
        and e.after.get("target") == "CONFIRMED"
    ]
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento.user_id == "u-1"
    assert evento.company_id == COMPANY


def test_au09_transicion_invalida_no_audita(db_session, mundo):  # noqa: F811
    with pytest.raises(ConflictError):
        ap_service.enviar_a_calidad(db_session, receipt=mundo.recepcion, actor=None)
    assert _eventos(db_session, "RECEIPT_TRANSITIONED") == []


@pytest.mark.parametrize(
    ("estado", "calidad", "conciliacion", "esperado"),
    [
        ("DRAFT", "PENDING", "PENDIENTE", {"confirm", "cancel"}),
        ("CONFIRMED", "PENDING", "PENDIENTE", {"send_to_quality"}),
        ("QUALITY_PENDING", "PENDING", "PENDIENTE", {"record_quality"}),
        ("QUALITY_PENDING", "APPROVED", "PENDIENTE", {"accept"}),
        ("ACCEPTED", "APPROVED", "PENDIENTE", set()),
        ("ACCEPTED", "APPROVED", "CONFIRMADA", {"close"}),
        ("PARTIALLY_ACCEPTED", "APPROVED", "CONFIRMADA", {"close"}),
        ("REJECTED", "REJECTED", "PENDIENTE", {"close"}),
        ("CLOSED", "APPROVED", "CONFIRMADA", set()),
        ("CANCELLED", "PENDING", "PENDIENTE", set()),
    ],
)
def test_allowed_actions_publica_solo_lo_posible(
    db_session, mundo, estado, calidad, conciliacion, esperado  # noqa: F811
):
    mundo.recepcion.status = estado
    mundo.recepcion.quality_status = calidad
    mundo.recepcion.confirmation_status = conciliacion
    db_session.flush()
    acciones = ap_service.receipt_allowed_actions(mundo.recepcion)
    assert set(acciones.keys()) == {
        "confirm",
        "cancel",
        "send_to_quality",
        "record_quality",
        "accept",
        "close",
    }
    activas = {k for k, v in acciones.items() if v}
    assert activas == esperado
