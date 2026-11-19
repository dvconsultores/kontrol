from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import DocumentType
from app.modules.government.models import (
    ACCIONES_COMPETENCIA,
    AMBITOS_AUTORIZACION_ASIGNACION,
    ETAPAS_DOCUMENTO_ASIGNACION,
    FIGURAS_ASIGNACION,
    MATERIAS_COMPETENCIA,
    MEDIOS_EFICACIA,
    TIPOS_EMISOR_ASIGNACION,
    GovernmentAct,
    GovernmentAssignment,
    GovernmentAssignmentPolicy,
    GovernmentAssignmentPolicyCompetency,
    GovernmentAssignmentPolicyDocument,
    GovernmentAssignmentPolicyHistory,
    GovernmentPosition,
)
from app.modules.government.service_asignacion_regla import (
    FIGURAS_DELEGACION,
    PISOS,
    instantanea,
    nivel_del_ente,
)
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_ocupacion import FIGURAS
from app.shared.audit import record_audit
from app.shared.clock import instante_actual

ENTIDAD = "GovernmentAssignmentPolicy"

EVENTOS = {
    "CREADA": "CREADA",
    "EDITADA": "EDITADA",
    "ACTIVADA": "ACTIVADA",
    "CERRADA": "CERRADA",
    "SUSTITUIDA": "SUSTITUIDA",
    "NUEVA_VERSION": "NUEVA_VERSION",
}

_ESTADOS = {
    "BORRADOR": "Borrador",
    "VIGENTE": "Vigente",
    "CERRADA": "Cerrada",
}


def _etiqueta_figura(codigo: str) -> str:
    return FIGURAS.get(codigo, {}).get("etiqueta", codigo)


def _invalida(field_errors: dict[str, list[str]], motivos: list[str] | None = None) -> KontrolError:
    return KontrolError(
        code="GOV_ASSIGNMENT_POLICY_INVALID",
        message="La política no se puede activar" if motivos is not None else "La política no es válida",
        status_code=422,
        field_errors=field_errors,
        details={"motivos": motivos} if motivos is not None else None,
    )


def catalogo() -> dict[str, Any]:
    figuras = [
        {"codigo": codigo, "etiqueta": _etiqueta_figura(codigo)}
        for codigo in FIGURAS_ASIGNACION
    ]
    estados = [{"codigo": codigo, "etiqueta": etiqueta} for codigo, etiqueta in _ESTADOS.items()]
    medios = [{"codigo": codigo, "etiqueta": codigo} for codigo in MEDIOS_EFICACIA]
    emisor_tipos = [{"codigo": codigo, "etiqueta": codigo} for codigo in TIPOS_EMISOR_ASIGNACION]
    ambitos = [
        {"codigo": codigo, "etiqueta": codigo}
        for codigo in AMBITOS_AUTORIZACION_ASIGNACION
    ]
    etapas = [{"codigo": codigo, "etiqueta": codigo} for codigo in ETAPAS_DOCUMENTO_ASIGNACION]
    acciones = [{"codigo": codigo, "etiqueta": codigo} for codigo in ACCIONES_COMPETENCIA]
    materias = [{"codigo": codigo, "etiqueta": codigo} for codigo in MATERIAS_COMPETENCIA]
    return {
        "figuras": figuras,
        "estados": estados,
        "medios": medios,
        "emisor_tipos": emisor_tipos,
        "ambitos": ambitos,
        "etapas": etapas,
        "acciones": acciones,
        "materias": materias,
    }


