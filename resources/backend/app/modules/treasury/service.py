"""Servicios de tesorería (006).

Cajas (sesiones, movimientos, arqueo, pre-cierre, cierre y diferencias), bancos
(transacciones, ingresos/egresos, transferencias y depósitos), conciliación
asistida con reglas y resolución manual auditada, e IGTF por regla y evento.

Integración: 006 consume los pagos de 004 (egresos) y los cobros de 005
(ingresos) vía `ap_payments`; no duplica su lógica. La ejecución marca el
pago/cobro como POSTED y genera la transacción de caja o banco (idempotente).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import Payment
from app.modules.sales.models import SalesCreditNote
from app.modules.treasury import rates
from app.modules.treasury.models import (
    BankTransaction,
    Cashbox,
    CashSession,
    CashSessionMovement,
    Currency,
    ExchangeRate,
    FinancialAccount,
    FinancialBank,
    FiscalRule,
    IgftEvent,
    PaymentMethod,
    Reconciliation,
    ReconciliationLine,
    TreasuryFxConversion,
    TreasuryFxPolicy,
    TreasuryInstrument,
    TreasuryRateSnapshot,
    TreasuryRefund,
    TreasuryTransfer,
)
from app.shared import audit as audit_service


def _audit(db: Session, *, action: str, entity_type: str, entity_id: str,
           company_id: str, actor: str | None = None, **kw: Any) -> None:
    """Registra un evento de auditoría de negocio (KAUD-001 → FR-009-022)."""
    audit_service.record_audit(
        db, action=action, entity_type=entity_type, entity_id=entity_id,
        company_id=company_id, user_id=actor, source="API", **kw,
    )

# --------------------------------------------------------------------------- #
# Máquinas de estado (DOC-02 §10 / DOC-03 §13)
# --------------------------------------------------------------------------- #
CASH_SESSION_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"ARCHED"},
    "ARCHED": {"PRE_CLOSED"},
    "PRE_CLOSED": {"CLOSED", "REJECTED"},
    "CLOSED": set(),
    "REJECTED": set(),
}

RECONCILIATION_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"IN_PROGRESS"},
    "IN_PROGRESS": {"REVIEW"},
    "REVIEW": {"APPROVED", "REJECTED"},
    "APPROVED": set(),
    "REJECTED": set(),
}


def _assert_transition(current: str, target: str, transitions: dict[str, set[str]], what: str) -> None:
    if target not in transitions.get(current, set()):
        raise ConflictError(code="INVALID_STATE_TRANSITION", message=f"No se permite pasar {what} de {current} a {target}.")


def _company(company_id: str | None, *, obj: str) -> str:
    if not company_id:
        raise KontrolError(code="COMPANY_REQUIRED", message="Se requiere la empresa para esta operación", status_code=422)
    return company_id


#: La escala de las columnas monetarias de tesorería, `NUMERIC(18, 2)`. Su
#: autoridad es `Currency.decimal_places`: si hiciera falta otra, cambiaría la
#: columna. Aquí no se decide ninguna política de redondeo.
_MONEY_PLACES = 2


def _money(value: Any) -> Decimal:
    """Dinero como `Decimal` exacto, **sin pasar por `float`**.

    Misma regla que la autoridad compartida de saldos (delta de la Spec 028):
    `ADR-D0-001` registra `KQA-100` —«`Decimal + float`… que rompió factura,
    pago, cobro»— como defecto CRÍTICO. El arqueo de caja nunca lo recibió, y es
    dinero contado contra dinero esperado: el sitio exacto donde un céntimo
    falso se convierte en una discusión con el cajero.
    """
    if value is None:
        return Decimal(0)
    entrada = value if isinstance(value, Decimal) else Decimal(str(value))
    return entrada.quantize(Decimal(1).scaleb(-_MONEY_PLACES))


def _require_cashbox(db: Session, company_id: str, cashbox_id: str) -> Cashbox:
    c = db.get(Cashbox, cashbox_id)
    if not c or c.company_id != company_id:
        raise NotFoundError(code="CASHBOX_NOT_FOUND", message="Caja no encontrada")
    return c


def _require_account(db: Session, company_id: str, account_id: str) -> FinancialAccount:
    a = db.get(FinancialAccount, account_id)
    if not a or a.company_id != company_id:
        raise NotFoundError(code="ACCOUNT_NOT_FOUND", message="Cuenta bancaria no encontrada")
    return a


def _require_session(db: Session, company_id: str, session_id: str) -> CashSession:
    s = db.get(CashSession, session_id)
    if not s or s.company_id != company_id:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    return s


def _require_currency(db: Session, company_id: str, currency_id: str) -> Currency:
    c = db.get(Currency, currency_id)
    if not c or c.company_id != company_id:
        raise NotFoundError(code="CURRENCY_NOT_FOUND", message="Moneda no encontrada")
    return c


def active_fx_policy(db: Session, company_id: str, on_date: date | None = None) -> TreasuryFxPolicy | None:
    """La política cambiaria vigente de la empresa en una fecha.

    Vigente es una sola: el índice único parcial impide dos activas con el mismo
    código, porque dos políticas a la vez darían dos respuestas a la misma
    pregunta.
    """
    dia = on_date or date.today()
    return db.execute(
        select(TreasuryFxPolicy).where(
            TreasuryFxPolicy.company_id == company_id,
            TreasuryFxPolicy.status == "ACTIVE",
            TreasuryFxPolicy.effective_from <= dia,
            (TreasuryFxPolicy.effective_to.is_(None)) | (TreasuryFxPolicy.effective_to >= dia),
        ).order_by(TreasuryFxPolicy.version.desc())).scalars().first()


def _rate_snapshot(db: Session, company_id: str, currency: str) -> float | None:
    """Compatibilidad: la tasa registrada, o `None` si no hay ninguna.

    **Devolvía `1.0`** cuando no encontraba la moneda o no había tasa cargada.
    Un pago en divisa se registraba al cambio uno y nadie se enteraba. Ahora
    devuelve `None`: no saber la tasa es un hecho, no el número uno.
    """
    if currency in ("VED", "VES"):
        return 1.0
    cur = db.execute(select(Currency).where(
        Currency.company_id == company_id, Currency.code == currency)).scalars().first()
    if not cur:
        return None
    row = db.execute(
        select(ExchangeRate)
        .where(ExchangeRate.company_id == company_id, ExchangeRate.currency_id == str(cur.id))
        .order_by(ExchangeRate.rate_date.desc())
        .limit(1)
    ).scalars().first()
    return row.rate if row else None


def capture_rate_snapshot(db: Session, *, company_id: str, source_currency: str,
                          target_currency: str, on_date: date | None = None,
                          manual_rate: Decimal | float | None = None,
                          manual_reason: str | None = None,
                          actor: str | None = None) -> TreasuryRateSnapshot:
    """Congela la tasa que gobierna una operación, con su procedencia entera.

    Si no hay tasa registrada y la política no admite tasa manual, **falla**. No
    hay tasa por defecto: inventar un uno es peor que negarse, porque el uno
    parece un número correcto.
    """
    company_id = _company(company_id, obj="tasa")
    dia = on_date or date.today()
    politica = active_fx_policy(db, company_id, dia)

    if manual_rate is not None:
        if politica is None or not politica.allow_manual_rate:
            raise ConflictError(
                code="MANUAL_RATE_NOT_ALLOWED",
                message="La política vigente no admite tasa manual.")
        if not (manual_reason or "").strip():
            raise KontrolError(code="MANUAL_RATE_REASON_REQUIRED",
                               message="Una tasa manual exige motivo.", status_code=422)
        tasa = Decimal(str(manual_rate))
        if tasa <= 0:
            raise KontrolError(code="INVALID_RATE", message="La tasa debe ser positiva.",
                               status_code=422)
        snap = TreasuryRateSnapshot(
            company_id=company_id, source_currency=source_currency,
            target_currency=target_currency, rate=tasa,
            rate_source=politica.rate_source, rate_type=politica.rate_type, rate_date=dia,
            policy_id=str(politica.id), policy_version=politica.version,
            origin="MANUAL", manual_reason=manual_reason, created_by=actor)
        db.add(snap)
        db.flush()
        return snap

    resuelta = resolucion_de_tasa(db, company_id, source_currency, target_currency, dia)
    if resuelta is None:
        raise ConflictError(
            code="RATE_NOT_AVAILABLE",
            message="No hay tasa registrada para esa conversión en esa fecha.",
            details={"source_currency": source_currency, "target_currency": target_currency,
                     "rate_date": dia.isoformat()})
    fila = (db.get(ExchangeRate, resuelta.observation_id)
            if resuelta.observation_id and not resuelta.derived else None)
    snap = TreasuryRateSnapshot(
        company_id=company_id, source_currency=source_currency,
        target_currency=target_currency, rate=resuelta.rate,
        rate_source=resuelta.source_code or (politica.rate_source if politica else None),
        rate_type=resuelta.rate_type or (politica.rate_type if politica else None),
        rate_date=dia,
        exchange_rate_id=str(fila.id) if fila else None,
        policy_id=str(politica.id) if politica else None,
        policy_version=politica.version if politica else None,
        origin="REGISTERED",
        # Si la tasa se derivó, la instantánea lo dice y de qué filas salió.
        derivation=resuelta.derived,
        derived_from=",".join(resuelta.derived_from) or None,
        created_by=actor)
    db.add(snap)
    db.flush()
    return snap


def _buscar_tasa(db: Session, company_id: str, origen: str, destino: str,
                 dia: date) -> tuple[Decimal, ExchangeRate | None] | None:
    """La tasa que convierte `origen` en `destino` ese día.

    Delega en la Spec 013, que es la dueña de la resolución. Este envoltorio
    existe porque la 038 necesita la fila para su instantánea y porque, aquí, no
    haber tasa es una condición esperada —la política decide si se admite tasa
    manual—, no un fallo.

    Lo que antes hacía esta función y ya no: escribir `("VED", "VES")` dentro
    del dominio, invertir una cotización sin decirlo y cruzar dos sin permiso.
    Las tres eran decisiones económicas tomadas por el código.
    """
    try:
        resuelta = rates.resolve_rate(db, company_id=company_id, base_code=origen,
                                      quote_code=destino, effective_at=dia)
    except KontrolError:
        return None
    fila = (db.get(ExchangeRate, resuelta.observation_id)
            if resuelta.observation_id and not resuelta.derived else None)
    return (resuelta.rate, fila)


def resolucion_de_tasa(db: Session, company_id: str, origen: str, destino: str,
                       dia: date) -> rates.RateResolution | None:
    """La resolución entera, para que la instantánea guarde su procedencia."""
    try:
        return rates.resolve_rate(db, company_id=company_id, base_code=origen,
                                  quote_code=destino, effective_at=dia)
    except KontrolError:
        return None


def _session_expected(db: Session, session: CashSession) -> float:
    ins = db.execute(select(CashSessionMovement).where(
        CashSessionMovement.session_id == session.id, CashSessionMovement.movement_type == "IN")).scalars().all()
    outs = db.execute(select(CashSessionMovement).where(
        CashSessionMovement.session_id == session.id, CashSessionMovement.movement_type == "OUT")).scalars().all()
    return (_money(session.opened_amount) + sum((_money(m.amount) for m in ins), Decimal(0))
            - sum((_money(m.amount) for m in outs), Decimal(0)))


# --------------------------------------------------------------------------- #
# Maestros financieros
# --------------------------------------------------------------------------- #
def create_bank(db: Session, *, company_id: str, code: str, name: str, swift: str | None = None,
                country: str | None = None, actor: str | None = None) -> FinancialBank:
    company_id = _company(company_id, obj="banco")
    b = FinancialBank(company_id=company_id, code=code, name=name, swift=swift, country=country,
                      status="ACTIVE", created_by=actor)
    db.add(b)
    db.flush()
    return b


def create_account(db: Session, *, company_id: str, bank_id: str, code: str, name: str, currency: str = "VED",
                   iban: str | None = None, reference: str | None = None, actor: str | None = None) -> FinancialAccount:
    company_id = _company(company_id, obj="cuenta")
    bank = db.get(FinancialBank, bank_id)
    if not bank or bank.company_id != company_id:
        raise NotFoundError(code="BANK_NOT_FOUND", message="Banco no encontrado")
    a = FinancialAccount(company_id=company_id, bank_id=bank_id, code=code, name=name, currency=currency,
                         iban=iban, reference=reference, status="ACTIVE", created_by=actor)
    db.add(a)
    db.flush()
    return a


def create_cashbox(db: Session, *, company_id: str, code: str, name: str, currency: str = "VED",
                   warehouse_id: str | None = None, policies: str | None = None, actor: str | None = None) -> Cashbox:
    company_id = _company(company_id, obj="caja")
    if warehouse_id:
        from app.modules.organization.models import Warehouse
        from app.modules.organization.service import warehouse_belongs_to

        warehouse = db.get(Warehouse, warehouse_id)
        if not warehouse or not warehouse_belongs_to(company_id, warehouse):
            raise NotFoundError(code="WAREHOUSE_NOT_FOUND", message="Almacén no encontrado")
    c = Cashbox(company_id=company_id, code=code, name=name, currency=currency, warehouse_id=warehouse_id,
                policies=policies, status="ACTIVE", created_by=actor)
    db.add(c)
    db.flush()
    return c


def create_payment_method(db: Session, *, company_id: str, code: str, name: str, kind: str = "OTHER",
                          actor: str | None = None) -> PaymentMethod:
    company_id = _company(company_id, obj="método")
    m = PaymentMethod(company_id=company_id, code=code, name=name, kind=kind, status="ACTIVE", created_by=actor)
    db.add(m)
    db.flush()
    return m


def create_instrument(db: Session, *, company_id: str, method_id: str, code: str, name: str,
                      cashbox_id: str | None = None, account_id: str | None = None,
                      actor: str | None = None) -> TreasuryInstrument:
    company_id = _company(company_id, obj="instrumento")
    method = db.get(PaymentMethod, method_id)
    if not method or method.company_id != company_id:
        raise NotFoundError(code="PAYMENT_METHOD_NOT_FOUND", message="Método de pago no encontrado")
    i = TreasuryInstrument(company_id=company_id, method_id=method_id, code=code, name=name,
                           cashbox_id=cashbox_id, account_id=account_id, status="ACTIVE", created_by=actor)
    db.add(i)
    db.flush()
    return i


def create_currency(db: Session, *, company_id: str, code: str, name: str | None = None, symbol: str | None = None,
                    decimal_places: int = 2, actor: str | None = None) -> Currency:
    company_id = _company(company_id, obj="moneda")
    c = Currency(company_id=company_id, code=code, name=name, symbol=symbol, decimal_places=decimal_places,
                 status="ACTIVE", created_by=actor)
    db.add(c)
    db.flush()
    return c


def set_exchange_rate(db: Session, *, company_id: str, currency_id: str, rate_date: date,
                      rate: Decimal | float, source: str | None = None,
                      actor: str | None = None) -> ExchangeRate:
    """Registra una tasa por el camino antiguo, con el par ya explícito.

    El camino corto —«la tasa del dólar»— sigue existiendo, pero ya no deja el
    par a la imaginación: la moneda de la fila es la base y la cotizada es la
    funcional **que la empresa declara**. Lo escribe la Spec 013, que es su
    dueña; esto es solo la puerta de compatibilidad.
    """
    company_id = _company(company_id, obj="tasa")
    moneda = _require_currency(db, company_id, currency_id)
    funcional = rates.asegurar_moneda_funcional(db, company_id, actor).code
    if moneda.code == funcional:
        raise KontrolError(
            code="INVALID_PAIR",
            message="La moneda funcional no cotiza contra sí misma.", status_code=422)
    # El texto libre que traía esta llamada —«BCV», «banco»— siempre quiso
    # nombrar una fuente. Se convierte en una del maestro la primera vez que se
    # usa, en vez de acabar en el cajón de lo heredado: así el histórico gana
    # procedencia de verdad sin que nadie tenga que migrar nada a mano.
    fuente = rates.fuente_por_texto(db, company_id, source, actor)
    return rates.register_rate(
        db, company_id=company_id, base_code=moneda.code, quote_code=funcional,
        rate=rate, effective_at=rate_date, source_id=str(fuente.id),
        source_reference=source, actor=actor)


# --------------------------------------------------------------------------- #
# Cajas — sesiones
# --------------------------------------------------------------------------- #
def open_session(db: Session, *, company_id: str, cashbox_id: str, opened_amount: float = 0.0,
                 actor: str | None = None) -> CashSession:
    company_id = _company(company_id, obj="sesión de caja")
    _require_cashbox(db, company_id, cashbox_id)
    s = CashSession(company_id=company_id, cashbox_id=cashbox_id, opened_by=actor,
                    opened_at=date.today(), opened_amount=opened_amount, status="OPEN", created_by=actor)
    db.add(s)
    db.flush()
    return s


def add_session_movement(db: Session, *, session_id: str, movement_type: str, amount: float,
                         instrument_id: str | None = None, payment_id: str | None = None,
                         source: str = "PAYMENT", reference: str | None = None,
                         note: str | None = None) -> CashSessionMovement:
    session = db.get(CashSession, session_id)
    if not session:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    if session.status not in ("OPEN", "ARCHED"):
        raise ConflictError(code="SESSION_NOT_ACTIVE", message="La sesión de caja no admite movimientos.")
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto del movimiento debe ser positivo", status_code=422)
    if movement_type not in ("IN", "OUT", "ADJUST"):
        raise KontrolError(code="INVALID_MOVEMENT_TYPE", message="Tipo de movimiento inválido", status_code=422)
    m = CashSessionMovement(session_id=str(session.id), movement_type=movement_type, amount=amount,
                            instrument_id=instrument_id, payment_id=payment_id, source=source,
                            reference=reference, note=note)
    db.add(m)
    db.flush()
    return m


def arqueo_session(db: Session, *, session_id: str, counted_amount: float,
                   notes: str | None = None, actor: str | None = None) -> CashSession:
    session = db.get(CashSession, session_id)
    if not session:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    _assert_transition(session.status, "ARCHED", CASH_SESSION_TRANSITIONS, "la sesión de caja")
    expected = _session_expected(db, session)
    session.counted_amount = counted_amount
    session.expected_amount = expected
    session.difference = _money(counted_amount) - _money(expected)
    session.status = "ARCHED"
    if notes:
        session.audit = f'{{"arqueo_notes": {notes!r}}}'
    session.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="CASH_SESSION_ARCHED", entity_type="CashSession", entity_id=str(session.id),
           company_id=session.company_id, actor=actor,
           after={"expected": float(session.expected_amount or 0), "counted": float(session.counted_amount or 0),
                  "difference": float(session.difference or 0)})
    return session


def pre_close_session(db: Session, *, session_id: str, actor: str | None = None) -> CashSession:
    session = db.get(CashSession, session_id)
    if not session:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    _assert_transition(session.status, "PRE_CLOSED", CASH_SESSION_TRANSITIONS, "la sesión de caja")
    session.status = "PRE_CLOSED"
    session.updated_at = datetime.now(UTC)
    db.flush()
    return session


def reject_session(db: Session, *, session_id: str, actor: str | None = None) -> CashSession:
    session = db.get(CashSession, session_id)
    if not session:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    _assert_transition(session.status, "REJECTED", CASH_SESSION_TRANSITIONS, "la sesión de caja")
    session.status = "REJECTED"
    session.updated_at = datetime.now(UTC)
    db.flush()
    return session


def close_session(db: Session, *, session_id: str, difference_approved: bool = False,
                  approval_note: str | None = None, actor: str | None = None) -> CashSession:
    """Cierra la caja; rechaza si hay diferencia sin aprobación (FR-006-003)."""
    session = db.get(CashSession, session_id)
    if not session:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    _assert_transition(session.status, "CLOSED", CASH_SESSION_TRANSITIONS, "la sesión de caja")
    diff = session.difference or 0.0
    if abs(diff) > 1e-6 and not difference_approved:
        raise ConflictError(code="DIFFERENCE_NOT_APPROVED",
                            message="La caja tiene diferencia y debe aprobarse/justificarse para cerrarla.")
    session.status = "CLOSED"
    session.closed_at = date.today()
    session.approval_note = approval_note
    session.audit = f'{{"difference_approved": {str(difference_approved).lower()}, "closed_by": {actor!r}}}'
    session.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="CASH_SESSION_CLOSED", entity_type="CashSession", entity_id=str(session.id),
           company_id=session.company_id, actor=actor,
           after={"difference": float(session.difference or 0), "approved": difference_approved})
    return session


def session_dict(db: Session, session: CashSession) -> dict:
    movements = db.execute(select(CashSessionMovement).where(
        CashSessionMovement.session_id == session.id).order_by(CashSessionMovement.created_at)).scalars().all()
    expected = _session_expected(db, session)
    return {"id": session.id, "cashbox_id": session.cashbox_id, "opened_by": session.opened_by,
            "opened_at": session.opened_at.isoformat() if session.opened_at else None,
            "closed_at": session.closed_at.isoformat() if session.closed_at else None,
            "opened_amount": session.opened_amount, "counted_amount": session.counted_amount,
            "expected_amount": expected, "difference": session.difference, "status": session.status,
            "approval_note": session.approval_note,
            "allowed_actions": session_allowed_actions(session),
            "movements": [{"id": m.id, "movement_type": m.movement_type, "payment_id": m.payment_id,
                           "amount": m.amount, "instrument_id": m.instrument_id, "reference": m.reference}
                          for m in movements]}


def session_allowed_actions(session: CashSession) -> dict[str, bool]:
    s = session.status
    return {"view": True, "arqueo": s == "OPEN", "pre_close": s == "ARCHED", "close": s == "PRE_CLOSED",
            "reject": s == "PRE_CLOSED", "movement": s in ("OPEN", "ARCHED")}


# --------------------------------------------------------------------------- #
# Bancos — transacciones, ingresos/egresos, transferencias
# --------------------------------------------------------------------------- #
def create_bank_transaction(db: Session, *, company_id: str, account_id: str, direction: str, amount: Decimal,
                            currency: str = "VED", txn_date: date | None = None, value_date: date | None = None,
                            reference: str | None = None, source: str = "ADJUSTMENT", payment_id: str | None = None,
                            commission: Decimal | None = None, actor: str | None = None) -> BankTransaction:
    company_id = _company(company_id, obj="transacción bancaria")
    _require_account(db, company_id, account_id)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto debe ser positivo", status_code=422)
    bt = BankTransaction(company_id=company_id, account_id=account_id, txn_date=txn_date or date.today(),
                         value_date=value_date or txn_date or date.today(), direction=direction, amount=amount,
                         currency=currency, reference=reference, source=source, payment_id=payment_id,
                         commission=commission, rate_snapshot=_rate_snapshot(db, company_id, currency),
                         status="PENDING", created_by=actor)
    db.add(bt)
    db.flush()
    return bt


def _find_execution(db: Session, payment_id: str) -> dict | None:
    """Busca una ejecución previa (caja o banco) para idempotencia."""
    bt = db.execute(select(BankTransaction).where(BankTransaction.payment_id == payment_id)).scalars().first()
    if bt:
        return {"kind": "bank", "id": str(bt.id)}
    mv = db.execute(select(CashSessionMovement).where(CashSessionMovement.payment_id == payment_id)).scalars().first()
    if mv:
        return {"kind": "cash", "id": str(mv.id)}
    return None


def execute_payment(db: Session, *, company_id: str, payment_id: str, target_type: str, target_id: str,
                    actor: str | None = None, idempotency_key: str | None = None) -> dict:
    """Ejecuta un egreso de 004 (Payment OUT) contra caja o banco (FR-006-020/022).

    Idempotente: reintentar la misma ejecución no duplica transacciones.
    """
    company_id = _company(company_id, obj="egreso")
    payment = db.get(Payment, payment_id)
    if not payment or payment.company_id != company_id or payment.direction != "OUT":
        raise NotFoundError(code="PAYMENT_NOT_FOUND", message="Pago de egreso no encontrado")
    if idempotency_key:
        existing = _find_execution(db, str(payment.id))
        if existing:
            return {"id": existing["id"], "kind": existing["kind"], "idempotent": True,
                    "amount": payment.amount, "currency": payment.currency}
    if payment.status != "APPROVED":
        raise ConflictError(code="PAYMENT_NOT_APPROVED", message="Solo se ejecutan egresos aprobados.")

    if target_type == "CASHBOX":
        _require_cashbox(db, company_id, target_id)
        session = db.execute(select(CashSession).where(
            CashSession.company_id == company_id, CashSession.cashbox_id == target_id,
            CashSession.status.in_(["OPEN", "ARCHED"])).order_by(CashSession.opened_at.desc())).scalars().first()
        if not session:
            raise ConflictError(code="NO_OPEN_SESSION", message="La caja no tiene una sesión abierta para ejecutar el egreso.")
        mv = add_session_movement(db, session_id=str(session.id), movement_type="OUT", amount=payment.amount,
                                  payment_id=str(payment.id), source="PAYMENT", reference=f"EGRESO-{str(payment.id)[:8]}")
        result = {"id": str(mv.id), "kind": "cash", "idempotent": False, "amount": payment.amount,
                  "currency": payment.currency}
    elif target_type == "ACCOUNT":
        _require_account(db, company_id, target_id)
        bt = create_bank_transaction(db, company_id=company_id, account_id=target_id, direction="OUT",
                                     amount=payment.amount, currency=payment.currency, source="PAYMENT",
                                     payment_id=str(payment.id), reference=f"EGRESO-{str(payment.id)[:8]}", actor=actor)
        result = {"id": str(bt.id), "kind": "bank", "idempotent": False, "amount": payment.amount,
                  "currency": payment.currency}
    else:
        raise KontrolError(code="INVALID_TARGET", message="Destino inválido (CASHBOX/ACCOUNT)", status_code=422)

    ap_service.transition_payment(db, payment=payment, target="POSTED", actor=actor)
    db.flush()
    return result


def execute_collection(db: Session, *, company_id: str, payment_id: str, target_type: str, target_id: str,
                       actor: str | None = None, idempotency_key: str | None = None) -> dict:
    """Ejecuta un ingreso de 005 (Payment IN) contra caja o banco (FR-006-020/022)."""
    company_id = _company(company_id, obj="ingreso")
    payment = db.get(Payment, payment_id)
    if not payment or payment.company_id != company_id or payment.direction != "IN":
        raise NotFoundError(code="COLLECTION_NOT_FOUND", message="Cobro de ingreso no encontrado")
    if idempotency_key:
        existing = _find_execution(db, str(payment.id))
        if existing:
            return {"id": existing["id"], "kind": existing["kind"], "idempotent": True,
                    "amount": payment.amount, "currency": payment.currency}
    if payment.status != "APPROVED":
        raise ConflictError(code="COLLECTION_NOT_APPROVED", message="Solo se ejecutan ingresos aprobados.")

    if target_type == "CASHBOX":
        _require_cashbox(db, company_id, target_id)
        session = db.execute(select(CashSession).where(
            CashSession.company_id == company_id, CashSession.cashbox_id == target_id,
            CashSession.status.in_(["OPEN", "ARCHED"])).order_by(CashSession.opened_at.desc())).scalars().first()
        if not session:
            raise ConflictError(code="NO_OPEN_SESSION", message="La caja no tiene una sesión abierta para ejecutar el ingreso.")
        mv = add_session_movement(db, session_id=str(session.id), movement_type="IN", amount=payment.amount,
                                  payment_id=str(payment.id), source="COLLECTION", reference=f"INGRESO-{str(payment.id)[:8]}")
        result = {"id": str(mv.id), "kind": "cash", "idempotent": False, "amount": payment.amount,
                  "currency": payment.currency}
    elif target_type == "ACCOUNT":
        _require_account(db, company_id, target_id)
        bt = create_bank_transaction(db, company_id=company_id, account_id=target_id, direction="IN",
                                     amount=payment.amount, currency=payment.currency, source="COLLECTION",
                                     payment_id=str(payment.id), reference=f"INGRESO-{str(payment.id)[:8]}", actor=actor)
        result = {"id": str(bt.id), "kind": "bank", "idempotent": False, "amount": payment.amount,
                  "currency": payment.currency}
    else:
        raise KontrolError(code="INVALID_TARGET", message="Destino inválido (CASHBOX/ACCOUNT)", status_code=422)

    ap_service.transition_payment(db, payment=payment, target="POSTED", actor=actor)
    db.flush()
    return result


def create_transfer(db: Session, *, company_id: str, amount: float, currency: str = "VED",
                    from_cashbox_id: str | None = None, from_account_id: str | None = None,
                    to_cashbox_id: str | None = None, to_account_id: str | None = None,
                    value_date: date | None = None, reference: str | None = None,
                    actor: str | None = None) -> TreasuryTransfer:
    """Transferencia entre cajas/cuentas y depósitos (FR-006-023).

    Registra la transferencia y las transacciones de banco/movimientos de caja
    de origen y destino. Requiere sesión abierta cuando participa una caja.
    """
    company_id = _company(company_id, obj="transferencia")
    if not (from_cashbox_id or from_account_id) or not (to_cashbox_id or to_account_id):
        raise KontrolError(code="INVALID_TRANSFER", message="Se requieren origen y destino válidos", status_code=422)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto debe ser positivo", status_code=422)
    t = TreasuryTransfer(company_id=company_id, from_cashbox_id=from_cashbox_id, from_account_id=from_account_id,
                         to_cashbox_id=to_cashbox_id, to_account_id=to_account_id, amount=amount,
                         currency=currency, value_date=value_date or date.today(), reference=reference,
                         status="PENDING", created_by=actor)
    db.add(t)
    db.flush()

    ref = reference or f"TRANSFER-{str(t.id)[:8]}"
    if from_account_id:
        create_bank_transaction(db, company_id=company_id, account_id=from_account_id, direction="OUT",
                                amount=amount, currency=currency, value_date=value_date, reference=ref,
                                source="TRANSFER", actor=actor)
    if to_account_id:
        create_bank_transaction(db, company_id=company_id, account_id=to_account_id, direction="IN",
                                amount=amount, currency=currency, value_date=value_date, reference=ref,
                                source="TRANSFER", actor=actor)
    if from_cashbox_id:
        _require_cashbox(db, company_id, from_cashbox_id)
        session = db.execute(select(CashSession).where(
            CashSession.company_id == company_id, CashSession.cashbox_id == from_cashbox_id,
            CashSession.status.in_(["OPEN", "ARCHED"])).order_by(CashSession.opened_at.desc())).scalars().first()
        if not session:
            raise ConflictError(code="NO_OPEN_SESSION", message="La caja de origen no tiene sesión abierta.")
        add_session_movement(db, session_id=str(session.id), movement_type="OUT", amount=amount,
                             source="TRANSFER", reference=ref)
    if to_cashbox_id:
        _require_cashbox(db, company_id, to_cashbox_id)
        session = db.execute(select(CashSession).where(
            CashSession.company_id == company_id, CashSession.cashbox_id == to_cashbox_id,
            CashSession.status.in_(["OPEN", "ARCHED"])).order_by(CashSession.opened_at.desc())).scalars().first()
        if not session:
            raise ConflictError(code="NO_OPEN_SESSION", message="La caja de destino no tiene sesión abierta.")
        add_session_movement(db, session_id=str(session.id), movement_type="IN", amount=amount,
                             source="TRANSFER", reference=ref)
    t.status = "POSTED"
    db.flush()
    return t


def bank_transaction_dict(bt: BankTransaction) -> dict:
    # Spec 038 · FLOAT-038-A: el importe sale como texto exacto, igual que la
    # conversión y el reembolso. Devolver el `Decimal` crudo lo dejaba en manos de
    # `jsonable_encoder`, que lo pasa por `float`.
    return {"id": bt.id, "account_id": bt.account_id, "txn_date": bt.txn_date.isoformat() if bt.txn_date else None,
            "value_date": bt.value_date.isoformat() if bt.value_date else None, "direction": bt.direction,
            "amount": str(_money(bt.amount)), "currency": bt.currency, "reference": bt.reference, "source": bt.source,
            "payment_id": bt.payment_id,
            "commission": None if bt.commission is None else str(_money(bt.commission)), "status": bt.status}


def transfer_dict(t: TreasuryTransfer) -> dict:
    return {"id": t.id, "from_cashbox_id": t.from_cashbox_id, "from_account_id": t.from_account_id,
            "to_cashbox_id": t.to_cashbox_id, "to_account_id": t.to_account_id, "amount": t.amount,
            "currency": t.currency, "value_date": t.value_date.isoformat() if t.value_date else None,
            "reference": t.reference, "status": t.status}


# --------------------------------------------------------------------------- #
# Conciliación (FR-006-030/031)
# --------------------------------------------------------------------------- #
def create_reconciliation(db: Session, *, company_id: str, account_id: str, statement_date: date | None = None,
                          statement_ref: str | None = None, opening_balance: float | None = None,
                          closing_balance: float | None = None, actor: str | None = None) -> Reconciliation:
    company_id = _company(company_id, obj="conciliación")
    _require_account(db, company_id, account_id)
    r = Reconciliation(company_id=company_id, account_id=account_id, statement_date=statement_date,
                       statement_ref=statement_ref, opening_balance=opening_balance,
                       closing_balance=closing_balance, status="DRAFT", created_by=actor)
    db.add(r)
    db.flush()
    return r


def add_reconciliation_line(db: Session, *, reconciliation_id: str, bank_transaction_id: str) -> ReconciliationLine:
    rec = db.get(Reconciliation, reconciliation_id)
    if not rec:
        raise NotFoundError(code="RECONCILIATION_NOT_FOUND", message="Conciliación no encontrada")
    if rec.status not in ("DRAFT", "IN_PROGRESS"):
        raise ConflictError(code="RECONCILIATION_LOCKED", message="La conciliación no admite nuevas líneas.")
    bt = db.get(BankTransaction, bank_transaction_id)
    if not bt:
        raise NotFoundError(code="BANK_TRANSACTION_NOT_FOUND", message="Transacción bancaria no encontrada")
    line = ReconciliationLine(reconciliation_id=str(rec.id), bank_transaction_id=str(bt.id), status="UNMATCHED")
    db.add(line)
    db.flush()
    return line


def propose_matches(db: Session, *, reconciliation_id: str) -> list[ReconciliationLine]:
    """Propone emparejamientos por reglas (match score) — FR-006-030.

    Reglas: referencia+importe (1.0), importe+fecha valor (0.8), importe (0.6).
    Los movimientos del sistema candidatos son pagos/cobros de 004/005.
    """
    rec = db.get(Reconciliation, reconciliation_id)
    if not rec:
        raise NotFoundError(code="RECONCILIATION_NOT_FOUND", message="Conciliación no encontrada")
    lines = db.execute(select(ReconciliationLine).where(
        ReconciliationLine.reconciliation_id == reconciliation_id,
        ReconciliationLine.status == "UNMATCHED")).scalars().all()
    matched = []
    for line in lines:
        bt = db.get(BankTransaction, line.bank_transaction_id) if line.bank_transaction_id else None
        if not bt:
            continue
        candidates = db.execute(select(Payment).where(
            Payment.company_id == rec.company_id, Payment.amount == bt.amount)).scalars().all()
        best = None
        best_score = 0.0
        for p in candidates:
            if p.status not in ("APPROVED", "POSTED"):
                continue
            score = 0.6
            if bt.reference and p.id and bt.reference == f"{'EGRESO' if p.direction == 'OUT' else 'INGRESO'}-{str(p.id)[:8]}":
                score = 1.0
            elif p.date and bt.value_date and p.date == bt.value_date:
                score = 0.8
            if score > best_score:
                best, best_score = p, score
        if best and best_score >= 0.8:
            line.system_movement_id = str(best.id)
            line.system_movement_type = "PAYMENT"
            line.match_score = best_score
            line.matched_by = "RULE"
            line.status = "MATCHED"
            matched.append(line)
    db.flush()
    return matched


def resolve_line(db: Session, *, company_id: str, line_id: str, resolution_type: str,
                 system_movement_id: str | None = None,
                 notes: str | None = None, actor: str | None = None) -> ReconciliationLine:
    """Resolución manual auditada de una línea de conciliación — FR-006-030.

    `resolution_type`: MATCHED / DIFFERENCE / COMMISSION / FX.
    La resolución queda auditada sin alterar el IVA original (FR-006-032).
    """
    line = db.get(ReconciliationLine, line_id)
    if not line:
        raise NotFoundError(code="RECONCILIATION_LINE_NOT_FOUND", message="Línea de conciliación no encontrada")
    rec = db.get(Reconciliation, line.reconciliation_id)
    # La línea no lleva empresa propia: la alcanza por su conciliación, que es
    # exactamente la ruta que declara `ReconciliationLine.__scope_authority__`.
    if rec is None or rec.company_id != company_id:
        raise NotFoundError(code="RECONCILIATION_LINE_NOT_FOUND", message="Línea de conciliación no encontrada")
    if rec.status not in ("IN_PROGRESS", "REVIEW"):
        raise ConflictError(code="RECONCILIATION_LOCKED", message="La conciliación no admite resoluciones.")
    if resolution_type not in ("MATCHED", "DIFFERENCE", "COMMISSION", "FX"):
        raise KontrolError(code="INVALID_RESOLUTION", message="Tipo de resolución inválido", status_code=422)
    if system_movement_id:
        line.system_movement_id = system_movement_id
        line.system_movement_type = "PAYMENT"
    line.matched_by = "MANUAL"
    line.match_score = 1.0
    line.status = "RESOLVED"
    line.resolution = f'{{"type": {resolution_type!r}, "resolved_by": {actor!r}}}'
    line.notes = notes
    db.flush()
    return line


def transition_reconciliation(db: Session, *, reconciliation_id: str, target: str,
                              actor: str | None = None) -> Reconciliation:
    rec = db.get(Reconciliation, reconciliation_id)
    if not rec:
        raise NotFoundError(code="RECONCILIATION_NOT_FOUND", message="Conciliación no encontrada")
    _assert_transition(rec.status, target, RECONCILIATION_TRANSITIONS, "la conciliación")
    rec.status = target
    rec.updated_at = datetime.now(UTC)
    if target == "APPROVED":
        rec.approved_by = actor
        rec.approved_at = date.today()
    db.flush()
    _audit(db, action="RECONCILIATION_TRANSITIONED", entity_type="Reconciliation", entity_id=str(rec.id),
           company_id=rec.company_id, actor=actor, after={"target": rec.status})
    return rec


def reconciliation_dict(db: Session, rec: Reconciliation) -> dict:
    lines = db.execute(select(ReconciliationLine).where(
        ReconciliationLine.reconciliation_id == rec.id).order_by(ReconciliationLine.created_at)).scalars().all()
    return {"id": rec.id, "account_id": rec.account_id,
            "statement_date": rec.statement_date.isoformat() if rec.statement_date else None,
            "statement_ref": rec.statement_ref, "opening_balance": rec.opening_balance,
            "closing_balance": rec.closing_balance, "status": rec.status, "approved_by": rec.approved_by,
            "approved_at": rec.approved_at.isoformat() if rec.approved_at else None,
            "allowed_actions": reconciliation_allowed_actions(rec),
            "lines": [{"id": line.id, "bank_transaction_id": line.bank_transaction_id,
                       "system_movement_id": line.system_movement_id, "system_movement_type": line.system_movement_type,
                       "match_score": line.match_score, "matched_by": line.matched_by, "status": line.status,
                       "resolution": line.resolution, "notes": line.notes} for line in lines]}


def reconciliation_allowed_actions(rec: Reconciliation) -> dict[str, bool]:
    s = rec.status
    return {"view": True, "in_progress": s == "DRAFT", "review": s == "IN_PROGRESS",
            "approve": s == "REVIEW", "reject": s == "REVIEW", "match": s in ("DRAFT", "IN_PROGRESS")}


# --------------------------------------------------------------------------- #
# IGTF por regla y evento (FR-006-040/041)
# --------------------------------------------------------------------------- #
def create_fiscal_rule(db: Session, *, company_id: str, rule_code: str, name: str | None = None,
                       rule_type: str = "IGTF", version: str = "1.0", effective_from: date | None = None,
                       effective_to: date | None = None, params: str | None = None,
                       actor: str | None = None) -> FiscalRule:
    company_id = _company(company_id, obj="regla fiscal")
    r = FiscalRule(company_id=company_id, rule_code=rule_code, name=name, rule_type=rule_type, version=version,
                   effective_from=effective_from, effective_to=effective_to, params=params,
                   status="ACTIVE", created_by=actor)
    db.add(r)
    db.flush()
    return r


def _active_rule(db: Session, company_id: str, rule_type: str, on_date: date) -> FiscalRule | None:
    today = on_date or date.today()
    return db.execute(select(FiscalRule).where(
        FiscalRule.company_id == company_id, FiscalRule.rule_type == rule_type, FiscalRule.status == "ACTIVE",
        (FiscalRule.effective_from.is_(None)) | (FiscalRule.effective_from <= today),
        (FiscalRule.effective_to.is_(None)) | (FiscalRule.effective_to >= today),
    ).order_by(FiscalRule.created_at.desc())).scalars().first()


def evaluate_igft(db: Session, *, company_id: str, event_type: str, source_document: str | None = None,
                  amount: float, currency: str = "VED", on_date: date | None = None) -> IgftEvent:
    """Evalúa IGTF por regla y evento; no confundir con IVA adicional (FR-006-040)."""
    company_id = _company(company_id, obj="evento IGTF")
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto debe ser positivo", status_code=422)
    rule = _active_rule(db, company_id, "IGTF", on_date or date.today())
    if rule is None:
        raise NotFoundError(code="NO_IGTF_RULE", message="No hay una regla IGTF vigente.")
    import json

    params = json.loads(rule.params or "{}")
    rate = float(params.get("rate", 0.0))
    snapshot = _rate_snapshot(db, company_id, currency)
    igft_amount = round(amount * rate * snapshot, 2) if currency not in ("VED", "VES") else round(amount * rate, 2)
    event = IgftEvent(company_id=company_id, event_type=event_type, source_document=source_document, amount=amount,
                      currency=currency, rate_snapshot=snapshot, igft_amount=igft_amount, rule_id=str(rule.id),
                      evaluated_at=on_date or date.today(), status="EVALUATED")
    db.add(event)
    db.flush()
    return event


def igft_event_dict(e: IgftEvent) -> dict:
    return {"id": e.id, "event_type": e.event_type, "source_document": e.source_document, "amount": e.amount,
            "currency": e.currency, "rate_snapshot": e.rate_snapshot, "igft_amount": e.igft_amount,
            "rule_id": e.rule_id, "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
            "status": e.status}


# --------------------------------------------------------------------------- #
# Spec 038 · conversión de moneda explícita
#
# «Moneda A → Moneda B no puede ocultarse dentro de una Application como simple
# cambio numérico» (`OWNER-DECISION-038-02`, regla 12). Por eso cambiar de
# moneda es un hecho con su propia fila, su instantánea de tasa y su diferencia
# cambiaria, y no un número que aparece en el importe de otra cosa.
# --------------------------------------------------------------------------- #

def convert_currency(db: Session, *, company_id: str, source_account_id: str,
                     target_account_id: str, source_amount: Decimal | float,
                     on_date: date | None = None, manual_rate: Decimal | float | None = None,
                     manual_reason: str | None = None, idempotency_key: str | None = None,
                     actor: str | None = None) -> TreasuryFxConversion:
    """Convierte dinero de una cuenta propia a otra, en moneda distinta.

    Produce dos movimientos —salida en origen, entrada en destino— unidos por la
    conversión, y congela la tasa con su procedencia. La diferencia cambiaria,
    si la hay, es su propio hecho y **no toca ningún documento fiscal**.
    """
    company_id = _company(company_id, obj="conversión")
    if idempotency_key:
        previa = db.execute(select(TreasuryFxConversion).where(
            TreasuryFxConversion.company_id == company_id,
            TreasuryFxConversion.idempotency_key == idempotency_key)).scalars().first()
        if previa is not None:
            return previa

    origen = _require_account(db, company_id, source_account_id)
    destino = _require_account(db, company_id, target_account_id)
    if str(origen.id) == str(destino.id):
        raise KontrolError(code="SAME_ACCOUNT",
                           message="La conversión necesita dos cuentas distintas.",
                           status_code=422)
    if origen.currency == destino.currency:
        raise ConflictError(
            code="SAME_CURRENCY_CONVERSION",
            message="Las dos cuentas están en la misma moneda: eso es una transferencia.")

    dia = on_date or date.today()
    politica = active_fx_policy(db, company_id, dia)
    if politica is None or not politica.allow_cross_currency:
        raise ConflictError(
            code="CROSS_CURRENCY_NOT_ALLOWED",
            message="La política vigente no admite conversión entre monedas.")

    importe = _money(source_amount)
    if importe <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto debe ser positivo.",
                           status_code=422)
    disponible = account_balance(db, company_id=company_id, account_id=str(origen.id))
    if importe > disponible:
        raise ConflictError(
            code="INSUFFICIENT_FUNDS",
            message=f"La cuenta no tiene fondos suficientes ({disponible}).",
            details={"available": str(disponible), "requested": str(importe)})

    snap = capture_rate_snapshot(db, company_id=company_id, source_currency=origen.currency,
                                 target_currency=destino.currency, on_date=dia,
                                 manual_rate=manual_rate, manual_reason=manual_reason,
                                 actor=actor)
    convertido = _money(importe * Decimal(str(snap.rate)))

    salida = create_bank_transaction(
        db, company_id=company_id, account_id=str(origen.id), direction="OUT",
        amount=importe, currency=origen.currency, source="FX",
        reference=f"FX-OUT-{idempotency_key or ''}"[:120], actor=actor)
    entrada = create_bank_transaction(
        db, company_id=company_id, account_id=str(destino.id), direction="IN",
        amount=convertido, currency=destino.currency, source="FX",
        reference=f"FX-IN-{idempotency_key or ''}"[:120], actor=actor)
    salida.rate_snapshot_id = str(snap.id)
    entrada.rate_snapshot_id = str(snap.id)

    conv = TreasuryFxConversion(
        company_id=company_id, source_account_id=str(origen.id),
        target_account_id=str(destino.id), source_currency=origen.currency,
        target_currency=destino.currency, source_amount=importe, target_amount=convertido,
        rate_snapshot_id=str(snap.id), source_movement_id=str(salida.id),
        target_movement_id=str(entrada.id), status="SETTLED",
        idempotency_key=idempotency_key, created_by=actor)
    db.add(conv)
    db.flush()
    _audit(db, action="TREASURY_FX_CONVERTED", entity_type="TreasuryFxConversion",
           entity_id=str(conv.id), company_id=company_id, actor=actor,
           after={"source_amount": str(importe), "target_amount": str(convertido),
                  "rate": str(snap.rate), "rate_source": snap.rate_source,
                  "rate_date": snap.rate_date.isoformat(), "origin": snap.origin,
                  "policy_version": snap.policy_version})
    return conv


def account_balance(db: Session, *, company_id: str, account_id: str) -> Decimal:
    """El saldo de una cuenta, calculado desde sus movimientos.

    «Los saldos no se editan; se calculan desde movimientos y aplicaciones». No
    hay campo de saldo que mantener al día ni que pueda mentir.
    """
    company_id = _company(company_id, obj="saldo de cuenta")
    filas = db.execute(select(BankTransaction).where(
        BankTransaction.company_id == company_id,
        BankTransaction.account_id == str(account_id),
        BankTransaction.status != "CANCELLED")).scalars().all()
    saldo = Decimal(0)
    for m in filas:
        saldo += _money(m.amount) if m.direction == "IN" else -_money(m.amount)
    return saldo


def cash_position(db: Session, *, company_id: str) -> dict:
    """La posición de caja por cuenta y por moneda.

    Es una **lectura**. Mostrar un equivalente no convierte dinero: por eso no
    agrega monedas distintas en un solo número, que exigiría una conversión que
    nadie ha hecho.
    """
    company_id = _company(company_id, obj="posición de caja")
    cuentas = db.execute(select(FinancialAccount).where(
        FinancialAccount.company_id == company_id)).scalars().all()
    detalle, por_moneda = [], {}
    for c in cuentas:
        saldo = account_balance(db, company_id=company_id, account_id=str(c.id))
        detalle.append({"account_id": str(c.id), "code": c.code, "name": c.name,
                        "currency": c.currency, "balance": str(saldo), "status": c.status})
        por_moneda[c.currency] = por_moneda.get(c.currency, Decimal(0)) + saldo
    return {"accounts": detalle,
            "by_currency": [{"currency": k, "balance": str(v)} for k, v in sorted(por_moneda.items())]}


# --------------------------------------------------------------------------- #
# Spec 038 · reembolso de un crédito a favor
#
# `OWNER-DECISION-038-01`. El crédito lo habilita la Spec 037 y el dinero lo
# mueve ésta. El saldo económico sigue viviendo en la nota: duplicarlo aquí
# sería tener dos verdades sobre el mismo dinero.
#
# La regla que lo sostiene todo: el mismo importe no puede estar a la vez
# reservado para devolución y disponible para aplicarse a una cuenta por cobrar.
# --------------------------------------------------------------------------- #

def refundable_credit(db: Session, nota: SalesCreditNote) -> Decimal:
    """Lo que de una nota puede devolverse en dinero.

    Lo emitido menos lo ya aplicado a documentos, lo ya reservado para otra
    devolución y lo ya devuelto. Las tres restas son la misma idea: un crédito
    se gasta una vez.
    """
    return (_money(nota.amount) - _money(nota.applied)
            - _money(nota.refund_reserved) - _money(nota.refunded))


def request_refund(db: Session, *, company_id: str, credit_note_id: str,
                   amount: Decimal | float, reason: str, account_id: str | None = None,
                   payment_method_id: str | None = None, beneficiary_reference: str | None = None,
                   idempotency_key: str | None = None, actor: str | None = None) -> TreasuryRefund:
    """Solicita la devolución y **reserva** el crédito.

    La reserva es lo que impide gastarlo dos veces: desde aquí, ese importe ya
    no está disponible para aplicarse a una cuenta por cobrar.
    """
    company_id = _company(company_id, obj="reembolso")
    if idempotency_key:
        previa = db.execute(select(TreasuryRefund).where(
            TreasuryRefund.company_id == company_id,
            TreasuryRefund.idempotency_key == idempotency_key)).scalars().first()
        if previa is not None:
            return previa
    if not (reason or "").strip():
        raise KontrolError(code="REFUND_REASON_REQUIRED",
                           message="Una devolución exige motivo.", status_code=422)

    # El dueño se comprueba **antes** que la política: al revés, pedir el
    # reembolso de un crédito ajeno respondía «la política no lo admite» y
    # confirmaba de paso que el crédito existe. Es la misma lección que la Spec
    # 035 aprendió cuando el estado del pedido tapaba la comprobación de empresa.
    nota = db.execute(select(SalesCreditNote).where(
        SalesCreditNote.id == str(credit_note_id)).with_for_update()).scalars().first()
    if nota is None or str(nota.company_id) != str(company_id):
        raise NotFoundError(code="CREDIT_NOTE_NOT_FOUND", message="Nota de crédito no encontrada")

    politica = active_fx_policy(db, company_id)
    if politica is None or not politica.allow_refund:
        raise ConflictError(code="REFUND_NOT_ALLOWED",
                            message="La política vigente no admite devolución en dinero.")
    if nota.issued_at is None:
        raise ConflictError(code="CREDIT_NOTE_NOT_ISSUED",
                            message="Solo se devuelve un crédito de una nota emitida.")

    importe = _money(amount)
    disponible = refundable_credit(db, nota)
    if importe <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto debe ser positivo.",
                           status_code=422)
    if importe > disponible:
        raise ConflictError(
            code="REFUND_EXCEEDS_CREDIT",
            message="No se devuelve más crédito del que queda.",
            details={"refundable": str(disponible), "requested": str(importe)})

    if account_id:
        cuenta = _require_account(db, company_id, account_id)
        if cuenta.currency != nota.currency:
            raise ConflictError(
                code="REFUND_CURRENCY_MISMATCH",
                message="La cuenta está en otra moneda que el crédito.",
                details={"credit_currency": nota.currency, "account_currency": cuenta.currency})

    nota.refund_reserved = _money(nota.refund_reserved) + importe
    ahora = datetime.now(UTC)
    refund = TreasuryRefund(
        company_id=company_id, customer_id=str(nota.customer_id),
        credit_note_id=str(nota.id), currency=nota.currency, amount=importe,
        account_id=account_id, payment_method_id=payment_method_id,
        beneficiary_reference=beneficiary_reference, reason=reason, status="REQUESTED",
        idempotency_key=idempotency_key, requested_at=ahora, requested_by=actor,
        created_by=actor)
    db.add(refund)
    db.flush()
    _audit(db, action="TREASURY_REFUND_REQUESTED", entity_type="TreasuryRefund",
           entity_id=str(refund.id), company_id=company_id, actor=actor,
           after={"credit_note_id": str(nota.id), "amount": str(importe),
                  "currency": nota.currency, "reserved": str(nota.refund_reserved)})
    return refund


def decide_refund(db: Session, *, company_id: str, refund_id: str, approved: bool,
                  reason: str | None = None, actor: str | None = None) -> TreasuryRefund:
    """Aprueba o deniega. Denegar **libera** la reserva: el crédito vuelve."""
    company_id = _company(company_id, obj="reembolso")
    refund = _require_refund(db, company_id, refund_id, lock=True)
    if refund.status != "REQUESTED":
        raise ConflictError(code="REFUND_STATE", message="La devolución ya fue decidida.")
    if not approved and not (reason or "").strip():
        raise KontrolError(code="REFUND_REJECTION_REASON_REQUIRED",
                           message="Denegar una devolución exige motivo.", status_code=422)
    nota = db.execute(select(SalesCreditNote).where(
        SalesCreditNote.id == str(refund.credit_note_id)).with_for_update()).scalars().first()
    ahora = datetime.now(UTC)
    if approved:
        refund.status = "APPROVED"
    else:
        refund.status = "REJECTED"
        nota.refund_reserved = _money(nota.refund_reserved) - _money(refund.amount)
    refund.status_reason = reason
    refund.approved_at = ahora
    refund.approved_by = actor
    refund.updated_at = ahora
    db.flush()
    _audit(db, action=f"TREASURY_REFUND_{refund.status}", entity_type="TreasuryRefund",
           entity_id=str(refund.id), company_id=company_id, actor=actor,
           after={"reason": reason, "reserved": str(nota.refund_reserved)})
    return refund


def settle_refund(db: Session, *, company_id: str, refund_id: str, account_id: str | None = None,
                  actor: str | None = None) -> TreasuryRefund:
    """Ejecuta el pago y **consume** el crédito reservado.

    Aquí sale el dinero de verdad: un movimiento de salida en la cuenta, y la
    reserva se convierte en devuelto. Lo devuelto ya no vuelve a aplicarse.
    """
    company_id = _company(company_id, obj="reembolso")
    refund = _require_refund(db, company_id, refund_id, lock=True)
    if refund.settled_at is not None:
        return refund
    if refund.status != "APPROVED":
        raise ConflictError(code="REFUND_NOT_APPROVED",
                            message="Solo se ejecuta una devolución aprobada.")
    cuenta_id = account_id or refund.account_id
    if cuenta_id is None:
        raise ConflictError(code="REFUND_WITHOUT_ACCOUNT",
                            message="La devolución no dice desde qué cuenta se paga.")
    cuenta = _require_account(db, company_id, cuenta_id)
    if cuenta.currency != refund.currency:
        raise ConflictError(
            code="REFUND_CURRENCY_MISMATCH",
            message="La cuenta está en otra moneda que el crédito.",
            details={"credit_currency": refund.currency, "account_currency": cuenta.currency})
    importe = _money(refund.amount)
    disponible = account_balance(db, company_id=company_id, account_id=str(cuenta.id))
    if importe > disponible:
        raise ConflictError(
            code="INSUFFICIENT_FUNDS",
            message=f"La cuenta no tiene fondos suficientes ({disponible}).",
            details={"available": str(disponible), "requested": str(importe)})

    movimiento = create_bank_transaction(
        db, company_id=company_id, account_id=str(cuenta.id), direction="OUT",
        amount=importe, currency=refund.currency, source="REFUND",
        reference=f"REEMBOLSO-{str(refund.id)[:8]}", actor=actor)

    nota = db.execute(select(SalesCreditNote).where(
        SalesCreditNote.id == str(refund.credit_note_id)).with_for_update()).scalars().first()
    # La reserva se convierte en devuelto: el crédito se consume aquí, no antes.
    nota.refund_reserved = _money(nota.refund_reserved) - importe
    nota.refunded = _money(nota.refunded) + importe

    ahora = datetime.now(UTC)
    refund.status = "SETTLED"
    refund.account_id = str(cuenta.id)
    refund.movement_id = str(movimiento.id)
    refund.settled_at = ahora
    refund.settled_by = actor
    refund.updated_at = ahora
    db.flush()
    _audit(db, action="TREASURY_REFUND_SETTLED", entity_type="TreasuryRefund",
           entity_id=str(refund.id), company_id=company_id, actor=actor,
           after={"movement_id": str(movimiento.id), "amount": str(importe),
                  "account_id": str(cuenta.id), "refunded": str(nota.refunded)})
    return refund


def _require_refund(db: Session, company_id: str, refund_id: str,
                    *, lock: bool = False) -> TreasuryRefund:
    consulta = select(TreasuryRefund).where(TreasuryRefund.id == str(refund_id))
    if lock:
        consulta = consulta.with_for_update()
    refund = db.execute(consulta).scalars().first()
    if refund is None or str(refund.company_id) != str(company_id):
        raise NotFoundError(code="REFUND_NOT_FOUND", message="Devolución no encontrada")
    return refund


def refund_dict(refund: TreasuryRefund) -> dict:
    return {
        "id": str(refund.id), "status": refund.status, "status_reason": refund.status_reason,
        "customer_id": str(refund.customer_id), "credit_note_id": str(refund.credit_note_id),
        "currency": refund.currency, "amount": str(_money(refund.amount)),
        "account_id": str(refund.account_id) if refund.account_id else None,
        "movement_id": refund.movement_id, "reason": refund.reason,
        "requested_at": refund.requested_at.isoformat() if refund.requested_at else None,
        "approved_at": refund.approved_at.isoformat() if refund.approved_at else None,
        "settled_at": refund.settled_at.isoformat() if refund.settled_at else None,
    }


def fx_conversion_dict(db: Session, conv: TreasuryFxConversion) -> dict:
    snap = db.get(TreasuryRateSnapshot, str(conv.rate_snapshot_id))
    return {
        "id": str(conv.id), "status": conv.status,
        "source_account_id": str(conv.source_account_id),
        "target_account_id": str(conv.target_account_id),
        "source_currency": conv.source_currency, "target_currency": conv.target_currency,
        "source_amount": str(_money(conv.source_amount)),
        "target_amount": str(_money(conv.target_amount)),
        "exchange_difference": (str(_money(conv.exchange_difference))
                                if conv.exchange_difference is not None else None),
        "rate": str(snap.rate) if snap else None,
        "rate_source": snap.rate_source if snap else None,
        "rate_date": snap.rate_date.isoformat() if snap else None,
        "rate_origin": snap.origin if snap else None,
        "policy_version": snap.policy_version if snap else None,
    }


def create_fx_policy(db: Session, *, company_id: str, policy_code: str,
                     functional_currency: str, effective_from: date,
                     effective_date_basis: str = "SETTLEMENT", rate_source: str | None = None,
                     rate_type: str | None = None, allow_cross_currency: bool = False,
                     allow_manual_rate: bool = False, allow_refund: bool = False,
                     authority_reference: str | None = None,
                     actor: str | None = None) -> TreasuryFxPolicy:
    """Crea una versión de política. Nace en borrador: se activa aparte."""
    company_id = _company(company_id, obj="política cambiaria")
    if effective_date_basis not in ("TRANSACTION", "SETTLEMENT"):
        raise KontrolError(code="INVALID_DATE_BASIS",
                           message="La base de fecha efectiva no es válida.", status_code=422)
    previa = db.execute(select(TreasuryFxPolicy).where(
        TreasuryFxPolicy.company_id == company_id,
        TreasuryFxPolicy.policy_code == policy_code)
        .order_by(TreasuryFxPolicy.version.desc())).scalars().first()
    politica = TreasuryFxPolicy(
        company_id=company_id, policy_code=policy_code,
        version=(previa.version + 1) if previa else 1,
        functional_currency=functional_currency, effective_date_basis=effective_date_basis,
        rate_source=rate_source, rate_type=rate_type,
        allow_cross_currency=allow_cross_currency, allow_manual_rate=allow_manual_rate,
        allow_refund=allow_refund, authority_reference=authority_reference,
        effective_from=effective_from, status="DRAFT", created_by=actor)
    db.add(politica)
    db.flush()
    return politica


def activate_fx_policy(db: Session, *, company_id: str, policy_id: str,
                       actor: str | None = None) -> TreasuryFxPolicy:
    """Activa una versión y **sustituye** la anterior, sin reescribirla.

    La política anterior queda `SUPERSEDED`, no borrada: las operaciones que
    gobernó siguen apuntando a ella.
    """
    company_id = _company(company_id, obj="política cambiaria")
    politica = db.execute(select(TreasuryFxPolicy).where(
        TreasuryFxPolicy.id == str(policy_id)).with_for_update()).scalars().first()
    if politica is None or str(politica.company_id) != str(company_id):
        raise NotFoundError(code="FX_POLICY_NOT_FOUND", message="Política no encontrada")
    if politica.status != "DRAFT":
        raise ConflictError(code="FX_POLICY_STATE", message="La política ya fue activada.")
    # La sustitución se descarga **antes** de activar la nueva: el índice único
    # parcial no admite dos activas ni por un instante, y el orden en que
    # SQLAlchemy escribe no es el orden en que se asignan los atributos.
    for otra in db.execute(select(TreasuryFxPolicy).where(
            TreasuryFxPolicy.company_id == company_id,
            TreasuryFxPolicy.policy_code == politica.policy_code,
            TreasuryFxPolicy.status == "ACTIVE")).scalars().all():
        otra.status = "SUPERSEDED"
        otra.effective_to = politica.effective_from
    db.flush()
    politica.status = "ACTIVE"
    politica.approved_by = actor
    politica.approved_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="TREASURY_FX_POLICY_ACTIVATED", entity_type="TreasuryFxPolicy",
           entity_id=str(politica.id), company_id=company_id, actor=actor,
           after={"policy_code": politica.policy_code, "version": politica.version})
    return politica
