"""API de reportes y auditoría (009).

Endpoints REST `/reporting/*` (solo lectura salvo exportaciones/jobs) con las
convenciones heredadas.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.modules.identity_access import authority
from app.modules.identity_access.models import User
from app.modules.reporting import service as reporting_service
from app.modules.reporting.models import ReportExport, ReportJob

router = APIRouter(prefix="/reporting", tags=["reportes"])


class ExportCreate(BaseModel):
    report_key: str = Field(min_length=1, max_length=64)
    format: str = "CSV"
    filters: dict | None = None


class JobCreate(BaseModel):
    report_key: str = Field(min_length=1, max_length=64)
    params: dict | None = None


def _exigir_capacidades_de_reporte(db: Session, user: User, ctx: CompanyContext, key: str) -> None:
    """Capacidades de origen del reporte (AD-5): sin ellas en ninguna empresa, PERMISSION_DENIED; solo en otra, COMPANY_SCOPE_FORBIDDEN; clave desconocida, 404 REPORT_NOT_FOUND."""
    for capacidad in reporting_service.capacidades_de_reporte(key):
        authority.require_capability(db, user=user, capability=capacidad, company_id=ctx.company_id)


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db), user: User = Depends(require_permission("dashboard", "view")), ctx: CompanyContext = Depends(get_company_context)):
    return reporting_service.dashboard(db, company_id=ctx.company_id, capacidades=authority.capabilities_in_company(db, user, ctx.company_id))


# --------------------------------------------------------------------------- #
# Reportes
# --------------------------------------------------------------------------- #
@router.get("/reports/{key}")
def get_report(key: str, period: str = "0", db: Session = Depends(get_db),
               user: User = Depends(require_permission("reportes", "view")), ctx: CompanyContext = Depends(get_company_context)):
    _exigir_capacidades_de_reporte(db, user, ctx, key)
    return reporting_service.report(db, company_id=ctx.company_id, key=key, period=period)


# --------------------------------------------------------------------------- #
# Exportación auditada
# --------------------------------------------------------------------------- #
@router.post("/exports", dependencies=[Depends(require_write_allowed)])
def create_export(body: ExportCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("reportes", "export")), ctx: CompanyContext = Depends(get_company_context)):
    _exigir_capacidades_de_reporte(db, actor, ctx, body.report_key)
    export = reporting_service.create_export(db, company_id=ctx.company_id, report_key=body.report_key,
                                             fmt=body.format, filters=body.filters, actor=str(actor.id))
    db.commit()
    db.refresh(export)
    return {"id": export.id, "report_key": export.report_key, "format": export.format,
            "file_ref": export.file_ref, "exported_by": export.exported_by, "status": export.status}


@router.get("/exports")
def list_exports(report_key: str | None = None, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("reportes", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(ReportExport).where(ReportExport.company_id == ctx.company_id)
    if report_key:
        query = query.where(ReportExport.report_key == report_key)
    items = db.execute(query.order_by(ReportExport.exported_at.desc())).scalars().all()
    return {"items": [{"id": e.id, "report_key": e.report_key, "format": e.format, "file_ref": e.file_ref,
                       "exported_by": e.exported_by, "exported_at": e.exported_at.isoformat() if e.exported_at else None,
                       "status": e.status} for e in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/exports/{export_id}/download")
def download_export(export_id: str, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("reportes", "export")), ctx: CompanyContext = Depends(get_company_context)):
    """Descarga el archivo real de una exportación del propio tenant (KAUD-002)."""
    clave = db.execute(select(ReportExport.report_key).where(ReportExport.id == export_id, ReportExport.company_id == ctx.company_id)).scalar_one_or_none()
    if clave is not None:
        _exigir_capacidades_de_reporte(db, user, ctx, clave)
    from app.modules.reporting import service as reporting_service

    filename, content = reporting_service.get_export_file(db, export_id=export_id, company_id=ctx.company_id)
    # Content-Disposition con nombre original; se sirve desde bytes (memoria).
    import io

    from starlette.responses import StreamingResponse

    media = "application/pdf" if filename.lower().endswith(".pdf") else "text/csv; charset=utf-8"
    return StreamingResponse(io.BytesIO(content), media_type=media,
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# --------------------------------------------------------------------------- #
# Trabajos asíncronos
# --------------------------------------------------------------------------- #
@router.post("/jobs", dependencies=[Depends(require_write_allowed)])
def create_job(body: JobCreate, db: Session = Depends(get_db),
               actor: User = Depends(require_permission("reportes", "export")), ctx: CompanyContext = Depends(get_company_context)):
    _exigir_capacidades_de_reporte(db, actor, ctx, body.report_key)
    job = reporting_service.create_job(db, company_id=ctx.company_id, report_key=body.report_key,
                                       params=body.params, actor=str(actor.id))
    db.commit()
    db.refresh(job)
    return {"id": job.id, "report_key": job.report_key, "status": job.status}


@router.post("/jobs/{job_id}/run", dependencies=[Depends(require_write_allowed)])
def run_job(job_id: str, db: Session = Depends(get_db),
            actor: User = Depends(require_permission("reportes", "export")), ctx: CompanyContext = Depends(get_company_context)):
    trabajo = db.get(ReportJob, job_id)
    if trabajo is not None and trabajo.company_id == ctx.company_id:
        _exigir_capacidades_de_reporte(db, actor, ctx, trabajo.report_key)
    job = reporting_service.run_job(db, company_id=ctx.company_id, job_id=job_id)
    db.commit()
    db.refresh(job)
    return {"id": job.id, "report_key": job.report_key, "status": job.status, "error": job.error,
            "result_ref": job.result_ref}


@router.get("/jobs")
def list_jobs(report_key: str | None = None, db: Session = Depends(get_db),
              user: User = Depends(require_permission("reportes", "view")), ctx: CompanyContext = Depends(get_company_context)):
    """Lista de trabajos asíncronos del propio tenant (KAUD-003)."""
    query = select(ReportJob).where(ReportJob.company_id == ctx.company_id)
    if report_key:
        query = query.where(ReportJob.report_key == report_key)
    items = db.execute(query.order_by(ReportJob.created_at.desc())).scalars().all()
    return {"items": [{"id": j.id, "report_key": j.report_key, "status": j.status, "error": j.error,
                       "result_ref": j.result_ref, "created_at": j.created_at.isoformat() if j.created_at else None}
                      for j in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("reportes", "view")), ctx: CompanyContext = Depends(get_company_context)):
    job = db.get(ReportJob, job_id)
    if not job or job.company_id != ctx.company_id:
        from app.core.errors import NotFoundError

        raise NotFoundError(code="JOB_NOT_FOUND", message="Trabajo no encontrado")
    return {"id": job.id, "report_key": job.report_key, "status": job.status, "error": job.error,
            "result_ref": job.result_ref}


# --------------------------------------------------------------------------- #
# Auditoría
# --------------------------------------------------------------------------- #
@router.get("/audit/timeline")
def get_audit_timeline(entity_type: str | None = None, action: str | None = None,
                       user_id: str | None = None, db: Session = Depends(get_db),
                       user: User = Depends(require_permission("audit", "view")), ctx: CompanyContext = Depends(get_company_context)):
    items = reporting_service.audit_timeline(db, company_id=ctx.company_id, entity_type=entity_type,
                                             action=action, user_id=user_id)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1}
