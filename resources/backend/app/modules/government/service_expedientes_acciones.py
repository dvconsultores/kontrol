from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, NotFoundError
from app.modules.documents import service as documentos
from app.modules.documents.models import Document, DocumentType, DocumentVersion
from app.modules.government.models import (
    GovernmentProcurementCommittee,
    GovernmentProcurementCommitteeMember,
    GovernmentProcurementFile,
)
from app.modules.government.models import GovernmentProcurementFileEvent as Event
from app.modules.government.models import GovernmentProcurementFileFolio as Folio
from app.modules.government.models import GovernmentProcurementFileMilestone as Hito
from app.modules.government.models import GovernmentProcurementFileResponsible as Resp
from app.modules.government.service_comisiones import _ETIQUETAS_TIPO_ACTO, _acto_ref, situacion_de
from app.modules.government.service_expedientes import (
    _ETIQUETAS_ROL,
    CLASES_FOLIO,
    ENTIDAD,
    _abierto,
    _acto_valido,
    _auditar,
    _err,
    _etiqueta_funcionario,
    _evento,
    _funcionario,
    _para_escribir,
    _texto_responsable,
    detalle,
)
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.government.service_sod_funciones import verificar_antes_de_asumir_funcion
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio


def _after(**kw: Any) -> dict[str, Any]:
    permitidas = {"acto", "clase", "comision", "estado", "fecha", "fecha_prevista", "fecha_real", "folio", "funcionario", "hito", "modalidad", "motivo", "numero", "resultado", "rol", "secuencia", "titulo", "version"}
    return {k: v for k, v in kw.items() if k in permitidas}


def _f(d: date | None) -> str:
    if d is None:
        return "-"
    return d.strftime("%d/%m/%Y")


def _motivo(datos: dict[str, Any], campo: str = "motivo") -> str:
    v = datos.get(campo)
    if not isinstance(v, str) or not v.strip():
        raise _err(campo, "El motivo es obligatorio")
    return v.strip()


def _fecha(datos: dict[str, Any], campo: str = "fecha") -> date:
    v = datos.get(campo)
    if not isinstance(v, date) or isinstance(v, datetime):
        raise _err(campo, "La fecha es obligatoria")
    return v


def _en_rango(f: GovernmentProcurementFile, d: date, campo: str = "fecha") -> None:
    hoy = hoy_de_negocio()
    inicio = f.fecha_inicio
    if d < inicio or d > hoy:
        raise _err(campo, f"La fecha debe estar entre {inicio.isoformat()} y {hoy.isoformat()}")


def descartar(db: Session, ctx: CompanyContext, expediente_id: str, version: int | None, datos: dict[str, Any]) -> dict[str, Any]:
    f = _para_escribir(db, ctx, expediente_id, version)
    _abierto(f)
    motivo = _motivo(datos)
    folios = db.scalar(select(Folio.id).where(Folio.file_id == f.id, Folio.company_id == ctx.company_id).limit(1))
    hitos = db.scalar(select(Hito.id).where(Hito.file_id == f.id, Hito.company_id == ctx.company_id).limit(1))
    con_eventos = db.scalar(select(Event.id).where(Event.file_id == f.id, Event.company_id == ctx.company_id, Event.clase.in_(("ACTUACION", "DECISION"))).limit(1))
    if folios is not None or hitos is not None or con_eventos is not None:
        raise ConflictError("GOV_PROCUREMENT_FILE_CON_CONTENIDO", "El expediente tiene contenido: no puede descartarse")
    hoy = hoy_de_negocio()
    f.status = "DESCARTADO"
    f.cierre_fecha = hoy
    f.cierre_motivo = motivo
    f.version += 1
    _evento(db, ctx, f, "DESCARTE", hoy, "Expediente descartado", motivo=motivo)
    _auditar(db, ctx, "GOV_PROCUREMENT_FILE_DISCARDED", expediente_id=str(f.id), after=_after(motivo=motivo, estado=f.status, version=f.version))
    db.flush()
    return detalle(db, ctx, str(f.id))