def opciones(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    cargos = db.scalars(
        select(GovernmentPosition)
        .where(
            GovernmentPosition.company_id == ctx.company_id,
            GovernmentPosition.status == "VIGENTE",
        )
        .order_by(GovernmentPosition.name.asc())
    ).all()
    tipos_documentales = db.scalars(
        select(DocumentType)
        .where(
            DocumentType.company_id == ctx.company_id,
            DocumentType.status == "ACTIVE",
        )
        .order_by(DocumentType.name.asc())
    ).all()
    nivel = nivel_del_ente(db, ctx)
    pisos = [
        {
            "codigo": p["codigo"],
            "fuente": p["fuente"],
            "version": p["version"],
            "figuras": list(p["figuras"]),
            "niveles": list(p["niveles"]) if p["niveles"] is not None else None,
        }
        for p in PISOS
        if p["niveles"] is None or nivel in p["niveles"]
    ]
    return {
        "cargos": [{"id": str(c.id), "etiqueta": c.name} for c in cargos],
        "tipos_documentales": [
            {"id": str(t.id), "etiqueta": t.name} for t in tipos_documentales
        ],
        "nivel_territorial": nivel,
        "pisos": pisos,
    }


def _contar_asignaciones(db: Session, ctx: CompanyContext, policy_id: str) -> int:
    return db.scalar(
        select(func.count(GovernmentAssignment.id)).where(
            GovernmentAssignment.company_id == ctx.company_id,
            GovernmentAssignment.policy_id == policy_id,
        )
    ) or 0


def _resumen(db: Session, ctx: CompanyContext, politica: GovernmentAssignmentPolicy) -> dict[str, Any]:
    return {
        "id": str(politica.id),
        "codigo": politica.codigo,
        "numero_version": politica.numero_version,
        "nombre": politica.nombre,
        "figura": politica.figura,
        "figura_etiqueta": _etiqueta_figura(politica.figura),
        "estado": politica.estado,
        "estado_etiqueta": _ESTADOS.get(politica.estado, politica.estado),
        "vigente_desde": politica.vigente_desde,
        "vigente_hasta": politica.vigente_hasta,
        "version": politica.version,
        "asignaciones": _contar_asignaciones(db, ctx, str(politica.id)),
    }


def listar(
    db: Session,
    ctx: CompanyContext,
    estado: str | None = None,
    figura: str | None = None,
    q: str | None = None,
) -> dict[str, Any]:
    condicion = [GovernmentAssignmentPolicy.company_id == ctx.company_id]
    if estado:
        condicion.append(GovernmentAssignmentPolicy.estado == estado)
    if figura:
        condicion.append(GovernmentAssignmentPolicy.figura == figura)
    if q:
        like = f"%{q}%"
        condicion.append(
            or_(
                GovernmentAssignmentPolicy.codigo.ilike(like),
                GovernmentAssignmentPolicy.nombre.ilike(like),
            )
        )
    politicas = db.scalars(
        select(GovernmentAssignmentPolicy)
        .where(*condicion)
        .order_by(
            GovernmentAssignmentPolicy.codigo.asc(),
            GovernmentAssignmentPolicy.numero_version.desc(),
        )
    ).all()
    items = [_resumen(db, ctx, p) for p in politicas]
    return {"items": items, "total": len(items)}


def _para_escribir(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
) -> GovernmentAssignmentPolicy:
    if version is None:
        raise KontrolError(
            code="GOV_ASSIGNMENT_POLICY_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    politica = db.scalar(
        select(GovernmentAssignmentPolicy)
        .where(
            GovernmentAssignmentPolicy.id == id,
            GovernmentAssignmentPolicy.company_id == ctx.company_id,
        )
        .with_for_update()
    )
    if not politica:
        raise NotFoundError(
            "GOV_ASSIGNMENT_POLICY_NOT_FOUND",
            "La política no existe en este ente",
        )
    if politica.version != version:
        raise ConflictError(
            "GOV_ASSIGNMENT_POLICY_STALE",
            "La política cambió desde que la abrió; recárguela",
            details={"version_actual": politica.version},
        )
    return politica


def _exigir_borrador(politica: GovernmentAssignmentPolicy) -> None:
    if politica.estado != "BORRADOR":
        raise ConflictError(
            "GOV_ASSIGNMENT_POLICY_NOT_DRAFT",
            "Solo una política en borrador se puede editar; cree una nueva versión",
        )


def _historia(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentAssignmentPolicy,
    evento: str,
) -> None:
    db.add(
        GovernmentAssignmentPolicyHistory(
            policy_id=str(politica.id),
            company_id=ctx.company_id,
            evento=evento,
            version=politica.version,
            instantanea=_instantanea_historia(db, politica),
            actor_id=ctx.user_id,
            created_by=ctx.user_id,
        )
    )


def _auditar(
    db: Session,
    ctx: CompanyContext,
    accion: str,
    id: str,
    despues: dict[str, Any],
    motivo: str | None = None,
) -> None:
    permitidas = {
        "codigo",
        "estado",
        "figura",
        "motivo",
        "nombre",
        "numero_version",
        "sustituye",
        "version",
        "vigente_desde",
        "vigente_hasta",
    }
    limpio: dict[str, Any] = {}
    for k, v in despues.items():
        if k not in permitidas:
            continue
        if hasattr(v, "isoformat"):
            limpio[k] = v.isoformat()
        else:
            limpio[k] = v
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD,
        entity_id=id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=limpio,
        reason=motivo,
    )


