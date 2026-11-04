"""Servicio de dominio de los actos administrativos (GOV-DOC-02 · DOC-02)."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentLink
from app.modules.documents.service import freeze_links
from app.modules.government.models import (
    GovernmentAct,
    GovernmentActVersion,
    GovernmentNotification,
    GovernmentPosition,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.schemas_actos import (
    ActoCambio,
    ActoIn,
    CorreccionIn,
    EficaciaIn,
    EmisionIn,
    ReferenciaIn,
    validar_coherencia,
)
from app.modules.government.service_autoridad import competencias_en_vigor
from app.modules.government.service_estructura import _ente, _error_campo, _utc
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from app.shared.mixins import utcnow

ORDEN_FALTANTES_ACTO: tuple[str, ...] = (
    "DOCUMENTO_ACTO",
    "HECHOS",
    "FUNDAMENTOS",
    "DECISION",
    "DESTINATARIO",
    "AUTORIDAD",
)


def _claves(numero: str | None, denominacion: str | None) -> tuple[str | None, str | None]:
    """Normaliza las claves únicas del número y la denominación del acto."""
    numero_clave = numero.strip().upper() if numero is not None and numero.strip() else None
    denominacion_clave = denominacion.strip().upper() if denominacion else ""
    return numero_clave, denominacion_clave


def _documento_activo_vinculado(db: Session, acto: GovernmentAct) -> bool:
    """Indica si el acto tiene un documento ACTIVO vinculado a la empresa del acto."""
    stmt = (
        select(DocumentLink.id)
        .join(Document, Document.id == DocumentLink.document_id)
        .where(
            DocumentLink.resource_type == "GovernmentAct",
            DocumentLink.resource_id == acto.id,
            DocumentLink.company_id == acto.company_id,
            Document.company_id == acto.company_id,
            Document.status == "ACTIVE",
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def _validar_autoridad(
    db: Session,
    company_id: str,
    cargo_id: str,
    fecha: date,
    accion: str,
    materia: str,
) -> GovernmentPosition:
    """Valida cargo, vigencia y competencia para dictar un acto en la fecha indicada."""
    cargo = db.execute(
        select(GovernmentPosition).where(
            GovernmentPosition.id == cargo_id,
            GovernmentPosition.company_id == company_id,
        )
    ).scalar_one_or_none()

    if cargo is None:
        raise KontrolError(
            code="GOV_ACT_INVALID_AUTHORITY",
            message="El cargo no puede dictar actos en esa fecha",
            field_errors={"cargo_id": ["El cargo no puede dictar actos en esa fecha"]},
            status_code=422,
        )

    estructura = db.execute(
        select(GovernmentStructure).where(
            GovernmentStructure.id == cargo.structure_id,
            GovernmentStructure.company_id == company_id,
            GovernmentStructure.exercise == fecha.year,
        )
    ).scalar_one_or_none()

    if estructura is None:
        raise KontrolError(
            code="GOV_ACT_INVALID_AUTHORITY",
            message="El cargo no puede dictar actos en esa fecha",
            field_errors={"cargo_id": ["El cargo no puede dictar actos en esa fecha"]},
            status_code=422,
        )

    if cargo.status not in ("VIGENTE", "INACTIVO"):
        raise KontrolError(
            code="GOV_ACT_INVALID_AUTHORITY",
            message="El cargo no puede dictar actos en esa fecha",
            field_errors={"cargo_id": ["El cargo no puede dictar actos en esa fecha"]},
            status_code=422,
        )

    inicio_cubierto = cargo.valid_from is not None and cargo.valid_from <= fecha
    fin_real = cargo.valid_to if cargo.valid_to is not None else date(fecha.year, 12, 31)
    final_cubierto = fin_real >= fecha

    if not inicio_cubierto or not final_cubierto:
        raise KontrolError(
            code="GOV_ACT_INVALID_AUTHORITY",
            message="El cargo no puede dictar actos en esa fecha",
            field_errors={"cargo_id": ["El cargo no puede dictar actos en esa fecha"]},
            status_code=422,
        )

    competencias = competencias_en_vigor(db, cargo, fecha)
    if not any(
        competencia.get("accion") == accion and competencia.get("materia") == materia
        for competencia in competencias
    ):
        raise KontrolError(
            code="GOV_ACT_INVALID_COMPETENCY",
            message="El cargo no tiene la competencia indicada para dictar este acto",
            field_errors={"competencia": ["La competencia indicada no estaba vigente en el cargo en la fecha del acto"]},
            status_code=422,
        )

    return cargo


def _autoridad_valida(
    db: Session,
    company_id: str,
    cargo_id: str,
    fecha: date,
    accion: str,
    materia: str,
) -> bool:
    """Comprueba autoridad sin lanzar errores de negocio."""
    try:
        _validar_autoridad(db, company_id, cargo_id, fecha, accion, materia)
        return True
    except KontrolError:
        return False


def _cargo_y_unidad(db: Session, acto: GovernmentAct) -> tuple[GovernmentPosition | None, GovernmentUnit | None]:
    """Obtiene el cargo emisor y su unidad actual para la salida del acto."""
    cargo = db.execute(
        select(GovernmentPosition).where(
            GovernmentPosition.id == acto.cargo_id,
            GovernmentPosition.company_id == acto.company_id,
        )
    ).scalar_one_or_none()
    if cargo is None:
        return None, None
    unidad = db.execute(
        select(GovernmentUnit).where(
            GovernmentUnit.id == cargo.unit_id,
            GovernmentUnit.company_id == acto.company_id,
        )
    ).scalar_one_or_none()
    return cargo, unidad


def _acto_referido(db: Session, acto_id: str | None, company_id: str) -> dict[str, Any] | None:
    """Serializa la referencia completa a un acto relacionado de la misma empresa."""
    if acto_id is None:
        return None
    acto = db.execute(
        select(GovernmentAct).where(
            GovernmentAct.id == acto_id,
            GovernmentAct.company_id == company_id,
        )
    ).scalar_one_or_none()
    if acto is None:
        return None
    return {
        "id": str(acto.id),
        "tipo": acto.tipo,
        "numero": acto.numero,
        "fecha": acto.fecha,
    }


def _snapshot_acto(db: Session, acto: GovernmentAct) -> dict[str, Any]:
    """Construye la instantánea persistible de un acto sin listas derivadas."""
    cargo, unidad = _cargo_y_unidad(db, acto)
    return {
        "tipo": acto.tipo,
        "denominacion_tipo": acto.denominacion_tipo or None,
        "numero": acto.numero,
        "fecha": acto.fecha.isoformat(),
        "lugar": acto.lugar,
        "cargo": {
            "id": str(acto.cargo_id),
            "codigo": cargo.code if cargo else None,
            "denominacion": cargo.name if cargo else None,
            "unidad_codigo": unidad.code if unidad else None,
            "unidad_denominacion": unidad.name if unidad else None,
        },
        "competencia": {
            "accion": acto.competencia_accion,
            "materia": acto.competencia_materia,
        },
        "fundamento_competencia": acto.fundamento_competencia,
        "funcionario": acto.funcionario,
        "titularidad": acto.titularidad,
        "delegacion_numero": acto.delegacion_numero,
        "delegacion_fecha": acto.delegacion_fecha.isoformat() if acto.delegacion_fecha else None,
        "caracter": acto.caracter,
        "simple_tramite": acto.simple_tramite,
        "destinatario": acto.destinatario,
        "asunto": acto.asunto,
        "hechos": acto.hechos,
        "fundamentos": acto.fundamentos,
        "decision": acto.decision,
        "documento_acto_id": str(acto.documento_acto_id) if acto.documento_acto_id else None,
        "medio": acto.medio,
        "referencia_publicacion": acto.referencia_publicacion,
        "fecha_publicacion_notificacion": (
            acto.fecha_publicacion_notificacion.isoformat()
            if acto.fecha_publicacion_notificacion
            else None
        ),
        "documento_eficacia_id": str(acto.documento_eficacia_id) if acto.documento_eficacia_id else None,
        "fecha_eficacia": acto.fecha_eficacia.isoformat() if acto.fecha_eficacia else None,
    }


def _versionar(
    db: Session,
    acto: GovernmentAct,
    motivo: str | None,
    actor_id: str | None,
) -> None:
    """Registra una instantánea inmutable de la versión actual del acto."""
    version = GovernmentActVersion(
        act_id=acto.id,
        company_id=acto.company_id,
        version=acto.version,
        status=acto.status,
        snapshot=_snapshot_acto(db, acto),
        reason=motivo,
        actor_id=actor_id,
    )
    db.add(version)
    db.flush()


def _auditar(
    db: Session,
    ctx: CompanyContext,
    accion: str,
    entity_type: str,
    entity_id: str,
    before: Any,
    after: Any,
    motivo: str | None = None,
) -> None:
    """Registra un evento de auditoría del contexto actual."""
    record_audit(
        db,
        action=accion,
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before=before,
        after=after,
        reason=motivo,
    )


def faltantes_para_emitir(db: Session, acto: GovernmentAct) -> list[str]:
    """Calcula los requisitos pendientes para emitir el acto."""
    faltantes: list[str] = []
    if not _documento_activo_vinculado(db, acto):
        faltantes.append("DOCUMENTO_ACTO")
    if not acto.simple_tramite:
        if not acto.hechos:
            faltantes.append("HECHOS")
        if not acto.fundamentos:
            faltantes.append("FUNDAMENTOS")
    if not acto.decision:
        faltantes.append("DECISION")
    if acto.caracter == "PARTICULAR" and not acto.destinatario:
        faltantes.append("DESTINATARIO")
    if not _autoridad_valida(
        db,
        acto.company_id,
        acto.cargo_id,
        acto.fecha,
        acto.competencia_accion,
        acto.competencia_materia,
    ):
        faltantes.append("AUTORIDAD")
    return faltantes


def _acto_por_id(db: Session, ctx: CompanyContext, acto_id: str) -> GovernmentAct:
    """Obtiene un acto de la empresa actual, sin revelar actos ajenos."""
    acto = db.execute(
        select(GovernmentAct).where(
            GovernmentAct.id == acto_id,
            GovernmentAct.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if acto is None:
        raise NotFoundError("GOV_ACT_NOT_FOUND", "El acto no existe en esta empresa")
    return acto


def listar_actos(db: Session, ctx: CompanyContext, anio: int) -> dict[str, Any]:
    """Lista los actos de la empresa en el año indicado."""
    _ente(db, ctx)
    inicio = date(anio, 1, 1)
    fin = date(anio, 12, 31)
    actos = db.execute(
        select(GovernmentAct)
        .where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.fecha >= inicio,
            GovernmentAct.fecha <= fin,
        )
        .order_by(GovernmentAct.fecha.desc(), GovernmentAct.numero.asc())
    ).scalars().all()

    items: list[dict[str, Any]] = []
    for acto in actos:
        cargo, unidad = _cargo_y_unidad(db, acto)
        items.append(
            {
                "id": str(acto.id),
                "tipo": acto.tipo,
                "denominacion_tipo": acto.denominacion_tipo or None,
                "numero": acto.numero,
                "fecha": acto.fecha,
                "cargo_codigo": cargo.code if cargo else "",
                "cargo_denominacion": cargo.name if cargo else "",
                "unidad_codigo": unidad.code if unidad else "",
                "caracter": acto.caracter,
                "asunto": acto.asunto,
                "estado": acto.status,
                "fecha_eficacia": acto.fecha_eficacia,
            }
        )
    return {"anio": anio, "items": items, "total": len(items)}


def crear_acto(
    db: Session,
    ctx: CompanyContext,
    datos: ActoIn,
    actor_id: str,
) -> dict[str, Any]:
    """Registra un acto administrativo en borrador."""
    _ente(db, ctx)
    _validar_autoridad(
        db,
        ctx.company_id,
        datos.cargo_id,
        datos.fecha,
        datos.competencia.accion,
        datos.competencia.materia,
    )

    numero_clave, denominacion_clave = _claves(datos.numero, datos.denominacion_tipo)

    acto = GovernmentAct(
        company_id=ctx.company_id,
        tipo=datos.tipo,
        denominacion_tipo=datos.denominacion_tipo or "",
        denominacion_clave=denominacion_clave or "",
        numero=datos.numero,
        numero_clave=numero_clave or "",
        fecha=datos.fecha,
        lugar=datos.lugar,
        cargo_id=datos.cargo_id,
        competencia_accion=datos.competencia.accion,
        competencia_materia=datos.competencia.materia,
        fundamento_competencia=datos.fundamento_competencia,
        funcionario=datos.funcionario,
        titularidad=datos.titularidad,
        delegacion_numero=datos.delegacion_numero,
        delegacion_fecha=datos.delegacion_fecha,
        caracter=datos.caracter,
        simple_tramite=datos.simple_tramite,
        destinatario=datos.destinatario,
        asunto=datos.asunto,
        hechos=datos.hechos,
        fundamentos=datos.fundamentos,
        decision=datos.decision,
        status="BORRADOR",
        version=1,
        created_by=actor_id or None,
    )
    db.add(acto)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_ACT_NUMBER_DUPLICATE",
            "Ya existe un acto con este cargo, tipo y número",
        ) from None

    _versionar(db, acto, None, actor_id)
    _auditar(
        db,
        ctx,
        "GOV_ACT_CREATED",
        "GovernmentAct",
        str(acto.id),
        None,
        {**_snapshot_acto(db, acto), "version": 1},
    )
    return salida_acto(db, acto)


def obtener_acto(db: Session, ctx: CompanyContext, acto_id: str) -> dict[str, Any]:
    """Obtiene un acto de la empresa actual."""
    acto = _acto_por_id(db, ctx, acto_id)
    return salida_acto(db, acto)


def _serializar_valor(v: Any) -> Any:
    """Convierte valores para auditoría y snapshots."""
    if isinstance(v, datetime):
        return _utc(v)
    if isinstance(v, date):
        return v.isoformat()
    return v


def modificar_acto(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    datos: ActoCambio,
    version_esperada: int | None,
    actor_id: str,
) -> dict[str, Any]:
    """Modifica un acto en borrador con control de concurrencia."""
    acto = acto_para_escribir(db, ctx, acto_id, version_esperada)

    if acto.status != "BORRADOR":
        raise ConflictError(
            "GOV_ACT_INVALID_STATE",
            "Solo se modifica un acto en borrador",
        )

    cambios_entrada = datos.model_dump(exclude_none=True)
    if "denominacion_tipo" in cambios_entrada and cambios_entrada["denominacion_tipo"] is None:
        cambios_entrada["denominacion_tipo"] = ""

    estado = {
        "tipo": acto.tipo,
        "denominacion_tipo": acto.denominacion_tipo,
        "numero": acto.numero,
        "fecha": acto.fecha,
        "lugar": acto.lugar,
        "cargo_id": acto.cargo_id,
        "competencia_accion": acto.competencia_accion,
        "competencia_materia": acto.competencia_materia,
        "fundamento_competencia": acto.fundamento_competencia,
        "funcionario": acto.funcionario,
        "titularidad": acto.titularidad,
        "delegacion_numero": acto.delegacion_numero,
        "delegacion_fecha": acto.delegacion_fecha,
        "caracter": acto.caracter,
        "simple_tramite": acto.simple_tramite,
        "destinatario": acto.destinatario,
        "asunto": acto.asunto,
        "hechos": acto.hechos,
        "fundamentos": acto.fundamentos,
        "decision": acto.decision,
    }

    if "competencia" in cambios_entrada and cambios_entrada["competencia"] is not None:
        estado["competencia_accion"] = cambios_entrada["competencia"].accion
        estado["competencia_materia"] = cambios_entrada["competencia"].materia
        cambios_entrada = cambios_entrada.copy()
        cambios_entrada.pop("competencia", None)

    estado.update(cambios_entrada)

    if "tipo" in cambios_entrada and estado.get("tipo") != "OTRA_DECISION":
        if "denominacion_tipo" not in cambios_entrada:
            estado["denominacion_tipo"] = ""

    if "titularidad" in cambios_entrada and estado.get("titularidad") != "DELEGACION":
        estado["delegacion_numero"] = None
        estado["delegacion_fecha"] = None

    coherencia = validar_coherencia(
        {
            **estado,
            "denominacion_tipo": estado["denominacion_tipo"] or None,
        }
    )
    if coherencia is not None:
        raise _error_campo(coherencia[0], coherencia[1])

    campos_cambiados: dict[str, Any] = {}
    for campo, valor in estado.items():
        actual = getattr(acto, campo)
        if actual != valor:
            campos_cambiados[campo] = valor

    if not campos_cambiados:
        raise KontrolError(code="GOV_ACT_NO_CHANGES", message="No hay cambios que guardar", status_code=422)

    evaluar_antes_de_actuar(db, ctx, "DOC02_EDITAR", "GovernmentAct", str(acto.id))

    antes = {campo: _serializar_valor(getattr(acto, campo)) for campo in campos_cambiados}

    for campo, valor in campos_cambiados.items():
        setattr(acto, campo, valor)

    if any(campo in campos_cambiados for campo in ("cargo_id", "fecha", "competencia_accion", "competencia_materia")):
        _validar_autoridad(
            db,
            ctx.company_id,
            acto.cargo_id,
            acto.fecha,
            acto.competencia_accion,
            acto.competencia_materia,
        )

    if any(campo in campos_cambiados for campo in ("numero", "denominacion_tipo")):
        numero_clave, denominacion_clave = _claves(acto.numero, acto.denominacion_tipo)
        acto.numero_clave = numero_clave or ""
        acto.denominacion_clave = denominacion_clave or ""
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            if "uq_gov_acts_numero" not in str(exc):
                raise
            raise ConflictError(
                "GOV_ACT_NUMBER_DUPLICATE",
                "Ya existe un acto con este cargo, tipo y número",
            ) from None
    else:
        db.flush()

    acto.version += 1
    _versionar(db, acto, None, actor_id)
    despues = {campo: _serializar_valor(getattr(acto, campo)) for campo in campos_cambiados}
    _auditar(
        db,
        ctx,
        "GOV_ACT_UPDATED",
        "GovernmentAct",
        str(acto.id),
        {**antes, "version": acto.version - 1},
        {**despues, "version": acto.version},
    )
    return salida_acto(db, acto)


def eliminar_acto(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    version_esperada: int | None,
    actor_id: str,
) -> None:
    """Elimina un acto en borrador."""
    acto = acto_para_escribir(db, ctx, acto_id, version_esperada)

    if acto.status != "BORRADOR":
        raise ConflictError(
            "GOV_ACT_INVALID_STATE",
            "Solo se elimina un acto en borrador",
        )

    vinculos = db.execute(
        select(DocumentLink.id).where(
            DocumentLink.resource_type == "GovernmentAct",
            DocumentLink.resource_id == acto.id,
            DocumentLink.company_id == ctx.company_id,
        )
    ).first()

    if vinculos is not None:
        raise ConflictError(
            "GOV_ACT_HAS_DOCUMENTS",
            "Desvincule antes sus documentos",
        )

    _auditar(
        db,
        ctx,
        "GOV_ACT_DELETED",
        "GovernmentAct",
        str(acto.id),
        {**_snapshot_acto(db, acto), "version": acto.version},
        None,
    )

    db.execute(
        delete(GovernmentActVersion).where(
            GovernmentActVersion.act_id == acto.id,
            GovernmentActVersion.company_id == ctx.company_id,
        )
    )
    db.delete(acto)
    db.flush()


def autoridades(db: Session, ctx: CompanyContext, fecha: date) -> dict[str, Any]:
    """Lista los cargos elegibles para dictar actos en la fecha indicada."""
    _ente(db, ctx)

    estructura = db.execute(
        select(GovernmentStructure).where(
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.exercise == fecha.year,
        )
    ).scalar_one_or_none()

    if estructura is None:
        return {"fecha": fecha, "items": []}

    cargos = db.execute(
        select(GovernmentPosition)
        .where(
            GovernmentPosition.structure_id == estructura.id,
            GovernmentPosition.company_id == ctx.company_id,
            GovernmentPosition.status.in_(("VIGENTE", "INACTIVO")),
        )
        .order_by(GovernmentPosition.code.asc())
    ).scalars().all()

    items: list[dict[str, Any]] = []
    for cargo in cargos:
        inicio_cubierto = cargo.valid_from is not None and cargo.valid_from <= fecha
        fin_real = cargo.valid_to if cargo.valid_to is not None else date(fecha.year, 12, 31)
        final_cubierto = fin_real >= fecha
        if not inicio_cubierto or not final_cubierto:
            continue

        unidad = db.execute(
            select(GovernmentUnit).where(
                GovernmentUnit.id == cargo.unit_id,
                GovernmentUnit.company_id == ctx.company_id,
            )
        ).scalar_one_or_none()

        competencias = competencias_en_vigor(db, cargo, fecha)

        items.append(
            {
                "cargo_id": str(cargo.id),
                "codigo": cargo.code,
                "denominacion": cargo.name,
                "unidad_codigo": unidad.code if unidad else "",
                "unidad_denominacion": unidad.name if unidad else "",
                "estado": cargo.status,
                "competencias": [
                    {"accion": k.get("accion"), "materia": k.get("materia")}
                    for k in competencias
                ],
            }
        )

    return {"fecha": fecha, "items": items}


def exportar_actos_csv(db: Session, ctx: CompanyContext, anio: int) -> tuple[str, bytes]:
    """Exporta los actos del año a CSV."""
    ente = _ente(db, ctx)
    inicio = date(anio, 1, 1)
    fin = date(anio, 12, 31)
    actos = db.execute(
        select(GovernmentAct)
        .where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.fecha >= inicio,
            GovernmentAct.fecha <= fin,
        )
        .order_by(GovernmentAct.fecha.desc(), GovernmentAct.numero.asc())
    ).scalars().all()

    salida = io.StringIO()
    writer = csv.writer(salida, lineterminator="\n")
    writer.writerow(
        [
            "numero",
            "tipo",
            "denominacion_tipo",
            "fecha",
            "lugar",
            "caracter",
            "asunto",
            "cargo",
            "unidad",
            "competencia",
            "funcionario",
            "titularidad",
            "destinatario",
            "estado",
            "fecha_eficacia",
            "revocado_por",
            "anulado_por",
        ]
    )

    filas = 0
    for acto in actos:
        cargo, unidad = _cargo_y_unidad(db, acto)
        revocado_por = ""
        if acto.revocado_por_id:
            acto_revocador = db.execute(
                select(GovernmentAct).where(
                    GovernmentAct.id == acto.revocado_por_id,
                    GovernmentAct.company_id == ctx.company_id,
                )
            ).scalar_one_or_none()
            revocado_por = acto_revocador.numero if acto_revocador else ""
        anulado_por = ""
        if acto.anulado_por_id:
            acto_anulador = db.execute(
                select(GovernmentAct).where(
                    GovernmentAct.id == acto.anulado_por_id,
                    GovernmentAct.company_id == ctx.company_id,
                )
            ).scalar_one_or_none()
            anulado_por = acto_anulador.numero if acto_anulador else ""

        writer.writerow(
            [
                acto.numero,
                acto.tipo,
                acto.denominacion_tipo,
                acto.fecha.isoformat(),
                acto.lugar,
                acto.caracter,
                acto.asunto,
                cargo.code if cargo else "",
                unidad.code if unidad else "",
                f"{acto.competencia_accion}·{acto.competencia_materia}",
                acto.funcionario,
                acto.titularidad,
                acto.destinatario or "",
                acto.status,
                acto.fecha_eficacia.isoformat() if acto.fecha_eficacia else "",
                revocado_por,
                anulado_por,
            ]
        )
        filas += 1

    _auditar(
        db,
        ctx,
        "GOV_ACTS_EXPORTED",
        "GovernmentEntity",
        str(ente.id),
        None,
        {"anio": anio, "filas": filas},
    )
    return f"actos-{anio}.csv", salida.getvalue().encode("utf-8")


def versiones_acto(db: Session, ctx: CompanyContext, acto_id: str) -> dict[str, Any]:
    """Lista las versiones históricas de un acto."""
    _acto_por_id(db, ctx, acto_id)

    versiones = db.execute(
        select(GovernmentActVersion)
        .where(
            GovernmentActVersion.act_id == acto_id,
            GovernmentActVersion.company_id == ctx.company_id,
        )
        .order_by(GovernmentActVersion.version.asc())
    ).scalars().all()

    items = [
        {
            "version": v.version,
            "estado": v.status,
            "motivo": v.reason,
            "actor": v.actor_id,
            "creado_en": _utc(v.created_at),
            "instantanea": v.snapshot,
        }
        for v in versiones
    ]
    return {"items": items, "total": len(items)}


def acto_para_escribir(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    version_esperada: int | None,
) -> GovernmentAct:
    """Prepara un acto para escritura con control de concurrencia."""
    if version_esperada is None:
        raise KontrolError(
            code="GOV_ACT_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión del acto",
            status_code=428,
        )

    acto = db.execute(
        select(GovernmentAct)
        .where(
            GovernmentAct.id == acto_id,
            GovernmentAct.company_id == ctx.company_id,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if acto is None:
        raise NotFoundError("GOV_ACT_NOT_FOUND", "El acto no existe en esta empresa")

    if version_esperada != acto.version:
        raise ConflictError(
            "GOV_ACT_STALE",
            "El acto cambió desde que lo abrió; recárguelo",
            details={"version_actual": acto.version},
        )

    return acto


def salida_acto(db: Session, acto: GovernmentAct) -> dict[str, Any]:
    """Convierte un acto al dict completo de salida de la API."""
    cargo, unidad = _cargo_y_unidad(db, acto)
    faltantes = faltantes_para_emitir(db, acto)

    revocado_por = _acto_referido(db, acto.revocado_por_id, acto.company_id)
    anulado_por = _acto_referido(db, acto.anulado_por_id, acto.company_id)

    revoca_a_rows = db.execute(
        select(GovernmentAct).where(
            GovernmentAct.revocado_por_id == acto.id,
            GovernmentAct.company_id == acto.company_id,
        )
    ).scalars().all()
    anula_a_rows = db.execute(
        select(GovernmentAct).where(
            GovernmentAct.anulado_por_id == acto.id,
            GovernmentAct.company_id == acto.company_id,
        )
    ).scalars().all()

    notificaciones: dict[str, int] | None = None
    if acto.caracter == "PARTICULAR":
        fila = db.execute(
            select(
                func.count(GovernmentNotification.id),
                func.count(GovernmentNotification.id).filter(
                    GovernmentNotification.status == "NOTIFICADA"
                ),
                func.count(GovernmentNotification.id).filter(
                    GovernmentNotification.status == "PENDIENTE"
                ),
            ).where(
                GovernmentNotification.act_id == acto.id,
                GovernmentNotification.company_id == acto.company_id,
                GovernmentNotification.status != "ANULADA",
            )
        ).one()
        notificaciones = {
            "total": fila[0],
            "notificadas": fila[1],
            "pendientes": fila[2],
        }

    return {
        "id": str(acto.id),
        "tipo": acto.tipo,
        "denominacion_tipo": acto.denominacion_tipo or None,
        "numero": acto.numero,
        "fecha": acto.fecha,
        "lugar": acto.lugar,
        "cargo": {
            "id": str(acto.cargo_id),
            "codigo": cargo.code if cargo else "",
            "denominacion": cargo.name if cargo else "",
            "unidad_codigo": unidad.code if unidad else "",
            "unidad_denominacion": unidad.name if unidad else "",
        },
        "competencia": {
            "accion": acto.competencia_accion,
            "materia": acto.competencia_materia,
        },
        "fundamento_competencia": acto.fundamento_competencia,
        "funcionario": acto.funcionario,
        "titularidad": acto.titularidad,
        "delegacion_numero": acto.delegacion_numero,
        "delegacion_fecha": acto.delegacion_fecha,
        "caracter": acto.caracter,
        "simple_tramite": acto.simple_tramite,
        "destinatario": acto.destinatario,
        "asunto": acto.asunto,
        "hechos": acto.hechos,
        "fundamentos": acto.fundamentos,
        "decision": acto.decision,
        "estado": acto.status,
        "faltantes_para_emitir": faltantes,
        "documento_acto_id": str(acto.documento_acto_id) if acto.documento_acto_id else None,
        "medio": acto.medio,
        "referencia_publicacion": acto.referencia_publicacion,
        "fecha_publicacion_notificacion": acto.fecha_publicacion_notificacion,
        "documento_eficacia_id": str(acto.documento_eficacia_id) if acto.documento_eficacia_id else None,
        "fecha_eficacia": acto.fecha_eficacia,
        "revocado_por": revocado_por,
        "anulado_por": anulado_por,
        "revoca_a": [
            {"id": str(a.id), "tipo": a.tipo, "numero": a.numero} for a in revoca_a_rows
        ],
        "anula_a": [
            {"id": str(a.id), "tipo": a.tipo, "numero": a.numero} for a in anula_a_rows
        ],
        "version": acto.version,
        "emitido_en": _utc(acto.emitido_en),
        "emitido_por": acto.emitido_por,
        "creado_en": _utc(acto.created_at),
        "notificaciones": notificaciones,
    }


def _documento_del_acto(
    db: Session,
    acto: GovernmentAct,
    documento_id: str,
    campo: str,
    *,
    excluir: str | None = None,
) -> Document:
    """Obtiene un documento activo, de la empresa del acto, vinculado al acto."""
    stmt = (
        select(Document, DocumentLink.id)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            Document.id == documento_id,
            Document.company_id == acto.company_id,
            DocumentLink.resource_type == "GovernmentAct",
            DocumentLink.resource_id == acto.id,
            DocumentLink.company_id == acto.company_id,
            Document.status == "ACTIVE",
        )
        .limit(1)
    )
    fila = db.execute(stmt).first()
    documento = fila[0] if fila is not None else None

    if documento is None or (excluir is not None and str(documento.id) == excluir):
        raise KontrolError(
            code="GOV_ACT_INVALID_DOCUMENT",
            message="El documento no es válido para este acto",
            field_errors={campo: ["El documento no es válido para este acto"]},
            status_code=422,
        )

    return documento


def emitir_acto(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    datos: EmisionIn,
    version_esperada: int | None,
    actor: User,
) -> dict[str, Any]:
    """Emite un acto en borrador y lo pasa a EMITIDO o EFICAZ."""
    acto = acto_para_escribir(db, ctx, acto_id, version_esperada)

    if acto.status != "BORRADOR":
        raise ConflictError(
            "GOV_ACT_INVALID_STATE",
            "Solo se emite un acto en borrador",
        )

    faltantes = [f for f in faltantes_para_emitir(db, acto) if f != "DOCUMENTO_ACTO"]
    if faltantes:
        raise KontrolError(
            code="GOV_ACT_INCOMPLETE",
            message="El acto no está completo para emitir",
            details={"faltantes": faltantes},
            status_code=422,
        )

    documento = _documento_del_acto(
        db, acto, datos.documento_acto_id, "documento_acto_id"
    )

    _validar_autoridad(
        db,
        ctx.company_id,
        acto.cargo_id,
        acto.fecha,
        acto.competencia_accion,
        acto.competencia_materia,
    )

    evaluar_antes_de_actuar(db, ctx, "DOC02_EMITIR", "GovernmentAct", str(acto.id))

    if acto.caracter == "INTERNO":
        fecha_eficacia = (
            datos.fecha_eficacia if datos.fecha_eficacia is not None else acto.fecha
        )
        if fecha_eficacia < acto.fecha:
            raise _error_campo(
                "fecha_eficacia",
                "La eficacia no puede ser anterior a la fecha del acto",
            )
        acto.fecha_eficacia = fecha_eficacia
        estado_final = "EFICAZ"
    else:
        if datos.fecha_eficacia is not None:
            raise _error_campo(
                "fecha_eficacia",
                "Se fija al registrar la publicación o la notificación",
            )
        estado_final = "EMITIDO"

    acto.documento_acto_id = str(documento.id)
    acto.emitido_en = utcnow()
    acto.emitido_por = str(actor.id)
    acto.status = estado_final
    acto.version += 1
    _versionar(db, acto, "Emisión del acto", str(actor.id))
    freeze_links(
        db, resource_type="GovernmentAct", resource_id=str(acto.id), actor=actor
    )
    before = {"status": "BORRADOR", "documento_acto_id": None, "fecha_eficacia": None}
    after = {
        "status": acto.status,
        "documento_acto_id": str(acto.documento_acto_id),
        "fecha_eficacia": acto.fecha_eficacia,
    }
    _auditar(
        db,
        ctx,
        "GOV_ACT_ISSUED",
        "GovernmentAct",
        str(acto.id),
        {k: _serializar_valor(v) for k, v in before.items()},
        {k: _serializar_valor(v) for k, v in after.items()},
        "Emisión del acto",
    )
    return salida_acto(db, acto)


def registrar_eficacia(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    datos: EficaciaIn,
    version_esperada: int | None,
    actor: User,
) -> dict[str, Any]:
    """Registra la eficacia de un acto emitido."""
    acto = acto_para_escribir(db, ctx, acto_id, version_esperada)

    if acto.status != "EMITIDO":
        raise ConflictError(
            "GOV_ACT_INVALID_STATE",
            "Solo se registra la eficacia de un acto emitido",
        )

    if acto.caracter == "PARTICULAR":
        raise KontrolError(
            code="GOV_ACT_NOTIFICATION_REQUIRED",
            message="La notificación de un acto particular se registra en Notificaciones administrativas",
            field_errors={
                "medio": [
                    "Registre la notificación de cada interesado en Notificaciones administrativas"
                ]
            },
            status_code=422,
        )

    if acto.caracter == "GENERAL" and datos.medio != "GACETA":
        raise KontrolError(
            code="GOV_ACT_INVALID_MEDIUM",
            message="El medio no es válido para este acto",
            field_errors={"medio": ["Los actos generales se publican en gaceta"]},
            status_code=422,
        )
    if datos.medio in ("GACETA", "PRENSA") and not datos.referencia:
        raise _error_campo("referencia", "El medio exige una referencia")

    if datos.fecha < acto.fecha:
        raise _error_campo(
            "fecha", "No puede ser anterior a la fecha del acto"
        )

    documento = _documento_del_acto(
        db,
        acto,
        datos.documento_eficacia_id,
        "documento_eficacia_id",
        excluir=(
            str(acto.documento_acto_id) if acto.documento_acto_id else None
        ),
    )

    if datos.medio == "PRENSA":
        base = datos.fecha + timedelta(days=15)
    else:
        base = datos.fecha

    if datos.fecha_eficacia is not None:
        if datos.fecha_eficacia < base:
            raise _error_campo(
                "fecha_eficacia",
                "La fecha de eficacia es anterior a la fecha base",
            )
        fecha_eficacia = datos.fecha_eficacia
    else:
        fecha_eficacia = base

    evaluar_antes_de_actuar(db, ctx, "DOC02_EFICACIA", "GovernmentAct", str(acto.id))

    acto.medio = datos.medio
    acto.referencia_publicacion = datos.referencia
    acto.fecha_publicacion_notificacion = datos.fecha
    acto.documento_eficacia_id = str(documento.id)
    acto.fecha_eficacia = fecha_eficacia
    acto.status = "EFICAZ"
    acto.version += 1
    _versionar(db, acto, "Registro de eficacia", str(actor.id))
    freeze_links(
        db, resource_type="GovernmentAct", resource_id=str(acto.id), actor=actor
    )
    before = {
        "medio": None,
        "referencia_publicacion": None,
        "fecha_publicacion_notificacion": None,
        "documento_eficacia_id": None,
        "fecha_eficacia": None,
        "status": "EMITIDO",
    }
    after = {
        "medio": acto.medio,
        "referencia_publicacion": acto.referencia_publicacion,
        "fecha_publicacion_notificacion": acto.fecha_publicacion_notificacion,
        "documento_eficacia_id": str(acto.documento_eficacia_id),
        "fecha_eficacia": acto.fecha_eficacia,
        "status": acto.status,
    }
    _auditar(
        db,
        ctx,
        "GOV_ACT_EFFECTIVENESS_RECORDED",
        "GovernmentAct",
        str(acto.id),
        {k: _serializar_valor(v) for k, v in before.items()},
        {k: _serializar_valor(v) for k, v in after.items()},
        "Registro de eficacia",
    )
    return salida_acto(db, acto)


def corregir_acto(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    datos: CorreccionIn,
    version_esperada: int | None,
    actor: User,
) -> dict[str, Any]:
    """Corrige un acto emitido o eficaz."""
    acto = acto_para_escribir(db, ctx, acto_id, version_esperada)

    if acto.status not in ("EMITIDO", "EFICAZ"):
        raise ConflictError(
            "GOV_ACT_INVALID_STATE",
            "Solo se corrige un acto emitido o eficaz",
        )

    cambios = {
        campo: valor
        for campo, valor in datos.model_dump(exclude_none=True).items()
        if campo != "motivo" and valor is not None
    }

    if not cambios:
        raise KontrolError(
            code="GOV_ACT_NO_CHANGES",
            message="No hay cambios que guardar",
            status_code=422,
        )

    evaluar_antes_de_actuar(db, ctx, "DOC02_CORREGIR", "GovernmentAct", str(acto.id))

    antes: dict[str, Any] = {}
    despues: dict[str, Any] = {}
    for campo, valor in cambios.items():
        actual = getattr(acto, campo)
        if actual != valor:
            antes[campo] = _serializar_valor(actual)
            despues[campo] = _serializar_valor(valor)
            setattr(acto, campo, valor)

    if not despues:
        raise KontrolError(
            code="GOV_ACT_NO_CHANGES",
            message="No hay cambios que guardar",
            status_code=422,
        )

    acto.version += 1
    _versionar(db, acto, datos.motivo, str(actor.id))
    _auditar(
        db,
        ctx,
        "GOV_ACT_CORRECTED",
        "GovernmentAct",
        str(acto.id),
        antes,
        despues,
        datos.motivo,
    )
    return salida_acto(db, acto)


def _validar_referencia(
    db: Session,
    ctx: CompanyContext,
    objetivo: GovernmentAct,
    acto_id_referencia: str,
) -> GovernmentAct:
    """Valida la referencia para revocar o anular (lectura con FOR UPDATE)."""
    referencia = db.execute(
        select(GovernmentAct)
        .where(
            GovernmentAct.id == acto_id_referencia,
            GovernmentAct.company_id == ctx.company_id,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if (
        referencia is None
        or referencia.id == objetivo.id
        or referencia.status not in ("EMITIDO", "EFICAZ")
        or referencia.fecha < objetivo.fecha
    ):
        raise KontrolError(
            code="GOV_ACT_INVALID_REFERENCE",
            message="El acto de referencia no es válido para revocar o anular este acto",
            field_errors={
                "acto_id_referencia": [
                    "El acto de referencia no es válido para revocar o anular este acto"
                ]
            },
            status_code=422,
        )

    return referencia


def _revocar_o_anular(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    datos: ReferenciaIn,
    version_esperada: int | None,
    actor: User,
    *,
    accion: str,
    campo: str,
    estado_final: str,
    evento: str,
) -> dict[str, Any]:
    """Ayudante compartido para revocar y anular un acto."""
    acto = acto_para_escribir(db, ctx, acto_id, version_esperada)

    if acto.status not in ("EMITIDO", "EFICAZ"):
        raise ConflictError(
            "GOV_ACT_INVALID_STATE",
            f"Solo se {accion} un acto emitido o eficaz",
        )

    referencia = _validar_referencia(db, ctx, acto, datos.acto_id_referencia)

    evaluar_antes_de_actuar(db, ctx, "DOC02_REVOCAR" if evento == "GOV_ACT_REVOKED" else "DOC02_ANULAR", "GovernmentAct", str(acto.id))

    before = {"status": acto.status, "version": acto.version}
    setattr(acto, campo, referencia.id)
    acto.status = estado_final
    acto.version += 1
    _versionar(db, acto, datos.motivo, str(actor.id))
    _auditar(
        db,
        ctx,
        evento,
        "GovernmentAct",
        str(acto.id),
        before,
        {
            "status": acto.status,
            "version": acto.version,
            "acto_referencia": {
                "id": str(referencia.id),
                "tipo": referencia.tipo,
                "numero": referencia.numero,
                "fecha": referencia.fecha.isoformat(),
            },
        },
        datos.motivo,
    )
    return salida_acto(db, acto)


def revocar_acto(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    datos: ReferenciaIn,
    version_esperada: int | None,
    actor: User,
) -> dict[str, Any]:
    """Revoca un acto emitido o eficaz."""
    return _revocar_o_anular(
        db,
        ctx,
        acto_id,
        datos,
        version_esperada,
        actor,
        accion="revoca",
        campo="revocado_por_id",
        estado_final="REVOCADO",
        evento="GOV_ACT_REVOKED",
    )


def anular_acto(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    datos: ReferenciaIn,
    version_esperada: int | None,
    actor: User,
) -> dict[str, Any]:
    """Anula un acto emitido o eficaz."""
    return _revocar_o_anular(
        db,
        ctx,
        acto_id,
        datos,
        version_esperada,
        actor,
        accion="anula",
        campo="anulado_por_id",
        estado_final="NULO",
        evento="GOV_ACT_NULLIFIED",
    )