def cerrar(db: Session, ctx: CompanyContext, expediente_id: str, version: int | None, datos: dict[str, Any]) -> dict[str, Any]:
    f = _para_escribir(db, ctx, expediente_id, version)
    _abierto(f)
    fecha = _fecha(datos)
    _en_rango(f, fecha)
    motivo = _motivo(datos)
    evaluar_antes_de_actuar(db, ctx, "PROC03_CERRAR", ENTIDAD, str(f.id))
    f.status = "CERRADO"
    f.cierre_fecha = fecha
    f.cierre_motivo = motivo
    f.closed_at = datetime.now(UTC)
    f.closed_by = ctx.user_id
    f.version += 1
    _evento(db, ctx, f, "CIERRE", fecha, "Expediente cerrado", motivo=motivo)
    _auditar(db, ctx, "GOV_PROCUREMENT_FILE_CLOSED", expediente_id=str(f.id), after=_after(motivo=motivo, estado=f.status, fecha=fecha, version=f.version))
    db.flush()
    return detalle(db, ctx, str(f.id))


def asignar_responsable(db: Session, ctx: CompanyContext, expediente_id: str, version: int | None, datos: dict[str, Any]) -> dict[str, Any]:
    f = _para_escribir(db, ctx, expediente_id, version)
    _abierto(f)
    valor = datos.get("funcionario_id")
    if not valor:
        raise _err("funcionario_id", "El funcionario es obligatorio")
    oficial = _funcionario(db, ctx, str(valor), "funcionario_id")
    rol = datos.get("rol") or "RESPONSABLE"
    if rol not in _ETIQUETAS_ROL:
        raise _err("rol", "Rol no válido")
    desde = datos.get("desde") or hoy_de_negocio()
    if not isinstance(desde, date) or isinstance(desde, datetime):
        raise _err("desde", "La fecha es obligatoria")
    _en_rango(f, desde, "desde")
    vigentes = _responsables_vigentes(db, f.id)
    for r in vigentes:
        if str(r.official_id) == str(oficial.id) and r.rol == rol:
            raise ConflictError("GOV_PROCUREMENT_FILE_RESPONSABLE_DUPLICADO", "El funcionario ya está vigente en ese rol")
        if rol == "RESPONSABLE" and r.rol == "RESPONSABLE":
            raise ConflictError("GOV_PROCUREMENT_FILE_PRINCIPAL_VIGENTE", "Termine primero al responsable vigente")
    if rol == "REQUIRENTE":
        verificar_antes_de_asumir_funcion(db, ctx, f, "SOLICITANTE", official_ids=[oficial.id])
    nombre, cargo, unidad_txt = _etiqueta_funcionario(db, ctx, oficial, desde)
    fila = Resp(file_id=f.id, company_id=ctx.company_id, official_id=str(oficial.id), funcionario_nombre=nombre, cargo_nombre=cargo, unidad_nombre=unidad_txt, rol=rol, desde=desde, created_by=ctx.user_id)
    db.add(fila)
    db.flush()
    etiqueta = _texto_responsable(nombre, cargo, unidad_txt)
    _evento(db, ctx, f, "RESPONSABLE", desde, f"{_ETIQUETAS_ROL[rol]}: {nombre}", official_id=str(oficial.id), responsable_etiqueta=etiqueta)
    f.version += 1
    _auditar(db, ctx, "GOV_PROCUREMENT_FILE_RESPONSIBLE_ASSIGNED", expediente_id=str(f.id), after=_after(funcionario=nombre, rol=rol, fecha=desde, version=f.version))
    db.flush()
    return detalle(db, ctx, str(f.id))


