"""Servicio de actas de entrega (CTL-09)."""

from __future__ import annotations

import hashlib
import io
import json
from datetime import date, datetime
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError, PermissionDeniedError
from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentLink, DocumentVersion
from app.modules.documents.storage import generate_storage_key, get_storage
from app.modules.government.models import (
    GovernmentAct,
    GovernmentAssignment,
    GovernmentBank,
    GovernmentBankAccount,
    GovernmentEntity,
    GovernmentHandoverAct,
    GovernmentHandoverAnnex,
    GovernmentHandoverObservation,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentProcurementFile,
    GovernmentRenditionFile,
    GovernmentUnit,
)
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_identidad import _funcionario_del_actor
from app.shared.audit import record_audit
from app.shared.audit_catalog import catalog
from app.shared.clock import hoy_de_negocio, instante_actual

ANEXOS_CATALOGO: list[dict[str, Any]] = [
    {"codigo": "A11_1", "titulo": "Estado de cuentas (situación presupuestaria, financiera y patrimonial)", "obligatorio": True, "generable": True},
    {"codigo": "A11_2", "titulo": "Cargos existentes", "obligatorio": True, "generable": True},
    {"codigo": "A11_3", "titulo": "Inventario de bienes muebles e inmuebles", "obligatorio": True, "generable": False},
    {"codigo": "A11_4", "titulo": "Situación de la ejecución del plan operativo", "obligatorio": True, "generable": False},
    {"codigo": "A11_5", "titulo": "Índice general del archivo", "obligatorio": True, "generable": True},
    {"codigo": "A11_6", "titulo": "Otra información o documentación", "obligatorio": False, "generable": False},
]

ANEXOS_MUNICIPALES: list[dict[str, Any]] = [
    {"codigo": "A17_1", "titulo": "Situación del Tesoro municipal", "obligatorio": True, "generable": False},
    {"codigo": "A17_2", "titulo": "Ejecución del presupuesto de ingresos y egresos y derechos pendientes", "obligatorio": True, "generable": False},
    {"codigo": "A17_3", "titulo": "Situación de las cuentas municipales", "obligatorio": True, "generable": False},
    {"codigo": "A17_4", "titulo": "Inventario de terrenos ejidos y propios", "obligatorio": True, "generable": False},
    {"codigo": "A17_5", "titulo": "Ingresos por venta de terrenos", "obligatorio": True, "generable": False},
]


def _a_iso(valor: Any) -> str:
    if isinstance(valor, date) or isinstance(valor, datetime):
        return valor.isoformat()
    return str(valor)


def _json_nativo(d: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(d, default=_a_iso))


def _hash_canonico(d: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(d, sort_keys=True, separators=(",", ":"), default=_a_iso).encode("utf-8")
    ).hexdigest()


def _not_found() -> NotFoundError:
    return NotFoundError(code="GOV_HANDOVER_NOT_FOUND", message="Acta de entrega no encontrada.")


def _state_error(message: str) -> ConflictError:
    return ConflictError(code="GOV_HANDOVER_STATE", message=message)


def _obtener_asignacion(db: Session, ctx: CompanyContext, assignment_id: str) -> GovernmentAssignment:
    asignacion = db.scalar(
        select(GovernmentAssignment).where(
            GovernmentAssignment.id == assignment_id,
            GovernmentAssignment.company_id == ctx.company_id,
        )
    )
    if not asignacion or asignacion.status not in ("ACTIVO", "FINALIZADO", "REVOCADO"):
        raise KontrolError(
            code="GOV_HANDOVER_ASSIGNMENT_INVALID",
            message="Ocupación saliente no válida.",
            status_code=422,
        )
    return asignacion


def _snapshot_responsable(db: Session, ctx: CompanyContext, assignment_id: str) -> dict[str, str]:
    asignacion = _obtener_asignacion(db, ctx, assignment_id)
    oficial = db.scalar(select(GovernmentOfficial).where(GovernmentOfficial.id == asignacion.official_id))
    posicion = db.scalar(select(GovernmentPosition).where(GovernmentPosition.id == asignacion.position_id))
    unidad = db.scalar(select(GovernmentUnit).where(GovernmentUnit.id == posicion.unit_id)) if posicion else None
    return {
        "funcionario": oficial.nombre if oficial else "",
        "funcionario_codigo": oficial.codigo if oficial else "",
        "cargo": posicion.name if posicion else "",
        "cargo_codigo": posicion.code if posicion else "",
        "unidad": unidad.name if unidad else "",
        "unidad_codigo": unidad.code if unidad else "",
        "figura": asignacion.figura or "",
        "asignacion_codigo": asignacion.codigo or "",
    }


def _siguiente_codigo(db: Session, ctx: CompanyContext, anio: int) -> str:
    prefijo = f"AE-{anio}-"
    maximo = db.scalar(
        select(func.max(GovernmentHandoverAct.codigo)).where(
            GovernmentHandoverAct.company_id == ctx.company_id,
            GovernmentHandoverAct.codigo.like(f"{prefijo}%"),
        )
    )
    secuencia = 1
    if maximo:
        try:
            secuencia = int(maximo.split("-")[-1]) + 1
        except (ValueError, IndexError):
            secuencia = 1
    return f"{prefijo}{secuencia:04d}"


def _cargar_acta(db: Session, ctx: CompanyContext, acta_id: str, bloqueo: bool = False) -> GovernmentHandoverAct:
    consulta = select(GovernmentHandoverAct).where(
        GovernmentHandoverAct.id == acta_id,
        GovernmentHandoverAct.company_id == ctx.company_id,
    )
    if bloqueo:
        consulta = consulta.with_for_update()
    acta = db.scalar(consulta)
    if not acta:
        raise _not_found()
    return acta


def _anexos_del_acta(db: Session, acta_id: str) -> list[GovernmentHandoverAnnex]:
    return list(
        db.scalars(
            select(GovernmentHandoverAnnex)
            .where(GovernmentHandoverAnnex.act_id == acta_id)
            .order_by(GovernmentHandoverAnnex.codigo)
        )
    )


def _ente(db: Session, ctx: CompanyContext) -> GovernmentEntity | None:
    return db.scalar(select(GovernmentEntity).where(GovernmentEntity.company_id == ctx.company_id))


def _es_admin_nacional(db: Session, ctx: CompanyContext) -> bool:
    ente = _ente(db, ctx)
    return bool(ente and ente.nivel_territorial == "NACIONAL")


def _nivel_territorial(db: Session, ctx: CompanyContext) -> str | None:
    ente = _ente(db, ctx)
    return ente.nivel_territorial if ente else None


