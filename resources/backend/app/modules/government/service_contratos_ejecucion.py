"""Ejecución del contrato (CNT-03, GOV-CNT-003 y GOV-CNT-007; LCP arts. 127, 137-151; RLCP art. 177)."""
from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.documents.models import Document, DocumentLink, DocumentVersion
from app.modules.documents.service import congelar_vinculo, documento_sellado, sellar_documento
from app.modules.government.models import (
    GovernmentContract,
    GovernmentContractDeliverable,
    GovernmentContractDeliverableSubmission,
    GovernmentContractExecutionAct,
    GovernmentContractInvoice,
    GovernmentContractMilestone,
    GovernmentContractReceipt,
    GovernmentContractReceiptMilestone,
    GovernmentContractValuation,
    GovernmentPosition,
    GovernmentProcurementCommittee,
    GovernmentProcurementFile,
)
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_contratos_supervision import supervisor_en, supervisor_vigente
from app.modules.government.service_contratos_terminos import terminos_efectivos
from app.modules.government.service_expedientes import _evento
from app.modules.government.service_identidad import _funcionario_del_actor
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.government.situacion_contractual import exigir_vigente_en
from app.shared.audit import record_audit, record_audit_after_rollback
from app.shared.clock import hoy_de_negocio, instante_actual

ENTIDAD = "GovernmentProcurementFile"
ETIQUETA_ESTADO_EJECUCION = {
    "SIN_INICIAR": "Sin iniciar",
    "EN_EJECUCION": "En ejecución",
    "TERMINADA": "Obra terminada",
    "RECIBIDA_PROVISIONAL": "Aceptación provisional",
    "RECIBIDA_DEFINITIVA": "Recepción definitiva",
    "CERRADA": "Cerrada",
}
ETIQUETA_RECEPCION = {"PARCIAL": "parcial", "PROVISIONAL": "provisional", "DEFINITIVA": "definitiva"}
ETIQUETA_VALUACION = {"PRESENTADA": "Presentada", "CONFORMADA": "Conformada", "REPARADA": "Reparada", "ANULADA": "Anulada"}


def _t(valor: Decimal) -> str:
    return f"{Decimal(valor):.2f}"


def _inv(campo: str, mensaje: str, code: str) -> KontrolError:
    return KontrolError(
        code,
        "Datos de la ejecución inválidos",
        field_errors={campo: [mensaje]},
        status_code=422,
    )


