"""Prueba de arquitectura: toda lectura GET debe declarar capacidad o estar clasificada explícitamente.

AD-7 / READ-FR-12 y READ-FR-15: las lecturas amplias se clasifican explícitamente
en una de las clases cerradas (OD-READ-05) y el fallo es cerrado, no abierto
(OD-READ-06). Esta prueba falla en construcción para que el defecto no vuelva.

La fuente es el catálogo de operaciones existente, no un catálogo nuevo.
"""

from __future__ import annotations

from app.core.operaciones import catalogo_de_operaciones
from app.main import create_app

CLASES = frozenset({
    "PUBLIC_REFERENCE_DATA",
    "AUTHENTICATED_GLOBAL_REFERENCE_DATA",
    "TENANT_REFERENCE_DATA",
    "COMPANY_REFERENCE_DATA",
    "SELF_SCOPED_DATA",
})

LECTURAS_SIN_CAPACIDAD: dict[str, tuple[str, str]] = {
    "/": ("PUBLIC_REFERENCE_DATA", "raíz técnica sin datos"),
    "/api/v1/health/live": ("PUBLIC_REFERENCE_DATA", "sonda de vida sin datos"),
    "/api/v1/health/ready": ("PUBLIC_REFERENCE_DATA", "sonda de disponibilidad sin datos de negocio"),
    "/api/v1/setup/status": ("PUBLIC_REFERENCE_DATA", "estado de inicialización, necesario antes de que existan usuarios"),
    "/api/v1/license/status": ("PUBLIC_REFERENCE_DATA", "modo de licencia, necesario antes de iniciar sesión (FR-001-052)"),
    "/api/v1/auth/me": ("SELF_SCOPED_DATA", "identidad y autoridad propias"),
    "/api/v1/auth/mfa": ("SELF_SCOPED_DATA", "estado MFA propio"),
    "/api/v1/auth/sessions": ("SELF_SCOPED_DATA", "sesiones propias"),
    "/api/v1/auth/operations": ("AUTHENTICATED_GLOBAL_REFERENCE_DATA", "metadato de la API, igual para todos (ADR-018)"),
    "/api/v1/authority/company": ("SELF_SCOPED_DATA", "autoridad propia en la empresa activa (ADR-018)"),
    "/api/v1/organization/companies": ("SELF_SCOPED_DATA", "empresas a las que el usuario accede: autoridad del selector de empresa"),
    "/api/v1/notifications": ("SELF_SCOPED_DATA", "filas de destinatario; tipos sin capacidad excluidos (CL-047-05)"),
    "/api/v1/notifications/counts": ("SELF_SCOPED_DATA", "contadores propios (CL-047-05)"),
    "/api/v1/notifications/preferences": ("SELF_SCOPED_DATA", "preferencias propias (CL-047-05)"),
    "/api/v1/notifications/{notification_id}": ("SELF_SCOPED_DATA", "fila de destinatario (CL-047-05)"),
    "/api/v1/tasks": ("SELF_SCOPED_DATA", "candidato o asignado; scope=all exige tareas:view (CL-047-05)"),
    "/api/v1/tasks/{task_id}": ("SELF_SCOPED_DATA", "candidato o asignado, o tareas:view (CL-047-05)"),
    "/api/v1/tasks/priorities": ("COMPANY_REFERENCE_DATA", "catálogo de prioridades que necesita todo participante de una tarea"),
    "/api/v1/gobierno/modulo": ("AUTHENTICATED_GLOBAL_REFERENCE_DATA", "habilitación del módulo Gobierno por la licencia de la instalación (GOV-0-01)"),
    "/api/v1/gobierno/identidad/mi-contexto": ("SELF_SCOPED_DATA", "contexto institucional propio: cuenta, funcionario, cargo y autoridad del usuario (GOV-ORG-007)"),
}