def _funcionario_valido(db: Session, ctx: CompanyContext, official_id: str) -> GovernmentOfficial | None:
    return db.scalar(
        select(GovernmentOfficial).where(
            GovernmentOfficial.id == official_id,
            GovernmentOfficial.company_id == ctx.company_id,
            GovernmentOfficial.estado == "ACTIVO",
        )
    )


def _asignacion_valida(
    db: Session,
    ctx: CompanyContext,
    assignment_id: str,
    official_id: str | None = None,
) -> GovernmentAssignment | None:
    consulta = select(GovernmentAssignment).where(
        GovernmentAssignment.id == assignment_id,
        GovernmentAssignment.company_id == ctx.company_id,
        GovernmentAssignment.status.in_(("ACTIVO", "FINALIZADO", "REVOCADO")),
    )
    if official_id:
        consulta = consulta.where(GovernmentAssignment.official_id == official_id)
    return db.scalar(consulta)


def _receptor_snapshot(db: Session, acta: GovernmentHandoverAct) -> dict[str, Any]:
    snap: dict[str, Any] = {
        "funcionario": acta.receptor.get("funcionario", ""),
        "funcionario_codigo": acta.receptor.get("funcionario_codigo", ""),
    }
    if acta.receptor_assignment_id:
        asignacion = db.scalar(
            select(GovernmentAssignment).where(GovernmentAssignment.id == acta.receptor_assignment_id)
        )
        if asignacion:
            posicion = db.scalar(select(GovernmentPosition).where(GovernmentPosition.id == asignacion.position_id))
            snap["cargo"] = posicion.name if posicion else ""
            snap["cargo_codigo"] = posicion.code if posicion else ""
    return snap


def _saliente_snapshot(db: Session, acta: GovernmentHandoverAct) -> dict[str, Any]:
    return acta.saliente


def _ficha_anexo(anexo: GovernmentHandoverAnnex) -> dict[str, Any]:
    resuelto = (
        (anexo.generable and anexo.incluir_generado)
        or bool(anexo.documento_ids)
        or (anexo.constancia or "").strip() != ""
    )
    return {
        "codigo": anexo.codigo,
        "titulo": anexo.titulo,
        "obligatorio": anexo.obligatorio,
        "generable": anexo.generable,
        "incluir_generado": anexo.incluir_generado,
        "documento_ids": anexo.documento_ids,
        "constancia": anexo.constancia,
        "resuelto": resuelto,
        "documentos_congelados": anexo.documentos,
    }


def _documentos_del_acta(db: Session, ctx: CompanyContext, acta_id: str) -> list[dict[str, str]]:
    filas = db.execute(
        select(DocumentLink.document_id, Document.title)
        .join(Document, Document.id == DocumentLink.document_id)
        .where(
            DocumentLink.company_id == ctx.company_id,
            DocumentLink.resource_type == "GovernmentHandoverAct",
            DocumentLink.resource_id == acta_id,
        )
    ).all()
    return [{"id": str(fila[0]), "nombre": fila[1] or ""} for fila in filas]


def _ficha(db: Session, ctx: CompanyContext, acta: GovernmentHandoverAct) -> dict[str, Any]:
    anexos = _anexos_del_acta(db, str(acta.id))
    ficha = {
        "id": str(acta.id),
        "codigo": acta.codigo,
        "version": acta.version,
        "estado": acta.estado,
        "ambito": acta.ambito,
        "unidad": None,
        "saliente": acta.saliente,
        "receptor": _receptor_snapshot(db, acta),
        "modalidad": acta.modalidad,
        "testigos": acta.testigos,
        "auditor": None,
        "motivo": acta.motivo,
        "fundamento": acta.fundamento,
        "lugar": acta.lugar,
        "fecha_corte": acta.fecha_corte.isoformat() if acta.fecha_corte else None,
        "anexos": [_ficha_anexo(anexo) for anexo in anexos],
        "anexos_pendientes": [
            anexo.codigo
            for anexo in anexos
            if anexo.obligatorio
            and not (
                (anexo.generable and anexo.incluir_generado)
                or bool(anexo.documento_ids)
                or (anexo.constancia or "").strip() != ""
            )
        ],
        "documentos_del_acta": _documentos_del_acta(db, ctx, str(acta.id)),
        "fecha_suscripcion": acta.fecha_suscripcion.isoformat() if acta.fecha_suscripcion else None,
        "errores_deficiencias": acta.errores_deficiencias,
        "suscrita_por": acta.suscrita_por,
        "suscrita_en": acta.suscrita_en.isoformat() if acta.suscrita_en else None,
        "snapshot_sha256": acta.snapshot_sha256,
        "informe": (
            {
                "sha256": acta.informe_sha256,
                "bytes": acta.informe_bytes,
            }
            if acta.informe_sha256
            else None
        ),
        "remision_uai_fecha": acta.remision_uai_fecha.isoformat() if acta.remision_uai_fecha else None,
        "observaciones": [],
        "verificacion": None,
    }

    if acta.unit_id:
        unidad = db.scalar(select(GovernmentUnit).where(GovernmentUnit.id == acta.unit_id))
        ficha["unidad"] = unidad.name if unidad else None

    if acta.auditor_official_id:
        auditor = db.scalar(
            select(GovernmentOfficial).where(GovernmentOfficial.id == acta.auditor_official_id)
        )
        if auditor:
            ficha["auditor"] = {"funcionario": auditor.nombre, "codigo": auditor.codigo}

    observaciones = list(
        db.scalars(
            select(GovernmentHandoverObservation)
            .where(GovernmentHandoverObservation.act_id == str(acta.id))
            .order_by(GovernmentHandoverObservation.fecha)
        )
    )
    ficha["observaciones"] = [
        {
            "fecha": obs.fecha.isoformat(),
            "texto": obs.texto,
            "registrada_por": obs.registrada_por,
            "registrada_en": obs.registrada_en.isoformat(),
        }
        for obs in observaciones
    ]

    if acta.verificacion_numero:
        ficha["verificacion"] = {
            "numero": acta.verificacion_numero,
            "fecha": acta.verificacion_fecha.isoformat() if acta.verificacion_fecha else None,
            "resultado": acta.verificacion_resultado,
            "fundamento": acta.verificacion_fundamento,
            "verificada_por": acta.verificada_por,
            "verificada_en": acta.verificada_en.isoformat() if acta.verificada_en else None,
        }

    return ficha