def _contrato(db: Session, ctx: CompanyContext, contrato_id: str, bloquear: bool) -> GovernmentContract:
    consulta = select(GovernmentContract).where(
        GovernmentContract.id == contrato_id,
        GovernmentContract.company_id == ctx.company_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    contrato = db.execute(consulta).scalar_one_or_none()
    if contrato is None:
        raise NotFoundError("GOV_CONTRACT_NOT_FOUND", "Contrato u orden no encontrado")
    return contrato


def _expediente(
    db: Session,
    ctx: CompanyContext,
    contrato: GovernmentContract,
    bloquear: bool = False,
) -> GovernmentProcurementFile:
    consulta = select(GovernmentProcurementFile).where(
        GovernmentProcurementFile.id == contrato.file_id,
        GovernmentProcurementFile.company_id == ctx.company_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    return db.execute(consulta).scalar_one()


def _flujo(expediente: GovernmentProcurementFile) -> str:
    return "OBRAS" if expediente.tipo_contratacion == "OBRAS" else "BIENES_SERVICIOS"


def _actos(db: Session, contrato_id: str) -> dict[str, GovernmentContractExecutionAct]:
    filas = db.execute(
        select(GovernmentContractExecutionAct).where(GovernmentContractExecutionAct.contract_id == contrato_id)
    ).scalars().all()
    return {fila.tipo: fila for fila in filas}


def _preparar(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    requiere_inicio: bool,
) -> tuple[GovernmentContract, GovernmentProcurementFile, dict[str, GovernmentContractExecutionAct]]:
    contrato = _contrato(db, ctx, contrato_id, True)
    if contrato.estado != "FORMALIZADO":
        raise ConflictError("GOV_CONTRACT_EXEC_NOT_FORMALIZED", "Solo un contrato formalizado admite ejecución")
    actos = _actos(db, str(contrato.id))
    if "CIERRE" in actos:
        raise ConflictError("GOV_CONTRACT_EXEC_CLOSED", "La ejecución del contrato está cerrada")
    if requiere_inicio and "INICIO" not in actos:
        raise ConflictError("GOV_CONTRACT_EXEC_NOT_STARTED", "Registre primero el inicio de la ejecución")
    expediente = _expediente(db, ctx, contrato)
    return contrato, expediente, actos


def _fecha_hecho(
    fecha: date,
    actos: dict[str, GovernmentContractExecutionAct],
    campo: str,
) -> None:
    hoy = hoy_de_negocio()
    inicio = actos.get("INICIO")
    if fecha > hoy or (inicio is not None and fecha < inicio.fecha):
        if inicio is not None:
            raise _inv(
                campo,
                f"La fecha debe estar entre el {inicio.fecha:%d/%m/%Y} y hoy",
                "GOV_CONTRACT_EXEC_DATE_INVALID",
            )
        raise _inv(campo, "La fecha debe ser igual o anterior a hoy", "GOV_CONTRACT_EXEC_DATE_INVALID")


def _bloqueo(
    db: Session,
    ctx: CompanyContext,
    contrato: GovernmentContract,
    causal: str,
    campos: dict[str, Any] | None = None,
) -> None:
    after: dict[str, Any] = {"contrato": contrato.codigo, "causal": causal}
    if campos:
        after.update({clave: valor for clave, valor in campos.items() if valor is not None})
    record_audit_after_rollback(
        db,
        action="GOV_CONTRACT_EXEC_BLOCKED",
        entity_type=ENTIDAD,
        entity_id=str(contrato.file_id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _conformante(
    db: Session,
    ctx: CompanyContext,
    contrato: GovernmentContract,
    fecha: date,
) -> dict[str, Any]:
    sup = supervisor_en(db, ctx, str(contrato.id), fecha)
    if sup is None:
        _bloqueo(db, ctx, contrato, "GOV_CONTRACT_EXEC_NO_SUPERVISOR")
        raise ConflictError(
            "GOV_CONTRACT_EXEC_NO_SUPERVISOR",
            f"El contrato no tenía supervisor el {fecha:%d/%m/%Y}",
        )
    official_id = _funcionario_del_actor(db, ctx)
    if official_id != sup["funcionario"]["id"]:
        _bloqueo(db, ctx, contrato, "GOV_CONTRACT_EXEC_NOT_SUPERVISOR", campos={"supervisor": sup["funcionario"]["nombre"]})
        raise KontrolError(
            "GOV_CONTRACT_EXEC_NOT_SUPERVISOR",
            "Solo el supervisor del contrato en esa fecha puede conformar",
            status_code=403,
        )
    return sup


def _sup(sup: dict[str, Any]) -> dict[str, Any]:
    return {
        "supervisor_assignment_id": sup["id"],
        "supervisor_official_id": sup["funcionario"]["id"],
        "supervisor_nombre": sup["funcionario"]["nombre"],
    }


def _documento(
    db: Session,
    ctx: CompanyContext,
    contrato: GovernmentContract,
    documento_id: str,
    campo: str,
) -> tuple[Document, DocumentVersion, DocumentLink]:
    doc = db.scalar(
        select(Document).where(
            Document.company_id == ctx.company_id,
            Document.id == documento_id,
            Document.status.in_(("DRAFT", "ACTIVE")),
        )
    )
    if doc is None or doc.current_version_id is None or documento_sellado(db, str(doc.id)):
        raise _inv(
            campo,
            "Elija un documento del expediente que no esté usado en otro acto",
            "GOV_CONTRACT_EXEC_DOCUMENT_INVALID",
        )
    version = db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.id == doc.current_version_id,
            DocumentVersion.document_id == doc.id,
        )
    )
    link = db.scalar(
        select(DocumentLink).where(
            DocumentLink.document_id == doc.id,
            DocumentLink.resource_type == "GovernmentProcurementFile",
            DocumentLink.resource_id == contrato.file_id,
        )
    )
    if version is None or link is None:
        raise _inv(
            campo,
            "Elija un documento del expediente que no esté usado en otro acto",
            "GOV_CONTRACT_EXEC_DOCUMENT_INVALID",
        )
    return doc, version, link


def _doc(r: tuple[Document, DocumentVersion, DocumentLink]) -> dict[str, Any]:
    doc, version, _link = r
    return {
        "document_id": str(doc.id),
        "document_version_id": str(version.id),
        "documento_sha256": version.sha256,
        "documento_titulo": doc.title,
    }


def _sellar(
    db: Session,
    ctx: CompanyContext,
    contrato: GovernmentContract,
    r: tuple[Document, DocumentVersion, DocumentLink],
    motivo: str,
) -> None:
    doc, version, link = r
    sellar_documento(
        db,
        document=doc,
        resource_type="GovernmentContract",
        resource_id=str(contrato.id),
        actor_id=ctx.user_id,
        motivo=motivo,
    )
    congelar_vinculo(db, link=link, version_id=str(version.id))


def _siguiente(db: Session, Modelo: Any, contrato_id: str, filtro_extra: Any = None) -> int:
    consulta = select(func.coalesce(func.max(Modelo.numero), 0)).where(Modelo.contract_id == contrato_id)
    if filtro_extra is not None:
        consulta = consulta.where(filtro_extra)
    valor = db.scalar(consulta)
    return int(valor or 0) + 1


def _suma(db: Session, columna: Any, *condiciones: Any) -> Decimal:
    valor = db.scalar(select(func.coalesce(func.sum(columna), 0)).where(*condiciones))
    return Decimal(str(valor or 0))


def _cumplidos(db: Session, contrato_id: str) -> dict[str, str]:
    filas = db.execute(
        select(
            GovernmentContractReceiptMilestone.milestone_id,
            GovernmentContractReceipt.numero,
        )
        .join(
            GovernmentContractReceipt,
            GovernmentContractReceipt.id == GovernmentContractReceiptMilestone.receipt_id,
        )
        .where(
            GovernmentContractReceiptMilestone.contract_id == contrato_id,
            GovernmentContractReceipt.estado == "CONFORME",
        )
    ).all()
    return {str(milestone_id): f"REC-{numero:02d}" for milestone_id, numero in filas}


def _conforme(db: Session, entregable_id: str) -> bool:
    existe = db.scalar(
        select(GovernmentContractDeliverableSubmission.id).where(
            GovernmentContractDeliverableSubmission.deliverable_id == entregable_id,
            GovernmentContractDeliverableSubmission.estado == "CONFORME",
        )
    )
    return existe is not None


def _pendientes(
    db: Session,
    contrato_id: str,
    hito_ids: set[str] | None,
) -> list[str]:
    pendientes: list[str] = []
    consulta_entregables = select(GovernmentContractDeliverable).where(
        GovernmentContractDeliverable.contract_id == contrato_id,
        GovernmentContractDeliverable.estado == "VIGENTE",
        GovernmentContractDeliverable.obligatorio.is_(True),
    )
    if hito_ids is not None:
        consulta_entregables = consulta_entregables.where(
            GovernmentContractDeliverable.milestone_id.in_(hito_ids)
        )
    entregables = db.execute(consulta_entregables).scalars().all()
    for entregable in entregables:
        if not _conforme(db, str(entregable.id)):
            pendientes.append(f"ENT-{entregable.numero:02d}")

    if hito_ids is None:
        valuaciones = db.execute(
            select(GovernmentContractValuation).where(
                GovernmentContractValuation.contract_id == contrato_id,
                GovernmentContractValuation.estado == "PRESENTADA",
            )
        ).scalars().all()
        for valuacion in valuaciones:
            pendientes.append(f"VAL-{valuacion.numero:02d}")

        entregas = db.execute(
            select(GovernmentContractDeliverableSubmission)
            .join(
                GovernmentContractDeliverable,
                GovernmentContractDeliverable.id
                == GovernmentContractDeliverableSubmission.deliverable_id,
            )
            .where(
                GovernmentContractDeliverableSubmission.contract_id == contrato_id,
                GovernmentContractDeliverableSubmission.estado == "ENTREGADA",
            )
        ).scalars().all()
        for entrega in entregas:
            entregable_abierto: GovernmentContractDeliverable | None = db.scalar(
                select(GovernmentContractDeliverable).where(
                    GovernmentContractDeliverable.id == entrega.deliverable_id
                )
            )
            pendientes.append(
                f"ENT-{entregable_abierto.numero:02d}/{entrega.numero:02d}"
                if entregable_abierto is not None
                else f"ENT-??/{entrega.numero:02d}"
            )

    return pendientes


def _flush(
    db: Session,
    indices: dict[str, tuple[str, str]],
) -> None:
    try:
        db.flush()
    except IntegrityError as error:
        for indice, (code, mensaje) in indices.items():
            if es_violacion_unica(error, indice):
                db.rollback()
                raise ConflictError(code, mensaje) from error
        raise


def _cronologia_expediente(
    db: Session,
    ctx: CompanyContext,
    contrato: GovernmentContract,
    fecha: date,
    titulo: str,
    detalle: str,
) -> None:
    expediente = _expediente(db, ctx, contrato, True)
    expediente.version += 1
    _evento(db, ctx, expediente, "CONTRATO", fecha, titulo, detalle=detalle)


def _auditar(
    db: Session,
    ctx: CompanyContext,
    contrato: GovernmentContract,
    accion: str,
    after: dict[str, Any],
) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD,
        entity_id=str(contrato.file_id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={clave: valor for clave, valor in after.items() if valor is not None},
    )


def iniciar(db: Session, ctx: CompanyContext, contrato_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    contrato, expediente, actos = _preparar(db, ctx, contrato_id, False)
    if "INICIO" in actos:
        raise ConflictError("GOV_CONTRACT_EXEC_ALREADY_STARTED", "El inicio de la ejecución ya está registrado")
    fecha: date = cuerpo["fecha"]
    exigir_vigente_en(db, ctx.company_id, str(contrato.id), fecha)
    terminos = terminos_efectivos(db, contrato, fecha)
    formalizacion = contrato.fecha_formalizacion
    if formalizacion is None:
        raise ConflictError(
            "GOV_CONTRACT_EXEC_NOT_FORMALIZED",
            "Solo un contrato formalizado admite ejecución",
        )
    desde = formalizacion
    hasta = min(hoy_de_negocio(), terminos["fecha_fin"]) if terminos["fecha_fin"] is not None else hoy_de_negocio()
    if fecha < desde or fecha > hasta:
        raise _inv(
            "fecha",
            f"La fecha de inicio debe estar entre el {desde:%d/%m/%Y} y el {hasta:%d/%m/%Y}",
            "GOV_CONTRACT_EXEC_DATE_INVALID",
        )
    sup = _conformante(db, ctx, contrato, fecha)
    r = _documento(db, ctx, contrato, cuerpo["documento_id"], "documento_id")
    evaluar_antes_de_actuar(db, ctx, "PROC03_EJEC_INICIAR", ENTIDAD, str(contrato.file_id))
    ahora = instante_actual()
    observacion = (cuerpo.get("observacion") or "").strip() or None
    acto = GovernmentContractExecutionAct(
        company_id=ctx.company_id,
        contract_id=str(contrato.id),
        tipo="INICIO",
        fecha=fecha,
        observacion=observacion,
        **_sup(sup),
        **_doc(r),
        registrado_en=ahora,
        registrado_por=ctx.user_id,
        created_by=ctx.user_id,
    )
    db.add(acto)
    _flush(
        db,
        {
            "uq_gov_contract_execution_acts_tipo": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            )
        },
    )
    _sellar(db, ctx, contrato, r, f"Acta de inicio de {contrato.codigo} (CNT-03)")
    _cronologia_expediente(
        db,
        ctx,
        contrato,
        fecha,
        f"Inicio de la ejecución de {contrato.codigo}",
        detalle=f"Supervisor: {sup['funcionario']['nombre']}",
    )
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_STARTED",
        {
            "contrato": contrato.codigo,
            "fecha": fecha.isoformat(),
            "supervisor": sup["funcionario"]["nombre"],
            "documento": r[0].title,
        },
    )
    return ejecucion(db, ctx, contrato_id)


def crear_hito(db: Session, ctx: CompanyContext, contrato_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    contrato, _exp, _actos = _preparar(db, ctx, contrato_id, False)
    descripcion = (cuerpo["descripcion"] or "").strip()
    if not descripcion:
        raise _inv("descripcion", "Indique la descripción del hito", "GOV_CONTRACT_EXEC_REASON_REQUIRED")
    formalizacion = contrato.fecha_formalizacion
    if formalizacion is None:
        raise ConflictError(
            "GOV_CONTRACT_EXEC_NOT_FORMALIZED",
            "Solo un contrato formalizado admite ejecución",
        )
    fecha_prevista: date = cuerpo["fecha_prevista"]
    exigir_vigente_en(db, ctx.company_id, str(contrato.id), fecha_prevista)
    if fecha_prevista < formalizacion:
        raise _inv(
            "fecha_prevista",
            "La fecha prevista debe ser igual o posterior a la formalización del contrato",
            "GOV_CONTRACT_EXEC_DATE_INVALID",
        )
    terminos = terminos_efectivos(db, contrato, hoy_de_negocio())
    monto_previsto = cuerpo.get("monto_previsto")
    porcentaje_previsto = cuerpo.get("porcentaje_previsto")
    consulta_vigentes = select(GovernmentContractMilestone).where(
        GovernmentContractMilestone.contract_id == contrato_id,
        GovernmentContractMilestone.estado == "VIGENTE",
    )
    vigentes = db.execute(consulta_vigentes).scalars().all()
    if monto_previsto is not None:
        suma_actual = sum((Decimal(fila.monto_previsto) for fila in vigentes if fila.monto_previsto is not None), Decimal("0"))
        if suma_actual + Decimal(monto_previsto) > terminos["monto"]:
            raise _inv(
                "monto_previsto",
                f"La suma de montos previstos no puede superar el monto del contrato "
                f"({_t(terminos['monto'])} {terminos['moneda']})",
                "GOV_CONTRACT_EXEC_MILESTONE_AMOUNT_EXCEEDED",
            )
    if porcentaje_previsto is not None:
        suma_actual = sum(
            (Decimal(fila.porcentaje_previsto) for fila in vigentes if fila.porcentaje_previsto is not None),
            Decimal("0"),
        )
        if suma_actual + Decimal(porcentaje_previsto) > Decimal("100"):
            raise _inv(
                "porcentaje_previsto",
                "La suma de porcentajes previstos no puede superar 100",
                "GOV_CONTRACT_EXEC_MILESTONE_AMOUNT_EXCEEDED",
            )
    numero = _siguiente(db, GovernmentContractMilestone, contrato_id)
    hito = GovernmentContractMilestone(
        company_id=ctx.company_id,
        contract_id=contrato_id,
        numero=numero,
        descripcion=descripcion,
        fecha_prevista=fecha_prevista,
        monto_previsto=monto_previsto,
        porcentaje_previsto=porcentaje_previsto,
        obligatorio=bool(cuerpo.get("obligatorio", True)),
        estado="VIGENTE",
        registrado_en=instante_actual(),
        registrado_por=ctx.user_id,
        created_by=ctx.user_id,
    )
    db.add(hito)
    _flush(
        db,
        {
            "uq_gov_contract_milestones_numero": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            )
        },
    )
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_MILESTONE_CREATED",
        {
            "contrato": contrato.codigo,
            "hito": f"HIT-{numero:02d}",
            "monto": _t(Decimal(monto_previsto)) if monto_previsto is not None else None,
            "fecha": fecha_prevista.isoformat(),
        },
    )
    return ejecucion(db, ctx, contrato_id)


def anular_hito(db: Session, ctx: CompanyContext, contrato_id: str, hito_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    contrato, _exp, _actos = _preparar(db, ctx, contrato_id, False)
    hito = db.scalar(
        select(GovernmentContractMilestone).where(
            GovernmentContractMilestone.id == hito_id,
            GovernmentContractMilestone.contract_id == contrato_id,
            GovernmentContractMilestone.estado == "VIGENTE",
        )
    )
    if hito is None:
        raise NotFoundError("GOV_CONTRACT_EXEC_NOT_FOUND", "Elemento de la ejecución no encontrado")
    motivo = (cuerpo["motivo"] or "").strip()
    if not motivo:
        raise _inv("motivo", "Indique el motivo", "GOV_CONTRACT_EXEC_REASON_REQUIRED")
    en_uso = db.scalar(
        select(GovernmentContractValuation.id).where(
            GovernmentContractValuation.milestone_id == hito_id,
            GovernmentContractValuation.estado != "ANULADA",
        )
    )
    if en_uso is None:
        en_uso = db.scalar(
            select(GovernmentContractDeliverable.id).where(
                GovernmentContractDeliverable.milestone_id == hito_id,
                GovernmentContractDeliverable.estado == "VIGENTE",
            )
        )
    if en_uso is None:
        en_uso_recepcion = db.scalar(
            select(GovernmentContractReceiptMilestone.milestone_id)
            .join(
                GovernmentContractReceipt,
                GovernmentContractReceipt.id == GovernmentContractReceiptMilestone.receipt_id,
            )
            .where(
                GovernmentContractReceiptMilestone.milestone_id == hito_id,
                GovernmentContractReceipt.estado == "CONFORME",
            )
        )
    if en_uso is None:
        en_uso = db.scalar(
            select(GovernmentContractInvoice.id).where(
                GovernmentContractInvoice.milestone_id == hito_id,
                GovernmentContractInvoice.estado == "CONFORME",
            )
        )
    if en_uso is not None or en_uso_recepcion is not None:
        raise ConflictError("GOV_CONTRACT_EXEC_IN_USE", "No se puede anular: tiene hechos asociados")
    hito.estado = "ANULADO"
    hito.motivo_anulacion = motivo
    hito.anulado_en = instante_actual()
    hito.anulado_por = ctx.user_id
    hito.version += 1
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_MILESTONE_CANCELLED",
        {"contrato": contrato.codigo, "hito": f"HIT-{hito.numero:02d}", "motivo": motivo},
    )
    return ejecucion(db, ctx, contrato_id)