def _historia_salida(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentAssignmentPolicy,
) -> list[dict[str, Any]]:
    eventos = db.scalars(
        select(GovernmentAssignmentPolicyHistory)
        .where(
            GovernmentAssignmentPolicyHistory.policy_id == str(politica.id),
            GovernmentAssignmentPolicyHistory.company_id == ctx.company_id,
        )
        .order_by(GovernmentAssignmentPolicyHistory.created_at.asc())
    ).all()
    actores_ids = {e.actor_id for e in eventos if e.actor_id}
    actores = _usuarios_por_ids(db, list(actores_ids), ctx.tenant_id)
    return [
        {
            "evento": e.evento,
            "version": e.version,
            "fecha": e.created_at,
            "actor": actores.get(e.actor_id) if e.actor_id else None,
        }
        for e in eventos
    ]


def _versiones_salida(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentAssignmentPolicy,
) -> list[dict[str, Any]]:
    versiones = db.scalars(
        select(GovernmentAssignmentPolicy)
        .where(GovernmentAssignmentPolicy.company_id == ctx.company_id)
        .where(GovernmentAssignmentPolicy.codigo == politica.codigo)
        .order_by(GovernmentAssignmentPolicy.numero_version.desc())
    ).all()
    return [
        {
            "id": str(v.id),
            "numero_version": v.numero_version,
            "estado": v.estado,
        }
        for v in versiones
    ]


def _existe_borrador_codigo(db: Session, ctx: CompanyContext, codigo: str) -> bool:
    borrador = db.scalar(
        select(GovernmentAssignmentPolicy.id).where(
            GovernmentAssignmentPolicy.company_id == ctx.company_id,
            GovernmentAssignmentPolicy.codigo == codigo,
            GovernmentAssignmentPolicy.estado == "BORRADOR",
        )
    )
    return borrador is not None


def _instantanea_historia(
    db: Session,
    politica: GovernmentAssignmentPolicy,
) -> dict[str, Any]:
    competencias = db.scalars(
        select(GovernmentAssignmentPolicyCompetency).where(
            GovernmentAssignmentPolicyCompetency.policy_id == str(politica.id),
            GovernmentAssignmentPolicyCompetency.company_id == politica.company_id,
        )
    ).all()
    documentos = db.scalars(
        select(GovernmentAssignmentPolicyDocument).where(
            GovernmentAssignmentPolicyDocument.policy_id == str(politica.id),
            GovernmentAssignmentPolicyDocument.company_id == politica.company_id,
        )
    ).all()
    return {
        "codigo": politica.codigo,
        "numero_version": politica.numero_version,
        "nombre": politica.nombre,
        "descripcion": politica.descripcion,
        "figura": politica.figura,
        "fundamento": politica.fundamento,
        "act_id": str(politica.act_id) if politica.act_id else None,
        "vigente_desde": politica.vigente_desde.isoformat(),
        "vigente_hasta": politica.vigente_hasta.isoformat() if politica.vigente_hasta else None,
        "estado": politica.estado,
        "exige_fin": politica.exige_fin,
        "max_dias": politica.max_dias,
        "acto_medio": politica.acto_medio,
        "emisor_tipo": politica.emisor_tipo,
        "emisor_position_id": str(politica.emisor_position_id)
        if politica.emisor_position_id
        else None,
        "emisor_competencia_accion": politica.emisor_competencia_accion,
        "emisor_competencia_materia": politica.emisor_competencia_materia,
        "autorizacion_requerida": politica.autorizacion_requerida,
        "autorizacion_etiqueta": politica.autorizacion_etiqueta,
        "autorizacion_ambito": politica.autorizacion_ambito,
        "autorizacion_mas_de_dias": politica.autorizacion_mas_de_dias,
        "prohibe_avocacion": politica.prohibe_avocacion,
        "version_anterior_id": str(politica.version_anterior_id)
        if politica.version_anterior_id
        else None,
        "competencias": [
            {"accion": c.accion, "materia": c.materia} for c in competencias
        ],
        "documentos": [
            {
                "document_type_id": str(d.document_type_id),
                "etapa": d.etapa,
                "obligatorio": d.obligatorio,
            }
            for d in documentos
        ],
    }