def _ficha_resumida(db: Session, ctx: CompanyContext, acta: GovernmentHandoverAct) -> dict[str, Any]:
    unidad = None
    if acta.unit_id:
        _unidad = db.scalar(select(GovernmentUnit).where(GovernmentUnit.id == acta.unit_id))
        unidad = _unidad.name if _unidad else None
    return {
        "id": str(acta.id),
        "codigo": acta.codigo,
        "estado": acta.estado,
        "ambito": acta.ambito,
        "unidad": unidad,
        "saliente": acta.saliente,
        "receptor": _receptor_snapshot(db, acta),
        "fecha_corte": acta.fecha_corte.isoformat() if acta.fecha_corte else None,
        "fecha_suscripcion": acta.fecha_suscripcion.isoformat() if acta.fecha_suscripcion else None,
    }


def _validar_testigos(
    db: Session,
    ctx: CompanyContext,
    modalidad: str,
    testigos: list[dict[str, Any]],
    auditor_official_id: str | None,
) -> None:
    if modalidad == "LEVANTADA_POR_RECEPTOR":
        if len(testigos) != 2:
            raise KontrolError(
                code="GOV_HANDOVER_WITNESSES_REQUIRED",
                message="La modalidad por receptor exige exactamente dos testigos.",
                status_code=422,
            )
        for testigo in testigos:
            nombre = str(testigo.get("nombre", ""))
            documento = str(testigo.get("documento", ""))
            if not (3 <= len(nombre) <= 120) or not (3 <= len(documento) <= 20):
                raise KontrolError(
                    code="GOV_HANDOVER_WITNESSES_REQUIRED",
                    message="Los testigos deben tener nombre (3..120) y documento (3..20).",
                    status_code=422,
                )
        if not auditor_official_id or not _funcionario_valido(db, ctx, auditor_official_id):
            raise KontrolError(
                code="GOV_HANDOVER_WITNESSES_REQUIRED",
                message="La modalidad por receptor exige un auditor del ente.",
                status_code=422,
            )


def _validar_datos_base(
    db: Session,
    ctx: CompanyContext,
    *,
    fecha_corte: date,
    motivo: str,
    fundamento: str,
    lugar: str,
    receptor_official_id: str,
    receptor_assignment_id: str | None,
    assigment_official_id: str,
    modalidad: str,
    testigos: list[dict[str, Any]],
    auditor_official_id: str | None,
) -> None:
    if not (10 <= len(motivo) <= 1000):
        raise KontrolError(
            code="GOV_HANDOVER_ASSIGNMENT_INVALID",
            message="Motivo debe tener entre 10 y 1000 caracteres.",
            status_code=422,
        )
    if not (10 <= len(fundamento) <= 1000):
        raise KontrolError(
            code="GOV_HANDOVER_RECEIVER_INVALID",
            message="Fundamento debe tener entre 10 y 1000 caracteres.",
            status_code=422,
        )
    if not (2 <= len(lugar) <= 200):
        raise KontrolError(
            code="GOV_HANDOVER_ASSIGNMENT_INVALID",
            message="Lugar debe tener entre 2 y 200 caracteres.",
            status_code=422,
        )
    if fecha_corte > hoy_de_negocio():
        raise KontrolError(
            code="GOV_HANDOVER_CUTOFF_INVALID",
            message="La fecha de corte no puede ser futura.",
            status_code=422,
        )
    receptor = _funcionario_valido(db, ctx, receptor_official_id)
    if not receptor:
        raise KontrolError(
            code="GOV_HANDOVER_RECEIVER_INVALID",
            message="Receptor no válido.",
            status_code=422,
        )
    if receptor_official_id == assigment_official_id:
        raise KontrolError(
            code="GOV_HANDOVER_RECEIVER_INVALID",
            message="El receptor no puede ser el funcionario saliente.",
            status_code=422,
        )
    if receptor_assignment_id and not _asignacion_valida(
        db, ctx, receptor_assignment_id, receptor_official_id
    ):
        raise KontrolError(
            code="GOV_HANDOVER_RECEIVER_INVALID",
            message="La ocupación del receptor no es válida.",
            status_code=422,
        )
    _validar_testigos(db, ctx, modalidad, testigos, auditor_official_id)


def _estado_vigente(asignacion: GovernmentAssignment, corte: date) -> bool:
    desde = asignacion.desde
    if not desde or desde > corte:
        return False
    fin_efectivo = asignacion.fin_efectivo or asignacion.hasta
    return fin_efectivo is None or fin_efectivo >= corte


def _asignacion_al_corte(db: Session, position_id: str, corte: date) -> GovernmentAssignment | None:
    asignaciones = list(
        db.scalars(
            select(GovernmentAssignment)
            .where(
                GovernmentAssignment.position_id == position_id,
                GovernmentAssignment.status.in_(("ACTIVO", "FINALIZADO", "REVOCADO")),
                GovernmentAssignment.desde <= corte,
            )
            .order_by(GovernmentAssignment.desde.desc())
        )
    )
    for asignacion in asignaciones:
        if _estado_vigente(asignacion, corte):
            return asignacion
    return None


