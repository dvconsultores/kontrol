from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, NotFoundError
from app.modules.documents.models import (
    Document,
    DocumentLink,
    DocumentVersion,
)
from app.modules.documents.service import (
    assert_deliverable,
    congelar_vinculo,
    documento_sellado,
    sellar_documento,
    verificar_integridad,
)
from app.modules.government.models import (
    GovernmentProcurementFile,
    GovernmentProcurementFileFolio,
    GovernmentProcurementOffer,
    GovernmentProcurementOfferDocument,
)
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_expedientes import (
    _abierto,
    _auditar,
    _cargar,
    _err,
    _etiqueta_funcionario,
    _evento,
    _funcionario,
    _para_escribir,
    _texto_responsable,
)
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.government.service_sod_funciones import verificar_antes_de_asumir_funcion
from app.modules.identity_access.models import User

_CARACAS = ZoneInfo("America/Caracas")

_CANALES = {
    "ACTO_PUBLICO": "Acto público",
    "UNIDAD_CONTRATANTE": "Unidad contratante",
    "MEDIO_ELECTRONICO": "Medio electrónico",
}
_TIPOS_SOBRE = {
    "UNICO": "Sobre único",
    "CALIFICACION": "Sobre de calificación",
    "OFERTA": "Sobre de oferta",
}
_MODALIDADES_SELLO_OBLIGATORIO = {"CONCURSO_ABIERTO", "CONCURSO_CERRADO", None}


def _normalizar_documento(valor: str) -> str:
    return valor.upper().replace(" ", "").replace("-", "")


def _local_now() -> datetime:
    return datetime.now(UTC)


def _referencia(numero: int) -> str:
    return f"R-{numero:04d}"


def _integrity_for_row(db: Session, row: GovernmentProcurementOfferDocument) -> str:
    version = db.get(DocumentVersion, row.document_version_id)
    if version is None:
        return "SIN_ARCHIVO"
    if row.sha256 == version.sha256 and verificar_integridad(db, version):
        return "VERIFICADA"
    return "ALTERADA"


def _integrity_for_offer(db: Session, offer: GovernmentProcurementOffer) -> str:
    rows = db.scalars(
        select(GovernmentProcurementOfferDocument).where(
            GovernmentProcurementOfferDocument.offer_id == offer.id,
            GovernmentProcurementOfferDocument.company_id == offer.company_id,
        )
    ).all()
    statuses = {_integrity_for_row(db, row) for row in rows}
    if not rows:
        return "SIN_ARCHIVO"
    if "SIN_ARCHIVO" in statuses:
        return "SIN_ARCHIVO"
    if "ALTERADA" in statuses:
        return "ALTERADA"
    return "VERIFICADA"


def _serializar_oferta(db: Session, offer: GovernmentProcurementOffer,
                       *, ctx, con_documentos: bool = False) -> dict:
    from app.modules.government.models import GovernmentProcurementOpeningOffer

    abierta = (
        db.query(GovernmentProcurementOpeningOffer)
        .filter(
            GovernmentProcurementOpeningOffer.company_id == ctx.company_id,
            GovernmentProcurementOpeningOffer.offer_id == offer.id,
        )
        .one_or_none()
        is not None
    )
    data = {
        "id": offer.id,
        "referencia": _referencia(offer.numero),
        "oferente_nombre": offer.oferente_nombre,
        "oferente_documento": offer.oferente_documento,
        "identidad_etiqueta": "Identidad declarada, sin validar en RNC/SNC",
        "representante": offer.representante,
        "tipo_sobre": offer.tipo_sobre,
        "tipo_sobre_etiqueta": _TIPOS_SOBRE[offer.tipo_sobre],
        "canal": offer.canal,
        "canal_etiqueta": _CANALES[offer.canal],
        "recibida_en": offer.recibida_en,
        "registrada_en": offer.created_at,
        "receptor": offer.receptor_etiqueta,
        "registrado_por": _usuarios_por_ids(db, [offer.created_by], ctx.tenant_id).get(offer.created_by) if offer.created_by else None,
        "confidencial": offer.confidencial,
        "confidencialidad_etiqueta": (
            "Sello levantado en la apertura"
            if offer.confidencial and abierta
            else "Sellada hasta la apertura"
            if offer.confidencial
            else "Sin sello"
        ),
        "fundamento_confidencialidad": offer.fundamento_confidencialidad,
        "situacion": "ABIERTA" if abierta else "PENDIENTE_APERTURA",
        "situacion_etiqueta": "Abierta" if abierta else "Pendiente de apertura",
        "condicion_sobre": offer.condicion_sobre,
        "documentos_total": db.scalar(
            select(func.count(GovernmentProcurementOfferDocument.id)).where(
                GovernmentProcurementOfferDocument.offer_id == offer.id,
                GovernmentProcurementOfferDocument.company_id == offer.company_id,
            )
        ) or 0,
        "integridad": _integrity_for_offer(db, offer),
    }
    if con_documentos:
        documentos = []
        for row in db.scalars(
            select(GovernmentProcurementOfferDocument).where(
                GovernmentProcurementOfferDocument.offer_id == offer.id,
                GovernmentProcurementOfferDocument.company_id == offer.company_id,
            ).order_by(GovernmentProcurementOfferDocument.created_at)
        ).all():
            item = {
                "version_numero": row.version_numero,
                "huella": row.sha256,
                "integridad": _integrity_for_row(db, row),
            }
            if documento_sellado(db, row.document_id):
                item["documento_id"] = None
                item["titulo"] = None
            else:
                doc = db.get(Document, row.document_id)
                item["documento_id"] = row.document_id
                item["titulo"] = doc.title if doc else None
            documentos.append(item)
        data["documentos"] = documentos
    return data