def crear_entregable(db: Session, ctx: CompanyContext, contrato_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    contrato, _exp, _actos = _preparar(db, ctx, contrato_id, False)
    descripcion = (cuerpo["descripcion"] or "").strip()
    if not descripcion:
        raise _inv("descripcion", "Indique la descripción del entregable", "GOV_CONTRACT_EXEC_REASON_REQUIRED")
    hito_id = cuerpo.get("hito_id")
    hito: GovernmentContractMilestone | None = None
    if hito_id is not None:
        hito = db.scalar(
            select(GovernmentContractMilestone).where(
                GovernmentContractMilestone.id == hito_id,
                GovernmentContractMilestone.contract_id == contrato_id,
                GovernmentContractMilestone.estado == "VIGENTE",
            )
        )
        if hito is None:
            raise _inv("hito_id", "Elija un hito vigente", "GOV_CONTRACT_EXEC_MILESTONE_INVALID")
    formalizacion = contrato.fecha_formalizacion
    if formalizacion is None:
        raise ConflictError(
            "GOV_CONTRACT_EXEC_NOT_FORMALIZED",
            "Solo un contrato formalizado admite ejecución",
        )
    fecha_vencimiento: date = cuerpo["fecha_vencimiento"]
    exigir_vigente_en(db, ctx.company_id, str(contrato.id), fecha_vencimiento)
    if fecha_vencimiento < formalizacion:
        raise _inv(
            "fecha_vencimiento",
            "La fecha de vencimiento debe ser igual o posterior a la formalización del contrato",
            "GOV_CONTRACT_EXEC_DATE_INVALID",
        )
    numero = _siguiente(db, GovernmentContractDeliverable, contrato_id)
    entregable = GovernmentContractDeliverable(
        company_id=ctx.company_id,
        contract_id=contrato_id,
        milestone_id=hito_id,
        numero=numero,
        descripcion=descripcion,
        fecha_vencimiento=fecha_vencimiento,
        obligatorio=bool(cuerpo.get("obligatorio", True)),
        estado="VIGENTE",
        registrado_en=instante_actual(),
        registrado_por=ctx.user_id,
        created_by=ctx.user_id,
    )
    db.add(entregable)
    _flush(
        db,
        {
            "uq_gov_contract_deliverables_numero": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            )
        },
    )
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_DELIVERABLE_CREATED",
        {
            "contrato": contrato.codigo,
            "entregable": f"ENT-{numero:02d}",
            "hito": f"HIT-{hito.numero:02d}" if hito is not None else None,
            "fecha": fecha_vencimiento.isoformat(),
        },
    )
    return ejecucion(db, ctx, contrato_id)


def anular_entregable(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    entregable_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    contrato, _exp, _actos = _preparar(db, ctx, contrato_id, False)
    entregable = db.scalar(
        select(GovernmentContractDeliverable).where(
            GovernmentContractDeliverable.id == entregable_id,
            GovernmentContractDeliverable.contract_id == contrato_id,
            GovernmentContractDeliverable.estado == "VIGENTE",
        )
    )
    if entregable is None:
        raise NotFoundError("GOV_CONTRACT_EXEC_NOT_FOUND", "Elemento de la ejecución no encontrado")
    motivo = (cuerpo["motivo"] or "").strip()
    if not motivo:
        raise _inv("motivo", "Indique el motivo", "GOV_CONTRACT_EXEC_REASON_REQUIRED")
    tiene_entrega = db.scalar(
        select(GovernmentContractDeliverableSubmission.id).where(
            GovernmentContractDeliverableSubmission.deliverable_id == entregable_id
        )
    )
    if tiene_entrega is not None:
        raise ConflictError("GOV_CONTRACT_EXEC_IN_USE", "No se puede anular: tiene hechos asociados")
    entregable.estado = "ANULADO"
    entregable.motivo_anulacion = motivo
    entregable.anulado_en = instante_actual()
    entregable.anulado_por = ctx.user_id
    entregable.version += 1
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_DELIVERABLE_CANCELLED",
        {"contrato": contrato.codigo, "entregable": f"ENT-{entregable.numero:02d}", "motivo": motivo},
    )
    return ejecucion(db, ctx, contrato_id)


def entregar(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    entregable_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    contrato, _exp, actos = _preparar(db, ctx, contrato_id, True)
    entregable = db.scalar(
        select(GovernmentContractDeliverable).where(
            GovernmentContractDeliverable.id == entregable_id,
            GovernmentContractDeliverable.contract_id == contrato_id,
            GovernmentContractDeliverable.estado == "VIGENTE",
        )
    )
    if entregable is None:
        raise NotFoundError("GOV_CONTRACT_EXEC_NOT_FOUND", "Elemento de la ejecución no encontrado")
    if _conforme(db, entregable_id):
        raise ConflictError("GOV_CONTRACT_EXEC_SUBMISSION_INVALID", "El entregable ya está conforme")
    abierta = db.scalar(
        select(GovernmentContractDeliverableSubmission.id).where(
            GovernmentContractDeliverableSubmission.deliverable_id == entregable_id,
            GovernmentContractDeliverableSubmission.estado == "ENTREGADA",
        )
    )
    if abierta is not None:
        raise ConflictError("GOV_CONTRACT_EXEC_SUBMISSION_OPEN", "Hay una entrega pendiente de revisión")
    fecha_entrega: date = cuerpo["fecha_entrega"]
    _fecha_hecho(fecha_entrega, actos, "fecha_entrega")
    exigir_vigente_en(db, ctx.company_id, str(contrato.id), fecha_entrega)
    r = _documento(db, ctx, contrato, cuerpo["documento_id"], "documento_id")
    numero = _siguiente(
        db,
        GovernmentContractDeliverableSubmission,
        contrato_id,
        GovernmentContractDeliverableSubmission.deliverable_id == entregable_id,
    )
    referencia = f"ENT-{entregable.numero:02d}/{numero:02d}"
    entrega = GovernmentContractDeliverableSubmission(
        company_id=ctx.company_id,
        contract_id=contrato_id,
        deliverable_id=entregable_id,
        numero=numero,
        fecha_entrega=fecha_entrega,
        observacion_entrega=(cuerpo.get("observacion") or "").strip() or None,
        estado="ENTREGADA",
        **_doc(r),
        registrado_en=instante_actual(),
        registrado_por=ctx.user_id,
        created_by=ctx.user_id,
    )
    db.add(entrega)
    _flush(
        db,
        {
            "uq_gov_contract_submissions_abierta": (
                "GOV_CONTRACT_EXEC_SUBMISSION_OPEN",
                "Hay una entrega pendiente de revisión",
            ),
            "uq_gov_contract_submissions_numero": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            ),
        },
    )
    _sellar(db, ctx, contrato, r, f"Entrega {referencia} de {contrato.codigo} (CNT-03)")
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_DELIVERABLE_SUBMITTED",
        {
            "contrato": contrato.codigo,
            "entregable": referencia,
            "fecha": fecha_entrega.isoformat(),
            "documento": r[0].title,
        },
    )
    return ejecucion(db, ctx, contrato_id)


def revisar_entrega(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    entrega_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    contrato, _exp, actos = _preparar(db, ctx, contrato_id, True)
    entrega = db.scalar(
        select(GovernmentContractDeliverableSubmission).where(
            GovernmentContractDeliverableSubmission.id == entrega_id,
            GovernmentContractDeliverableSubmission.contract_id == contrato_id,
        )
    )
    if entrega is None:
        raise NotFoundError("GOV_CONTRACT_EXEC_NOT_FOUND", "Elemento de la ejecución no encontrado")
    if entrega.estado != "ENTREGADA":
        raise ConflictError("GOV_CONTRACT_EXEC_SUBMISSION_INVALID", "La entrega ya fue revisada")
    fecha_revision: date = cuerpo["fecha_revision"]
    if fecha_revision < entrega.fecha_entrega or fecha_revision > hoy_de_negocio():
        raise _inv(
            "fecha_revision",
            "La fecha de revisión debe estar entre la entrega y hoy",
            "GOV_CONTRACT_EXEC_DATE_INVALID",
        )
    resultado = cuerpo["resultado"]
    observacion = (cuerpo.get("observacion") or "").strip() or None
    if resultado == "RECHAZADA" and not observacion:
        raise _inv("observacion", "Indique el motivo del rechazo", "GOV_CONTRACT_EXEC_REASON_REQUIRED")
    sup = _conformante(db, ctx, contrato, fecha_revision)
    evaluar_antes_de_actuar(db, ctx, "PROC03_EJEC_CONFORMAR", ENTIDAD, str(contrato.file_id))
    entrega.estado = resultado
    entrega.fecha_revision = fecha_revision
    entrega.observacion_revision = observacion
    for clave, valor in _sup(sup).items():
        setattr(entrega, clave, valor)
    entrega.revisado_en = instante_actual()
    entrega.revisado_por = ctx.user_id
    entrega.version += 1
    _flush(
        db,
        {
            "uq_gov_contract_submissions_conforme": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            )
        },
    )
    entregable = db.scalar(
        select(GovernmentContractDeliverable).where(
            GovernmentContractDeliverable.id == entrega.deliverable_id
        )
    )
    if entregable is None:
        raise NotFoundError("GOV_CONTRACT_EXEC_NOT_FOUND", "Elemento de la ejecución no encontrado")
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_DELIVERABLE_REVIEWED",
        {
            "contrato": contrato.codigo,
            "entregable": f"ENT-{entregable.numero:02d}/{entrega.numero:02d}",
            "resultado": resultado,
            "supervisor": sup["funcionario"]["nombre"],
            "fecha": fecha_revision.isoformat(),
        },
    )
    return ejecucion(db, ctx, contrato_id)


