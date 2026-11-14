"""Alertas de operaciones atípicas de Gobierno (CTL-07, GOV-CTL-009)."""

from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.government.models import (
    GovernmentAtypicalAlertReview,
    GovernmentOfficial,
    GovernmentProcurementFile,
    GovernmentProcurementOffer,
    GovernmentUserOfficialLink,
)
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids
from app.modules.government.service_ocupacion import enmascarar_documento
from app.modules.government.service_ofertas import _normalizar_documento
from app.modules.government.service_sod import etiqueta_de
from app.modules.government.service_sod_funciones import etiqueta_de_funcion
from app.shared.audit import record_audit
from app.shared.clock import instante_actual

AVISO = "Una alerta es una señal para revisar; no es una acusación ni una conclusión."
ACCIONES_SOD = ("GOV_SOD_CONFLICT_BLOCKED", "GOV_SOD_ROLE_CONFLICT_BLOCKED")
ESTADOS_ALERTA = ("PENDIENTE", "REVISADA")
RESULTADOS: dict[str, str] = {
    "SIN_OBSERVACION": "Sin observación",
    "REQUIERE_SEGUIMIENTO": "Requiere seguimiento",
}
ESTADOS_EXPEDIENTE_ETIQUETA = {"ABIERTO": "Abierto", "CERRADO": "Cerrado"}
TIPOS: dict[str, dict[str, Any]] = {
    "DUPLICIDAD": {
        "etiqueta": "Duplicidad",
        "descripcion": "Dos expedientes de contratación no descartados, de la misma unidad, con el mismo objeto.",
        "disponible": True,
        "motivo": None,
        "requisito": None,
    },
    "PROVEEDOR_RELACIONADO": {
        "etiqueta": "Proveedor relacionado",
        "descripcion": "Una oferta cuyo documento de oferente coincide con el documento de un funcionario del ente.",
        "disponible": True,
        "motivo": None,
        "requisito": None,
    },
    "AUTOAPROBACION": {
        "etiqueta": "Autoaprobación",
        "descripcion": "Intento bloqueado de aprobar lo propio o de ejercer funciones incompatibles (segregación de funciones).",
        "disponible": True,
        "motivo": None,
        "requisito": None,
    },
    "FRACCIONAMIENTO": {
        "etiqueta": "Fraccionamiento",
        "descripcion": "Partición de una contratación para eludir la modalidad que corresponde por monto.",
        "disponible": False,
        "motivo": (
            "Las ofertas y las adjudicaciones no registran monto y los umbrales de modalidad en U.T. dependen de una fuente legal sin validar. "
            "Sin monto, la alerta sería una conjetura."
        ),
        "requisito": "Monto de la oferta y de la adjudicación, y umbrales de modalidad con fuente legal validada.",
    },
    "OVERRIDE_FRECUENTE": {
        "etiqueta": "Override frecuente",
        "descripcion": "Uso reiterado de excepciones a un control.",
        "disponible": False,
        "motivo": (
            "Gobierno no admite excepciones: la segregación de funciones y el techo de autoridad bloquean sin override. "
            "No hay overrides que contar."
        ),
        "requisito": "Un mecanismo de excepción autorizado y auditado.",
    },
}