def terminar_responsable(db: Session, ctx: CompanyContext, expediente_id: str, version: int | None, responsable_id: str, datos: dict[str, Any]) -> dict[str, Any]:
    f = _para_escribir(db, ctx, expediente_id, version)
    fila = db.scalar(select(Resp).where(Resp.id == responsable_id, Resp.file_id == f.id, Resp.company_id == ctx.company_id))
    if fila is None:
        raise NotFoundError("GOV_PROCUREMENT_FILE_RESPONSABLE_NOT_FOUND", "Responsable no encontrado")
    _abierto(f)
    if fila.fin_efectivo is not None:
        raise ConflictError("GOV_PROCUREMENT_FILE_RESPONSABLE_TERMINADO", "El responsable ya está terminado")
    fecha = _fecha(datos)
    _en_rango(f, fecha)
    motivo = _motivo(datos)
    fila.fin_efectivo = fecha
    fila.motivo_fin = motivo
    _evento(db, ctx, f, "RESPONSABLE", fecha, f"Termina {_ETIQUETAS_ROL.get(fila.rol, fila.rol)}: {fila.funcionario_nombre}", motivo=motivo)
    f.version += 1
    _auditar(db, ctx, "GOV_PROCUREMENT_FILE_RESPONSIBLE_ENDED", expediente_id=str(f.id), after=_after(funcionario=fila.funcionario_nombre, rol=fila.rol, fecha=fecha, motivo=motivo, version=f.version))
    db.flush()
    return detalle(db, ctx, str(f.id))


def registrar_comision(db: Session, ctx: CompanyContext, expediente_id: str, version: int | None, datos: dict[str, Any]) -> dict[str, Any]:
    f = _para_escribir(db, ctx, expediente_id, version)
    _abierto(f)
    comision_id = datos.get("comision_id")
    no_aplica = datos.get("no_aplica_motivo")
    if bool(comision_id) == bool(no_aplica):
        raise _err("comision_id", "Indique una comisión o un motivo de no aplicación")
    hoy = hoy_de_negocio()
    c = None
    if comision_id:
        c = db.scalar(select(GovernmentProcurementCommittee).where(GovernmentProcurementCommittee.id == comision_id, GovernmentProcurementCommittee.company_id == ctx.company_id))
        if c is None or situacion_de(c, hoy) != "EN_VIGOR":
            raise _err("comision_id", "La comisión debe estar en vigor en este ente")
    motivo = None
    if f.committee_id or f.comision_no_aplica_motivo:
        motivo = _motivo(datos)
    codigo = getattr(c, "codigo", "") if c else ""
    nombre = getattr(c, "nombre", "") if c else ""
    if c:
        miembros = db.execute(
            select(GovernmentProcurementCommitteeMember.official_id).where(
                GovernmentProcurementCommitteeMember.company_id == ctx.company_id,
                GovernmentProcurementCommitteeMember.committee_id == c.id,
                GovernmentProcurementCommitteeMember.fin_efectivo.is_(None),
            )
        ).scalars().all()
        verificar_antes_de_asumir_funcion(db, ctx, f, "EVALUADOR", official_ids=miembros)
    if c:
        f.committee_id = str(c.id)
        f.comision_no_aplica_motivo = None
        titulo = f"Comisión {codigo} · {nombre} vinculada"
    else:
        f.committee_id = None
        f.comision_no_aplica_motivo = no_aplica
        titulo = "Se declara que no interviene comisión"
    f.version += 1
    _evento(db, ctx, f, "COMISION", hoy, titulo, detalle=no_aplica, motivo=motivo)
    _auditar(db, ctx, "GOV_PROCUREMENT_FILE_COMMISSION_LINKED", expediente_id=str(f.id), after=_after(comision=nombre or no_aplica, motivo=motivo, version=f.version))
    db.flush()
    return detalle(db, ctx, str(f.id))