CAPACIDAD_FIJADA: dict[str, list[str]] = {
    "/api/v1/purchasing/receipts/{receipt_id}/conciliacion": ["inventario:view"],
    "/api/v1/purchasing/receipts/{receipt_id}/confirmacion-inventario": ["inventario:view"],
    "/api/v1/reporting/dashboard": ["dashboard:view"],
    "/api/v1/reporting/reports/{key}": ["reportes:view"],
    "/api/v1/reporting/exports": ["reportes:view"],
    "/api/v1/reporting/exports/{export_id}/download": ["reportes:export"],
    "/api/v1/reporting/jobs": ["reportes:view"],
    "/api/v1/reporting/jobs/{job_id}": ["reportes:view"],
    "/api/v1/reporting/audit/timeline": ["audit:view"],
    "/api/v1/fiscal/legal-sources": ["fiscal:view"],
    "/api/v1/homologation/records": ["homologacion:view"],
}


def _lecturas() -> dict[str, dict]:
    """Construye la app una vez y devuelve las operaciones GET por ruta."""
    app = create_app()
    return {op["path"]: op for op in catalogo_de_operaciones(app) if op["method"] == "GET"}


def test_toda_lectura_declara_capacidad_o_esta_clasificada():
    """Cada GET con capabilities vacía debe estar clasificada en LECTURAS_SIN_CAPACIDAD."""
    culpables = sorted(
        path
        for path, op in _lecturas().items()
        if op["capabilities"] == [] and path not in LECTURAS_SIN_CAPACIDAD
    )
    assert culpables == [], (
        "Las siguientes lecturas GET no declaran capacidad y no están clasificadas en "
        "LECTURAS_SIN_CAPACIDAD; declare la capacidad de vista del módulo con "
        "require_permission o, si la lectura es deliberadamente amplia, clasifíquela en "
        "LECTURAS_SIN_CAPACIDAD con su motivo:\n  " + "\n  ".join(culpables)
    )


def test_las_lecturas_clasificadas_siguen_existiendo():
    """Cada entrada de LECTURAS_SIN_CAPACIDAD debe corresponder a un GET del catálogo."""
    lecturas = _lecturas()
    culpables = sorted(
        path for path in LECTURAS_SIN_CAPACIDAD if lecturas.get(path, {}).get("method") != "GET"
    )
    assert culpables == [], (
        "Las siguientes entradas de LECTURAS_SIN_CAPACIDAD ya no existen como GET en el "
        "catálogo; elimínelas de la lista:\n  " + "\n  ".join(culpables)
    )


def test_las_lecturas_clasificadas_no_declaran_capacidad():
    """Una lectura clasificada no debe declarar capacidades; eso escondería una lectura protegida."""
    lecturas = _lecturas()
    culpables = sorted(
        path
        for path in LECTURAS_SIN_CAPACIDAD
        if path in lecturas and lecturas[path]["capabilities"]
    )
    assert culpables == [], (
        "Las siguientes lecturas están clasificadas en LECTURAS_SIN_CAPACIDAD pero "
        "declaran capacidades; una clasificación obsoleta escondería una lectura "
        "protegida:\n  " + "\n  ".join(culpables)
    )


def test_las_clases_y_motivos_son_validos():
    """Cada clasificación debe usar una clase del catálogo cerrado y un motivo no vacío."""
    culpables = sorted(
        f"{path}: clase={clase!r}, motivo={motivo!r}"
        for path, (clase, motivo) in LECTURAS_SIN_CAPACIDAD.items()
        if clase not in CLASES or not isinstance(motivo, str) or not motivo.strip()
    )
    assert culpables == [], (
        "Las siguientes clasificaciones de LECTURAS_SIN_CAPACIDAD tienen una clase no "
        "válida o un motivo vacío:\n  " + "\n  ".join(culpables)
    )


def test_las_capacidades_fijadas_por_el_diseno():
    """Los GET con capacidad decidida por diseño deben declarar exactamente esa capacidad."""
    lecturas = _lecturas()
    diferencias = {}
    for path, esperado in CAPACIDAD_FIJADA.items():
        op = lecturas.get(path)
        if op is None:
            diferencias[path] = (esperado, "<GET no existe>")
        elif op["capabilities"] != esperado:
            diferencias[path] = (esperado, op["capabilities"])
    assert diferencias == {}, (
        "Las siguientes lecturas no declaran la capacidad fijada por el diseño:\n  "
        + "\n  ".join(
            f"{path}: esperado={esperado!r}, obtenido={obtenido!r}"
            for path, (esperado, obtenido) in sorted(diferencias.items())
        )
    )