def _normalizar_objeto(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.casefold()
    return " ".join(texto.split())


def _alerta(
    clave: str,
    tipo: str,
    fecha: datetime,
    titulo: str,
    detalle: str,
    sujetos: list[dict[str, str]],
    *,
    usuarios: frozenset[str] = frozenset(),
    funcionarios: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    return {
        "clave": clave,
        "tipo": tipo,
        "tipo_etiqueta": TIPOS[tipo]["etiqueta"],
        "fecha": _instante(fecha),
        "titulo": titulo,
        "detalle": detalle,
        "sujetos": sujetos,
        "_usuarios": set(usuarios),
        "_funcionarios": set(funcionarios),
    }


def _duplicidades(db: Session, ctx: CompanyContext) -> list[dict[str, Any]]:
    expedientes = (
        db.execute(
            select(GovernmentProcurementFile)
            .where(
                GovernmentProcurementFile.company_id == ctx.company_id,
                GovernmentProcurementFile.status != "DESCARTADO",
            )
            .order_by(GovernmentProcurementFile.created_at, GovernmentProcurementFile.id)
        )
        .scalars()
        .all()
    )
    grupos: dict[tuple[str, str], list[GovernmentProcurementFile]] = {}
    for expediente in expedientes:
        clave_grupo = (expediente.unidad_id, _normalizar_objeto(expediente.objeto))
        grupos.setdefault(clave_grupo, []).append(expediente)

    alertas: list[dict[str, Any]] = []
    for grupo in grupos.values():
        for indice, expediente_a in enumerate(grupo):
            for expediente_b in grupo[indice + 1 :]:
                alertas.append(
                    _alerta(
                        f"DUPLICIDAD:{min(expediente_a.id, expediente_b.id)}:{max(expediente_a.id, expediente_b.id)}",
                        "DUPLICIDAD",
                        max(expediente_a.created_at, expediente_b.created_at),
                        f"Expedientes {expediente_a.numero} y {expediente_b.numero} con el mismo objeto",
                        f"Los dos expedientes son de la unidad {expediente_a.unidad_nombre} y tienen el objeto «{expediente_a.objeto}».",
                        [
                            {"etiqueta": "Expediente", "valor": f"{expediente_a.numero} · {ESTADOS_EXPEDIENTE_ETIQUETA.get(expediente_a.status, expediente_a.status)}"},
                            {"etiqueta": "Expediente", "valor": f"{expediente_b.numero} · {ESTADOS_EXPEDIENTE_ETIQUETA.get(expediente_b.status, expediente_b.status)}"},
                            {"etiqueta": "Unidad", "valor": expediente_a.unidad_nombre},
                            {"etiqueta": "Objeto", "valor": expediente_a.objeto},
                        ],
                    )
                )
    return alertas


def _proveedores_relacionados(db: Session, ctx: CompanyContext) -> list[dict[str, Any]]:
    funcionarios = (
        db.execute(
            select(GovernmentOfficial).where(GovernmentOfficial.company_id == ctx.company_id)
        )
        .scalars()
        .all()
    )
    indice_documentos: dict[str, list[GovernmentOfficial]] = {}
    for funcionario in funcionarios:
        documento_normalizado = _normalizar_documento(
            funcionario.tipo_documento + funcionario.numero_documento
        )
        indice_documentos.setdefault(documento_normalizado, []).append(funcionario)

    filas = db.execute(
        select(GovernmentProcurementOffer, GovernmentProcurementFile)
        .join(GovernmentProcurementFile, GovernmentProcurementFile.id == GovernmentProcurementOffer.file_id)
        .where(GovernmentProcurementOffer.company_id == ctx.company_id)
    ).all()

    alertas: list[dict[str, Any]] = []
    for oferta, expediente in filas:
        documento_oferente = _normalizar_documento(oferta.oferente_documento)
        for funcionario in indice_documentos.get(documento_oferente, []):
            alertas.append(
                _alerta(
                    f"PROVEEDOR_RELACIONADO:{oferta.id}:{funcionario.id}",
                    "PROVEEDOR_RELACIONADO",
                    oferta.recibida_en,
                    f"Oferente {oferta.oferente_nombre} con el documento de un funcionario",
                    (
                        f"La oferta R-{oferta.numero:04d} del expediente {expediente.numero} la presentó un oferente "
                        f"cuyo documento coincide con el del funcionario {funcionario.nombre}."
                    ),
                    [
                        {"etiqueta": "Expediente", "valor": expediente.numero},
                        {"etiqueta": "Oferta", "valor": f"R-{oferta.numero:04d}"},
                        {"etiqueta": "Oferente", "valor": oferta.oferente_nombre},
                        {
                            "etiqueta": "Funcionario",
                            "valor": f"{funcionario.nombre} ({enmascarar_documento(funcionario.tipo_documento, funcionario.numero_documento)})",
                        },
                    ],
                    funcionarios=frozenset({str(funcionario.id)}),
                )
            )
    return alertas


def _autoaprobaciones(db: Session, ctx: CompanyContext) -> list[dict[str, Any]]:
    eventos = (
        db.execute(
            select(AuditEvent)
            .where(
                AuditEvent.tenant_id == ctx.tenant_id,
                AuditEvent.company_id == ctx.company_id,
                AuditEvent.action.in_(ACCIONES_SOD),
            )
            .order_by(AuditEvent.event_time.desc())
        )
        .scalars()
        .all()
    )
    usuarios = _usuarios_por_ids(db, [evento.user_id for evento in eventos], ctx.tenant_id)

    alertas: list[dict[str, Any]] = []
    for evento in eventos:
        after = evento.after or {}
        usuario = usuarios.get(str(evento.user_id), "Usuario no identificado") if evento.user_id else "Usuario no identificado"
        regla = str(after.get("regla_codigo") or "sin código")
        sujetos: list[dict[str, str]] = [
            {"etiqueta": "Usuario", "valor": usuario},
            {"etiqueta": "Regla", "valor": regla},
        ]
        if evento.action == "GOV_SOD_CONFLICT_BLOCKED":
            operacion = etiqueta_de(after.get("accion")) or "una operación"
            previa = etiqueta_de(after.get("accion_previa")) or "una operación previa"
            titulo = "Intento bloqueado por segregación de funciones"
            detalle = (
                f"{usuario} intentó «{operacion}» después de «{previa}» sobre el mismo objeto. "
                f"La regla {regla} lo bloqueó."
            )
        else:
            funcion = etiqueta_de_funcion(after.get("funcion")) or "una función"
            previa = etiqueta_de_funcion(after.get("funcion_previa")) or "otra función"
            expediente = str(after.get("expediente_numero") or "sin número")
            titulo = "Intento bloqueado por funciones incompatibles"
            detalle = (
                f"{usuario} intentó actuar como {funcion} en el expediente {expediente} "
                f"después de actuar como {previa}. La regla {regla} lo bloqueó."
            )
            sujetos.append({"etiqueta": "Expediente", "valor": expediente})
        usuarios_alerta = frozenset({str(evento.user_id)}) if evento.user_id else frozenset()
        alertas.append(
            _alerta(
                f"AUTOAPROBACION:{evento.id}",
                "AUTOAPROBACION",
                evento.event_time,
                titulo,
                detalle,
                sujetos,
                usuarios=usuarios_alerta,
            )
        )
    return alertas


def _detectar(db: Session, ctx: CompanyContext) -> dict[str, dict[str, Any]]:
    alertas: dict[str, dict[str, Any]] = {}
    for alerta in _duplicidades(db, ctx) + _proveedores_relacionados(db, ctx) + _autoaprobaciones(db, ctx):
        alertas[alerta["clave"]] = alerta
    return alertas


def _funcionarios_de(db: Session, ctx: CompanyContext, usuario_id: str) -> set[str]:
    filas = db.execute(
        select(GovernmentUserOfficialLink.official_id).where(
            GovernmentUserOfficialLink.company_id == ctx.company_id,
            GovernmentUserOfficialLink.user_id == usuario_id,
        )
    ).scalars()
    return set(filas)


def _salida(
    alerta: dict[str, Any],
    revision: GovernmentAtypicalAlertReview | None,
    usuarios_revisores: dict[str, str],
    *,
    vigente: bool,
    es_sujeto: bool,
) -> dict[str, Any]:
    if revision:
        estado = "REVISADA"
        revision_salida: dict[str, Any] | None = {
            "resultado": revision.resultado,
            "resultado_etiqueta": RESULTADOS[revision.resultado],
            "observacion": revision.observacion,
            "revisada_por": usuarios_revisores.get(revision.revisada_por),
            "revisada_en": revision.revisada_en,
        }
    else:
        estado = "PENDIENTE"
        revision_salida = None
    return {
        "clave": alerta["clave"],
        "tipo": alerta["tipo"],
        "tipo_etiqueta": alerta["tipo_etiqueta"],
        "fecha": alerta["fecha"],
        "titulo": alerta["titulo"],
        "detalle": alerta["detalle"],
        "sujetos": alerta["sujetos"],
        "estado": estado,
        "vigente": vigente,
        "es_sujeto": es_sujeto,
        "revision": revision_salida,
    }


def listar_alertas(
    db: Session,
    ctx: CompanyContext,
    *,
    tipo: str | None,
    estado: str | None,
    usuario_id: str,
) -> dict[str, Any]:
    if tipo is not None and tipo not in TIPOS:
        raise KontrolError(code="GOV_ALERT_FILTER_INVALID", message="Tipo de alerta no válido.", status_code=422)
    if estado is not None and estado not in ESTADOS_ALERTA:
        raise KontrolError(code="GOV_ALERT_FILTER_INVALID", message="Estado de alerta no válido.", status_code=422)

    derivadas = _detectar(db, ctx)
    revisiones = {
        revision.clave: revision
        for revision in db.execute(
            select(GovernmentAtypicalAlertReview).where(
                GovernmentAtypicalAlertReview.company_id == ctx.company_id
            )
        )
        .scalars()
        .all()
    }
    revisores = _usuarios_por_ids(
        db, [revision.revisada_por for revision in revisiones.values()], ctx.tenant_id
    )
    mis_funcionarios = _funcionarios_de(db, ctx, usuario_id)

    alertas: list[dict[str, Any]] = []
    for clave, alerta in derivadas.items():
        es_sujeto = usuario_id in alerta["_usuarios"] or bool(
            mis_funcionarios & alerta["_funcionarios"]
        )
        salida = _salida(alerta, revisiones.get(clave), revisores, vigente=True, es_sujeto=es_sujeto)
        alertas.append(salida)

    for clave, revision in revisiones.items():
        if clave not in derivadas:
            alerta_sintetica = _alerta(
                revision.clave,
                revision.tipo,
                revision.revisada_en,
                TIPOS[revision.tipo]["etiqueta"],
                revision.resumen,
                [],
            )
            alertas.append(_salida(alerta_sintetica, revision, revisores, vigente=False, es_sujeto=False))

    tipos = []
    for codigo, definicion in TIPOS.items():
        total = sum(1 for alerta in alertas if alerta["tipo"] == codigo)
        pendientes = sum(
            1 for alerta in alertas if alerta["tipo"] == codigo and alerta["estado"] == "PENDIENTE"
        )
        tipos.append(
            {
                "codigo": codigo,
                "etiqueta": definicion["etiqueta"],
                "descripcion": definicion["descripcion"],
                "disponible": definicion["disponible"],
                "motivo_no_disponible": definicion["motivo"],
                "requisito_habilitante": definicion["requisito"],
                "total": total,
                "pendientes": pendientes,
            }
        )

    if tipo is not None:
        alertas = [alerta for alerta in alertas if alerta["tipo"] == tipo]
    if estado is not None:
        alertas = [alerta for alerta in alertas if alerta["estado"] == estado]
    alertas.sort(key=lambda alerta: alerta["clave"])
    alertas.sort(key=lambda alerta: alerta["fecha"], reverse=True)

    return {"aviso": AVISO, "tipos": tipos, "alertas": alertas}


def revisar_alerta(
    db: Session,
    ctx: CompanyContext,
    *,
    usuario_id: str,
    clave: str,
    resultado: str,
    observacion: str,
) -> dict[str, Any]:
    if resultado not in RESULTADOS:
        raise KontrolError(
            code="GOV_ALERT_REVIEW_INVALID",
            message="El resultado no es válido.",
            status_code=422,
            field_errors={"resultado": ["Elija Sin observación o Requiere seguimiento."]},
        )
    texto = observacion.strip()
    if len(texto) < 10 or len(texto) > 2000:
        mensaje = "La observación debe tener entre 10 y 2000 caracteres."
        raise KontrolError(
            code="GOV_ALERT_REVIEW_INVALID",
            message=mensaje,
            status_code=422,
            field_errors={"observacion": [mensaje]},
        )

    alerta = _detectar(db, ctx).get(clave)
    if alerta is None:
        raise NotFoundError("GOV_ALERT_NOT_FOUND", "La alerta no existe o ya no se detecta.")

    existente = db.execute(
        select(GovernmentAtypicalAlertReview).where(
            GovernmentAtypicalAlertReview.company_id == ctx.company_id,
            GovernmentAtypicalAlertReview.clave == clave,
        )
    ).scalar_one_or_none()
    if existente:
        raise ConflictError("GOV_ALERT_ALREADY_REVIEWED", "La alerta ya fue revisada.")

    mis_funcionarios = _funcionarios_de(db, ctx, usuario_id)
    if usuario_id in alerta["_usuarios"] or bool(mis_funcionarios & alerta["_funcionarios"]):
        raise ConflictError(
            "GOV_ALERT_SELF_REVIEW",
            "No puede revisar una alerta de la que es sujeto. Debe hacerlo otro usuario de Control Interno.",
        )

    revision = GovernmentAtypicalAlertReview(
        company_id=ctx.company_id,
        clave=clave,
        tipo=alerta["tipo"],
        resultado=resultado,
        observacion=texto,
        resumen=f"{alerta['titulo']}. {alerta['detalle']}"[:1000],
        revisada_por=usuario_id,
        revisada_en=instante_actual(),
        created_by=usuario_id,
    )
    db.add(revision)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("GOV_ALERT_ALREADY_REVIEWED", "La alerta ya fue revisada.") from None

    record_audit(
        db,
        action="GOV_ATYPICAL_ALERT_REVIEWED",
        entity_type="GovernmentAtypicalAlertReview",
        entity_id=str(revision.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=usuario_id,
        after={"clave": clave, "resultado": resultado, "tipo": alerta["tipo"]},
    )
    db.commit()

    listado = listar_alertas(db, ctx, tipo=None, estado=None, usuario_id=usuario_id)
    return next(alerta for alerta in listado["alertas"] if alerta["clave"] == clave)
