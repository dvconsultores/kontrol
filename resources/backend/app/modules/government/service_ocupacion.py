from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.government.models import (
    GovernmentAct,  # noqa: F401
    GovernmentAssignment,
    GovernmentAssignmentCompetency,  # noqa: F401
    GovernmentAssignmentHistory,
    GovernmentEntity,  # noqa: F401
    GovernmentOfficial,
    GovernmentOfficialHistory,
    GovernmentPosition,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.schemas_ocupacion import (
    AsignacionIn,
    AvocarIn,
    DescartarIn,
    FinalizarIn,
    RevocarIn,
)
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids  # noqa: F401
from app.modules.government.service_autoridad import competencias_en_vigor
from app.modules.government.service_sod import (  # noqa: F401
    evaluar_antes_de_actuar,
    funcionarios_de_actor,
    usuarios_equivalentes,
)
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio  # noqa: F401

ENTIDAD_FUNCIONARIO = "GovernmentOfficial"
ENTIDAD_ASIGNACION = "GovernmentAssignment"

FIGURAS: dict[str, dict[str, Any]] = {
    "TITULAR": {
        "etiqueta": "Titular",
        "grupo": "TITULARIDAD",
        "base_legal": "LOPPM art. 88.7",
        "descripcion": "Designado para ocupar el cargo.",
        "exige_fin": False,
        "exige_cargo_origen": False,
        "exige_gaceta": False,
        "lleva_competencias": False,
    },
    "ENCARGADURIA": {
        "etiqueta": "Encargado",
        "grupo": "TEMPORAL",
        "base_legal": "LOPPM art. 87; práctica administrativa",
        "descripcion": "Ejerce el cargo por encargo, también en designación temporal.",
        "exige_fin": False,
        "exige_cargo_origen": False,
        "exige_gaceta": False,
        "lleva_competencias": False,
    },
    "SUPLENCIA": {
        "etiqueta": "Suplente",
        "grupo": "TEMPORAL",
        "base_legal": "LOPPM art. 87",
        "descripcion": "Suple la ausencia temporal del titular.",
        "exige_fin": True,
        "exige_cargo_origen": True,
        "exige_gaceta": False,
        "lleva_competencias": False,
    },
    "COMISION_SERVICIO": {
        "etiqueta": "En comisión de servicio",
        "grupo": "TEMPORAL",
        "base_legal": "LEFP arts. 71 y 72",
        "descripcion": "Ejerce temporalmente otro cargo, un año como máximo.",
        "exige_fin": True,
        "exige_cargo_origen": True,
        "exige_gaceta": False,
        "lleva_competencias": False,
    },
    "DELEGACION_ATRIBUCIONES": {
        "etiqueta": "Delegación de atribuciones",
        "grupo": "DELEGACION",
        "base_legal": "LOAP arts. 34, 35, 37 y 40",
        "descripcion": "Ejerce atribuciones delegadas por el cargo.",
        "exige_fin": False,
        "exige_cargo_origen": True,
        "exige_gaceta": True,
        "lleva_competencias": True,
    },
    "DELEGACION_FIRMA": {
        "etiqueta": "Delegación de firma",
        "grupo": "DELEGACION",
        "base_legal": "LOAP arts. 34, 35 y 40",
        "descripcion": "Firma por delegación; el acto sigue siendo del delegante.",
        "exige_fin": False,
        "exige_cargo_origen": True,
        "exige_gaceta": True,
        "lleva_competencias": True,
    },
}

ETIQUETAS_INSTRUMENTO: dict[str, str] = {
    "DECRETO": "Decreto",
    "RESOLUCION": "Resolución",
    "ORDEN": "Orden",
    "PROVIDENCIA": "Providencia",
    "INSTRUCCION": "Instrucción",
    "CIRCULAR": "Circular",
    "OTRA_DECISION": "Otra decisión",
}

SITUACIONES = [
    "BORRADOR",
    "DESCARTADA",
    "FUTURA",
    "VIGENTE",
    "VENCIDA",
    "REVOCADA",
    "FINALIZADA",
    "SIN_EFECTO",
]


def enmascarar_documento(tipo: str, numero: str) -> str:
    return f"{tipo}-" + "*" * (len(numero) - 2) + numero[-2:]


def _invalida(codigo: str, mensaje: str) -> KontrolError:
    return KontrolError(code=codigo, message=mensaje, status_code=422)


def _funcionario_salida(f: GovernmentOfficial) -> dict[str, Any]:
    return {
        "id": f.id,
        "codigo": f.codigo,
        "nombre": f.nombre,
        "documento": enmascarar_documento(f.tipo_documento, f.numero_documento),
        "estado": f.estado,
        "version": f.version,
        "creado_en": _instante(f.created_at),
    }


def _funcionario_de_empresa(
    db: Session, ctx: CompanyContext, funcionario_id: str, bloquear: bool = False
) -> GovernmentOfficial:
    query = select(GovernmentOfficial).where(
        GovernmentOfficial.id == funcionario_id,
        GovernmentOfficial.company_id == ctx.company_id,
    )
    if bloquear:
        query = query.with_for_update()
    funcionario = db.scalar(query)
    if not funcionario:
        raise NotFoundError(
            code="GOV_OFFICIAL_NOT_FOUND",
            message="El funcionario no existe en este ente",
        )
    return funcionario


def _siguiente_codigo_funcionario(db: Session, ctx: CompanyContext) -> str:
    total = (
        db.scalar(
            select(func.count(GovernmentOfficial.id)).where(
                GovernmentOfficial.company_id == ctx.company_id
            )
        )
        or 0
    )
    return f"FUN-{total + 1:05d}"


def _siguiente_codigo_asignacion(db: Session, ctx: CompanyContext) -> str:
    total = (
        db.scalar(
            select(func.count(GovernmentAssignment.id)).where(
                GovernmentAssignment.company_id == ctx.company_id
            )
        )
        or 0
    )
    return f"ASG-{total + 1:05d}"


def _historia_funcionario(
    db: Session,
    ctx: CompanyContext,
    funcionario: GovernmentOfficial,
    tipo: str,
    detalle: dict[str, Any],
) -> None:
    db.add(
        GovernmentOfficialHistory(
            official_id=funcionario.id,
            tipo=tipo,
            detalle=detalle,
            company_id=ctx.company_id,
            created_by=ctx.user_id,
        )
    )


def _historia_asignacion(
    db: Session,
    ctx: CompanyContext,
    asignacion: GovernmentAssignment,
    tipo: str,
    detalle: dict[str, Any],
) -> None:
    db.add(
        GovernmentAssignmentHistory(
            assignment_id=asignacion.id,
            tipo=tipo,
            detalle=detalle,
            company_id=ctx.company_id,
            created_by=ctx.user_id,
        )
    )


def _estado_funcionario(f: GovernmentOfficial) -> dict[str, Any]:
    return {
        "codigo": f.codigo,
        "nombre": f.nombre,
        "documento_enmascarado": enmascarar_documento(f.tipo_documento, f.numero_documento),
        "estado": f.estado,
    }


def _auditar(
    db: Session,
    ctx: CompanyContext,
    accion: str,
    entidad: str,
    entidad_id: str | None,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    motivo: str | None = None,
) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=entidad,
        entity_id=entidad_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before=before,
        after=after,
        reason=motivo,
    )


def catalogo() -> dict[str, Any]:
    figuras = []
    for codigo, datos in FIGURAS.items():
        figuras.append({**datos, "codigo": codigo})
    instrumentos = [
        {"codigo": codigo, "etiqueta": etiqueta}
        for codigo, etiqueta in ETIQUETAS_INSTRUMENTO.items()
    ]
    return {
        "figuras": figuras,
        "instrumentos": instrumentos,
        "situaciones": SITUACIONES,
    }


def listar_funcionarios(
    db: Session,
    ctx: CompanyContext,
    texto: str | None,
    estado: str | None,
    pagina: int,
    por_pagina: int,
) -> dict[str, Any]:
    condiciones = [GovernmentOfficial.company_id == ctx.company_id]
    if texto:
        like = f"%{texto}%"
        condiciones.append(
            or_(
                GovernmentOfficial.nombre.ilike(like),
                GovernmentOfficial.codigo.ilike(like),
            )
        )
    if estado:
        condiciones.append(GovernmentOfficial.estado == estado)

    total = db.scalar(
        select(func.count(GovernmentOfficial.id)).where(*condiciones)
    ) or 0
    registros = db.scalars(
        select(GovernmentOfficial)
        .where(*condiciones)
        .order_by(GovernmentOfficial.nombre)
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()
    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "items": [_funcionario_salida(f) for f in registros],
    }


