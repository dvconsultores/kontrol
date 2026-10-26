"""Servicio de dominio MFA: desafíos, verificación, alta, reautenticación y resets."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import NoReturn
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session as OrmSession

from app.core import clock, security
from app.core.errors import ConflictError, KontrolError, NotFoundError, PermissionDeniedError
from app.modules.identity_access import mfa_crypto, mfa_policy, mfa_qr, totp
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import (
    MfaChallenge,
    MfaFactor,
    MfaRecoveryCode,
    Session,
    User,
)
from app.modules.organization.models import Tenant
from app.shared.audit import record_audit

CHALLENGE_TTL = timedelta(seconds=300)
ENROLLMENT_TTL = timedelta(seconds=600)
REAUTH_MAX_AGE = timedelta(seconds=300)
MAX_CHALLENGE_ATTEMPTS = 5
MAX_ENROLLMENT_FAILURES = 5
RECOVERY_CODE_COUNT = 10
AUDIT_EVIDENCE_KEYS = frozenset(
    {
        "method",
        "policy_class",
        "recovery_codes_remaining",
        "reason",
        "sessions_revoked",
        "target_user_id",
        "attempts_remaining",
    }
)

_RECOVERY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def clock_now() -> datetime:
    """Instante del reloj único (`app.core.clock.now`), leído en cada llamada: las pruebas lo sustituyen."""
    return clock.now()


@dataclass
class LoginResult:
    status: str
    user: User
    session: Session | None = None
    refresh_token: str | None = None
    challenge_token: str | None = None
    recovery_codes_remaining: int | None = None


@dataclass
class EnrollmentResult:
    recovery_codes: list[str]
    login: LoginResult | None = None


def _hash(valor: str) -> str:
    return security.sha256_hex(valor)


def _aad(factor: MfaFactor) -> str:
    return f"{factor.tenant_id}|{factor.user_id}|{factor.id}"


def _normaliza_codigo_recuperacion(c: str) -> str:
    return c.upper().replace("-", "").replace(" ", "")


def _nuevo_codigo_recuperacion() -> str:
    codigo = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(16))
    return f"{codigo[:4]}-{codigo[4:8]}-{codigo[8:12]}-{codigo[12:]}"


def _active_factor(db: OrmSession, user_id: str) -> MfaFactor | None:
    return db.execute(
        select(MfaFactor).where(
            MfaFactor.user_id == user_id,
            MfaFactor.status == "ACTIVE",
        )
    ).scalar_one_or_none()


def _pending_factor(db: OrmSession, user_id: str) -> MfaFactor | None:
    return db.execute(
        select(MfaFactor).where(
            MfaFactor.user_id == user_id,
            MfaFactor.status == "PENDING",
        )
    ).scalar_one_or_none()


def _revoke_factor(db: OrmSession, factor: MfaFactor) -> None:
    now = clock_now()
    factor.status = "REVOKED"
    factor.secret_ciphertext = b""
    factor.key_id = None
    factor.revoked_at = now
    db.execute(
        delete(MfaRecoveryCode).where(MfaRecoveryCode.factor_id == factor.id)
    )


def _set_mfa_enabled(user: User, value: bool) -> None:
    user.mfa_enabled = value


def _audit_mfa(
    db: OrmSession,
    action: str,
    *,
    user: User,
    actor_id: str | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
    ip: str | None = None,
    source: str = "API",
    **evidence: str | int | bool | None,
) -> None:
    for key, value in evidence.items():
        if key not in AUDIT_EVIDENCE_KEYS:
            raise ValueError(f"Clave de auditoría no permitida: {key}")
        if not isinstance(value, str | int | bool | type(None)):
            raise ValueError(f"Valor de auditoría no permitido para {key}")
    record_audit(
        db,
        action=action,
        entity_type="User",
        entity_id=str(user.id),
        tenant_id=user.tenant_id,
        user_id=actor_id or str(user.id),
        session_id=session_id,
        request_id=request_id,
        source=source,
        ip=ip,
        reason=str(evidence["reason"]) if evidence.get("reason") is not None else None,
        evidence=dict(evidence) or None,
    )


def _fail_code(
    db: OrmSession,
    *,
    user: User,
    challenge: MfaChallenge | None,
    reason: str,
    request_id: str | None,
    ip: str | None,
) -> NoReturn:
    identity_service.register_auth_failure(db, user)
    if challenge is not None:
        challenge.attempts += 1
        if challenge.attempts >= MAX_CHALLENGE_ATTEMPTS:
            challenge.consumed_at = clock_now()
    attempts_remaining = max(
        0, MAX_CHALLENGE_ATTEMPTS - (challenge.attempts if challenge else 0)
    )
    _audit_mfa(
        db,
        "MFA_CHALLENGE_FAILED",
        user=user,
        request_id=request_id,
        ip=ip,
        reason=reason,
        attempts_remaining=attempts_remaining,
    )
    db.commit()
    code = "MFA_CODE_ALREADY_USED" if reason == "REPLAY" else "MFA_INVALID_CODE"
    raise KontrolError(
        code,
        "Código MFA no válido",
        details={"attempts_remaining": attempts_remaining},
        status_code=401,
    )


def _unavailable() -> NoReturn:
    raise KontrolError(
        "MFA_UNAVAILABLE",
        "El segundo factor no está disponible; contacta al administrador",
        status_code=503,
    )


def _decrypt(factor: MfaFactor) -> bytes:
    if factor.key_id is None:
        _unavailable()
    try:
        return mfa_crypto.decrypt_secret(
            factor.key_id, factor.secret_ciphertext, aad=_aad(factor)
        )
    except (mfa_crypto.MfaUnavailable, mfa_crypto.MfaDecryptError):
        _unavailable()


def _consume_totp(
    db: OrmSession, factor: MfaFactor, code: str, now: datetime
) -> str:
    raw = _decrypt(factor)
    step = totp.match_step(raw, code, now)
    if step is None:
        return "INVALID_CODE"
    result = db.execute(
        update(MfaFactor)
        .where(
            MfaFactor.id == factor.id,
            (MfaFactor.last_used_step.is_(None))
            | (MfaFactor.last_used_step < step),
        )
        .values(last_used_step=step)
    )
    if result.rowcount == 0:
        return "REPLAY"
    return "OK"


def _consume_recovery(
    db: OrmSession, user_id: str, code: str, now: datetime
) -> bool:
    normalizado = _normaliza_codigo_recuperacion(code)
    code_hash = _hash(normalizado)
    result = db.execute(
        update(MfaRecoveryCode)
        .where(
            MfaRecoveryCode.user_id == user_id,
            MfaRecoveryCode.code_hash == code_hash,
            MfaRecoveryCode.used_at.is_(None),
        )
        .values(used_at=now)
    )
    return result.rowcount == 1


def _new_recovery_codes(db: OrmSession, factor: MfaFactor) -> list[str]:
    user_id = factor.user_id
    db.execute(delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user_id))
    codigos: list[str] = []
    for _ in range(RECOVERY_CODE_COUNT):
        codigo = _nuevo_codigo_recuperacion()
        codigos.append(codigo)
        db.add(
            MfaRecoveryCode(
                user_id=user_id,
                factor_id=factor.id,
                code_hash=_hash(_normaliza_codigo_recuperacion(codigo)),
            )
        )
    return codigos


def _issue_challenge(
    db: OrmSession,
    *,
    user: User,
    purpose: str,
    ip: str | None,
    user_agent: str | None,
    request_id: str | None,
) -> str:
    token = secrets.token_urlsafe(32)
    now = clock_now()
    db.execute(
        delete(MfaChallenge).where(
            MfaChallenge.user_id == user.id,
            (
                (MfaChallenge.consumed_at.isnot(None))
                | (MfaChallenge.expires_at <= now)
            ),
        )
    )
    challenge = MfaChallenge(
        tenant_id=user.tenant_id,
        user_id=user.id,
        purpose=purpose,
        token_hash=_hash(token),
        expires_at=now + CHALLENGE_TTL,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(challenge)
    policy_class = mfa_policy.user_policy_class(db, user)
    _audit_mfa(
        db,
        "MFA_CHALLENGE_ISSUED",
        user=user,
        request_id=request_id,
        ip=ip,
        method=purpose,
        policy_class=policy_class,
    )
    return token


def _as_utc(dt: datetime) -> datetime:
    """Adjunta UTC solo si el motor devolvió la fecha sin zona (SQLite); una fecha con zona se respeta."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _load_challenge(
    db: OrmSession, token: str, purpose: str
) -> MfaChallenge:
    challenge = db.execute(
        select(MfaChallenge)
        .where(MfaChallenge.token_hash == _hash(token))
        .with_for_update()
    ).scalar_one_or_none()
    now = clock_now()
    if (
        challenge is None
        or challenge.purpose != purpose
        or challenge.consumed_at is not None
        or _as_utc(challenge.expires_at) <= _as_utc(now)
        or challenge.attempts >= MAX_CHALLENGE_ATTEMPTS
    ):
        raise KontrolError(
            "MFA_CHALLENGE_INVALID",
            "Desafío MFA no válido",
            status_code=401,
        )
    return challenge