def registrar_actuacion(db: Session, ctx: CompanyContext, expediente_id: str, version: int | None, datos: dict[str, Any]) -> dict[str, Any]:
    f = _para_escribir(db, ctx, expediente_id, version)
    _abierto(f)
    clase = datos.get("clase") or "ACTUACION"
    if clase not in ("ACTUACION", "DECISION"):
        raise _err("clase", "Clase no válida")
    fecha = _fecha(datos)
    _en_rango(f, fecha)
    titulo = datos.get("titulo")
    if not isinstance(titulo, str) or not titulo.strip():
        raise _err("titulo", "El título es obligatorio")
    valor_funcionario = datos.get("funcionario_id")
    if not valor_funcionario:
        raise _err("funcionario_id", "El funcionario es obligatorio")
    oficial = _funcionario(db, ctx, str(valor_funcionario), "funcionario_id")
    res = _etiqueta_funcionario(db, ctx, oficial, fecha)
    etiqueta_res = _texto_responsable(res[0], res[1], res[2])
    resultado = datos.get("resultado")
    if clase == "DECISION" and (not isinstance(resultado, str) or not resultado.strip()):
        raise _err("resultado", "El resultado es obligatorio")
    acto = None
    if datos.get("acto_id"):
        acto = _acto_valido(db, ctx, str(datos["acto_id"]))
    folio = None
    if datos.get("folio_id"):
        folio = db.scalar(select(Folio).where(Folio.id == datos["folio_id"], Folio.file_id == f.id, Folio.company_id == ctx.company_id))
        if folio is None:
            raise _err("folio_id", "El folio no pertenece a este expediente")
    hito = None
    if datos.get("hito_id"):
        hito = db.scalar(select(Hito).where(Hito.id == datos["hito_id"], Hito.file_id == f.id, Hito.company_id == ctx.company_id))
        if hito is None:
            raise _err("hito_id", "El hito no pertenece a este expediente")
    rectifica_id = datos.get("rectifica_id")
    original = None
    motivo = None
    if rectifica_id:
        original = db.scalar(select(Event).where(Event.id == rectifica_id, Event.file_id == f.id, Event.company_id == ctx.company_id))
        if original is None or original.clase not in ("ACTUACION", "DECISION"):
            raise _err("rectifica_id", "El evento no existe o no es rectificable")
        ya = db.scalar(select(Event.id).where(Event.rectifica_id == original.id, Event.company_id == ctx.company_id))
        if ya is not None:
            raise ConflictError("GOV_PROCUREMENT_FILE_YA_RECTIFICADA", "El evento ya está rectificado")
        motivo = _motivo(datos)
    if clase == "DECISION":
        evaluar_antes_de_actuar(db, ctx, "PROC03_DECIDIR", ENTIDAD, str(f.id))
    ref = _acto_ref(db, acto) if acto is not None else None
    acto_etiqueta = ref["etiqueta"] if ref else None
    folio_et = f"Folio {folio.numero} · {folio.etiqueta}" if folio else None
    evento = _evento(db, ctx, f, clase, fecha, titulo, detalle=datos.get("detalle"), resultado=resultado, official_id=str(oficial.id), responsable_etiqueta=etiqueta_res, act_id=str(acto.id) if acto else None, acto_etiqueta=acto_etiqueta, folio_id=str(folio.id) if folio else None, folio_etiqueta=folio_et, milestone_id=str(hito.id) if hito else None, hito_etiqueta=hito.nombre if hito else None, rectifica_id=str(original.id) if original is not None else None, motivo=motivo)
    accion = "GOV_PROCUREMENT_FILE_DECISION_RECORDED" if clase == "DECISION" else "GOV_PROCUREMENT_FILE_ACTION_RECORDED"
    f.version += 1
    _auditar(db, ctx, accion, expediente_id=str(f.id), after=_after(clase=clase, secuencia=evento.secuencia, titulo=titulo, fecha=fecha, version=f.version))
    db.flush()
    return detalle(db, ctx, str(f.id))