def detalle_funcionario(
    db: Session, ctx: CompanyContext, funcionario_id: str
) -> dict[str, Any]:
    funcionario = _funcionario_de_empresa(db, ctx, funcionario_id)
    historial = db.scalars(
        select(GovernmentOfficialHistory)
        .where(
            GovernmentOfficialHistory.official_id == funcionario.id,
            GovernmentOfficialHistory.company_id == ctx.company_id,
        )
        .order_by(GovernmentOfficialHistory.created_at.desc())
    ).all()
    asignaciones = db.scalars(
        select(GovernmentAssignment)
        .where(
            GovernmentAssignment.official_id == funcionario.id,
            GovernmentAssignment.company_id == ctx.company_id,
        )
        .order_by(GovernmentAssignment.created_at.desc())
    ).all()
    return {
        **_funcionario_salida(funcionario),
        "historia": [_historia_salida(h, db, ctx) for h in historial],
        "asignaciones": [_resumen_de(a, db, ctx) for a in asignaciones],
    }


def crear_funcionario(
    db: Session, ctx: CompanyContext, datos: Any
) -> GovernmentOfficial:
    funcionario = GovernmentOfficial(
        company_id=ctx.company_id,
        codigo=_siguiente_codigo_funcionario(db, ctx),
        nombre=datos.nombre,
        tipo_documento=datos.tipo_documento,
        numero_documento=datos.numero_documento,
        estado="ACTIVO",
        version=1,
        created_by=ctx.user_id,
    )
    db.add(funcionario)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            code="GOV_OFFICIAL_DUPLICATE",
            message="Ya hay un funcionario con ese documento",
        ) from None
    _historia_funcionario(
        db,
        ctx,
        funcionario,
        "CREADO",
        {"despues": _estado_funcionario(funcionario)},
    )
    _auditar(
        db,
        ctx,
        "GOV_OFFICIAL_CREATED",
        ENTIDAD_FUNCIONARIO,
        str(funcionario.id),
        None,
        _estado_funcionario(funcionario),
    )
    return funcionario


def editar_funcionario(
    db: Session,
    ctx: CompanyContext,
    funcionario_id: str,
    version: int | None,
    cambios: Any,
) -> GovernmentOfficial:
    if version is None:
        raise KontrolError(
            code="GOV_OFFICIAL_IF_MATCH_REQUIRED",
            message="Se requiere la versión del funcionario",
            status_code=428,
        )
    funcionario = _funcionario_de_empresa(db, ctx, funcionario_id, bloquear=True)
    if funcionario.version != version:
        raise ConflictError(
            code="GOV_OFFICIAL_STALE",
            message="La versión enviada no coincide con la actual",
            details={"version_actual": funcionario.version},
        )
    datos_cambios = cambios.model_dump(exclude_unset=True)
    if not datos_cambios:
        raise _invalida("GOV_ASSIGNMENT_INVALID", "No hay cambios")
    antes = _estado_funcionario(funcionario)
    for clave, valor in datos_cambios.items():
        setattr(funcionario, clave, valor)
    funcionario.version += 1
    despues = _estado_funcionario(funcionario)
    _historia_funcionario(
        db, ctx, funcionario, "EDITADO", {"antes": antes, "despues": despues}
    )
    _auditar(
        db,
        ctx,
        "GOV_OFFICIAL_UPDATED",
        ENTIDAD_FUNCIONARIO,
        str(funcionario.id),
        antes,
        despues,
    )
    return funcionario


def _cargo_de_empresa(
    db: Session, ctx: CompanyContext, cargo_id: str, bloquear: bool = False
) -> GovernmentPosition:
    query = select(GovernmentPosition).where(
        GovernmentPosition.id == cargo_id,
        GovernmentPosition.company_id == ctx.company_id,
    )
    if bloquear:
        query = query.with_for_update()
    cargo = db.scalar(query)
    if not cargo:
        raise NotFoundError(
            code="GOV_ASSIGNMENT_POSITION_NOT_FOUND",
            message="El cargo no existe en este ente",
        )
    return cargo


def _acto_de_empresa(db: Session, ctx: CompanyContext, acto_id: str) -> GovernmentAct:
    acto = db.scalar(
        select(GovernmentAct).where(
            GovernmentAct.id == acto_id,
            GovernmentAct.company_id == ctx.company_id,
        )
    )
    if not acto:
        raise NotFoundError(
            code="GOV_ASSIGNMENT_ACT_NOT_FOUND",
            message="El acto no existe en este ente",
        )
    return acto


def _ejercicio_de(db: Session, cargo: GovernmentPosition) -> GovernmentStructure | None:
    return db.scalar(
        select(GovernmentStructure).where(
            GovernmentStructure.id == cargo.structure_id,
            GovernmentStructure.company_id == cargo.company_id,
        )
    )


def _exigir_cargo_utilizable(
    db: Session,
    ctx: CompanyContext,
    cargo: GovernmentPosition,
    desde: date,
    hasta: date | None,
) -> None:
    if cargo.status != "VIGENTE":
        raise _invalida(
            "GOV_ASSIGNMENT_POSITION_INVALID", "El cargo no está vigente"
        )
    estructura = _ejercicio_de(db, cargo)
    if not estructura or estructura.status != "VIGENTE":
        raise _invalida(
            "GOV_ASSIGNMENT_POSITION_INVALID",
            "La estructura del cargo no está vigente",
        )
    if desde < cargo.valid_from:
        raise _invalida(
            "GOV_ASSIGNMENT_POSITION_INVALID",
            "La vigencia no cabe en la del cargo",
        )
    if cargo.valid_to and (desde > cargo.valid_to or (hasta and hasta > cargo.valid_to)):
        raise _invalida(
            "GOV_ASSIGNMENT_POSITION_INVALID",
            "La vigencia no cabe en la del cargo",
        )
    if desde.year != estructura.exercise or (
        hasta is not None and hasta.year != estructura.exercise
    ):
        raise _invalida(
            "GOV_ASSIGNMENT_POSITION_INVALID",
            "La vigencia debe caber en el ejercicio del cargo",
        )


def _acto_eficaz_en(acto: GovernmentAct, fecha: date) -> bool:
    return (
        acto.status == "EFICAZ"
        and acto.fecha_eficacia is not None
        and acto.fecha_eficacia <= fecha
    )


def _exigir_acto(acto: GovernmentAct, fecha: date, figura: str) -> None:
    if not _acto_eficaz_en(acto, fecha):
        raise _invalida(
            "GOV_ASSIGNMENT_ACT_INVALID",
            "El acto debe estar eficaz antes del inicio",
        )
    if FIGURAS[figura]["exige_gaceta"] and acto.medio != "GACETA":
        raise _invalida(
            "GOV_ASSIGNMENT_ACT_INVALID",
            "La delegación debe estar publicada en gaceta (LOAP art. 40)",
        )


def _ejerce_cargo(
    db: Session,
    ctx: CompanyContext,
    funcionario_id: str,
    cargo_id: str,
    fecha: date,
) -> bool:
    return (
        db.scalar(
            select(GovernmentAssignment.id).where(
                GovernmentAssignment.company_id == ctx.company_id,
                GovernmentAssignment.official_id == funcionario_id,
                GovernmentAssignment.position_id == cargo_id,
                GovernmentAssignment.status == "ACTIVO",
                GovernmentAssignment.desde <= fecha,
                or_(
                    GovernmentAssignment.hasta.is_(None),
                    GovernmentAssignment.hasta >= fecha,
                ),
                or_(
                    GovernmentAssignment.fin_efectivo.is_(None),
                    GovernmentAssignment.fin_efectivo >= fecha,
                ),
                GovernmentAssignment.grupo.in_(("TITULARIDAD", "TEMPORAL")),
            )
        )
        is not None
    )


def _hay_titular(
    db: Session, ctx: CompanyContext, cargo_id: str, fecha: date
) -> bool:
    return (
        db.scalar(
            select(GovernmentAssignment.id).where(
                GovernmentAssignment.company_id == ctx.company_id,
                GovernmentAssignment.position_id == cargo_id,
                GovernmentAssignment.status == "ACTIVO",
                GovernmentAssignment.desde <= fecha,
                or_(
                    GovernmentAssignment.hasta.is_(None),
                    GovernmentAssignment.hasta >= fecha,
                ),
                or_(
                    GovernmentAssignment.fin_efectivo.is_(None),
                    GovernmentAssignment.fin_efectivo >= fecha,
                ),
                GovernmentAssignment.grupo == "TITULARIDAD",
            )
        )
        is not None
    )


