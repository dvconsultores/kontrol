from __future__ import annotations

from collections.abc import Callable
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
    AREAS_COMISION,
    MATERIAS_COMPETENCIA,
    GovernmentCommissionPolicy,
    GovernmentCommissionPolicyDocument,
    GovernmentCommissionPolicyHistory,
    GovernmentCommissionPolicyRequirement,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentProcurementCommittee,
    GovernmentUnit,
)
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_comision_regla import (
    ETIQUETAS_AREA,
    ETIQUETAS_ETAPA,
    ETIQUETAS_MAYORIA,
    PISO_LCP_ART14,
    instantanea,
)
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual

ENTIDAD = "GovernmentCommissionPolicy"

EVENTOS = {
    "CREADA": "CREADA",
    "EDITADA": "EDITADA",
    "ACTIVADA": "ACTIVADA",
    "CERRADA": "CERRADA",
    "SUSTITUIDA": "SUSTITUIDA",
    "NUEVA_VERSION": "NUEVA_VERSION",
}

ESTADOS = {
    "BORRADOR": "Borrador",
    "VIGENTE": "Vigente",
    "CERRADA": "Cerrada",
}

TIPOS_COMISION = {
    "PERMANENTE": "Permanente",
    "TEMPORAL": "Temporal",
    "CUALQUIERA": "Cualquiera",
}

_BASES_NORMATIVAS = {
    "LCP_ART14": "Ley de Contrataciones Públicas, art. 14 (piso legal)",
    "NINGUNA": "Sin piso legal: solo la política del ente",
}

_BASES_DECISION = {
    "MIEMBROS_CON_VOTO": "Sobre todos los miembros con voto",
    "ASISTENTES_CON_VOTO": "Sobre los asistentes con voto",
}

_FUNCIONES = {
    "MIEMBRO": "Miembro",
    "SECRETARIO": "Secretario",
}

_CONDICIONES = {
    "PRINCIPAL": "Principal",
    "SUPLENTE": "Suplente",
    "CUALQUIERA": "Principal o suplente",
}

_TIPOS_REQUISITO = {
    "AREA": "Área de la comisión",
    "CARGO": "Ejerce un cargo",
    "UNIDAD": "Ejerce un cargo de una unidad",
    "COMPETENCIA": "Tiene una competencia",
    "FUNCIONARIO": "Funcionario designado",
}

_ETAPAS = {
    "CONSTITUCION": "Constitución de la comisión",
    "APERTURA": "Apertura de ofertas",
    "RECOMENDACION": "Recomendación",
}

_MEDIOS = {
    "GACETA": "Gaceta",
    "PERSONAL": "Notificación personal",
    "PRENSA": "Prensa",
}

_TIPOS_MAYORIA = {codigo: etiqueta for codigo, etiqueta in ETIQUETAS_MAYORIA.items()}


def _para_escribir(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
) -> GovernmentCommissionPolicy:
    if version is None:
        raise KontrolError(
            code="GOV_COMMISSION_POLICY_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    politica = db.scalar(
        select(GovernmentCommissionPolicy)
        .where(
            GovernmentCommissionPolicy.id == id,
            GovernmentCommissionPolicy.company_id == ctx.company_id,
        )
        .with_for_update()
    )
    if not politica:
        raise NotFoundError(
            "GOV_COMMISSION_POLICY_NOT_FOUND",
            "La política no existe en este ente",
        )
    if politica.version != version:
        raise ConflictError(
            "GOV_COMMISSION_POLICY_STALE",
            "La política cambió desde que la abrió; recárguela",
            details={"version_actual": politica.version},
        )
    return politica


def _exigir_borrador(politica: GovernmentCommissionPolicy) -> None:
    if politica.estado != "BORRADOR":
        raise ConflictError(
            "GOV_COMMISSION_POLICY_NOT_DRAFT",
            "Solo una política en borrador se puede editar; cree una nueva versión",
        )


