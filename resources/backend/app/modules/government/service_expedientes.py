from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.government.models import (
    GovernmentAct,
    GovernmentOfficial,
    GovernmentProcurementCommittee,
    GovernmentProcurementFile,
    GovernmentProcurementFileEvent,
    GovernmentProcurementFileFolio,
    GovernmentProcurementFileMilestone,
    GovernmentProcurementFileResponsible,
    GovernmentProcurementOffer,
    GovernmentProcurementOpeningOffer,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_comisiones import (
    ETIQUETAS as ETIQUETAS_COMISION,
)
from app.modules.government.service_comisiones import (
    _acto_ref,
    situacion_de,
)
from app.modules.government.service_ocupacion import ocupaciones_de_funcionario
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

ENTIDAD = "GovernmentProcurementFile"

_ETIQUETAS_TIPO: dict[str, str] = {
    "BIENES": "Bienes",
    "SERVICIOS": "Servicios",
    "OBRAS": "Obras",
}
_ETIQUETAS_MODALIDAD: dict[str, str] = {
    "CONCURSO_ABIERTO": "Concurso abierto",
    "CONCURSO_CERRADO": "Concurso cerrado",
    "CONSULTA_PRECIOS": "Consulta de precios",
    "CONTRATACION_DIRECTA": "Contratación directa",
}
_ETIQUETAS_ROL: dict[str, str] = {
    "RESPONSABLE": "Responsable del expediente",
    "REQUIRENTE": "Unidad usuaria o requirente",
    "SUSTANCIACION": "Sustanciación",
    "CUSTODIA": "Custodia",
}
_ETIQUETAS_ESTADO: dict[str, str] = {
    "ABIERTO": "En curso",
    "CERRADO": "Cerrado",
    "DESCARTADO": "Descartado",
}
_ETIQUETAS_ESTADO_HITO: dict[str, str] = {
    "PREVISTO": "Previsto",
    "CUMPLIDO": "Cumplido",
    "NO_APLICA": "No aplica",
}
_ETIQUETAS_EVENTO: dict[str, str] = {
    "APERTURA": "Apertura",
    "DATOS": "Datos",
    "RESPONSABLE": "Responsable",
    "COMISION": "Comisión",
    "ACTUACION": "Actuación",
    "DECISION": "Decisión",
    "DOCUMENTO": "Documento",
    "ACTO": "Acto",
    "HITO": "Hito",
    "CIERRE": "Cierre",
    "DESCARTE": "Descarte",
    "OFERTA": "Oferta",
    "APERTURA_OFERTA": "Apertura de ofertas",
    "EVALUACION": "Evaluación",
    "RECOMENDACION": "Recomendación",
    "RECHAZO_OFERTA": "Rechazo de oferta",
    "ADJUDICACION": "Adjudicación",
    "DESIERTA": "Declaratoria desierta",
    "TERMINACION": "Terminación",
    "NULIDAD": "Nulidad",
}

_SECCION_ORDEN = (
    "SOLICITUD",
    "AUTORIZACION_INICIO",
    "PLIEGO",
    "ACTOS_MOTIVADOS",
    "LLAMADO_INVITACION",
    "MODIFICACIONES_PLIEGO",
    "ACTA_RECEPCION",
    "OFERTAS",
    "INFORME_RECOMENDACION",
    "ADJUDICACION",
    "NOTIFICACION",
    "CONTRATO",
    "OTRO_SELECCION",
)
_ADMIN_ORDEN = (
    "GARANTIAS",
    "ACTAS_EJECUCION",
    "MODIFICACION_CONTRATO",
    "FORMULARIOS_PAGO",
    "APROBACIONES_PAGO",
    "PAGOS",
    "FINIQUITO",
    "LIBERACION_GARANTIAS",
    "EVALUACION_CONTRATISTA",
    "OTRO_ADMINISTRACION",
)
_SECCION_ETIQUETAS = {
    "SOLICITUD": "Solicitud de la unidad usuaria o requirente",
    "AUTORIZACION_INICIO": "Autorización de inicio o acta de inicio",
    "PLIEGO": "Pliego o condiciones de la contratación",
    "ACTOS_MOTIVADOS": "Actos motivados",
    "LLAMADO_INVITACION": "Llamado o invitación a los participantes",
    "MODIFICACIONES_PLIEGO": "Modificaciones o aclaratorias del pliego",
    "ACTA_RECEPCION": "Acta de recepción de documentos u ofertas",
    "OFERTAS": "Ofertas recibidas",
    "INFORME_RECOMENDACION": "Informe de análisis y recomendación",
    "ADJUDICACION": "Documento de adjudicación",
    "NOTIFICACION": "Notificación de la adjudicación",
    "CONTRATO": "Contrato",
    "OTRO_SELECCION": "Otro del procedimiento de selección",
    "GARANTIAS": "Garantías",
    "ACTAS_EJECUCION": "Actas de inicio, suspensión, terminación y recepción",
    "MODIFICACION_CONTRATO": "Modificación del contrato",
    "FORMULARIOS_PAGO": "Formularios de pago o valuaciones",
    "APROBACIONES_PAGO": "Aprobaciones de pago",
    "PAGOS": "Pagos realizados",
    "FINIQUITO": "Finiquito",
    "LIBERACION_GARANTIAS": "Liberación de garantías",
    "EVALUACION_CONTRATISTA": "Evaluación del contratista",
    "OTRO_ADMINISTRACION": "Otro de la administración del contrato",
}

CLASES_FOLIO: tuple[tuple[str, str, str, str, bool], ...] = (
    ("SOLICITUD", _SECCION_ETIQUETAS["SOLICITUD"], "RLCP art. 32.1", "SELECCION", False),
    ("AUTORIZACION_INICIO", _SECCION_ETIQUETAS["AUTORIZACION_INICIO"], "RLCP art. 32.2", "SELECCION", False),
    ("PLIEGO", _SECCION_ETIQUETAS["PLIEGO"], "RLCP art. 32.3", "SELECCION", False),
    ("ACTOS_MOTIVADOS", _SECCION_ETIQUETAS["ACTOS_MOTIVADOS"], "RLCP art. 32.4", "SELECCION", True),
    ("LLAMADO_INVITACION", _SECCION_ETIQUETAS["LLAMADO_INVITACION"], "RLCP art. 32.5", "SELECCION", False),
    ("MODIFICACIONES_PLIEGO", _SECCION_ETIQUETAS["MODIFICACIONES_PLIEGO"], "RLCP art. 32.6", "SELECCION", True),
    ("ACTA_RECEPCION", _SECCION_ETIQUETAS["ACTA_RECEPCION"], "RLCP art. 32.7", "SELECCION", False),
    ("OFERTAS", _SECCION_ETIQUETAS["OFERTAS"], "RLCP art. 32.8", "SELECCION", False),
    ("INFORME_RECOMENDACION", _SECCION_ETIQUETAS["INFORME_RECOMENDACION"], "RLCP art. 32.9", "SELECCION", False),
    ("ADJUDICACION", _SECCION_ETIQUETAS["ADJUDICACION"], "RLCP art. 32.10", "SELECCION", False),
    ("NOTIFICACION", _SECCION_ETIQUETAS["NOTIFICACION"], "RLCP art. 32.11", "SELECCION", True),
    ("CONTRATO", _SECCION_ETIQUETAS["CONTRATO"], "RLCP art. 32.12", "SELECCION", False),
    ("OTRO_SELECCION", _SECCION_ETIQUETAS["OTRO_SELECCION"], "RLCP art. 32.13", "SELECCION", True),
    ("GARANTIAS", _SECCION_ETIQUETAS["GARANTIAS"], "RLCP art. 32, administración 1", "ADMINISTRACION", True),
    ("ACTAS_EJECUCION", _SECCION_ETIQUETAS["ACTAS_EJECUCION"], "RLCP art. 32, administración 2", "ADMINISTRACION", True),
    ("MODIFICACION_CONTRATO", _SECCION_ETIQUETAS["MODIFICACION_CONTRATO"], "RLCP art. 32, administración 3", "ADMINISTRACION", True),
    ("FORMULARIOS_PAGO", _SECCION_ETIQUETAS["FORMULARIOS_PAGO"], "RLCP art. 32, administración 4", "ADMINISTRACION", True),
    ("APROBACIONES_PAGO", _SECCION_ETIQUETAS["APROBACIONES_PAGO"], "RLCP art. 32, administración 5", "ADMINISTRACION", True),
    ("PAGOS", _SECCION_ETIQUETAS["PAGOS"], "RLCP art. 32, administración 6", "ADMINISTRACION", True),
    ("FINIQUITO", _SECCION_ETIQUETAS["FINIQUITO"], "RLCP art. 32, administración 7", "ADMINISTRACION", True),
    ("LIBERACION_GARANTIAS", _SECCION_ETIQUETAS["LIBERACION_GARANTIAS"], "RLCP art. 32, administración 8", "ADMINISTRACION", True),
    ("EVALUACION_CONTRATISTA", _SECCION_ETIQUETAS["EVALUACION_CONTRATISTA"], "RLCP art. 32, administración 9", "ADMINISTRACION", True),
    ("OTRO_ADMINISTRACION", _SECCION_ETIQUETAS["OTRO_ADMINISTRACION"], "RLCP art. 32, administración 10", "ADMINISTRACION", True),
)
_CLASES_FOLIO_CODIGOS = frozenset(item[0] for item in CLASES_FOLIO)
_CLASES_SELECCION_NO_CONDICIONAL = tuple(
    item[0] for item in CLASES_FOLIO if item[3] == "SELECCION" and not item[4]
)

_AVISO_MODALIDAD = (
    "La modalidad es la que declara la unidad. Kontrol no la determina ni valida montos o excepciones."
)
_AVISO_LAPSOS = (
    "Las fechas las registra el usuario. Kontrol no calcula lapsos ni días hábiles."
)

_CLAVES_AUDITORIA = frozenset(
    {
        "acto",
        "apertura",
        "aspecto",
        "asistentes",
        "canal",
        "causal",
        "clase",
        "comision",
        "confidencial",
        "criterio",
        "decision",
        "documentos",
        "estado",
        "fecha",
        "fecha_prevista",
        "fecha_real",
        "firmantes",
        "folio",
        "funcionario",
        "hito",
        "matriz",
        "modalidad",
        "motivo",
        "numero",
        "oferta",
        "ofertas",
        "opciones",
        "quorum",
        "recomendacion",
        "rechazos",
        "referencia",
        "resultado",
        "rol",
        "secuencia",
        "sustituye",
        "titulo",
        "version",
    }
)


def _iso(value: Any) -> Any:
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def _auditar(
    db: Session,
    ctx: CompanyContext,
    accion: str,
    *,
    expediente_id: str,
    after: dict[str, Any],
    motivo: str | None = None,
) -> None:
    limpio = {
        k: _iso(v)
        for k, v in after.items()
        if k in _CLAVES_AUDITORIA and v is not None
    }
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD,
        entity_id=expediente_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=limpio,
        reason=motivo,
    )