def _unidad_bajo(
    db: Session, ctx: CompanyContext, unidad_id: str | None, ancestro_id: str
) -> bool:
    if unidad_id is None:
        return False
    visitados: set[str] = set()
    actual: str | None = unidad_id
    while actual is not None and actual not in visitados:
        if actual == ancestro_id:
            return True
        visitados.add(actual)
        unidad = db.scalar(
            select(GovernmentUnit).where(
                GovernmentUnit.id == actual,
                GovernmentUnit.company_id == ctx.company_id,
            )
        )
        if not unidad:
            break
        actual = unidad.parent_id
    return False


def _competencias_a_delegar(
    db: Session, cargo: GovernmentPosition, datos: Any
) -> list[dict[str, Any]]:
    vigentes = competencias_en_vigor(db, cargo, datos.desde)
    pedidas = datos.competencias or []
    if not pedidas:
        return []

    if datos.figura == "DELEGACION_FIRMA":
        for c in pedidas:
            if c.accion != "FIRMAR":
                raise _invalida(
                    "GOV_ASSIGNMENT_NOT_DELEGABLE",
                    "La competencia no corresponde a esa figura",
                )
    elif datos.figura == "DELEGACION_ATRIBUCIONES":
        for c in pedidas:
            if c.accion == "FIRMAR":
                raise _invalida(
                    "GOV_ASSIGNMENT_NOT_DELEGABLE",
                    "La competencia no corresponde a esa figura",
                )

    resultado = []
    for c in pedidas:
        encontrada = next(
            (
                v
                for v in vigentes
                if v["accion"] == c.accion and v["materia"] == c.materia
            ),
            None,
        )
        if not encontrada:
            raise _invalida(
                "GOV_ASSIGNMENT_NOT_DELEGABLE",
                "Solo se delega lo que el cargo tiene (LOAP art. 34)",
            )
        resultado.append(encontrada)
    return resultado


def _exigir_emisor(acto: GovernmentAct, cargo: GovernmentPosition, figura: str) -> None:
    if FIGURAS[figura]["grupo"] == "DELEGACION":
        if acto.cargo_id != cargo.id:
            raise _invalida(
                "GOV_ASSIGNMENT_ISSUER_INVALID",
                "La delegación la confiere el cargo delegante (LOAP art. 34)",
            )
    elif figura in ("TITULAR", "ENCARGADURIA", "COMISION_SERVICIO"):
        if acto.cargo_id == cargo.id:
            raise _invalida(
                "GOV_ASSIGNMENT_ISSUER_INVALID",
                "El cargo no puede designarse a sí mismo",
            )
    # SUPLENCIA: sin condición


def validar(db: Session, ctx: CompanyContext, datos: Any) -> list[dict[str, Any]]:
    # 1. Funcionario
    funcionario = _funcionario_de_empresa(db, ctx, datos.funcionario_id)
    if funcionario.estado != "ACTIVO":
        raise _invalida(
            "GOV_ASSIGNMENT_OFFICIAL_INVALID", "El funcionario no está activo"
        )

    # 2. Cargo
    cargo = _cargo_de_empresa(db, ctx, datos.cargo_id)
    _exigir_cargo_utilizable(db, ctx, cargo, datos.desde, datos.hasta)

    # 3. Acto
    acto = _acto_de_empresa(db, ctx, datos.acto_id)
    _exigir_acto(acto, datos.desde, datos.figura)
    _exigir_emisor(acto, cargo, datos.figura)

    # 4. Cargo de origen
    cargo_origen = None
    if FIGURAS[datos.figura]["exige_cargo_origen"] and datos.cargo_origen_id is None:
        raise _invalida(
            "GOV_ASSIGNMENT_INVALID", "Indique el cargo de origen"
        )
    if datos.cargo_origen_id is not None:
        cargo_origen = _cargo_de_empresa(db, ctx, datos.cargo_origen_id)
        if cargo_origen.id == cargo.id:
            raise _invalida(
                "GOV_ASSIGNMENT_INVALID", "El cargo de origen debe ser otro"
            )

    # 5. Ejercicio del cargo de origen
    if datos.figura == "SUPLENCIA":
        if not _hay_titular(db, ctx, str(cargo.id), datos.desde):
            raise _invalida(
                "GOV_ASSIGNMENT_INVALID", "Solo se suple a un titular"
            )
    elif datos.figura in ("COMISION_SERVICIO", "DELEGACION_ATRIBUCIONES", "DELEGACION_FIRMA"):
        if cargo_origen is None:
            raise _invalida("GOV_ASSIGNMENT_INVALID", "Esta figura exige cargo de origen")
        if not _ejerce_cargo(
            db, ctx, str(funcionario.id), str(cargo_origen.id), datos.desde
        ):
            raise _invalida(
                "GOV_ASSIGNMENT_INVALID",
                "El funcionario no ejerce el cargo de origen",
            )

    # 6. Comisión de servicio: máximo un año
    if datos.figura == "COMISION_SERVICIO" and datos.hasta is not None:
        try:
            limite = datos.desde.replace(year=datos.desde.year + 1)
        except ValueError:
            limite = datos.desde.replace(year=datos.desde.year + 1, day=28)
        if datos.hasta > limite:
            raise _invalida(
                "GOV_ASSIGNMENT_LIMIT_EXCEEDED",
                "La comisión de servicio no puede exceder un año (LEFP art. 72)",
            )

    # 7. Máxima autoridad municipal
    if datos.figura == "SUPLENCIA" and datos.maxima_autoridad is True:
        ente = db.scalar(
            select(GovernmentEntity).where(
                GovernmentEntity.company_id == ctx.company_id
            )
        )
        if (
            ente is not None
            and ente.nivel_territorial == "MUNICIPAL"
            and datos.hasta is not None
        ):
            dias = (datos.hasta - datos.desde).days + 1
            if dias > 90:
                raise _invalida(
                    "GOV_ASSIGNMENT_LIMIT_EXCEEDED",
                    "Más de 90 días: el Concejo debe evaluar la ausencia (LOPPM art. 87)",
                )
            if dias > 15 and datos.autorizacion_concejo is None:
                raise _invalida(
                    "GOV_ASSIGNMENT_LIMIT_EXCEEDED",
                    "Más de 15 días exige autorización del Concejo (LOPPM art. 87)",
                )

    # 8. Delegaciones
    if FIGURAS[datos.figura]["grupo"] == "DELEGACION":
        if acto.titularidad == "DELEGACION":
            raise _invalida(
                "GOV_ASSIGNMENT_NOT_DELEGABLE",
                "Lo delegado no se delega (LOAP art. 35)",
            )
        if not _unidad_bajo(
            db,
            ctx,
            cargo_origen.unit_id if cargo_origen else None,
            cargo.unit_id,
        ):
            raise _invalida(
                "GOV_ASSIGNMENT_INVALID",
                "El delegado debe depender del delegante (LOAP art. 34)",
            )
        return _competencias_a_delegar(db, cargo, datos)

    return []


def _asignacion_de_empresa(db: Session, ctx: CompanyContext, asignacion_id: str, bloquear: bool = False) -> GovernmentAssignment:
    query = select(GovernmentAssignment).where(
        GovernmentAssignment.id == asignacion_id,
        GovernmentAssignment.company_id == ctx.company_id,
    )
    if bloquear:
        query = query.with_for_update()
    asignacion = db.execute(query).scalar_one_or_none()
    if asignacion is None:
        raise NotFoundError("GOV_ASSIGNMENT_NOT_FOUND", "La asignación no existe en este ente")
    return asignacion


