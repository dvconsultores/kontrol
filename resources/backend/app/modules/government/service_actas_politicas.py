from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import DocumentType
from app.modules.government.models import (
    GovernmentAct,
    GovernmentHandoverPolicy,
    GovernmentHandoverPolicyBinding,
    GovernmentHandoverPolicyDeadline,
    GovernmentHandoverPolicyHistory,
    GovernmentHandoverPolicyRequirement,
    GovernmentUnit,
)
from app.modules.government.service_actas_regla import (
    PATRON_POR_DEFECTO,
    PLAZOS_LEGALES,
    SUPUESTOS,
    TESTIGOS_LEGALES,
    ente_de,
    instantanea,
    motivo_codigo_requisito_invalido,
    motivo_patron_invalido,
    motivo_plazo_invalido,
    motivo_vinculo_invalido,
    politicas_que_usan,
    supuesto,
)
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.shared.audit import record_audit
from app.shared.clock import instante_actual

ENTIDAD = "GovernmentHandoverPolicy"

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

_EVIDENCIAS = {
    "DOCUMENTO": "Documento",
    "CERTIFICACION": "Certificación",
    "DECLARACION": "Declaración",
    "DATO": "Dato",
}

_AMBITOS_REQUISITO = {
    "TODAS": "Todas las actas",
    "ENTE": "Acta de la entidad",
    "UNIDAD": "Acta de una unidad",
}

_ALCANCES = {
    "ENTE": "Entidad",
    "UNIDAD": "Unidad",
}

_HITOS = {
    "ELABORACION": "Elaboración del acta",
    "REMISION_UAI": "Remisión a la UAI",
}

_UNIDADES_PLAZO = {
    "DIAS_HABILES": "Días hábiles",
    "DIAS_CONTINUOS": "Días continuos",
}


def _invalida(field_errors: dict[str, list[str]], motivos: list[str] | None = None) -> KontrolError:
    return KontrolError(
        code="GOV_HANDOVER_POLICY_INVALID",
        message="La política no se puede activar" if motivos is not None else "La política no es válida",
        status_code=422,
        field_errors=field_errors,
        details={"motivos": motivos} if motivos is not None else None,
    )


def catalogo() -> dict[str, Any]:
    return {
        "estados": [{"codigo": c, "etiqueta": e} for c, e in _ESTADOS.items()],
        "evidencias": [{"codigo": c, "etiqueta": e} for c, e in _EVIDENCIAS.items()],
        "ambitos_requisito": [
            {"codigo": c, "etiqueta": e} for c, e in _AMBITOS_REQUISITO.items()
        ],
        "alcances": [{"codigo": c, "etiqueta": e} for c, e in _ALCANCES.items()],
        "hitos": [{"codigo": c, "etiqueta": e} for c, e in _HITOS.items()],
        "unidades_plazo": [
            {"codigo": c, "etiqueta": e} for c, e in _UNIDADES_PLAZO.items()
        ],
    }


def opciones(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    ente = ente_de(db, ctx)
    nivel = ente.nivel_territorial if ente else None
    supuestos: list[dict[str, Any]] = []
    for s in SUPUESTOS:
        ambitos = s.get("ambitos") or []
        ambito_principal = ambitos[0] if ambitos else "ENTE"
        motivo = motivo_vinculo_invalido(nivel, s["codigo"], ambito_principal)
        declarable = s["vinculo"] == "DECLARADO" and motivo is None
        supuestos.append(
            {
                "codigo": s["codigo"],
                "articulo": s["articulo"],
                "titulo": s["titulo"],
                "sujeto": s["sujeto"],
                "vinculo": s["vinculo"],
                "niveles": s.get("niveles"),
                "ambitos": ambitos,
                "nota": s.get("nota"),
                "anexos": s.get("anexos", []),
                "declarable": declarable,
                "motivo_no_declarable": None if declarable else motivo,
            }
        )

    unidades = db.scalars(
        select(GovernmentUnit)
        .where(
            GovernmentUnit.company_id == ctx.company_id,
            GovernmentUnit.status == "ACTIVA",
        )
        .order_by(GovernmentUnit.code.asc())
    ).all()
    tipos_documento = db.scalars(
        select(DocumentType)
        .where(DocumentType.company_id == ctx.company_id)
        .order_by(DocumentType.name.asc())
    ).all()
    actos = db.scalars(
        select(GovernmentAct)
        .where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.status != "BORRADOR",
        )
        .order_by(GovernmentAct.fecha.desc())
    ).all()
    return {
        "nivel_territorial": nivel,
        "forma_organizativa": ente.forma_organizativa if ente else None,
        "supuestos": supuestos,
        "unidades": [
            {"id": str(u.id), "codigo": u.code, "nombre": u.name} for u in unidades
        ],
        "tipos_documento": [
            {"id": str(t.id), "nombre": t.name} for t in tipos_documento
        ],
        "actos": [{"id": str(a.id), "etiqueta": f"{a.tipo} {a.numero}"} for a in actos],
        "testigos_legales": TESTIGOS_LEGALES,
        "plazos_legales": PLAZOS_LEGALES,
        "patron_por_defecto": PATRON_POR_DEFECTO,
    }