def _err(campo: str, mensaje: str) -> KontrolError:
    return KontrolError(
        code="GOV_PROCUREMENT_FILE_INVALID",
        message="Datos del expediente inválidos",
        field_errors={campo: [mensaje]},
        status_code=422,
    )


def _para_escribir(
    db: Session, ctx: CompanyContext, id: str, version: int | None
) -> GovernmentProcurementFile:
    if version is None:
        raise KontrolError(
            code="GOV_PROCUREMENT_FILE_IF_MATCH_REQUIRED",
            message="Se requiere la versión del expediente",
            status_code=428,
        )
    expediente = db.scalar(
        select(GovernmentProcurementFile)
        .where(
            GovernmentProcurementFile.id == id,
            GovernmentProcurementFile.company_id == ctx.company_id,
        )
        .with_for_update()
    )
    if expediente is None:
        raise NotFoundError(
            "GOV_PROCUREMENT_FILE_NOT_FOUND", "Expediente no encontrado"
        )
    if expediente.version != version:
        raise ConflictError(
            "GOV_PROCUREMENT_FILE_STALE",
            "El expediente fue modificado por otro usuario",
            details={"version_actual": expediente.version},
        )
    return expediente


def _abierto(expediente: GovernmentProcurementFile) -> None:
    if expediente.status != "ABIERTO":
        raise ConflictError(
            "GOV_PROCUREMENT_FILE_NOT_OPEN", "El expediente no está en curso"
        )


def _evento(
    db: Session,
    ctx: CompanyContext,
    expediente: GovernmentProcurementFile,
    clase: str,
    fecha: date,
    titulo: str,
    **campos: Any,
) -> GovernmentProcurementFileEvent:
    max_sec = db.scalar(
        select(func.max(GovernmentProcurementFileEvent.secuencia)).where(
            GovernmentProcurementFileEvent.file_id == expediente.id,
            GovernmentProcurementFileEvent.company_id == ctx.company_id,
        )
    )
    secuencia = (max_sec or 0) + 1
    evento = GovernmentProcurementFileEvent(
        company_id=ctx.company_id,
        file_id=expediente.id,
        secuencia=secuencia,
        clase=clase,
        fecha=fecha,
        titulo=titulo,
        estado_expediente=expediente.status,
        created_by=ctx.user_id,
        **campos,
    )
    db.add(evento)
    db.flush()
    return evento