def _para_escribir(db: Session, ctx: CompanyContext, asignacion_id: str, version: int | None) -> GovernmentAssignment:
    if version is None:
        raise KontrolError(
            code="GOV_ASSIGNMENT_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    asignacion = _asignacion_de_empresa(db, ctx, asignacion_id, bloquear=True)
    if asignacion.version != version:
        raise ConflictError(
            "GOV_ASSIGNMENT_STALE",
            "La asignación cambió desde que la abrió; recárguela",
            details={"version_actual": asignacion.version},
        )
    return asignacion


def _exigir_estado(asignacion: GovernmentAssignment, estado: str) -> None:
    if asignacion.status != estado:
        raise ConflictError(
            "GOV_ASSIGNMENT_INVALID_STATE",
            f"La asignación debe estar en estado {estado}",
        )


def _estado_asignacion(a: GovernmentAssignment) -> dict:
    return {
        "codigo": a.codigo,
        "figura": a.figura,
        "grupo": a.grupo,
        "status": a.status,
        "funcionario_id": a.official_id,
        "cargo_id": a.position_id,
        "cargo_origen_id": a.cargo_origen_id,
        "acto_id": a.act_id,
        "desde": a.desde.isoformat(),
        "hasta": a.hasta.isoformat() if a.hasta else None,
        "fin_efectivo": a.fin_efectivo.isoformat() if a.fin_efectivo else None,
        "fundamento": a.fundamento,
        "revocation_act_id": a.revocation_act_id,
        "motivo": a.motivo_fin,
        "version": a.version,
    }


def _competencias_de(db: Session, ctx: CompanyContext, asignacion_id: str) -> list[GovernmentAssignmentCompetency]:
    return list(
        db.execute(
            select(GovernmentAssignmentCompetency).where(
                GovernmentAssignmentCompetency.assignment_id == asignacion_id,
                GovernmentAssignmentCompetency.company_id == ctx.company_id,
            )
        )
        .scalars()
        .all()
    )


def _reemplazar_competencias(db: Session, ctx: CompanyContext, asignacion: GovernmentAssignment, filas: list[dict]) -> None:
    db.execute(
        delete(GovernmentAssignmentCompetency).where(
            GovernmentAssignmentCompetency.assignment_id == asignacion.id,
            GovernmentAssignmentCompetency.company_id == ctx.company_id,
        )
    )
    for fila in filas:
        monto = fila.get("monto")
        db.add(
            GovernmentAssignmentCompetency(
                assignment_id=asignacion.id,
                company_id=ctx.company_id,
                action=fila["accion"],
                subject=fila["materia"],
                limit_type=fila.get("tipo_limite"),
                limit_amount=Decimal(monto) if monto is not None else None,
                limit_currency=fila.get("moneda"),
            )
        )


def _como_datos(db: Session, ctx: CompanyContext, a: GovernmentAssignment) -> SimpleNamespace:
    competencias = [
        SimpleNamespace(accion=c.action, materia=c.subject)
        for c in _competencias_de(db, ctx, str(a.id))
    ]
    return SimpleNamespace(
        funcionario_id=a.official_id,
        cargo_id=a.position_id,
        figura=a.figura,
        cargo_origen_id=a.cargo_origen_id,
        acto_id=a.act_id,
        desde=a.desde,
        hasta=a.hasta,
        maxima_autoridad=a.maxima_autoridad,
        autorizacion_concejo=a.autorizacion_concejo,
        competencias=competencias,
    )


def _exigir_no_autoridad_propia(db: Session, ctx: CompanyContext, official_id: str) -> None:
    """Impide registrar o activar la ocupación del propio funcionario."""
    if official_id in funcionarios_de_actor(db, ctx, str(ctx.user_id)):
        raise KontrolError(
            code="GOV_ASSIGNMENT_SELF_AUTHORITY",
            message="Nadie registra ni activa la ocupación de su propio funcionario",
            status_code=403,
        )


def crear(db: Session, ctx: CompanyContext, datos: AsignacionIn) -> GovernmentAssignment:
    _exigir_no_autoridad_propia(db, ctx, str(datos.funcionario_id))
    filas = validar(db, ctx, datos)
    asignacion = GovernmentAssignment(
        company_id=ctx.company_id,
        codigo=_siguiente_codigo_asignacion(db, ctx),
        official_id=datos.funcionario_id,
        position_id=datos.cargo_id,
        figura=datos.figura,
        grupo=FIGURAS[datos.figura]["grupo"],
        cargo_origen_id=datos.cargo_origen_id,
        act_id=datos.acto_id,
        desde=datos.desde,
        hasta=datos.hasta,
        status="BORRADOR",
        fundamento=datos.fundamento,
        rendicion=datos.rendicion,
        maxima_autoridad=datos.maxima_autoridad,
        autorizacion_concejo=datos.autorizacion_concejo,
        declara_delegable=datos.declara_delegable,
        version=1,
        created_by=ctx.user_id,
    )
    db.add(asignacion)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_ASSIGNMENT_STALE",
            "Otra asignación se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    _reemplazar_competencias(db, ctx, asignacion, filas)
    estado = _estado_asignacion(asignacion)
    _historia_asignacion(db, ctx, asignacion, "CREADA", {"despues": estado})
    _auditar(db, ctx, "GOV_ASSIGNMENT_CREATED", ENTIDAD_ASIGNACION, str(asignacion.id), None, estado)
    return asignacion


def editar(db: Session, ctx: CompanyContext, asignacion_id: str, version: int | None, datos: AsignacionIn) -> GovernmentAssignment:
    asignacion = _para_escribir(db, ctx, asignacion_id, version)
    _exigir_estado(asignacion, "BORRADOR")
    filas = validar(db, ctx, datos)
    antes = _estado_asignacion(asignacion)

    asignacion.official_id = datos.funcionario_id
    asignacion.position_id = datos.cargo_id
    asignacion.figura = datos.figura
    asignacion.grupo = FIGURAS[datos.figura]["grupo"]
    asignacion.cargo_origen_id = datos.cargo_origen_id
    asignacion.act_id = datos.acto_id
    asignacion.desde = datos.desde
    asignacion.hasta = datos.hasta
    asignacion.fundamento = datos.fundamento
    asignacion.rendicion = datos.rendicion
    asignacion.maxima_autoridad = datos.maxima_autoridad
    asignacion.autorizacion_concejo = datos.autorizacion_concejo
    asignacion.declara_delegable = datos.declara_delegable
    asignacion.version += 1
    db.flush()
    _reemplazar_competencias(db, ctx, asignacion, filas)

    despues = _estado_asignacion(asignacion)
    _historia_asignacion(db, ctx, asignacion, "EDITADA", {"antes": antes, "despues": despues})
    _auditar(db, ctx, "GOV_ASSIGNMENT_UPDATED", ENTIDAD_ASIGNACION, str(asignacion.id), antes, despues)
    return asignacion


def descartar(db: Session, ctx: CompanyContext, asignacion_id: str, version: int | None, datos: DescartarIn) -> None:
    asignacion = _para_escribir(db, ctx, asignacion_id, version)
    _exigir_estado(asignacion, "BORRADOR")
    antes = _estado_asignacion(asignacion)

    asignacion.status = "DESCARTADO"
    asignacion.motivo_fin = datos.motivo
    asignacion.ended_at = datetime.now(UTC)
    asignacion.ended_by = ctx.user_id
    asignacion.version += 1

    despues = _estado_asignacion(asignacion)
    _historia_asignacion(db, ctx, asignacion, "DESCARTADA", {"antes": antes, "despues": despues})
    _auditar(db, ctx, "GOV_ASSIGNMENT_DISCARDED", ENTIDAD_ASIGNACION, str(asignacion.id), antes, despues, datos.motivo)


def _solapada(db: Session, ctx: CompanyContext, a: GovernmentAssignment) -> bool:
    fin_a = a.fin_efectivo or a.hasta
    condiciones = [
        GovernmentAssignment.company_id == ctx.company_id,
        GovernmentAssignment.position_id == a.position_id,
        GovernmentAssignment.id != a.id,
        GovernmentAssignment.status == "ACTIVO",
    ]
    if a.grupo == "DELEGACION":
        condiciones.append(GovernmentAssignment.official_id == a.official_id)
        condiciones.append(GovernmentAssignment.grupo == "DELEGACION")
    else:
        condiciones.append(GovernmentAssignment.grupo == a.grupo)

    if fin_a is not None:
        condiciones.append(GovernmentAssignment.desde <= fin_a)
    condiciones.append(
        or_(
            func.coalesce(GovernmentAssignment.fin_efectivo, GovernmentAssignment.hasta).is_(None),
            func.coalesce(GovernmentAssignment.fin_efectivo, GovernmentAssignment.hasta) >= a.desde,
        )
    )
    otra = db.execute(select(GovernmentAssignment.id).where(*condiciones).limit(1)).scalar_one_or_none()
    return otra is not None


def activar(db: Session, ctx: CompanyContext, asignacion_id: str, version: int | None) -> GovernmentAssignment:
    asignacion = _para_escribir(db, ctx, asignacion_id, version)
    _exigir_estado(asignacion, "BORRADOR")

    if asignacion.created_by in usuarios_equivalentes(db, ctx, str(ctx.user_id)):
        raise KontrolError(
            code="GOV_ASSIGNMENT_SELF_ACTIVATION",
            message="Quien registró la asignación no puede activarla: debe hacerlo otro usuario",
            status_code=403,
        )
    _exigir_no_autoridad_propia(db, ctx, str(asignacion.official_id))

    _cargo_de_empresa(db, ctx, asignacion.position_id, bloquear=True)
    filas = validar(db, ctx, _como_datos(db, ctx, asignacion))
    _reemplazar_competencias(db, ctx, asignacion, filas)

    if _solapada(db, ctx, asignacion):
        raise ConflictError(
            "GOV_ASSIGNMENT_OVERLAP",
            "Ya hay otra asignación vigente incompatible en ese período",
        )

    evaluar_antes_de_actuar(db, ctx, "ORG04_ACTIVAR", ENTIDAD_ASIGNACION, str(asignacion.id))

    antes = _estado_asignacion(asignacion)
    asignacion.status = "ACTIVO"
    asignacion.activated_at = datetime.now(UTC)
    asignacion.activated_by = ctx.user_id
    asignacion.version += 1

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("GOV_ASSIGNMENT_OVERLAP", "Ya hay otra asignación vigente incompatible en ese período") from None

    despues = _estado_asignacion(asignacion)
    _historia_asignacion(db, ctx, asignacion, "ACTIVADA", {"antes": antes, "despues": despues})
    _auditar(db, ctx, "GOV_ASSIGNMENT_ACTIVATED", ENTIDAD_ASIGNACION, str(asignacion.id), antes, despues)
    return asignacion


def _validar_fin(a: GovernmentAssignment, fecha: date) -> None:
    if fecha < a.desde or (a.hasta and fecha > a.hasta):
        raise _invalida("GOV_ASSIGNMENT_INVALID", "La fecha debe caber en la vigencia")


def revocar(db: Session, ctx: CompanyContext, asignacion_id: str, version: int | None, datos: RevocarIn) -> None:
    asignacion = _para_escribir(db, ctx, asignacion_id, version)
    _exigir_estado(asignacion, "ACTIVO")
    cargo = _cargo_de_empresa(db, ctx, asignacion.position_id, bloquear=True)
    acto = _acto_de_empresa(db, ctx, datos.acto_id)
    _exigir_acto(acto, datos.fecha, asignacion.figura)
    _exigir_emisor(acto, cargo, asignacion.figura)
    _validar_fin(asignacion, datos.fecha)
    evaluar_antes_de_actuar(db, ctx, "ORG04_REVOCAR", ENTIDAD_ASIGNACION, str(asignacion.id))

    antes = _estado_asignacion(asignacion)
    asignacion.status = "REVOCADO"
    asignacion.revocation_act_id = str(acto.id)
    asignacion.fin_efectivo = datos.fecha
    asignacion.motivo_fin = datos.motivo
    asignacion.ended_at = datetime.now(UTC)
    asignacion.ended_by = ctx.user_id
    asignacion.version += 1

    despues = _estado_asignacion(asignacion)
    _historia_asignacion(db, ctx, asignacion, "REVOCADA", {"antes": antes, "despues": despues})
    _auditar(db, ctx, "GOV_ASSIGNMENT_REVOKED", ENTIDAD_ASIGNACION, str(asignacion.id), antes, despues, datos.motivo)


def finalizar(db: Session, ctx: CompanyContext, asignacion_id: str, version: int | None, datos: FinalizarIn) -> None:
    asignacion = _para_escribir(db, ctx, asignacion_id, version)
    _exigir_estado(asignacion, "ACTIVO")
    _cargo_de_empresa(db, ctx, asignacion.position_id, bloquear=True)
    _validar_fin(asignacion, datos.fecha)
    evaluar_antes_de_actuar(db, ctx, "ORG04_FINALIZAR", ENTIDAD_ASIGNACION, str(asignacion.id))

    antes = _estado_asignacion(asignacion)
    asignacion.status = "FINALIZADO"
    asignacion.fin_efectivo = datos.fecha
    asignacion.motivo_fin = datos.motivo
    asignacion.ended_at = datetime.now(UTC)
    asignacion.ended_by = ctx.user_id
    asignacion.version += 1

    despues = _estado_asignacion(asignacion)
    _historia_asignacion(db, ctx, asignacion, "FINALIZADA", {"antes": antes, "despues": despues})
    _auditar(db, ctx, "GOV_ASSIGNMENT_FINISHED", ENTIDAD_ASIGNACION, str(asignacion.id), antes, despues, datos.motivo)


def avocar(db: Session, ctx: CompanyContext, asignacion_id: str, version: int | None, datos: AvocarIn) -> None:
    asignacion = _para_escribir(db, ctx, asignacion_id, version)
    _exigir_estado(asignacion, "ACTIVO")

    if asignacion.grupo != "DELEGACION":
        raise _invalida("GOV_ASSIGNMENT_INVALID", "Solo se avoca lo delegado (LOAP art. 41)")

    cargo = _cargo_de_empresa(db, ctx, asignacion.position_id, bloquear=True)
    acto = _acto_de_empresa(db, ctx, datos.acto_id)

    if not _acto_eficaz_en(acto, hoy_de_negocio()):
        raise _invalida("GOV_ASSIGNMENT_ACT_INVALID", "El acto de avocación debe estar eficaz")

    _exigir_emisor(acto, cargo, asignacion.figura)

    asignacion.version += 1
    _historia_asignacion(
        db,
        ctx,
        asignacion,
        "AVOCADA",
        {"asunto": datos.asunto, "acto_id": str(acto.id)},
    )
    _auditar(
        db,
        ctx,
        "GOV_ASSIGNMENT_AVOCATED",
        ENTIDAD_ASIGNACION,
        str(asignacion.id),
        None,
        {"codigo": asignacion.codigo, "asunto": datos.asunto, "acto_id": str(acto.id)},
    )


@dataclass
class _Contexto:
    funcionarios: dict
    cargos: dict
    unidades: dict
    estructuras: dict
    actos: dict
    eficacia_revocacion: dict


def _cargar_contexto(db: Session, ctx: CompanyContext, asignaciones) -> _Contexto:
    funcionario_ids = {a.official_id for a in asignaciones if a.official_id}
    cargo_ids = {a.position_id for a in asignaciones if a.position_id}
    cargo_ids.update(a.cargo_origen_id for a in asignaciones if a.cargo_origen_id)
    acto_ids = {a.act_id for a in asignaciones if a.act_id}
    acto_ids.update(a.revocation_act_id for a in asignaciones if a.revocation_act_id)

    funcionarios = {}
    if funcionario_ids:
        funcionarios = {
            f.id: f
            for f in db.execute(
                select(GovernmentOfficial).where(
                    GovernmentOfficial.company_id == ctx.company_id,
                    GovernmentOfficial.id.in_(funcionario_ids),
                )
            ).scalars()
        }

    cargos = {}
    if cargo_ids:
        cargos = {
            c.id: c
            for c in db.execute(
                select(GovernmentPosition).where(
                    GovernmentPosition.company_id == ctx.company_id,
                    GovernmentPosition.id.in_(cargo_ids),
                )
            ).scalars()
        }

    actos_dict: dict[str, GovernmentAct] = {}
    if acto_ids:
        actos_rows = db.execute(
            select(GovernmentAct).where(
                GovernmentAct.company_id == ctx.company_id,
                GovernmentAct.id.in_(acto_ids),
            )
        ).scalars()
        actos_dict = {str(a.id): a for a in actos_rows}
        # Cargar actos revocadores referenciados por revocado_por_id
        revocador_ids = {
            a.revocado_por_id for a in actos_dict.values() if a.revocado_por_id
        }
        if revocador_ids:
            revocadores = db.execute(
                select(GovernmentAct).where(
                    GovernmentAct.company_id == ctx.company_id,
                    GovernmentAct.id.in_(revocador_ids),
                )
            ).scalars()
            for r in revocadores:
                actos_dict[str(r.id)] = r

    # Cargar cargos emisores de los actos que falten
    for acto in actos_dict.values():
        if acto.cargo_id and acto.cargo_id not in cargo_ids:
            cargo_ids.add(acto.cargo_id)

    if cargo_ids:
        cargos_rows = db.execute(
            select(GovernmentPosition).where(
                GovernmentPosition.company_id == ctx.company_id,
                GovernmentPosition.id.in_(cargo_ids),
            )
        ).scalars()
        for c in cargos_rows:
            cargos[c.id] = c

    unit_ids = {c.unit_id for c in cargos.values() if c.unit_id}
    structure_ids = {c.structure_id for c in cargos.values() if c.structure_id}

    unidades = {}
    if unit_ids:
        unidades = {
            u.id: u
            for u in db.execute(
                select(GovernmentUnit).where(
                    GovernmentUnit.company_id == ctx.company_id,
                    GovernmentUnit.id.in_(unit_ids),
                )
            ).scalars()
        }

    estructuras = {}
    if structure_ids:
        estructuras = {
            e.id: e
            for e in db.execute(
                select(GovernmentStructure).where(
                    GovernmentStructure.company_id == ctx.company_id,
                    GovernmentStructure.id.in_(structure_ids),
                )
            ).scalars()
        }

    eficacia_revocacion = {}
    for acto in actos_dict.values():
        if acto.revocado_por_id:
            revocador = actos_dict.get(str(acto.revocado_por_id)) if acto.revocado_por_id else None
            eficacia_revocacion[acto.id] = (
                revocador.fecha_eficacia if revocador else None
            )

    return _Contexto(
        funcionarios=funcionarios,
        cargos=cargos,
        unidades=unidades,
        estructuras=estructuras,
        actos=actos_dict,
        eficacia_revocacion=eficacia_revocacion,
    )


def situacion_en(a, acto, eficacia_revocacion: date | None, fecha: date) -> str:
    if a.status == "BORRADOR":
        return "BORRADOR"
    if a.status == "DESCARTADO":
        return "DESCARTADA"
    if acto and acto.status == "NULO":
        return "SIN_EFECTO"
    if (
        acto
        and acto.status == "REVOCADO"
        and (eficacia_revocacion is None or eficacia_revocacion <= fecha)
    ):
        return "SIN_EFECTO"
    if fecha < a.desde:
        return "FUTURA"
    if a.fin_efectivo and fecha > a.fin_efectivo:
        return "REVOCADA" if a.status == "REVOCADO" else "FINALIZADA"
    if a.hasta and fecha > a.hasta:
        return "VENCIDA"
    return "VIGENTE"


def _situacion_con_cargo(a, acto, efic, cargo, fecha: date) -> str:
    situacion = situacion_en(a, acto, efic, fecha)
    if situacion == "VIGENTE" and cargo and cargo.valid_to and fecha > cargo.valid_to:
        return "VENCIDA"
    return situacion


def _ref_funcionario(contexto: _Contexto, f_id: str | None) -> dict | None:
    if not f_id:
        return None
    f = contexto.funcionarios.get(f_id)
    if not f:
        return None
    return {
        "id": f.id,
        "codigo": f.codigo,
        "nombre": f.nombre,
        "documento": enmascarar_documento(f.tipo_documento, f.numero_documento),
    }


def _ref_cargo(contexto: _Contexto, c_id: str | None) -> dict | None:
    if not c_id:
        return None
    c = contexto.cargos.get(c_id)
    if not c:
        return None
    unidad = contexto.unidades.get(c.unit_id)
    estructura = contexto.estructuras.get(c.structure_id)
    return {
        "id": c.id,
        "codigo": c.code,
        "nombre": c.name,
        "unidad_id": c.unit_id,
        "unidad": unidad.name if unidad else "",
        "ejercicio": estructura.exercise if estructura else 0,
    }


def _ref_acto(contexto: _Contexto, a_id: str | None) -> dict | None:
    if not a_id:
        return None
    acto = contexto.actos.get(a_id)
    if not acto:
        return None
    emisor = contexto.cargos.get(acto.cargo_id)
    return {
        "id": acto.id,
        "tipo": acto.tipo,
        "numero": acto.numero,
        "fecha": acto.fecha,
        "status": acto.status,
        "fecha_eficacia": acto.fecha_eficacia,
        "medio": acto.medio,
        "emisor_cargo_id": acto.cargo_id,
        "emisor_cargo": emisor.name if emisor else "",
        "funcionario": acto.funcionario,
        "asunto": acto.asunto,
    }


def _competencia_de_cargo(c: dict) -> dict:
    return {
        "accion": c["accion"],
        "materia": c["materia"],
        "tipo_limite": c.get("tipo_limite"),
        "monto": str(c["monto"]) if c.get("monto") is not None else None,
        "moneda": c.get("moneda"),
    }


def _competencia_salida(c) -> dict:
    return {
        "accion": c.action,
        "materia": c.subject,
        "tipo_limite": c.limit_type,
        "monto": str(c.limit_amount) if c.limit_amount is not None else None,
        "moneda": c.limit_currency,
    }


def _resumen(a, contexto: _Contexto, fecha: date) -> dict:
    acto = contexto.actos.get(a.act_id)
    efic = contexto.eficacia_revocacion.get(a.act_id)
    figura = a.figura
    figura_info = FIGURAS.get(figura, {})
    cargo = contexto.cargos.get(a.position_id)
    situacion = _situacion_con_cargo(a, acto, efic, cargo, fecha)
    return {
        "id": a.id,
        "codigo": a.codigo,
        "figura": figura,
        "figura_etiqueta": figura_info.get("etiqueta", figura),
        "funcionario": _ref_funcionario(contexto, a.official_id),
        "cargo": _ref_cargo(contexto, a.position_id),
        "cargo_origen": _ref_cargo(contexto, a.cargo_origen_id),
        "acto": _ref_acto(contexto, a.act_id),
        "desde": a.desde,
        "hasta": a.hasta,
        "fin_efectivo": a.fin_efectivo,
        "status": a.status,
        "situacion": situacion,
        "version": a.version,
    }


def _resumen_de(a, db: Session, ctx: CompanyContext, fecha: date | None = None) -> dict:
    if fecha is None:
        fecha = hoy_de_negocio()
    contexto = _cargar_contexto(db, ctx, [a])
    return _resumen(a, contexto, fecha)


def _historia_salida(h, db: Session, ctx: CompanyContext, usuarios=None) -> dict:
    if usuarios is None:
        usuarios = _usuarios_por_ids(db, [h.created_by], ctx.tenant_id)
    actor = usuarios.get(h.created_by)
    return {
        "id": h.id,
        "tipo": h.tipo,
        "detalle": h.detalle,
        "actor": actor,
        "creado_en": _instante(h.created_at),
    }


def _cargar_cargos(db: Session, ctx: CompanyContext, contexto: _Contexto, cargo_ids: list[str]) -> None:
    """Añade cargos, unidades y estructuras faltantes al contexto."""
    faltantes = [c_id for c_id in cargo_ids if c_id and c_id not in contexto.cargos]
    if not faltantes:
        return

    cargos_rows = db.execute(
        select(GovernmentPosition).where(
            GovernmentPosition.company_id == ctx.company_id,
            GovernmentPosition.id.in_(faltantes),
        )
    ).scalars()
    for c in cargos_rows:
        contexto.cargos[c.id] = c

    unit_ids = {c.unit_id for c in contexto.cargos.values() if c.unit_id}
    unit_faltantes = [
        u_id for u_id in unit_ids if u_id and u_id not in contexto.unidades
    ]
    if unit_faltantes:
        unidades_rows = db.execute(
            select(GovernmentUnit).where(
                GovernmentUnit.company_id == ctx.company_id,
                GovernmentUnit.id.in_(unit_faltantes),
            )
        ).scalars()
        for u in unidades_rows:
            contexto.unidades[u.id] = u

    structure_ids = {
        c.structure_id for c in contexto.cargos.values() if c.structure_id
    }
    structure_faltantes = [
        s_id
        for s_id in structure_ids
        if s_id and s_id not in contexto.estructuras
    ]
    if structure_faltantes:
        structures_rows = db.execute(
            select(GovernmentStructure).where(
                GovernmentStructure.company_id == ctx.company_id,
                GovernmentStructure.id.in_(structure_faltantes),
            )
        ).scalars()
        for e in structures_rows:
            contexto.estructuras[e.id] = e


def _vigentes_en(
    db: Session, ctx: CompanyContext, cargo_ids: list[str], fecha: date
) -> tuple[dict, _Contexto]:
    if not cargo_ids:
        return {}, _cargar_contexto(db, ctx, [])
    asignaciones = db.execute(
        select(GovernmentAssignment).where(
            GovernmentAssignment.company_id == ctx.company_id,
            GovernmentAssignment.position_id.in_(cargo_ids),
            GovernmentAssignment.status.in_(["ACTIVO", "REVOCADO", "FINALIZADO"]),
            GovernmentAssignment.desde <= fecha,
        )
    ).scalars().all()
    contexto = _cargar_contexto(db, ctx, asignaciones)
    resultado: dict[str, dict] = {}
    for cargo_id in cargo_ids:
        resultado[cargo_id] = {"titular": None, "ejerce": None, "delegaciones": []}
        titulares = []
        temporales = []
        delegaciones = []
        for a in asignaciones:
            if a.position_id != cargo_id:
                continue
            acto = contexto.actos.get(a.act_id)
            efic = contexto.eficacia_revocacion.get(a.act_id)
            cargo = contexto.cargos.get(a.position_id)
            situacion = _situacion_con_cargo(a, acto, efic, cargo, fecha)
            if situacion != "VIGENTE":
                continue
            figura_info = FIGURAS.get(a.figura, {})
            grupo = figura_info.get("grupo")
            if grupo == "TITULARIDAD":
                titulares.append(a)
            elif grupo == "TEMPORAL":
                temporales.append(a)
            elif grupo == "DELEGACION":
                delegaciones.append(a)
        if titulares:
            titulares.sort(key=lambda x: x.desde, reverse=True)
            resultado[cargo_id]["titular"] = titulares[0]
        if temporales:
            temporales.sort(key=lambda x: x.desde, reverse=True)
            resultado[cargo_id]["ejerce"] = temporales[0]
        else:
            resultado[cargo_id]["ejerce"] = resultado[cargo_id]["titular"]
        delegaciones.sort(key=lambda x: x.desde, reverse=True)
        resultado[cargo_id]["delegaciones"] = delegaciones
    return resultado, contexto


def ocupacion_en(db: Session, ctx: CompanyContext, cargo_id: str, fecha: date) -> dict:
    ocupacion, _ = _vigentes_en(db, ctx, [cargo_id], fecha)
    return ocupacion.get(cargo_id, {"titular": None, "ejerce": None, "delegaciones": []})


def ocupaciones_de_funcionario(db: Session, ctx: CompanyContext, official_id: str, fecha: date) -> list[dict]:
    filas = db.scalars(
        select(GovernmentAssignment)
        .where(
            GovernmentAssignment.company_id == ctx.company_id,
            GovernmentAssignment.official_id == official_id,
            GovernmentAssignment.status.in_(["ACTIVO", "REVOCADO", "FINALIZADO"]),
            GovernmentAssignment.desde <= fecha,
        )
        .order_by(GovernmentAssignment.desde)
    ).all()
    resultado = []
    for fila in filas:
        detalle_ocupacion = detalle(db, ctx, str(fila.id), fecha)
        if detalle_ocupacion.get("situacion") == "VIGENTE":
            resultado.append(detalle_ocupacion)
    return resultado


def detalle(db: Session, ctx: CompanyContext, asignacion_id: str, fecha: date | None = None) -> dict:
    if fecha is None:
        fecha = hoy_de_negocio()
    a = _asignacion_de_empresa(db, ctx, asignacion_id)
    contexto = _cargar_contexto(db, ctx, [a])
    det = _resumen(a, contexto, fecha)
    det["fundamento"] = a.fundamento
    det["rendicion"] = a.rendicion
    det["maxima_autoridad"] = a.maxima_autoridad
    det["autorizacion_concejo"] = a.autorizacion_concejo
    det["declara_delegable"] = a.declara_delegable
    det["acto_revocacion"] = _ref_acto(contexto, str(a.revocation_act_id) if a.revocation_act_id else None)
    det["motivo_fin"] = a.motivo_fin
    usuarios_asignacion = _usuarios_por_ids(db, [a.created_by, a.activated_by, a.ended_by], ctx.tenant_id)
    det["registrada_por"] = usuarios_asignacion.get(str(a.created_by)) if a.created_by else None
    det["activada_por"] = usuarios_asignacion.get(str(a.activated_by)) if a.activated_by else None
    det["activada_en"] = _instante(a.activated_at) if a.activated_at else None
    det["terminada_por"] = usuarios_asignacion.get(str(a.ended_by)) if a.ended_by else None
    det["terminada_en"] = _instante(a.ended_at) if a.ended_at else None
    competencias = _competencias_de(db, ctx, str(a.id))
    det["competencias"] = [_competencia_salida(c) for c in competencias]

    historia_rows = db.execute(
        select(GovernmentAssignmentHistory)
        .where(GovernmentAssignmentHistory.assignment_id == a.id)
        .order_by(GovernmentAssignmentHistory.created_at.asc())
    ).scalars().all()
    usuarios = _usuarios_por_ids(
        db, [h.created_by for h in historia_rows if h.created_by], ctx.tenant_id
    )
    det["historia"] = [_historia_salida(h, db, ctx, usuarios) for h in historia_rows]

    avocaciones = []
    for h in historia_rows:
        if h.tipo == "AVOCADA" and h.detalle and h.detalle.get("acto_id"):
            acto = _acto_de_empresa(db, ctx, h.detalle["acto_id"])
            if acto:
                contexto.actos[acto.id] = acto
                _cargar_cargos(db, ctx, contexto, [acto.cargo_id])
                avocaciones.append(
                    {
                        "id": h.id,
                        "asunto": h.detalle.get("asunto"),
                        "acto": _ref_acto(contexto, str(acto.id)),
                        "actor": usuarios.get(str(h.created_by)) if h.created_by else None,
                        "creado_en": _instante(h.created_at),
                    }
                )
    det["avocaciones"] = avocaciones

    situacion = det["situacion"]
    figura_info = FIGURAS.get(a.figura, {})
    grupo = figura_info.get("grupo")
    ejerce = False
    if situacion == "VIGENTE":
        if grupo == "DELEGACION":
            ejerce = True
        else:
            ocupacion, _ = _vigentes_en(db, ctx, [a.position_id], fecha)
            ejerce_asignacion = ocupacion.get(a.position_id, {}).get("ejerce")
            if ejerce_asignacion is not None and ejerce_asignacion.id == a.id:
                ejerce = True
    det["ejerce"] = ejerce

    if not ejerce:
        det["autoridad"] = []
    elif grupo == "DELEGACION":
        det["autoridad"] = [_competencia_salida(c) for c in competencias]
    else:
        cargo = contexto.cargos.get(str(a.position_id)) if a.position_id else None
        if cargo is None:
            det["autoridad"] = []
        else:
            autoridad = competencias_en_vigor(db, cargo, fecha)
            det["autoridad"] = [_competencia_de_cargo(c) for c in autoridad]

    return det


def _consulta_asignaciones(
    ctx: CompanyContext,
    figura: str | None,
    estado: str | None,
    funcionario_id: str | None,
    cargo_id: str | None,
):
    query = select(GovernmentAssignment).where(
        GovernmentAssignment.company_id == ctx.company_id
    )
    if figura:
        query = query.where(GovernmentAssignment.figura == figura)
    if estado:
        query = query.where(GovernmentAssignment.status == estado)
    if funcionario_id:
        query = query.where(GovernmentAssignment.official_id == funcionario_id)
    if cargo_id:
        query = query.where(GovernmentAssignment.position_id == cargo_id)
    return query


def listar(
    db: Session,
    ctx: CompanyContext,
    figura: str | None,
    estado: str | None,
    funcionario_id: str | None,
    cargo_id: str | None,
    fecha: date | None,
    pagina: int,
    por_pagina: int,
) -> dict:
    if fecha is None:
        fecha = hoy_de_negocio()
    query = _consulta_asignaciones(ctx, figura, estado, funcionario_id, cargo_id)
    query = query.order_by(
        GovernmentAssignment.desde.desc(), GovernmentAssignment.codigo
    )
    total = db.execute(
        select(func.count()).select_from(query.subquery())
    ).scalar_one()
    offset = (pagina - 1) * por_pagina
    rows = db.execute(query.offset(offset).limit(por_pagina)).scalars().all()
    contexto = _cargar_contexto(db, ctx, rows)
    items = [_resumen(a, contexto, fecha) for a in rows]
    return {
        "items": items,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "fecha": fecha,
    }


def _celda(valor) -> str:
    if valor is None:
        return ""
    texto = str(valor)
    if texto and texto[0] in "=+-@\t\r":
        return "'" + texto
    return texto


def exportar_csv(
    db: Session,
    ctx: CompanyContext,
    figura: str | None,
    estado: str | None,
    funcionario_id: str | None,
    cargo_id: str | None,
    fecha: date | None,
) -> tuple[str, bytes]:
    if fecha is None:
        fecha = hoy_de_negocio()
    query = _consulta_asignaciones(ctx, figura, estado, funcionario_id, cargo_id)
    query = query.order_by(
        GovernmentAssignment.desde.desc(), GovernmentAssignment.codigo
    )
    rows = db.execute(query).scalars().all()
    contexto = _cargar_contexto(db, ctx, rows)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "codigo", "figura", "funcionario", "cargo", "unidad",
        "acto", "emisor", "desde", "hasta", "fin_efectivo", "estado", "situacion",
    ])
    for a in rows:
        resumen = _resumen(a, contexto, fecha)
        funcionario_ref = resumen.get("funcionario") or {}
        cargo_ref = resumen.get("cargo") or {}
        acto_ref = resumen.get("acto") or {}
        writer.writerow([
            _celda(resumen.get("codigo")),
            _celda(resumen.get("figura_etiqueta")),
            _celda(funcionario_ref.get("nombre")),
            _celda(cargo_ref.get("nombre")),
            _celda(cargo_ref.get("unidad")),
            _celda(acto_ref.get("numero")),
            _celda(acto_ref.get("emisor_cargo")),
            _celda(resumen.get("desde")),
            _celda(resumen.get("hasta")),
            _celda(resumen.get("fin_efectivo")),
            _celda(resumen.get("status")),
            _celda(resumen.get("situacion")),
        ])
    total = len(rows)
    _auditar(
        db,
        ctx,
        "GOV_ASSIGNMENTS_EXPORTED",
        ENTIDAD_ASIGNACION,
        None,
        None,
        {"total": total},
    )
    content = output.getvalue().encode("utf-8")
    nombre = f"ocupacion-{fecha.isoformat()}.csv"
    return nombre, content