def presentar_valuacion(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    contrato, _exp, actos = _preparar(db, ctx, contrato_id, True)
    hito = db.scalar(
        select(GovernmentContractMilestone).where(
            GovernmentContractMilestone.id == cuerpo["hito_id"],
            GovernmentContractMilestone.contract_id == contrato_id,
            GovernmentContractMilestone.estado == "VIGENTE",
        )
    )
    if hito is None:
        raise _inv("hito_id", "Elija un hito vigente", "GOV_CONTRACT_EXEC_MILESTONE_INVALID")
    periodo_desde: date = cuerpo["periodo_desde"]
    periodo_hasta: date = cuerpo["periodo_hasta"]
    exigir_vigente_en(db, ctx.company_id, str(contrato.id), periodo_hasta)
    fecha: date = cuerpo["fecha"]
    inicio = actos["INICIO"]
    if periodo_desde < inicio.fecha or periodo_desde > periodo_hasta or periodo_hasta > fecha:
        raise _inv(
            "periodo_hasta",
            "El período debe estar dentro de la ejecución y antes de la fecha de la valuación",
            "GOV_CONTRACT_EXEC_DATE_INVALID",
        )
    _fecha_hecho(fecha, actos, "fecha")
    monto = Decimal(cuerpo["monto"])
    terminos = terminos_efectivos(db, contrato, fecha)
    comprometido = _suma(
        db,
        GovernmentContractValuation.monto,
        GovernmentContractValuation.contract_id == contrato_id,
        GovernmentContractValuation.estado.in_(("PRESENTADA", "CONFORMADA")),
    )
    if comprometido + monto > terminos["monto"]:
        _bloqueo(db, ctx, contrato, "GOV_CONTRACT_EXEC_VALUATION_EXCEEDS_CONTRACT", campos={"monto": _t(monto)})
        raise _inv(
            "monto",
            f"La valuación supera el saldo del contrato: quedan "
            f"{_t(terminos['monto'] - comprometido)} {terminos['moneda']}",
            "GOV_CONTRACT_EXEC_VALUATION_EXCEEDS_CONTRACT",
        )
    r = _documento(db, ctx, contrato, cuerpo["documento_id"], "documento_id")
    numero = _siguiente(db, GovernmentContractValuation, contrato_id)
    valuacion = GovernmentContractValuation(
        company_id=ctx.company_id,
        contract_id=contrato_id,
        milestone_id=str(hito.id),
        numero=numero,
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
        fecha=fecha,
        monto=monto,
        moneda=contrato.moneda,
        **_doc(r),
        estado="PRESENTADA",
        registrado_en=instante_actual(),
        registrado_por=ctx.user_id,
        created_by=ctx.user_id,
    )
    db.add(valuacion)
    _flush(
        db,
        {
            "uq_gov_contract_valuations_numero": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            )
        },
    )
    _sellar(db, ctx, contrato, r, f"Valuación VAL-{numero:02d} de {contrato.codigo} (CNT-03)")
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_VALUATION_PRESENTED",
        {
            "contrato": contrato.codigo,
            "valuacion": f"VAL-{numero:02d}",
            "hito": f"HIT-{hito.numero:02d}",
            "monto": _t(monto),
            "moneda": contrato.moneda,
            "fecha": fecha.isoformat(),
        },
    )
    return ejecucion(db, ctx, contrato_id)


def resolver_valuacion(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    valuacion_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    contrato, _exp, _actos = _preparar(db, ctx, contrato_id, True)
    valuacion = db.scalar(
        select(GovernmentContractValuation).where(
            GovernmentContractValuation.id == valuacion_id,
            GovernmentContractValuation.contract_id == contrato_id,
        )
    )
    if valuacion is None:
        raise NotFoundError("GOV_CONTRACT_EXEC_NOT_FOUND", "Elemento de la ejecución no encontrado")
    if valuacion.estado != "PRESENTADA":
        raise ConflictError("GOV_CONTRACT_EXEC_VALUATION_INVALID", "La valuación ya fue resuelta")
    fecha_conformidad: date = cuerpo["fecha_conformidad"]
    if fecha_conformidad < valuacion.fecha or fecha_conformidad > hoy_de_negocio():
        raise _inv(
            "fecha_conformidad",
            "La fecha de conformidad debe estar entre la valuación y hoy",
            "GOV_CONTRACT_EXEC_DATE_INVALID",
        )
    resultado = cuerpo["resultado"]
    reparos = (cuerpo.get("reparos") or "").strip() or None
    if resultado == "REPARADA" and not reparos:
        raise _inv("reparos", "Indique los reparos", "GOV_CONTRACT_EXEC_REASON_REQUIRED")
    sup = _conformante(db, ctx, contrato, fecha_conformidad)
    evaluar_antes_de_actuar(db, ctx, "PROC03_EJEC_CONFORMAR", ENTIDAD, str(contrato.file_id))
    acumulado: Decimal | None = None
    if resultado == "CONFORMADA":
        terminos = terminos_efectivos(db, contrato, fecha_conformidad)
        conformado = _suma(
            db,
            GovernmentContractValuation.monto,
            GovernmentContractValuation.contract_id == contrato_id,
            GovernmentContractValuation.estado == "CONFORMADA",
        )
        if conformado + Decimal(valuacion.monto) > terminos["monto"]:
            _bloqueo(
                db,
                ctx,
                contrato,
                "GOV_CONTRACT_EXEC_VALUATION_EXCEEDS_CONTRACT",
                campos={"monto": _t(Decimal(valuacion.monto))},
            )
            raise _inv(
                "monto",
                f"La valuación supera el saldo del contrato: quedan "
                f"{_t(terminos['monto'] - conformado)} {terminos['moneda']}",
                "GOV_CONTRACT_EXEC_VALUATION_EXCEEDS_CONTRACT",
            )
        acumulado = conformado + Decimal(valuacion.monto)
    valuacion.estado = resultado
    valuacion.fecha_conformidad = fecha_conformidad
    valuacion.acumulado = acumulado
    valuacion.reparos = reparos
    for clave, valor in _sup(sup).items():
        setattr(valuacion, clave, valor)
    valuacion.resuelto_en = instante_actual()
    valuacion.resuelto_por = ctx.user_id
    valuacion.version += 1
    accion = "GOV_CONTRACT_EXEC_VALUATION_CONFORMED" if resultado == "CONFORMADA" else "GOV_CONTRACT_EXEC_VALUATION_OBJECTED"
    _auditar(
        db,
        ctx,
        contrato,
        accion,
        {
            "contrato": contrato.codigo,
            "valuacion": f"VAL-{valuacion.numero:02d}",
            "monto": _t(Decimal(valuacion.monto)),
            "acumulado": _t(acumulado) if acumulado is not None else None,
            "resultado": resultado,
            "supervisor": sup["funcionario"]["nombre"],
        },
    )
    return ejecucion(db, ctx, contrato_id)


def anular_valuacion(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    valuacion_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    contrato, _exp, _actos = _preparar(db, ctx, contrato_id, True)
    valuacion = db.scalar(
        select(GovernmentContractValuation).where(
            GovernmentContractValuation.id == valuacion_id,
            GovernmentContractValuation.contract_id == contrato_id,
        )
    )
    if valuacion is None:
        raise NotFoundError("GOV_CONTRACT_EXEC_NOT_FOUND", "Elemento de la ejecución no encontrado")
    if valuacion.estado != "PRESENTADA":
        raise ConflictError("GOV_CONTRACT_EXEC_VALUATION_INVALID", "Solo se anula una valuación presentada")
    motivo = (cuerpo["motivo"] or "").strip()
    if not motivo:
        raise _inv("motivo", "Indique el motivo", "GOV_CONTRACT_EXEC_REASON_REQUIRED")
    valuacion.estado = "ANULADA"
    valuacion.motivo_anulacion = motivo
    valuacion.resuelto_en = instante_actual()
    valuacion.resuelto_por = ctx.user_id
    valuacion.version += 1
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_VALUATION_CANCELLED",
        {"contrato": contrato.codigo, "valuacion": f"VAL-{valuacion.numero:02d}", "motivo": motivo},
    )
    return ejecucion(db, ctx, contrato_id)


def terminar_obra(db: Session, ctx: CompanyContext, contrato_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    contrato, expediente, actos = _preparar(db, ctx, contrato_id, True)
    if _flujo(expediente) != "OBRAS":
        raise ConflictError(
            "GOV_CONTRACT_EXEC_WORKS_ONLY",
            "El acta de terminación solo aplica a contratos de obras",
        )
    if "TERMINACION" in actos:
        raise ConflictError("GOV_CONTRACT_EXEC_ALREADY_COMPLETED", "La terminación ya está registrada")
    fecha: date = cuerpo["fecha"]
    exigir_vigente_en(db, ctx.company_id, str(contrato.id), fecha)
    _fecha_hecho(fecha, actos, "fecha")
    sup = _conformante(db, ctx, contrato, fecha)
    r = _documento(db, ctx, contrato, cuerpo["documento_id"], "documento_id")
    evaluar_antes_de_actuar(db, ctx, "PROC03_EJEC_CONFORMAR", ENTIDAD, str(contrato.file_id))
    acto = GovernmentContractExecutionAct(
        company_id=ctx.company_id,
        contract_id=str(contrato.id),
        tipo="TERMINACION",
        fecha=fecha,
        observacion=(cuerpo.get("observacion") or "").strip() or None,
        **_sup(sup),
        **_doc(r),
        registrado_en=instante_actual(),
        registrado_por=ctx.user_id,
        created_by=ctx.user_id,
    )
    db.add(acto)
    _flush(
        db,
        {
            "uq_gov_contract_execution_acts_tipo": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            )
        },
    )
    _sellar(db, ctx, contrato, r, f"Acta de terminación de {contrato.codigo} (CNT-03)")
    _cronologia_expediente(db, ctx, contrato, fecha, f"Terminación de la obra {contrato.codigo}", detalle="")
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_WORKS_COMPLETED",
        {
            "contrato": contrato.codigo,
            "fecha": fecha.isoformat(),
            "supervisor": sup["funcionario"]["nombre"],
            "documento": r[0].title,
        },
    )
    return ejecucion(db, ctx, contrato_id)