def _funcionario(
    db: Session, ctx: CompanyContext, id: str, campo: str
) -> GovernmentOfficial:
    oficial = db.scalar(
        select(GovernmentOfficial).where(
            GovernmentOfficial.id == id,
            GovernmentOfficial.company_id == ctx.company_id,
        )
    )
    if oficial is None or oficial.estado != "ACTIVO":
        raise _err(campo, "Funcionario no válido")
    return oficial


def _etiqueta_funcionario(
    db: Session, ctx: CompanyContext, oficial: GovernmentOfficial, fecha: date
) -> tuple[str, str | None, str | None]:
    ocupaciones = ocupaciones_de_funcionario(db, ctx, str(oficial.id), fecha)
    cargo: str | None = None
    unidad: str | None = None
    for ocupacion in ocupaciones:
        if ocupacion.get("ejerce"):
            cargo_info = ocupacion.get("cargo") or {}
            cargo = cargo_info.get("nombre")
            unidad = cargo_info.get("unidad")
            break
    return oficial.nombre, cargo, unidad


def _texto_responsable(nombre: str, cargo: str | None, unidad: str | None) -> str:
    partes = [p for p in (nombre, cargo, unidad) if p]
    return " · ".join(partes)


def _acto_valido(db: Session, ctx: CompanyContext, id: str) -> GovernmentAct:
    acto = db.scalar(
        select(GovernmentAct).where(
            GovernmentAct.id == id,
            GovernmentAct.company_id == ctx.company_id,
        )
    )
    if acto is None or acto.status not in ("EMITIDO", "EFICAZ"):
        raise _err("acto_id", "Acto no válido")
    return acto


def _nombre_modulo(codigo: str) -> str:
    return dict(_ETIQUETAS_MODALIDAD).get(codigo, codigo)


def _campo_valido(campo: str, valor: str | None) -> str | None:
    if valor is None:
        return None
    limpio = valor.strip()
    return limpio or None


def catalogo() -> dict[str, Any]:
    return {
        "tipos": [{"codigo": k, "etiqueta": v} for k, v in _ETIQUETAS_TIPO.items()],
        "modalidades": [
            {"codigo": k, "etiqueta": v} for k, v in _ETIQUETAS_MODALIDAD.items()
        ],
        "roles": [{"codigo": k, "etiqueta": v} for k, v in _ETIQUETAS_ROL.items()],
        "estados": [{"codigo": k, "etiqueta": v} for k, v in _ETIQUETAS_ESTADO.items()],
        "clases_evento": [
            {"codigo": k, "etiqueta": v} for k, v in _ETIQUETAS_EVENTO.items()
        ],
        "clases_folio": [
            {
                "codigo": codigo,
                "etiqueta": etiqueta,
                "fuente": fuente,
                "grupo": grupo,
                "condicional": condicional,
            }
            for codigo, etiqueta, fuente, grupo, condicional in CLASES_FOLIO
        ],
        "aviso_modalidad": _AVISO_MODALIDAD,
        "aviso_lapsos": _AVISO_LAPSOS,
    }


def opciones(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    hoy = hoy_de_negocio()
    oficiales = db.scalars(
        select(GovernmentOfficial)
        .where(
            GovernmentOfficial.company_id == ctx.company_id,
            GovernmentOfficial.estado == "ACTIVO",
        )
        .order_by(GovernmentOfficial.nombre)
    ).all()
    funcionarios = []
    for oficial in oficiales:
        ocupaciones = ocupaciones_de_funcionario(db, ctx, str(oficial.id), hoy)
        cargos: list[str] = []
        unidades: list[str] = []
        for ocupacion in ocupaciones:
            if not ocupacion.get("ejerce"):
                continue
            cargo_info = ocupacion.get("cargo") or {}
            nombre_cargo = cargo_info.get("nombre")
            nombre_unidad = cargo_info.get("unidad")
            if nombre_cargo and nombre_cargo not in cargos:
                cargos.append(nombre_cargo)
            if nombre_unidad and nombre_unidad not in unidades:
                unidades.append(nombre_unidad)
        funcionarios.append(
            {
                "id": str(oficial.id),
                "nombre": oficial.nombre,
                "cargos": cargos,
                "unidades": unidades,
            }
        )
    unidades_orm = db.scalars(
        select(GovernmentUnit)
        .join(
            GovernmentStructure,
            GovernmentStructure.id == GovernmentUnit.structure_id,
        )
        .where(
            GovernmentUnit.company_id == ctx.company_id,
            GovernmentUnit.status == "ACTIVA",
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.exercise == hoy.year,
            GovernmentStructure.status == "VIGENTE",
        )
        .order_by(GovernmentUnit.name)
    ).all()
    comisiones_orm = db.scalars(
        select(GovernmentProcurementCommittee)
        .where(
            GovernmentProcurementCommittee.company_id == ctx.company_id,
            GovernmentProcurementCommittee.status == "VIGENTE",
        )
        .order_by(GovernmentProcurementCommittee.nombre)
    ).all()
    comisiones = []
    for comision in comisiones_orm:
        if situacion_de(comision, hoy) != "EN_VIGOR":
            continue
        comisiones.append(
            {
                "id": str(comision.id),
                "codigo": comision.codigo,
                "nombre": comision.nombre,
            }
        )
    actos_orm = db.scalars(
        select(GovernmentAct)
        .where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.status.in_(("EMITIDO", "EFICAZ")),
        )
        .order_by(GovernmentAct.fecha.desc())
    ).all()
    actos = []
    for acto in actos_orm:
        ref = _acto_ref(db, acto)
        if ref:
            actos.append({"id": str(ref["id"]), "etiqueta": ref["etiqueta"]})
    return {
        "funcionarios": funcionarios,
        "unidades": [
            {"id": str(u.id), "nombre": u.name} for u in unidades_orm
        ],
        "comisiones": comisiones,
        "actos": actos,
    }


