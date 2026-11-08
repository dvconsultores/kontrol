"""Logging estructurado JSON con request ID (ADR-010).

Cada request genera un request_id; los logs incluyen servicio, nivel,
request_id y, cuando es seguro, tenant/company/user. Nunca secretos.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        if hasattr(record, "event_id"):
            payload["event_id"] = record.event_id
        if hasattr(record, "service"):
            payload["service"] = record.service
        if hasattr(record, "tenant_id"):
            payload["tenant_id"] = record.tenant_id
        if hasattr(record, "company_id"):
            payload["company_id"] = record.company_id
        if hasattr(record, "user_id"):
            payload["user_id"] = record.user_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if settings.log_json else logging.Formatter())
    root.addHandler(handler)
    # Silenciar loggers ruidosos de terceros
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def new_request_id() -> str:
    return uuid.uuid4().hex


# Correlación de la petición en curso; GOV-CTL-003
request_id_actual: ContextVar[str | None] = ContextVar(
    "kontrol_request_id", default=None
)


@dataclass
class ContextoTecnico:
    """Sesión e IP de la petición en curso. Es mutable a propósito: FastAPI ejecuta las dependencias síncronas en un hilo con una copia del contexto, y solo un objeto compartido llega de la autenticación al servicio."""
    ip: str | None = None
    session_id: str | None = None


contexto_tecnico_actual: ContextVar[ContextoTecnico | None] = ContextVar(
    "kontrol_contexto_tecnico", default=None
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