def listar_ocupacion(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    fecha: date | None,
    texto: str | None,
    pagina: int,
    por_pagina: int,
) -> dict:
    if fecha is None:
        fecha = hoy_de_negocio()
    estructura = db.execute(
        select(GovernmentStructure).where(
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.exercise == ejercicio,
        )
    ).scalars().first()
    if not estructura:
        return {
            "ejercicio": ejercicio,
            "fecha": fecha,
            "items": [],
            "total": 0,
            "pagina": pagina,
            "por_pagina": por_pagina,
        }
    query = select(GovernmentPosition).where(
        GovernmentPosition.company_id == ctx.company_id,
        GovernmentPosition.structure_id == estructura.id,
        GovernmentPosition.status.in_(["VIGENTE", "INACTIVO"]),
    )
    if texto:
        query = query.where(
            or_(
                GovernmentPosition.code.ilike(f"%{texto}%"),
                GovernmentPosition.name.ilike(f"%{texto}%"),
            )
        )
    query = query.order_by(GovernmentPosition.code)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    offset = (pagina - 1) * por_pagina
    cargos = db.execute(query.offset(offset).limit(por_pagina)).scalars().all()
    cargo_ids = [str(c.id) for c in cargos]
    ocupacion_dict, contexto = _vigentes_en(db, ctx, cargo_ids, fecha)
    _cargar_cargos(db, ctx, contexto, cargo_ids)
    items = []
    for cargo in cargos:
        ocupacion = ocupacion_dict.get(
            cargo.id, {"titular": None, "ejerce": None, "delegaciones": []}
        )
        titular = ocupacion.get("titular")
        ejerce = ocupacion.get("ejerce")
        delegaciones = ocupacion.get("delegaciones", [])
        items.append(
            {
                "cargo": _ref_cargo(contexto, str(cargo.id)),
                "titular": _resumen(titular, contexto, fecha) if titular else None,
                "ejerce": _resumen(ejerce, contexto, fecha) if ejerce else None,
                "vacante": ejerce is None,
                "delegaciones": len(delegaciones),
            }
        )
    return {
        "ejercicio": ejercicio,
        "fecha": fecha,
        "items": items,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
    }


