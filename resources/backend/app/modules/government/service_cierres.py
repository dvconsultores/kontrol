"""Servicio de políticas de cierre de Gobierno (CTL-10, GOV-CTL-012)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.government.models import (
    GovernmentAct,
    GovernmentClosureControl,
    GovernmentClosurePolicy,
    GovernmentClosurePolicyHistory,
    GovernmentFinding,
)
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.shared.audit import record_audit, record_audit_after_rollback
from app.shared.clock import hoy_de_negocio, limites_del_dia_utc

ENTIDAD_POLITICA = "GovernmentClosurePolicy"
ACCION_BLOQUEO = "GOV_MATERIAL_CLOSE_BLOCKED"
ACCION_PERMITIDO = "GOV_MATERIAL_CLOSE_ALLOWED"

ACCIONES_CIERRE = {
    "ORG02_CERRAR_ESTRUCTURA": "Cerrar estructura",
    "TRE02_CERRAR_PROGRAMA": "Cerrar programa",
}

TIPOS_CONTROL = {
    "HALLAZGOS_ABIERTOS": {
        "etiqueta": "Hallazgos abiertos",
        "requiere_riesgo": True,
    },
    "ACTOS_SIN_EFICACIA": {
        "etiqueta": "Actos sin eficacia",
        "requiere_riesgo": False,
    },
}

RIESGOS = ["ALTO", "MEDIO", "BAJO"]
ORDEN_RIESGO = {"ALTO": 3, "MEDIO": 2, "BAJO": 1}


def _invalida(mensaje: str) -> KontrolError:
    return KontrolError(code="GOV_CLOSURE_POLICY_INVALID", message=mensaje, status_code=422)


def catalogo() -> dict:
    return {
        "acciones": [
            {"codigo": codigo, "etiqueta": etiqueta}
            for codigo, etiqueta in ACCIONES_CIERRE.items()
        ],
        "tipos": [
            {
                "codigo": codigo,
                "etiqueta": datos["etiqueta"],
                "requiere_riesgo": datos["requiere_riesgo"],
            }
            for codigo, datos in TIPOS_CONTROL.items()
        ],
    }


def _politica_de_empresa(
    db: Session, ctx: CompanyContext, politica_id: str, bloquear: bool = False
) -> GovernmentClosurePolicy:
    consulta = select(GovernmentClosurePolicy).where(
        GovernmentClosurePolicy.id == politica_id,
        GovernmentClosurePolicy.tenant_id == ctx.tenant_id,
        GovernmentClosurePolicy.company_id == ctx.company_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    politica = db.execute(consulta).scalar_one_or_none()
    if politica is None:
        raise NotFoundError("GOV_CLOSURE_POLICY_NOT_FOUND", "La política no existe en este ente")
    return politica


def _para_escribir(
    db: Session,
    ctx: CompanyContext,
    politica_id: str,
    version: int | None,
) -> GovernmentClosurePolicy:
    if version is None:
        raise KontrolError(
            code="GOV_CLOSURE_POLICY_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión de la política",
            status_code=428,
        )
    politica = _politica_de_empresa(db, ctx, politica_id, bloquear=True)
    if politica.version != version:
        raise ConflictError(
            "GOV_CLOSURE_POLICY_STALE",
            "La política cambió desde que la abrió; recárguela",
            details={"version_actual": politica.version},
        )
    return politica


def _exigir_estado(politica: GovernmentClosurePolicy, estado: str) -> None:
    if politica.estado != estado:
        raise ConflictError(
            "GOV_CLOSURE_POLICY_INVALID_STATE", f"La política debe estar en estado {estado}"
        )


def _politica_efectiva_bloqueada(
    db: Session, ctx: CompanyContext, accion_cierre: str
) -> GovernmentClosurePolicy | None:
    hoy = hoy_de_negocio()
    consulta = (
        select(GovernmentClosurePolicy)
        .where(
            GovernmentClosurePolicy.tenant_id == ctx.tenant_id,
            GovernmentClosurePolicy.company_id == ctx.company_id,
            GovernmentClosurePolicy.accion_cierre == accion_cierre,
            GovernmentClosurePolicy.estado == "VIGENTE",
            GovernmentClosurePolicy.vigente_desde <= hoy,
            or_(
                GovernmentClosurePolicy.vigente_hasta.is_(None),
                GovernmentClosurePolicy.vigente_hasta >= hoy,
            ),
        )
        .order_by(GovernmentClosurePolicy.codigo)
        .with_for_update(read=True)
    )
    return db.execute(consulta).scalars().first()


def _controles_de_politica(db: Session, ctx: CompanyContext, politica_id: str) -> list[GovernmentClosureControl]:
    return list(
        db.execute(
            select(GovernmentClosureControl)
            .where(
                GovernmentClosureControl.tenant_id == ctx.tenant_id,
                GovernmentClosureControl.company_id == ctx.company_id,
                GovernmentClosureControl.policy_id == politica_id,
            )
            .order_by(GovernmentClosureControl.tipo)
        )
        .scalars()
        .all()
    )


def _historia(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentClosurePolicy,
    evento: str,
    detalle: dict | None,
) -> None:
    db.add(
        GovernmentClosurePolicyHistory(
            policy_id=str(politica.id),
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            evento=evento,
            detalle=detalle,
            usuario=ctx.user_id,
            instante=datetime.now(UTC),
        )
    )


def _auditar(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentClosurePolicy,
    accion: str,
    after: dict,
) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD_POLITICA,
        entity_id=str(politica.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _contar_hallazgos_abiertos(db: Session, ctx: CompanyContext, riesgo_minimo: str) -> int:
    minimo = ORDEN_RIESGO[riesgo_minimo]
    riesgos_incluidos = [riesgo for riesgo in RIESGOS if ORDEN_RIESGO[riesgo] >= minimo]
    return (
        db.execute(
            select(func.count())
            .select_from(GovernmentFinding)
            .where(
                GovernmentFinding.tenant_id == ctx.tenant_id,
                GovernmentFinding.company_id == ctx.company_id,
                GovernmentFinding.estado != "CERRADO",
                GovernmentFinding.riesgo.in_(riesgos_incluidos),
            )
        )
        .scalar_one_or_none()
        or 0
    )


def _contar_actos_sin_eficacia(db: Session, ctx: CompanyContext, ejercicio: int) -> int:
    return (
        db.execute(
            select(func.count())
            .select_from(GovernmentAct)
            .where(
                GovernmentAct.company_id == ctx.company_id,
                GovernmentAct.status == "EMITIDO",
                GovernmentAct.fecha >= date(ejercicio, 1, 1),
                GovernmentAct.fecha <= date(ejercicio, 12, 31),
            )
        )
        .scalar_one_or_none()
        or 0
    )


def _muestra_hallazgos(db: Session, ctx: CompanyContext, riesgo_minimo: str, limite: int) -> list[dict]:
    minimo = ORDEN_RIESGO[riesgo_minimo]
    riesgos_incluidos = [riesgo for riesgo in RIESGOS if ORDEN_RIESGO[riesgo] >= minimo]
    hallazgos = db.execute(
        select(GovernmentFinding)
        .where(
            GovernmentFinding.tenant_id == ctx.tenant_id,
            GovernmentFinding.company_id == ctx.company_id,
            GovernmentFinding.estado != "CERRADO",
            GovernmentFinding.riesgo.in_(riesgos_incluidos),
        )
        .order_by(GovernmentFinding.codigo)
        .limit(limite)
    ).scalars()
    return [
        {
            "codigo": h.codigo,
            "titulo": h.titulo,
            "ruta": f"/gobierno/hallazgos/{h.id}",
        }
        for h in hallazgos
    ]


def _muestra_actos(db: Session, ctx: CompanyContext, ejercicio: int, limite: int) -> list[dict]:
    actos = db.execute(
        select(GovernmentAct)
        .where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.status == "EMITIDO",
            GovernmentAct.fecha >= date(ejercicio, 1, 1),
            GovernmentAct.fecha <= date(ejercicio, 12, 31),
        )
        .order_by(GovernmentAct.numero)
        .limit(limite)
    ).scalars()
    return [
        {
            "numero": a.numero,
            "asunto": a.asunto,
            "ruta": f"/gobierno/actos/{a.id}",
        }
        for a in actos
    ]


def _resultados_controles(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentClosurePolicy,
    accion_cierre: str,
    objeto_tipo: str,
    objeto_id: str,
    objeto_codigo: str,
    ejercicio: int,
) -> tuple[list[dict], int]:
    controles = _controles_de_politica(db, ctx, str(politica.id))
    resultados: list[dict] = []
    total_pendientes = 0
    for control in controles:
        pendientes = 0
        muestra: list[dict] = []
        ruta_lista = ""
        if control.tipo == "HALLAZGOS_ABIERTOS":
            pendientes = _contar_hallazgos_abiertos(db, ctx, cast(str, control.riesgo_minimo))
            if pendientes > 0:
                muestra = _muestra_hallazgos(db, ctx, cast(str, control.riesgo_minimo), 5)
                ruta_lista = "/gobierno/hallazgos"
        elif control.tipo == "ACTOS_SIN_EFICACIA":
            pendientes = _contar_actos_sin_eficacia(db, ctx, ejercicio)
            if pendientes > 0:
                muestra = _muestra_actos(db, ctx, ejercicio, 5)
                ruta_lista = "/gobierno/actos"
        if pendientes > 0:
            total_pendientes += pendientes
            resultados.append(
                {
                    "tipo": control.tipo,
                    "etiqueta": TIPOS_CONTROL[control.tipo]["etiqueta"],
                    "materialidad": control.materialidad,
                    "pendientes": pendientes,
                    "muestra": muestra,
                    "ruta_lista": ruta_lista,
                }
            )
    return resultados, total_pendientes


def evaluar_cierre(
    db: Session,
    ctx: CompanyContext,
    accion: str,
    objeto_tipo: str,
    objeto_id: str,
    objeto_codigo: str,
    ejercicio: int,
) -> None:
    """Guarda de cierre material (CTL-10, spec §5). Nunca concede autoridad: solo puede impedir."""
    politica = _politica_efectiva_bloqueada(db, ctx, accion)
    if politica is None:
        return

    controles_pendientes, total_pendientes = _resultados_controles(
        db, ctx, politica, accion, objeto_tipo, objeto_id, objeto_codigo, ejercicio
    )

    if total_pendientes == 0:
        _auditar(
            db,
            ctx,
            politica,
            ACCION_PERMITIDO,
            {
                "politica_codigo": politica.codigo,
                "politica_version": politica.version,
                "accion_cierre": accion,
                "objeto_tipo": objeto_tipo,
                "objeto_id": objeto_id,
                "objeto_codigo": objeto_codigo,
                "ejercicio": ejercicio,
            },
        )
        return

    politica_id, politica_codigo, politica_version, politica_nombre = (
        str(politica.id),
        politica.codigo,
        politica.version,
        politica.nombre,
    )
    detalles = {
        "politica_codigo": politica_codigo,
        "politica_nombre": politica_nombre,
        "proceso": accion,
        "objeto_codigo": objeto_codigo,
        "total": total_pendientes,
        "dueno": "Control Interno",
        "controles": controles_pendientes,
    }
    record_audit_after_rollback(
        db,
        action=ACCION_BLOQUEO,
        entity_type=ENTIDAD_POLITICA,
        entity_id=politica_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "politica_codigo": politica_codigo,
            "politica_version": politica_version,
            "accion_cierre": accion,
            "objeto_tipo": objeto_tipo,
            "objeto_id": objeto_id,
            "objeto_codigo": objeto_codigo,
            "ejercicio": ejercicio,
            "controles": [
                {"tipo": c["tipo"], "pendientes": c["pendientes"]}
                for c in controles_pendientes
            ],
            "total": total_pendientes,
        },
    )
    raise ConflictError(
        "GOV_MATERIAL_CLOSE_BLOCKED",
        f"La operación está bloqueada por controles de cierre: política {politica_codigo} · {politica_nombre}",
        details=detalles,
    )


def _siguiente_codigo(db: Session, ctx: CompanyContext) -> str:
    n = db.execute(
        select(func.count())
        .select_from(GovernmentClosurePolicy)
        .where(
            GovernmentClosurePolicy.tenant_id == ctx.tenant_id,
            GovernmentClosurePolicy.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    return f"PC-{(n or 0) + 1:03d}"


def _efectiva_hoy(politica: GovernmentClosurePolicy, hoy: date) -> bool:
    return (
        politica.estado == "VIGENTE"
        and politica.vigente_desde <= hoy
        and (politica.vigente_hasta is None or hoy <= politica.vigente_hasta)
    )


def _resumen(politica: GovernmentClosurePolicy, hoy: date) -> dict:
    return {
        "id": str(politica.id),
        "codigo": politica.codigo,
        "nombre": politica.nombre,
        "accion_cierre": politica.accion_cierre,
        "accion_cierre_etiqueta": ACCIONES_CIERRE[politica.accion_cierre],
        "fundamento": politica.fundamento,
        "estado": politica.estado,
        "vigente_desde": politica.vigente_desde,
        "vigente_hasta": politica.vigente_hasta,
        "efectiva_hoy": _efectiva_hoy(politica, hoy),
        "version": politica.version,
        "activada_por": politica.activada_por,
        "activada_en": _instante(politica.activada_en) if politica.activada_en is not None else None,
        "retirada_por": politica.retirada_por,
        "retirada_en": _instante(politica.retirada_en) if politica.retirada_en is not None else None,
        "motivo_retiro": politica.motivo_retiro,
    }


def detalle(db: Session, ctx: CompanyContext, politica_id: str) -> dict:
    politica = _politica_de_empresa(db, ctx, politica_id)
    controles = _controles_de_politica(db, ctx, politica_id)
    historias = (
        db.execute(
            select(GovernmentClosurePolicyHistory)
            .where(
                GovernmentClosurePolicyHistory.tenant_id == ctx.tenant_id,
                GovernmentClosurePolicyHistory.company_id == ctx.company_id,
                GovernmentClosurePolicyHistory.policy_id == politica_id,
            )
            .order_by(GovernmentClosurePolicyHistory.instante, GovernmentClosurePolicyHistory.id)
        )
        .scalars()
        .all()
    )
    ids_usuarios = [
        politica.created_by,
        politica.activada_por,
        politica.retirada_por,
    ] + [h.usuario for h in historias]
    usuarios = _usuarios_por_ids(db, ids_usuarios, ctx.tenant_id)

    def _nombre(usuario_id: Any) -> str | None:
        return usuarios.get(str(usuario_id)) if usuario_id is not None else None

    return {
        **_resumen(politica, hoy_de_negocio()),
        "controles": [
            {
                "id": str(c.id),
                "tipo": c.tipo,
                "tipo_etiqueta": TIPOS_CONTROL[c.tipo]["etiqueta"],
                "riesgo_minimo": c.riesgo_minimo,
                "materialidad": c.materialidad,
            }
            for c in controles
        ],
        "creada_por": _nombre(politica.created_by),
        "creada_en": _instante(politica.created_at),
        "activada_por": _nombre(politica.activada_por),
        "activada_en": _instante(politica.activada_en) if politica.activada_en is not None else None,
        "retirada_por": _nombre(politica.retirada_por),
        "retirada_en": _instante(politica.retirada_en) if politica.retirada_en is not None else None,
        "motivo_retiro": politica.motivo_retiro,
        "historia": [
            {
                "evento": h.evento,
                "detalle": h.detalle,
                "usuario": _nombre(h.usuario),
                "instante": _instante(h.instante),
            }
            for h in historias
        ],
    }


def listar(
    db: Session,
    ctx: CompanyContext,
    accion_cierre: str | None,
    estado: str | None,
    pagina: int,
    tamano: int,
) -> dict:
    condiciones = [
        GovernmentClosurePolicy.tenant_id == ctx.tenant_id,
        GovernmentClosurePolicy.company_id == ctx.company_id,
    ]
    if accion_cierre is not None:
        condiciones.append(GovernmentClosurePolicy.accion_cierre == accion_cierre)
    if estado is not None:
        condiciones.append(GovernmentClosurePolicy.estado == estado)
    total = (
        db.execute(select(func.count()).select_from(GovernmentClosurePolicy).where(*condiciones))
        .scalar_one_or_none()
        or 0
    )
    politicas = db.execute(
        select(GovernmentClosurePolicy)
        .where(*condiciones)
        .order_by(GovernmentClosurePolicy.codigo.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).scalars()
    hoy = hoy_de_negocio()
    conteos = (
        db.execute(
            select(GovernmentClosurePolicy.estado, func.count())
            .where(
                GovernmentClosurePolicy.tenant_id == ctx.tenant_id,
                GovernmentClosurePolicy.company_id == ctx.company_id,
            )
            .group_by(GovernmentClosurePolicy.estado)
        )
        .all()
    )
    conteos_por_estado = {estado_contado: total_contado for estado_contado, total_contado in conteos}
    return {
        "items": [_resumen(p, hoy) for p in politicas],
        "total": total,
        "resumen": {
            "borradores": conteos_por_estado.get("BORRADOR", 0),
            "vigentes": conteos_por_estado.get("VIGENTE", 0),
            "retiradas": conteos_por_estado.get("RETIRADA", 0),
        },
    }


def crear(db: Session, ctx: CompanyContext, datos: Any) -> GovernmentClosurePolicy:
    if datos.accion_cierre not in ACCIONES_CIERRE:
        raise _invalida("La acción de cierre no pertenece al catálogo")
    if datos.vigente_hasta and datos.vigente_hasta < datos.vigente_desde:
        raise _invalida("La vigencia final no puede ser anterior a la inicial")
    politica = GovernmentClosurePolicy(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        codigo=_siguiente_codigo(db, ctx),
        nombre=datos.nombre,
        accion_cierre=datos.accion_cierre,
        fundamento=datos.fundamento,
        estado="BORRADOR",
        vigente_desde=datos.vigente_desde,
        vigente_hasta=datos.vigente_hasta,
        version=1,
        created_by=ctx.user_id,
    )
    db.add(politica)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_CLOSURE_POLICY_CONFLICT", "Otra política se registró al mismo tiempo; vuelva a intentarlo"
        ) from None
    _historia(db, ctx, politica, "CREADA", None)
    _auditar(
        db,
        ctx,
        politica,
        "GOV_CLOSURE_POLICY_CREATED",
        {
            "codigo": politica.codigo,
            "accion_cierre": politica.accion_cierre,
            "vigente_desde": politica.vigente_desde.isoformat(),
            "vigente_hasta": politica.vigente_hasta.isoformat() if politica.vigente_hasta else None,
        },
    )
    db.flush()
    return politica


def editar(
    db: Session,
    ctx: CompanyContext,
    politica_id: str,
    version: int | None,
    cambios: Any,
) -> GovernmentClosurePolicy:
    politica = _para_escribir(db, ctx, politica_id, version)
    _exigir_estado(politica, "BORRADOR")
    valores = cambios.model_dump(exclude_unset=True)
    nuevos = {
        "nombre": valores.get("nombre", politica.nombre),
        "fundamento": valores.get("fundamento", politica.fundamento),
        "vigente_desde": valores.get("vigente_desde", politica.vigente_desde),
        "vigente_hasta": valores.get("vigente_hasta", politica.vigente_hasta),
    }
    if nuevos["vigente_hasta"] and nuevos["vigente_hasta"] < nuevos["vigente_desde"]:
        raise _invalida("La vigencia final no puede ser anterior a la inicial")
    cambiados = sorted(c for c, v in nuevos.items() if v != getattr(politica, c))
    for campo, valor in nuevos.items():
        setattr(politica, campo, valor)
    politica.version += 1
    _historia(db, ctx, politica, "ACTUALIZADA", {"campos": cambiados})
    _auditar(db, ctx, politica, "GOV_CLOSURE_POLICY_UPDATED", {"codigo": politica.codigo, "campos": cambiados})
    db.flush()
    return politica


def _validar_control(control: GovernmentClosureControl) -> None:
    if control.tipo not in TIPOS_CONTROL:
        raise _invalida("El tipo de control no pertenece al catálogo")
    if TIPOS_CONTROL[control.tipo]["requiere_riesgo"] and control.riesgo_minimo not in RIESGOS:
        raise _invalida("Debe indicar un riesgo mínimo para hallazgos abiertos")
    if not TIPOS_CONTROL[control.tipo]["requiere_riesgo"] and control.riesgo_minimo is not None:
        raise _invalida("Este tipo de control no admite riesgo mínimo")


def anadir_control(
    db: Session,
    ctx: CompanyContext,
    politica_id: str,
    version: int | None,
    datos: Any,
) -> GovernmentClosurePolicy:
    politica = _para_escribir(db, ctx, politica_id, version)
    _exigir_estado(politica, "BORRADOR")
    control = GovernmentClosureControl(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        policy_id=str(politica.id),
        tipo=datos.tipo,
        riesgo_minimo=datos.riesgo_minimo,
        materialidad=datos.materialidad,
    )
    _validar_control(control)
    db.add(control)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _invalida("Ya existe un control de ese tipo en la política") from None
    politica.version += 1
    _historia(db, ctx, politica, "CONTROL_ANADIDO", {"tipo": datos.tipo})
    _auditar(db, ctx, politica, "GOV_CLOSURE_POLICY_CONTROL_ADDED", {"tipo": datos.tipo})
    db.flush()
    return politica


def quitar_control(
    db: Session,
    ctx: CompanyContext,
    politica_id: str,
    control_id: str,
    version: int | None,
) -> GovernmentClosurePolicy:
    politica = _para_escribir(db, ctx, politica_id, version)
    _exigir_estado(politica, "BORRADOR")
    control = db.execute(
        select(GovernmentClosureControl).where(
            GovernmentClosureControl.id == control_id,
            GovernmentClosureControl.tenant_id == ctx.tenant_id,
            GovernmentClosureControl.company_id == ctx.company_id,
            GovernmentClosureControl.policy_id == str(politica.id),
        )
    ).scalar_one_or_none()
    if control is None:
        raise NotFoundError("GOV_CLOSURE_CONTROL_NOT_FOUND", "El control no existe en esta política")
    db.delete(control)
    politica.version += 1
    _historia(db, ctx, politica, "CONTROL_RETIRADO", {"tipo": control.tipo})
    _auditar(db, ctx, politica, "GOV_CLOSURE_POLICY_CONTROL_REMOVED", {"tipo": control.tipo})
    db.flush()
    return politica


def activar(
    db: Session,
    ctx: CompanyContext,
    politica_id: str,
    version: int | None,
) -> GovernmentClosurePolicy:
    politica = _para_escribir(db, ctx, politica_id, version)
    _exigir_estado(politica, "BORRADOR")
    controles = _controles_de_politica(db, ctx, politica_id)
    if not controles:
        raise _invalida("Debe añadir al menos un control para activar la política")

    duplicada = db.execute(
        select(GovernmentClosurePolicy).where(
            GovernmentClosurePolicy.tenant_id == ctx.tenant_id,
            GovernmentClosurePolicy.company_id == ctx.company_id,
            GovernmentClosurePolicy.accion_cierre == politica.accion_cierre,
            GovernmentClosurePolicy.estado == "VIGENTE",
            GovernmentClosurePolicy.id != politica.id,
        )
    ).scalar_one_or_none()
    if duplicada is not None:
        raise ConflictError(
            "GOV_CLOSURE_POLICY_ACTIVE_EXISTS",
            "Ya hay una política vigente para esa acción de cierre",
        )
    evaluar_antes_de_actuar(db, ctx, "CTL10_ACTIVAR", ENTIDAD_POLITICA, politica_id)
    politica.estado = "VIGENTE"
    politica.activada_por = ctx.user_id
    politica.activada_en = datetime.now(UTC)
    politica.version += 1
    detalle_auditoria = {
        "vigente_desde": politica.vigente_desde.isoformat(),
        "vigente_hasta": politica.vigente_hasta.isoformat() if politica.vigente_hasta else None,
    }
    _historia(db, ctx, politica, "ACTIVADA", detalle_auditoria)
    _auditar(
        db,
        ctx,
        politica,
        "GOV_CLOSURE_POLICY_ACTIVATED",
        {"codigo": politica.codigo, **detalle_auditoria},
    )
    db.flush()
    return politica


def retirar(
    db: Session,
    ctx: CompanyContext,
    politica_id: str,
    version: int | None,
    datos: Any,
) -> GovernmentClosurePolicy:
    politica = _para_escribir(db, ctx, politica_id, version)
    if politica.estado not in ("BORRADOR", "VIGENTE"):
        raise ConflictError("GOV_CLOSURE_POLICY_INVALID_STATE", "La política no se puede retirar")
    if not datos.motivo:
        raise _invalida("Debe indicar el motivo del retiro")
    evaluar_antes_de_actuar(db, ctx, "CTL10_RETIRAR", ENTIDAD_POLITICA, politica_id)
    politica.estado = "RETIRADA"
    politica.retirada_por = ctx.user_id
    politica.retirada_en = datetime.now(UTC)
    politica.motivo_retiro = datos.motivo
    politica.version += 1
    _historia(db, ctx, politica, "RETIRADA", {"motivo": datos.motivo})
    _auditar(
        db,
        ctx,
        politica,
        "GOV_CLOSURE_POLICY_RETIRED",
        {"codigo": politica.codigo, "motivo": datos.motivo},
    )
    db.flush()
    return politica


def listar_bloqueos(
    db: Session,
    ctx: CompanyContext,
    accion_cierre: str | None,
    desde: date | None,
    hasta: date | None,
    pagina: int,
    tamano: int,
) -> dict:
    condiciones = [
        AuditEvent.tenant_id == ctx.tenant_id,
        AuditEvent.company_id == ctx.company_id,
        AuditEvent.action == ACCION_BLOQUEO,
        AuditEvent.entity_type == ENTIDAD_POLITICA,
    ]
    if desde:
        inicio, _ = limites_del_dia_utc(desde)
        condiciones.append(AuditEvent.event_time >= inicio)
    if hasta:
        _, fin = limites_del_dia_utc(hasta)
        condiciones.append(AuditEvent.event_time < fin)
    eventos = db.scalars(
        select(AuditEvent)
        .where(*condiciones)
        .order_by(AuditEvent.event_time.desc(), AuditEvent.id.desc())
        .limit(5000)
    ).all()
    filtrados = [
        e
        for e in eventos
        if not accion_cierre or (e.after or {}).get("accion_cierre") == accion_cierre
    ]
    total = len(filtrados)
    pagina_ev = filtrados[(pagina - 1) * tamano : pagina * tamano]
    usuarios = _usuarios_por_ids(
        db, [e.user_id for e in pagina_ev], ctx.tenant_id
    )
    items: list[dict] = []
    for evento in pagina_ev:
        after = evento.after or {}
        items.append(
            {
                "id": str(evento.id),
                "instante": _instante(evento.event_time),
                "politica_id": evento.entity_id,
                "politica_codigo": after.get("politica_codigo"),
                "accion_cierre": after.get("accion_cierre"),
                "objeto_tipo": after.get("objeto_tipo"),
                "objeto_id": after.get("objeto_id"),
                "objeto_codigo": after.get("objeto_codigo"),
                "total": after.get("total"),
                "usuario": (
                    usuarios.get(str(evento.user_id))
                    if evento.user_id is not None
                    else None
                ),
            }
        )
    return {"items": items, "total": total, "pagina": pagina, "tamano": tamano}