def incorporar_folio(db: Session, ctx: CompanyContext, expediente_id: str, version: int | None, datos: dict[str, Any]) -> dict[str, Any]:
    f = _para_escribir(db, ctx, expediente_id, version)
    _abierto(f)
    clase = datos.get("clase")
    codigos = {c[0] for c in CLASES_FOLIO}
    if clase not in codigos:
        raise _err("clase", "Clase de folio no válida")
    documento_id = datos.get("documento_id")
    acto_id = datos.get("acto_id")
    if bool(documento_id) == bool(acto_id):
        raise _err("documento_id", "Indique un documento o un acto")
    reservado = bool(datos.get("reservado"))
    motivo_reserva = datos.get("motivo_reserva")
    if reservado and (not isinstance(motivo_reserva, str) or not motivo_reserva.strip()):
        raise _err("motivo_reserva", "El motivo de reserva es obligatorio")
    hito = None
    if datos.get("hito_id"):
        hito = db.scalar(select(Hito).where(Hito.id == datos["hito_id"], Hito.file_id == f.id, Hito.company_id == ctx.company_id))
        if hito is None:
            raise _err("hito_id", "El hito no pertenece a este expediente")
    hoy = hoy_de_negocio()
    numero = db.scalar(select(Folio.numero).where(Folio.file_id == f.id, Folio.company_id == ctx.company_id).order_by(Folio.numero.desc()).limit(1)) or 0
    numero += 1
    etiqueta_clase = dict((c[0], c[1]) for c in CLASES_FOLIO).get(clase, clase)

    if documento_id:
        doc = db.scalar(select(Document).where(Document.id == documento_id, Document.company_id == ctx.company_id))
        if doc is None or doc.status not in ("DRAFT", "ACTIVE") or documentos.documento_sellado(db, documento_id):
            raise _err("documento_id", "El documento no existe en este ente")
        if doc.current_version_id is None:
            raise _err("documento_id", "El documento no tiene archivo")
        version_doc = db.get(DocumentVersion, doc.current_version_id)
        if version_doc is None:
            raise _err("documento_id", "El documento no tiene versión vigente")
        documentos.assert_deliverable(db, version_doc)
        dup = db.scalar(select(Folio.id).where(Folio.file_id == f.id, Folio.document_id == doc.id, Folio.document_version_id == version_doc.id, Folio.company_id == ctx.company_id))
        if dup is not None:
            raise ConflictError("GOV_PROCUREMENT_FILE_FOLIO_DUPLICADO", "El documento ya está foliado en esta versión")
        actor = db.get(User, ctx.user_id)
        documentos.attach(db, document=doc, resource_type=ENTIDAD, resource_id=str(f.id), actor=actor)
        tipo = db.get(DocumentType, doc.document_type_id) if doc.document_type_id else None
        if tipo is None:
            raise _err("documento_id", "El tipo documental no existe")
        etiqueta = (doc.title or "")[:400]
        tipo_etiqueta = tipo.name
        fecha_doc = doc.issued_at
        fila = Folio(file_id=f.id, company_id=ctx.company_id, numero=numero, clase=clase, document_id=str(doc.id), document_version_id=str(version_doc.id), version_numero=version_doc.version_number, etiqueta=etiqueta, tipo_etiqueta=tipo_etiqueta, fecha_documento=fecha_doc, fecha_incorporacion=hoy, reservado=reservado, motivo_reserva=motivo_reserva, milestone_id=str(hito.id) if hito else None, created_by=ctx.user_id)
        db.add(fila)
        db.flush()
        folio_et = f"Folio {numero} · {fila.etiqueta}"
        _evento(db, ctx, f, "DOCUMENTO", hoy, f"Folio {numero}: {etiqueta_clase}", folio_id=str(fila.id), folio_etiqueta=folio_et, milestone_id=str(hito.id) if hito else None, hito_etiqueta=hito.nombre if hito else None)
        f.version += 1
        _auditar(db, ctx, "GOV_PROCUREMENT_FILE_DOCUMENT_LINKED", expediente_id=str(f.id), after=_after(folio=numero, clase=clase, hito=hito.nombre if hito else None, version=f.version))
    else:
        acto = _acto_valido(db, ctx, str(acto_id))
        dup = db.scalar(select(Folio.id).where(Folio.file_id == f.id, Folio.act_id == acto.id, Folio.company_id == ctx.company_id))
        if dup is not None:
            raise ConflictError("GOV_PROCUREMENT_FILE_FOLIO_DUPLICADO", "El acto ya está foliado")
        ref = _acto_ref(db, acto)
        etiqueta = ref["etiqueta"] if ref else ""
        tipo_etiqueta = _ETIQUETAS_TIPO_ACTO.get(acto.tipo, acto.tipo)
        fila = Folio(file_id=f.id, company_id=ctx.company_id, numero=numero, clase=clase, act_id=str(acto.id), etiqueta=etiqueta, tipo_etiqueta=tipo_etiqueta, fecha_documento=acto.fecha, fecha_incorporacion=hoy, reservado=reservado, motivo_reserva=motivo_reserva, milestone_id=str(hito.id) if hito else None, created_by=ctx.user_id)
        db.add(fila)
        db.flush()
        folio_et = f"Folio {numero} · {fila.etiqueta}"
        _evento(db, ctx, f, "ACTO", hoy, f"Folio {numero}: {etiqueta_clase}", folio_id=str(fila.id), folio_etiqueta=folio_et, act_id=str(acto.id), acto_etiqueta=etiqueta, milestone_id=str(hito.id) if hito else None, hito_etiqueta=hito.nombre if hito else None)
        f.version += 1
        _auditar(db, ctx, "GOV_PROCUREMENT_FILE_ACT_LINKED", expediente_id=str(f.id), after=_after(folio=numero, clase=clase, acto=etiqueta, version=f.version))
    db.flush()
    return detalle(db, ctx, str(f.id))