def _detalle_base(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentAssignmentPolicy,
) -> dict[str, Any]:
    regla = instantanea(db, ctx, politica, nivel_del_ente(db, ctx), politica.vigente_desde)
    resumen = _resumen(db, ctx, politica)
    detalle: dict[str, Any] = dict(resumen)
    detalle.update(
        {
            "descripcion": politica.descripcion,
            "fundamento": politica.fundamento,
            "act_id": str(politica.act_id) if politica.act_id else None,
            "exige_fin": politica.exige_fin,
            "max_dias": politica.max_dias,
            "acto_medio": politica.acto_medio,
            "emisor_tipo": politica.emisor_tipo,
            "emisor_position_id": str(politica.emisor_position_id)
            if politica.emisor_position_id
            else None,
            "emisor_competencia_accion": politica.emisor_competencia_accion,
            "emisor_competencia_materia": politica.emisor_competencia_materia,
            "autorizacion_requerida": politica.autorizacion_requerida,
            "autorizacion_etiqueta": politica.autorizacion_etiqueta,
            "autorizacion_ambito": politica.autorizacion_ambito,
            "autorizacion_mas_de_dias": politica.autorizacion_mas_de_dias,
            "prohibe_avocacion": politica.prohibe_avocacion,
            "competencias": regla.get("competencias", []),
            "documentos": regla.get("documentos", []),
            "regla": regla,
            "activada_en": politica.activada_en,
            "cerrada_en": politica.cerrada_en,
            "motivo_cierre": politica.motivo_cierre,
            "version_anterior_id": str(politica.version_anterior_id)
            if politica.version_anterior_id
            else None,
        }
    )
    return detalle


def detalle(db: Session, ctx: CompanyContext, id: str) -> dict[str, Any]:
    politica = db.scalar(
        select(GovernmentAssignmentPolicy).where(
            GovernmentAssignmentPolicy.id == id,
            GovernmentAssignmentPolicy.company_id == ctx.company_id,
        )
    )
    if not politica:
        raise NotFoundError(
            "GOV_ASSIGNMENT_POLICY_NOT_FOUND",
            "La política no existe en este ente",
        )

    detalle_data = _detalle_base(db, ctx, politica)
    detalle_data["historia"] = _historia_salida(db, ctx, politica)
    detalle_data["versiones"] = _versiones_salida(db, ctx, politica)
    detalle_data["existe_borrador"] = (
        _existe_borrador_codigo(db, ctx, politica.codigo)
        if politica.estado != "BORRADOR"
        else False
    )
    return detalle_data