def registrar_recepcion(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    contrato, expediente, actos = _preparar(db, ctx, contrato_id, True)
    flujo = _flujo(expediente)
    tipo = cuerpo["tipo"]
    fecha: date = cuerpo["fecha"]
    _fecha_hecho(fecha, actos, "fecha")
    cumplidos = _cumplidos(db, contrato_id)
    hito_ids_a_vincular: list[Any] = []
    fin_garantia: date | None = cuerpo.get("fin_garantia")
    representante_cargo_id = cuerpo.get("representante_cargo_id")

    if tipo == "PARCIAL":
        if flujo != "BIENES_SERVICIOS":
            raise ConflictError(
                "GOV_CONTRACT_EXEC_RECEIPT_TYPE_INVALID",
                "La recepción parcial aplica a bienes y servicios; en obras se usan la terminación y la aceptación provisional",
            )
        hito_ids = cuerpo.get("hito_ids") or []
        if not hito_ids or any(
            db.scalar(
                select(GovernmentContractMilestone.id).where(
                    GovernmentContractMilestone.id == hito_id,
                    GovernmentContractMilestone.contract_id == contrato_id,
                    GovernmentContractMilestone.estado == "VIGENTE",
                )
            )
            is None
            for hito_id in hito_ids
        ) or any(hito_id in cumplidos for hito_id in hito_ids):
            raise _inv("hito_ids", "Elija hitos vigentes no recibidos", "GOV_CONTRACT_EXEC_MILESTONE_INVALID")
        pend = _pendientes(db, contrato_id, set(hito_ids))
        if pend:
            raise ConflictError(
                "GOV_CONTRACT_EXEC_RECEIPT_NOT_READY",
                "Faltan entregables conformes",
                details={"pendientes": pend},
            )
        hito_ids_a_vincular = hito_ids
    elif tipo == "PROVISIONAL":
        if flujo != "OBRAS":
            raise ConflictError(
                "GOV_CONTRACT_EXEC_RECEIPT_TYPE_INVALID",
                "La aceptación provisional aplica a obras",
            )
        terminacion = actos.get("TERMINACION")
        if terminacion is None or fecha < terminacion.fecha:
            raise ConflictError(
                "GOV_CONTRACT_EXEC_RECEIPT_NOT_READY",
                "Registre primero el acta de terminación",
            )
        if db.scalar(
            select(GovernmentContractReceipt.id).where(
                GovernmentContractReceipt.contract_id == contrato_id,
                GovernmentContractReceipt.tipo == "PROVISIONAL",
                GovernmentContractReceipt.estado == "CONFORME",
            )
        ):
            raise ConflictError("GOV_CONTRACT_EXEC_CONFLICT", "La aceptación provisional ya está registrada")
        if fin_garantia is None or fin_garantia < fecha:
            raise _inv(
                "fin_garantia",
                "Indique el fin del lapso de garantía, igual o posterior a la fecha",
                "GOV_CONTRACT_EXEC_DATE_INVALID",
            )
        pend = _pendientes(db, contrato_id, None)
        if pend:
            raise ConflictError(
                "GOV_CONTRACT_EXEC_RECEIPT_NOT_READY",
                "Faltan entregables conformes",
                details={"pendientes": pend},
            )
        hito_ids_a_vincular = [
            str(fila.id)
            for fila in db.execute(
                select(GovernmentContractMilestone).where(
                    GovernmentContractMilestone.contract_id == contrato_id,
                    GovernmentContractMilestone.estado == "VIGENTE",
                )
            ).scalars()
            if str(fila.id) not in cumplidos
        ]

    else:
        if db.scalar(
            select(GovernmentContractReceipt.id).where(
                GovernmentContractReceipt.contract_id == contrato_id,
                GovernmentContractReceipt.tipo == "DEFINITIVA",
                GovernmentContractReceipt.estado == "CONFORME",
            )
        ):
            raise ConflictError("GOV_CONTRACT_EXEC_CONFLICT", "La recepción definitiva ya está registrada")
        if flujo == "OBRAS":
            provisional = db.scalar(
                select(GovernmentContractReceipt).where(
                    GovernmentContractReceipt.contract_id == contrato_id,
                    GovernmentContractReceipt.tipo == "PROVISIONAL",
                    GovernmentContractReceipt.estado == "CONFORME",
                )
            )
            if provisional is None:
                raise ConflictError(
                    "GOV_CONTRACT_EXEC_RECEIPT_NOT_READY",
                    "Registre primero la aceptación provisional",
                )
            fin = provisional.fin_garantia
            if fin is None:
                raise ConflictError(
                    "GOV_CONTRACT_EXEC_RECEIPT_NOT_READY",
                    "Registre primero la aceptación provisional",
                )
            if fecha < fin:
                raise ConflictError(
                    "GOV_CONTRACT_EXEC_WARRANTY_PENDING",
                    f"El lapso de garantía termina el {fin:%d/%m/%Y}",
                    details={"fin_garantia": fin.isoformat()},
                )
        pend = _pendientes(db, contrato_id, None)
        if pend:
            raise ConflictError(
                "GOV_CONTRACT_EXEC_RECEIPT_NOT_READY",
                "Faltan entregables conformes",
                details={"pendientes": pend},
            )
        terminos = terminos_efectivos(db, contrato, fecha)
        conformado = _suma(
            db,
            GovernmentContractValuation.monto,
            GovernmentContractValuation.contract_id == contrato_id,
            GovernmentContractValuation.estado == "CONFORMADA",
        )
        if conformado > terminos["monto"]:
            raise ConflictError(
                "GOV_CONTRACT_EXEC_RECEIPT_NOT_READY",
                "No se puede recibir: hay sobreejecución del contrato",
                details={"excedente": _t(conformado - terminos["monto"])},
            )
        hito_ids_a_vincular = [
            str(fila.id)
            for fila in db.execute(
                select(GovernmentContractMilestone).where(
                    GovernmentContractMilestone.contract_id == contrato_id,
                    GovernmentContractMilestone.estado == "VIGENTE",
                )
            ).scalars()
            if str(fila.id) not in cumplidos
        ]
    if (tipo in ("PROVISIONAL", "DEFINITIVA") and flujo == "OBRAS") and representante_cargo_id is None:
        raise _inv(
            "representante_cargo_id",
            "Indique el cargo del representante del contratante",
            "GOV_CONTRACT_EXEC_REPRESENTATIVE_INVALID",
        )
    if representante_cargo_id is not None and not (tipo in ("PROVISIONAL", "DEFINITIVA") and flujo == "OBRAS"):
        raise _inv(
            "representante_cargo_id",
            "El representante solo se indica en la aceptación provisional o la recepción definitiva de obras",
            "GOV_CONTRACT_EXEC_REPRESENTATIVE_INVALID",
        )
    representante_cargo: GovernmentPosition | None = None
    if representante_cargo_id is not None:
        representante_cargo = db.scalar(
            select(GovernmentPosition).where(
                GovernmentPosition.company_id == ctx.company_id,
                GovernmentPosition.id == representante_cargo_id,
            )
        )
        if representante_cargo is None or not _autoridad_valida(
            db,
            ctx.company_id,
            representante_cargo_id,
            fecha,
            "APROBAR",
            "CONTRATACIONES",
        ):
            _bloqueo(db, ctx, contrato, "GOV_CONTRACT_EXEC_REPRESENTATIVE_INVALID")
            raise _inv(
                "representante_cargo_id",
                "El representante del contratante debe ocupar un cargo con la competencia Aprobar sobre Contrataciones",
                "GOV_CONTRACT_EXEC_REPRESENTATIVE_INVALID",
            )
    if fin_garantia is not None and tipo != "PROVISIONAL":
        fin_garantia = None

    sup = _conformante(db, ctx, contrato, fecha)
    evaluar_antes_de_actuar(db, ctx, "PROC03_EJEC_RECIBIR", ENTIDAD, str(contrato.file_id))
    r = _documento(db, ctx, contrato, cuerpo["documento_id"], "documento_id")
    numero = _siguiente(db, GovernmentContractReceipt, contrato_id)
    recepcion = GovernmentContractReceipt(
        company_id=ctx.company_id,
        contract_id=contrato_id,
        numero=numero,
        tipo=tipo,
        fecha=fecha,
        observacion=(cuerpo.get("observacion") or "").strip() or None,
        **_doc(r),
        **_sup(sup),
        representante_cargo_id=representante_cargo_id,
        representante_cargo_nombre=representante_cargo.name if representante_cargo else None,
        fin_garantia=fin_garantia,
        estado="CONFORME",
        registrado_en=instante_actual(),
        registrado_por=ctx.user_id,
        created_by=ctx.user_id,
    )
    db.add(recepcion)
    db.flush()
    for hito_id in hito_ids_a_vincular:
        db.add(
            GovernmentContractReceiptMilestone(
                company_id=ctx.company_id,
                contract_id=contrato_id,
                receipt_id=str(recepcion.id),
                milestone_id=str(hito_id),
                created_by=ctx.user_id,
            )
        )
    _flush(
        db,
        {
            "uq_gov_contract_receipts_definitiva": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            ),
            "uq_gov_contract_receipts_provisional": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            ),
            "uq_gov_contract_receipts_numero": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            ),
            "uq_gov_contract_receipt_milestones": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            ),
        },
    )
    etiqueta = ETIQUETA_RECEPCION[tipo]
    _sellar(db, ctx, contrato, r, f"Acta de recepción REC-{numero:02d} de {contrato.codigo} (CNT-03)")
    _cronologia_expediente(
        db,
        ctx,
        contrato,
        fecha,
        f"Recepción {etiqueta} REC-{numero:02d} de {contrato.codigo}",
        detalle="",
    )
    hitos_ref = ", ".join(
        f"HIT-{db.scalar(select(GovernmentContractMilestone.numero).where(GovernmentContractMilestone.id == hito_id)):02d}"
        for hito_id in hito_ids_a_vincular
    )
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_RECEIPT_RECORDED",
        {
            "contrato": contrato.codigo,
            "recepcion": f"REC-{numero:02d}",
            "tipo": tipo,
            "fecha": fecha.isoformat(),
            "hito": hitos_ref or None,
            "supervisor": sup["funcionario"]["nombre"],
        },
    )
    return ejecucion(db, ctx, contrato_id)


def anular_recepcion(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    recepcion_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    contrato, _exp, _actos = _preparar(db, ctx, contrato_id, True)
    recepcion = db.scalar(
        select(GovernmentContractReceipt).where(
            GovernmentContractReceipt.id == recepcion_id,
            GovernmentContractReceipt.contract_id == contrato_id,
        )
    )
    if recepcion is None or recepcion.estado != "CONFORME" or recepcion.tipo != "PARCIAL":
        raise ConflictError(
            "GOV_CONTRACT_EXEC_IN_USE",
            "Solo se anula una recepción parcial sin facturas ni recepción definitiva",
        )
    hay_factura = db.scalar(
        select(GovernmentContractInvoice.id).where(
            GovernmentContractInvoice.receipt_id == recepcion_id,
            GovernmentContractInvoice.estado == "CONFORME",
        )
    )
    hay_definitiva = db.scalar(
        select(GovernmentContractReceipt.id).where(
            GovernmentContractReceipt.contract_id == contrato_id,
            GovernmentContractReceipt.tipo == "DEFINITIVA",
            GovernmentContractReceipt.estado == "CONFORME",
        )
    )
    if hay_factura is not None or hay_definitiva is not None:
        raise ConflictError(
            "GOV_CONTRACT_EXEC_IN_USE",
            "Solo se anula una recepción parcial sin facturas ni recepción definitiva",
        )
    motivo = (cuerpo["motivo"] or "").strip()
    if not motivo:
        raise _inv("motivo", "Indique el motivo", "GOV_CONTRACT_EXEC_REASON_REQUIRED")
    recepcion.estado = "ANULADA"
    recepcion.motivo_anulacion = motivo
    recepcion.anulado_en = instante_actual()
    recepcion.anulado_por = ctx.user_id
    recepcion.version += 1
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_RECEIPT_CANCELLED",
        {"contrato": contrato.codigo, "recepcion": f"REC-{recepcion.numero:02d}", "motivo": motivo},
    )
    return ejecucion(db, ctx, contrato_id)