def crear_hito(db: Session, ctx: CompanyContext, expediente_id: str, version: int | None, datos: dict[str, Any]) -> dict[str, Any]:
    f = _para_escribir(db, ctx, expediente_id, version)
    _abierto(f)
    nombre = datos.get("nombre")
    if not isinstance(nombre, str) or not nombre.strip():
        raise _err("nombre", "El nombre es obligatorio")
    fecha_prevista = datos.get("fecha_prevista")
    if not isinstance(fecha_prevista, date) or isinstance(fecha_prevista, datetime):
        raise _err("fecha_prevista", "La fecha prevista es obligatoria")
    oficial = None
    if datos.get("funcionario_id"):
        oficial = _funcionario(db, ctx, str(datos["funcionario_id"]), "funcionario_id")
    responsable_etiqueta = None
    hoy = hoy_de_negocio()
    if oficial:
        r = _etiqueta_funcionario(db, ctx, oficial, hoy)
        responsable_etiqueta = _texto_responsable(r[0], r[1], r[2])
    fuente_hito = datos.get("fuente")
    fila = Hito(file_id=f.id, company_id=ctx.company_id, nombre=nombre.strip(), fecha_prevista=fecha_prevista, estado="PREVISTO", official_id=str(oficial.id) if oficial else None, responsable_etiqueta=responsable_etiqueta, created_by=ctx.user_id, fuente=fuente_hito)
    db.add(fila)
    db.flush()
    _evento(db, ctx, f, "HITO", hoy, f"Hito previsto: {fila.nombre}", detalle=f"Fecha prevista {_f(fecha_prevista)}", milestone_id=str(fila.id), hito_etiqueta=fila.nombre, responsable_etiqueta=responsable_etiqueta)
    f.version += 1
    _auditar(db, ctx, "GOV_PROCUREMENT_FILE_MILESTONE_CREATED", expediente_id=str(f.id), after=_after(hito=fila.nombre, fecha_prevista=fecha_prevista, version=f.version))
    db.flush()
    return detalle(db, ctx, str(f.id))