def _historia(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentCommissionPolicy,
    evento: str,
) -> None:
    db.add(
        GovernmentCommissionPolicyHistory(
            policy_id=str(politica.id),
            company_id=ctx.company_id,
            evento=evento,
            version=politica.version,
            instantanea=instantanea(db, politica),
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
        "base_normativa",
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


def _cat_lista(valores: dict[str, str]) -> list[dict[str, str]]:
    return [{"codigo": k, "etiqueta": v} for k, v in valores.items()]


def catalogo() -> dict[str, Any]:
    return {
        "estados": _cat_lista(ESTADOS),
        "tipos_comision": _cat_lista(TIPOS_COMISION),
        "bases_normativas": _cat_lista(_BASES_NORMATIVAS),
        "tipos_mayoria": _cat_lista(_TIPOS_MAYORIA),
        "bases_decision": _cat_lista(_BASES_DECISION),
        "funciones": _cat_lista(_FUNCIONES),
        "condiciones": _cat_lista(_CONDICIONES),
        "tipos_requisito": _cat_lista(_TIPOS_REQUISITO),
        "areas": _cat_lista(ETIQUETAS_AREA),
        "etapas": _cat_lista(ETIQUETAS_ETAPA),
        "medios": _cat_lista(_MEDIOS),
        "acciones_competencia": [
            {"codigo": codigo, "etiqueta": codigo.capitalize().replace("_", " ")}
            for codigo in ACCIONES_COMPETENCIA
        ],
        "materias_competencia": [
            {"codigo": codigo, "etiqueta": codigo.capitalize().replace("_", " ")}
            for codigo in MATERIAS_COMPETENCIA
        ],
        "piso_lcp": PISO_LCP_ART14,
    }


def opciones(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    cargos = db.scalars(
        select(GovernmentPosition)
        .where(GovernmentPosition.company_id == ctx.company_id)
        .order_by(GovernmentPosition.code)
    ).all()
    unidades = db.scalars(
        select(GovernmentUnit)
        .where(GovernmentUnit.company_id == ctx.company_id)
        .order_by(GovernmentUnit.code)
    ).all()
    funcionarios = db.scalars(
        select(GovernmentOfficial)
        .where(
            GovernmentOfficial.company_id == ctx.company_id,
            GovernmentOfficial.estado == "ACTIVO",
        )
        .order_by(GovernmentOfficial.codigo)
    ).all()
    tipos_documentales = db.scalars(
        select(DocumentType)
        .where(DocumentType.company_id == ctx.company_id, DocumentType.status == "ACTIVE")
        .order_by(DocumentType.code)
    ).all()

    def _opciones(items: Any, _etiqueta: Callable[[Any], str]) -> list[dict[str, str]]:
        return [
            {"id": str(item.id), "etiqueta": _etiqueta(item)}
            for item in items
        ]

    return {
        "cargos": sorted(
            _opciones(cargos, lambda c: f"{c.code} · {c.name}"),
            key=lambda x: x["etiqueta"],
        ),
        "unidades": sorted(
            _opciones(unidades, lambda u: f"{u.code} · {u.name}"),
            key=lambda x: x["etiqueta"],
        ),
        "funcionarios": sorted(
            _opciones(funcionarios, lambda f: f"{f.codigo} · {f.nombre}"),
            key=lambda x: x["etiqueta"],
        ),
        "tipos_documentales": sorted(
            _opciones(tipos_documentales, lambda t: f"{t.code} · {t.name}"),
            key=lambda x: x["etiqueta"],
        ),
    }


def _contar_comisiones(db: Session, ctx: CompanyContext, policy_id: str) -> int:
    total = db.scalar(
        select(func.count(GovernmentProcurementCommittee.id)).where(
            GovernmentProcurementCommittee.company_id == ctx.company_id,
            GovernmentProcurementCommittee.policy_id == policy_id,
        )
    )
    return int(total or 0)


def _resumen(db: Session, ctx: CompanyContext, politica: GovernmentCommissionPolicy) -> dict[str, Any]:
    return {
        "id": str(politica.id),
        "codigo": politica.codigo,
        "numero_version": politica.numero_version,
        "nombre": politica.nombre,
        "tipo_comision": politica.tipo_comision,
        "base_normativa": politica.base_normativa,
        "estado": politica.estado,
        "vigente_desde": politica.vigente_desde,
        "vigente_hasta": politica.vigente_hasta,
        "aplica_apertura": politica.aplica_apertura,
        "aplica_recomendacion": politica.aplica_recomendacion,
        "version": politica.version,
        "comisiones": _contar_comisiones(db, ctx, str(politica.id)),
    }


def listar(
    db: Session,
    ctx: CompanyContext,
    estado: str | None = None,
    q: str | None = None,
) -> dict[str, Any]:
    condicion = [GovernmentCommissionPolicy.company_id == ctx.company_id]
    if estado:
        condicion.append(GovernmentCommissionPolicy.estado == estado)
    if q:
        like = f"%{q}%"
        condicion.append(
            or_(
                GovernmentCommissionPolicy.codigo.ilike(like),
                GovernmentCommissionPolicy.nombre.ilike(like),
            )
        )
    politicas = db.scalars(
        select(GovernmentCommissionPolicy)
        .where(*condicion)
        .order_by(
            GovernmentCommissionPolicy.codigo.asc(),
            GovernmentCommissionPolicy.numero_version.desc(),
        )
    ).all()
    items = [_resumen(db, ctx, p) for p in politicas]
    return {"items": items, "total": len(items)}


def _detalle_base(db: Session, ctx: CompanyContext, politica: GovernmentCommissionPolicy) -> dict[str, Any]:
    regla = instantanea(db, politica)
    resumen = _resumen(db, ctx, politica)
    detalle: dict[str, Any] = dict(resumen)
    detalle.update(
        {
            "descripcion": politica.descripcion,
            "fundamento": politica.fundamento,
            "min_principales": politica.min_principales,
            "max_principales": politica.max_principales,
            "exige_impar": politica.exige_impar,
            "suplente_por_principal": politica.suplente_por_principal,
            "exige_secretario": politica.exige_secretario,
            "exige_suplente_secretario": politica.exige_suplente_secretario,
            "exige_presidente": politica.exige_presidente,
            "quorum": regla["quorum"],
            "decision": regla["decision"],
            "presidente_vota": politica.presidente_vota,
            "presidente_dirimente": politica.presidente_dirimente,
            "acto_requerido": politica.acto_requerido,
            "acto_medio": politica.acto_medio,
            "requisitos": regla["requisitos"],
            "documentos": regla["documentos"],
            "regla": regla,
            "activada_en": politica.activada_en,
            "cerrada_en": politica.cerrada_en,
            "motivo_cierre": politica.motivo_cierre,
        }
    )
    return detalle


def _historia_salida(db: Session, ctx: CompanyContext, politica: GovernmentCommissionPolicy) -> list[dict[str, Any]]:
    eventos = db.scalars(
        select(GovernmentCommissionPolicyHistory)
        .where(
            GovernmentCommissionPolicyHistory.policy_id == str(politica.id),
            GovernmentCommissionPolicyHistory.company_id == ctx.company_id,
        )
        .order_by(GovernmentCommissionPolicyHistory.created_at.asc())
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


def _versiones_salida(db: Session, ctx: CompanyContext, politica: GovernmentCommissionPolicy) -> list[dict[str, Any]]:
    versiones = db.scalars(
        select(GovernmentCommissionPolicy)
        .where(GovernmentCommissionPolicy.company_id == ctx.company_id)
        .where(GovernmentCommissionPolicy.codigo == politica.codigo)
        .order_by(GovernmentCommissionPolicy.numero_version.desc())
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
        select(GovernmentCommissionPolicy.id).where(
            GovernmentCommissionPolicy.company_id == ctx.company_id,
            GovernmentCommissionPolicy.codigo == codigo,
            GovernmentCommissionPolicy.estado == "BORRADOR",
        )
    )
    return borrador is not None


def detalle(db: Session, ctx: CompanyContext, id: str) -> dict[str, Any]:
    politica = db.scalar(
        select(GovernmentCommissionPolicy).where(
            GovernmentCommissionPolicy.id == id,
            GovernmentCommissionPolicy.company_id == ctx.company_id,
        )
    )
    if not politica:
        raise NotFoundError(
            "GOV_COMMISSION_POLICY_NOT_FOUND",
            "La política no existe en este ente",
        )

    max_numero = db.scalar(
        select(func.max(GovernmentCommissionPolicy.numero_version)).where(
            GovernmentCommissionPolicy.company_id == ctx.company_id,
            GovernmentCommissionPolicy.codigo == politica.codigo,
        )
    )
    es_ultima = politica.numero_version == (max_numero or 0)
    otro_borrador = _existe_borrador_codigo(db, ctx, politica.codigo) if politica.estado != "BORRADOR" else False

    detalle = _detalle_base(db, ctx, politica)
    detalle["historia"] = _historia_salida(db, ctx, politica)
    detalle["versiones"] = _versiones_salida(db, ctx, politica)
    detalle["puede_editar"] = politica.estado == "BORRADOR"
    detalle["puede_activar"] = politica.estado == "BORRADOR"
    detalle["puede_cerrar"] = politica.estado != "CERRADA"
    detalle["puede_versionar"] = (
        politica.estado != "BORRADOR" and es_ultima and not otro_borrador
    )
    return detalle


def _invalida(field_errors: dict[str, list[str]], motivos: list[str] | None = None) -> KontrolError:
    return KontrolError(
        code="GOV_COMMISSION_POLICY_INVALID",
        message="La política no se puede activar" if motivos is not None else "La política no es válida",
        status_code=422,
        field_errors=field_errors,
        details={"motivos": motivos} if motivos is not None else None,
    )


def _normalizar_mayoria(valor: Any) -> tuple[str, int | None, int | None, int | None]:
    tipo = valor.tipo
    cantidad = valor.cantidad
    numerador = valor.numerador
    denominador = valor.denominador
    if tipo != "ABSOLUTE_COUNT":
        cantidad = None
    if tipo != "QUALIFIED_MAJORITY":
        numerador = None
        denominador = None
    return tipo, cantidad, numerador, denominador


def _validar_mayoria(valor: Any, nombre: str, field_errors: dict[str, list[str]]) -> None:
    if valor.tipo == "ABSOLUTE_COUNT" and (valor.cantidad is None or valor.cantidad < 1):
        field_errors.setdefault(nombre, []).append("La cantidad debe ser mayor o igual a 1")
    if valor.tipo == "QUALIFIED_MAJORITY":
        if valor.numerador is None or valor.denominador is None:
            field_errors.setdefault(nombre, []).append("Se requiere numerador y denominador")
        else:
            if not (1 <= valor.numerador <= valor.denominador):
                field_errors.setdefault(nombre, []).append("El numerador debe estar entre 1 y el denominador")
            if not (2 * valor.numerador > valor.denominador):
                field_errors.setdefault(nombre, []).append("La fracción debe ser mayor a la mitad")


def _validar_requisito(
    db: Session,
    ctx: CompanyContext,
    requisito: Any,
    i: int,
    field_errors: dict[str, list[str]],
) -> None:
    errores: list[str] = []
    tipo = requisito.tipo

    if tipo == "AREA":
        if not requisito.area:
            errores.append("Debe indicar el área")
        elif requisito.area not in AREAS_COMISION:
            errores.append("Área inválida")
    elif tipo == "CARGO":
        if not requisito.position_id:
            errores.append("Debe indicar el cargo")
        else:
            cargo = db.scalar(
                select(GovernmentPosition.id).where(
                    GovernmentPosition.id == requisito.position_id,
                    GovernmentPosition.company_id == ctx.company_id,
                )
            )
            if cargo is None:
                errores.append("El cargo no existe en este ente")
    elif tipo == "UNIDAD":
        if not requisito.unit_id:
            errores.append("Debe indicar la unidad")
        else:
            unidad = db.scalar(
                select(GovernmentUnit.id).where(
                    GovernmentUnit.id == requisito.unit_id,
                    GovernmentUnit.company_id == ctx.company_id,
                )
            )
            if unidad is None:
                errores.append("La unidad no existe en este ente")
    elif tipo == "COMPETENCIA":
        if not requisito.competencia_accion or not requisito.competencia_materia:
            errores.append("Debe indicar acción y materia")
        else:
            if requisito.competencia_accion not in ACCIONES_COMPETENCIA:
                errores.append("Acción de competencia inválida")
            if requisito.competencia_materia not in MATERIAS_COMPETENCIA:
                errores.append("Materia de competencia inválida")
    elif tipo == "FUNCIONARIO":
        if not requisito.official_id:
            errores.append("Debe indicar el funcionario")
        else:
            funcionario = db.scalar(
                select(GovernmentOfficial.id).where(
                    GovernmentOfficial.id == requisito.official_id,
                    GovernmentOfficial.company_id == ctx.company_id,
                    GovernmentOfficial.estado == "ACTIVO",
                )
            )
            if funcionario is None:
                errores.append("El funcionario no existe o no está activo en este ente")

    if requisito.maximo is not None and requisito.maximo < requisito.minimo:
        errores.append("El máximo debe ser mayor o igual al mínimo")

    if errores:
        field_errors.setdefault("requisitos", []).append(f"Requisito {i + 1}: {'; '.join(errores)}")


def _validar_documentos(
    db: Session,
    ctx: CompanyContext,
    documentos: list[Any],
    field_errors: dict[str, list[str]],
) -> None:
    vistos: set[tuple[str, str]] = set()
    for i, documento in enumerate(documentos):
        errores: list[str] = []
        tipo = db.scalar(
            select(DocumentType.id).where(
                DocumentType.id == documento.document_type_id,
                DocumentType.company_id == ctx.company_id,
                DocumentType.status == "ACTIVE",
            )
        )
        if tipo is None:
            errores.append("El tipo documental no existe o no está activo en este ente")
        clave = (documento.document_type_id, documento.etapa)
        if clave in vistos:
            errores.append("Tipo documental repetido para la misma etapa")
        vistos.add(clave)
        if errores:
            field_errors.setdefault("documentos", []).append(f"Documento {i + 1}: {'; '.join(errores)}")


def _validar(db: Session, ctx: CompanyContext, datos: Any) -> dict[str, list[str]]:
    field_errors: dict[str, list[str]] = {}
    if datos.vigente_hasta is not None and datos.vigente_hasta < datos.vigente_desde:
        field_errors.setdefault("vigente_hasta", [])
        field_errors["vigente_hasta"].append("La fecha de fin no puede ser anterior a la de inicio")
    if datos.max_principales is not None and datos.max_principales < datos.min_principales:
        field_errors.setdefault("max_principales", [])
        field_errors["max_principales"].append("El máximo no puede ser menor al mínimo")
    if not datos.aplica_apertura and not datos.aplica_recomendacion:
        field_errors.setdefault("aplica_apertura", [])
        field_errors["aplica_apertura"].append(
            "La política debe aplicar al menos a la apertura o a la recomendación"
        )
    _validar_mayoria(datos.quorum, "quorum", field_errors)
    _validar_mayoria(datos.decision, "decision", field_errors)
    if datos.presidente_dirimente and not datos.exige_presidente:
        field_errors.setdefault("presidente_dirimente", [])
        field_errors["presidente_dirimente"].append(
            "El presidente dirimente requiere exigir presidente"
        )
    for i, requisito in enumerate(datos.requisitos):
        _validar_requisito(db, ctx, requisito, i, field_errors)
    _validar_documentos(db, ctx, datos.documentos, field_errors)
    return field_errors


def _aplicar_campos(
    politica: GovernmentCommissionPolicy,
    datos: Any,
) -> None:
    politica.nombre = datos.nombre
    politica.descripcion = datos.descripcion
    politica.tipo_comision = datos.tipo_comision
    politica.aplica_apertura = datos.aplica_apertura
    politica.aplica_recomendacion = datos.aplica_recomendacion
    politica.base_normativa = datos.base_normativa
    politica.fundamento = datos.fundamento
    politica.vigente_desde = datos.vigente_desde
    politica.vigente_hasta = datos.vigente_hasta
    politica.min_principales = datos.min_principales
    politica.max_principales = datos.max_principales
    politica.exige_impar = datos.exige_impar
    politica.suplente_por_principal = datos.suplente_por_principal
    politica.exige_secretario = datos.exige_secretario
    politica.exige_suplente_secretario = datos.exige_suplente_secretario
    politica.exige_presidente = datos.exige_presidente
    (
        politica.quorum_tipo,
        politica.quorum_cantidad,
        politica.quorum_numerador,
        politica.quorum_denominador,
    ) = _normalizar_mayoria(datos.quorum)
    (
        politica.decision_tipo,
        politica.decision_cantidad,
        politica.decision_numerador,
        politica.decision_denominador,
    ) = _normalizar_mayoria(datos.decision)
    politica.decision_base = datos.decision.base
    politica.presidente_vota = datos.presidente_vota
    politica.presidente_dirimente = datos.presidente_dirimente
    politica.acto_requerido = datos.acto_requerido
    politica.acto_medio = datos.acto_medio


def _crear_requisitos(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentCommissionPolicy,
    requisitos: list[Any],
) -> None:
    for i, requisito in enumerate(requisitos, start=1):
        db.add(
            GovernmentCommissionPolicyRequirement(
                policy_id=str(politica.id),
                company_id=ctx.company_id,
                orden=i,
                etiqueta=requisito.etiqueta,
                funcion=requisito.funcion,
                condicion=requisito.condicion,
                tipo=requisito.tipo,
                area=requisito.area if requisito.tipo == "AREA" else None,
                position_id=requisito.position_id if requisito.tipo == "CARGO" else None,
                unit_id=requisito.unit_id if requisito.tipo == "UNIDAD" else None,
                competencia_accion=requisito.competencia_accion if requisito.tipo == "COMPETENCIA" else None,
                competencia_materia=requisito.competencia_materia if requisito.tipo == "COMPETENCIA" else None,
                official_id=requisito.official_id if requisito.tipo == "FUNCIONARIO" else None,
                minimo=requisito.minimo,
                maximo=requisito.maximo,
                created_by=ctx.user_id,
            )
        )


def _crear_documentos(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentCommissionPolicy,
    documentos: list[Any],
) -> None:
    for documento in documentos:
        db.add(
            GovernmentCommissionPolicyDocument(
                policy_id=str(politica.id),
                company_id=ctx.company_id,
                document_type_id=documento.document_type_id,
                etapa=documento.etapa,
                obligatorio=documento.obligatorio,
                condicion=documento.condicion,
                created_by=ctx.user_id,
            )
        )


def _borrar_detalles(db: Session, ctx: CompanyContext, politica: GovernmentCommissionPolicy) -> None:
    db.query(GovernmentCommissionPolicyRequirement).filter(
        GovernmentCommissionPolicyRequirement.policy_id == str(politica.id)
    ).delete(synchronize_session=False)
    db.query(GovernmentCommissionPolicyDocument).filter(
        GovernmentCommissionPolicyDocument.policy_id == str(politica.id)
    ).delete(synchronize_session=False)


def crear(db: Session, ctx: CompanyContext, datos: Any) -> dict[str, Any]:
    field_errors = _validar(db, ctx, datos)
    if field_errors:
        raise _invalida(field_errors)

    existente = db.scalar(
        select(GovernmentCommissionPolicy.id).where(
            GovernmentCommissionPolicy.company_id == ctx.company_id,
            GovernmentCommissionPolicy.codigo == datos.codigo,
        )
    )
    if existente is not None:
        raise ConflictError(
            "GOV_COMMISSION_POLICY_CODE_TAKEN",
            "Ya existe una política con ese código; cree una nueva versión",
        )

    politica = GovernmentCommissionPolicy(
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
            "GOV_COMMISSION_POLICY_CONFLICT",
            "Otra política se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    _crear_requisitos(db, ctx, politica, datos.requisitos)
    _crear_documentos(db, ctx, politica, datos.documentos)
    db.flush()
    _historia(db, ctx, politica, EVENTOS["CREADA"])
    _auditar(
        db,
        ctx,
        "GOV_COMMISSION_POLICY_CREATED",
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
            code="GOV_COMMISSION_POLICY_INVALID",
            message="La política no es válida",
            status_code=422,
            field_errors={"codigo": ["El código no se puede cambiar"]},
        )

    field_errors = _validar(db, ctx, datos)
    if field_errors:
        raise _invalida(field_errors)

    _aplicar_campos(politica, datos)
    politica.version += 1
    _borrar_detalles(db, ctx, politica)
    _crear_requisitos(db, ctx, politica, datos.requisitos)
    _crear_documentos(db, ctx, politica, datos.documentos)
    db.flush()
    _historia(db, ctx, politica, EVENTOS["EDITADA"])
    _auditar(
        db,
        ctx,
        "GOV_COMMISSION_POLICY_UPDATED",
        str(politica.id),
        {
            "codigo": politica.codigo,
            "numero_version": politica.numero_version,
            "version": politica.version,
        },
    )
    db.flush()
    return detalle(db, ctx, str(politica.id))


def _validar_activacion(
    politica: GovernmentCommissionPolicy,
    max_principales: int | None,
    requisitos: list[dict[str, Any]],
) -> tuple[dict[str, list[str]], list[str]]:
    field_errors: dict[str, list[str]] = {}
    motivos: list[str] = []

    if not politica.fundamento or len(politica.fundamento.strip()) < 10:
        field_errors.setdefault("fundamento", [])
        field_errors["fundamento"].append("El fundamento es obligatorio y debe tener al menos 10 caracteres")
        motivos.append("El fundamento es obligatorio y debe tener al menos 10 caracteres")

    if politica.vigente_hasta is not None and politica.vigente_hasta < hoy_de_negocio():
        field_errors.setdefault("vigente_hasta", [])
        field_errors["vigente_hasta"].append("La vigencia ya terminó")
        motivos.append("La vigencia ya terminó")

    if politica.base_normativa == "LCP_ART14":
        exigencias = [
            (
                "exige_impar",
                politica.exige_impar,
                "La base LCP art. 14 exige que el número de miembros sea impar; el ente puede endurecer el piso legal, no rebajarlo",
            ),
            (
                "suplente_por_principal",
                politica.suplente_por_principal,
                "La base LCP art. 14 exige suplentes por cada principal; el ente puede endurecer el piso legal, no rebajarlo",
            ),
            (
                "exige_secretario",
                politica.exige_secretario,
                "La base LCP art. 14 exige secretario; el ente puede endurecer el piso legal, no rebajarlo",
            ),
            (
                "exige_suplente_secretario",
                politica.exige_suplente_secretario,
                "La base LCP art. 14 exige suplente del secretario; el ente puede endurecer el piso legal, no rebajarlo",
            ),
        ]
        for campo, valor, mensaje in exigencias:
            if not valor:
                field_errors.setdefault(campo, [])
                field_errors[campo].append(mensaje)
                motivos.append(mensaje)

        if not politica.acto_requerido:
            mensaje = "La base LCP art. 14 exige acto administrativo; el ente puede endurecer el piso legal, no rebajarlo"
            field_errors.setdefault("acto_requerido", [])
            field_errors["acto_requerido"].append(mensaje)
            motivos.append(mensaje)

        if politica.acto_medio not in (None, "GACETA"):
            mensaje = "La base LCP art. 14 exige gaceta o no definir medio; el ente puede endurecer el piso legal, no rebajarlo"
            field_errors.setdefault("acto_medio", [])
            field_errors["acto_medio"].append(mensaje)
            motivos.append(mensaje)

    if max_principales is not None:
        if (
            politica.quorum_tipo == "ABSOLUTE_COUNT"
            and politica.quorum_cantidad is not None
            and politica.quorum_cantidad > max_principales
        ):
            mensaje = "El quórum exige más miembros que el máximo permitido"
            field_errors.setdefault("quorum", [])
            field_errors["quorum"].append(mensaje)
            motivos.append(mensaje)
        if (
            politica.decision_tipo == "ABSOLUTE_COUNT"
            and politica.decision_cantidad is not None
            and politica.decision_cantidad > max_principales
        ):
            mensaje = "La mayoría exige más miembros que el máximo permitido"
            field_errors.setdefault("decision", [])
            field_errors["decision"].append(mensaje)
            motivos.append(mensaje)

        total_minimos_principales = sum(
            r.get("minimo", 0)
            for r in requisitos
            if r.get("funcion") == "MIEMBRO" and r.get("condicion") == "PRINCIPAL"
        )
        if total_minimos_principales > max_principales:
            mensaje = "Los requisitos exigen más principales que el máximo permitido"
            field_errors.setdefault("requisitos", [])
            field_errors["requisitos"].append(mensaje)
            motivos.append(mensaje)

    return field_errors, motivos


def activar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
) -> dict[str, Any]:
    politica = _para_escribir(db, ctx, id, version)
    _exigir_borrador(politica)

    regla = instantanea(db, politica)
    field_errors, motivos = _validar_activacion(
        politica,
        politica.max_principales,
        regla["requisitos"],
    )
    if field_errors:
        raise _invalida(field_errors, motivos)

    vigente_anterior = db.scalar(
        select(GovernmentCommissionPolicy)
        .where(
            GovernmentCommissionPolicy.company_id == ctx.company_id,
            GovernmentCommissionPolicy.codigo == politica.codigo,
            GovernmentCommissionPolicy.estado == "VIGENTE",
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
            "GOV_COMMISSION_POLICY_CLOSED",
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
            "GOV_COMMISSION_POLICY_CONFLICT",
            "Otra política se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    _historia(db, ctx, politica, EVENTOS["ACTIVADA"])
    _auditar(
        db,
        ctx,
        "GOV_COMMISSION_POLICY_ACTIVATED",
        str(politica.id),
        {
            "codigo": politica.codigo,
            "numero_version": politica.numero_version,
            "estado": politica.estado,
            "vigente_desde": politica.vigente_desde,
            "vigente_hasta": politica.vigente_hasta,
            "base_normativa": politica.base_normativa,
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
    if politica.estado == "CERRADA":
        raise ConflictError(
            "GOV_COMMISSION_POLICY_CLOSED",
            "La política ya está cerrada",
        )
    if not datos.motivo or not datos.motivo.strip():
        raise KontrolError(
            code="GOV_COMMISSION_POLICY_INVALID",
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
        "GOV_COMMISSION_POLICY_CLOSED",
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
            "GOV_COMMISSION_POLICY_NOT_VERSIONABLE",
            "Una política en borrador se edita, no se versiona",
        )
    max_numero = db.scalar(
        select(func.max(GovernmentCommissionPolicy.numero_version)).where(
            GovernmentCommissionPolicy.company_id == ctx.company_id,
            GovernmentCommissionPolicy.codigo == politica.codigo,
        )
    )
    if politica.numero_version != (max_numero or 0):
        raise ConflictError(
            "GOV_COMMISSION_POLICY_NOT_VERSIONABLE",
            "Solo la última versión se puede versionar",
        )
    borrador_existente = db.scalar(
        select(GovernmentCommissionPolicy.id).where(
            GovernmentCommissionPolicy.company_id == ctx.company_id,
            GovernmentCommissionPolicy.codigo == politica.codigo,
            GovernmentCommissionPolicy.estado == "BORRADOR",
        )
    )
    if borrador_existente is not None:
        raise ConflictError(
            "GOV_COMMISSION_POLICY_DRAFT_EXISTS",
            "Ya hay una versión en borrador de esta política",
        )

    nueva = GovernmentCommissionPolicy(
        company_id=ctx.company_id,
        codigo=politica.codigo,
        numero_version=politica.numero_version + 1,
        nombre=politica.nombre,
        descripcion=politica.descripcion,
        tipo_comision=politica.tipo_comision,
        aplica_apertura=politica.aplica_apertura,
        aplica_recomendacion=politica.aplica_recomendacion,
        base_normativa=politica.base_normativa,
        fundamento=politica.fundamento,
        act_id=politica.act_id,
        vigente_desde=politica.vigente_desde,
        vigente_hasta=politica.vigente_hasta,
        estado="BORRADOR",
        min_principales=politica.min_principales,
        max_principales=politica.max_principales,
        exige_impar=politica.exige_impar,
        suplente_por_principal=politica.suplente_por_principal,
        exige_secretario=politica.exige_secretario,
        exige_suplente_secretario=politica.exige_suplente_secretario,
        exige_presidente=politica.exige_presidente,
        quorum_tipo=politica.quorum_tipo,
        quorum_cantidad=politica.quorum_cantidad,
        quorum_numerador=politica.quorum_numerador,
        quorum_denominador=politica.quorum_denominador,
        decision_tipo=politica.decision_tipo,
        decision_cantidad=politica.decision_cantidad,
        decision_numerador=politica.decision_numerador,
        decision_denominador=politica.decision_denominador,
        decision_base=politica.decision_base,
        presidente_vota=politica.presidente_vota,
        presidente_dirimente=politica.presidente_dirimente,
        acto_requerido=politica.acto_requerido,
        acto_medio=politica.acto_medio,
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
            "GOV_COMMISSION_POLICY_CONFLICT",
            "Otra política se registró al mismo tiempo; vuelva a intentarlo",
        ) from None

    requisitos = db.scalars(
        select(GovernmentCommissionPolicyRequirement).where(
            GovernmentCommissionPolicyRequirement.policy_id == str(politica.id),
            GovernmentCommissionPolicyRequirement.company_id == ctx.company_id,
        ).order_by(GovernmentCommissionPolicyRequirement.orden)
    ).all()
    for requisito in requisitos:
        db.add(
            GovernmentCommissionPolicyRequirement(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                orden=requisito.orden,
                etiqueta=requisito.etiqueta,
                funcion=requisito.funcion,
                condicion=requisito.condicion,
                tipo=requisito.tipo,
                area=requisito.area,
                position_id=requisito.position_id,
                unit_id=requisito.unit_id,
                competencia_accion=requisito.competencia_accion,
                competencia_materia=requisito.competencia_materia,
                official_id=requisito.official_id,
                minimo=requisito.minimo,
                maximo=requisito.maximo,
                created_by=ctx.user_id,
            )
        )

    documentos = db.scalars(
        select(GovernmentCommissionPolicyDocument).where(
            GovernmentCommissionPolicyDocument.policy_id == str(politica.id),
            GovernmentCommissionPolicyDocument.company_id == ctx.company_id,
        )
    ).all()
    for documento in documentos:
        db.add(
            GovernmentCommissionPolicyDocument(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                document_type_id=documento.document_type_id,
                etapa=documento.etapa,
                obligatorio=documento.obligatorio,
                condicion=documento.condicion,
                created_by=ctx.user_id,
            )
        )

    db.flush()
    _historia(db, ctx, nueva, EVENTOS["NUEVA_VERSION"])
    _auditar(
        db,
        ctx,
        "GOV_COMMISSION_POLICY_VERSIONED",
        str(nueva.id),
        {
            "codigo": nueva.codigo,
            "numero_version": nueva.numero_version,
            "sustituye": politica.numero_version,
        },
    )
    db.flush()
    return detalle(db, ctx, str(nueva.id))


def vigentes_para(
    db: Session,
    ctx: CompanyContext,
    tipo_comision: str,
    fecha: date,
) -> list[GovernmentCommissionPolicy]:
    condicion = [
        GovernmentCommissionPolicy.company_id == ctx.company_id,
        GovernmentCommissionPolicy.estado == "VIGENTE",
        GovernmentCommissionPolicy.vigente_desde <= fecha,
        or_(
            GovernmentCommissionPolicy.vigente_hasta.is_(None),
            GovernmentCommissionPolicy.vigente_hasta >= fecha,
        ),
    ]
    if tipo_comision != "CUALQUIERA":
        condicion.append(
            or_(
                GovernmentCommissionPolicy.tipo_comision == tipo_comision,
                GovernmentCommissionPolicy.tipo_comision == "CUALQUIERA",
            )
        )
    politicas = db.scalars(
        select(GovernmentCommissionPolicy)
        .where(*condicion)
        .order_by(GovernmentCommissionPolicy.codigo)
    ).all()
    if tipo_comision == "CUALQUIERA":
        politicas = [p for p in politicas if p.tipo_comision == "CUALQUIERA"]
    else:
        politicas = [
            p
            for p in politicas
            if p.tipo_comision in (tipo_comision, "CUALQUIERA")
        ]
    return politicas


def politica_aplicable(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    tipo_comision: str,
    fecha: date,
) -> GovernmentCommissionPolicy:
    politica = db.scalar(
        select(GovernmentCommissionPolicy).where(
            GovernmentCommissionPolicy.id == policy_id,
            GovernmentCommissionPolicy.company_id == ctx.company_id,
        )
    )
    if politica is None:
        raise NotFoundError(
            "GOV_COMMISSION_POLICY_NOT_FOUND",
            "La política no existe en este ente",
        )
    vigentes = vigentes_para(db, ctx, tipo_comision, fecha)
    if politica not in vigentes:
        raise KontrolError(
            code="GOV_COMMITTEE_POLICY_NOT_APPLICABLE",
            message="La política no es aplicable",
            status_code=422,
            field_errors={
                "politica_id": ["La política no está vigente para ese tipo de comisión en esa fecha"]
            },
        )
    return politica