def _contenido_anexo(db: Session, ctx: CompanyContext, acta: GovernmentHandoverAct, codigo: str) -> dict[str, Any]:
    corte = acta.fecha_corte
    empresa = ctx.company_id
    resultado: dict[str, Any] = {}
    truncado = False

    if codigo == "A11_1":
        cuentas = []
        filas = db.scalars(
            select(GovernmentBankAccount)
            .join(GovernmentBank, GovernmentBank.id == GovernmentBankAccount.bank_id)
            .where(
                GovernmentBankAccount.company_id == empresa,
                GovernmentBankAccount.estado != "BORRADOR",
                GovernmentBankAccount.vigente_desde <= corte,
            )
            .order_by(GovernmentBankAccount.codigo)
        )
        for cuenta in filas:
            if cuenta.fecha_cierre is not None and cuenta.fecha_cierre <= corte:
                continue
            banco = db.scalar(select(GovernmentBank).where(GovernmentBank.id == cuenta.bank_id))
            cuentas.append(
                {
                    "codigo": cuenta.codigo,
                    "denominacion": cuenta.denominacion,
                    "banco": banco.nombre if banco else "",
                    "tipo": cuenta.tipo,
                    "numero": cuenta.numero,
                    "moneda": cuenta.moneda,
                    "estado": cuenta.estado,
                }
            )
            if len(cuentas) >= 500:
                cuentas = cuentas[:500]
                truncado = True
                break

        expedientes = []
        for exp in db.scalars(
            select(GovernmentRenditionFile)
            .where(
                GovernmentRenditionFile.company_id == empresa,
                GovernmentRenditionFile.periodo_desde <= corte,
            )
            .order_by(GovernmentRenditionFile.codigo)
        ):
            expedientes.append(
                {
                    "codigo": exp.codigo,
                    "numero_version": exp.numero_version,
                    "denominacion": exp.denominacion,
                    "periodo_desde": exp.periodo_desde.isoformat() if exp.periodo_desde else None,
                    "periodo_hasta": exp.periodo_hasta.isoformat() if exp.periodo_hasta else None,
                    "estado": exp.estado,
                }
            )
            if len(expedientes) >= 500:
                expedientes = expedientes[:500]
                truncado = True
                break
        resultado = {"cuentas_bancarias": cuentas, "expedientes_de_cuenta": expedientes}

    elif codigo == "A11_2":
        consulta = select(GovernmentPosition).where(
            GovernmentPosition.company_id == empresa,
            GovernmentPosition.status != "BORRADOR",
        )
        if acta.ambito == "UNIDAD" and acta.unit_id:
            consulta = consulta.where(GovernmentPosition.unit_id == acta.unit_id)
        cargos = []
        total = 0
        ocupados = 0
        for posicion in db.scalars(consulta.order_by(GovernmentPosition.code)):
            total += 1
            asignacion = _asignacion_al_corte(db, str(posicion.id), corte)
            ocupante = None
            figura = None
            if asignacion:
                ocupados += 1
                oficial = db.scalar(
                    select(GovernmentOfficial).where(GovernmentOfficial.id == asignacion.official_id)
                )
                ocupante = oficial.nombre if oficial else None
                figura = asignacion.figura
            cargos.append(
                {
                    "codigo": posicion.code,
                    "denominacion": posicion.name,
                    "unidad": acta.unit_id or "",
                    "ocupante": ocupante,
                    "figura": figura,
                }
            )
            if len(cargos) >= 500:
                cargos = cargos[:500]
                truncado = True
                break
        resultado = {
            "cargos": cargos,
            "total": total,
            "ocupados": ocupados,
            "vacantes": total - ocupados,
        }

    elif codigo == "A11_5":
        expedientes_contratacion = []
        consulta_contratacion = select(GovernmentProcurementFile).where(
            GovernmentProcurementFile.company_id == empresa,
            GovernmentProcurementFile.fecha_inicio <= corte,
            GovernmentProcurementFile.status != "DESCARTADO",
        )
        if acta.ambito == "UNIDAD" and acta.unit_id:
            consulta_contratacion = consulta_contratacion.where(
                GovernmentProcurementFile.unidad_id == acta.unit_id
            )
        for contratacion in db.scalars(
            consulta_contratacion.order_by(GovernmentProcurementFile.numero)
        ):
            expedientes_contratacion.append(
                {
                    "numero": contratacion.numero,
                    "objeto": contratacion.objeto,
                    "estado": contratacion.status,
                    "fecha_inicio": (
                        contratacion.fecha_inicio.isoformat()
                        if contratacion.fecha_inicio
                        else None
                    ),
                }
            )
            if len(expedientes_contratacion) >= 500:
                expedientes_contratacion = expedientes_contratacion[:500]
                truncado = True
                break

        actos = []
        consulta_actos = select(GovernmentAct).where(
            GovernmentAct.company_id == empresa,
            GovernmentAct.status != "BORRADOR",
            GovernmentAct.fecha <= corte,
        )
        if acta.ambito == "UNIDAD":
            ids_cargos = []
            for posicion in db.scalars(
                select(GovernmentPosition).where(
                    GovernmentPosition.company_id == empresa,
                    GovernmentPosition.unit_id == acta.unit_id,
                )
            ):
                ids_cargos.append(str(posicion.id))
            if ids_cargos:
                consulta_actos = consulta_actos.where(GovernmentAct.cargo_id.in_(ids_cargos))
            else:
                consulta_actos = consulta_actos.where(GovernmentAct.cargo_id.is_(None))
        for acto in db.scalars(consulta_actos.order_by(GovernmentAct.numero)):
            actos.append(
                {
                    "tipo": acto.tipo,
                    "numero": acto.numero,
                    "fecha": acto.fecha.isoformat() if acto.fecha else None,
                    "estado": acto.status,
                }
            )
            if len(actos) >= 500:
                actos = actos[:500]
                truncado = True
                break

        expedientes_cuenta = []
        for exp in db.scalars(
            select(GovernmentRenditionFile)
            .where(
                GovernmentRenditionFile.company_id == empresa,
                GovernmentRenditionFile.periodo_desde <= corte,
            )
            .order_by(GovernmentRenditionFile.codigo)
        ):
            expedientes_cuenta.append(
                {
                    "codigo": exp.codigo,
                    "numero_version": exp.numero_version,
                    "estado": exp.estado,
                }
            )
            if len(expedientes_cuenta) >= 500:
                expedientes_cuenta = expedientes_cuenta[:500]
                truncado = True
                break

        resultado = {
            "expedientes_contratacion": expedientes_contratacion,
            "actos": actos,
            "expedientes_de_cuenta": expedientes_cuenta,
        }

    if truncado:
        resultado["truncado"] = True
    return resultado