def _principales(
    db: Session, ctx: CompanyContext, ids: Sequence[str], hoy: date
) -> dict[str, str]:
    if not ids:
        return {}
    filas = db.scalars(
        select(GovernmentProcurementFileResponsible).where(
            GovernmentProcurementFileResponsible.company_id == ctx.company_id,
            GovernmentProcurementFileResponsible.file_id.in_(ids),
            GovernmentProcurementFileResponsible.rol == "RESPONSABLE",
        )
    ).all()
    resultado: dict[str, str] = {}
    for fila in filas:
        fin = fila.fin_efectivo
        if fin is not None and fin < hoy:
            continue
        if fila.file_id not in resultado:
            resultado[fila.file_id] = _texto_responsable(
                fila.funcionario_nombre, fila.cargo_nombre, fila.unidad_nombre
            )
    return resultado


def _proximo_hitos(
    db: Session, ctx: CompanyContext, ids: Sequence[str]
) -> dict[str, GovernmentProcurementFileMilestone]:
    if not ids:
        return {}
    filas = db.scalars(
        select(GovernmentProcurementFileMilestone)
        .where(
            GovernmentProcurementFileMilestone.company_id == ctx.company_id,
            GovernmentProcurementFileMilestone.file_id.in_(ids),
            GovernmentProcurementFileMilestone.estado == "PREVISTO",
        )
        .order_by(
            GovernmentProcurementFileMilestone.file_id,
            GovernmentProcurementFileMilestone.fecha_prevista,
        )
    ).all()
    resultado: dict[str, GovernmentProcurementFileMilestone] = {}
    for fila in filas:
        if fila.file_id not in resultado:
            resultado[fila.file_id] = fila
    return resultado


def _codigos_comision(
    db: Session, ctx: CompanyContext, expedientes: Sequence[GovernmentProcurementFile]
) -> dict[str, str]:
    ids = [c.committee_id for c in expedientes if c.committee_id]
    if not ids:
        return {}
    comisiones = db.scalars(
        select(GovernmentProcurementCommittee).where(
            GovernmentProcurementCommittee.company_id == ctx.company_id,
            GovernmentProcurementCommittee.id.in_(ids),
        )
    ).all()
    por_id = {str(c.id): c.codigo for c in comisiones}
    resultado: dict[str, str] = {}
    for expediente in expedientes:
        if expediente.committee_id and expediente.committee_id in por_id:
            resultado[str(expediente.id)] = por_id[str(expediente.committee_id)]
    return resultado


def _resumen(
    expediente: GovernmentProcurementFile,
    *,
    responsable: str | None,
    comision: str | None,
    proximo_hito: GovernmentProcurementFileMilestone | None,
) -> dict[str, Any]:
    hoy = hoy_de_negocio()
    proximo = None
    if proximo_hito is not None:
        proximo = {
            "nombre": proximo_hito.nombre,
            "fecha_prevista": proximo_hito.fecha_prevista,
            "fecha_superada": proximo_hito.fecha_prevista < hoy,
        }
    return {
        "id": str(expediente.id),
        "numero": expediente.numero,
        "objeto": expediente.objeto,
        "fecha_inicio": expediente.fecha_inicio,
        "tipo_contratacion": expediente.tipo_contratacion,
        "tipo_etiqueta": _ETIQUETAS_TIPO.get(
            expediente.tipo_contratacion, expediente.tipo_contratacion
        ),
        "modalidad_declarada": expediente.modalidad_declarada,
        "modalidad_etiqueta": (
            _ETIQUETAS_MODALIDAD.get(expediente.modalidad_declarada)
            if expediente.modalidad_declarada
            else None
        ),
        "unidad_id": str(expediente.unidad_id),
        "unidad_nombre": expediente.unidad_nombre,
        "responsable": responsable,
        "comision": comision,
        "status": expediente.status,
        "status_etiqueta": _ETIQUETAS_ESTADO.get(expediente.status, expediente.status),
        "proximo_hito": proximo,
        "version": expediente.version,
    }


def listar(
    db: Session,
    ctx: CompanyContext,
    *,
    q: str | None = None,
    status: str | None = None,
    unidad_id: str | None = None,
    responsable_id: str | None = None,
    modalidad: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int = 1,
    por_pagina: int = 25,
) -> dict[str, Any]:
    hoy = hoy_de_negocio()
    hoy_dt = hoy
    condiciones = [GovernmentProcurementFile.company_id == ctx.company_id]
    if q:
        condiciones.append(
            or_(
                GovernmentProcurementFile.numero.icontains(q, autoescape=True),
                GovernmentProcurementFile.objeto.icontains(q, autoescape=True),
            )
        )
    if status:
        condiciones.append(GovernmentProcurementFile.status == status)
    if unidad_id:
        condiciones.append(GovernmentProcurementFile.unidad_id == unidad_id)
    if modalidad:
        condiciones.append(GovernmentProcurementFile.modalidad_declarada == modalidad)
    if desde:
        condiciones.append(GovernmentProcurementFile.fecha_inicio >= desde)
    if hasta:
        condiciones.append(GovernmentProcurementFile.fecha_inicio <= hasta)
    if responsable_id:
        subq = select(GovernmentProcurementFileResponsible.file_id).where(
            GovernmentProcurementFileResponsible.company_id == ctx.company_id,
            GovernmentProcurementFileResponsible.official_id == responsable_id,
            GovernmentProcurementFileResponsible.rol == "RESPONSABLE",
            or_(
                GovernmentProcurementFileResponsible.fin_efectivo.is_(None),
                GovernmentProcurementFileResponsible.fin_efectivo >= hoy_dt,
            ),
        )
        condiciones.append(GovernmentProcurementFile.id.in_(subq))
    total = db.scalar(
        select(func.count()).select_from(
            select(GovernmentProcurementFile.id)
            .where(*condiciones)
            .subquery()
        )
    ) or 0
    offset = max(pagina - 1, 0) * por_pagina
    filas = db.scalars(
        select(GovernmentProcurementFile)
        .where(*condiciones)
        .order_by(
            GovernmentProcurementFile.fecha_inicio.desc(),
            GovernmentProcurementFile.numero.desc(),
        )
        .offset(offset)
        .limit(por_pagina)
    ).all()
    ids = [f.id for f in filas]
    responsables = _principales(db, ctx, [str(x) for x in ids], hoy)
    hitos = _proximo_hitos(db, ctx, [str(x) for x in ids])
    comisiones = _codigos_comision(db, ctx, filas)
    items = [
        _resumen(
            f,
            responsable=responsables.get(str(f.id)),
            comision=comisiones.get(str(f.id)),
            proximo_hito=hitos.get(str(f.id)),
        )
        for f in filas
    ]
    return {
        "items": items,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
    }


