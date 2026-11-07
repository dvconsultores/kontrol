from __future__ import annotations

import pytest
from backup_job_apoyo import AHORA, crear_mundo
from sqlalchemy import select

from app.core.errors import ConflictError, KontrolError
from app.core.operaciones import catalogo_de_operaciones
from app.main import create_app
from app.modules.audit.models import AuditEvent
from app.modules.identity_access.mfa_policy import REAUTH_PROTECTED_OPERATIONS
from app.modules.organization.models import Tenant
from app.ops import backup_job
from app.ops.backup_rpo import TIPO_DESTINO_MONTADO


@pytest.fixture
def factory(tmp_path):
    return crear_mundo(tmp_path)


def _datos(**cambios):
    datos = {
        "configured_rpo_minutes": 15,
        "schedule_interval_minutes": 5,
        "safety_margin_minutes": 2,
        "retention_days": 7,
        "retention_min_copies": 1,
        "destination_type": TIPO_DESTINO_MONTADO,
        "destination_label": "nas-1",
        "scheduler_enabled": True,
    }
    datos.update(cambios)
    return datos


def _guardar(factory, version=0, **cambios):
    with factory() as db:
        tenant = db.scalar(select(Tenant))
        return backup_job.guardar_configuracion(
            db,
            _datos(**cambios),
            version=version,
            usuario_id="u1",
            tenant_id=str(tenant.id),
            ahora=AHORA,
        )


def test_guardar_y_leer(factory):
    estado = _guardar(factory)
    assert estado["configured_rpo_minutes"] == 15
    assert estado["scheduler_enabled"] is True
    assert estado["version"] == 1


def test_rpo_mayor_de_15_rechazado(factory):
    with pytest.raises(KontrolError) as error:
        _guardar(factory, configured_rpo_minutes=16)
    assert "RPO_ABOVE_MAXIMUM" in error.value.details["errors"]
    assert error.value.status_code == 422


def test_rpo_mayor_de_15_rechazado_aunque_este_deshabilitado(factory):
    with pytest.raises(KontrolError) as error:
        _guardar(factory, configured_rpo_minutes=16, scheduler_enabled=False)
    assert "RPO_ABOVE_MAXIMUM" in error.value.details["errors"]
    assert error.value.status_code == 422


def test_habilitar_sin_retencion_rechazado(factory):
    with pytest.raises(KontrolError) as error:
        _guardar(factory, retention_days=None)
    assert "RETENTION_REQUIRED" in error.value.details["errors"]


def test_habilitar_sin_destino_rechazado(factory):
    with pytest.raises(KontrolError) as error:
        _guardar(factory, destination_label=None)
    assert "DESTINATION_REQUIRED" in error.value.details["errors"]


def test_guardar_deshabilitada_incompleta_se_permite(factory):
    estado = _guardar(
        factory,
        configured_rpo_minutes=None,
        schedule_interval_minutes=None,
        safety_margin_minutes=None,
        retention_days=None,
        retention_min_copies=None,
        destination_type=None,
        destination_label=None,
        scheduler_enabled=False,
    )
    assert estado["version"] == 1


def test_destino_s3_rechazado(factory):
    with pytest.raises(KontrolError) as error:
        _guardar(factory, destination_type="s3")
    assert "DESTINATION_UNSUPPORTED" in error.value.details["errors"]


def test_etiqueta_con_ruta_rechazada(factory):
    with pytest.raises(KontrolError) as error:
        _guardar(factory, destination_label="../x")
    assert "DESTINATION_LABEL_INVALID" in error.value.details["errors"]


def test_version_desfasada_rechazada(factory):
    _guardar(factory)
    with pytest.raises(ConflictError):
        _guardar(factory, version=0)


def test_segunda_escritura_incrementa_version(factory):
    _guardar(factory)
    estado = _guardar(factory, version=1)
    assert estado["version"] == 2


def test_cambio_queda_auditado(factory):
    _guardar(factory)
    with factory() as db:
        evento = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "INSTALLATION_BACKUP_CONFIG_CHANGED")
        )
        assert evento is not None
        assert evento.source == "API"


def test_operacion_exige_reautenticacion():
    assert ("PUT", "/api/v1/system/backup-config") in REAUTH_PROTECTED_OPERATIONS


def test_operacion_exige_licencia_editar():
    app = create_app()
    operaciones = catalogo_de_operaciones(app)
    assert {
        "method": "PUT",
        "path": "/api/v1/system/backup-config",
        "capabilities": ["license:edit"],
        "scope": "GLOBAL",
    } in operaciones


def test_diagnostico_no_expone_secretos(factory):
    with factory() as db:
        estado = backup_job.estado_de_copias(db, AHORA)
    texto = str(sorted(estado))
    assert "sha256" not in texto
    assert "path" not in texto
    assert "key" not in texto