def _crear(
    db: Session,
    ctx: CompanyContext,
    *,
    assignment_id: str,
    receptor_official_id: str,
    receptor_assignment_id: str | None,
    modalidad: str,
    testigos: list[dict[str, Any]],
    auditor_official_id: str | None,
    motivo: str,
    fundamento: str,
    lugar: str,
    fecha_corte: date,
) -> GovernmentHandoverAct:
    asignacion = _obtener_asignacion(db, ctx, assignment_id)
    if fecha_corte < asignacion.desde:
        raise KontrolError(
            code="GOV_HANDOVER_CUTOFF_INVALID",
            message="La fecha de corte es anterior a la vigencia de la ocupación.",
            status_code=422,
        )
    if fecha_corte > hoy_de_negocio():
        raise KontrolError(
            code="GOV_HANDOVER_CUTOFF_INVALID",
            message="La fecha de corte no puede ser futura.",
            status_code=422,
        )

    _validar_datos_base(
        db,
        ctx,
        fecha_corte=fecha_corte,
        motivo=motivo,
        fundamento=fundamento,
        lugar=lugar,
        receptor_official_id=receptor_official_id,
        receptor_assignment_id=receptor_assignment_id,
        assigment_official_id=str(asignacion.official_id),
        modalidad=modalidad,
        testigos=testigos or [],
        auditor_official_id=auditor_official_id,
    )

    existente = db.scalar(
        select(GovernmentHandoverAct.id).where(
            GovernmentHandoverAct.company_id == ctx.company_id,
            GovernmentHandoverAct.assignment_id == assignment_id,
        )
    )
    if existente:
        raise ConflictError(code="GOV_HANDOVER_DUPLICATE", message="Ya existe un acta para esa ocupación.")

    posicion = db.scalar(
        select(GovernmentPosition).where(GovernmentPosition.id == asignacion.position_id)
    )
    receptor = _funcionario_valido(db, ctx, receptor_official_id)
    if receptor is None:
        raise KontrolError(
            code="GOV_HANDOVER_RECEIVER_INVALID",
            message="Receptor no válido.",
            status_code=422,
        )
    saliente = _snapshot_responsable(db, ctx, assignment_id)
    ambito = "ENTE" if asignacion.maxima_autoridad else "UNIDAD"
    acta = GovernmentHandoverAct(
        company_id=ctx.company_id,
        codigo=_siguiente_codigo(db, ctx, fecha_corte.year),
        estado="BORRADOR",
        ambito=ambito,
        unit_id=posicion.unit_id if posicion else None,
        assignment_id=assignment_id,
        saliente=saliente,
        receptor_official_id=receptor_official_id,
        receptor_assignment_id=receptor_assignment_id,
        receptor={
            "funcionario": receptor.nombre,
            "funcionario_codigo": receptor.codigo,
        },
        modalidad=modalidad,
        testigos=testigos or [],
        auditor_official_id=auditor_official_id,
        motivo=motivo,
        fundamento=fundamento,
        lugar=lugar,
        fecha_corte=fecha_corte,
    )
    db.add(acta)
    try:
        db.flush()
    except IntegrityError as err:
        constraint_name = getattr(getattr(err.orig, "diag", None), "constraint_name", None)
        if not constraint_name:
            constraint_name = (
                "uq_gov_handover_acts_company_assignment"
                if "uq_gov_handover_acts_company_assignment" in str(err.orig)
                else None
            )
        if constraint_name == "uq_gov_handover_acts_company_assignment":
            raise ConflictError(
                code="GOV_HANDOVER_DUPLICATE",
                message="Ya existe un acta para esa ocupación.",
            ) from err
        raise

    catalogo = list(ANEXOS_CATALOGO)
    ente = _ente(db, ctx)
    if ente and ente.nivel_territorial == "MUNICIPAL" and ambito == "ENTE":
        catalogo.extend(ANEXOS_MUNICIPALES)
    for item in catalogo:
        anexo = GovernmentHandoverAnnex(
            company_id=ctx.company_id,
            act_id=str(acta.id),
            codigo=item["codigo"],
            titulo=item["titulo"],
            obligatorio=item["obligatorio"],
            generable=item["generable"],
            incluir_generado=item["generable"],
            documento_ids=[],
            constancia=None,
        )
        db.add(anexo)
    db.flush()

    record_audit(
        db,
        action="GOV_HANDOVER_ACT_CREATED",
        entity_type="GovernmentHandoverAct",
        entity_id=str(acta.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": acta.codigo, "ambito": acta.ambito, "fecha_corte": acta.fecha_corte.isoformat()},
    )
    return acta


def _actualizar(
    db: Session,
    ctx: CompanyContext,
    acta: GovernmentHandoverAct,
    *,
    version: int,
    motivo: str,
    fundamento: str,
    lugar: str,
    fecha_corte: date,
    testigos: list[dict[str, Any]],
    auditor_official_id: str | None,
    receptor_official_id: str,
    receptor_assignment_id: str | None,
    modalidad: str,
) -> GovernmentHandoverAct:
    if acta.version != version:
        raise ConflictError(code="VERSION_CONFLICT", message="La versión no coincide.")
    if acta.estado != "BORRADOR":
        raise _state_error("Solo se puede editar un acta en BORRADOR.")
    asignacion = _obtener_asignacion(db, ctx, str(acta.assignment_id))
    _validar_datos_base(
        db,
        ctx,
        fecha_corte=fecha_corte,
        motivo=motivo,
        fundamento=fundamento,
        lugar=lugar,
        receptor_official_id=receptor_official_id,
        receptor_assignment_id=receptor_assignment_id,
        assigment_official_id=str(asignacion.official_id),
        modalidad=modalidad,
        testigos=testigos or [],
        auditor_official_id=auditor_official_id,
    )
    if fecha_corte < asignacion.desde:
        raise KontrolError(
            code="GOV_HANDOVER_CUTOFF_INVALID",
            message="La fecha de corte es anterior a la vigencia de la ocupación.",
            status_code=422,
        )
    receptor = _funcionario_valido(db, ctx, receptor_official_id)
    if receptor is None:
        raise KontrolError(
            code="GOV_HANDOVER_RECEIVER_INVALID",
            message="Receptor no válido.",
            status_code=422,
        )
    acta.motivo = motivo
    acta.fundamento = fundamento
    acta.lugar = lugar
    acta.fecha_corte = fecha_corte
    acta.testigos = testigos or []
    acta.auditor_official_id = auditor_official_id
    acta.receptor_official_id = receptor_official_id
    acta.receptor_assignment_id = receptor_assignment_id
    acta.receptor = {
        "funcionario": receptor.nombre,
        "funcionario_codigo": receptor.codigo,
    }
    acta.modalidad = modalidad
    acta.version += 1
    db.flush()
    record_audit(
        db,
        action="GOV_HANDOVER_ACT_UPDATED",
        entity_type="GovernmentHandoverAct",
        entity_id=str(acta.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": acta.codigo},
    )
    return acta


def _actualizar_anexo(
    db: Session,
    ctx: CompanyContext,
    acta: GovernmentHandoverAct,
    codigo: str,
    *,
    incluir_generado: bool | None,
    documento_ids: list[str] | None,
    constancia: str | None,
) -> GovernmentHandoverAct:
    if acta.estado != "BORRADOR":
        raise _state_error("Solo se pueden editar anexos en BORRADOR.")
    anexo = db.scalar(
        select(GovernmentHandoverAnnex).where(
            GovernmentHandoverAnnex.act_id == str(acta.id),
            GovernmentHandoverAnnex.codigo == codigo,
        )
    )
    if not anexo:
        raise _not_found()

    if incluir_generado is not None:
        if incluir_generado and not anexo.generable:
            raise KontrolError(
                code="GOV_HANDOVER_ANNEX_INVALID",
                message="El anexo no es generable.",
                status_code=422,
            )
        anexo.incluir_generado = incluir_generado

    if documento_ids is not None:
        for documento_id in documento_ids:
            link = db.scalar(
                select(DocumentLink.id).where(
                    DocumentLink.company_id == ctx.company_id,
                    DocumentLink.document_id == documento_id,
                    DocumentLink.resource_type == "GovernmentHandoverAct",
                    DocumentLink.resource_id == str(acta.id),
                )
            )
            if not link:
                raise KontrolError(
                    code="GOV_HANDOVER_ANNEX_INVALID",
                    message="El documento no está vinculado al acta.",
                    status_code=422,
                )
        anexo.documento_ids = documento_ids

    if constancia is not None:
        if len(constancia.strip()) < 10:
            raise KontrolError(
                code="GOV_HANDOVER_ANNEX_INVALID",
                message="La constancia debe tener al menos 10 caracteres.",
                status_code=422,
            )
        anexo.constancia = constancia

    db.flush()
    record_audit(
        db,
        action="GOV_HANDOVER_ACT_ANNEX_RESOLVED",
        entity_type="GovernmentHandoverAct",
        entity_id=str(acta.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": acta.codigo, "anexo": codigo},
    )
    return acta


def _pdf_desde_acta(acta: GovernmentHandoverAct, anexos: list[GovernmentHandoverAnnex]) -> bytes:
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    elementos: list[Any] = []
    elementos.append(Paragraph(escape(f"Acta de entrega {acta.codigo}"), styles["Title"]))
    elementos.append(Spacer(1, 6 * mm))
    elementos.append(Paragraph(escape(f"{acta.lugar}, {acta.fecha_corte.isoformat()}"), styles["Normal"]))
    elementos.append(Spacer(1, 6 * mm))
    elementos.append(Paragraph("Órgano / dependencia", styles["Heading2"]))
    elementos.append(Paragraph(escape(str(acta.saliente.get("unidad", ""))), styles["Normal"]))
    elementos.append(Spacer(1, 3 * mm))
    elementos.append(Paragraph("Quien entrega", styles["Heading2"]))
    elementos.append(Paragraph(escape(str(acta.saliente.get("funcionario", ""))), styles["Normal"]))
    elementos.append(Spacer(1, 3 * mm))
    elementos.append(Paragraph("Quien recibe", styles["Heading2"]))
    elementos.append(Paragraph(escape(str(acta.receptor.get("funcionario", ""))), styles["Normal"]))
    elementos.append(Spacer(1, 3 * mm))
    elementos.append(Paragraph(f"Modalidad: {escape(acta.modalidad)}", styles["Normal"]))
    if acta.testigos:
        testigos = ", ".join(str(t.get("nombre", "")) for t in acta.testigos)
        elementos.append(Paragraph(f"Testigos: {escape(testigos)}", styles["Normal"]))
    elementos.append(Spacer(1, 6 * mm))
    elementos.append(Paragraph("Motivo", styles["Heading2"]))
    elementos.append(Paragraph(escape(acta.motivo), styles["Normal"]))
    elementos.append(Paragraph("Fundamento", styles["Heading2"]))
    elementos.append(Paragraph(escape(acta.fundamento), styles["Normal"]))
    elementos.append(Spacer(1, 6 * mm))
    elementos.append(Paragraph("Relación de anexos", styles["Heading2"]))
    filas = [["Anexo", "Resolución"]]
    for anexo in anexos:
        if anexo.generable and anexo.incluir_generado:
            forma = "Generado"
        elif anexo.documento_ids:
            forma = "Documentos"
        elif anexo.constancia:
            forma = f"Constancia art. 19: {anexo.constancia}"
        else:
            forma = "Pendiente"
        filas.append([anexo.codigo, forma])
    tabla = Table(filas, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementos.append(tabla)
    elementos.append(Spacer(1, 6 * mm))
    if acta.errores_deficiencias:
        elementos.append(Paragraph("Errores y deficiencias", styles["Heading2"]))
        elementos.append(Paragraph(escape(acta.errores_deficiencias), styles["Normal"]))
    if acta.snapshot_sha256:
        elementos.append(Paragraph(f"Huella: {acta.snapshot_sha256}", styles["Normal"]))
        elementos.append(
            Paragraph(
                "La huella SHA-256 prueba integridad; no es una firma electrónica.",
                styles["Normal"],
            )
        )
    doc.build(elementos)
    return buffer.getvalue()


def _suscribir(
    db: Session,
    ctx: CompanyContext,
    acta: GovernmentHandoverAct,
    *,
    fecha_suscripcion: date,
    errores_deficiencias: str | None,
) -> GovernmentHandoverAct:
    if acta.estado != "BORRADOR":
        raise _state_error("Solo se puede suscribir un acta en BORRADOR.")
    if fecha_suscripcion < acta.fecha_corte or fecha_suscripcion > hoy_de_negocio():
        raise KontrolError(
            code="GOV_HANDOVER_CUTOFF_INVALID",
            message="La fecha de suscripción debe estar entre la fecha de corte y hoy.",
            status_code=422,
        )
    if errores_deficiencias and len(errores_deficiencias) > 2000:
        raise KontrolError(
            code="GOV_HANDOVER_CUTOFF_INVALID",
            message="Los errores y deficiencias no pueden superar 2000 caracteres.",
            status_code=422,
        )

    anexos = _anexos_del_acta(db, str(acta.id))
    pendientes = [
        anexo.codigo
        for anexo in anexos
        if anexo.obligatorio
        and not (
            (anexo.generable and anexo.incluir_generado)
            or bool(anexo.documento_ids)
            or (anexo.constancia or "").strip() != ""
        )
    ]
    if pendientes:
        raise KontrolError(
            code="GOV_HANDOVER_ANNEXES_PENDING",
            message=f"Faltan anexos obligatorios: {', '.join(pendientes)}.",
            details={"anexos": pendientes},
            status_code=422,
        )

    for anexo in anexos:
        anexo.contenido = _contenido_anexo(db, ctx, acta, anexo.codigo) if anexo.incluir_generado else None
        documentos = []
        for documento_id in anexo.documento_ids or []:
            version = db.scalar(
                select(DocumentVersion)
                .where(
                    DocumentVersion.document_id == documento_id,
                    DocumentVersion.company_id == ctx.company_id,
                )
                .order_by(DocumentVersion.version_number.desc())
            )
            if version:
                documentos.append(
                    {
                        "documento_id": documento_id,
                        "version_id": str(version.id),
                        "sha256": version.sha256,
                    }
                )
        anexo.documentos = documentos
    db.flush()

    cabecera = _ficha(db, ctx, acta)
    snapshot = {
        "acta": cabecera,
        "anexos": [
            {
                "codigo": anexo.codigo,
                "titulo": anexo.titulo,
                "obligatorio": anexo.obligatorio,
                "contenido": anexo.contenido,
                "documentos": anexo.documentos,
                "constancia": anexo.constancia,
            }
            for anexo in anexos
        ],
        "fecha_suscripcion": fecha_suscripcion.isoformat(),
        "errores_deficiencias": errores_deficiencias,
    }
    acta.snapshot = snapshot
    acta.snapshot_sha256 = _hash_canonico(snapshot)

    pdf_bytes = _pdf_desde_acta(acta, anexos)
    pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    storage = get_storage()
    storage_key = generate_storage_key(ctx.company_id)
    size, sha = storage.put(storage_key, io.BytesIO(pdf_bytes))
    if sha != pdf_sha256 or not storage.verify(storage_key, sha):
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            status_code=500,
            message="El informe almacenado no coincide con su huella",
        )
    acta.informe_storage_key = storage_key
    acta.informe_sha256 = pdf_sha256
    acta.informe_bytes = size
    acta.fecha_suscripcion = fecha_suscripcion
    acta.errores_deficiencias = errores_deficiencias
    acta.suscrita_por = str(ctx.user_id or "")
    acta.suscrita_en = instante_actual()
    acta.estado = "SUSCRITA"
    db.flush()

    record_audit(
        db,
        action="GOV_HANDOVER_ACT_SUBSCRIBED",
        entity_type="GovernmentHandoverAct",
        entity_id=str(acta.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": acta.codigo, "snapshot_sha256": acta.snapshot_sha256},
    )
    return acta


def _remitir(db: Session, ctx: CompanyContext, acta: GovernmentHandoverAct, *, fecha: date) -> GovernmentHandoverAct:
    if acta.estado not in ("SUSCRITA", "VERIFICADA"):
        raise _state_error("Solo se puede remitir un acta suscrita o verificada.")
    if acta.remision_uai_fecha is not None:
        raise _state_error("El acta ya fue remitida.")
    if acta.fecha_suscripcion is None:
        raise _state_error("El acta no tiene fecha de suscripción.")
    if fecha < acta.fecha_suscripcion or fecha > hoy_de_negocio():
        raise KontrolError(
            code="GOV_HANDOVER_CUTOFF_INVALID",
            message="La fecha de remisión debe estar entre la suscripción y hoy.",
            status_code=422,
        )
    acta.remision_uai_fecha = fecha
    acta.remision_uai_registrada_por = str(ctx.user_id or "")
    db.flush()
    record_audit(
        db,
        action="GOV_HANDOVER_ACT_REMITTED",
        entity_type="GovernmentHandoverAct",
        entity_id=str(acta.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": acta.codigo, "fecha": fecha.isoformat()},
    )
    return acta


def _observar(db: Session, ctx: CompanyContext, acta: GovernmentHandoverAct, *, fecha: date, texto: str) -> GovernmentHandoverAct:
    if acta.estado not in ("SUSCRITA", "VERIFICADA"):
        raise _state_error("Solo se pueden observar actas suscritas o verificadas.")
    if acta.fecha_suscripcion is None:
        raise _state_error("El acta no tiene fecha de suscripción.")
    if fecha < acta.fecha_suscripcion or fecha > hoy_de_negocio():
        raise KontrolError(
            code="GOV_HANDOVER_CUTOFF_INVALID",
            message="La fecha de la observación debe estar entre la suscripción y hoy.",
            status_code=422,
        )
    if not (10 <= len(texto) <= 2000):
        raise KontrolError(
            code="GOV_HANDOVER_ASSIGNMENT_INVALID",
            message="El texto de la observación debe tener entre 10 y 2000 caracteres.",
            status_code=422,
        )
    observacion = GovernmentHandoverObservation(
        company_id=ctx.company_id,
        act_id=str(acta.id),
        fecha=fecha,
        texto=texto,
        registrada_por=str(ctx.user_id or ""),
        registrada_en=instante_actual(),
    )
    db.add(observacion)
    db.flush()
    record_audit(
        db,
        action="GOV_HANDOVER_ACT_OBSERVED",
        entity_type="GovernmentHandoverAct",
        entity_id=str(acta.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": acta.codigo, "fecha": fecha.isoformat()},
    )
    return acta


def _verificar(
    db: Session,
    ctx: CompanyContext,
    acta: GovernmentHandoverAct,
    *,
    numero: str,
    fecha: date,
    resultado: str,
    fundamento: str,
) -> GovernmentHandoverAct:
    if acta.estado != "SUSCRITA":
        raise _state_error("Solo se puede verificar un acta suscrita.")
    if not (1 <= len(numero) <= 50):
        raise KontrolError(
            code="GOV_HANDOVER_ASSIGNMENT_INVALID",
            message="El número debe tener entre 1 y 50 caracteres.",
            status_code=422,
        )
    if acta.fecha_suscripcion is None:
        raise _state_error("El acta no tiene fecha de suscripción.")
    if fecha < acta.fecha_suscripcion or fecha > hoy_de_negocio():
        raise KontrolError(
            code="GOV_HANDOVER_CUTOFF_INVALID",
            message="La fecha de verificación debe estar entre la suscripción y hoy.",
            status_code=422,
        )
    if resultado not in ("CONFORME", "CON_OBSERVACIONES"):
        raise KontrolError(
            code="GOV_HANDOVER_ASSIGNMENT_INVALID",
            message="Resultado no válido.",
            status_code=422,
        )
    if not (10 <= len(fundamento) <= 2000):
        raise KontrolError(
            code="GOV_HANDOVER_ASSIGNMENT_INVALID",
            message="El fundamento debe tener entre 10 y 2000 caracteres.",
            status_code=422,
        )

    actor_funcionario = _funcionario_del_actor(db, ctx)
    asignacion = _obtener_asignacion(db, ctx, str(acta.assignment_id))
    if (
        str(ctx.user_id or "") == acta.suscrita_por
        or (actor_funcionario in (str(asignacion.official_id), acta.receptor_official_id))
    ):
        raise PermissionDeniedError(
            code="GOV_HANDOVER_SAME_ACTOR",
            message="La verificación no puede registrarla quien suscribió, el saliente o el receptor.",
        )

    acta.verificacion_numero = numero
    acta.verificacion_fecha = fecha
    acta.verificacion_resultado = resultado
    acta.verificacion_fundamento = fundamento
    acta.verificada_por = str(ctx.user_id or "")
    acta.verificada_en = instante_actual()
    acta.estado = "VERIFICADA"
    db.flush()
    record_audit(
        db,
        action="GOV_HANDOVER_ACT_VERIFIED",
        entity_type="GovernmentHandoverAct",
        entity_id=str(acta.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": acta.codigo, "resultado": resultado},
    )
    return acta


def _contenido_anexo_vista(
    db: Session, ctx: CompanyContext, acta: GovernmentHandoverAct, codigo: str
) -> dict[str, Any]:
    anexo = db.scalar(
        select(GovernmentHandoverAnnex).where(
            GovernmentHandoverAnnex.act_id == str(acta.id),
            GovernmentHandoverAnnex.codigo == codigo,
        )
    )
    if not anexo:
        raise _not_found()
    if acta.estado == "BORRADOR":
        return _contenido_anexo(db, ctx, acta, codigo)
    return anexo.contenido or {}


def _pdf_bytes(db: Session, ctx: CompanyContext, acta: GovernmentHandoverAct) -> bytes:
    if acta.estado == "BORRADOR":
        raise _state_error("El acta aún no está suscrita.")
    if not acta.informe_storage_key:
        raise _state_error("El acta no tiene informe generado.")
    contenido = get_storage().open(acta.informe_storage_key)
    return contenido.read()


def _opciones(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    asignaciones = list(
        db.scalars(
            select(GovernmentAssignment)
            .where(
                GovernmentAssignment.company_id == ctx.company_id,
                GovernmentAssignment.status.in_(("ACTIVO", "FINALIZADO", "REVOCADO")),
            )
            .order_by(GovernmentAssignment.codigo)
        )
    )
    ocupaciones = []
    for asignacion in asignaciones:
        posicion = db.scalar(
            select(GovernmentPosition).where(GovernmentPosition.id == asignacion.position_id)
        )
        oficial = db.scalar(
            select(GovernmentOfficial).where(GovernmentOfficial.id == asignacion.official_id)
        )
        unidad = db.scalar(select(GovernmentUnit).where(GovernmentUnit.id == posicion.unit_id)) if posicion else None
        ocupaciones.append(
            {
                "asignacion_id": str(asignacion.id),
                "codigo": asignacion.codigo,
                "funcionario": oficial.nombre if oficial else "",
                "cargo": posicion.name if posicion else "",
                "unidad": unidad.name if unidad else "",
                "figura": asignacion.figura or "",
                "estado": asignacion.status,
                "desde": asignacion.desde.isoformat() if asignacion.desde else None,
                "hasta": asignacion.hasta.isoformat() if asignacion.hasta else None,
                "fin_efectivo": asignacion.fin_efectivo.isoformat() if asignacion.fin_efectivo else None,
                "maxima_autoridad": asignacion.maxima_autoridad,
            }
        )

    funcionarios = []
    for oficial in db.scalars(
        select(GovernmentOfficial)
        .where(
            GovernmentOfficial.company_id == ctx.company_id,
            GovernmentOfficial.estado == "ACTIVO",
        )
        .order_by(GovernmentOfficial.codigo)
    ):
        funcionarios.append(
            {
                "official_id": str(oficial.id),
                "codigo": oficial.codigo,
                "nombre": oficial.nombre,
            }
        )

    return {
        "ocupaciones": ocupaciones,
        "funcionarios": funcionarios,
        "anexos": ANEXOS_CATALOGO,
        "nivel_territorial": _nivel_territorial(db, ctx),
    }


def _listar(
    db: Session,
    ctx: CompanyContext,
    *,
    estado: str | None,
    texto: str | None,
    ambito: str | None,
    desde: date | None,
    hasta: date | None,
    pagina: int,
    por_pagina: int,
) -> dict[str, Any]:
    consulta = select(GovernmentHandoverAct).where(GovernmentHandoverAct.company_id == ctx.company_id)
    if estado:
        consulta = consulta.where(GovernmentHandoverAct.estado == estado)
    if ambito:
        consulta = consulta.where(GovernmentHandoverAct.ambito == ambito)
    if texto:
        comodines = {"%": r"\%", "_": r"\_"}
        texto_escapado = "".join(comodines.get(caracter, caracter) for caracter in texto)
        patron = f"%{texto_escapado}%"
        consulta = consulta.where(
            or_(
                GovernmentHandoverAct.codigo.ilike(patron),
                GovernmentHandoverAct.motivo.ilike(patron),
            )
        )
    if desde:
        consulta = consulta.where(GovernmentHandoverAct.fecha_corte >= desde)
    if hasta:
        consulta = consulta.where(GovernmentHandoverAct.fecha_corte <= hasta)

    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    consulta = consulta.order_by(GovernmentHandoverAct.created_at.desc())
    consulta = consulta.offset((pagina - 1) * por_pagina).limit(por_pagina)
    actas = list(db.scalars(consulta))
    return {
        "items": [_ficha_resumida(db, ctx, acta) for acta in actas],
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
    }


def _historial(db: Session, ctx: CompanyContext, acta: GovernmentHandoverAct) -> dict[str, Any]:
    eventos = list(
        db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.entity_type == "GovernmentHandoverAct",
                AuditEvent.entity_id == str(acta.id),
                AuditEvent.tenant_id == ctx.tenant_id,
                AuditEvent.company_id == ctx.company_id,
            )
            .order_by(AuditEvent.event_time.asc())
        )
    )
    usuarios = _usuarios_por_ids(db, [str(e.user_id) for e in eventos if e.user_id], ctx.tenant_id)
    items = []
    for evento in eventos:
        spec = catalog().get((evento.action, evento.entity_type))
        accion_etiqueta = spec.label if spec is not None else evento.action
        items.append(
            {
                "fecha": evento.event_time.isoformat() if evento.event_time else None,
                "accion": evento.action,
                "accion_etiqueta": accion_etiqueta,
                "usuario": usuarios.get(str(evento.user_id), ""),
            }
        )
    return {"items": items}


def verificar_integridad(db: Session, ctx: CompanyContext, acta: GovernmentHandoverAct) -> dict[str, Any]:
    if acta.estado == "BORRADOR":
        raise _state_error("El acta aún no está suscrita.")
    snapshot_ok = acta.snapshot_sha256 is not None and _hash_canonico(acta.snapshot or {}) == acta.snapshot_sha256
    informe_ok = False
    if acta.informe_storage_key and acta.informe_sha256:
        informe_ok = get_storage().verify(acta.informe_storage_key, acta.informe_sha256)
    documentos: list[dict[str, Any]] = []
    for anexo in _anexos_del_acta(db, str(acta.id)):
        for doc in anexo.documentos or []:
            version = db.scalar(
                select(DocumentVersion).where(
                    DocumentVersion.id == doc["version_id"],
                    DocumentVersion.company_id == ctx.company_id,
                )
            )
            if version is None or version.sha256 != doc.get("sha256"):
                estado = "SIN_EVIDENCIA"
            else:
                estado = "VIGENTE"
            documentos.append(
                {
                    "codigo": anexo.codigo,
                    "documento_id": doc["documento_id"],
                    "estado": estado,
                }
            )
    estado = "VALIDO" if snapshot_ok and informe_ok and all(d["estado"] == "VIGENTE" for d in documentos) else "INCOMPLETO"
    return {
        "estado": estado,
        "snapshot_ok": snapshot_ok,
        "informe_ok": informe_ok,
        "documentos": documentos,
    }