def _validar(
    db: Session,
    ctx: CompanyContext,
    datos: Any,
) -> dict[str, list[str]]:
    field_errors: dict[str, list[str]] = {}

    if datos.vigente_hasta is not None and datos.vigente_hasta < datos.vigente_desde:
        field_errors.setdefault("vigente_hasta", [])
        field_errors["vigente_hasta"].append(
            "La fecha de fin no puede ser anterior a la de inicio"
        )

    # Emisor
    if datos.emisor_tipo == "CUALQUIERA":
        if datos.emisor_position_id or datos.emisor_competencia_accion or datos.emisor_competencia_materia:
            field_errors.setdefault("emisor_tipo", [])
            field_errors["emisor_tipo"].append(
                "Con emisor «Cualquiera» no se indica cargo ni competencia"
            )
    elif datos.emisor_tipo == "CARGO":
        if datos.emisor_competencia_accion or datos.emisor_competencia_materia:
            field_errors.setdefault("emisor_tipo", [])
            field_errors["emisor_tipo"].append(
                "Con emisor «Cargo» no se indica competencia"
            )
        if not datos.emisor_position_id:
            field_errors.setdefault("emisor_position_id", [])
            field_errors["emisor_position_id"].append("Indique el cargo emisor")
        else:
            cargo = db.scalar(
                select(GovernmentPosition.id).where(
                    GovernmentPosition.id == datos.emisor_position_id,
                    GovernmentPosition.company_id == ctx.company_id,
                )
            )
            if cargo is None:
                field_errors.setdefault("emisor_position_id", [])
                field_errors["emisor_position_id"].append("El cargo no existe en este ente")
    elif datos.emisor_tipo == "COMPETENCIA":
        if datos.emisor_position_id:
            field_errors.setdefault("emisor_tipo", [])
            field_errors["emisor_tipo"].append(
                "Con emisor «Competencia» no se indica cargo"
            )
        if not datos.emisor_competencia_accion or not datos.emisor_competencia_materia:
            field_errors.setdefault("emisor_tipo", [])
            field_errors["emisor_tipo"].append(
                "Con emisor «Competencia» indique acción y materia"
            )

    # Delegación
    if datos.figura in FIGURAS_DELEGACION:
        if datos.acto_medio is not None and datos.acto_medio != "GACETA":
            field_errors.setdefault("acto_medio", [])
            field_errors["acto_medio"].append(
                "La LOAP art. 40 exige publicar la delegación en gaceta"
            )
        if datos.emisor_tipo != "CUALQUIERA":
            field_errors.setdefault("emisor_tipo", [])
            field_errors["emisor_tipo"].append(
                "En la delegación emite el cargo delegante (LOAP art. 34)"
            )
    else:
        if datos.competencias:
            field_errors.setdefault("competencias", [])
            field_errors["competencias"].append(
                "Solo las delegaciones transfieren competencias"
            )
        if datos.prohibe_avocacion:
            field_errors.setdefault("prohibe_avocacion", [])
            field_errors["prohibe_avocacion"].append("Solo se avoca lo delegado")

    # Competencias repetidas
    vistas_competencias: set[tuple[str, str]] = set()
    for i, competencia in enumerate(datos.competencias):
        clave = (competencia.accion, competencia.materia)
        if clave in vistas_competencias:
            field_errors.setdefault(f"competencias.{i}", [])
            field_errors[f"competencias.{i}"].append("Competencia repetida")
        vistas_competencias.add(clave)

    # Autorización
    if datos.autorizacion_requerida:
        if not datos.autorizacion_etiqueta:
            field_errors.setdefault("autorizacion_etiqueta", [])
            field_errors["autorizacion_etiqueta"].append(
                "Indique la etiqueta de la autorización"
            )
        if not datos.autorizacion_ambito:
            field_errors.setdefault("autorizacion_ambito", [])
            field_errors["autorizacion_ambito"].append(
                "Indique el ámbito de la autorización"
            )
        if (
            datos.autorizacion_ambito == "MAXIMA_AUTORIDAD"
            and datos.figura != "SUPLENCIA"
        ):
            field_errors.setdefault("autorizacion_ambito", [])
            field_errors["autorizacion_ambito"].append(
                "El ámbito «Máxima autoridad» solo aplica a la suplencia"
            )
    else:
        if (
            datos.autorizacion_etiqueta
            or datos.autorizacion_ambito
            or datos.autorizacion_mas_de_dias is not None
        ):
            field_errors.setdefault("autorizacion_requerida", [])
            field_errors["autorizacion_requerida"].append(
                "Marque «Exige autorización» para configurarla"
            )

    # Acto
    if datos.act_id:
        acto = db.scalar(
            select(GovernmentAct.id).where(
                GovernmentAct.id == datos.act_id,
                GovernmentAct.company_id == ctx.company_id,
            )
        )
        if acto is None:
            field_errors.setdefault("act_id", [])
            field_errors["act_id"].append("El acto no existe en este ente")

    # Documentos
    vistos: set[tuple[str, str]] = set()
    for i, documento in enumerate(datos.documentos):
        tipo = db.scalar(
            select(DocumentType.id).where(
                DocumentType.id == documento.document_type_id,
                DocumentType.company_id == ctx.company_id,
                DocumentType.status == "ACTIVE",
            )
        )
        if tipo is None:
            field_errors.setdefault(f"documentos.{i}", [])
            field_errors[f"documentos.{i}"].append(
                "El tipo documental no existe o no está activo en este ente"
            )
        clave = (documento.document_type_id, documento.etapa)
        if clave in vistos:
            field_errors.setdefault(f"documentos.{i}", [])
            field_errors[f"documentos.{i}"].append(
                "Tipo documental repetido para la misma etapa"
            )
        vistos.add(clave)

    return field_errors


def _aplicar_campos(
    politica: GovernmentAssignmentPolicy,
    datos: Any,
) -> None:
    politica.nombre = datos.nombre
    politica.descripcion = datos.descripcion
    politica.figura = datos.figura
    politica.fundamento = datos.fundamento
    politica.act_id = datos.act_id
    politica.vigente_desde = datos.vigente_desde
    politica.vigente_hasta = datos.vigente_hasta
    politica.exige_fin = datos.exige_fin
    politica.max_dias = datos.max_dias
    politica.acto_medio = datos.acto_medio
    politica.emisor_tipo = datos.emisor_tipo
    politica.emisor_position_id = datos.emisor_position_id
    politica.emisor_competencia_accion = datos.emisor_competencia_accion
    politica.emisor_competencia_materia = datos.emisor_competencia_materia
    politica.autorizacion_requerida = datos.autorizacion_requerida
    politica.autorizacion_etiqueta = datos.autorizacion_etiqueta
    politica.autorizacion_ambito = datos.autorizacion_ambito
    politica.autorizacion_mas_de_dias = datos.autorizacion_mas_de_dias
    politica.prohibe_avocacion = datos.prohibe_avocacion


