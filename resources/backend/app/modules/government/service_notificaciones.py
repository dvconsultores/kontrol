"""Servicio de dominio de las notificaciones administrativas (DOC-04 · GOV-DOC-005)."""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentLink
from app.modules.documents.service import freeze_links
from app.modules.government.models import (
    GovernmentAct,
    GovernmentNotification,
    GovernmentNotificationAttempt,
    GovernmentNotificationVersion,
)
from app.modules.government.schemas_notificaciones import (
    AnulacionIn,
    IntentoIn,
    NotificacionCambio,
    NotificacionIn,
    TipoPersona,
    clave_identificacion,
    validar_identificacion,
)
from app.modules.government.service_actos import _auditar, _serializar_valor
from app.modules.government.service_actos import _versionar as _versionar_acto
from app.modules.government.service_estructura import _ente, _error_campo, _utc
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio


def _notificacion_por_id(
    db: Session,
    ctx: CompanyContext,
    notificacion_id: str,
) -> GovernmentNotification:
    """Obtiene una notificación de la empresa actual, sin revelar ajenas."""
    notificacion = db.execute(
        select(GovernmentNotification).where(
            GovernmentNotification.id == notificacion_id,
            GovernmentNotification.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if notificacion is None:
        raise NotFoundError(
            "GOV_NOTIFICATION_NOT_FOUND",
            "La notificación no existe en esta empresa",
        )
    return notificacion


def _acto_de_notificacion(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    *,
    for_update: bool = False,
) -> GovernmentAct:
    """Obtiene el acto de la notificación, validando existencia en la empresa."""
    stmt = select(GovernmentAct).where(
        GovernmentAct.id == acto_id,
        GovernmentAct.company_id == ctx.company_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    acto = db.execute(stmt).scalar_one_or_none()
    if acto is None:
        raise NotFoundError("GOV_ACT_NOT_FOUND", "El acto no existe en esta empresa")
    return acto


def _snapshot_notificacion(db: Session, n: GovernmentNotification) -> dict[str, Any]:
    """Instantánea de la notificación sin intentos (para versionado)."""
    return {
        "acto_id": str(n.act_id),
        "tipo_persona": n.tipo_persona,
        "nombre": n.nombre,
        "identificacion": n.identificacion,
        "domicilio": n.domicilio,
        "apoderado_nombre": n.apoderado_nombre,
        "apoderado_identificacion": n.apoderado_identificacion,
        "recursos": n.recursos,
        "documento_oficio_id": str(n.documento_oficio_id) if n.documento_oficio_id else None,
        "status": n.status,
        "fecha_notificacion": _serializar_valor(n.fecha_notificacion),
        "medio_notificacion": n.medio_notificacion,
        "motivo_anulacion": n.motivo_anulacion,
    }


def _versionar(
    db: Session,
    notificacion: GovernmentNotification,
    motivo: str | None,
    actor_id: str | None,
) -> None:
    """Registra una instantánea inmutable de la versión actual de la notificación."""
    version = GovernmentNotificationVersion(
        notification_id=notificacion.id,
        company_id=notificacion.company_id,
        version=notificacion.version,
        status=notificacion.status,
        snapshot=_snapshot_notificacion(db, notificacion),
        reason=motivo,
        actor_id=actor_id,
    )
    db.add(version)
    db.flush()


def _intentos_de_notificacion(
    db: Session,
    notificacion_id: str,
) -> list[GovernmentNotificationAttempt]:
    """Intento(s) de una notificación ordenados por número."""
    return list(
        db.execute(
            select(GovernmentNotificationAttempt)
            .where(GovernmentNotificationAttempt.notification_id == notificacion_id)
            .order_by(GovernmentNotificationAttempt.numero.asc())
        ).scalars().all()
    )


def salida_notificacion(
    db: Session,
    notificacion: GovernmentNotification,
) -> dict[str, Any]:
    """Representación pública de una notificación administrativa."""
    acto = db.execute(
        select(GovernmentAct).where(GovernmentAct.id == notificacion.act_id)
    ).scalar_one()
    intentos = _intentos_de_notificacion(db, str(notificacion.id))

    puede_publicar_en_prensa = notificacion.status == "PENDIENTE" and any(
        intento.medio == "PERSONAL" and intento.resultado == "FALLIDA"
        for intento in intentos
    )

    return {
        "id": str(notificacion.id),
        "acto": {
            "id": str(acto.id),
            "tipo": acto.tipo,
            "denominacion_tipo": acto.denominacion_tipo or None,
            "numero": acto.numero,
            "fecha": acto.fecha,
            "estado": acto.status,
        },
        "tipo_persona": notificacion.tipo_persona,
        "nombre": notificacion.nombre,
        "identificacion": notificacion.identificacion,
        "domicilio": notificacion.domicilio,
        "apoderado_nombre": notificacion.apoderado_nombre,
        "apoderado_identificacion": notificacion.apoderado_identificacion,
        "recursos": notificacion.recursos,
        "documento_oficio_id": (
            str(notificacion.documento_oficio_id)
            if notificacion.documento_oficio_id
            else None
        ),
        "estado": notificacion.status,
        "fecha_notificacion": notificacion.fecha_notificacion,
        "medio_notificacion": notificacion.medio_notificacion,
        "motivo_anulacion": notificacion.motivo_anulacion,
        "intentos": [
            {
                "numero": intento.numero,
                "medio": intento.medio,
                "resultado": intento.resultado,
                "fecha": intento.fecha,
                "receptor_nombre": intento.receptor_nombre,
                "receptor_identificacion": intento.receptor_identificacion,
                "motivo_fallo": intento.motivo_fallo,
                "diario": intento.diario,
                "referencia": intento.referencia,
                "documento_id": str(intento.documento_id),
                "registrado_por": intento.registrado_por,
                "creado_en": _utc(intento.created_at),
            }
            for intento in intentos
        ],
        "puede_publicar_en_prensa": puede_publicar_en_prensa,
        "version": notificacion.version,
        "creado_en": _utc(notificacion.created_at),
    }


def listar_notificaciones(
    db: Session,
    ctx: CompanyContext,
    anio: int,
    estado: str | None,
    acto_id: str | None,
) -> dict[str, Any]:
    """Lista las notificaciones de la empresa cuyos actos son del año."""
    _ente(db, ctx)

    inicio = date(anio, 1, 1)
    fin = date(anio, 12, 31)

    stmt = (
        select(GovernmentNotification, GovernmentAct)
        .join(GovernmentAct, GovernmentAct.id == GovernmentNotification.act_id)
        .where(
            GovernmentNotification.company_id == ctx.company_id,
            GovernmentAct.fecha >= inicio,
            GovernmentAct.fecha <= fin,
        )
    )
    if estado is not None:
        stmt = stmt.where(GovernmentNotification.status == estado)
    if acto_id is not None:
        stmt = stmt.where(GovernmentNotification.act_id == acto_id)

    filas = db.execute(
        stmt.order_by(
            GovernmentAct.fecha.desc(),
            GovernmentAct.numero.asc(),
            GovernmentNotification.nombre.asc(),
        )
    ).all()

    items: list[dict[str, Any]] = []
    for notificacion, acto in filas:
        intentos = _intentos_de_notificacion(db, notificacion.id)
        items.append(
            {
                "id": str(notificacion.id),
                "acto": {
                    "id": str(acto.id),
                    "tipo": acto.tipo,
                    "denominacion_tipo": acto.denominacion_tipo or None,
                    "numero": acto.numero,
                    "fecha": acto.fecha,
                    "estado": acto.status,
                },
                "tipo_persona": notificacion.tipo_persona,
                "nombre": notificacion.nombre,
                "identificacion": notificacion.identificacion,
                "estado": notificacion.status,
                "intentos": len(intentos),
                "fecha_notificacion": notificacion.fecha_notificacion,
                "medio_notificacion": notificacion.medio_notificacion,
            }
        )
    return {"anio": anio, "items": items, "total": len(items)}


def _existe_destinatario(
    db: Session,
    ctx: CompanyContext,
    acto_id: str,
    identificacion_clave: str,
    *,
    excluir: str | None = None,
) -> bool:
    """Comprueba si ya hay un destinatario no anulado con la misma clave."""
    stmt = select(GovernmentNotification.id).where(
        GovernmentNotification.company_id == ctx.company_id,
        GovernmentNotification.act_id == acto_id,
        GovernmentNotification.identificacion_clave == identificacion_clave,
        GovernmentNotification.status != "ANULADA",
    )
    if excluir is not None:
        stmt = stmt.where(GovernmentNotification.id != excluir)
    return db.execute(stmt.limit(1)).scalar_one_or_none() is not None


def crear_notificacion(
    db: Session,
    ctx: CompanyContext,
    datos: NotificacionIn,
    actor_id: str | None,
) -> dict[str, Any]:
    """Registra un destinatario para notificar un acto particular emitido."""
    acto = _acto_de_notificacion(db, ctx, str(datos.acto_id))

    if acto.caracter != "PARTICULAR":
        raise KontrolError(
            code="GOV_NOTIFICATION_ACT_NOT_PARTICULAR",
            message="Solo se notifican actos particulares",
            field_errors={"acto_id": ["Solo se notifican actos particulares"]},
            status_code=422,
        )

    if acto.status != "EMITIDO":
        raise ConflictError(
            "GOV_NOTIFICATION_ACT_NOT_EMITTED",
            "Solo se notifican actos emitidos y pendientes de eficacia",
        )

    identificacion_clave = clave_identificacion(datos.identificacion)
    if _existe_destinatario(db, ctx, str(acto.id), identificacion_clave):
        raise ConflictError(
            "GOV_NOTIFICATION_RECIPIENT_DUPLICATE",
            "Ese destinatario ya está registrado para este acto",
        )

    notificacion = GovernmentNotification(
        company_id=ctx.company_id,
        act_id=acto.id,
        tipo_persona=datos.tipo_persona,
        nombre=datos.nombre,
        identificacion=datos.identificacion,
        identificacion_clave=identificacion_clave,
        domicilio=datos.domicilio,
        apoderado_nombre=datos.apoderado_nombre,
        apoderado_identificacion=datos.apoderado_identificacion,
        recursos=datos.recursos,
        status="PENDIENTE",
        version=1,
        created_by=actor_id or None,
    )
    db.add(notificacion)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_NOTIFICATION_RECIPIENT_DUPLICATE",
            "Ese destinatario ya está registrado para este acto",
        ) from None

    _versionar(db, notificacion, None, actor_id)
    _auditar(
        db,
        ctx,
        "GOV_NOTIFICATION_CREATED",
        "GovernmentNotification",
        str(notificacion.id),
        None,
        {
            "acto_id": str(acto.id),
            "tipo_persona": notificacion.tipo_persona,
            "identificacion": notificacion.identificacion,
            "version": 1,
        },
    )
    return salida_notificacion(db, notificacion)


def obtener_notificacion(
    db: Session,
    ctx: CompanyContext,
    notificacion_id: str,
) -> dict[str, Any]:
    """Obtiene una notificación de la empresa actual."""
    notificacion = _notificacion_por_id(db, ctx, notificacion_id)
    return salida_notificacion(db, notificacion)


def notificacion_para_escribir(
    db: Session,
    ctx: CompanyContext,
    notificacion_id: str,
    version_esperada: int | None,
) -> GovernmentNotification:
    """Prepara una notificación para escritura con control de concurrencia."""
    if version_esperada is None:
        raise KontrolError(
            code="GOV_NOTIFICATION_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión de la notificación",
            status_code=428,
        )

    notificacion = db.execute(
        select(GovernmentNotification)
        .where(
            GovernmentNotification.id == notificacion_id,
            GovernmentNotification.company_id == ctx.company_id,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if notificacion is None:
        raise NotFoundError(
            "GOV_NOTIFICATION_NOT_FOUND",
            "La notificación no existe en esta empresa",
        )

    if version_esperada != notificacion.version:
        raise ConflictError(
            "GOV_NOTIFICATION_STALE",
            "La notificación cambió desde que la abrió; recárguela",
            details={"version_actual": notificacion.version},
        )

    return notificacion


def _campos_cambiados(
    actual: GovernmentNotification,
    datos: NotificacionCambio,
) -> dict[str, Any]:
    """Calcula los cambios reales entre la notificación y los datos nuevos."""
    antes: dict[str, Any] = {}
    despues: dict[str, Any] = {}

    cambios: list[tuple[str, Any, Any]] = [
        ("tipo_persona", actual.tipo_persona, datos.tipo_persona if datos.tipo_persona else None),
        ("nombre", actual.nombre, datos.nombre),
        ("identificacion", actual.identificacion, datos.identificacion),
        ("domicilio", actual.domicilio, datos.domicilio),
        ("apoderado_nombre", actual.apoderado_nombre, datos.apoderado_nombre),
        (
            "apoderado_identificacion",
            actual.apoderado_identificacion,
            datos.apoderado_identificacion,
        ),
        ("recursos", actual.recursos, datos.recursos),
    ]

    for campo, valor_actual, valor_nuevo in cambios:
        if valor_nuevo is not None and valor_nuevo != valor_actual:
            antes[campo] = valor_actual
            despues[campo] = valor_nuevo

    return {"before": antes, "after": despues}


def modificar_notificacion(
    db: Session,
    ctx: CompanyContext,
    notificacion_id: str,
    datos: NotificacionCambio,
    version_esperada: int | None,
    actor_id: str | None,
) -> dict[str, Any]:
    """Corrige los datos de una notificación pendiente y sin intentos."""
    notificacion = notificacion_para_escribir(
        db, ctx, notificacion_id, version_esperada
    )

    if notificacion.status != "PENDIENTE" or _intentos_de_notificacion(
        db, str(notificacion.id)
    ):
        raise ConflictError(
            "GOV_NOTIFICATION_INVALID_STATE",
            "Solo se corrige una notificación pendiente y sin intentos",
        )

    tipo_persona = (
        datos.tipo_persona if datos.tipo_persona else notificacion.tipo_persona
    )
    identificacion = datos.identificacion or notificacion.identificacion

    if datos.identificacion and not datos.tipo_persona:
        try:
            validar_identificacion(cast(TipoPersona, tipo_persona), identificacion)
        except ValueError as exc:
            raise _error_campo("identificacion", str(exc)) from None

    cambios = _campos_cambiados(notificacion, datos)
    if not cambios["before"]:
        raise KontrolError(
            code="GOV_NOTIFICATION_NO_CHANGES",
            message="No hay cambios que guardar",
            status_code=422,
        )

    nueva_clave = clave_identificacion(identificacion)
    if (
        "identificacion" in cambios["after"]
        or "tipo_persona" in cambios["after"]
    ) and _existe_destinatario(
        db, ctx, notificacion.act_id, nueva_clave, excluir=str(notificacion.id)
    ):
        raise ConflictError(
            "GOV_NOTIFICATION_RECIPIENT_DUPLICATE",
            "Ese destinatario ya está registrado para este acto",
        )

    notificacion.tipo_persona = tipo_persona
    notificacion.nombre = datos.nombre if datos.nombre is not None else notificacion.nombre
    notificacion.identificacion = identificacion
    notificacion.identificacion_clave = nueva_clave
    notificacion.domicilio = (
        datos.domicilio if datos.domicilio is not None else notificacion.domicilio
    )
    notificacion.apoderado_nombre = (
        datos.apoderado_nombre
        if datos.apoderado_nombre is not None
        else notificacion.apoderado_nombre
    )
    notificacion.apoderado_identificacion = (
        datos.apoderado_identificacion
        if datos.apoderado_identificacion is not None
        else notificacion.apoderado_identificacion
    )
    notificacion.recursos = (
        datos.recursos if datos.recursos is not None else notificacion.recursos
    )

    notificacion.version += 1
    db.flush()
    _versionar(db, notificacion, "Corrección de datos", actor_id)
    _auditar(
        db,
        ctx,
        "GOV_NOTIFICATION_UPDATED",
        "GovernmentNotification",
        str(notificacion.id),
        cambios["before"],
        cambios["after"],
    )
    return salida_notificacion(db, notificacion)


def aplicar_eficacia_del_acto(
    db: Session,
    ctx: CompanyContext,
    acto: GovernmentAct,
    actor: User,
) -> None:
    """Marca el acto como EFICAZ cuando todas sus notificaciones están notificadas."""
    if acto.caracter != "PARTICULAR" or acto.status != "EMITIDO":
        return

    notificaciones = db.execute(
        select(GovernmentNotification).where(
            GovernmentNotification.act_id == acto.id,
            GovernmentNotification.company_id == ctx.company_id,
            GovernmentNotification.status != "ANULADA",
        )
    ).scalars().all()

    if not notificaciones or any(
        notificacion.status != "NOTIFICADA" for notificacion in notificaciones
    ):
        return

    def _fecha_determinante(notificacion: GovernmentNotification) -> date:
        fecha = notificacion.fecha_notificacion
        return fecha if fecha is not None else date.min

    determinante = max(notificaciones, key=_fecha_determinante)

    intentos = _intentos_de_notificacion(db, str(determinante.id))
    intento = next(
        (i for i in reversed(intentos) if i.resultado in ("ENTREGADA", "PUBLICADA")),
        None,
    )
    if intento is None:
        return

    acto.medio = determinante.medio_notificacion
    if determinante.medio_notificacion == "PRENSA":
        acto.referencia_publicacion = f"{intento.diario} · {intento.referencia}"
    else:
        acto.referencia_publicacion = None
    acto.fecha_publicacion_notificacion = intento.fecha
    acto.documento_eficacia_id = intento.documento_id
    acto.fecha_eficacia = determinante.fecha_notificacion
    acto.status = "EFICAZ"
    acto.version += 1
    _versionar_acto(
        db,
        acto,
        "Eficacia por notificación de todos los destinatarios",
        str(actor.id),
    )
    _auditar(
        db,
        ctx,
        "GOV_ACT_EFFECTIVENESS_RECORDED",
        "GovernmentAct",
        str(acto.id),
        {k: _serializar_valor(v) for k, v in {"status": "EMITIDO"}.items()},
        {
            k: _serializar_valor(v)
            for k, v in {
                "medio": acto.medio,
                "referencia_publicacion": acto.referencia_publicacion,
                "fecha_publicacion_notificacion": acto.fecha_publicacion_notificacion,
                "documento_eficacia_id": (
                    str(acto.documento_eficacia_id)
                    if acto.documento_eficacia_id
                    else None
                ),
                "fecha_eficacia": acto.fecha_eficacia,
                "status": acto.status,
            }.items()
        },
        "Eficacia por notificación de todos los destinatarios",
    )


def anular_notificacion(
    db: Session,
    ctx: CompanyContext,
    notificacion_id: str,
    datos: AnulacionIn,
    version_esperada: int | None,
    actor: User,
) -> dict[str, Any]:
    """Anula una notificación pendiente sin resultados que cierren el proceso."""
    existente = _notificacion_por_id(db, ctx, notificacion_id)
    acto = db.execute(
        select(GovernmentAct)
        .where(
            GovernmentAct.id == existente.act_id,
            GovernmentAct.company_id == ctx.company_id,
        )
        .with_for_update()
    ).scalar_one()
    notificacion = notificacion_para_escribir(db, ctx, notificacion_id, version_esperada)

    if notificacion.status != "PENDIENTE":
        raise ConflictError(
            "GOV_NOTIFICATION_INVALID_STATE",
            "Solo se anula una notificación pendiente",
        )

    intentos = _intentos_de_notificacion(db, str(notificacion.id))
    if any(
        intento.resultado in ("ENTREGADA", "PUBLICADA") for intento in intentos
    ):
        raise ConflictError(
            "GOV_NOTIFICATION_INVALID_STATE",
            "Solo se anula una notificación pendiente",
        )

    notificacion.status = "ANULADA"
    notificacion.motivo_anulacion = datos.motivo
    notificacion.version += 1
    db.flush()
    _versionar(db, notificacion, datos.motivo, str(actor.id))
    _auditar(
        db,
        ctx,
        "GOV_NOTIFICATION_CANCELLED",
        "GovernmentNotification",
        str(notificacion.id),
        {"status": "PENDIENTE"},
        {
            "status": "ANULADA",
            "motivo_anulacion": datos.motivo,
        },
    )
    aplicar_eficacia_del_acto(db, ctx, acto, actor)
    return salida_notificacion(db, notificacion)


def versiones_notificacion(
    db: Session,
    ctx: CompanyContext,
    notificacion_id: str,
) -> dict[str, Any]:
    """Lista las versiones históricas de una notificación."""
    _notificacion_por_id(db, ctx, notificacion_id)

    versiones = db.execute(
        select(GovernmentNotificationVersion)
        .where(
            GovernmentNotificationVersion.notification_id == notificacion_id,
            GovernmentNotificationVersion.company_id == ctx.company_id,
        )
        .order_by(GovernmentNotificationVersion.version.asc())
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


def exportar_notificaciones_csv(
    db: Session,
    ctx: CompanyContext,
    anio: int,
) -> tuple[str, bytes]:
    """Exporta a CSV las notificaciones del año."""
    ente = _ente(db, ctx)
    listado = listar_notificaciones(db, ctx, anio, None, None)

    salida = io.StringIO()
    writer = csv.writer(salida, lineterminator="\n")
    writer.writerow(
        [
            "acto",
            "fecha del acto",
            "destinatario",
            "tipo de persona",
            "identificación",
            "estado",
            "intentos",
            "último intento (canal y resultado)",
            "fecha de notificación",
        ]
    )

    filas = 0
    for item in listado["items"]:
        notificacion = _notificacion_por_id(db, ctx, item["id"])
        ultimo = _intentos_de_notificacion(db, str(notificacion.id))
        ultimo_texto = ""
        if ultimo:
            intento = ultimo[-1]
            ultimo_texto = f"{intento.medio}·{intento.resultado}"

        writer.writerow(
            [
                item["acto"]["numero"],
                item["acto"]["fecha"].isoformat(),
                item["nombre"],
                item["tipo_persona"],
                item["identificacion"],
                item["estado"],
                item["intentos"],
                ultimo_texto,
                item["fecha_notificacion"].isoformat()
                if item["fecha_notificacion"]
                else "",
            ]
        )
        filas += 1

    _auditar(
        db,
        ctx,
        "GOV_NOTIFICATIONS_EXPORTED",
        "GovernmentEntity",
        str(ente.id),
        None,
        {"anio": anio, "filas": filas},
    )
    return f"notificaciones-{anio}.csv", salida.getvalue().encode("utf-8")


def _documento_de_la_notificacion(
    db: Session,
    n: GovernmentNotification,
    documento_id: str,
    campo: str,
    excluir: str | None = None,
) -> Document:
    """Valida un documento activo, de la empresa de la notificación, vinculado a ella."""
    stmt = (
        select(Document, DocumentLink.id)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            Document.id == documento_id,
            Document.company_id == n.company_id,
            DocumentLink.resource_type == "GovernmentNotification",
            DocumentLink.resource_id == str(n.id),
            DocumentLink.company_id == n.company_id,
            Document.status == "ACTIVE",
        )
        .limit(1)
    )
    fila = db.execute(stmt).first()
    documento = fila[0] if fila is not None else None

    if documento is None or (excluir is not None and str(documento.id) == excluir):
        mensaje = (
            "La constancia debe ser un documento distinto del oficio"
            if excluir is not None and documento is not None
            else "El documento no está vinculado a esta notificación o no está activo"
        )
        raise KontrolError(
            code="GOV_NOTIFICATION_INVALID_DOCUMENT",
            message="El documento no está vinculado a esta notificación o no está activo",
            field_errors={campo: [mensaje]},
            status_code=422,
        )

    return documento


def registrar_intento(
    db: Session,
    ctx: CompanyContext,
    notificacion_id: str,
    datos: IntentoIn,
    version_esperada: int | None,
    actor: User,
) -> dict[str, Any]:
    """Registra un intento de notificación y, si procede, la eficacia del acto."""
    acto = db.execute(
        select(GovernmentAct)
        .where(
            GovernmentAct.id == GovernmentNotification.act_id,
            GovernmentNotification.id == notificacion_id,
            GovernmentAct.company_id == ctx.company_id,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if acto is None:
        raise NotFoundError(
            "GOV_NOTIFICATION_NOT_FOUND",
            "La notificación no existe en esta empresa",
        )

    n = notificacion_para_escribir(db, ctx, notificacion_id, version_esperada)

    if acto.status != "EMITIDO":
        raise ConflictError(
            "GOV_NOTIFICATION_ACT_NOT_EMITTED",
            "El acto ya no está pendiente de notificación",
        )

    if n.status != "PENDIENTE":
        raise ConflictError(
            "GOV_NOTIFICATION_INVALID_STATE",
            "Solo se registran intentos en una notificación pendiente",
        )

    if datos.fecha < acto.fecha:
        raise _error_campo("fecha", "No puede ser anterior a la fecha del acto")
    if datos.fecha > hoy_de_negocio():
        raise _error_campo("fecha", "No puede ser posterior a hoy")

    oficio_id: str
    if n.documento_oficio_id is not None:
        if (
            datos.documento_oficio_id is not None
            and datos.documento_oficio_id != n.documento_oficio_id
        ):
            raise _error_campo(
                "documento_oficio_id",
                "El oficio quedó fijado en el primer intento",
            )
        oficio_id = n.documento_oficio_id
    else:
        if datos.documento_oficio_id is None:
            raise _error_campo("documento_oficio_id", "El oficio es obligatorio")
        _documento_de_la_notificacion(
            db, n, datos.documento_oficio_id, "documento_oficio_id"
        )
        oficio_id = datos.documento_oficio_id

    constancia = _documento_de_la_notificacion(
        db, n, str(datos.documento_id), "documento_id", excluir=oficio_id
    )

    intentos_previos = _intentos_de_notificacion(db, str(n.id))
    if any(
        str(intento.documento_id) == str(datos.documento_id)
        for intento in intentos_previos
    ):
        raise _error_campo(
            "documento_id", "Esa constancia ya se usó en otro intento"
        )

    if (
        datos.medio == "PRENSA"
        and not any(
            intento.medio == "PERSONAL" and intento.resultado == "FALLIDA"
            for intento in intentos_previos
        )
    ):
        raise KontrolError(
            code="GOV_NOTIFICATION_PRESS_REQUIRES_FAILED_ATTEMPT",
            message=(
                "La prensa solo procede si la notificación personal fue "
                "impracticable (LOPA art. 76)"
            ),
            field_errors={
                "medio": [
                    "La prensa solo procede si la notificación personal fue "
                    "impracticable (LOPA art. 76)"
                ]
            },
            status_code=422,
        )

    numero = (max((i.numero for i in intentos_previos), default=0)) + 1

    intento = GovernmentNotificationAttempt(
        company_id=ctx.company_id,
        notification_id=n.id,
        numero=numero,
        medio=datos.medio,
        resultado=datos.resultado,
        fecha=datos.fecha,
        receptor_nombre=datos.receptor_nombre,
        receptor_identificacion=datos.receptor_identificacion,
        motivo_fallo=datos.motivo_fallo,
        diario=datos.diario,
        referencia=datos.referencia,
        documento_id=constancia.id,
        registrado_por=actor.id,
    )
    db.add(intento)
    n.documento_oficio_id = oficio_id

    motivo: str
    if datos.resultado == "ENTREGADA":
        n.status = "NOTIFICADA"
        n.fecha_notificacion = datos.fecha
        n.medio_notificacion = "PERSONAL"
        motivo = "Entrega personal"
    elif datos.resultado == "PUBLICADA":
        n.status = "NOTIFICADA"
        n.fecha_notificacion = datos.fecha + timedelta(days=15)
        n.medio_notificacion = "PRENSA"
        motivo = "Publicación en prensa"
    else:
        motivo = "Intento fallido"

    n.version += 1
    db.flush()
    _versionar(db, n, motivo, str(actor.id))
    freeze_links(
        db,
        resource_type="GovernmentNotification",
        resource_id=str(n.id),
        actor=actor,
    )

    accion = {
        "ENTREGADA": "GOV_NOTIFICATION_DELIVERED",
        "PUBLICADA": "GOV_NOTIFICATION_PUBLISHED",
    }.get(datos.resultado, "GOV_NOTIFICATION_ATTEMPT_FAILED")

    _auditar(
        db,
        ctx,
        accion,
        "GovernmentNotification",
        str(n.id),
        None,
        {
            "numero": numero,
            "medio": datos.medio,
            "resultado": datos.resultado,
            "fecha": _serializar_valor(datos.fecha),
            "documento_id": str(constancia.id),
            "fecha_notificacion": _serializar_valor(n.fecha_notificacion),
        },
        motivo,
    )

    aplicar_eficacia_del_acto(db, ctx, acto, actor)
    db.flush()
    return salida_notificacion(db, n)