def _cargar(
    db: Session, ctx: CompanyContext, id: str
) -> GovernmentProcurementFile:
    expediente = db.scalar(
        select(GovernmentProcurementFile).where(
            GovernmentProcurementFile.id == id,
            GovernmentProcurementFile.company_id == ctx.company_id,
        )
    )
    if expediente is None:
        raise NotFoundError(
            "GOV_PROCUREMENT_FILE_NOT_FOUND", "Expediente no encontrado"
        )
    return expediente


def _validar_funcionario_texto(
    db: Session, ctx: CompanyContext, id: str | None, campo: str, hoy: date
) -> str | None:
    if not id:
        return None
    oficial = _funcionario(db, ctx, id, campo)
    nombre, cargo, unidad = _etiqueta_funcionario(db, ctx, oficial, hoy)
    return _texto_responsable(nombre, cargo, unidad)


def detalle(db: Session, ctx: CompanyContext, id: str) -> dict[str, Any]:
    hoy = hoy_de_negocio()
    expediente = _cargar(db, ctx, id)

    responsables_orm = db.scalars(
        select(GovernmentProcurementFileResponsible)
        .where(
            GovernmentProcurementFileResponsible.company_id == ctx.company_id,
            GovernmentProcurementFileResponsible.file_id == expediente.id,
        )
        .order_by(
            GovernmentProcurementFileResponsible.fin_efectivo.is_(None).desc(),
            GovernmentProcurementFileResponsible.desde,
        )
    ).all()
    hitos_orm = db.scalars(
        select(GovernmentProcurementFileMilestone)
        .where(
            GovernmentProcurementFileMilestone.company_id == ctx.company_id,
            GovernmentProcurementFileMilestone.file_id == expediente.id,
        )
        .order_by(GovernmentProcurementFileMilestone.fecha_prevista)
    ).all()
    folios_orm = db.scalars(
        select(GovernmentProcurementFileFolio)
        .where(
            GovernmentProcurementFileFolio.company_id == ctx.company_id,
            GovernmentProcurementFileFolio.file_id == expediente.id,
        )
        .order_by(GovernmentProcurementFileFolio.numero)
    ).all()
    eventos_orm = db.scalars(
        select(GovernmentProcurementFileEvent)
        .where(
            GovernmentProcurementFileEvent.company_id == ctx.company_id,
            GovernmentProcurementFileEvent.file_id == expediente.id,
        )
        .order_by(
            GovernmentProcurementFileEvent.fecha.desc(),
            GovernmentProcurementFileEvent.secuencia.desc(),
        )
    ).all()

    hitos_por_id = {str(h.id): h for h in hitos_orm}


    usuario_ids = {expediente.created_by}
    usuario_ids.update(f.created_by for f in folios_orm if f.created_by)
    usuarios = _usuarios_por_ids(
        db, [u for u in usuario_ids if u], ctx.tenant_id
    )

    principal_vigente: GovernmentProcurementFileResponsible | None = None
    responsables_out: list[dict[str, Any]] = []
    for fila in responsables_orm:
        fin_efectivo = fila.fin_efectivo
        vigente = fin_efectivo is None or fin_efectivo >= hoy
        if vigente and fila.rol == "RESPONSABLE" and principal_vigente is None:
            principal_vigente = fila
        responsables_out.append(
            {
                "id": str(fila.id),
                "funcionario_id": str(fila.official_id),
                "rol": fila.rol,
                "rol_etiqueta": _ETIQUETAS_ROL.get(fila.rol, fila.rol),
                "nombre": fila.funcionario_nombre,
                "cargo": fila.cargo_nombre,
                "unidad": fila.unidad_nombre,
                "desde": fila.desde,
                "fin_efectivo": fin_efectivo,
                "motivo_fin": fila.motivo_fin,
                "vigente": vigente,
            }
        )

    hitos_out: list[dict[str, Any]] = []
    for hito in hitos_orm:
        estado = hito.estado
        hitos_out.append(
            {
                "id": str(hito.id),
                "nombre": hito.nombre,
                "fuente": hito.fuente,
                "fecha_prevista": hito.fecha_prevista,
                "fecha_real": hito.fecha_real,
                "estado": estado,
                "estado_etiqueta": _ETIQUETAS_ESTADO_HITO.get(estado, estado),
                "fecha_superada": (
                    estado == "PREVISTO" and hito.fecha_prevista < hoy
                ),
                "funcionario_id": (
                    str(hito.official_id) if hito.official_id else None
                ),
                "responsable": hito.responsable_etiqueta,
                "motivo_no_aplica": hito.motivo_no_aplica,
            }
        )

    folios_out: list[dict[str, Any]] = []
    for folio in folios_orm:
        hito_ref = (
            hitos_por_id.get(folio.milestone_id) if folio.milestone_id else None
        )
        folios_out.append(
            {
                "id": str(folio.id),
                "numero": folio.numero,
                "clase": folio.clase,
                "clase_etiqueta": _SECCION_ETIQUETAS.get(folio.clase, folio.clase),
                "tipo_etiqueta": folio.tipo_etiqueta,
                "etiqueta": folio.etiqueta,
                "documento_id": (
                    str(folio.document_id) if folio.document_id else None
                ),
                "acto_id": str(folio.act_id) if folio.act_id else None,
                "version_numero": folio.version_numero,
                "fecha_documento": folio.fecha_documento,
                "fecha_incorporacion": folio.fecha_incorporacion,
                "incorporado_por": (
                    usuarios.get(folio.created_by) if folio.created_by else None
                ),
                "reservado": folio.reservado,
                "motivo_reserva": folio.motivo_reserva,
                "hito": hito_ref.nombre if hito_ref else None,
            }
        )

    conteo: dict[str, int] = {codigo: 0 for codigo in _CLASES_FOLIO_CODIGOS}
    for folio in folios_orm:
        if folio.clase in conteo:
            conteo[folio.clase] += 1
    contenido = [
        {
            "clase": codigo,
            "etiqueta": etiqueta,
            "fuente": fuente,
            "grupo": grupo,
            "condicional": condicional,
            "folios": conteo[codigo],
        }
        for codigo, etiqueta, fuente, grupo, condicional in CLASES_FOLIO
    ]

    pendientes: list[dict[str, str]] = []
    siguiente_accion: str | None = None
    ofertas_total = db.scalar(
        select(func.count(GovernmentProcurementOffer.id)).where(
            GovernmentProcurementOffer.file_id == expediente.id,
            GovernmentProcurementOffer.company_id == expediente.company_id,
        )
    ) or 0
    ofertas_selladas = db.scalar(
        select(func.count(GovernmentProcurementOffer.id)).where(
            GovernmentProcurementOffer.file_id == expediente.id,
            GovernmentProcurementOffer.company_id == expediente.company_id,
            GovernmentProcurementOffer.confidencial.is_(True),
        )
    ) or 0
    if expediente.status == "ABIERTO":
        if not expediente.partes:
            pendientes.append(
                {
                    "codigo": "PARTES",
                    "texto": "Identifique las partes (LCP art. 19)",
                }
            )
        if principal_vigente is None:
            pendientes.append(
                {
                    "codigo": "RESPONSABLE",
                    "texto": "Asigne un responsable del expediente",
                }
            )
        elif principal_vigente.official_id:
            ocupaciones = ocupaciones_de_funcionario(
                db, ctx, principal_vigente.official_id, hoy
            )
            if not any(o.get("ejerce") for o in ocupaciones):
                pendientes.append(
                    {
                        "codigo": "RESPONSABLE_SIN_CARGO",
                        "texto": "El responsable no ejerce cargo hoy",
                    }
                )
        if not expediente.modalidad_declarada or not expediente.modalidad_fundamento:
            pendientes.append(
                {
                    "codigo": "MODALIDAD",
                    "texto": "Declare la modalidad y su fundamento",
                }
            )
        if not expediente.committee_id and not expediente.comision_no_aplica_motivo:
            pendientes.append(
                {
                    "codigo": "COMISION",
                    "texto": (
                        "Vincule la comisión o declare que no interviene (RLCP art. 33)"
                    ),
                }
            )
        for hito in hitos_orm:
            if hito.estado == "PREVISTO" and hito.fecha_prevista < hoy:
                pendientes.append(
                    {
                        "codigo": "HITO_SUPERADO",
                        "texto": f"Fecha prevista superada: {hito.nombre}",
                    }
                )
        if not hitos_orm:
            pendientes.append(
                {
                    "codigo": "SIN_HITOS",
                    "texto": "Registre los hitos del procedimiento",
                }
            )
        if not conteo.get("SOLICITUD"):
            pendientes.append(
                {
                    "codigo": "CONTENIDO_SOLICITUD",
                    "texto": "Incorpore la solicitud de la unidad usuaria",
                }
            )
        if not conteo.get("AUTORIZACION_INICIO"):
            pendientes.append(
                {
                    "codigo": "CONTENIDO_INICIO",
                    "texto": "Incorpore la autorización o acta de inicio",
                }
            )
        if ofertas_total and expediente.status not in ("CERRADO", "DESCARTADO"):
            ofertas_abiertas = (
                db.query(GovernmentProcurementOpeningOffer)
                .filter(
                    GovernmentProcurementOpeningOffer.company_id == ctx.company_id,
                    GovernmentProcurementOpeningOffer.offer_id.in_(
                        db.query(GovernmentProcurementOffer.id).filter(
                            GovernmentProcurementOffer.company_id == ctx.company_id,
                            GovernmentProcurementOffer.file_id == expediente.id,
                        )
                    ),
                )
                .count()
            )
            if ofertas_abiertas == 0:
                pendientes.insert(
                    0,
                    {
                        "codigo": "APERTURA_PENDIENTE",
                        "texto": "Pendiente de apertura",
                    },
                )
            elif expediente.evaluacion_concluida_en is None:
                pendientes.insert(
                    0,
                    {
                        "codigo": "EVALUACION_PENDIENTE",
                        "texto": "Evaluación de ofertas en curso",
                    },
                )
            else:
                pendientes.insert(
                    0,
                    {
                        "codigo": "RECOMENDACION_PENDIENTE",
                        "texto": "Preparar recomendación",
                    },
                )
        if pendientes:
            siguiente_accion = pendientes[0]["texto"]
        else:
            proximo = next(
                (h for h in hitos_orm if h.estado == "PREVISTO"), None
            )
            if proximo is not None:
                siguiente_accion = f"Próximo hito: {proximo.nombre}"
            else:
                sin_folio = None
                for codigo in _CLASES_SELECCION_NO_CONDICIONAL:
                    if not conteo.get(codigo):
                        sin_folio = codigo
                        break
                if sin_folio is not None:
                    siguiente_accion = (
                        f"Incorporar: {_SECCION_ETIQUETAS[sin_folio]}"
                    )

    ultima_orm: GovernmentProcurementFileEvent | None = None
    for evento in eventos_orm:
        if evento.clase in ("ACTUACION", "DECISION"):
            ultima_orm = evento
            break
    ultima = None
    if ultima_orm is not None:
        ultima = {
            "fecha": ultima_orm.fecha,
            "titulo": ultima_orm.titulo,
            "clase_etiqueta": _ETIQUETAS_EVENTO.get(
                ultima_orm.clase, ultima_orm.clase
            ),
        }

    actuaciones = sum(1 for e in eventos_orm if e.clase == "ACTUACION")
    decisiones = sum(1 for e in eventos_orm if e.clase == "DECISION")

    comision_detalle = None
    if expediente.committee_id:
        comision = db.scalar(
            select(GovernmentProcurementCommittee).where(
                GovernmentProcurementCommittee.company_id == ctx.company_id,
                GovernmentProcurementCommittee.id == expediente.committee_id,
            )
        )
        if comision is not None:
            situacion = situacion_de(comision, hoy)
            etiquetas = ETIQUETAS_COMISION["situaciones"]
            comision_detalle = {
                "id": str(comision.id),
                "codigo": comision.codigo,
                "nombre": comision.nombre,
                "situacion": situacion,
                "situacion_etiqueta": etiquetas.get(situacion, situacion),
            }

    principal_texto = (
        _texto_responsable(
            principal_vigente.funcionario_nombre,
            principal_vigente.cargo_nombre,
            principal_vigente.unidad_nombre,
        )
        if principal_vigente
        else None
    )
    comision_codigo = comision_detalle["codigo"] if comision_detalle else None
    proximo_hito_orm = next(
        (h for h in hitos_orm if h.estado == "PREVISTO"), None
    )
    base = _resumen(
        expediente,
        responsable=principal_texto,
        comision=comision_codigo,
        proximo_hito=proximo_hito_orm,
    )
    base.update(
        {
            "partes": expediente.partes,
            "modalidad_fundamento": expediente.modalidad_fundamento,
            "modalidad_fuente": expediente.modalidad_fuente,
            "comision_no_aplica_motivo": expediente.comision_no_aplica_motivo,
            "cierre_motivo": expediente.cierre_motivo,
            "cierre_fecha": expediente.cierre_fecha,
            "comision_detalle": comision_detalle,
            "responsables": responsables_out,
            "hitos": hitos_out,
            "folios": folios_out,
            "contenido": contenido,
            "pendientes": pendientes,
            "siguiente_accion": siguiente_accion,
            "ultima_actuacion": ultima,
            "ofertas_total": ofertas_total,
            "ofertas_selladas": ofertas_selladas,
            "recepcion_concluida_en": expediente.recepcion_concluida_en,
            "totales": {
                "actuaciones": actuaciones,
                "decisiones": decisiones,
                "folios": len(folios_out),
                "hitos": len(hitos_out),
            },
            "creado_por": usuarios.get(expediente.created_by)
            if expediente.created_by
            else None,
            "creado_en": expediente.created_at,
        }
    )
    return base