def _crear_competencias(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentAssignmentPolicy,
    competencias: list[Any],
) -> None:
    for competencia in competencias:
        db.add(
            GovernmentAssignmentPolicyCompetency(
                policy_id=str(politica.id),
                company_id=ctx.company_id,
                accion=competencia.accion,
                materia=competencia.materia,
                created_by=ctx.user_id,
            )
        )


def _crear_documentos(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentAssignmentPolicy,
    documentos: list[Any],
) -> None:
    for documento in documentos:
        db.add(
            GovernmentAssignmentPolicyDocument(
                policy_id=str(politica.id),
                company_id=ctx.company_id,
                document_type_id=documento.document_type_id,
                etapa=documento.etapa,
                obligatorio=documento.obligatorio,
                created_by=ctx.user_id,
            )
        )


def _borrar_detalles(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentAssignmentPolicy,
) -> None:
    db.query(GovernmentAssignmentPolicyCompetency).filter(
        GovernmentAssignmentPolicyCompetency.policy_id == str(politica.id)
    ).delete(synchronize_session=False)
    db.query(GovernmentAssignmentPolicyDocument).filter(
        GovernmentAssignmentPolicyDocument.policy_id == str(politica.id)
    ).delete(synchronize_session=False)


def crear(db: Session, ctx: CompanyContext, datos: Any) -> dict[str, Any]:
    field_errors = _validar(db, ctx, datos)
    if field_errors:
        raise _invalida(field_errors)

    existente = db.scalar(
        select(GovernmentAssignmentPolicy.id).where(
            GovernmentAssignmentPolicy.company_id == ctx.company_id,
            GovernmentAssignmentPolicy.codigo == datos.codigo,
        )
    )
    if existente is not None:
        raise ConflictError(
            "GOV_ASSIGNMENT_POLICY_DUPLICATE",
            "Ya hay una política con ese código; cree una nueva versión",
        )

    politica = GovernmentAssignmentPolicy(
        company_id=ctx.company_id,
        codigo=datos.codigo,
        numero_version=1,
        estado="BORRADOR",
        version=1,
        created_by=ctx.user_id,
    )
    _aplicar_campos(politica, datos)
    db.add(politica)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_ASSIGNMENT_POLICY_CONFLICT",
            "Otra política se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    _crear_competencias(db, ctx, politica, datos.competencias)
    _crear_documentos(db, ctx, politica, datos.documentos)
    db.flush()
    _historia(db, ctx, politica, EVENTOS["CREADA"])
    _auditar(
        db,
        ctx,
        "GOV_ASSIGNMENT_POLICY_CREATED",
        str(politica.id),
        {
            "codigo": politica.codigo,
            "nombre": politica.nombre,
            "estado": politica.estado,
            "numero_version": politica.numero_version,
        },
    )
    db.flush()
    return detalle(db, ctx, str(politica.id))


def editar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
    datos: Any,
) -> dict[str, Any]:
    politica = _para_escribir(db, ctx, id, version)
    _exigir_borrador(politica)

    if datos.codigo != politica.codigo:
        raise KontrolError(
            code="GOV_ASSIGNMENT_POLICY_INVALID",
            message="La política no es válida",
            status_code=422,
            field_errors={"codigo": ["El código no se cambia; cree una política nueva"]},
        )

    field_errors = _validar(db, ctx, datos)
    if field_errors:
        raise _invalida(field_errors)

    _aplicar_campos(politica, datos)
    politica.version += 1
    _borrar_detalles(db, ctx, politica)
    _crear_competencias(db, ctx, politica, datos.competencias)
    _crear_documentos(db, ctx, politica, datos.documentos)
    db.flush()
    _historia(db, ctx, politica, EVENTOS["EDITADA"])
    _auditar(
        db,
        ctx,
        "GOV_ASSIGNMENT_POLICY_UPDATED",
        str(politica.id),
        {
            "codigo": politica.codigo,
            "numero_version": politica.numero_version,
            "version": politica.version,
        },
    )
    db.flush()
    return detalle(db, ctx, str(politica.id))


