"""Guardas de arquitectura del aislamiento (Spec 001).

Estas pruebas impiden volver atrás en las decisiones de aislamiento: cualquier
modelo, ruta o ayudante nuevo que rompa las reglas hace fallar la suite. No
tocan base de datos: solo introspección de modelos y lectura de fuentes.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest
from fastapi.routing import APIRoute

from app.core.company_context import get_company_context
from app.core.database import Base, init_models
from app.core.scope import Scope, declared_scope
from app.main import create_app

RAIZ = pathlib.Path(__file__).resolve().parent.parent / "app"

ALCANCE_DE_INSTALACION_JUSTIFICADO: dict[str, tuple[str, str]] = {
    "feature_flags": ("interruptores de funcionalidad de la instalación", "001"),
    "homologation_events": ("bitácora de homologación de la instalación", "011"),
    "homologation_records": ("expedientes de homologación de la instalación", "011"),
    "idempotency_records": ("registro técnico de idempotencia; la clave lleva el recurso acotado", "001"),
    "installations": ("la propia instalación", "001"),
    "legacy_document_references": ("anotación del legado importado por la operadora, sin ruta HTTP", "046"),
    "legal_sources": ("fuentes legales versionadas por instalación (P4)", "007"),
    "license_artifacts": ("licencia de la instalación", "004/010"),
    "license_central_config": ("configuración del licenciamiento central", "010"),
    "license_entitlement_snapshots": ("derechos de la licencia", "010"),
    "license_events": ("historial inmutable de licencia", "004"),
    "license_renewal_requests": ("solicitudes de renovación de la licencia", "010"),
    "license_states": ("estado de licencia de la instalación", "004"),
    "license_sync_runs": ("sincronizaciones con el licenciamiento central", "010"),
    "permissions": ("catálogo estático de permisos", "001"),
    "release_versions": ("versiones liberadas de la instalación", "011"),
    "role_permissions": ("permisos de un rol; su alcance es el del rol", "001"),
    "scheduler_handler_runs": ("ejecuciones técnicas del planificador", "047"),
    "scheduler_runs": ("ciclos técnicos del planificador", "047"),
    "system_settings": ("ajustes técnicos (sin uso de API)", "001"),
    "tax_rule_versions": ("versiones de reglas fiscales de referencia", "007"),
    "tenants": ("los tenants de la instalación", "001"),
    "unit_conversions": ("conversiones de unidades de la plataforma", "011"),
}

RUTAS_SIN_EMPRESA_CLASIFICADAS: dict[tuple[str, str], tuple[str, str]] = {
    ("DELETE", "/api/v1/auth/mfa"): ("SELF", "factor del propio usuario"),
    ("DELETE", "/api/v1/auth/sessions/{session_id}"): ("SELF", "solo sesiones propias; ajena = inexistente (G-SES-01)"),
    ("DELETE", "/api/v1/users/{user_id}/roles/{role_id}"): ("TENANT", "usuario del tenant del actor"),
    ("GET", "/"): ("PUBLIC", "raíz informativa"),
    ("GET", "/api/v1/approvals/process-types"): ("INSTALLATION", "catálogo estático de tipos de proceso"),
    ("GET", "/api/v1/audit/events"): ("TENANT", "bitácora del tenant del actor, acotada por empresa auditable (ciclo 04)"),
    ("GET", "/api/v1/audit/filters"): ("TENANT", "filtros del alcance de auditoría del actor (ciclo 04)"),
    ("GET", "/api/v1/auth/me"): ("SELF", "el propio usuario"),
    ("GET", "/api/v1/auth/mfa"): ("SELF", "factor del propio usuario"),
    ("GET", "/api/v1/auth/operations"): ("SELF", "operaciones del propio usuario"),
    ("GET", "/api/v1/auth/sessions"): ("SELF", "sesiones del propio usuario"),
    ("GET", "/api/v1/documentos/salud/almacenamiento"): ("INSTALLATION", "salud del almacén de la instalación"),
    ("GET", "/api/v1/fiscal/legal-sources"): ("INSTALLATION", "núcleo fiscal versionado por instalación (P4); exige autoridad de todo el tenant"),
    ("GET", "/api/v1/fiscal/tax-rule-versions"): ("INSTALLATION", "núcleo fiscal versionado por instalación (P4); exige autoridad de todo el tenant"),
    ("GET", "/api/v1/health/live"): ("PUBLIC", "sonda de vida sin datos"),
    ("GET", "/api/v1/health/ready"): ("PUBLIC", "sonda de disponibilidad sin datos de negocio"),
    ("GET", "/api/v1/homologation/records"): ("INSTALLATION", "homologación y liberación de la instalación (Spec 011)"),
    ("GET", "/api/v1/homologation/records/{record_id}"): ("INSTALLATION", "homologación y liberación de la instalación (Spec 011)"),
    ("GET", "/api/v1/homologation/releases"): ("INSTALLATION", "homologación y liberación de la instalación (Spec 011)"),
    ("GET", "/api/v1/homologation/timeline"): ("INSTALLATION", "homologación y liberación de la instalación (Spec 011)"),
    ("GET", "/api/v1/license/detail"): ("INSTALLATION", "licencia de la instalación (Spec 004)"),
    ("GET", "/api/v1/license/history"): ("INSTALLATION", "licencia de la instalación (Spec 004)"),
    ("GET", "/api/v1/license/installation-request"): ("INSTALLATION", "licencia de la instalación (Spec 004)"),
    ("GET", "/api/v1/license/status"): ("PUBLIC", "estado de licencia de la instalación para la pantalla previa al login"),
    ("GET", "/api/v1/licensing/central-config"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("GET", "/api/v1/licensing/entitlement-snapshots"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("GET", "/api/v1/licensing/entitlements"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("GET", "/api/v1/licensing/offline-status"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("GET", "/api/v1/licensing/overview"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("GET", "/api/v1/licensing/renewal-requests"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("GET", "/api/v1/licensing/sync-runs"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("GET", "/api/v1/organization/companies"): ("TENANT", "empresas accesibles del tenant del actor"),
    ("GET", "/api/v1/roles"): ("TENANT", "roles del sistema y del tenant del actor (OD-ISO-11)"),
    ("GET", "/api/v1/setup/status"): ("PUBLIC", "estado de inicialización de la instalación (sin datos de tenant)"),
    ("GET", "/api/v1/system/diagnostics"): ("INSTALLATION", "diagnóstico técnico de la instalación"),
    ("GET", "/api/v1/users"): ("TENANT", "usuarios del tenant del actor (N10)"),
    ("POST", "/api/v1/approvals/steps/{step_id}/approve"): ("ELIGIBILITY", "elegibilidad congelada del aprobador (N10)"),
    ("POST", "/api/v1/approvals/steps/{step_id}/reject"): ("ELIGIBILITY", "elegibilidad congelada del aprobador (N10)"),
    ("POST", "/api/v1/approvals/steps/{step_id}/return"): ("ELIGIBILITY", "elegibilidad congelada del aprobador (N10)"),
    ("POST", "/api/v1/auth/change-password"): ("SELF", "el propio usuario"),
    ("POST", "/api/v1/auth/login"): ("PUBLIC", "credenciales; el tenant lo da el cuerpo y se valida con la contraseña"),
    ("POST", "/api/v1/auth/logout"): ("PUBLIC", "cookie de la propia sesión"),
    ("POST", "/api/v1/auth/mfa/enrollment"): ("PUBLIC", "token de desafío del propio login"),
    ("POST", "/api/v1/auth/mfa/enrollment/confirm"): ("PUBLIC", "token de desafío del propio login"),
    ("POST", "/api/v1/auth/mfa/recovery-codes"): ("SELF", "códigos del propio usuario"),
    ("POST", "/api/v1/auth/mfa/verify"): ("PUBLIC", "token de desafío del propio login"),
    ("POST", "/api/v1/auth/password-reset/confirm"): ("PUBLIC", "token de un solo uso"),
    ("POST", "/api/v1/auth/password-reset/request"): ("PUBLIC", "respuesta idéntica exista o no el usuario (Spec 002)"),
    ("POST", "/api/v1/auth/reauth"): ("SELF", "reautenticación de la propia sesión"),
    ("POST", "/api/v1/auth/refresh"): ("PUBLIC", "cookie de refresco de la propia sesión"),
    ("POST", "/api/v1/fiscal/legal-sources"): ("INSTALLATION", "núcleo fiscal versionado por instalación (P4); exige autoridad de todo el tenant"),
    ("POST", "/api/v1/fiscal/legal-sources/{source_id}/activate"): ("INSTALLATION", "núcleo fiscal versionado por instalación (P4); exige autoridad de todo el tenant"),
    ("POST", "/api/v1/fiscal/tax-rule-versions"): ("INSTALLATION", "núcleo fiscal versionado por instalación (P4); exige autoridad de todo el tenant"),
    ("POST", "/api/v1/fiscal/tax-rule-versions/{rule_id}/approve"): ("INSTALLATION", "núcleo fiscal versionado por instalación (P4); exige autoridad de todo el tenant"),
    ("POST", "/api/v1/homologation/records"): ("INSTALLATION", "homologación y liberación de la instalación (Spec 011)"),
    ("POST", "/api/v1/homologation/records/{record_id}/evaluate"): ("INSTALLATION", "homologación y liberación de la instalación (Spec 011)"),
    ("POST", "/api/v1/homologation/records/{record_id}/submit"): ("INSTALLATION", "homologación y liberación de la instalación (Spec 011)"),
    ("POST", "/api/v1/homologation/releases"): ("INSTALLATION", "homologación y liberación de la instalación (Spec 011)"),
    ("POST", "/api/v1/homologation/releases/{release_id}/promote"): ("INSTALLATION", "homologación y liberación de la instalación (Spec 011)"),
    ("POST", "/api/v1/homologation/releases/{release_id}/release"): ("INSTALLATION", "homologación y liberación de la instalación (Spec 011)"),
    ("POST", "/api/v1/license/activate"): ("INSTALLATION", "licencia de la instalación (Spec 004)"),
    ("POST", "/api/v1/license/import"): ("INSTALLATION", "licencia de la instalación (Spec 004)"),
    ("POST", "/api/v1/license/renewal-request"): ("INSTALLATION", "licencia de la instalación (Spec 004)"),
    ("POST", "/api/v1/licensing/mode-transition"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("POST", "/api/v1/licensing/renewal-requests"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("POST", "/api/v1/licensing/renewal-requests/{request_id}/transition"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("POST", "/api/v1/licensing/sync"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
    ("POST", "/api/v1/organization/companies"): ("TENANT", "empresa en el tenant del actor; exige autoridad de todo el tenant"),
    ("POST", "/api/v1/roles"): ("TENANT", "rol del tenant del actor (OD-ISO-11)"),
    ("POST", "/api/v1/setup/initialize"): ("PUBLIC", "una sola vez por instalación (SETUP_ALREADY_DONE)"),
    ("POST", "/api/v1/users"): ("TENANT", "alta en el tenant del actor"),
    ("POST", "/api/v1/users/{user_id}/mfa/reset"): ("TENANT", "usuario del tenant del actor (Spec 002)"),
    ("POST", "/api/v1/users/{user_id}/roles"): ("TENANT", "usuario y rol del tenant del actor; techo de delegación (G-ROL-01)"),
    ("PUT", "/api/v1/licensing/central-config"): ("INSTALLATION", "licenciamiento central de la instalación (Spec 010)"),
}

_CLASES_VALIDAS = {"PUBLIC", "SELF", "TENANT", "INSTALLATION", "ELIGIBILITY"}


@pytest.fixture(scope="module")
def tablas_mapeadas() -> set[str]:
    init_models()
    return {mapper.class_.__tablename__ for mapper in Base.registry.mappers}


def _tablas_de_instalacion_o_global() -> set[str]:
    init_models()
    resultado: set[str] = set()
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if declared_scope(cls) in (Scope.INSTALLATION, Scope.GLOBAL):
            resultado.add(cls.__tablename__)
    return resultado


def test_iso_g01_todo_modelo_de_instalacion_o_global_esta_justificado() -> None:
    """Impide (OD-ISO-06/09) una tabla de instalación o global sin motivo declarado."""
    reales = _tablas_de_instalacion_o_global()
    justificadas = set(ALCANCE_DE_INSTALACION_JUSTIFICADO)
    sobrantes = reales - justificadas
    faltantes = justificadas - reales
    assert reales == justificadas, (
        "Tablas con alcance de instalación/global sin justificar: "
        f"{sorted(sobrantes)}; justificadas inexistentes: {sorted(faltantes)}"
    )


def test_iso_g02_la_lista_de_instalacion_no_guarda_entradas_muertas(tablas_mapeadas: set[str]) -> None:
    """Impide (OD-ISO-06/09) que la lista de justificación conserve tablas que ya no existen."""
    muertas = sorted(set(ALCANCE_DE_INSTALACION_JUSTIFICADO) - tablas_mapeadas)
    assert not muertas, f"Entradas muertas en ALCANCE_DE_INSTALACION_JUSTIFICADO: {muertas}"


def _depende_de_empresa(depend: Any) -> bool:
    if depend.call is get_company_context:
        return True
    return any(_depende_de_empresa(sub) for sub in depend.dependencies)


def _rutas_sin_empresa() -> set[tuple[str, str]]:
    app = create_app()
    resultado: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if _depende_de_empresa(route.dependant):
            continue
        for metodo in route.methods:
            resultado.add((metodo.upper(), route.path))
    return resultado


def test_iso_g03_toda_ruta_sin_empresa_esta_clasificada() -> None:
    """Impide (OD-ISO-09) rutas sin contexto de empresa sin clasificar, y entradas muertas."""
    reales = _rutas_sin_empresa()
    registradas = set(RUTAS_SIN_EMPRESA_CLASIFICADAS)
    sin_clasificar = reales - registradas
    muertas = registradas - reales
    assert not sin_clasificar, (
        "Rutas sin get_company_context sin clasificar (método, ruta): "
        f"{sorted(sin_clasificar)}"
    )
    assert not muertas, (
        "Entradas clasificadas que no corresponden a una ruta sin contexto existente: "
        f"{sorted(muertas)}"
    )
    for clave, (clase, motivo) in RUTAS_SIN_EMPRESA_CLASIFICADAS.items():
        assert clase in _CLASES_VALIDAS, f"Clase inválida para {clave}: {clase!r}"
        assert isinstance(motivo, str) and motivo.strip(), f"Motivo vacío para {clave}"


def _fuentes_python() -> list[pathlib.Path]:
    return sorted(RAIZ.rglob("*.py"))


def test_iso_g04_ningun_ayudante_de_propiedad_falla_abierto() -> None:
    """Impide (G-HLP-01) ayudantes de propiedad que fallan abiertos con getattr por defecto."""
    patron = 'getattr(obj, "company_id",'
    ofensores = [str(p) for p in _fuentes_python() if patron in p.read_text(encoding="utf-8")]
    assert not ofensores, f"Ficheros con {patron!r}: {ofensores}"


def test_iso_g05_ninguna_ruta_crea_filas_globales_desde_una_empresa() -> None:
    """Impide (OD-ISO-10) crear filas globales desde el contexto de una empresa."""
    patron = "None if body.global_scope"
    ofensores = [str(p) for p in _fuentes_python() if patron in p.read_text(encoding="utf-8")]
    assert not ofensores, f"Ficheros con {patron!r}: {ofensores}"