def cronologia(
    db: Session,
    ctx: CompanyContext,
    id: str,
    *,
    clases: list[str] | None = None,
    pagina: int = 1,
    por_pagina: int = 50,
) -> dict[str, Any]:
    expediente = _cargar(db, ctx, id)
    condiciones: list[Any] = [
        GovernmentProcurementFileEvent.company_id == ctx.company_id,
        GovernmentProcurementFileEvent.file_id == expediente.id,
    ]
    if clases:
        condiciones.append(GovernmentProcurementFileEvent.clase.in_(clases))
    total = db.scalar(
        select(func.count())
        .select_from(GovernmentProcurementFileEvent)
        .where(*condiciones)
    ) or 0
    offset = max(pagina - 1, 0) * por_pagina
    eventos = db.scalars(
        select(GovernmentProcurementFileEvent)
        .where(*condiciones)
        .order_by(
            GovernmentProcurementFileEvent.fecha.asc(),
            GovernmentProcurementFileEvent.secuencia.asc(),
        )
        .offset(offset)
        .limit(por_pagina)
    ).all()

    evento_ids = [e.id for e in eventos]
    rectifica_map: dict[str, int] = {}
    rectificado_map: dict[str, int] = {}
    if evento_ids:
        rectif_ids = {e.rectifica_id for e in eventos if e.rectifica_id}
        if rectif_ids:
            referenciados = db.scalars(
                select(GovernmentProcurementFileEvent).where(
                    GovernmentProcurementFileEvent.company_id == ctx.company_id,
                    GovernmentProcurementFileEvent.file_id == expediente.id,
                    GovernmentProcurementFileEvent.id.in_(rectif_ids),
                )
            ).all()
            por_id = {str(e.id): e.secuencia for e in referenciados}
            for evento in eventos:
                if evento.rectifica_id and str(evento.rectifica_id) in por_id:
                    rectifica_map[str(evento.id)] = por_id[str(evento.rectifica_id)]
        rectificados = db.scalars(
            select(GovernmentProcurementFileEvent).where(
                GovernmentProcurementFileEvent.company_id == ctx.company_id,
                GovernmentProcurementFileEvent.file_id == expediente.id,
                GovernmentProcurementFileEvent.rectifica_id.in_(evento_ids),
            )
        ).all()
        for evento in rectificados:
            if evento.rectifica_id:
                rectificado_map[evento.rectifica_id] = evento.secuencia

    usuario_ids = {e.created_by for e in eventos if e.created_by}
    usuarios = _usuarios_por_ids(
        db, list(usuario_ids), ctx.tenant_id
    )

    items = [
        {
            "id": str(evento.id),
            "secuencia": evento.secuencia,
            "fecha": evento.fecha,
            "clase": evento.clase,
            "clase_etiqueta": _ETIQUETAS_EVENTO.get(evento.clase, evento.clase),
            "titulo": evento.titulo,
            "detalle": evento.detalle,
            "resultado": evento.resultado,
            "responsable": evento.responsable_etiqueta,
            "acto_id": str(evento.act_id) if evento.act_id else None,
            "acto_etiqueta": evento.acto_etiqueta,
            "folio_id": str(evento.folio_id) if evento.folio_id else None,
            "folio_etiqueta": evento.folio_etiqueta,
            "hito_etiqueta": evento.hito_etiqueta,
            "estado_expediente": evento.estado_expediente,
            "estado_etiqueta": _ETIQUETAS_ESTADO.get(
                evento.estado_expediente, evento.estado_expediente
            ),
            "actor": usuarios.get(evento.created_by)
            if evento.created_by
            else None,
            "registrado_en": evento.created_at,
            "motivo": evento.motivo,
            "rectifica_secuencia": rectifica_map.get(str(evento.id)),
            "rectificada_por_secuencia": rectificado_map.get(str(evento.id)),
        }
        for evento in eventos
    ]
    return {
        "items": items,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
    }