def _complete(
    db: OrmSession,
    *,
    user: User,
    auth_method: str,
    ip: str | None,
    user_agent: str | None,
    request_id: str | None,
    mfa: bool,
) -> LoginResult:
    identity_service.complete_login_bookkeeping(db, user, request_id=request_id)
    session, refresh = identity_service.create_session(
        db,
        user=user,
        ip=ip,
        user_agent=user_agent,
        auth_method=auth_method,
        mfa_verified_at=clock_now() if mfa else None,
        reauth_at=clock_now(),
    )
    return LoginResult("AUTHENTICATED", user, session, refresh)


def is_reauth_recent(session: Session) -> bool:
    reauth_at = session.reauth_at
    if reauth_at is None:
        return False
    return clock_now() - _as_utc(reauth_at) <= REAUTH_MAX_AGE


def _require_reauth(session: Session) -> None:
    if not is_reauth_recent(session):
        raise KontrolError(
            "REAUTH_REQUIRED",
            "Se requiere reautenticación reciente",
            status_code=403,
        )


def _consume_challenge(db: OrmSession, challenge: MfaChallenge) -> None:
    now = clock_now()
    result = db.execute(
        update(MfaChallenge)
        .where(
            MfaChallenge.id == challenge.id,
            MfaChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    if result.rowcount == 0:
        raise KontrolError(
            "MFA_CHALLENGE_INVALID",
            "Desafío MFA no válido",
            status_code=401,
        )


def start_login(
    db: OrmSession,
    *,
    user: User,
    ip: str | None,
    user_agent: str | None,
    request_id: str | None,
) -> LoginResult:
    factor = _active_factor(db, str(user.id))
    policy_class = mfa_policy.user_policy_class(db, user)
    if factor is not None:
        token = _issue_challenge(
            db,
            user=user,
            purpose="LOGIN",
            ip=ip,
            user_agent=user_agent,
            request_id=request_id,
        )
        db.commit()
        return LoginResult(
            status="MFA_REQUIRED",
            user=user,
            challenge_token=token,
        )
    if mfa_policy.requires_mfa(policy_class):
        token = _issue_challenge(
            db,
            user=user,
            purpose="ENROLL",
            ip=ip,
            user_agent=user_agent,
            request_id=request_id,
        )
        db.commit()
        return LoginResult(
            status="MFA_ENROLLMENT_REQUIRED",
            user=user,
            challenge_token=token,
        )
    return _complete(
        db,
        user=user,
        auth_method="PASSWORD",
        ip=ip,
        user_agent=user_agent,
        request_id=request_id,
        mfa=False,
    )


def verify_login(
    db: OrmSession,
    *,
    challenge_token: str,
    code: str | None,
    recovery_code: str | None,
    ip: str | None,
    user_agent: str | None,
    request_id: str | None,
) -> LoginResult:
    if (code is None) == (recovery_code is None):
        raise KontrolError(
            "MFA_METHOD_REQUIRED",
            "Debe indicarse exactamente un método MFA",
            status_code=422,
        )
    challenge = _load_challenge(db, challenge_token, "LOGIN")
    user = db.execute(
        select(User).where(User.id == challenge.user_id)
    ).scalar_one_or_none()
    if user is None:
        raise KontrolError(
            "MFA_CHALLENGE_INVALID",
            "Desafío MFA no válido",
            status_code=401,
        )
    if identity_service.is_locked(user):
        _audit_mfa(
            db,
            "MFA_CHALLENGE_FAILED",
            user=user,
            request_id=request_id,
            ip=ip,
            reason="LOCKED",
        )
        db.commit()
        raise KontrolError(
            "AUTH_ACCOUNT_LOCKED",
            "Cuenta bloqueada",
            status_code=423,
        )
    factor = _active_factor(db, str(user.id))
    if factor is None:
        raise KontrolError(
            "MFA_CHALLENGE_INVALID",
            "Desafío MFA no válido",
            status_code=401,
        )

    method = "TOTP" if code is not None else "RECOVERY_CODE"
    auth_method = "PASSWORD_TOTP" if code is not None else "PASSWORD_RECOVERY"
    if code is not None:
        resultado = _consume_totp(db, factor, code, clock_now())
        if resultado != "OK":
            _fail_code(
                db,
                user=user,
                challenge=challenge,
                reason=resultado,
                request_id=request_id,
                ip=ip,
            )
    else:
        recovery = recovery_code if recovery_code is not None else ""
        if not _consume_recovery(db, str(user.id), recovery, clock_now()):
            _fail_code(
                db,
                user=user,
                challenge=challenge,
                reason="INVALID_CODE",
                request_id=request_id,
                ip=ip,
            )

    _consume_challenge(db, challenge)
    _audit_mfa(
        db,
        "MFA_CHALLENGE_SUCCEEDED",
        user=user,
        request_id=request_id,
        ip=ip,
        method=method,
    )
    recovery_codes_remaining: int | None = None
    if method == "RECOVERY_CODE":
        recovery_codes_remaining = db.execute(
            select(func.count())
            .select_from(MfaRecoveryCode)
            .where(
                MfaRecoveryCode.user_id == user.id,
                MfaRecoveryCode.used_at.is_(None),
            )
        ).scalar_one()
        _audit_mfa(
            db,
            "MFA_RECOVERY_CODE_USED",
            user=user,
            request_id=request_id,
            ip=ip,
            recovery_codes_remaining=recovery_codes_remaining,
        )
    login = _complete(
        db,
        user=user,
        auth_method=auth_method,
        ip=ip,
        user_agent=user_agent,
        request_id=request_id,
        mfa=True,
    )
    login.recovery_codes_remaining = recovery_codes_remaining
    return login


def _resolve_enrollment(
    db: OrmSession,
    *,
    challenge_token: str | None,
    user: User | None,
    session: Session | None,
) -> tuple[MfaChallenge | None, User, Session | None]:
    if challenge_token is not None:
        challenge = _load_challenge(db, challenge_token, "ENROLL")
        resolved_user = db.execute(
            select(User).where(User.id == challenge.user_id)
        ).scalar_one_or_none()
        if resolved_user is None:
            raise KontrolError(
                "MFA_CHALLENGE_INVALID",
                "Desafío MFA no válido",
                status_code=401,
            )
        if _active_factor(db, str(resolved_user.id)) is not None:
            raise KontrolError(
                "MFA_CHALLENGE_INVALID",
                "Desafío MFA no válido",
                status_code=401,
            )
        return challenge, resolved_user, None

    if user is None or session is None:
        raise KontrolError(
            "MFA_CHALLENGE_INVALID",
            "Desafío MFA no válido",
            status_code=401,
        )
    _require_reauth(session)
    return None, user, session


def start_enrollment(
    db: OrmSession,
    *,
    challenge_token: str | None,
    user: User | None,
    session: Session | None,
    request_id: str | None,
) -> dict:
    challenge, resolved_user, _ = _resolve_enrollment(
        db,
        challenge_token=challenge_token,
        user=user,
        session=session,
    )

    pending = _pending_factor(db, str(resolved_user.id))
    if pending is not None:
        _revoke_factor(db, pending)

    factor_id = str(uuid4())
    raw = totp.generate_secret()
    aad = f"{resolved_user.tenant_id}|{str(resolved_user.id)}|{factor_id}"
    try:
        kid, blob = mfa_crypto.encrypt_secret(raw, aad=aad)
    except mfa_crypto.MfaUnavailable:
        _unavailable()

    now = clock_now()
    factor = MfaFactor(
        id=factor_id,
        tenant_id=resolved_user.tenant_id,
        user_id=str(resolved_user.id),
        status="PENDING",
        key_id=kid,
        secret_ciphertext=blob,
        pending_expires_at=now + ENROLLMENT_TTL,
        created_by=str(resolved_user.id),
    )
    db.add(factor)
    policy_class = mfa_policy.user_policy_class(db, resolved_user)
    method = "CHALLENGE" if challenge is not None else "SESSION"
    _audit_mfa(
        db,
        "MFA_ENROLLMENT_STARTED",
        user=resolved_user,
        request_id=request_id,
        method=method,
        policy_class=policy_class,
    )
    db.commit()

    encoded = totp.encode_secret(raw)
    otpauth_uri = totp.provisioning_uri(raw, account=resolved_user.username)
    return {
        "otpauth_uri": otpauth_uri,
        "manual_key": totp.format_manual_key(encoded),
        "qr_svg_data_uri": mfa_qr.svg_data_uri(otpauth_uri),
        "expires_in": 600,
    }


def confirm_enrollment(
    db: OrmSession,
    *,
    challenge_token: str | None,
    user: User | None,
    session: Session | None,
    code: str,
    ip: str | None,
    user_agent: str | None,
    request_id: str | None,
) -> EnrollmentResult:
    challenge, resolved_user, narrowed_session = _resolve_enrollment(
        db,
        challenge_token=challenge_token,
        user=user,
        session=session,
    )

    if identity_service.is_locked(resolved_user):
        raise KontrolError(
            "AUTH_ACCOUNT_LOCKED",
            "Cuenta bloqueada",
            status_code=423,
        )

    factor = _pending_factor(db, str(resolved_user.id))
    now = clock_now()
    if (
        factor is None
        or factor.pending_expires_at is None
        or _as_utc(factor.pending_expires_at) <= _as_utc(now)
    ):
        raise ConflictError(
            "MFA_NO_PENDING_ENROLLMENT",
            "No hay un alta MFA pendiente",
        )

    raw = _decrypt(factor)
    step = totp.match_step(raw, code, now)
    if step is None:
        factor.failed_confirmations += 1
        if factor.failed_confirmations >= MAX_ENROLLMENT_FAILURES:
            _revoke_factor(db, factor)
        identity_service.register_auth_failure(db, resolved_user)
        _audit_mfa(
            db,
            "MFA_ENROLLMENT_FAILED",
            user=resolved_user,
            request_id=request_id,
            ip=ip,
            reason="INVALID_CODE",
        )
        db.commit()
        raise KontrolError(
            "MFA_INVALID_CODE",
            "Código MFA no válido",
            status_code=401,
        )

    old_factor = _active_factor(db, str(resolved_user.id))
    replaced = old_factor is not None
    if old_factor is not None:
        _revoke_factor(db, old_factor)
        db.flush()

    factor.status = "ACTIVE"
    factor.activated_at = now
    factor.last_used_step = step
    factor.pending_expires_at = None
    _set_mfa_enabled(resolved_user, True)
    recovery_codes = _new_recovery_codes(db, factor)

    if replaced:
        _audit_mfa(
            db,
            "MFA_FACTOR_REPLACED",
            user=resolved_user,
            request_id=request_id,
            ip=ip,
        )
    else:
        _audit_mfa(
            db,
            "MFA_ENABLED",
            user=resolved_user,
            request_id=request_id,
            ip=ip,
        )

    login: LoginResult | None = None
    if challenge is not None:
        _consume_challenge(db, challenge)
        login = _complete(
            db,
            user=resolved_user,
            auth_method="PASSWORD_TOTP",
            ip=ip,
            user_agent=user_agent,
            request_id=request_id,
            mfa=True,
        )
    else:
        if narrowed_session is None:
            raise KontrolError(
                "MFA_CHALLENGE_INVALID",
                "Desafío MFA no válido",
                status_code=401,
            )
        if narrowed_session.mfa_verified_at is None:
            narrowed_session.mfa_verified_at = now
        reason = "FACTOR_REPLACED" if replaced else "FACTOR_ENABLED"
        identity_service.revoke_user_sessions(
            db,
            user_id=str(resolved_user.id),
            except_family_id=narrowed_session.family_id,
            reason=reason,
        )
        db.commit()

    return EnrollmentResult(recovery_codes=recovery_codes, login=login)


def mfa_status(db: OrmSession, *, user: User) -> dict:
    factor = _active_factor(db, str(user.id))
    policy_class = mfa_policy.user_policy_class(db, user)
    remaining = (
        db.execute(
            select(func.count())
            .select_from(MfaRecoveryCode)
            .where(
                MfaRecoveryCode.user_id == user.id,
                MfaRecoveryCode.used_at.is_(None),
            )
        ).scalar_one()
        if factor is not None
        else 0
    )
    return {
        "required": mfa_policy.requires_mfa(policy_class),
        "policy_class": policy_class,
        "enabled": factor is not None,
        "activated_at": factor.activated_at.isoformat() if factor and factor.activated_at else None,
        "recovery_codes_remaining": remaining,
    }


def regenerate_recovery_codes(
    db: OrmSession,
    *,
    user: User,
    session: Session,
    request_id: str | None,
) -> list[str]:
    _require_reauth(session)
    factor = _active_factor(db, str(user.id))
    if factor is None:
        raise ConflictError("MFA_NOT_CONFIGURED", "MFA no configurado")
    codigos = _new_recovery_codes(db, factor)
    _audit_mfa(
        db,
        "MFA_RECOVERY_CODES_REGENERATED",
        user=user,
        session_id=str(session.id),
        request_id=request_id,
        recovery_codes_remaining=RECOVERY_CODE_COUNT,
    )
    db.commit()
    return codigos


def remove_own_factor(
    db: OrmSession,
    *,
    user: User,
    session: Session,
    request_id: str | None,
) -> None:
    _require_reauth(session)
    policy_class = mfa_policy.user_policy_class(db, user)
    if mfa_policy.requires_mfa(policy_class):
        raise PermissionDeniedError(
            "MFA_REQUIRED_BY_POLICY",
            "La política exige MFA",
        )
    factor = _active_factor(db, str(user.id))
    if factor is None:
        raise ConflictError("MFA_NOT_CONFIGURED", "MFA no configurado")
    _revoke_factor(db, factor)
    _set_mfa_enabled(user, False)
    identity_service.revoke_user_sessions(
        db,
        user_id=str(user.id),
        except_family_id=session.family_id,
        reason="FACTOR_DISABLED",
    )
    _audit_mfa(
        db,
        "MFA_DISABLED",
        user=user,
        session_id=str(session.id),
        request_id=request_id,
    )
    db.commit()


def reauthenticate(
    db: OrmSession,
    *,
    user: User,
    session: Session,
    password: str,
    code: str | None,
    recovery_code: str | None,
    request_id: str | None,
) -> datetime:
    if identity_service.is_locked(user):
        raise KontrolError(
            "AUTH_ACCOUNT_LOCKED",
            "Cuenta bloqueada",
            status_code=423,
        )

    if not security.verify_password(password, user.password_hash):
        identity_service.register_auth_failure(db, user)
        _audit_mfa(
            db,
            "MFA_REAUTH_FAILED",
            user=user,
            session_id=str(session.id),
            request_id=request_id,
            reason="INVALID_PASSWORD",
        )
        db.commit()
        raise KontrolError(
            "REAUTH_FAILED",
            "Reautenticación fallida",
            status_code=401,
        )

    factor = _active_factor(db, str(user.id))
    method: str | None = None
    if factor is not None:
        if code is None and recovery_code is None:
            identity_service.register_auth_failure(db, user)
            _audit_mfa(
                db,
                "MFA_REAUTH_FAILED",
                user=user,
                session_id=str(session.id),
                request_id=request_id,
                reason="SECOND_FACTOR_REQUIRED",
            )
            db.commit()
            raise KontrolError(
                "REAUTH_FAILED",
                "Reautenticación fallida",
                status_code=401,
            )

        now = clock_now()
        if code is not None:
            resultado = _consume_totp(db, factor, code, now)
            if resultado != "OK":
                identity_service.register_auth_failure(db, user)
                _audit_mfa(
                    db,
                    "MFA_REAUTH_FAILED",
                    user=user,
                    session_id=str(session.id),
                    request_id=request_id,
                    reason=resultado,
                )
                db.commit()
                raise KontrolError(
                    "REAUTH_FAILED",
                    "Reautenticación fallida",
                    status_code=401,
                )
            method = "TOTP"
        else:
            recovery = recovery_code if recovery_code is not None else ""
            if not _consume_recovery(db, str(user.id), recovery, now):
                identity_service.register_auth_failure(db, user)
                _audit_mfa(
                    db,
                    "MFA_REAUTH_FAILED",
                    user=user,
                    session_id=str(session.id),
                    request_id=request_id,
                    reason="INVALID_CODE",
                )
                db.commit()
                raise KontrolError(
                    "REAUTH_FAILED",
                    "Reautenticación fallida",
                    status_code=401,
                )
            method = "RECOVERY_CODE"

    now = clock_now()
    user.failed_attempts = 0
    current = identity_service.current_session_row(db, session.family_id)
    if current is not None:
        current.reauth_at = now
    _audit_mfa(
        db,
        "MFA_REAUTH_SUCCEEDED",
        user=user,
        session_id=str(session.id),
        request_id=request_id,
        method=method,
    )
    db.commit()
    return now + REAUTH_MAX_AGE


def admin_reset(
    db: OrmSession,
    *,
    actor: User,
    target_user_id: str,
    session: Session,
    request_id: str | None,
) -> None:
    _require_reauth(session)
    target = identity_service.get_user_in_tenant(
        db, target_user_id, actor.tenant_id
    )
    if target is None:
        raise NotFoundError("USER_NOT_FOUND", "Usuario no encontrado")
    if str(target.id) == str(actor.id):
        raise PermissionDeniedError(
            "MFA_RESET_SELF_FORBIDDEN",
            "No se permite el reset propio",
        )

    target_perms = set(identity_service.get_user_permissions(db, target))
    actor_perms = set(identity_service.get_user_permissions(db, actor))
    if target_perms - actor_perms:
        raise PermissionDeniedError(
            "MFA_RESET_CEILING",
            "El objetivo tiene permisos superiores",
        )

    factor = _active_factor(db, str(target.id))
    if factor is None:
        raise ConflictError("MFA_NOT_CONFIGURED", "MFA no configurado")

    _revoke_factor(db, factor)
    pending = _pending_factor(db, str(target.id))
    if pending is not None:
        _revoke_factor(db, pending)
    _set_mfa_enabled(target, False)

    n = identity_service.revoke_user_sessions(
        db,
        user_id=str(target.id),
        reason="MFA_RESET_BY_ADMIN",
        actor_id=str(actor.id),
    )
    _audit_mfa(
        db,
        "MFA_RESET_BY_ADMIN",
        user=target,
        actor_id=str(actor.id),
        session_id=str(session.id),
        target_user_id=str(target.id),
        sessions_revoked=n,
    )
    db.commit()


def breakglass_reset(
    db: OrmSession,
    *,
    tenant_code: str,
    username: str,
) -> None:
    tenant_row = db.execute(
        select(Tenant).where(Tenant.code == tenant_code)
    ).scalar_one_or_none()
    if tenant_row is None:
        raise LookupError("Tenant o usuario no encontrado")
    user = db.execute(
        select(User).where(
            User.tenant_id == tenant_row.id,
            User.username == username,
        )
    ).scalar_one_or_none()
    if user is None:
        raise LookupError("Tenant o usuario no encontrado")
    factor = _active_factor(db, str(user.id))
    if factor is None:
        raise LookupError("Tenant o usuario no encontrado")
    _revoke_factor(db, factor)
    pending = _pending_factor(db, str(user.id))
    if pending is not None:
        _revoke_factor(db, pending)
    _set_mfa_enabled(user, False)
    identity_service.revoke_user_sessions(
        db,
        user_id=str(user.id),
        reason="MFA_RESET_BREAKGLASS",
    )
    _audit_mfa(
        db,
        "MFA_RESET_BREAKGLASS",
        user=user,
        source="CLI",
    )
    db.commit()


def rekey_factors(db: OrmSession) -> int:
    active_kid = mfa_crypto.active_key_id()
    factores = db.execute(
        select(MfaFactor).where(
            MfaFactor.status.in_(("ACTIVE", "PENDING")),
            MfaFactor.key_id != active_kid,
        )
    ).scalars().all()
    rekeyed = 0
    for factor in factores:
        if factor.key_id is None:
            db.rollback()
            raise mfa_crypto.MfaUnavailable("No se pudo recifrar un factor: falta su clave o está dañado")
        try:
            raw = mfa_crypto.decrypt_secret(
                factor.key_id, factor.secret_ciphertext, aad=_aad(factor)
            )
        except (mfa_crypto.MfaUnavailable, mfa_crypto.MfaDecryptError):
            db.rollback()
            raise mfa_crypto.MfaUnavailable(
                "No se pudo recifrar un factor: falta su clave o está dañado"
            ) from None
        kid, blob = mfa_crypto.encrypt_secret(raw, aad=_aad(factor))
        factor.key_id = kid
        factor.secret_ciphertext = blob
        rekeyed += 1
        user = db.execute(
            select(User).where(User.id == factor.user_id)
        ).scalar_one_or_none()
        if user is not None:
            _audit_mfa(db, "MFA_REKEYED", user=user)
    db.commit()
    return rekeyed