def actualizar_hito(db: Session, ctx: CompanyContext, expediente_id: str, version: int | None, hito_id: str, datos: dict[str, Any]) -> dict[str, Any]:
    f = _para_escribir(db, ctx, expediente_id, version)
    fila = db.scalar(select(Hito).where(Hito.id == hito_id, Hito.file_id == f.id, Hito.company_id == ctx.company_id))
    if fila is None:
        raise NotFoundError("GOV_PROCUREMENT_FILE_HITO_NOT_FOUND", "Hito no encontrado")
    _abierto(f)
    hoy = hoy_de_negocio()
    antes_prev = fila.fecha_prevista
    antes_real = fila.fecha_real
    antes_estado = fila.estado
    nueva_prev = datos.get("fecha_prevista", antes_prev)
    if not isinstance(nueva_prev, date) or isinstance(nueva_prev, datetime):
        raise _err("fecha_prevista", "La fecha prevista no es válida")
    quitar_real = datos.get("quitar_fecha_real", False)
    nueva_real = None if quitar_real else datos.get("fecha_real", antes_real)
    if nueva_real is not None:
        if not isinstance(nueva_real, date) or isinstance(nueva_real, datetime):
            raise _err("fecha_real", "La fecha real no es válida")
        if nueva_real < f.fecha_inicio or nueva_real > hoy:
            raise _err("fecha_real", "La fecha real debe estar entre el inicio y hoy")
    no_aplica = bool(datos.get("no_aplica"))
    motivo_no_aplica = datos.get("motivo_no_aplica")
    if no_aplica and nueva_real is not None:
        raise _err("fecha_real", "Un hito no aplicable no puede tener fecha real")
    if no_aplica:
        if not isinstance(motivo_no_aplica, str) or not motivo_no_aplica.strip():
            raise _err("motivo_no_aplica", "El motivo es obligatorio")
        nuevo_estado = "NO_APLICA"
    elif nueva_real is not None:
        nuevo_estado = "CUMPLIDO"
    else:
        nuevo_estado = "PREVISTO"
    motivo = datos.get("motivo")
    exige = nueva_prev != antes_prev or (antes_real is not None and nueva_real != antes_real) or (antes_estado == "NO_APLICA" and nuevo_estado != "NO_APLICA")
    if exige and (not isinstance(motivo, str) or not motivo.strip()):
        raise _err("motivo", "El motivo es obligatorio")
    fuente = datos.get("fuente", fila.fuente)
    oficial = None
    if datos.get("funcionario_id"):
        oficial = _funcionario(db, ctx, str(datos["funcionario_id"]), "funcionario_id")
    resp = fila.responsable_etiqueta
    if oficial:
        r = _etiqueta_funcionario(db, ctx, oficial, hoy)
        resp = _texto_responsable(r[0], r[1], r[2])
    sin_cambios = nueva_prev == antes_prev and nueva_real == antes_real and nuevo_estado == antes_estado and (not oficial) and fuente == fila.fuente and (motivo_no_aplica if no_aplica else None) == fila.motivo_no_aplica
    if sin_cambios:
        return detalle(db, ctx, str(f.id))
    fila.fecha_prevista = nueva_prev
    fila.fecha_real = nueva_real
    fila.estado = nuevo_estado
    fila.motivo_no_aplica = motivo_no_aplica if no_aplica else None
    fila.fuente = fuente
    if oficial:
        fila.official_id = str(oficial.id)
        fila.responsable_etiqueta = resp
    nombre = fila.nombre
    if nuevo_estado == "CUMPLIDO" and antes_estado != "CUMPLIDO":
        titulo = f"Hito cumplido: {nombre}"
    elif nuevo_estado == "NO_APLICA" and antes_estado != "NO_APLICA":
        titulo = f"Hito no aplica: {nombre}"
    elif nueva_prev != antes_prev:
        titulo = f"Hito reprogramado: {nombre}"
    else:
        titulo = f"Hito actualizado: {nombre}"
    detalle_txt = f"Prevista {_f(antes_prev)}→{_f(nueva_prev)}; real {_f(antes_real)}→{_f(nueva_real)}"
    fecha_ev = nueva_real or hoy
    _evento(db, ctx, f, "HITO", fecha_ev, titulo, detalle=detalle_txt, milestone_id=str(fila.id), hito_etiqueta=nombre, motivo=motivo, responsable_etiqueta=resp)
    f.version += 1
    _auditar(db, ctx, "GOV_PROCUREMENT_FILE_MILESTONE_UPDATED", expediente_id=str(f.id), after=_after(hito=nombre, estado=nuevo_estado, fecha_prevista=nueva_prev, fecha_real=nueva_real, motivo=motivo, version=f.version))
    db.flush()
    return detalle(db, ctx, str(f.id))


def _responsables_vigentes(db: Session, expediente_id: Any) -> list[Resp]:
    hoy = hoy_de_negocio()
    stmt = select(Resp).where(Resp.file_id == expediente_id, Resp.desde <= hoy, (Resp.fin_efectivo.is_(None) | (Resp.fin_efectivo >= hoy)))
    return list(db.scalars(stmt).all())