def _validar_datos_expediente(
    db: Session,
    ctx: CompanyContext,
    *,
    numero: str,
    objeto: str,
    fecha_inicio: date,
    modalidad_declarada: str | None,
    modalidad_fundamento: str | None,
    unidad_id: str,
    hoy: date,
) -> GovernmentUnit:
    if fecha_inicio > hoy:
        raise _err("fecha_inicio", "La fecha de inicio no puede ser futura")
    if not numero:
        raise _err("numero", "El número es obligatorio")
    if not objeto:
        raise _err("objeto", "El objeto es obligatorio")
    if modalidad_declarada and not modalidad_fundamento:
        raise _err(
            "modalidad_fundamento",
            "La modalidad declarada exige fundamento",
        )
    unidad = db.scalar(
        select(GovernmentUnit).where(
            GovernmentUnit.id == unidad_id,
            GovernmentUnit.company_id == ctx.company_id,
        )
    )
    if unidad is None or unidad.status != "ACTIVA":
        raise _err("unidad_id", "Unidad no válida")
    return unidad


def _verificar_numero(
    db: Session, ctx: CompanyContext, numero: str, excluir_id: str | None
) -> None:
    condiciones = [
        GovernmentProcurementFile.company_id == ctx.company_id,
        GovernmentProcurementFile.numero == numero,
    ]
    if excluir_id is not None:
        condiciones.append(GovernmentProcurementFile.id != excluir_id)
    existe = db.scalar(
        select(GovernmentProcurementFile.id).where(*condiciones).limit(1)
    )
    if existe is not None:
        raise ConflictError(
            "GOV_PROCUREMENT_FILE_NUMERO_DUPLICADO",
            "Ya existe un expediente con ese número",
        )