def cargo_ocupacion(
    db: Session, ctx: CompanyContext, cargo_id: str, fecha: date | None
) -> dict:
    if fecha is None:
        fecha = hoy_de_negocio()
    cargo = _cargo_de_empresa(db, ctx, cargo_id, bloquear=False)
    ocupacion_dict, contexto_vigentes = _vigentes_en(db, ctx, [cargo_id], fecha)
    ocupacion = ocupacion_dict.get(
        cargo_id, {"titular": None, "ejerce": None, "delegaciones": []}
    )
    historial_rows = db.execute(
        select(GovernmentAssignment).where(
            GovernmentAssignment.company_id == ctx.company_id,
            GovernmentAssignment.position_id == cargo_id,
            GovernmentAssignment.status.notin_(["BORRADOR", "DESCARTADO"]),
        )
    ).scalars().all()
    contexto = _cargar_contexto(
        db, ctx, list(historial_rows)
    )
    # Asegurar el cargo actual en el contexto
    _cargar_cargos(db, ctx, contexto, [cargo_id])
    # Fusionar contexto de vigentes para no perder sus relaciones
    for k, v in contexto_vigentes.funcionarios.items():
        contexto.funcionarios[k] = v
    for k, v in contexto_vigentes.cargos.items():
        contexto.cargos[k] = v
    for k, v in contexto_vigentes.unidades.items():
        contexto.unidades[k] = v
    for k, v in contexto_vigentes.estructuras.items():
        contexto.estructuras[k] = v
    for k, v in contexto_vigentes.actos.items():
        contexto.actos[k] = v
    for k, v in contexto_vigentes.eficacia_revocacion.items():
        contexto.eficacia_revocacion[k] = v

    historial = [
        _resumen(a, contexto, fecha)
        for a in sorted(historial_rows, key=lambda x: x.desde, reverse=True)
    ]
    autoridad = competencias_en_vigor(db, cargo, fecha)
    competencias = [_competencia_de_cargo(c) for c in autoridad]
    titular = ocupacion.get("titular")
    ejerce = ocupacion.get("ejerce")
    delegaciones = ocupacion.get("delegaciones", [])
    return {
        "cargo": _ref_cargo(contexto, cargo_id),
        "fecha": fecha,
        "titular": _resumen(titular, contexto, fecha) if titular else None,
        "ejerce": _resumen(ejerce, contexto, fecha) if ejerce else None,
        "vacante": ejerce is None,
        "delegaciones": [
            _resumen(d, contexto, fecha) for d in delegaciones
        ],
        "competencias": competencias,
        "historial": historial,
    }