def listar_ofertas(db: Session, ctx: CompanyContext, expediente_id: str) -> dict:
    expediente = _cargar(db, ctx, expediente_id)
    offers = db.scalars(
        select(GovernmentProcurementOffer).where(
            GovernmentProcurementOffer.file_id == expediente.id,
            GovernmentProcurementOffer.company_id == ctx.company_id,
        ).order_by(GovernmentProcurementOffer.numero)
    ).all()
    return {
        "items": [_serializar_oferta(db, o, ctx=ctx) for o in offers],
        "total": len(offers),
        "canales": [{"codigo": k, "etiqueta": v} for k, v in _CANALES.items()],
        "tipos_sobre": [{"codigo": k, "etiqueta": v} for k, v in _TIPOS_SOBRE.items()],
        "recepcion_concluida_en": expediente.recepcion_concluida_en,
        "puede_recibir_sin_sello": expediente.modalidad_declarada in ("CONSULTA_PRECIOS", "CONTRATACION_DIRECTA"),
        "aviso_identidad": "Identidad declarada, sin validar en RNC/SNC",
    }


def detalle_oferta(db: Session, ctx: CompanyContext, expediente_id: str,
                   oferta_id: str) -> dict:
    _cargar(db, ctx, expediente_id)
    offer = db.scalar(
        select(GovernmentProcurementOffer).where(
            GovernmentProcurementOffer.id == oferta_id,
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente_id,
        )
    )
    if offer is None:
        raise NotFoundError(code="GOV_PROCUREMENT_OFFER_NOT_FOUND", message="Oferta no encontrada")
    return _serializar_oferta(db, offer, ctx=ctx, con_documentos=True)


def _validar_documento(db: Session, ctx: CompanyContext, expediente: GovernmentProcurementFile,
                       doc_id: str) -> tuple[Document, DocumentVersion, DocumentLink]:
    doc = db.scalar(
        select(Document).where(Document.id == doc_id, Document.company_id == ctx.company_id)
    )
    if doc is None or doc.status not in ("DRAFT", "ACTIVE") or documento_sellado(db, doc_id):
        raise _err("documento_ids", "El documento no existe en este ente")
    if doc.current_version_id is None:
        raise _err("documento_ids", "El documento no tiene versión vigente")
    version = db.get(DocumentVersion, doc.current_version_id)
    if version is None or version.document_id != doc.id:
        raise _err("documento_ids", "El documento no tiene versión vigente")
    link = db.scalar(
        select(DocumentLink).where(
            DocumentLink.document_id == doc.id,
            DocumentLink.resource_type == "GovernmentProcurementFile",
            DocumentLink.resource_id == expediente.id,
        )
    )
    if link is None:
        raise _err("documento_ids", "El documento no está vinculado a este expediente")
    other_links = db.scalar(
        select(func.count(DocumentLink.id)).where(
            DocumentLink.document_id == doc.id,
            DocumentLink.id != link.id,
        )
    )
    if other_links:
        raise _err("documento_ids", "El documento está vinculado a otra entidad")
    existing_offer_doc = db.scalar(
        select(GovernmentProcurementOfferDocument).where(
            GovernmentProcurementOfferDocument.document_id == doc.id,
            GovernmentProcurementOfferDocument.company_id == ctx.company_id,
        )
    )
    if existing_offer_doc is not None:
        raise _err("documento_ids", "El documento ya está en otra oferta")
    folio = db.scalar(
        select(GovernmentProcurementFileFolio).where(
            GovernmentProcurementFileFolio.document_id == doc.id,
            GovernmentProcurementFileFolio.company_id == ctx.company_id,
        )
    )
    if folio is not None:
        raise _err("documento_ids", "El documento ya está foliado")
    return doc, version, link