def crear(
    db: Session, ctx: CompanyContext, datos: dict[str, Any]
) -> dict[str, Any]:
    hoy = hoy_de_negocio()
    numero = datos["numero"]
    objeto = datos["objeto"]
    fecha_inicio = datos["fecha_inicio"]
    unidad = _validar_datos_expediente(
        db,
        ctx,
        numero=numero,
        objeto=objeto,
        fecha_inicio=fecha_inicio,
        modalidad_declarada=datos.get("modalidad_declarada"),
        modalidad_fundamento=datos.get("modalidad_fundamento"),
        unidad_id=datos["unidad_id"],
        hoy=hoy,
    )
    _verificar_numero(db, ctx, numero, None)
    responsable = _funcionario(db, ctx, datos["responsable_id"], "responsable_id")
    expediente = GovernmentProcurementFile(
        company_id=ctx.company_id,
        numero=numero,
        objeto=objeto,
        fecha_inicio=fecha_inicio,
        partes=_campo_valido("partes", datos.get("partes")),
        tipo_contratacion=datos["tipo_contratacion"],
        modalidad_declarada=datos.get("modalidad_declarada"),
        modalidad_fundamento=_campo_valido(
            "modalidad_fundamento", datos.get("modalidad_fundamento")
        ),
        modalidad_fuente=_campo_valido(
            "modalidad_fuente", datos.get("modalidad_fuente")
        ),
        unidad_id=unidad.id,
        unidad_nombre=unidad.name,
        status="ABIERTO",
        version=1,
        created_by=ctx.user_id,
    )
    db.add(expediente)
    db.flush()

    nombre, cargo, unidad_txt = _etiqueta_funcionario(
        db, ctx, responsable, fecha_inicio
    )
    responsable_row = GovernmentProcurementFileResponsible(
        company_id=ctx.company_id,
        file_id=expediente.id,
        official_id=responsable.id,
        rol="RESPONSABLE",
        funcionario_nombre=nombre,
        cargo_nombre=cargo,
        unidad_nombre=unidad_txt,
        desde=fecha_inicio,
        created_by=ctx.user_id,
    )
    db.add(responsable_row)
    db.flush()

    _evento(
        db,
        ctx,
        expediente,
        "APERTURA",
        fecha_inicio,
        f"Expediente {numero} abierto",
        responsable_etiqueta=_texto_responsable(nombre, cargo, unidad_txt),
    )
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_FILE_CREATED",
        expediente_id=str(expediente.id),
        after={
            "numero": numero,
            "fecha": fecha_inicio,
            "modalidad": datos.get("modalidad_declarada"),
            "version": expediente.version,
            "titulo": f"Expediente {numero} abierto",
        },
    )
    return detalle(db, ctx, str(expediente.id))


def editar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
    datos: dict[str, Any],
) -> dict[str, Any]:
    hoy = hoy_de_negocio()
    expediente = _para_escribir(db, ctx, id, version)
    _abierto(expediente)
    motivo = datos["motivo"]
    if not motivo:
        raise _err("motivo", "El motivo es obligatorio")
    numero = datos["numero"]
    objeto = datos["objeto"]
    fecha_inicio = datos["fecha_inicio"]
    unidad = _validar_datos_expediente(
        db,
        ctx,
        numero=numero,
        objeto=objeto,
        fecha_inicio=fecha_inicio,
        modalidad_declarada=datos.get("modalidad_declarada"),
        modalidad_fundamento=datos.get("modalidad_fundamento"),
        unidad_id=datos["unidad_id"],
        hoy=hoy,
    )
    folios = db.scalar(
        select(func.count())
        .select_from(GovernmentProcurementFileFolio)
        .where(
            GovernmentProcurementFileFolio.company_id == ctx.company_id,
            GovernmentProcurementFileFolio.file_id == expediente.id,
        )
    ) or 0
    if folios and (
        numero != expediente.numero or fecha_inicio != expediente.fecha_inicio
    ):
        campo = "numero" if numero != expediente.numero else "fecha_inicio"
        raise KontrolError(
            code="GOV_PROCUREMENT_FILE_IDENTIDAD_FIJA",
            message="No puede cambiar la identidad del expediente con folios",
            field_errors={campo: ["El expediente ya tiene folios"]},
            status_code=422,
        )
    if numero != expediente.numero:
        _verificar_numero(db, ctx, numero, str(expediente.id))

    cambios: list[str] = []
    if expediente.numero != numero:
        cambios.append("Número")
        expediente.numero = numero
    if expediente.fecha_inicio != fecha_inicio:
        cambios.append("Fecha de inicio")
        expediente.fecha_inicio = fecha_inicio
    if expediente.objeto != objeto:
        cambios.append("Objeto")
        expediente.objeto = objeto
    partes = _campo_valido("partes", datos.get("partes"))
    if expediente.partes != partes:
        cambios.append("Partes")
        expediente.partes = partes
    if expediente.tipo_contratacion != datos["tipo_contratacion"]:
        cambios.append("Tipo de contratación")
        expediente.tipo_contratacion = datos["tipo_contratacion"]
    if expediente.modalidad_declarada != datos.get("modalidad_declarada"):
        cambios.append("Modalidad")
        expediente.modalidad_declarada = datos.get("modalidad_declarada")
    fundamento = _campo_valido(
        "modalidad_fundamento", datos.get("modalidad_fundamento")
    )
    if expediente.modalidad_fundamento != fundamento:
        cambios.append("Fundamento de modalidad")
        expediente.modalidad_fundamento = fundamento
    fuente = _campo_valido("modalidad_fuente", datos.get("modalidad_fuente"))
    if expediente.modalidad_fuente != fuente:
        cambios.append("Fuente de modalidad")
        expediente.modalidad_fuente = fuente
    if str(expediente.unidad_id) != str(unidad.id):
        cambios.append("Unidad")
        expediente.unidad_id = str(unidad.id)
        expediente.unidad_nombre = unidad.name

    if not cambios:
        return detalle(db, ctx, str(expediente.id))

    expediente.version += 1
    db.flush()
    _evento(
        db,
        ctx,
        expediente,
        "DATOS",
        hoy,
        "Datos del expediente modificados",
        detalle=", ".join(cambios),
        motivo=motivo,
    )
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_FILE_UPDATED",
        expediente_id=str(expediente.id),
        after={
            "numero": expediente.numero,
            "version": expediente.version,
            "titulo": "Datos del expediente modificados",
            "motivo": motivo,
        },
        motivo=motivo,
    )
    return detalle(db, ctx, str(expediente.id))