def _vigencia_solapada(a: GovernmentAssignmentPolicy, b: GovernmentAssignmentPolicy) -> bool:
    a_desde = a.vigente_desde
    b_desde = b.vigente_desde
    a_hasta = a.vigente_hasta
    b_hasta = b.vigente_hasta
    inicio = max(a_desde, b_desde)
    fin = min(
        a_hasta if a_hasta is not None else date.max,
        b_hasta if b_hasta is not None else date.max,
    )
    return inicio <= fin


def activar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
) -> dict[str, Any]:
    politica = _para_escribir(db, ctx, id, version)
    _exigir_borrador(politica)

    if not politica.fundamento:
        raise _invalida({"fundamento": ["El fundamento es obligatorio para activar"]})

    vigente_conflicto = db.scalars(
        select(GovernmentAssignmentPolicy)
        .where(
            GovernmentAssignmentPolicy.company_id == ctx.company_id,
            GovernmentAssignmentPolicy.estado == "VIGENTE",
            GovernmentAssignmentPolicy.figura == politica.figura,
            GovernmentAssignmentPolicy.codigo != politica.codigo,
        )
        .with_for_update()
    ).all()
    for vigente in vigente_conflicto:
        if _vigencia_solapada(vigente, politica):
            raise ConflictError(
                "GOV_ASSIGNMENT_POLICY_OVERLAP",
                f"Ya hay una política vigente para esa figura en ese período: "
                f"{vigente.codigo} v{vigente.numero_version}",
            )

    vigente_anterior = db.scalar(
        select(GovernmentAssignmentPolicy)
        .where(
            GovernmentAssignmentPolicy.company_id == ctx.company_id,
            GovernmentAssignmentPolicy.codigo == politica.codigo,
            GovernmentAssignmentPolicy.estado == "VIGENTE",
        )
        .with_for_update()
    )
    if vigente_anterior is not None and vigente_anterior.id != politica.id:
        vigente_anterior.estado = "CERRADA"
        vigente_anterior.cerrada_en = instante_actual()
        vigente_anterior.cerrada_por = ctx.user_id
        vigente_anterior.motivo_cierre = (
            f"Sustituida por la versión {politica.numero_version}"
        )
        vigente_anterior.version += 1
        db.flush()
        _historia(db, ctx, vigente_anterior, EVENTOS["SUSTITUIDA"])
        _auditar(
            db,
            ctx,
            "GOV_ASSIGNMENT_POLICY_CLOSED",
            str(vigente_anterior.id),
            {
                "codigo": vigente_anterior.codigo,
                "numero_version": vigente_anterior.numero_version,
                "estado": vigente_anterior.estado,
                "motivo": vigente_anterior.motivo_cierre,
            },
            motivo=vigente_anterior.motivo_cierre,
        )
        db.flush()

    politica.estado = "VIGENTE"
    politica.activada_por = ctx.user_id
    politica.activada_en = instante_actual()
    politica.version += 1
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_ASSIGNMENT_POLICY_CONFLICT",
            "Otra política se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    _historia(db, ctx, politica, EVENTOS["ACTIVADA"])
    _auditar(
        db,
        ctx,
        "GOV_ASSIGNMENT_POLICY_ACTIVATED",
        str(politica.id),
        {
            "codigo": politica.codigo,
            "numero_version": politica.numero_version,
            "estado": politica.estado,
            "vigente_desde": politica.vigente_desde,
            "vigente_hasta": politica.vigente_hasta,
        },
    )
    db.flush()
    return detalle(db, ctx, str(politica.id))


def cerrar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
    datos: Any,
) -> dict[str, Any]:
    politica = _para_escribir(db, ctx, id, version)
    if politica.estado != "VIGENTE":
        raise ConflictError(
            "GOV_ASSIGNMENT_POLICY_NOT_VIGENTE",
            "Solo una política vigente se puede cerrar",
        )
    if not datos.motivo or not datos.motivo.strip():
        raise KontrolError(
            code="GOV_ASSIGNMENT_POLICY_INVALID",
            message="La política no es válida",
            status_code=422,
            field_errors={"motivo": ["El motivo es obligatorio"]},
        )
    politica.estado = "CERRADA"
    politica.cerrada_en = instante_actual()
    politica.cerrada_por = ctx.user_id
    politica.motivo_cierre = datos.motivo
    politica.version += 1
    db.flush()
    _historia(db, ctx, politica, EVENTOS["CERRADA"])
    _auditar(
        db,
        ctx,
        "GOV_ASSIGNMENT_POLICY_CLOSED",
        str(politica.id),
        {
            "codigo": politica.codigo,
            "numero_version": politica.numero_version,
            "estado": politica.estado,
            "motivo": politica.motivo_cierre,
        },
        motivo=politica.motivo_cierre,
    )
    db.flush()
    return detalle(db, ctx, str(politica.id))