def _nombre_unidad(contexto: _Contexto, unidad_id: str | None) -> str:
    unidad = contexto.unidades.get(str(unidad_id)) if unidad_id else None
    return unidad.name if unidad else ""


def opciones(db: Session, ctx: CompanyContext, ejercicio: int) -> dict:
    hoy = hoy_de_negocio()
    funcionarios = db.execute(
        select(GovernmentOfficial).where(
            GovernmentOfficial.company_id == ctx.company_id,
            GovernmentOfficial.estado == "ACTIVO",
        )
    ).scalars().all()

    estructura = db.execute(
        select(GovernmentStructure).where(
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.exercise == ejercicio,
        )
    ).scalars().first()
    cargos: list[GovernmentPosition] = []
    if estructura:
        cargos = list(db.execute(
            select(GovernmentPosition).where(
                GovernmentPosition.company_id == ctx.company_id,
                GovernmentPosition.structure_id == estructura.id,
                GovernmentPosition.status == "VIGENTE",
            )
        ).scalars().all())

    actos = db.execute(
        select(GovernmentAct)
        .where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.status == "EFICAZ",
        )
        .order_by(GovernmentAct.fecha.desc())
        .limit(200)
    ).scalars().all()

    contexto = _cargar_contexto(db, ctx, [])
    cargo_ids = [str(c.id) for c in cargos]
    _cargar_cargos(db, ctx, contexto, cargo_ids)
    acto_cargo_ids = [str(a.cargo_id) for a in actos if a.cargo_id]
    _cargar_cargos(db, ctx, contexto, acto_cargo_ids)
    for acto in actos:
        contexto.actos[acto.id] = acto

    cargo_opciones = []
    for c in cargos:
        competencias = competencias_en_vigor(db, c, hoy)
        cargo_opciones.append(
            {
                "id": c.id,
                "codigo": c.code,
                "nombre": c.name,
                "unidad": _nombre_unidad(contexto, c.unit_id),
                "ejercicio": ejercicio,
                "competencias": [_competencia_de_cargo(comp) for comp in competencias],
            }
        )

    return {
        "funcionarios": [
            {"id": f.id, "codigo": f.codigo, "nombre": f.nombre}
            for f in funcionarios
        ],
        "cargos": cargo_opciones,
        "actos": [_ref_acto(contexto, str(a.id) if a.id else None) for a in actos],
    }