def vincular_factura(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    contrato, _exp, actos = _preparar(db, ctx, contrato_id, True)
    numero_documento = (cuerpo["numero_documento"] or "").strip()
    if not numero_documento:
        raise _inv("numero_documento", "Indique el número del documento", "GOV_CONTRACT_EXEC_REASON_REQUIRED")
    fecha: date = cuerpo["fecha"]
    _fecha_hecho(fecha, actos, "fecha")
    fecha_conformidad: date = cuerpo["fecha_conformidad"]
    if fecha_conformidad < fecha or fecha_conformidad > hoy_de_negocio():
        raise _inv(
            "fecha_conformidad",
            "La fecha de conformidad debe estar entre la factura y hoy",
            "GOV_CONTRACT_EXEC_DATE_INVALID",
        )
    hito = db.scalar(
        select(GovernmentContractMilestone).where(
            GovernmentContractMilestone.id == cuerpo["hito_id"],
            GovernmentContractMilestone.contract_id == contrato_id,
            GovernmentContractMilestone.estado == "VIGENTE",
        )
    )
    if hito is None:
        raise _inv("hito_id", "Elija un hito vigente", "GOV_CONTRACT_EXEC_MILESTONE_INVALID")
    recepcion = db.scalar(
        select(GovernmentContractReceipt).where(
            GovernmentContractReceipt.id == cuerpo["recepcion_id"],
            GovernmentContractReceipt.contract_id == contrato_id,
            GovernmentContractReceipt.estado == "CONFORME",
        )
    )
    vinculo = (
        db.scalar(
            select(GovernmentContractReceiptMilestone.id).where(
                GovernmentContractReceiptMilestone.receipt_id == cuerpo["recepcion_id"],
                GovernmentContractReceiptMilestone.milestone_id == cuerpo["hito_id"],
            )
        )
        if recepcion is not None
        else None
    )
    if recepcion is None or vinculo is None:
        _bloqueo(db, ctx, contrato, "GOV_CONTRACT_EXEC_RECEIPT_INVALID")
        raise _inv(
            "recepcion_id",
            "La factura requiere una recepción conforme de este contrato que incluya el hito",
            "GOV_CONTRACT_EXEC_RECEIPT_INVALID",
        )
    duplicado = db.scalar(
        select(GovernmentContractInvoice.id).where(
            GovernmentContractInvoice.contract_id == contrato_id,
            GovernmentContractInvoice.numero_documento == numero_documento,
            GovernmentContractInvoice.estado == "CONFORME",
        )
    )
    if duplicado is not None:
        raise ConflictError(
            "GOV_CONTRACT_EXEC_INVOICE_DUPLICATE",
            "Ya hay una factura conforme con ese número",
        )
    monto = Decimal(cuerpo["monto"])
    facturado = _suma(
        db,
        GovernmentContractInvoice.monto,
        GovernmentContractInvoice.milestone_id == cuerpo["hito_id"],
        GovernmentContractInvoice.estado == "CONFORME",
    )
    valuado = _suma(
        db,
        GovernmentContractValuation.monto,
        GovernmentContractValuation.milestone_id == cuerpo["hito_id"],
        GovernmentContractValuation.estado == "CONFORMADA",
    )
    if facturado + monto > valuado:
        _bloqueo(db, ctx, contrato, "GOV_CONTRACT_EXEC_INVOICE_EXCEEDS_VALUED")
        raise _inv(
            "monto",
            f"La factura supera lo valuado y conformado del hito: disponible "
            f"{_t(valuado - facturado)} {contrato.moneda}",
            "GOV_CONTRACT_EXEC_INVOICE_EXCEEDS_VALUED",
        )
    sup = _conformante(db, ctx, contrato, fecha_conformidad)
    evaluar_antes_de_actuar(db, ctx, "PROC03_EJEC_FACTURA", ENTIDAD, str(contrato.file_id))
    r = _documento(db, ctx, contrato, cuerpo["documento_id"], "documento_id")
    numero = _siguiente(db, GovernmentContractInvoice, contrato_id)
    factura = GovernmentContractInvoice(
        company_id=ctx.company_id,
        contract_id=contrato_id,
        numero=numero,
        numero_documento=numero_documento,
        fecha=fecha,
        monto=monto,
        moneda=contrato.moneda,
        milestone_id=str(hito.id),
        receipt_id=str(recepcion.id),
        **_doc(r),
        fecha_conformidad=fecha_conformidad,
        **_sup(sup),
        estado="CONFORME",
        registrado_en=instante_actual(),
        registrado_por=ctx.user_id,
        created_by=ctx.user_id,
    )
    db.add(factura)
    _flush(
        db,
        {
            "uq_gov_contract_invoices_documento": (
                "GOV_CONTRACT_EXEC_INVOICE_DUPLICATE",
                "Ya hay una factura conforme con ese número",
            ),
            "uq_gov_contract_invoices_numero": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            ),
        },
    )
    _sellar(db, ctx, contrato, r, f"Factura FAC-{numero:02d} de {contrato.codigo} (CNT-03)")
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_INVOICE_LINKED",
        {
            "contrato": contrato.codigo,
            "factura": f"FAC-{numero:02d}",
            "hito": f"HIT-{hito.numero:02d}",
            "recepcion": f"REC-{recepcion.numero:02d}",
            "monto": _t(monto),
            "moneda": contrato.moneda,
            "supervisor": sup["funcionario"]["nombre"],
        },
    )
    return ejecucion(db, ctx, contrato_id)


def anular_factura(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    factura_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    contrato, _exp, _actos = _preparar(db, ctx, contrato_id, True)
    factura = db.scalar(
        select(GovernmentContractInvoice).where(
            GovernmentContractInvoice.id == factura_id,
            GovernmentContractInvoice.contract_id == contrato_id,
        )
    )
    if factura is None or factura.estado != "CONFORME":
        raise ConflictError("GOV_CONTRACT_EXEC_IN_USE", "Solo se anula una factura conforme")
    motivo = (cuerpo["motivo"] or "").strip()
    if not motivo:
        raise _inv("motivo", "Indique el motivo", "GOV_CONTRACT_EXEC_REASON_REQUIRED")
    factura.estado = "ANULADA"
    factura.motivo_anulacion = motivo
    factura.anulado_en = instante_actual()
    factura.anulado_por = ctx.user_id
    factura.version += 1
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_INVOICE_CANCELLED",
        {"contrato": contrato.codigo, "factura": f"FAC-{factura.numero:02d}", "motivo": motivo},
    )
    return ejecucion(db, ctx, contrato_id)