def _resumen(db: Session, ctx: CompanyContext, politica: GovernmentHandoverPolicy) -> dict[str, Any]:
    vinculos = db.scalar(
        select(func.count(GovernmentHandoverPolicyBinding.id)).where(
            GovernmentHandoverPolicyBinding.policy_id == str(politica.id),
            GovernmentHandoverPolicyBinding.company_id == ctx.company_id,
        )
    ) or 0
    requisitos = db.scalar(
        select(func.count(GovernmentHandoverPolicyRequirement.id)).where(
            GovernmentHandoverPolicyRequirement.policy_id == str(politica.id),
            GovernmentHandoverPolicyRequirement.company_id == ctx.company_id,
        )
    ) or 0
    return {
        "id": str(politica.id),
        "codigo": politica.codigo,
        "numero_version": politica.numero_version,
        "nombre": politica.nombre,
        "estado": politica.estado,
        "estado_etiqueta": _ESTADOS.get(politica.estado, politica.estado),
        "vigente_desde": politica.vigente_desde,
        "vigente_hasta": politica.vigente_hasta,
        "total_vinculos": vinculos,
        "total_requisitos": requisitos,
        "version": politica.version,
    }


def listar(
    db: Session,
    ctx: CompanyContext,
    estado: str | None = None,
    q: str | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> dict[str, Any]:
    condicion = [GovernmentHandoverPolicy.company_id == ctx.company_id]
    if estado:
        condicion.append(GovernmentHandoverPolicy.estado == estado)
    if q:
        like = f"%{q}%"
        condicion.append(
            or_(
                GovernmentHandoverPolicy.codigo.ilike(like),
                GovernmentHandoverPolicy.nombre.ilike(like),
            )
        )
    total = db.scalar(
        select(func.count(GovernmentHandoverPolicy.id)).where(*condicion)
    ) or 0
    politicas = db.scalars(
        select(GovernmentHandoverPolicy)
        .where(*condicion)
        .order_by(
            GovernmentHandoverPolicy.codigo.asc(),
            GovernmentHandoverPolicy.numero_version.desc(),
        )
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()
    return {
        "items": [_resumen(db, ctx, p) for p in politicas],
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
    }


def _para_escribir(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
) -> GovernmentHandoverPolicy:
    if version is None:
        raise KontrolError(
            code="GOV_HANDOVER_POLICY_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    politica = db.scalar(
        select(GovernmentHandoverPolicy)
        .where(
            GovernmentHandoverPolicy.id == id,
            GovernmentHandoverPolicy.company_id == ctx.company_id,
        )
        .with_for_update()
    )
    if not politica:
        raise NotFoundError(
            "GOV_HANDOVER_POLICY_NOT_FOUND",
            "La política no existe en este ente",
        )
    if politica.version != version:
        raise ConflictError(
            "GOV_HANDOVER_POLICY_STALE",
            "La política cambió desde que la abrió; recárguela",
            details={"version_actual": politica.version},
        )
    return politica


def _exigir_borrador(politica: GovernmentHandoverPolicy) -> None:
    if politica.estado != "BORRADOR":
        raise ConflictError(
            "GOV_HANDOVER_POLICY_STATE",
            "Solo una política en borrador admite esta operación",
        )


def _instantanea_historia(db: Session, politica: GovernmentHandoverPolicy) -> dict[str, Any]:
    vinculos = [
        {
            "supuesto": v.supuesto,
            "alcance": v.alcance,
            "unit_id": str(v.unit_id) if v.unit_id else None,
        }
        for v in db.scalars(
            select(GovernmentHandoverPolicyBinding).where(
                GovernmentHandoverPolicyBinding.policy_id == str(politica.id)
            )
        ).all()
    ]
    requisitos = [
        {
            "codigo": r.codigo,
            "titulo": r.titulo,
            "evidencia": r.evidencia,
            "obligatorio": r.obligatorio,
            "ambito": r.ambito,
            "supuesto": r.supuesto,
            "document_type_id": str(r.document_type_id) if r.document_type_id else None,
            "fuente": r.fuente,
        }
        for r in db.scalars(
            select(GovernmentHandoverPolicyRequirement)
            .where(GovernmentHandoverPolicyRequirement.policy_id == str(politica.id))
            .order_by(GovernmentHandoverPolicyRequirement.codigo.asc())
        ).all()
    ]
    plazos = [
        {"hito": p.hito, "valor": p.valor, "unidad": p.unidad, "fuente": p.fuente}
        for p in db.scalars(
            select(GovernmentHandoverPolicyDeadline).where(
                GovernmentHandoverPolicyDeadline.policy_id == str(politica.id)
            )
        ).all()
    ]
    return {
        "codigo": politica.codigo,
        "numero_version": politica.numero_version,
        "nombre": politica.nombre,
        "descripcion": politica.descripcion,
        "fundamento": politica.fundamento,
        "act_id": str(politica.act_id) if politica.act_id else None,
        "vigente_desde": politica.vigente_desde.isoformat(),
        "vigente_hasta": politica.vigente_hasta.isoformat()
        if politica.vigente_hasta
        else None,
        "estado": politica.estado,
        "numeracion_patron": politica.numeracion_patron,
        "testigos_en_entrega": politica.testigos_en_entrega,
        "cargo_maxima_autoridad_codigo": politica.cargo_maxima_autoridad_codigo,
        "motivo_cierre": politica.motivo_cierre,
        "vinculos": vinculos,
        "requisitos": requisitos,
        "plazos": plazos,
    }


def _historia(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentHandoverPolicy,
    evento: str,
) -> None:
    db.add(
        GovernmentHandoverPolicyHistory(
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
        limpio[k] = v.isoformat() if hasattr(v, "isoformat") else v
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
    politica: GovernmentHandoverPolicy,
) -> list[dict[str, Any]]:
    eventos = db.scalars(
        select(GovernmentHandoverPolicyHistory)
        .where(
            GovernmentHandoverPolicyHistory.policy_id == str(politica.id),
            GovernmentHandoverPolicyHistory.company_id == ctx.company_id,
        )
        .order_by(GovernmentHandoverPolicyHistory.created_at.asc())
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
    politica: GovernmentHandoverPolicy,
) -> list[dict[str, Any]]:
    versiones = db.scalars(
        select(GovernmentHandoverPolicy)
        .where(GovernmentHandoverPolicy.company_id == ctx.company_id)
        .where(GovernmentHandoverPolicy.codigo == politica.codigo)
        .order_by(GovernmentHandoverPolicy.numero_version.desc())
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
        select(GovernmentHandoverPolicy.id).where(
            GovernmentHandoverPolicy.company_id == ctx.company_id,
            GovernmentHandoverPolicy.codigo == codigo,
            GovernmentHandoverPolicy.estado == "BORRADOR",
        )
    )
    return borrador is not None


def _aplicar_campos(
    politica: GovernmentHandoverPolicy,
    datos: Any,
) -> None:
    politica.codigo = datos.codigo
    politica.nombre = datos.nombre
    politica.descripcion = datos.descripcion
    politica.fundamento = datos.fundamento
    politica.act_id = datos.act_id
    politica.vigente_desde = datos.vigente_desde
    politica.vigente_hasta = datos.vigente_hasta
    politica.numeracion_patron = datos.numeracion_patron
    politica.testigos_en_entrega = datos.testigos_en_entrega
    politica.cargo_maxima_autoridad_codigo = datos.cargo_maxima_autoridad_codigo


def _crear_detalles(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentHandoverPolicy,
    datos: Any,
) -> None:
    for vinculo in datos.vinculos:
        db.add(
            GovernmentHandoverPolicyBinding(
                policy_id=str(politica.id),
                company_id=ctx.company_id,
                supuesto=vinculo.supuesto,
                alcance=vinculo.alcance,
                unit_id=vinculo.unit_id,
                created_by=ctx.user_id,
            )
        )
    for requisito in datos.requisitos:
        db.add(
            GovernmentHandoverPolicyRequirement(
                policy_id=str(politica.id),
                company_id=ctx.company_id,
                codigo=requisito.codigo,
                titulo=requisito.titulo,
                evidencia=requisito.evidencia,
                obligatorio=requisito.obligatorio,
                ambito=requisito.ambito,
                supuesto=requisito.supuesto,
                document_type_id=requisito.document_type_id,
                fuente=requisito.fuente,
                created_by=ctx.user_id,
            )
        )
    for plazo in datos.plazos:
        db.add(
            GovernmentHandoverPolicyDeadline(
                policy_id=str(politica.id),
                company_id=ctx.company_id,
                hito=plazo.hito,
                valor=plazo.valor,
                unidad=plazo.unidad,
                fuente=plazo.fuente,
                created_by=ctx.user_id,
            )
        )


def _borrar_detalles(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentHandoverPolicy,
) -> None:
    db.query(GovernmentHandoverPolicyBinding).filter(
        GovernmentHandoverPolicyBinding.policy_id == str(politica.id)
    ).delete(synchronize_session=False)
    db.query(GovernmentHandoverPolicyRequirement).filter(
        GovernmentHandoverPolicyRequirement.policy_id == str(politica.id)
    ).delete(synchronize_session=False)
    db.query(GovernmentHandoverPolicyDeadline).filter(
        GovernmentHandoverPolicyDeadline.policy_id == str(politica.id)
    ).delete(synchronize_session=False)


def _detalle_salida(db: Session, ctx: CompanyContext, politica: GovernmentHandoverPolicy) -> dict[str, Any]:
    vinculos_rows = db.scalars(
        select(GovernmentHandoverPolicyBinding)
        .where(
            GovernmentHandoverPolicyBinding.policy_id == str(politica.id),
            GovernmentHandoverPolicyBinding.company_id == ctx.company_id,
        )
        .order_by(GovernmentHandoverPolicyBinding.created_at.asc())
    ).all()
    vinculos = []
    for v in vinculos_rows:
        s = supuesto(v.supuesto)
        unit_name = None
        if v.unit_id:
            unit = db.scalar(
                select(GovernmentUnit).where(
                    GovernmentUnit.id == v.unit_id,
                    GovernmentUnit.company_id == ctx.company_id,
                )
            )
            unit_name = unit.name if unit else None
        vinculos.append(
            {
                "supuesto": v.supuesto,
                "articulo": s["articulo"] if s else None,
                "titulo": s["titulo"] if s else None,
                "alcance": v.alcance,
                "unit_id": str(v.unit_id) if v.unit_id else None,
                "unidad": unit_name,
            }
        )

    requisitos_rows = db.scalars(
        select(GovernmentHandoverPolicyRequirement)
        .where(
            GovernmentHandoverPolicyRequirement.policy_id == str(politica.id),
            GovernmentHandoverPolicyRequirement.company_id == ctx.company_id,
        )
        .order_by(GovernmentHandoverPolicyRequirement.created_at.asc())
    ).all()
    requisitos = []
    for r in requisitos_rows:
        doc_name = None
        if r.document_type_id:
            doc = db.scalar(
                select(DocumentType).where(
                    DocumentType.id == r.document_type_id,
                    DocumentType.company_id == ctx.company_id,
                )
            )
            doc_name = doc.name if doc else None
        requisitos.append(
            {
                "codigo": r.codigo,
                "titulo": r.titulo,
                "evidencia": r.evidencia,
                "obligatorio": r.obligatorio,
                "ambito": r.ambito,
                "supuesto": r.supuesto,
                "document_type_id": str(r.document_type_id)
                if r.document_type_id
                else None,
                "document_type_nombre": doc_name,
                "fuente": r.fuente,
            }
        )

    plazos_rows = db.scalars(
        select(GovernmentHandoverPolicyDeadline)
        .where(
            GovernmentHandoverPolicyDeadline.policy_id == str(politica.id),
            GovernmentHandoverPolicyDeadline.company_id == ctx.company_id,
        )
        .order_by(GovernmentHandoverPolicyDeadline.created_at.asc())
    ).all()
    plazos = []
    legal_por_hito = {p["hito"]: p for p in PLAZOS_LEGALES}
    for p in plazos_rows:
        legal = legal_por_hito.get(p.hito)
        plazos.append(
            {
                "hito": p.hito,
                "valor": p.valor,
                "unidad": p.unidad,
                "fuente": p.fuente,
                "legal_valor": legal["valor"] if legal else None,
                "legal_fuente": legal["fuente"] if legal else None,
            }
        )

    regla_ente = instantanea(
        db, ctx, politica, ambito="ENTE", fecha=politica.vigente_desde
    )

    detalle_data: dict[str, Any] = {
        "id": str(politica.id),
        "codigo": politica.codigo,
        "numero_version": politica.numero_version,
        "nombre": politica.nombre,
        "descripcion": politica.descripcion,
        "fundamento": politica.fundamento,
        "act_id": str(politica.act_id) if politica.act_id else None,
        "vigente_desde": politica.vigente_desde,
        "vigente_hasta": politica.vigente_hasta,
        "estado": politica.estado,
        "estado_etiqueta": _ESTADOS.get(politica.estado, politica.estado),
        "numeracion_patron": politica.numeracion_patron,
        "testigos_en_entrega": politica.testigos_en_entrega,
        "cargo_maxima_autoridad_codigo": politica.cargo_maxima_autoridad_codigo,
        "version_anterior_id": str(politica.version_anterior_id)
        if politica.version_anterior_id
        else None,
        "activada_en": politica.activada_en,
        "cerrada_en": politica.cerrada_en,
        "motivo_cierre": politica.motivo_cierre,
        "version": politica.version,
        "vinculos": vinculos,
        "requisitos": requisitos,
        "total_vinculos": len(vinculos),
        "total_requisitos": len(requisitos),
        "plazos": plazos,
        "regla_ente": regla_ente,
    }
    return detalle_data


def detalle(db: Session, ctx: CompanyContext, id: str) -> dict[str, Any]:
    politica = db.scalar(
        select(GovernmentHandoverPolicy).where(
            GovernmentHandoverPolicy.id == id,
            GovernmentHandoverPolicy.company_id == ctx.company_id,
        )
    )
    if not politica:
        raise NotFoundError(
            "GOV_HANDOVER_POLICY_NOT_FOUND",
            "La política no existe en este ente",
        )

    detalle_data = _detalle_salida(db, ctx, politica)
    detalle_data["historia"] = _historia_salida(db, ctx, politica)
    detalle_data["versiones"] = _versiones_salida(db, ctx, politica)
    detalle_data["actas_que_la_usan"] = politicas_que_usan(db, ctx, str(politica.id))
    detalle_data["acciones"] = {
        "editar": politica.estado == "BORRADOR",
        "activar": politica.estado == "BORRADOR",
        "cerrar": politica.estado == "VIGENTE",
        "nueva_version": politica.estado in ("VIGENTE", "CERRADA"),
    }
    return detalle_data


def _validar(
    db: Session,
    ctx: CompanyContext,
    datos: Any,
) -> dict[str, list[str]]:
    field_errors: dict[str, list[str]] = {}

    if datos.fundamento is not None and (
        len(datos.fundamento) < 10 or len(datos.fundamento) > 2000
    ):
        field_errors.setdefault("fundamento", []).append(
            "El fundamento debe tener entre 10 y 2000 caracteres"
        )
    if datos.vigente_hasta is not None and datos.vigente_hasta < datos.vigente_desde:
        field_errors.setdefault("vigente_hasta", []).append(
            "La vigencia hasta no puede ser anterior a la vigencia desde"
        )
    if datos.act_id is not None:
        acto = db.scalar(
            select(GovernmentAct).where(
                GovernmentAct.id == datos.act_id,
                GovernmentAct.company_id == ctx.company_id,
            )
        )
        if acto is None:
            field_errors.setdefault("act_id", []).append(
                "El acto no existe en esta empresa"
            )

    if datos.numeracion_patron is not None:
        motivo = motivo_patron_invalido(datos.numeracion_patron)
        if motivo is not None:
            field_errors.setdefault("numeracion_patron", []).append(motivo)

    ente = ente_de(db, ctx)
    nivel = ente.nivel_territorial if ente else None

    vinculos_vistos: set[tuple[str, str, str | None]] = set()
    for i, vinculo in enumerate(datos.vinculos):
        clave = f"vinculos.{i}"
        motivo = motivo_vinculo_invalido(nivel, vinculo.supuesto, vinculo.alcance)
        if motivo is not None:
            field_errors.setdefault(f"{clave}.supuesto", []).append(motivo)
        if vinculo.alcance == "UNIDAD" and vinculo.unit_id is None:
            field_errors.setdefault(f"{clave}.unit_id", []).append(
                "El alcance unidad exige una unidad"
            )
        if vinculo.alcance == "ENTE" and vinculo.unit_id is not None:
            field_errors.setdefault(f"{clave}.unit_id", []).append(
                "El alcance ente no admite unidad"
            )
        if vinculo.alcance == "UNIDAD" and vinculo.unit_id is not None:
            unidad = db.scalar(
                select(GovernmentUnit).where(
                    GovernmentUnit.id == vinculo.unit_id,
                    GovernmentUnit.company_id == ctx.company_id,
                )
            )
            if unidad is None:
                field_errors.setdefault(f"{clave}.unit_id", []).append(
                    "La unidad no existe en esta empresa"
                )
        dupla = (vinculo.supuesto, vinculo.alcance, vinculo.unit_id)
        if dupla in vinculos_vistos:
            field_errors.setdefault(f"{clave}.supuesto", []).append(
                "El vínculo está duplicado"
            )
        else:
            vinculos_vistos.add(dupla)

    vistos_requisitos: set[str] = set()
    supuestos_vinculos = {v.supuesto for v in datos.vinculos}
    for i, requisito in enumerate(datos.requisitos):
        clave = f"requisitos.{i}"
        motivo_codigo = motivo_codigo_requisito_invalido(requisito.codigo)
        if motivo_codigo is not None:
            field_errors.setdefault(f"{clave}.codigo", []).append(motivo_codigo)
        if requisito.codigo in vistos_requisitos:
            field_errors.setdefault(f"{clave}.codigo", []).append(
                "El código del requisito está duplicado"
            )
        else:
            vistos_requisitos.add(requisito.codigo)
        if (
            requisito.supuesto is not None
            and requisito.supuesto != "N34_ART11"
            and requisito.supuesto not in supuestos_vinculos
        ):
            field_errors.setdefault(f"{clave}.supuesto", []).append(
                "El requisito se ata a un supuesto que la política no declara."
            )
        if requisito.document_type_id is not None:
            tipo = db.scalar(
                select(DocumentType).where(
                    DocumentType.id == requisito.document_type_id,
                    DocumentType.company_id == ctx.company_id,
                )
            )
            if tipo is None:
                field_errors.setdefault(f"{clave}.document_type_id", []).append(
                    "El tipo de documento no existe en esta empresa"
                )
            if requisito.evidencia in ("DECLARACION", "DATO"):
                field_errors.setdefault(f"{clave}.document_type_id", []).append(
                    "La evidencia no admite tipo de documento"
                )

    vistos_hitos: set[str] = set()
    for i, plazo in enumerate(datos.plazos):
        clave = f"plazos.{i}"
        if plazo.hito in vistos_hitos:
            field_errors.setdefault(f"{clave}.hito", []).append(
                "El hito está duplicado"
            )
        else:
            vistos_hitos.add(plazo.hito)
        motivo = motivo_plazo_invalido(plazo.hito, plazo.valor, plazo.unidad)
        if motivo is not None:
            field_errors.setdefault(f"{clave}.valor", []).append(motivo)

    return field_errors


def crear(db: Session, ctx: CompanyContext, datos: Any) -> dict[str, Any]:
    field_errors = _validar(db, ctx, datos)
    if field_errors:
        raise _invalida(field_errors)

    existente = db.scalar(
        select(GovernmentHandoverPolicy.id).where(
            GovernmentHandoverPolicy.company_id == ctx.company_id,
            GovernmentHandoverPolicy.codigo == datos.codigo,
        )
    )
    if existente is not None:
        raise _invalida({"codigo": ["Ya existe una política con ese código."]})

    politica = GovernmentHandoverPolicy(
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
            "GOV_HANDOVER_POLICY_CONFLICT",
            "Otra política se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    _crear_detalles(db, ctx, politica, datos)
    db.flush()
    _historia(db, ctx, politica, EVENTOS["CREADA"])
    _auditar(
        db,
        ctx,
        "GOV_HANDOVER_POLICY_CREATED",
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
        raise _invalida({"codigo": ["El código no se cambia; cree una política nueva"]})

    field_errors = _validar(db, ctx, datos)
    if field_errors:
        raise _invalida(field_errors)

    _aplicar_campos(politica, datos)
    politica.version += 1
    _borrar_detalles(db, ctx, politica)
    _crear_detalles(db, ctx, politica, datos)
    db.flush()
    _historia(db, ctx, politica, EVENTOS["EDITADA"])
    _auditar(
        db,
        ctx,
        "GOV_HANDOVER_POLICY_UPDATED",
        str(politica.id),
        {
            "codigo": politica.codigo,
            "numero_version": politica.numero_version,
            "version": politica.version,
        },
    )
    db.flush()
    return detalle(db, ctx, str(politica.id))


def activar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
) -> dict[str, Any]:
    politica = _para_escribir(db, ctx, id, version)
    _exigir_borrador(politica)

    motivos: list[str] = []
    if not politica.fundamento:
        motivos.append("La política necesita un fundamento para activarse.")

    ente = ente_de(db, ctx)
    nivel = ente.nivel_territorial if ente else None
    for vinculo in db.scalars(
        select(GovernmentHandoverPolicyBinding).where(
            GovernmentHandoverPolicyBinding.policy_id == str(politica.id),
            GovernmentHandoverPolicyBinding.company_id == ctx.company_id,
        )
    ).all():
        motivo = motivo_vinculo_invalido(nivel, vinculo.supuesto, vinculo.alcance)
        if motivo is not None:
            motivos.append(f"{vinculo.supuesto}: {motivo}")

    if motivos:
        raise _invalida({}, motivos)

    vigente_anterior = db.scalar(
        select(GovernmentHandoverPolicy)
        .where(
            GovernmentHandoverPolicy.company_id == ctx.company_id,
            GovernmentHandoverPolicy.estado == "VIGENTE",
        )
        .with_for_update()
    )
    sustituye = None
    if vigente_anterior is not None and vigente_anterior.id != politica.id:
        sustituye = str(vigente_anterior.id)
        vigente_anterior.estado = "CERRADA"
        vigente_anterior.cerrada_en = instante_actual()
        vigente_anterior.cerrada_por = ctx.user_id
        vigente_anterior.motivo_cierre = (
            f"Sustituida por {politica.codigo} v{politica.numero_version}"
        )
        vigente_anterior.version += 1
        db.flush()
        _historia(db, ctx, vigente_anterior, EVENTOS["SUSTITUIDA"])
        _auditar(
            db,
            ctx,
            "GOV_HANDOVER_POLICY_CLOSED",
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
            "GOV_HANDOVER_POLICY_CONFLICT",
            "Otra política se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    _historia(db, ctx, politica, EVENTOS["ACTIVADA"])
    _auditar(
        db,
        ctx,
        "GOV_HANDOVER_POLICY_ACTIVATED",
        str(politica.id),
        {
            "codigo": politica.codigo,
            "numero_version": politica.numero_version,
            "estado": politica.estado,
            "sustituye": sustituye,
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
            "GOV_HANDOVER_POLICY_STATE",
            "Solo una política vigente se puede cerrar",
        )
    if not datos.motivo or not datos.motivo.strip():
        raise _invalida({"motivo": ["El motivo es obligatorio"]})
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
        "GOV_HANDOVER_POLICY_CLOSED",
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
            "GOV_HANDOVER_POLICY_STATE",
            "Una política en borrador se edita, no se versiona",
        )
    if _existe_borrador_codigo(db, ctx, politica.codigo):
        raise ConflictError(
            "GOV_HANDOVER_POLICY_STATE",
            "Ya hay un borrador de esta política; termínelo antes de crear otra versión",
        )

    max_numero = db.scalar(
        select(func.max(GovernmentHandoverPolicy.numero_version)).where(
            GovernmentHandoverPolicy.company_id == ctx.company_id,
            GovernmentHandoverPolicy.codigo == politica.codigo,
        )
    )
    if politica.numero_version != (max_numero or 0):
        raise ConflictError(
            "GOV_HANDOVER_POLICY_STATE",
            "Solo la última versión se puede versionar",
        )

    nueva = GovernmentHandoverPolicy(
        company_id=ctx.company_id,
        codigo=politica.codigo,
        numero_version=politica.numero_version + 1,
        nombre=politica.nombre,
        descripcion=politica.descripcion,
        fundamento=politica.fundamento,
        act_id=politica.act_id,
        vigente_desde=politica.vigente_desde,
        vigente_hasta=politica.vigente_hasta,
        estado="BORRADOR",
        numeracion_patron=politica.numeracion_patron,
        testigos_en_entrega=politica.testigos_en_entrega,
        cargo_maxima_autoridad_codigo=politica.cargo_maxima_autoridad_codigo,
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
            "GOV_HANDOVER_POLICY_CONFLICT",
            "Otra política se registró al mismo tiempo; vuelva a intentarlo",
        ) from None

    vinculos = db.scalars(
        select(GovernmentHandoverPolicyBinding).where(
            GovernmentHandoverPolicyBinding.policy_id == str(politica.id),
            GovernmentHandoverPolicyBinding.company_id == ctx.company_id,
        )
    ).all()
    for v in vinculos:
        db.add(
            GovernmentHandoverPolicyBinding(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                supuesto=v.supuesto,
                alcance=v.alcance,
                unit_id=v.unit_id,
                created_by=ctx.user_id,
            )
        )

    requisitos = db.scalars(
        select(GovernmentHandoverPolicyRequirement).where(
            GovernmentHandoverPolicyRequirement.policy_id == str(politica.id),
            GovernmentHandoverPolicyRequirement.company_id == ctx.company_id,
        )
    ).all()
    for r in requisitos:
        db.add(
            GovernmentHandoverPolicyRequirement(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                codigo=r.codigo,
                titulo=r.titulo,
                evidencia=r.evidencia,
                obligatorio=r.obligatorio,
                ambito=r.ambito,
                supuesto=r.supuesto,
                document_type_id=r.document_type_id,
                fuente=r.fuente,
                created_by=ctx.user_id,
            )
        )

    plazos = db.scalars(
        select(GovernmentHandoverPolicyDeadline).where(
            GovernmentHandoverPolicyDeadline.policy_id == str(politica.id),
            GovernmentHandoverPolicyDeadline.company_id == ctx.company_id,
        )
    ).all()
    for p in plazos:
        db.add(
            GovernmentHandoverPolicyDeadline(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                hito=p.hito,
                valor=p.valor,
                unidad=p.unidad,
                fuente=p.fuente,
                created_by=ctx.user_id,
            )
        )

    db.flush()
    _historia(db, ctx, nueva, EVENTOS["NUEVA_VERSION"])
    _auditar(
        db,
        ctx,
        "GOV_HANDOVER_POLICY_VERSIONED",
        str(nueva.id),
        {
            "codigo": nueva.codigo,
            "numero_version": nueva.numero_version,
            "sustituye": politica.numero_version,
        },
    )
    db.flush()
    return detalle(db, ctx, str(nueva.id))