def recibir_oferta(db: Session, ctx: CompanyContext, expediente_id: str,
                   entrada, version_if_match: int | None) -> dict:
    expediente = _para_escribir(db, ctx, expediente_id, version_if_match)
    _abierto(expediente)
    if expediente.recepcion_concluida_en is not None:
        raise ConflictError(
            code="GOV_PROCUREMENT_OFFER_RECEPTION_CONCLUDED",
            message="La recepción de ofertas ya concluyó",
        )
    evaluar_antes_de_actuar(db, ctx, "PROC03_RECIBIR", "GovernmentProcurementFile", str(expediente.id))

    nombre = entrada.oferente_nombre.strip()
    documento_bruto = entrada.oferente_documento.strip()
    if not nombre:
        raise _err("oferente_nombre", "El nombre es obligatorio")
    if not documento_bruto:
        raise _err("oferente_documento", "El documento es obligatorio")
    documento = _normalizar_documento(documento_bruto)
    if not documento:
        raise _err("oferente_documento", "El documento es obligatorio")

    if entrada.canal not in _CANALES:
        raise _err("canal", "Canal no válido")
    if entrada.tipo_sobre not in _TIPOS_SOBRE:
        raise _err("tipo_sobre", "Tipo de sobre no válido")
    if len(entrada.documento_ids) != len(set(entrada.documento_ids)):
        raise _err("documento_ids", "Hay documentos repetidos")

    if entrada.canal != "MEDIO_ELECTRONICO" and not entrada.documento_ids:
        if not entrada.condicion_sobre:
            raise _err("condicion_sobre", "Un sobre físico requiere condición")
    if entrada.canal == "MEDIO_ELECTRONICO" and not entrada.documento_ids:
        raise _err("documento_ids", "Medio electrónico requiere al menos un documento")

    modalidad = expediente.modalidad_declarada
    if modalidad in _MODALIDADES_SELLO_OBLIGATORIO:
        if not entrada.confidencial:
            raise _err("confidencial", "Esta modalidad exige sello")
        fundamento = "LCP art. 92: sobres sellados" if modalidad in ("CONCURSO_ABIERTO", "CONCURSO_CERRADO") else "Modalidad sin declarar: se protege hasta la apertura"
    else:
        if not entrada.confidencial and not entrada.motivo_sin_sello:
            raise _err("motivo_sin_sello", "Indique el motivo para no sellar")
        if entrada.confidencial:
            fundamento = "Decisión de la unidad"
        else:
            fundamento = entrada.motivo_sin_sello or ""

    if modalidad in ("CONCURSO_ABIERTO", "CONCURSO_CERRADO"):
        if not expediente.committee_id and not expediente.comision_no_aplica_motivo:
            raise _err("comision", "Un concurso requiere comisión o declaración de no intervención")

    recibida_en = entrada.recibida_en
    if recibida_en.tzinfo is None or recibida_en.utcoffset() is None:
        raise _err("recibida_en", "La fecha debe incluir zona horaria")
    recibida_caracas = recibida_en.astimezone(_CARACAS)
    if recibida_caracas > datetime.now(_CARACAS):
        raise _err("recibida_en", "La fecha no puede ser futura")
    fecha_inicio = expediente.fecha_inicio
    if fecha_inicio and recibida_caracas.date() < fecha_inicio:
        raise _err("recibida_en", "La fecha es anterior a la fecha de inicio")

    duplicado = db.scalar(
        select(GovernmentProcurementOffer).where(
            GovernmentProcurementOffer.file_id == expediente.id,
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.oferente_documento == documento,
            GovernmentProcurementOffer.tipo_sobre == entrada.tipo_sobre,
        )
    )
    if duplicado is not None:
        raise ConflictError(
            code="GOV_PROCUREMENT_OFFER_DUPLICATE",
            message="Ya existe una oferta de este oferente con este tipo de sobre",
        )

    oficial = _funcionario(db, ctx, entrada.funcionario_id, "funcionario_id")
    verificar_antes_de_asumir_funcion(
        db,
        ctx,
        expediente,
        "RECEPTOR",
        user_ids=[ctx.user_id],
        official_ids=[oficial.id],
    )
    nombre_funcionario, cargo, unidad = _etiqueta_funcionario(db, ctx, oficial, recibida_caracas.date())
    receptor = _texto_responsable(nombre_funcionario, cargo, unidad)

    max_num = db.scalar(
        select(func.max(GovernmentProcurementOffer.numero)).where(
            GovernmentProcurementOffer.file_id == expediente.id,
            GovernmentProcurementOffer.company_id == ctx.company_id,
        )
    ) or 0

    offer = GovernmentProcurementOffer(
        company_id=ctx.company_id,
        file_id=expediente.id,
        numero=max_num + 1,
        oferente_nombre=nombre,
        oferente_documento=documento,
        representante=entrada.representante,
        tipo_sobre=entrada.tipo_sobre,
        canal=entrada.canal,
        recibida_en=recibida_en,
        official_id=oficial.id,
        receptor_etiqueta=receptor,
        condicion_sobre=entrada.condicion_sobre,
        confidencial=entrada.confidencial,
        fundamento_confidencialidad=fundamento,
        modalidad_al_recibir=modalidad,
        created_by=ctx.user_id,
    )
    db.add(offer)
    db.flush()

    for doc_id in entrada.documento_ids:
        doc, version, link = _validar_documento(db, ctx, expediente, doc_id)
        assert_deliverable(db, version)
        congelar_vinculo(db, link=link, version_id=str(version.id), actor=db.get(User, ctx.user_id))
        db.add(GovernmentProcurementOfferDocument(
            company_id=ctx.company_id,
            offer_id=offer.id,
            document_id=doc.id,
            document_version_id=version.id,
            version_numero=version.version_number,
            sha256=version.sha256,
            created_by=ctx.user_id,
        ))
        if entrada.confidencial:
            sellar_documento(
                db,
                document=doc,
                resource_type="GovernmentProcurementFile",
                resource_id=str(expediente.id),
                actor_id=ctx.user_id,
                motivo=fundamento,
            )
        db.flush()

    expediente.version += 1
    db.flush()

    _evento(
        db,
        ctx,
        expediente,
        "OFERTA",
        recibida_caracas.date(),
        f"{_referencia(offer.numero)} — {offer.oferente_nombre}",
        detalle=f"{recibida_caracas.strftime('%d/%m/%Y %H:%M')} · {_CANALES[offer.canal]} · {_TIPOS_SOBRE[offer.tipo_sobre]} · {'Sellada' if offer.confidencial else 'Sin sello'}",
        responsable_etiqueta=receptor,
        official_id=oficial.id,
    )

    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_OFFER_RECEIVED",
        expediente_id=str(expediente.id),
        after={
            "referencia": _referencia(offer.numero),
            "canal": offer.canal,
            "confidencial": offer.confidencial,
            "documentos": len(entrada.documento_ids),
            "version": expediente.version,
        },
    )

    return _serializar_oferta(db, offer, ctx=ctx, con_documentos=True)


def concluir_recepcion(db: Session, ctx: CompanyContext, expediente_id: str,
                       version_if_match: int | None, motivo: str | None) -> dict:
    expediente = _para_escribir(db, ctx, expediente_id, version_if_match)
    _abierto(expediente)
    if expediente.recepcion_concluida_en is not None:
        raise ConflictError(
            code="GOV_PROCUREMENT_OFFER_RECEPTION_CONCLUDED",
            message="La recepción de ofertas ya concluyó",
        )
    now = _local_now()
    expediente.recepcion_concluida_en = now
    expediente.recepcion_concluida_por = ctx.user_id
    expediente.version += 1
    db.flush()

    _evento(
        db,
        ctx,
        expediente,
        "OFERTA",
        datetime.now(_CARACAS).date(),
        "Recepción de ofertas concluida",
        detalle=motivo or "Recepción de ofertas concluida",
    )
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_OFFER_RECEPTION_CONCLUDED",
        expediente_id=str(expediente.id),
        after={"motivo": motivo, "version": expediente.version},
    )
    return {
        "expediente_id": expediente.id,
        "recepcion_concluida_en": now,
        "version": expediente.version,
    }