def nueva_version(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
) -> dict[str, Any]:
    politica = _para_escribir(db, ctx, id, version)
    if politica.estado == "BORRADOR":
        raise ConflictError(
            "GOV_ASSIGNMENT_POLICY_NOT_VERSIONABLE",
            "Una política en borrador se edita, no se versiona",
        )
    max_numero = db.scalar(
        select(func.max(GovernmentAssignmentPolicy.numero_version)).where(
            GovernmentAssignmentPolicy.company_id == ctx.company_id,
            GovernmentAssignmentPolicy.codigo == politica.codigo,
        )
    )
    if politica.numero_version != (max_numero or 0):
        raise ConflictError(
            "GOV_ASSIGNMENT_POLICY_NOT_VERSIONABLE",
            "Solo la última versión se puede versionar",
        )
    borrador_existente = db.scalar(
        select(GovernmentAssignmentPolicy.id).where(
            GovernmentAssignmentPolicy.company_id == ctx.company_id,
            GovernmentAssignmentPolicy.codigo == politica.codigo,
            GovernmentAssignmentPolicy.estado == "BORRADOR",
        )
    )
    if borrador_existente is not None:
        raise ConflictError(
            "GOV_ASSIGNMENT_POLICY_DUPLICATE",
            "Ya hay una versión en borrador de esta política",
        )

    nueva = GovernmentAssignmentPolicy(
        company_id=ctx.company_id,
        codigo=politica.codigo,
        numero_version=politica.numero_version + 1,
        nombre=politica.nombre,
        descripcion=politica.descripcion,
        figura=politica.figura,
        fundamento=politica.fundamento,
        act_id=politica.act_id,
        vigente_desde=politica.vigente_desde,
        vigente_hasta=politica.vigente_hasta,
        estado="BORRADOR",
        exige_fin=politica.exige_fin,
        max_dias=politica.max_dias,
        acto_medio=politica.acto_medio,
        emisor_tipo=politica.emisor_tipo,
        emisor_position_id=politica.emisor_position_id,
        emisor_competencia_accion=politica.emisor_competencia_accion,
        emisor_competencia_materia=politica.emisor_competencia_materia,
        autorizacion_requerida=politica.autorizacion_requerida,
        autorizacion_etiqueta=politica.autorizacion_etiqueta,
        autorizacion_ambito=politica.autorizacion_ambito,
        autorizacion_mas_de_dias=politica.autorizacion_mas_de_dias,
        prohibe_avocacion=politica.prohibe_avocacion,
        version_anterior_id=str(politica.id),
        version=1,
        created_by=ctx.user_id,
    )
    db.add(nueva)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_ASSIGNMENT_POLICY_CONFLICT",
            "Otra política se registró al mismo tiempo; vuelva a intentarlo",
        ) from None

    competencias = db.scalars(
        select(GovernmentAssignmentPolicyCompetency).where(
            GovernmentAssignmentPolicyCompetency.policy_id == str(politica.id),
            GovernmentAssignmentPolicyCompetency.company_id == ctx.company_id,
        )
    ).all()
    for competencia in competencias:
        db.add(
            GovernmentAssignmentPolicyCompetency(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                accion=competencia.accion,
                materia=competencia.materia,
                created_by=ctx.user_id,
            )
        )

    documentos = db.scalars(
        select(GovernmentAssignmentPolicyDocument).where(
            GovernmentAssignmentPolicyDocument.policy_id == str(politica.id),
            GovernmentAssignmentPolicyDocument.company_id == ctx.company_id,
        )
    ).all()
    for documento in documentos:
        db.add(
            GovernmentAssignmentPolicyDocument(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                document_type_id=documento.document_type_id,
                etapa=documento.etapa,
                obligatorio=documento.obligatorio,
                created_by=ctx.user_id,
            )
        )

    db.flush()
    _historia(db, ctx, nueva, EVENTOS["NUEVA_VERSION"])
    _auditar(
        db,
        ctx,
        "GOV_ASSIGNMENT_POLICY_VERSIONED",
        str(nueva.id),
        {
            "codigo": nueva.codigo,
            "numero_version": nueva.numero_version,
            "sustituye": politica.numero_version,
        },
    )
    db.flush()
    return detalle(db, ctx, str(nueva.id))