def cerrar(db: Session, ctx: CompanyContext, contrato_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    contrato, expediente, actos = _preparar(db, ctx, contrato_id, True)
    definitiva = db.scalar(
        select(GovernmentContractReceipt).where(
            GovernmentContractReceipt.contract_id == contrato_id,
            GovernmentContractReceipt.tipo == "DEFINITIVA",
            GovernmentContractReceipt.estado == "CONFORME",
        )
    )
    if definitiva is None:
        raise ConflictError(
            "GOV_CONTRACT_EXEC_NOT_CLOSABLE",
            "El cierre requiere la recepción definitiva",
        )
    fecha: date = cuerpo["fecha"]
    if fecha < definitiva.fecha or fecha > hoy_de_negocio():
        raise _inv(
            "fecha",
            "La fecha debe estar entre la recepción definitiva y hoy",
            "GOV_CONTRACT_EXEC_DATE_INVALID",
        )
    if cuerpo["documento_id"] == cuerpo["evaluacion_documento_id"]:
        raise _inv(
            "evaluacion_documento_id",
            "El acta de aprobación y la evaluación deben ser documentos distintos",
            "GOV_CONTRACT_EXEC_DOCUMENT_INVALID",
        )
    r1 = _documento(db, ctx, contrato, cuerpo["documento_id"], "documento_id")
    r2 = _documento(db, ctx, contrato, cuerpo["evaluacion_documento_id"], "evaluacion_documento_id")
    sup = supervisor_en(db, ctx, str(contrato.id), fecha)
    if sup is None:
        _bloqueo(db, ctx, contrato, "GOV_CONTRACT_EXEC_NO_SUPERVISOR")
        raise ConflictError(
            "GOV_CONTRACT_EXEC_NO_SUPERVISOR",
            f"El contrato no tenía supervisor el {fecha:%d/%m/%Y}",
        )
    if expediente.committee_id:
        comite = db.scalar(
            select(GovernmentProcurementCommittee).where(
                GovernmentProcurementCommittee.id == expediente.committee_id
            )
        )
        aprobador_tipo = "COMISION"
        aprobador_nombre = comite.nombre if comite else None
    else:
        aprobador_tipo = "UNIDAD_CONTRATANTE"
        aprobador_nombre = expediente.unidad_nombre
    evaluar_antes_de_actuar(db, ctx, "PROC03_EJEC_CERRAR", ENTIDAD, str(contrato.file_id))
    doc1 = _doc(r1)
    doc2 = _doc(r2)
    acto = GovernmentContractExecutionAct(
        company_id=ctx.company_id,
        contract_id=str(contrato.id),
        tipo="CIERRE",
        fecha=fecha,
        observacion=(cuerpo.get("observacion") or "").strip() or None,
        **_sup(sup),
        **doc1,
        aprobacion_document_id=doc1["document_id"],
        aprobacion_document_version_id=doc1["document_version_id"],
        aprobacion_sha256=doc1["documento_sha256"],
        aprobacion_titulo=doc1["documento_titulo"],
        evaluacion_document_id=doc2["document_id"],
        evaluacion_document_version_id=doc2["document_version_id"],
        evaluacion_sha256=doc2["documento_sha256"],
        evaluacion_titulo=doc2["documento_titulo"],
        aprobador_tipo=aprobador_tipo,
        aprobador_nombre=aprobador_nombre,
        registrado_en=instante_actual(),
        registrado_por=ctx.user_id,
        created_by=ctx.user_id,
    )
    db.add(acto)
    _flush(
        db,
        {
            "uq_gov_contract_execution_acts_tipo": (
                "GOV_CONTRACT_EXEC_CONFLICT",
                "Otra actuación se registró al mismo tiempo: recargue la página",
            )
        },
    )
    _sellar(db, ctx, contrato, r1, f"Acta de cierre de {contrato.codigo} (CNT-03)")
    _sellar(db, ctx, contrato, r2, f"Evaluación del cierre de {contrato.codigo} (CNT-03)")
    _cronologia_expediente(db, ctx, contrato, fecha, f"Cierre operativo de {contrato.codigo}", detalle="")
    _auditar(
        db,
        ctx,
        contrato,
        "GOV_CONTRACT_EXEC_CLOSED",
        {
            "contrato": contrato.codigo,
            "fecha": fecha.isoformat(),
            "aprobador": aprobador_nombre,
            "documento": r1[0].title,
        },
    )
    return ejecucion(db, ctx, contrato_id)


def ejecucion(db: Session, ctx: CompanyContext, contrato_id: str) -> dict[str, Any]:
    contrato = _contrato(db, ctx, contrato_id, False)
    expediente = _expediente(db, ctx, contrato)
    actos = _actos(db, str(contrato.id))
    flujo = _flujo(expediente)
    terminos = terminos_efectivos(db, contrato, hoy_de_negocio())
    cumplidos = _cumplidos(db, contrato_id)

    valuado_conformado = _suma(
        db,
        GovernmentContractValuation.monto,
        GovernmentContractValuation.contract_id == contrato_id,
        GovernmentContractValuation.estado == "CONFORMADA",
    )
    valuado_presentado = _suma(
        db,
        GovernmentContractValuation.monto,
        GovernmentContractValuation.contract_id == contrato_id,
        GovernmentContractValuation.estado == "PRESENTADA",
    )
    facturado = _suma(
        db,
        GovernmentContractInvoice.monto,
        GovernmentContractInvoice.contract_id == contrato_id,
        GovernmentContractInvoice.estado == "CONFORME",
    )
    hitos_total = db.scalar(
        select(func.count(GovernmentContractMilestone.id)).where(
            GovernmentContractMilestone.contract_id == contrato_id,
            GovernmentContractMilestone.estado == "VIGENTE",
        )
    )
    entregables_pendientes = db.scalar(
        select(func.count(GovernmentContractDeliverable.id)).where(
            GovernmentContractDeliverable.contract_id == contrato_id,
            GovernmentContractDeliverable.estado == "VIGENTE",
        )
    )
    hitos_cumplidos = len([k for k in cumplidos if k])

    if "CIERRE" in actos:
        estado_ejecucion = "CERRADA"
    elif db.scalar(
        select(GovernmentContractReceipt.id).where(
            GovernmentContractReceipt.contract_id == contrato_id,
            GovernmentContractReceipt.tipo == "DEFINITIVA",
            GovernmentContractReceipt.estado == "CONFORME",
        )
    ):
        estado_ejecucion = "RECIBIDA_DEFINITIVA"
    elif db.scalar(
        select(GovernmentContractReceipt.id).where(
            GovernmentContractReceipt.contract_id == contrato_id,
            GovernmentContractReceipt.tipo == "PROVISIONAL",
            GovernmentContractReceipt.estado == "CONFORME",
        )
    ):
        estado_ejecucion = "RECIBIDA_PROVISIONAL"
    elif "TERMINACION" in actos:
        estado_ejecucion = "TERMINADA"
    elif "INICIO" in actos:
        estado_ejecucion = "EN_EJECUCION"
    else:
        estado_ejecucion = "SIN_INICIAR"

    sup_vigente = supervisor_vigente(db, ctx, contrato_id)
    resultado: dict[str, Any] = {
        "contrato": {
            "id": str(contrato.id),
            "codigo": contrato.codigo,
            "objeto": contrato.objeto,
            "contratista": contrato.contratista_nombre,
            "estado": contrato.estado,
            "tipo_contratacion": expediente.tipo_contratacion,
            "flujo": flujo,
            "moneda": contrato.moneda,
            "expediente_id": str(contrato.file_id),
        },
        "terminos": {
            "monto_original": _t(terminos["monto_original"]),
            "monto_efectivo": _t(terminos["monto"]),
            "moneda": terminos["moneda"],
            "fecha_inicio": terminos["fecha_inicio"].isoformat() if terminos["fecha_inicio"] else None,
            "fecha_fin": terminos["fecha_fin"].isoformat() if terminos["fecha_fin"] else None,
            "fuente": terminos["fuente"],
            "modificacion": terminos["modificacion"],
        },
        "resumen": {
            "estado_ejecucion": estado_ejecucion,
            "estado_etiqueta": ETIQUETA_ESTADO_EJECUCION[estado_ejecucion],
            "valuado_conformado": _t(valuado_conformado),
            "valuado_presentado": _t(valuado_presentado),
            "saldo": _t(terminos["monto"] - valuado_conformado - valuado_presentado),
            "facturado": _t(facturado),
            "hitos_total": int(hitos_total or 0),
            "hitos_cumplidos": hitos_cumplidos,
            "entregables_pendientes": int(entregables_pendientes or 0),
            "supervisor": (
                {
                    "asignacion_id": sup_vigente["id"],
                    "referencia": sup_vigente["referencia"],
                    "nombre": sup_vigente["funcionario"]["nombre"],
                    "cargo": sup_vigente["cargo"]["nombre"],
                }
                if sup_vigente
                else None
            ),
        },
    }

    inicio = actos.get("INICIO")
    resultado["inicio"] = (
        {
            "id": str(inicio.id),
            "fecha": inicio.fecha.isoformat(),
            "observacion": inicio.observacion,
            "supervisor": inicio.supervisor_nombre,
            "documento": {"id": str(inicio.document_id), "titulo": inicio.documento_titulo},
        }
        if inicio
        else None
    )
    terminacion = actos.get("TERMINACION")
    resultado["terminacion"] = (
        {
            "id": str(terminacion.id),
            "fecha": terminacion.fecha.isoformat(),
            "observacion": terminacion.observacion,
            "supervisor": terminacion.supervisor_nombre,
            "documento": {"id": str(terminacion.document_id), "titulo": terminacion.documento_titulo},
        }
        if terminacion
        else None
    )
    cierre = actos.get("CIERRE")
    resultado["cierre"] = (
        {
            "id": str(cierre.id),
            "fecha": cierre.fecha.isoformat(),
            "observacion": cierre.observacion,
            "supervisor": cierre.supervisor_nombre,
            "documento": {"id": str(cierre.document_id), "titulo": cierre.documento_titulo},
            "aprobador_tipo": cierre.aprobador_tipo,
            "aprobador_nombre": cierre.aprobador_nombre,
            "evaluacion": {
                "id": str(cierre.evaluacion_document_id),
                "titulo": cierre.evaluacion_titulo,
            },
        }
        if cierre
        else None
    )

    hitos = db.execute(
        select(GovernmentContractMilestone)
        .where(GovernmentContractMilestone.contract_id == contrato_id)
        .order_by(GovernmentContractMilestone.numero)
    ).scalars().all()
    resultado["hitos"] = [
        {
            "id": str(hito.id),
            "referencia": f"HIT-{hito.numero:02d}",
            "descripcion": hito.descripcion,
            "fecha_prevista": hito.fecha_prevista.isoformat(),
            "monto_previsto": _t(Decimal(hito.monto_previsto)) if hito.monto_previsto is not None else None,
            "porcentaje_previsto": (
                _t(Decimal(hito.porcentaje_previsto)) if hito.porcentaje_previsto is not None else None
            ),
            "obligatorio": hito.obligatorio,
            "estado": hito.estado,
            "cumplido": str(hito.id) in cumplidos,
            "recepcion": cumplidos.get(str(hito.id)),
            "valuado_conformado": _t(
                _suma(
                    db,
                    GovernmentContractValuation.monto,
                    GovernmentContractValuation.milestone_id == hito.id,
                    GovernmentContractValuation.estado == "CONFORMADA",
                )
            ),
            "facturado": _t(
                _suma(
                    db,
                    GovernmentContractInvoice.monto,
                    GovernmentContractInvoice.milestone_id == hito.id,
                    GovernmentContractInvoice.estado == "CONFORME",
                )
            ),
            "motivo_anulacion": hito.motivo_anulacion,
        }
        for hito in hitos
    ]

    entregables = db.execute(
        select(GovernmentContractDeliverable)
        .where(GovernmentContractDeliverable.contract_id == contrato_id)
        .order_by(GovernmentContractDeliverable.numero)
    ).scalars().all()
    resultado_entregables: list[dict[str, Any]] = []
    for entregable in entregables:
        entregas = db.execute(
            select(GovernmentContractDeliverableSubmission)
            .where(GovernmentContractDeliverableSubmission.deliverable_id == entregable.id)
            .order_by(GovernmentContractDeliverableSubmission.numero)
        ).scalars().all()
        situacion = "PENDIENTE"
        if any(entrega.estado == "CONFORME" for entrega in entregas):
            situacion = "CONFORME"
        elif entregas and entregas[-1].estado == "ENTREGADA":
            situacion = "ENTREGADO"
        elif entregas and entregas[-1].estado == "RECHAZADA":
            situacion = "RECHAZADO"
        resultado_entregables.append(
            {
                "id": str(entregable.id),
                "referencia": f"ENT-{entregable.numero:02d}",
                "hito_id": str(entregable.milestone_id) if entregable.milestone_id else None,
                "hito": (
                    f"HIT-{db.scalar(select(GovernmentContractMilestone.numero).where(GovernmentContractMilestone.id == entregable.milestone_id)):02d}"
                    if entregable.milestone_id
                    else None
                ),
                "descripcion": entregable.descripcion,
                "fecha_vencimiento": entregable.fecha_vencimiento.isoformat(),
                "obligatorio": entregable.obligatorio,
                "estado": entregable.estado,
                "situacion": situacion,
                "entregas": [
                    {
                        "id": str(entrega.id),
                        "referencia": f"ENT-{entregable.numero:02d}/{entrega.numero:02d}",
                        "fecha_entrega": entrega.fecha_entrega.isoformat(),
                        "documento": {"id": str(entrega.document_id), "titulo": entrega.documento_titulo},
                        "estado": entrega.estado,
                        "fecha_revision": entrega.fecha_revision.isoformat() if entrega.fecha_revision else None,
                        "observacion_revision": entrega.observacion_revision,
                        "supervisor": entrega.supervisor_nombre,
                    }
                    for entrega in entregas
                ],
                "motivo_anulacion": entregable.motivo_anulacion,
            }
        )
    resultado["entregables"] = resultado_entregables

    valuaciones = db.execute(
        select(GovernmentContractValuation)
        .where(GovernmentContractValuation.contract_id == contrato_id)
        .order_by(GovernmentContractValuation.numero)
    ).scalars().all()
    resultado["valuaciones"] = [
        {
            "id": str(valuacion.id),
            "referencia": f"VAL-{valuacion.numero:02d}",
            "hito_id": str(valuacion.milestone_id),
            "hito": f"HIT-{db.scalar(select(GovernmentContractMilestone.numero).where(GovernmentContractMilestone.id == valuacion.milestone_id)):02d}",
            "periodo_desde": valuacion.periodo_desde.isoformat(),
            "periodo_hasta": valuacion.periodo_hasta.isoformat(),
            "fecha": valuacion.fecha.isoformat(),
            "monto": _t(Decimal(valuacion.monto)),
            "moneda": valuacion.moneda,
            "estado": valuacion.estado,
            "estado_etiqueta": ETIQUETA_VALUACION[valuacion.estado],
            "fecha_conformidad": valuacion.fecha_conformidad.isoformat() if valuacion.fecha_conformidad else None,
            "acumulado": _t(Decimal(valuacion.acumulado)) if valuacion.acumulado is not None else None,
            "reparos": valuacion.reparos,
            "supervisor": valuacion.supervisor_nombre,
            "documento": {"id": str(valuacion.document_id), "titulo": valuacion.documento_titulo},
            "motivo_anulacion": valuacion.motivo_anulacion,
        }
        for valuacion in valuaciones
    ]

    recepciones = db.execute(
        select(GovernmentContractReceipt)
        .where(GovernmentContractReceipt.contract_id == contrato_id)
        .order_by(GovernmentContractReceipt.numero)
    ).scalars().all()
    resultado_recepciones: list[dict[str, Any]] = []
    for recepcion in recepciones:
        vinculos = db.execute(
            select(GovernmentContractReceiptMilestone)
            .where(GovernmentContractReceiptMilestone.receipt_id == recepcion.id)
        ).scalars().all()
        hito_ids = [str(vinculo.milestone_id) for vinculo in vinculos]
        hitos_ref = [
            f"HIT-{db.scalar(select(GovernmentContractMilestone.numero).where(GovernmentContractMilestone.id == hito_id)):02d}"
            for hito_id in hito_ids
        ]
        resultado_recepciones.append(
            {
                "id": str(recepcion.id),
                "referencia": f"REC-{recepcion.numero:02d}",
                "tipo": recepcion.tipo,
                "tipo_etiqueta": ETIQUETA_RECEPCION[recepcion.tipo],
                "fecha": recepcion.fecha.isoformat(),
                "hitos": hitos_ref,
                "hito_ids": hito_ids,
                "supervisor": recepcion.supervisor_nombre,
                "representante": recepcion.representante_cargo_nombre,
                "fin_garantia": recepcion.fin_garantia.isoformat() if recepcion.fin_garantia else None,
                "documento": {"id": str(recepcion.document_id), "titulo": recepcion.documento_titulo},
                "observacion": recepcion.observacion,
                "estado": recepcion.estado,
                "motivo_anulacion": recepcion.motivo_anulacion,
            }
        )
    resultado["recepciones"] = resultado_recepciones

    facturas = db.execute(
        select(GovernmentContractInvoice)
        .where(GovernmentContractInvoice.contract_id == contrato_id)
        .order_by(GovernmentContractInvoice.numero)
    ).scalars().all()
    resultado["facturas"] = [
        {
            "id": str(factura.id),
            "referencia": f"FAC-{factura.numero:02d}",
            "numero_documento": factura.numero_documento,
            "fecha": factura.fecha.isoformat(),
            "monto": _t(Decimal(factura.monto)),
            "moneda": factura.moneda,
            "hito_id": str(factura.milestone_id),
            "hito": f"HIT-{db.scalar(select(GovernmentContractMilestone.numero).where(GovernmentContractMilestone.id == factura.milestone_id)):02d}",
            "recepcion_id": str(factura.receipt_id),
            "recepcion": f"REC-{db.scalar(select(GovernmentContractReceipt.numero).where(GovernmentContractReceipt.id == factura.receipt_id)):02d}",
            "fecha_conformidad": factura.fecha_conformidad.isoformat(),
            "supervisor": factura.supervisor_nombre,
            "documento": {"id": str(factura.document_id), "titulo": factura.documento_titulo},
            "estado": factura.estado,
            "motivo_anulacion": factura.motivo_anulacion,
        }
        for factura in facturas
    ]

    cronologia: list[dict[str, Any]] = []
    for acto_tipo in ("INICIO", "TERMINACION", "CIERRE"):
        acto = actos.get(acto_tipo)
        if acto is not None:
            cronologia.append(
                {
                    "fecha": acto.fecha.isoformat(),
                    "tipo": acto_tipo.lower(),
                    "referencia": acto_tipo,
                    "titulo": acto.documento_titulo or "",
                    "monto": None,
                    "moneda": None,
                    "estado": acto_tipo,
                }
            )
    for hito in hitos:
        cronologia.append(
            {
                "fecha": hito.registrado_en.date().isoformat() if hito.registrado_en else hito.fecha_prevista.isoformat(),
                "tipo": "hito",
                "referencia": f"HIT-{hito.numero:02d}",
                "titulo": hito.descripcion,
                "monto": _t(Decimal(hito.monto_previsto)) if hito.monto_previsto is not None else None,
                "moneda": contrato.moneda,
                "estado": hito.estado,
            }
        )
    for entregable in entregables:
        for entrega in db.execute(
            select(GovernmentContractDeliverableSubmission)
            .where(GovernmentContractDeliverableSubmission.deliverable_id == entregable.id)
            .order_by(GovernmentContractDeliverableSubmission.numero)
        ).scalars().all():
            cronologia.append(
                {
                    "fecha": entrega.fecha_entrega.isoformat(),
                    "tipo": "entrega",
                    "referencia": f"ENT-{entregable.numero:02d}/{entrega.numero:02d}",
                    "titulo": entrega.documento_titulo or "",
                    "monto": None,
                    "moneda": None,
                    "estado": entrega.estado,
                }
            )
            if entrega.fecha_revision is not None:
                cronologia.append(
                    {
                        "fecha": entrega.fecha_revision.isoformat(),
                        "tipo": "revision_entrega",
                        "referencia": f"ENT-{entregable.numero:02d}/{entrega.numero:02d}",
                        "titulo": entrega.observacion_revision or "",
                        "monto": None,
                        "moneda": None,
                        "estado": entrega.estado,
                    }
                )
    for valuacion in valuaciones:
        cronologia.append(
            {
                "fecha": valuacion.fecha.isoformat(),
                "tipo": "valuacion",
                "referencia": f"VAL-{valuacion.numero:02d}",
                "titulo": valuacion.documento_titulo or "",
                "monto": _t(Decimal(valuacion.monto)),
                "moneda": valuacion.moneda,
                "estado": valuacion.estado,
            }
        )
        if valuacion.fecha_conformidad is not None:
            cronologia.append(
                {
                    "fecha": valuacion.fecha_conformidad.isoformat(),
                    "tipo": "resolucion_valuacion",
                    "referencia": f"VAL-{valuacion.numero:02d}",
                    "titulo": valuacion.reparos or "",
                    "monto": _t(Decimal(valuacion.acumulado)) if valuacion.acumulado is not None else None,
                    "moneda": valuacion.moneda,
                    "estado": valuacion.estado,
                }
            )
    for recepcion in recepciones:
        cronologia.append(
            {
                "fecha": recepcion.fecha.isoformat(),
                "tipo": "recepcion",
                "referencia": f"REC-{recepcion.numero:02d}",
                "titulo": recepcion.documento_titulo or "",
                "monto": None,
                "moneda": None,
                "estado": recepcion.estado,
            }
        )
    for factura in facturas:
        cronologia.append(
            {
                "fecha": factura.fecha_conformidad.isoformat(),
                "tipo": "factura",
                "referencia": f"FAC-{factura.numero:02d}",
                "titulo": factura.numero_documento,
                "monto": _t(Decimal(factura.monto)),
                "moneda": factura.moneda,
                "estado": factura.estado,
            }
        )
    cronologia.sort(key=lambda fila: (fila["fecha"], fila["referencia"]))
    resultado["cronologia"] = cronologia

    actor_id = _funcionario_del_actor(db, ctx)
    soy_supervisor = (
        sup_vigente is not None and actor_id is not None and sup_vigente["funcionario"]["id"] == actor_id
    )
    hay_inicio = "INICIO" in actos
    hay_terminacion = "TERMINACION" in actos
    hay_definitiva = db.scalar(
        select(GovernmentContractReceipt.id).where(
            GovernmentContractReceipt.contract_id == contrato_id,
            GovernmentContractReceipt.tipo == "DEFINITIVA",
            GovernmentContractReceipt.estado == "CONFORME",
        )
    )
    hay_provisional = db.scalar(
        select(GovernmentContractReceipt.id).where(
            GovernmentContractReceipt.contract_id == contrato_id,
            GovernmentContractReceipt.tipo == "PROVISIONAL",
            GovernmentContractReceipt.estado == "CONFORME",
        )
    )
    hay_cierre = "CIERRE" in actos
    resultado["acciones"] = {
        "iniciar": contrato.estado == "FORMALIZADO" and not hay_inicio and not hay_cierre,
        "registrar": contrato.estado == "FORMALIZADO" and not hay_cierre,
        "registrar_hechos": contrato.estado == "FORMALIZADO" and hay_inicio and not hay_cierre,
        "terminar": flujo == "OBRAS" and hay_inicio and not hay_terminacion and not hay_cierre,
        "recepcion_parcial": flujo == "BIENES_SERVICIOS"
        and hay_inicio
        and not hay_definitiva
        and not hay_cierre,
        "recepcion_provisional": flujo == "OBRAS"
        and hay_terminacion
        and not hay_provisional
        and not hay_cierre,
        "recepcion_definitiva": hay_inicio
        and not hay_definitiva
        and not hay_cierre
        and (flujo == "BIENES_SERVICIOS" or bool(hay_provisional)),
        "cerrar": bool(hay_definitiva) and not hay_cierre,
    }
    resultado["soy_supervisor"] = soy_supervisor
    return resultado


def opciones(db: Session, ctx: CompanyContext, contrato_id: str) -> dict[str, Any]:
    contrato = _contrato(db, ctx, contrato_id, False)
    expediente = _expediente(db, ctx, contrato)
    hoy = hoy_de_negocio()
    documentos = db.execute(
        select(Document)
        .where(
            Document.company_id == ctx.company_id,
            Document.status.in_(("DRAFT", "ACTIVE")),
            Document.current_version_id.is_not(None),
        )
        .order_by(Document.title)
    ).scalars().all()
    documentos_disponibles: list[dict[str, Any]] = []
    for doc in documentos:
        if documento_sellado(db, str(doc.id)):
            continue
        link = db.scalar(
            select(DocumentLink).where(
                DocumentLink.document_id == doc.id,
                DocumentLink.resource_type == "GovernmentProcurementFile",
                DocumentLink.resource_id == contrato.file_id,
            )
        )
        if link is None:
            continue
        version = db.scalar(
            select(DocumentVersion).where(
                DocumentVersion.id == doc.current_version_id,
                DocumentVersion.document_id == doc.id,
            )
        )
        if version is None:
            continue
        documentos_disponibles.append(
            {"id": str(doc.id), "titulo": doc.title, "version": str(version.id)}
        )
    representantes: list[dict[str, Any]] = []
    if _flujo(expediente) == "OBRAS":
        cargos = db.execute(
            select(GovernmentPosition).where(GovernmentPosition.company_id == ctx.company_id)
        ).scalars().all()
        for cargo in cargos:
            if _autoridad_valida(db, ctx.company_id, str(cargo.id), hoy, "APROBAR", "CONTRATACIONES"):
                representantes.append({"id": str(cargo.id), "codigo": cargo.code, "nombre": cargo.name})
    return {
        "hoy": hoy.isoformat(),
        "documentos": documentos_disponibles,
        "representantes": representantes,
    }


def reporte_csv(db: Session, ctx: CompanyContext, contrato_id: str) -> tuple[str, bytes]:
    datos = ejecucion(db, ctx, contrato_id)
    codigo = datos["contrato"]["codigo"]
    nombre = f"ejecucion_{codigo}.csv"
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["fecha", "tipo", "referencia", "titulo", "monto", "moneda", "estado"])
    for fila in datos["cronologia"]:
        writer.writerow(
            [
                fila["fecha"],
                fila["tipo"],
                fila["referencia"],
                fila["titulo"],
                fila["monto"] or "",
                fila["moneda"] or "",
                fila["estado"],
            ]
        )
    return nombre, buffer.getvalue().encode("utf-8")
