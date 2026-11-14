"""Servicio de garantías y cauciones (PROC-10)."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentLink, DocumentVersion
from app.modules.documents.service import documento_sellado
from app.modules.government.garantias_reglas import (
    BASES_GARANTIA,
    DIAS_POR_VENCER,
    ETIQUETA_ACCION,
    ETIQUETA_EMISOR,
    ETIQUETA_ESTADO,
    ETIQUETA_ETAPA,
    ETIQUETA_PRECONDICION,
    ETIQUETA_TIPO,
    TIPOS_EMISOR,
    base_disponible,
    instantanea,
    regla,
    reglas_vigentes,
)
from app.modules.government.models import (
    MONEDAS_LIMITE,
    GovernmentAct,
    GovernmentBank,
    GovernmentGuaranteeEvent,
    GovernmentGuaranteeInstrument,
    GovernmentGuaranteeIssuer,
    GovernmentGuaranteeRequirement,
    GovernmentProcurementDecision,
    GovernmentProcurementFile,
    GovernmentProcurementOffer,
    GovernmentProcurementOfferAmount,
)
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_decision_resolver import _decision_vigente
from app.modules.government.service_expedientes import (
    _abierto,
    _auditar,
    _cargar,
    _evento,
    _para_escribir,
)
from app.modules.government.service_identidad import (
    _funcionario_del_actor,
    exigir_autoridad_funcional,
)
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual


def _inv(campo: str, mensaje: str) -> KontrolError:
    return KontrolError(
        code="GOV_GUARANTEE_INVALID",
        message="Datos de la garantía inválidos",
        field_errors={campo: [mensaje]},
        status_code=422,
    )


def _texto(valor: Any, campo: str, maximo: int) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise _inv(campo, "El campo es obligatorio")
    texto = valor.strip()
    if len(texto) > maximo:
        raise _inv(campo, f"Máximo {maximo} caracteres")
    return texto


def _decimal(valor: Any, campo: str) -> Decimal:
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, int | str):
        try:
            return Decimal(str(valor))
        except Exception:
            pass
    raise _inv(campo, "Debe ser un número decimal válido")


def _fecha(valor: Any, campo: str) -> date:
    if not isinstance(valor, date):
        raise _inv(campo, "Fecha obligatoria")
    return valor


def _moneda(valor: Any) -> str:
    if valor not in MONEDAS_LIMITE:
        raise _inv("moneda", "Moneda inválida")
    return valor


def _pct(valor: Decimal) -> str:
    return f"{valor:.2f}".replace(".", ",") + " %"


def _ref(prefijo: str, numero: int) -> str:
    return f"{prefijo}-{numero:02d}"


def _documento(
    db: Session, ctx: CompanyContext, expediente: GovernmentProcurementFile, documento_id: str, campo: str
) -> tuple[Document, DocumentVersion]:
    doc = db.scalar(
        select(Document).where(Document.id == documento_id, Document.company_id == ctx.company_id)
    )
    if doc is None or doc.status not in ("DRAFT", "ACTIVE") or documento_sellado(db, documento_id):
        raise _inv(campo, "El documento no existe en este ente o no está vinculado al expediente")
    if doc.current_version_id is None:
        raise _inv(campo, "El documento no existe en este ente o no está vinculado al expediente")
    version = db.get(DocumentVersion, doc.current_version_id)
    if version is None or version.document_id != doc.id:
        raise _inv(campo, "El documento no existe en este ente o no está vinculado al expediente")
    link = db.scalar(
        select(DocumentLink).where(
            DocumentLink.document_id == doc.id,
            DocumentLink.resource_type == "GovernmentProcurementFile",
            DocumentLink.resource_id == expediente.id,
        )
    )
    if link is None:
        raise _inv(campo, "El documento no existe en este ente o no está vinculado al expediente")
    return doc, version


def _acto_valido(db: Session, ctx: CompanyContext, acto_id: str) -> GovernmentAct:
    acto = db.get(GovernmentAct, acto_id) if acto_id else None
    if acto is None or acto.company_id != ctx.company_id:
        raise KontrolError(
            code="GOV_GUARANTEE_INVALID_ACT",
            message="El acto no es válido para esta actuación",
            status_code=422,
            field_errors={"acto_id": ["Acto inexistente o de otro ente"]},
        )
    if acto.status not in ("EMITIDO", "EFICAZ"):
        raise KontrolError(
            code="GOV_GUARANTEE_INVALID_ACT",
            message="El acto no está emitido ni eficaz",
            status_code=422,
            field_errors={"acto_id": ["El acto debe estar EMITIDO o EFICAZ"]},
        )
    if acto.caracter != "PARTICULAR":
        raise KontrolError(
            code="GOV_GUARANTEE_INVALID_ACT",
            message="El acto debe ser de carácter particular",
            status_code=422,
            field_errors={"acto_id": ["El acto debe ser PARTICULAR"]},
        )
    if acto.competencia_accion != "APROBAR" or acto.competencia_materia != "CONTRATACIONES":
        raise KontrolError(
            code="GOV_GUARANTEE_INVALID_ACT",
            message="El acto no tiene competencia para aprobar contrataciones",
            status_code=422,
            field_errors={"acto_id": ["Competencia del acto inválida"]},
        )
    if not _autoridad_valida(
        db, ctx.company_id, str(acto.cargo_id), acto.fecha, "APROBAR", "CONTRATACIONES"
    ):
        raise KontrolError(
            code="GOV_GUARANTEE_INVALID_ACT",
            message="La autoridad del acto no es válida para aprobar contrataciones",
            status_code=422,
            field_errors={"acto_id": ["Autoridad del acto inválida"]},
        )
    exigir_autoridad_funcional(db, ctx, str(acto.cargo_id), "APROBAR", "CONTRATACIONES")
    return acto


def _instrumento(
    db: Session, ctx: CompanyContext, expediente: GovernmentProcurementFile, garantia_id: str
) -> GovernmentGuaranteeInstrument:
    instrumento = db.scalar(
        select(GovernmentGuaranteeInstrument)
        .where(
            GovernmentGuaranteeInstrument.id == garantia_id,
            GovernmentGuaranteeInstrument.company_id == ctx.company_id,
            GovernmentGuaranteeInstrument.file_id == expediente.id,
        )
        .with_for_update()
    )
    if instrumento is None:
        raise NotFoundError("GOV_GUARANTEE_NOT_FOUND", "Garantía no encontrada")
    if instrumento.estado != "REGISTRADA":
        etiqueta = ETIQUETA_ESTADO.get(instrumento.estado, instrumento.estado)
        raise ConflictError(
            "GOV_GUARANTEE_NOT_ACTIVE",
            f"La garantía ya no está registrada: está {etiqueta}",
        )
    return instrumento


def _insertar_protegido(db: Session, objeto: Any, conflictos: dict[str, tuple[str, str]]) -> None:
    db.add(objeto)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as exc:
        origen = str(exc.orig)
        for indice, (codigo, mensaje) in conflictos.items():
            if indice in origen:
                raise ConflictError(codigo, mensaje) from exc
        raise


def _siguiente_numero(db: Session, ctx: CompanyContext, expediente_id: str, modelo: Any) -> int:
    maximo = db.scalar(
        select(func.max(modelo.numero)).where(
            modelo.company_id == ctx.company_id,
            modelo.file_id == expediente_id,
        )
    )
    return (maximo or 0) + 1


def _formato_fecha(fecha: date) -> str:
    return fecha.strftime("%d/%m/%Y")


def listar_emisores(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    emisores = db.scalars(
        select(GovernmentGuaranteeIssuer)
        .where(
            GovernmentGuaranteeIssuer.company_id == ctx.company_id,
            GovernmentGuaranteeIssuer.estado == "ACTIVO",
        )
        .order_by(GovernmentGuaranteeIssuer.nombre)
    ).all()
    bancos = db.scalars(
        select(GovernmentBank)
        .where(GovernmentBank.company_id == ctx.company_id, GovernmentBank.estado == "ACTIVO")
        .order_by(GovernmentBank.codigo)
    ).all()
    return {
        "emisores": [
            {
                "id": e.id,
                "tipo": e.tipo,
                "tipo_etiqueta": ETIQUETA_EMISOR.get(e.tipo, e.tipo),
                "nombre": e.nombre,
                "rif": e.rif,
                "banco_id": e.bank_id,
                "estado": e.estado,
            }
            for e in emisores
        ],
        "bancos": [{"id": b.id, "codigo": b.codigo, "nombre": b.nombre} for b in bancos],
    }


def registrar_emisor(db: Session, ctx: CompanyContext, user: User, cuerpo: dict[str, Any]) -> dict[str, Any]:
    tipo = cuerpo.get("tipo")
    if tipo not in TIPOS_EMISOR:
        raise _inv("tipo", "Tipo de emisor inválido")
    rif = _texto(cuerpo.get("rif"), "rif", 20).replace(" ", "").upper()
    if len(rif) < 6:
        raise _inv("rif", "El RIF debe tener al menos 6 caracteres")
    banco_id = cuerpo.get("banco_id")
    nombre = cuerpo.get("nombre")
    if tipo == "BANCO":
        if not banco_id:
            raise _inv("banco_id", "El banco es obligatorio para un emisor de tipo banco")
        banco = db.scalar(
            select(GovernmentBank).where(
                GovernmentBank.id == banco_id,
                GovernmentBank.company_id == ctx.company_id,
                GovernmentBank.estado == "ACTIVO",
            )
        )
        if banco is None:
            raise _inv("banco_id", "Banco inexistente, inactivo o de otro ente")
        nombre_final = nombre.strip() if isinstance(nombre, str) and nombre.strip() else banco.nombre
    else:
        if banco_id:
            raise _inv("banco_id", "Solo un emisor de tipo banco se enlaza a un banco")
        nombre_final = _texto(nombre, "nombre", 200)
    existente = db.scalar(
        select(GovernmentGuaranteeIssuer).where(
            GovernmentGuaranteeIssuer.company_id == ctx.company_id,
            GovernmentGuaranteeIssuer.rif == rif,
        )
    )
    if existente is not None:
        raise ConflictError("GOV_GUARANTEE_ISSUER_DUPLICATE", "Ya hay un emisor con ese RIF en el ente")
    emisor = GovernmentGuaranteeIssuer(
        company_id=ctx.company_id,
        tipo=tipo,
        nombre=nombre_final,
        rif=rif,
        bank_id=banco_id if tipo == "BANCO" else None,
        estado="ACTIVO",
        created_by=ctx.user_id,
    )
    _insertar_protegido(
        db,
        emisor,
        {"uq_gov_guarantee_issuers_company_rif": ("GOV_GUARANTEE_ISSUER_DUPLICATE", "Ya hay un emisor con ese RIF en el ente")},
    )
    record_audit(
        db,
        action="GOV_GUARANTEE_ISSUER_REGISTERED",
        entity_type="GovernmentGuaranteeIssuer",
        entity_id=str(emisor.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"nombre": emisor.nombre, "rif": emisor.rif, "tipo": emisor.tipo},
    )
    return {
        "id": emisor.id,
        "tipo": emisor.tipo,
        "tipo_etiqueta": ETIQUETA_EMISOR.get(emisor.tipo, emisor.tipo),
        "nombre": emisor.nombre,
        "rif": emisor.rif,
        "banco_id": emisor.bank_id,
        "estado": emisor.estado,
    }


def _requisito_del_expediente(
    db: Session, ctx: CompanyContext, expediente: GovernmentProcurementFile, requisito_id: str
) -> GovernmentGuaranteeRequirement:
    requisito = db.scalar(
        select(GovernmentGuaranteeRequirement).where(
            GovernmentGuaranteeRequirement.id == requisito_id,
            GovernmentGuaranteeRequirement.company_id == ctx.company_id,
            GovernmentGuaranteeRequirement.file_id == expediente.id,
        )
    )
    if requisito is None:
        raise _inv("requisito_id", "Requisito inexistente en este expediente")
    return requisito


def _oferta_del_expediente(
    db: Session, ctx: CompanyContext, expediente: GovernmentProcurementFile, oferta_id: str
) -> GovernmentProcurementOffer:
    oferta = db.scalar(
        select(GovernmentProcurementOffer).where(
            GovernmentProcurementOffer.id == oferta_id,
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente.id,
        )
    )
    if oferta is None:
        raise _inv("oferta_id", "Oferta inexistente en este expediente")
    return oferta


def _emisor_del_ente(db: Session, ctx: CompanyContext, emisor_id: str) -> GovernmentGuaranteeIssuer:
    emisor = db.scalar(
        select(GovernmentGuaranteeIssuer).where(
            GovernmentGuaranteeIssuer.id == emisor_id,
            GovernmentGuaranteeIssuer.company_id == ctx.company_id,
            GovernmentGuaranteeIssuer.estado == "ACTIVO",
        )
    )
    if emisor is None:
        raise _inv("emisor_id", "Emisor inexistente, inactivo o de otro ente")
    return emisor


def _validar_fechas_instrumento(
    fecha_emision: date, vigente_desde: date, vigente_hasta: date
) -> None:
    if vigente_desde > vigente_hasta:
        raise _inv("vigente_hasta", "Debe ser igual o posterior a «vigente desde»")
    if fecha_emision > vigente_hasta:
        raise _inv("fecha_emision", "Debe ser igual o anterior a «vigente hasta»")


def _validar_monto_moneda(monto: Decimal, moneda: str) -> None:
    if monto <= 0:
        raise _inv("monto", "El monto debe ser mayor que cero")
    if moneda not in MONEDAS_LIMITE:
        raise _inv("moneda", "Moneda inválida")


def _evento_garantia(
    db: Session,
    ctx: CompanyContext,
    expediente: GovernmentProcurementFile,
    instrumento: GovernmentGuaranteeInstrument,
    accion: str,
    fecha: date,
    motivo: str | None,
    *,
    act_id: str | None = None,
    cargo_id: str | None = None,
    document_id: str | None = None,
    document_version_id: str | None = None,
    version_numero: int | None = None,
    sha256: str | None = None,
    nuevo_instrument_id: str | None = None,
    monto: Decimal | None = None,
    moneda: str | None = None,
    precondicion: str | None = None,
    precondicion_detalle: str | None = None,
) -> GovernmentGuaranteeEvent:
    evento = GovernmentGuaranteeEvent(
        company_id=ctx.company_id,
        file_id=expediente.id,
        instrument_id=instrumento.id,
        accion=accion,
        fecha=fecha,
        motivo=motivo,
        act_id=act_id,
        cargo_id=cargo_id,
        document_id=document_id,
        document_version_id=document_version_id,
        version_numero=version_numero,
        sha256=sha256,
        nuevo_instrument_id=nuevo_instrument_id,
        monto=monto,
        moneda=moneda,
        precondicion=precondicion,
        precondicion_detalle=precondicion_detalle,
        registrada_en=instante_actual(),
        registrada_por=ctx.user_id or "",
        official_id=_funcionario_del_actor(db, ctx),
        created_by=ctx.user_id,
    )
    _insertar_protegido(
        db,
        evento,
        {"uq_gov_guarantee_events_final": ("GOV_GUARANTEE_NOT_ACTIVE", "La garantía ya tiene una actuación final")},
    )
    return evento


def _titulo_requisito(requisito: GovernmentGuaranteeRequirement, numero: int) -> str:
    return f"Requisito de garantía {_ref('REQ', numero)} registrado: {ETIQUETA_TIPO.get(requisito.tipo, requisito.tipo)}"


def _titulo_garantia(
    instrumento: GovernmentGuaranteeInstrument, oferta: GovernmentProcurementOffer, numero: int
) -> str:
    return (
        f"Garantía {_ref('GAR', numero)} registrada: "
        f"{ETIQUETA_TIPO.get(instrumento.tipo, instrumento.tipo)} de "
        f"{_ref('O', oferta.numero)} ({oferta.oferente_nombre})"
    )


def _titulo_renovacion(
    anterior: GovernmentGuaranteeInstrument, nueva: GovernmentGuaranteeInstrument, numero_nueva: int
) -> str:
    return (
        f"Garantía {_ref('GAR', anterior.numero)} renovada por "
        f"{_ref('GAR', numero_nueva)} hasta el {_formato_fecha(nueva.vigente_hasta)}"
    )


def _titulo_sustitucion(
    anterior: GovernmentGuaranteeInstrument, nueva: GovernmentGuaranteeInstrument, numero_nueva: int
) -> str:
    return f"Garantía {_ref('GAR', anterior.numero)} sustituida por {_ref('GAR', numero_nueva)}"


def _titulo_liberacion(instrumento: GovernmentGuaranteeInstrument) -> str:
    return f"Garantía {_ref('GAR', instrumento.numero)} liberada"


def _titulo_ejecucion(instrumento: GovernmentGuaranteeInstrument, monto: Decimal, moneda: str) -> str:
    return f"Garantía {_ref('GAR', instrumento.numero)} ejecutada por {monto} {moneda}"


def _criterio_documento(doc: Document | None, version: DocumentVersion | None) -> dict[str, str]:
    if doc is None or version is None:
        return {
            "criterio": "Documento",
            "resultado": "NO_CUMPLE",
            "detalle": "Documento fijado no disponible",
        }
    return {
        "criterio": "Documento",
        "resultado": "CUMPLE",
        "detalle": f"{doc.title}, versión {version.version_number}, con huella",
    }


def _criterio_emisor(regla: dict[str, Any], emisor: GovernmentGuaranteeIssuer) -> dict[str, str]:
    admitidos = regla.get("emisores_admitidos")
    if admitidos is None or emisor.tipo in admitidos:
        return {"criterio": "Emisor", "resultado": "CUMPLE", "detalle": "El emisor está admitido por la regla"}
    return {
        "criterio": "Emisor",
        "resultado": "NO_CUMPLE",
        "detalle": "La regla exige banco, aseguradora o Sociedad de Garantías Recíprocas",
    }


def _monto_oferta(db: Session, instrumento: GovernmentGuaranteeInstrument) -> GovernmentProcurementOfferAmount | None:
    """Monto vigente declarado en la oferta de la garantía (OMA-10); None si no hay."""
    return db.scalar(
        select(GovernmentProcurementOfferAmount)
        .where(
            GovernmentProcurementOfferAmount.company_id == instrumento.company_id,
            GovernmentProcurementOfferAmount.offer_id == instrumento.offer_id,
        )
        .order_by(GovernmentProcurementOfferAmount.version.desc())
        .limit(1)
    )


def _criterio_moneda(
    requisito: GovernmentGuaranteeRequirement,
    instrumento: GovernmentGuaranteeInstrument,
    monto_oferta: GovernmentProcurementOfferAmount | None,
) -> dict[str, str]:
    if requisito.moneda:
        if instrumento.moneda == requisito.moneda:
            return {"criterio": "Moneda", "resultado": "CUMPLE", "detalle": f"Coincide con {requisito.moneda}"}
        return {
            "criterio": "Moneda",
            "resultado": "NO_CUMPLE",
            "detalle": f"Se exige {requisito.moneda}",
        }
    if requisito.forma == "PORCENTAJE" and (requisito.regla or {}).get("base") == "MONTO_OFERTA" and monto_oferta is not None:
        if instrumento.moneda == monto_oferta.moneda:
            return {
                "criterio": "Moneda",
                "resultado": "CUMPLE",
                "detalle": f"Coincide con la moneda de la oferta ({monto_oferta.moneda})",
            }
        return {
            "criterio": "Moneda",
            "resultado": "NO_EVALUABLE",
            "detalle": f"La oferta está en {monto_oferta.moneda}; no se convierte moneda",
        }
    return {
        "criterio": "Moneda",
        "resultado": "NO_EVALUABLE",
        "detalle": "La moneda depende de la base de cálculo",
    }


def _criterio_monto(
    requisito: GovernmentGuaranteeRequirement,
    instrumento: GovernmentGuaranteeInstrument,
    monto_oferta: GovernmentProcurementOfferAmount | None,
) -> dict[str, str]:
    regla = requisito.regla or {}
    if requisito.forma == "MONTO_FIJO":
        if (
            requisito.monto_fijo is not None
            and instrumento.moneda == requisito.moneda
            and instrumento.monto >= requisito.monto_fijo
        ):
            return {
                "criterio": "Monto",
                "resultado": "CUMPLE",
                "detalle": f"{instrumento.monto} {instrumento.moneda} cubre lo exigido ({requisito.monto_fijo} {requisito.moneda})",
            }
        return {
            "criterio": "Monto",
            "resultado": "NO_CUMPLE",
            "detalle": f"{instrumento.monto} {instrumento.moneda} no cubre lo exigido ({requisito.monto_fijo} {requisito.moneda})",
        }
    base = regla.get("base")
    if base == "MONTO_OFERTA" and requisito.porcentaje is not None:
        if monto_oferta is None:
            return {
                "criterio": "Monto",
                "resultado": "NO_EVALUABLE",
                "detalle": "BASE_MONETARIA_NO_DISPONIBLE: la oferta no tiene monto declarado",
            }
        if instrumento.moneda != monto_oferta.moneda:
            return {
                "criterio": "Monto",
                "resultado": "NO_EVALUABLE",
                "detalle": f"La garantía está en {instrumento.moneda} y la oferta en {monto_oferta.moneda}; no se convierte moneda",
            }
        pct = requisito.porcentaje
        total = monto_oferta.total_con_tributos
        neto = monto_oferta.monto_sin_iva
        if total >= neto:
            etiqueta_mayor, mayor = "el total con tributos", total
            etiqueta_menor, menor = "el monto sin IVA", neto
        else:
            etiqueta_mayor, mayor = "el monto sin IVA", neto
            etiqueta_menor, menor = "el total con tributos", total
        if instrumento.monto * 100 >= pct * mayor:
            return {
                "criterio": "Monto",
                "resultado": "CUMPLE",
                "detalle": f"{instrumento.monto} {instrumento.moneda} cubre el {pct} % de la oferta sobre el total con tributos ({total}) y sobre el monto sin IVA ({neto})",
            }
        if not (instrumento.monto * 100 >= pct * menor):
            return {
                "criterio": "Monto",
                "resultado": "NO_CUMPLE",
                "detalle": f"{instrumento.monto} {instrumento.moneda} no cubre el {pct} % de la oferta ni sobre el monto sin IVA ({neto}) ni sobre el total con tributos ({total})",
            }
        return {
            "criterio": "Monto",
            "resultado": "NO_EVALUABLE",
            "detalle": f"{instrumento.monto} {instrumento.moneda} cubre el {pct} % sobre {etiqueta_menor} ({menor}) pero no sobre {etiqueta_mayor} ({mayor}); la regla no precisa la base (RLCP art. 135)",
        }
    disponible = base_disponible(base)
    if disponible is None:
        texto_base = BASES_GARANTIA.get(base or "", "la base de cálculo")
        return {
            "criterio": "Monto",
            "resultado": "NO_EVALUABLE",
            "detalle": f"BASE_MONETARIA_NO_DISPONIBLE: falta el {texto_base}",
        }
    return {
        "criterio": "Monto",
        "resultado": "NO_EVALUABLE",
        "detalle": "BASE_MONETARIA_NO_DISPONIBLE",
    }


def _criterio_vigencia_minima(
    requisito: GovernmentGuaranteeRequirement, instrumento: GovernmentGuaranteeInstrument
) -> dict[str, str]:
    if requisito.vigencia_minima_hasta:
        if instrumento.vigente_hasta >= requisito.vigencia_minima_hasta:
            return {
                "criterio": "Vigencia mínima",
                "resultado": "CUMPLE",
                "detalle": f"Cubre hasta el {_formato_fecha(instrumento.vigente_hasta)}",
            }
        return {
            "criterio": "Vigencia mínima",
            "resultado": "NO_CUMPLE",
            "detalle": f"Vence el {_formato_fecha(instrumento.vigente_hasta)}; se exige hasta el {_formato_fecha(requisito.vigencia_minima_hasta)}",
        }
    regla = requisito.regla or {}
    return {
        "criterio": "Vigencia mínima",
        "resultado": "NO_EVALUABLE",
        "detalle": f"El requisito no fija fecha: {regla.get('vigencia_exigida', '')}",
    }


def _vigencia(instrumento: GovernmentGuaranteeInstrument, hoy: date) -> tuple[str, str]:
    if hoy < instrumento.vigente_desde:
        return "FUTURA", "Aún no vigente"
    if hoy > instrumento.vigente_hasta:
        return "VENCIDA", "Vencida"
    dias = (instrumento.vigente_hasta - hoy).days
    if dias <= DIAS_POR_VENCER:
        return "POR_VENCER", "Por vencer"
    return "VIGENTE", "Vigente"


def _criterio_vigente_a_la_fecha(
    instrumento: GovernmentGuaranteeInstrument, hoy: date
) -> dict[str, str]:
    estado, etiqueta = _vigencia(instrumento, hoy)
    if estado in ("VIGENTE", "POR_VENCER"):
        return {"criterio": "Vigente a la fecha", "resultado": "CUMPLE", "detalle": etiqueta}
    if estado == "FUTURA":
        return {"criterio": "Vigente a la fecha", "resultado": "NO_CUMPLE", "detalle": "Aún no está vigente"}
    return {
        "criterio": "Vigente a la fecha",
        "resultado": "NO_CUMPLE",
        "detalle": f"Vencida el {_formato_fecha(instrumento.vigente_hasta)}",
    }


def _criterios(
    requisito: GovernmentGuaranteeRequirement,
    instrumento: GovernmentGuaranteeInstrument,
    emisor: GovernmentGuaranteeIssuer,
    doc: Document | None,
    version: DocumentVersion | None,
    hoy: date,
    monto_oferta: GovernmentProcurementOfferAmount | None,
) -> list[dict[str, str]]:
    return [
        _criterio_documento(doc, version),
        _criterio_emisor(requisito.regla or {}, emisor),
        _criterio_moneda(requisito, instrumento, monto_oferta),
        _criterio_monto(requisito, instrumento, monto_oferta),
        _criterio_vigencia_minima(requisito, instrumento),
        _criterio_vigente_a_la_fecha(instrumento, hoy),
    ]


def _suficiencia(criterios: list[dict[str, str]]) -> tuple[str, str]:
    if any(c["resultado"] == "NO_CUMPLE" for c in criterios):
        return "INSUFICIENTE", "Insuficiente"
    if any(c["resultado"] == "NO_EVALUABLE" for c in criterios):
        return "NO_EVALUABLE", "No evaluable"
    return "SUFICIENTE", "Suficiente"


def _documento_salida(db: Session, doc_id: str, version_id: str) -> dict[str, Any]:
    doc = db.get(Document, doc_id)
    version = db.get(DocumentVersion, version_id)
    return {
        "id": doc_id,
        "titulo": doc.title if doc else None,
        "version": version.version_number if version else None,
        "sha256": version.sha256 if version else None,
    }


def _cadena_ids(db: Session, instrumento: GovernmentGuaranteeInstrument) -> list[str]:
    ids: list[str] = []
    actual: GovernmentGuaranteeInstrument | None = instrumento
    while actual is not None:
        ids.append(str(actual.id))
        actual = db.get(GovernmentGuaranteeInstrument, actual.antecesor_id) if actual.antecesor_id else None
    actual = db.scalar(
        select(GovernmentGuaranteeInstrument).where(
            GovernmentGuaranteeInstrument.antecesor_id == instrumento.id
        )
    )
    while actual is not None:
        ids.append(str(actual.id))
        actual = db.scalar(
            select(GovernmentGuaranteeInstrument).where(
                GovernmentGuaranteeInstrument.antecesor_id == actual.id
            )
        )
    return ids


def _historial(
    db: Session, ctx: CompanyContext, instrumento: GovernmentGuaranteeInstrument
) -> list[dict[str, Any]]:
    ids = _cadena_ids(db, instrumento)
    if not ids:
        return []
    eventos = db.scalars(
        select(GovernmentGuaranteeEvent)
        .where(GovernmentGuaranteeEvent.instrument_id.in_(ids))
        .order_by(GovernmentGuaranteeEvent.registrada_en, GovernmentGuaranteeEvent.id)
    ).all()
    usuarios = _usuarios_por_ids(db, [e.registrada_por for e in eventos], ctx.tenant_id)
    instrumentos = {str(i.id): i for i in db.scalars(
        select(GovernmentGuaranteeInstrument).where(GovernmentGuaranteeInstrument.id.in_(ids))
    ).all()}
    salida: list[dict[str, Any]] = []
    for evento in eventos:
        inst = instrumentos.get(str(evento.instrument_id))
        acto = db.get(GovernmentAct, evento.act_id) if evento.act_id else None
        doc = db.get(Document, evento.document_id) if evento.document_id else None
        salida.append(
            {
                "id": evento.id,
                "accion": evento.accion,
                "accion_etiqueta": ETIQUETA_ACCION.get(evento.accion, evento.accion),
                "fecha": evento.fecha.isoformat(),
                "registrada_en": evento.registrada_en.isoformat(),
                "actor": usuarios.get(evento.registrada_por, evento.registrada_por),
                "motivo": evento.motivo,
                "garantia": _ref("GAR", inst.numero) if inst else None,
                "nueva_garantia": _ref("GAR", instrumentos[str(evento.nuevo_instrument_id)].numero)
                if evento.nuevo_instrument_id and str(evento.nuevo_instrument_id) in instrumentos
                else None,
                "acto": {"id": acto.id, "etiqueta": f"{acto.tipo} {acto.numero}"} if acto else None,
                "documento": {"id": doc.id, "titulo": doc.title} if doc else None,
                "monto": str(evento.monto) if evento.monto is not None else None,
                "moneda": evento.moneda,
                "precondicion": evento.precondicion,
                "precondicion_etiqueta": ETIQUETA_PRECONDICION.get(evento.precondicion, evento.precondicion)
                if evento.precondicion
                else None,
                "precondicion_detalle": evento.precondicion_detalle,
            }
        )
    return salida


def _instrumento_salida(
    db: Session,
    ctx: CompanyContext,
    instrumento: GovernmentGuaranteeInstrument,
    requisito: GovernmentGuaranteeRequirement,
    oferta: GovernmentProcurementOffer,
    emisor: GovernmentGuaranteeIssuer,
    hoy: date,
    expediente: GovernmentProcurementFile,
) -> dict[str, Any]:
    doc = db.get(Document, instrumento.document_id)
    version = db.get(DocumentVersion, instrumento.document_version_id)
    criterios = _criterios(requisito, instrumento, emisor, doc, version, hoy, _monto_oferta(db, instrumento))
    suficiencia, etiqueta_suficiencia = _suficiencia(criterios)
    estado_vigencia, etiqueta_vigencia = _vigencia(instrumento, hoy)
    dias = (instrumento.vigente_hasta - hoy).days
    decision = db.get(GovernmentProcurementDecision, instrumento.decision_id) if instrumento.decision_id else None
    antecesor = db.get(GovernmentGuaranteeInstrument, instrumento.antecesor_id) if instrumento.antecesor_id else None
    sucesor = db.scalar(
        select(GovernmentGuaranteeInstrument).where(
            GovernmentGuaranteeInstrument.antecesor_id == instrumento.id
        )
    )
    acciones: list[str] = []
    if instrumento.estado == "REGISTRADA" and expediente.status == "ABIERTO":
        acciones.append("RENOVAR")
        if (requisito.regla or {}).get("permite_sustitucion"):
            acciones.append("SUSTITUIR")
        acciones.extend(["LIBERAR", "EJECUTAR"])
    return {
        "id": instrumento.id,
        "referencia": _ref("GAR", instrumento.numero),
        "requisito_id": requisito.id,
        "requisito": _ref("REQ", requisito.numero),
        "tipo": instrumento.tipo,
        "tipo_etiqueta": ETIQUETA_TIPO.get(instrumento.tipo, instrumento.tipo),
        "nombre": requisito.nombre,
        "etapa": instrumento.etapa,
        "etapa_etiqueta": ETIQUETA_ETAPA.get(instrumento.etapa, instrumento.etapa),
        "offer_id": oferta.id,
        "oferta": _ref("O", oferta.numero),
        "oferente": oferta.oferente_nombre,
        "decision": _ref("DEC", decision.numero) if decision else None,
        "emisor": {
            "id": emisor.id,
            "nombre": emisor.nombre,
            "tipo": emisor.tipo,
            "tipo_etiqueta": ETIQUETA_EMISOR.get(emisor.tipo, emisor.tipo),
            "rif": emisor.rif,
        },
        "referencia_emisor": instrumento.referencia_emisor,
        "monto": str(instrumento.monto),
        "moneda": instrumento.moneda,
        "fecha_emision": instrumento.fecha_emision.isoformat(),
        "vigente_desde": instrumento.vigente_desde.isoformat(),
        "vigente_hasta": instrumento.vigente_hasta.isoformat(),
        "dias_restantes": dias,
        "vigencia": estado_vigencia,
        "vigencia_etiqueta": etiqueta_vigencia,
        "estado": instrumento.estado,
        "estado_etiqueta": ETIQUETA_ESTADO.get(instrumento.estado, instrumento.estado),
        "origen": instrumento.origen,
        "antecesor": _ref("GAR", antecesor.numero) if antecesor else None,
        "sucesor": _ref("GAR", sucesor.numero) if sucesor else None,
        "suficiencia": suficiencia if instrumento.estado == "REGISTRADA" else None,
        "suficiencia_etiqueta": etiqueta_suficiencia if instrumento.estado == "REGISTRADA" else None,
        "criterios": criterios if instrumento.estado == "REGISTRADA" else [],
        "documento": _documento_salida(db, str(instrumento.document_id), str(instrumento.document_version_id)),
        "observacion": instrumento.observacion,
        "acciones": acciones,
        "historial": _historial(db, ctx, instrumento),
    }


def _requisito_salida(
    db: Session,
    ctx: CompanyContext,
    requisito: GovernmentGuaranteeRequirement,
    instrumentos: Sequence[GovernmentGuaranteeInstrument],
    ofertas: Sequence[GovernmentProcurementOffer],
    decision: GovernmentProcurementDecision | None,
    hoy: date,
    expediente: GovernmentProcurementFile,
) -> dict[str, Any]:
    regla = requisito.regla or {}
    base = regla.get("base")
    sujetos: list[dict[str, Any]] = []
    ofertas_relevantes = ofertas
    if regla.get("requiere_adjudicacion"):
        if decision is None:
            ofertas_relevantes = []
        else:
            ofertas_relevantes = [o for o in ofertas if o.id == decision.offer_id]
    for oferta in ofertas_relevantes:
        garantias = [i for i in instrumentos if i.offer_id == oferta.id and i.estado == "REGISTRADA"]
        sujetos.append(
            {
                "offer_id": oferta.id,
                "oferta": _ref("O", oferta.numero),
                "oferente": oferta.oferente_nombre,
                "garantias": [_ref("GAR", i.numero) for i in garantias],
                "cubierto": len(garantias) > 0,
            }
        )
    return {
        "id": requisito.id,
        "referencia": _ref("REQ", requisito.numero),
        "tipo": requisito.tipo,
        "tipo_etiqueta": ETIQUETA_TIPO.get(requisito.tipo, requisito.tipo),
        "nombre": requisito.nombre,
        "etapa": requisito.etapa,
        "etapa_etiqueta": ETIQUETA_ETAPA.get(requisito.etapa, requisito.etapa),
        "regla": {**regla, "base_etiqueta": BASES_GARANTIA.get(base) if base else None},
        "forma": requisito.forma,
        "porcentaje": str(requisito.porcentaje) if requisito.porcentaje is not None else None,
        "monto_fijo": str(requisito.monto_fijo) if requisito.monto_fijo is not None else None,
        "moneda": requisito.moneda,
        "vigencia_minima_hasta": requisito.vigencia_minima_hasta.isoformat()
        if requisito.vigencia_minima_hasta
        else None,
        "fundamento": requisito.fundamento,
        "documento": _documento_salida(db, str(requisito.document_id), str(requisito.document_version_id)),
        "registrado_en": requisito.registrado_en.isoformat(),
        "pendiente_adjudicacion": bool(regla.get("requiere_adjudicacion") and decision is None),
        "sujetos": sujetos,
    }


def obtener_estado_garantias(
    db: Session, ctx: CompanyContext, user: User, expediente_id: str
) -> dict[str, Any]:
    expediente = _cargar(db, ctx, expediente_id)
    hoy = hoy_de_negocio()
    decision = _decision_vigente(db, str(expediente.id))
    adjudicacion = None
    if decision is not None and decision.resultado == "ADJUDICADA":
        oferta_adj = db.get(GovernmentProcurementOffer, decision.offer_id) if decision.offer_id else None
        adjudicacion = {
            "decision_id": decision.id,
            "decision": _ref("DEC", decision.numero),
            "offer_id": decision.offer_id,
            "oferta": _ref("O", oferta_adj.numero) if oferta_adj else None,
            "oferente": oferta_adj.oferente_nombre if oferta_adj else None,
        }
    requisitos = db.scalars(
        select(GovernmentGuaranteeRequirement)
        .where(
            GovernmentGuaranteeRequirement.company_id == ctx.company_id,
            GovernmentGuaranteeRequirement.file_id == expediente.id,
        )
        .order_by(GovernmentGuaranteeRequirement.numero)
    ).all()
    instrumentos = db.scalars(
        select(GovernmentGuaranteeInstrument)
        .where(
            GovernmentGuaranteeInstrument.company_id == ctx.company_id,
            GovernmentGuaranteeInstrument.file_id == expediente.id,
        )
        .order_by(GovernmentGuaranteeInstrument.numero)
    ).all()
    ofertas = db.scalars(
        select(GovernmentProcurementOffer)
        .where(
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente.id,
        )
        .order_by(GovernmentProcurementOffer.numero)
    ).all()
    emisores = db.scalars(
        select(GovernmentGuaranteeIssuer)
        .where(
            GovernmentGuaranteeIssuer.company_id == ctx.company_id,
            GovernmentGuaranteeIssuer.estado == "ACTIVO",
        )
        .order_by(GovernmentGuaranteeIssuer.nombre)
    ).all()
    documentos_validos: list[dict[str, Any]] = []
    for doc in db.scalars(
        select(Document)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            Document.company_id == ctx.company_id,
            Document.status.in_(("DRAFT", "ACTIVE")),
            Document.current_version_id.is_not(None),
            DocumentLink.resource_type == "GovernmentProcurementFile",
            DocumentLink.resource_id == expediente.id,
        )
        .order_by(Document.title)
    ).all():
        if not documento_sellado(db, str(doc.id)):
            version = db.get(DocumentVersion, doc.current_version_id)
            if version:
                documentos_validos.append(
                    {"id": doc.id, "titulo": doc.title, "version": version.version_number}
                )
    actos = db.scalars(
        select(GovernmentAct)
        .where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.status.in_(("EMITIDO", "EFICAZ")),
            GovernmentAct.caracter == "PARTICULAR",
            GovernmentAct.competencia_accion == "APROBAR",
            GovernmentAct.competencia_materia == "CONTRATACIONES",
        )
        .order_by(GovernmentAct.fecha.desc())
    ).all()
    actos_elegibles = [
        {"id": a.id, "etiqueta": f"{a.tipo} {a.numero}", "fecha": a.fecha.isoformat(), "asunto": a.asunto}
        for a in actos
    ]
    registradas = [i for i in instrumentos if i.estado == "REGISTRADA"]
    resumen = {
        "requisitos": len(requisitos),
        "registradas": len(registradas),
        "suficientes": 0,
        "insuficientes": 0,
        "no_evaluables": 0,
        "por_vencer": 0,
        "vencidas": 0,
        "liberadas": len([i for i in instrumentos if i.estado == "LIBERADA"]),
        "ejecutadas": len([i for i in instrumentos if i.estado == "EJECUTADA"]),
        "sin_garantia": 0,
    }
    for instrumento in registradas:
        requisito = next((r for r in requisitos if r.id == instrumento.requirement_id), None)
        if requisito is None:
            continue
        emisor = db.get(GovernmentGuaranteeIssuer, instrumento.issuer_id)
        if emisor is None:
            continue
        doc_fijado = db.get(Document, instrumento.document_id)
        version_fijada = db.get(DocumentVersion, instrumento.document_version_id)
        criterios = _criterios(requisito, instrumento, emisor, doc_fijado, version_fijada, hoy, _monto_oferta(db, instrumento))
        suficiencia, _ = _suficiencia(criterios)
        if suficiencia == "SUFICIENTE":
            resumen["suficientes"] += 1
        elif suficiencia == "INSUFICIENTE":
            resumen["insuficientes"] += 1
        else:
            resumen["no_evaluables"] += 1
        estado_vigencia, _ = _vigencia(instrumento, hoy)
        if estado_vigencia == "POR_VENCER":
            resumen["por_vencer"] += 1
        elif estado_vigencia == "VENCIDA":
            resumen["vencidas"] += 1
    adjudicada = decision if decision is not None and decision.resultado == "ADJUDICADA" else None
    sujetos_esperados: set[str] = set()
    for requisito in requisitos:
        regla = requisito.regla or {}
        if regla.get("requiere_adjudicacion"):
            if adjudicada is not None and adjudicada.offer_id:
                sujetos_esperados.add(str(adjudicada.offer_id))
        else:
            for oferta in ofertas:
                sujetos_esperados.add(str(oferta.id))
    requisitos_salida = [
        _requisito_salida(db, ctx, r, instrumentos, ofertas, adjudicada, hoy, expediente)
        for r in requisitos
    ]
    for requisito_salida in requisitos_salida:
        for sujeto in requisito_salida["sujetos"]:
            if not sujeto["cubierto"]:
                resumen["sin_garantia"] += 1
    garantias_salida = []
    for instrumento in instrumentos:
        requisito = next((r for r in requisitos if r.id == instrumento.requirement_id), None)
        oferta_instrumento = next((o for o in ofertas if o.id == instrumento.offer_id), None)
        emisor = db.get(GovernmentGuaranteeIssuer, instrumento.issuer_id)
        if requisito is None or oferta_instrumento is None or emisor is None:
            continue
        garantias_salida.append(
            _instrumento_salida(db, ctx, instrumento, requisito, oferta_instrumento, emisor, hoy, expediente)
        )
    reglas_salida = []
    for r in reglas_vigentes(hoy):
        datos = instantanea(r)
        datos["tipo_etiqueta"] = ETIQUETA_TIPO.get(r.tipo, r.tipo)
        datos["base_etiqueta"] = BASES_GARANTIA.get(r.base) if r.base else None
        reglas_salida.append(datos)
    return {
        "expediente_id": expediente.id,
        "version": expediente.version,
        "estado_expediente": expediente.status,
        "hoy": hoy.isoformat(),
        "adjudicacion": adjudicacion,
        "resumen": resumen,
        "requisitos": requisitos_salida,
        "garantias": garantias_salida,
        "ofertas": [
            {"id": o.id, "referencia": _ref("O", o.numero), "oferente": o.oferente_nombre}
            for o in ofertas
        ],
        "emisores": [
            {
                "id": e.id,
                "tipo": e.tipo,
                "tipo_etiqueta": ETIQUETA_EMISOR.get(e.tipo, e.tipo),
                "nombre": e.nombre,
                "rif": e.rif,
                "banco_id": e.bank_id,
                "estado": e.estado,
            }
            for e in emisores
        ],
        "documentos": documentos_validos,
        "actos_elegibles": actos_elegibles,
        "reglas": reglas_salida,
    }


def registrar_requisito(
    db: Session, ctx: CompanyContext, user: User, expediente_id: str, version: int | None, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    expediente = _para_escribir(db, ctx, expediente_id, version)
    _abierto(expediente)
    regla_codigo = _texto(cuerpo.get("regla_codigo"), "regla_codigo", 40)
    r = regla(regla_codigo)
    hoy = hoy_de_negocio()
    if r is None or r not in reglas_vigentes(hoy):
        raise _inv("regla_codigo", "Regla inexistente o no vigente")
    porcentaje = _decimal(cuerpo.get("porcentaje"), "porcentaje") if cuerpo.get("porcentaje") is not None else None
    monto_fijo = _decimal(cuerpo.get("monto_fijo"), "monto_fijo") if cuerpo.get("monto_fijo") is not None else None
    moneda = cuerpo.get("moneda")
    nombre = cuerpo.get("nombre")
    fundamento = _texto(cuerpo.get("fundamento"), "fundamento", 1000)
    vigencia_minima_hasta = cuerpo.get("vigencia_minima_hasta")
    if vigencia_minima_hasta is not None:
        vigencia_minima_hasta = _fecha(vigencia_minima_hasta, "vigencia_minima_hasta")
    documento_id = _texto(cuerpo.get("documento_id"), "documento_id", 36)
    if r.forma == "PORCENTAJE":
        if porcentaje is None:
            raise _inv("porcentaje", "El porcentaje es obligatorio para una regla porcentual")
        if porcentaje <= 0:
            raise _inv("porcentaje", "Debe ser mayor que cero")
        if r.porcentaje_min is not None and r.porcentaje_max is not None:
            if r.porcentaje_min == r.porcentaje_max:
                rango = _pct(r.porcentaje_min)
            else:
                rango = f"entre {_pct(r.porcentaje_min)} y {_pct(r.porcentaje_max)}"
        elif r.porcentaje_max is not None:
            rango = f"hasta {_pct(r.porcentaje_max)}"
        else:
            rango = ""
        if r.porcentaje_min is not None and porcentaje < r.porcentaje_min:
            raise _inv("porcentaje", f"Fuera del rango de la regla: {rango}")
        if r.porcentaje_max is not None and porcentaje > r.porcentaje_max:
            raise _inv("porcentaje", f"Fuera del rango de la regla: {rango}")
        if monto_fijo is not None or moneda is not None:
            raise _inv("monto_fijo", "La regla es porcentual")
    else:
        if monto_fijo is None:
            raise _inv("monto_fijo", "El monto fijo es obligatorio para una regla de monto fijo")
        if monto_fijo <= 0:
            raise _inv("monto_fijo", "Debe ser mayor que cero")
        moneda = _moneda(moneda)
        if r.moneda_exigida and moneda != r.moneda_exigida:
            raise _inv("moneda", f"La regla exige {r.moneda_exigida}")
        if porcentaje is not None:
            raise _inv("porcentaje", "La regla es de monto fijo")
    if r.tipo == "OTRA":
        nombre_final = _texto(nombre, "nombre", 200)
    else:
        nombre_final = None
    doc, version_doc = _documento(db, ctx, expediente, documento_id, "documento_id")
    numero = _siguiente_numero(db, ctx, str(expediente.id), GovernmentGuaranteeRequirement)
    requisito = GovernmentGuaranteeRequirement(
        company_id=ctx.company_id,
        file_id=expediente.id,
        numero=numero,
        regla_codigo=r.codigo,
        regla=instantanea(r),
        tipo=r.tipo,
        etapa=r.etapa,
        nombre=nombre_final,
        forma=r.forma,
        porcentaje=porcentaje,
        monto_fijo=monto_fijo,
        moneda=moneda if r.forma == "MONTO_FIJO" else None,
        vigencia_minima_hasta=vigencia_minima_hasta,
        fundamento=fundamento,
        document_id=doc.id,
        document_version_id=version_doc.id,
        version_numero=version_doc.version_number,
        sha256=version_doc.sha256,
        registrado_en=instante_actual(),
        registrado_por=ctx.user_id or "",
        official_id=_funcionario_del_actor(db, ctx),
        created_by=ctx.user_id,
    )
    db.add(requisito)
    with db.begin_nested():
        db.flush()
    expediente.version += 1
    _evento(
        db,
        ctx,
        expediente,
        "GARANTIA",
        hoy,
        _titulo_requisito(requisito, numero),
    )
    _auditar(
        db,
        ctx,
        "GOV_GUARANTEE_REQUIREMENT_REGISTERED",
        expediente_id=str(expediente.id),
        after={
            "requisito": _ref("REQ", numero),
            "tipo": r.tipo,
            "regla": r.codigo,
            "documentos": doc.title,
        },
    )
    return obtener_estado_garantias(db, ctx, user, expediente_id)


def registrar_garantia(
    db: Session, ctx: CompanyContext, user: User, expediente_id: str, version: int | None, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    expediente = _para_escribir(db, ctx, expediente_id, version)
    _abierto(expediente)
    requisito = _requisito_del_expediente(db, ctx, expediente, _texto(cuerpo.get("requisito_id"), "requisito_id", 36))
    regla = requisito.regla or {}
    oferta = _oferta_del_expediente(db, ctx, expediente, _texto(cuerpo.get("oferta_id"), "oferta_id", 36))
    decision_id = None
    if regla.get("requiere_adjudicacion"):
        adj = _decision_vigente(db, str(expediente.id))
        if adj is None or adj.resultado != "ADJUDICADA":
            raise ConflictError(
                "GOV_GUARANTEE_AWARD_REQUIRED",
                "Este tipo de garantía exige una adjudicación vigente",
            )
        if oferta.id != adj.offer_id:
            raise _inv("oferta_id", "Solo el adjudicatario puede constituir esta garantía")
        decision_id = adj.id
    emisor = _emisor_del_ente(db, ctx, _texto(cuerpo.get("emisor_id"), "emisor_id", 36))
    referencia_emisor = _texto(cuerpo.get("referencia_emisor"), "referencia_emisor", 60)
    monto = _decimal(cuerpo.get("monto"), "monto")
    moneda = _moneda(cuerpo.get("moneda"))
    _validar_monto_moneda(monto, moneda)
    fecha_emision = _fecha(cuerpo.get("fecha_emision"), "fecha_emision")
    vigente_desde = _fecha(cuerpo.get("vigente_desde"), "vigente_desde")
    vigente_hasta = _fecha(cuerpo.get("vigente_hasta"), "vigente_hasta")
    _validar_fechas_instrumento(fecha_emision, vigente_desde, vigente_hasta)
    documento_id = _texto(cuerpo.get("documento_id"), "documento_id", 36)
    doc, version_doc = _documento(db, ctx, expediente, documento_id, "documento_id")
    observacion = cuerpo.get("observacion")
    if observacion is not None:
        observacion = _texto(observacion, "observacion", 1000)
    if not regla.get("permite_coexistencia"):
        existente = db.scalar(
            select(GovernmentGuaranteeInstrument).where(
                GovernmentGuaranteeInstrument.company_id == ctx.company_id,
                GovernmentGuaranteeInstrument.file_id == expediente.id,
                GovernmentGuaranteeInstrument.requirement_id == requisito.id,
                GovernmentGuaranteeInstrument.offer_id == oferta.id,
                GovernmentGuaranteeInstrument.estado == "REGISTRADA",
            )
        )
        if existente is not None:
            raise ConflictError(
                "GOV_GUARANTEE_ACTIVE_EXISTS",
                "Ya hay una garantía registrada para este requisito y sujeto",
            )
    duplicada = db.scalar(
        select(GovernmentGuaranteeInstrument).where(
            GovernmentGuaranteeInstrument.company_id == ctx.company_id,
            GovernmentGuaranteeInstrument.issuer_id == emisor.id,
            GovernmentGuaranteeInstrument.referencia_emisor == referencia_emisor,
            GovernmentGuaranteeInstrument.estado == "REGISTRADA",
        )
    )
    if duplicada is not None:
        raise ConflictError(
            "GOV_GUARANTEE_DUPLICATE",
            "Ya hay una garantía registrada con ese emisor y referencia",
        )
    evaluar_antes_de_actuar(
        db, ctx, "PROC03_GARANTIA_REGISTRAR", "GovernmentProcurementFile", str(expediente.id)
    )
    numero = _siguiente_numero(db, ctx, str(expediente.id), GovernmentGuaranteeInstrument)
    instrumento = GovernmentGuaranteeInstrument(
        company_id=ctx.company_id,
        file_id=expediente.id,
        numero=numero,
        requirement_id=requisito.id,
        tipo=requisito.tipo,
        etapa=requisito.etapa,
        offer_id=oferta.id,
        decision_id=decision_id,
        issuer_id=emisor.id,
        referencia_emisor=referencia_emisor,
        monto=monto,
        moneda=moneda,
        fecha_emision=fecha_emision,
        vigente_desde=vigente_desde,
        vigente_hasta=vigente_hasta,
        document_id=doc.id,
        document_version_id=version_doc.id,
        version_numero=version_doc.version_number,
        sha256=version_doc.sha256,
        observacion=observacion,
        origen="REGISTRO",
        antecesor_id=None,
        estado="REGISTRADA",
        afectada_en=None,
        registrada_en=instante_actual(),
        registrada_por=ctx.user_id or "",
        official_id=_funcionario_del_actor(db, ctx),
        created_by=ctx.user_id,
    )
    _insertar_protegido(
        db,
        instrumento,
        {"uq_gov_guarantee_instruments_emisor_referencia": ("GOV_GUARANTEE_DUPLICATE", "Ya hay una garantía registrada con ese emisor y referencia")},
    )
    _evento_garantia(
        db,
        ctx,
        expediente,
        instrumento,
        "REGISTRO",
        hoy_de_negocio(),
        None,
        document_id=str(doc.id),
        document_version_id=str(version_doc.id),
        version_numero=version_doc.version_number,
        sha256=version_doc.sha256,
    )
    expediente.version += 1
    _evento(
        db,
        ctx,
        expediente,
        "GARANTIA",
        hoy_de_negocio(),
        _titulo_garantia(instrumento, oferta, numero),
    )
    _auditar(
        db,
        ctx,
        "GOV_GUARANTEE_REGISTERED",
        expediente_id=str(expediente.id),
        after={
            "garantia": _ref("GAR", numero),
            "requisito": _ref("REQ", requisito.numero),
            "tipo": instrumento.tipo,
            "oferta": _ref("O", oferta.numero),
            "emisor": emisor.nombre,
            "monto": str(monto),
            "moneda": moneda,
            "vigente_hasta": vigente_hasta.isoformat(),
            "documentos": doc.title,
        },
    )
    return obtener_estado_garantias(db, ctx, user, expediente_id)


def _renovar_o_sustituir(
    db: Session,
    ctx: CompanyContext,
    user: User,
    expediente_id: str,
    garantia_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
    *,
    sustitucion: bool,
) -> dict[str, Any]:
    expediente = _para_escribir(db, ctx, expediente_id, version)
    _abierto(expediente)
    inst = _instrumento(db, ctx, expediente, garantia_id)
    requisito = _requisito_del_expediente(db, ctx, expediente, str(inst.requirement_id))
    regla = requisito.regla or {}
    motivo = _texto(cuerpo.get("motivo"), "motivo", 2000)
    if sustitucion:
        if not regla.get("permite_sustitucion"):
            raise ConflictError(
                "GOV_GUARANTEE_SUBSTITUTION_NOT_ALLOWED",
                "La regla de esta garantía no admite sustitución",
            )
        emisor = _emisor_del_ente(db, ctx, _texto(cuerpo.get("emisor_id"), "emisor_id", 36))
        referencia_emisor = _texto(cuerpo.get("referencia_emisor"), "referencia_emisor", 60)
        monto = _decimal(cuerpo.get("monto"), "monto")
        moneda = _moneda(cuerpo.get("moneda"))
        _validar_monto_moneda(monto, moneda)
        fecha_emision = _fecha(cuerpo.get("fecha_emision"), "fecha_emision")
        vigente_desde = _fecha(cuerpo.get("vigente_desde"), "vigente_desde")
        vigente_hasta = _fecha(cuerpo.get("vigente_hasta"), "vigente_hasta")
        _validar_fechas_instrumento(fecha_emision, vigente_desde, vigente_hasta)
        documento_id = _texto(cuerpo.get("documento_id"), "documento_id", 36)
        doc, version_doc = _documento(db, ctx, expediente, documento_id, "documento_id")
        duplicada = db.scalar(
            select(GovernmentGuaranteeInstrument).where(
                GovernmentGuaranteeInstrument.company_id == ctx.company_id,
                GovernmentGuaranteeInstrument.issuer_id == emisor.id,
                GovernmentGuaranteeInstrument.referencia_emisor == referencia_emisor,
                GovernmentGuaranteeInstrument.estado == "REGISTRADA",
                GovernmentGuaranteeInstrument.id != inst.id,
            )
        )
        if duplicada is not None:
            raise ConflictError(
                "GOV_GUARANTEE_DUPLICATE",
                "Ya hay una garantía registrada con ese emisor y referencia",
            )
        nuevo_estado = "SUSTITUIDA"
        nuevo_origen = "SUSTITUCION"
        nueva_accion = "SUSTITUCION"
        titulo_fn = _titulo_sustitucion
        auditoria_accion = "GOV_GUARANTEE_SUBSTITUTED"
        auditoria_after: dict[str, Any] = {
            "garantia": None,
            "sustituye": _ref("GAR", inst.numero),
            "emisor": emisor.nombre,
            "monto": str(monto),
            "moneda": moneda,
            "documentos": doc.title,
        }
    else:
        vigente_hasta = _fecha(cuerpo.get("vigente_hasta"), "vigente_hasta")
        if vigente_hasta <= inst.vigente_hasta:
            raise _inv(
                "vigente_hasta",
                f"Debe extender la vigencia anterior (hasta el {_formato_fecha(inst.vigente_hasta)})",
            )
        documento_id = _texto(cuerpo.get("documento_id"), "documento_id", 36)
        doc, version_doc = _documento(db, ctx, expediente, documento_id, "documento_id")
        if doc.id == inst.document_id and version_doc.id == inst.document_version_id:
            raise _inv("documento_id", "Adjunte el documento de la renovación")
        monto = _decimal(cuerpo.get("monto"), "monto") if cuerpo.get("monto") is not None else inst.monto
        if monto <= 0:
            raise _inv("monto", "El monto debe ser mayor que cero")
        moneda = inst.moneda
        fecha_emision = _fecha(cuerpo.get("fecha_emision"), "fecha_emision") if cuerpo.get("fecha_emision") is not None else hoy_de_negocio()
        vigente_desde = _fecha(cuerpo.get("vigente_desde"), "vigente_desde") if cuerpo.get("vigente_desde") is not None else inst.vigente_desde
        _validar_fechas_instrumento(fecha_emision, vigente_desde, vigente_hasta)
        emisor_actual = db.get(GovernmentGuaranteeIssuer, inst.issuer_id)
        if emisor_actual is None:
            raise _inv("emisor_id", "Emisor inexistente, inactivo o de otro ente")
        emisor = emisor_actual
        referencia_emisor = inst.referencia_emisor
        nuevo_estado = "RENOVADA"
        nuevo_origen = "RENOVACION"
        nueva_accion = "RENOVACION"
        titulo_fn = _titulo_renovacion
        auditoria_accion = "GOV_GUARANTEE_RENEWED"
        auditoria_after = {
            "garantia": None,
            "sustituye": _ref("GAR", inst.numero),
            "vigente_hasta": vigente_hasta.isoformat(),
            "monto": str(monto),
            "moneda": moneda,
            "documentos": doc.title,
        }
    evaluar_antes_de_actuar(
        db, ctx, "PROC03_GARANTIA_REGISTRAR", "GovernmentProcurementFile", str(expediente.id)
    )
    inst.estado = nuevo_estado
    inst.afectada_en = instante_actual()
    db.flush()
    numero_nuevo = _siguiente_numero(db, ctx, str(expediente.id), GovernmentGuaranteeInstrument)
    nuevo = GovernmentGuaranteeInstrument(
        company_id=ctx.company_id,
        file_id=expediente.id,
        numero=numero_nuevo,
        requirement_id=inst.requirement_id,
        tipo=inst.tipo,
        etapa=inst.etapa,
        offer_id=inst.offer_id,
        decision_id=inst.decision_id,
        issuer_id=emisor.id if emisor else inst.issuer_id,
        referencia_emisor=referencia_emisor,
        monto=monto,
        moneda=moneda,
        fecha_emision=fecha_emision,
        vigente_desde=vigente_desde,
        vigente_hasta=vigente_hasta,
        document_id=doc.id,
        document_version_id=version_doc.id,
        version_numero=version_doc.version_number,
        sha256=version_doc.sha256,
        observacion=None,
        origen=nuevo_origen,
        antecesor_id=inst.id,
        estado="REGISTRADA",
        afectada_en=None,
        registrada_en=instante_actual(),
        registrada_por=ctx.user_id or "",
        official_id=_funcionario_del_actor(db, ctx),
        created_by=ctx.user_id,
    )
    _insertar_protegido(
        db,
        nuevo,
        {"uq_gov_guarantee_instruments_emisor_referencia": ("GOV_GUARANTEE_DUPLICATE", "Ya hay una garantía registrada con ese emisor y referencia")},
    )
    _evento_garantia(
        db,
        ctx,
        expediente,
        inst,
        nueva_accion,
        hoy_de_negocio(),
        motivo,
        nuevo_instrument_id=str(nuevo.id),
        document_id=str(doc.id),
        document_version_id=str(version_doc.id),
        version_numero=version_doc.version_number,
        sha256=version_doc.sha256,
    )
    expediente.version += 1
    _evento(
        db,
        ctx,
        expediente,
        "GARANTIA",
        hoy_de_negocio(),
        titulo_fn(inst, nuevo, numero_nuevo),
    )
    auditoria_after["garantia"] = _ref("GAR", numero_nuevo)
    _auditar(
        db,
        ctx,
        auditoria_accion,
        expediente_id=str(expediente.id),
        after=auditoria_after,
        motivo=motivo,
    )
    return obtener_estado_garantias(db, ctx, user, expediente_id)


def renovar_garantia(
    db: Session, ctx: CompanyContext, user: User, expediente_id: str, garantia_id: str, version: int | None, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    return _renovar_o_sustituir(
        db, ctx, user, expediente_id, garantia_id, version, cuerpo, sustitucion=False
    )


def sustituir_garantia(
    db: Session, ctx: CompanyContext, user: User, expediente_id: str, garantia_id: str, version: int | None, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    return _renovar_o_sustituir(
        db, ctx, user, expediente_id, garantia_id, version, cuerpo, sustitucion=True
    )


def _liberar_o_ejecutar(
    db: Session,
    ctx: CompanyContext,
    user: User,
    expediente_id: str,
    garantia_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
    *,
    ejecucion: bool,
) -> dict[str, Any]:
    expediente = _para_escribir(db, ctx, expediente_id, version)
    _abierto(expediente)
    inst = _instrumento(db, ctx, expediente, garantia_id)
    requisito = _requisito_del_expediente(db, ctx, expediente, str(inst.requirement_id))
    regla = requisito.regla or {}
    acto = _acto_valido(db, ctx, _texto(cuerpo.get("acto_id"), "acto_id", 36))
    motivo = _texto(cuerpo.get("motivo"), "motivo", 2000)
    documento_id = cuerpo.get("documento_id")
    doc = None
    version_doc = None
    if documento_id:
        doc, version_doc = _documento(db, ctx, expediente, documento_id, "documento_id")
    if ejecucion:
        monto_ejecutado = _decimal(cuerpo.get("monto_ejecutado"), "monto_ejecutado")
        if monto_ejecutado <= 0 or monto_ejecutado > inst.monto:
            raise _inv(
                "monto_ejecutado",
                f"Debe ser mayor que cero y no superar {inst.monto} {inst.moneda}",
            )
        moneda = inst.moneda
        accion_sod = "PROC03_GARANTIA_EJECUTAR"
        nuevo_estado = "EJECUTADA"
        nueva_accion = "EJECUCION"
        titulo = _titulo_ejecucion(inst, monto_ejecutado, moneda)
        auditoria_accion = "GOV_GUARANTEE_EXECUTED"
        auditoria_after: dict[str, Any] = {
            "garantia": _ref("GAR", inst.numero),
            "acto": acto.numero,
            "monto_ejecutado": str(monto_ejecutado),
            "moneda": moneda,
        }
        precondicion = None
        precondicion_detalle = None
    else:
        monto_ejecutado = None
        moneda = None
        accion_sod = "PROC03_GARANTIA_LIBERAR"
        nuevo_estado = "LIBERADA"
        nueva_accion = "LIBERACION"
        titulo = _titulo_liberacion(inst)
        auditoria_accion = "GOV_GUARANTEE_RELEASED"
        auditoria_after = {
            "garantia": _ref("GAR", inst.numero),
            "acto": acto.numero,
            "precondicion": None,
        }
        if inst.tipo == "MANTENIMIENTO_OFERTA":
            final = _decision_vigente(db, str(expediente.id))
            if final is not None and (
                final.resultado in ("DESIERTA", "TERMINADA")
                or (final.resultado == "ADJUDICADA" and final.offer_id != inst.offer_id)
            ):
                precondicion = "VERIFICADA"
                if final.resultado == "ADJUDICADA":
                    texto = "adjudicada a otra oferta"
                elif final.resultado == "DESIERTA":
                    texto = "procedimiento declarado desierto"
                else:
                    texto = "procedimiento terminado"
                precondicion_detalle = f"{_ref('DEC', final.numero)}: {texto}"
            else:
                precondicion = "SOPORTADA_POR_ACTO"
                detalle = (
                    f"La plataforma no demuestra la condición ({regla.get('condicion_liberacion', '')}); "
                    f"la sostiene el acto {acto.tipo} {acto.numero}"
                )
                precondicion_detalle = detalle[:300]
        else:
            precondicion = "SOPORTADA_POR_ACTO"
            detalle = (
                f"La plataforma no demuestra la condición ({regla.get('condicion_liberacion', '')}); "
                f"la sostiene el acto {acto.tipo} {acto.numero}"
            )
            precondicion_detalle = detalle[:300]
        auditoria_after["precondicion"] = precondicion
    evaluar_antes_de_actuar(db, ctx, accion_sod, "GovernmentProcurementFile", str(expediente.id))
    inst.estado = nuevo_estado
    inst.afectada_en = instante_actual()
    db.flush()
    _evento_garantia(
        db,
        ctx,
        expediente,
        inst,
        nueva_accion,
        hoy_de_negocio(),
        motivo,
        act_id=str(acto.id),
        cargo_id=str(acto.cargo_id),
        document_id=str(doc.id) if doc else None,
        document_version_id=str(version_doc.id) if version_doc else None,
        version_numero=version_doc.version_number if version_doc else None,
        sha256=version_doc.sha256 if version_doc else None,
        monto=monto_ejecutado,
        moneda=moneda,
        precondicion=precondicion,
        precondicion_detalle=precondicion_detalle,
    )
    expediente.version += 1
    _evento(
        db,
        ctx,
        expediente,
        "GARANTIA",
        hoy_de_negocio(),
        titulo,
        act_id=str(acto.id),
        acto_etiqueta=f"{acto.tipo} {acto.numero}",
    )
    _auditar(
        db,
        ctx,
        auditoria_accion,
        expediente_id=str(expediente.id),
        after=auditoria_after,
        motivo=motivo,
    )
    return obtener_estado_garantias(db, ctx, user, expediente_id)


def liberar_garantia(
    db: Session, ctx: CompanyContext, user: User, expediente_id: str, garantia_id: str, version: int | None, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    return _liberar_o_ejecutar(
        db, ctx, user, expediente_id, garantia_id, version, cuerpo, ejecucion=False
    )


def ejecutar_garantia(
    db: Session, ctx: CompanyContext, user: User, expediente_id: str, garantia_id: str, version: int | None, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    return _liberar_o_ejecutar(
        db, ctx, user, expediente_id, garantia_id, version, cuerpo, ejecucion=True
    )
