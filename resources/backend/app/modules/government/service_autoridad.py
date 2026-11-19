"""Servicio de la matriz de autoridad, proyección de solo lectura (GOV-0 · ORG-07)."""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentLink
from app.modules.government.models import (
    ACCIONES_COMPETENCIA,
    MATERIAS_COMPETENCIA,
    GovernmentPosition,
    GovernmentPositionVersion,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.service_cargos import _auditar
from app.modules.government.service_estructura import _estructura, _utc
from app.shared.clock import hoy_de_negocio, limites_del_dia_utc


def _fecha_corte(ejercicio: int, fecha: date | None) -> date:
    """Calcula la fecha de corte por defecto y valida que pertenezca al ejercicio."""
    hoy = hoy_de_negocio()
    if fecha is None:
        if hoy.year == ejercicio:
            return hoy
        if ejercicio < hoy.year:
            return date(ejercicio, 12, 31)
        return date(ejercicio, 1, 1)
    if fecha.year != ejercicio:
        raise KontrolError(
            code="GOV_AUTHORITY_DATE_OUT_OF_EXERCISE",
            message="La fecha debe estar dentro del ejercicio",
            field_errors={"fecha": ["La fecha debe estar dentro del ejercicio"]},
            status_code=422,
        )
    return fecha


def _version_en_vigor(versiones: list[GovernmentPositionVersion], fin_utc: Any) -> GovernmentPositionVersion | None:
    """Devuelve la última versión vigente o inactiva anterior a la fecha de corte."""
    ordenadas = sorted(versiones, key=lambda v: v.version)
    candidatas = [
        v for v in ordenadas if v.status in ("VIGENTE", "INACTIVO") and _utc(v.created_at) < fin_utc
    ]
    if candidatas:
        return candidatas[-1]
    for v in ordenadas:
        if v.status == "VIGENTE":
            return v
    return None


def competencias_en_vigor(db: Session, cargo: GovernmentPosition, fecha: date) -> list[dict[str, Any]]:
    """Competencias del cargo en vigor en la fecha (la misma regla de versión que la matriz de autoridad)."""
    versiones = list(
        db.scalars(
            select(GovernmentPositionVersion).where(
                GovernmentPositionVersion.position_id == str(cargo.id),
                GovernmentPositionVersion.company_id == cargo.company_id,
            )
        )
    )
    version = _version_en_vigor(versiones, limites_del_dia_utc(fecha)[1])
    if version is None:
        return []
    return list(version.snapshot.get("competencias") or [])


def _ruta(unidades: list[GovernmentUnit], unidad_id: str) -> str:
    """Calcula la ruta de códigos desde la raíz hasta la unidad."""
    por_id = {str(u.id): u for u in unidades}
    codigos: list[str] = []
    actual_id: str | None = unidad_id
    visitados: set[str] = set()
    while actual_id is not None and actual_id not in visitados:
        visitados.add(actual_id)
        unidad = por_id.get(actual_id)
        if unidad is None:
            break
        codigos.append(unidad.code)
        actual_id = str(unidad.parent_id) if unidad.parent_id is not None else None
    return " › ".join(reversed(codigos))


def _descendientes(unidades: list[GovernmentUnit], unidad_id: str) -> set[str]:
    """Devuelve la unidad y todas sus subunidades."""
    por_padre: dict[str | None, list[GovernmentUnit]] = {}
    for u in unidades:
        clave = str(u.parent_id) if u.parent_id is not None else None
        por_padre.setdefault(clave, []).append(u)
    resultado: set[str] = set()
    pendientes = [unidad_id]
    while pendientes:
        actual = pendientes.pop()
        if actual in resultado:
            continue
        resultado.add(actual)
        pendientes.extend(str(u.id) for u in por_padre.get(actual, []))
    return resultado


def _clave_orden(fila: dict[str, Any]) -> tuple[str, str, int, int, int, str]:
    """Clave de ordenación fija de la matriz: la fila del cargo antes que sus delegaciones."""
    fuente = fila.get("fuente") or {}
    delegada = 1 if fuente.get("grupo") == "DELEGACION" else 0
    return (
        fila["ruta_unidad"],
        fila["cargo_codigo"],
        ACCIONES_COMPETENCIA.index(fila["accion"]),
        MATERIAS_COMPETENCIA.index(fila["materia"]),
        delegada,
        fuente.get("asignacion_codigo") or "",
    )


def _persona(ref: dict[str, Any] | None, ver_personas: bool) -> dict[str, Any] | None:
    """Persona de ORG-04 sin documento de identidad; reservada sin `gobierno_ocupacion:view` (OD-EA-01)."""
    if ref is None or not ver_personas:
        return None
    return {"id": str(ref["id"]), "codigo": ref["codigo"], "nombre": ref["nombre"]}


def _fuente_de_fila(fuente: dict[str, Any], ver_personas: bool) -> dict[str, Any]:
    """Proyecta la fuente que resolvió ORG-04 (D-EA-04), sin decidir nada sobre ella."""
    cargo_origen = fuente.get("cargo_origen")
    acto = fuente.get("acto")
    return {
        "figura": fuente["figura"],
        "figura_etiqueta": fuente["figura_etiqueta"],
        "grupo": fuente["grupo"],
        "asignacion_id": fuente["asignacion_id"],
        "asignacion_codigo": fuente["asignacion_codigo"],
        "desde": fuente["desde"],
        "hasta": fuente["hasta"],
        "fin_efectivo": fuente["fin_efectivo"],
        "persona": _persona(fuente.get("funcionario"), ver_personas),
        "persona_reservada": fuente.get("funcionario") is not None and not ver_personas,
        "sustituye_a": _persona(fuente.get("sustituye_a"), ver_personas),
        "sustituye_reservado": fuente.get("sustituye_a") is not None and not ver_personas,
        "cargo_origen": (
            {"id": str(cargo_origen["id"]), "codigo": cargo_origen["codigo"], "denominacion": cargo_origen["nombre"]}
            if cargo_origen
            else None
        ),
        "acto": (
            {
                "id": str(acto["id"]),
                "tipo": acto["tipo"],
                "numero": acto["numero"],
                "fecha": acto["fecha"],
                "fecha_eficacia": acto["fecha_eficacia"],
            }
            if acto
            else None
        ),
        "avocaciones": fuente.get("avocaciones", 0),
    }


def _origen(fuente: dict[str, Any] | None) -> str:
    """`origen` con el vocabulario de ORG-04: CARGO si ejerce el titular o el cargo está vacante (D-EA-03)."""
    if fuente is None or fuente["grupo"] == "TITULARIDAD":
        return "CARGO"
    return str(fuente["figura"])


def listar_ejercicios(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    """Lista los ejercicios con estructura de la compañía, descendentes."""
    stmt = (
        select(GovernmentStructure)
        .where(GovernmentStructure.company_id == ctx.company_id)
        .order_by(GovernmentStructure.exercise.desc())
    )
    estructuras = db.execute(stmt).scalars().all()
    return {"items": [{"ejercicio": e.exercise, "estado": e.status} for e in estructuras]}


def filtros(db: Session, ctx: CompanyContext, ejercicio: int) -> dict[str, Any]:
    """Devuelve las unidades y los cargos activos usables como filtros."""
    est = _estructura(db, ctx, ejercicio, bloquear=False)
    stmt_unidades = (
        select(GovernmentUnit)
        .where(
            GovernmentUnit.structure_id == est.id,
            GovernmentUnit.company_id == est.company_id,
        )
        .order_by(GovernmentUnit.code.asc())
    )
    unidades = list(db.execute(stmt_unidades).scalars().all())
    unidades_out = [
        {"id": str(u.id), "codigo": u.code, "denominacion": u.name, "ruta": _ruta(unidades, str(u.id))}
        for u in unidades
    ]
    unidades_out.sort(key=lambda u: u["ruta"])

    stmt_cargos = (
        select(GovernmentPosition)
        .where(
            GovernmentPosition.structure_id == est.id,
            GovernmentPosition.company_id == est.company_id,
            GovernmentPosition.status.in_(("VIGENTE", "INACTIVO")),
        )
        .order_by(GovernmentPosition.code.asc())
    )
    cargos = list(db.execute(stmt_cargos).scalars().all())
    return {
        "unidades": unidades_out,
        "cargos": [{"id": str(c.id), "codigo": c.code, "denominacion": c.name} for c in cargos],
    }


def _filtrar(
    filas: list[dict[str, Any]],
    unidades: list[GovernmentUnit],
    cargos: list[GovernmentPosition],
    unidad_id: str | None,
    cargo_id: str | None,
    accion: str | None,
    materia: str | None,
    texto: str | None,
) -> list[dict[str, Any]]:
    """Aplica y valida los filtros sobre las filas proyectadas."""
    ids_unidades = {str(u.id) for u in unidades}
    ids_cargos = {str(c.id) for c in cargos}
    if unidad_id is not None and unidad_id not in ids_unidades:
        raise KontrolError(
            code="GOV_AUTHORITY_INVALID_FILTER",
            message="El filtro no pertenece a esta estructura",
            field_errors={"unidad_id": ["No pertenece a esta estructura"]},
            status_code=422,
        )
    if cargo_id is not None and cargo_id not in ids_cargos:
        raise KontrolError(
            code="GOV_AUTHORITY_INVALID_FILTER",
            message="El filtro no pertenece a esta estructura",
            field_errors={"cargo_id": ["No pertenece a esta estructura"]},
            status_code=422,
        )

    descendientes: set[str] | None = _descendientes(unidades, unidad_id) if unidad_id else None
    texto_norm = texto.strip().casefold() if texto is not None and texto.strip() else None

    resultado: list[dict[str, Any]] = []
    for fila in filas:
        if descendientes is not None and fila["unidad_id"] not in descendientes:
            continue
        if cargo_id is not None and fila["cargo_id"] != cargo_id:
            continue
        if accion is not None and fila["accion"] != accion:
            continue
        if materia is not None and fila["materia"] != materia:
            continue
        if texto_norm is not None:
            fuente = fila.get("fuente") or {}
            persona = fuente.get("persona") or {}
            campos = (
                fila["cargo_codigo"],
                fila["cargo_denominacion"],
                fila["unidad_codigo"] or "",
                fila["unidad_denominacion"] or "",
                fila["ruta_unidad"],
                fila["fundamento"] or "",
                fuente.get("asignacion_codigo") or "",
                # Solo la persona visible: el texto no revela a una persona reservada (OD-EA-01).
                persona.get("codigo") or "",
                persona.get("nombre") or "",
            )
            if not any(texto_norm in campo.casefold() for campo in campos):
                continue
        resultado.append(fila)
    return resultado


def _filas_filtradas(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    *,
    fecha: date | None,
    unidad_id: str | None,
    cargo_id: str | None,
    accion: str | None,
    materia: str | None,
    texto: str | None,
    ver_personas: bool = False,
) -> tuple[GovernmentStructure, date, list[dict[str, Any]]]:
    """Proyecta y filtra la matriz completa una sola vez: autoridad del cargo (ORG-03) y efectiva (ORG-04)."""
    # ORG-04 consume `competencias_en_vigor` de este módulo: la importación diferida evita el ciclo.
    from app.modules.government.service_ocupacion import autoridad_efectiva_en

    est = _estructura(db, ctx, ejercicio, bloquear=False)
    d = _fecha_corte(ejercicio, fecha)

    stmt_cargos = (
        select(GovernmentPosition)
        .where(
            GovernmentPosition.structure_id == est.id,
            GovernmentPosition.company_id == est.company_id,
        )
        .order_by(GovernmentPosition.code.asc())
    )
    cargos_todos = list(db.execute(stmt_cargos).scalars().all())
    cargos = [c for c in cargos_todos if c.status in ("VIGENTE", "INACTIVO")]
    ids_cargos = [str(c.id) for c in cargos]

    stmt_unidades = select(GovernmentUnit).where(
        GovernmentUnit.structure_id == est.id,
        GovernmentUnit.company_id == est.company_id,
    )
    unidades = list(db.execute(stmt_unidades).scalars().all())

    if not ids_cargos:
        return est, d, _filtrar(
            [], unidades, cargos_todos, unidad_id, cargo_id, accion, materia, texto
        )

    stmt_versiones = select(GovernmentPositionVersion).where(
        GovernmentPositionVersion.structure_id == est.id,
        GovernmentPositionVersion.company_id == est.company_id,
        GovernmentPositionVersion.position_id.in_(ids_cargos),
    )
    versiones = list(db.execute(stmt_versiones).scalars().all())

    stmt_docs = (
        select(Document, DocumentLink.resource_id)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            DocumentLink.resource_type == "GovernmentPosition",
            DocumentLink.resource_id.in_(ids_cargos),
            DocumentLink.company_id == est.company_id,
            Document.company_id == est.company_id,
            Document.status == "ACTIVE",
        )
    )
    docs_por_cargo: dict[str, list[str]] = {}
    for documento, cargo_id_doc in db.execute(stmt_docs).all():
        docs_por_cargo.setdefault(str(cargo_id_doc), []).append(documento.title)

    versiones_por_cargo: dict[str, list[GovernmentPositionVersion]] = {}
    for v in versiones:
        versiones_por_cargo.setdefault(str(v.position_id), []).append(v)

    unidades_out = {str(u.id): u for u in unidades}
    fin_utc = limites_del_dia_utc(d)[1]
    efectiva = autoridad_efectiva_en(db, ctx, ids_cargos, d)

    filas: list[dict[str, Any]] = []
    for cargo in cargos:
        limite_hasta = cargo.valid_to or date(ejercicio, 12, 31)
        if not (cargo.valid_from <= d <= limite_hasta):
            continue
        version = _version_en_vigor(versiones_por_cargo.get(str(cargo.id), []), fin_utc)
        if version is None:
            continue
        snapshot = version.snapshot or {}
        unidad_snapshot_id = snapshot.get("unidad_id")
        unidad_actual = unidades_out.get(str(unidad_snapshot_id)) if unidad_snapshot_id else None
        unidad_codigo: str | None
        unidad_denominacion: str | None
        ruta_unidad: str
        if unidad_actual is not None:
            unidad_codigo = unidad_actual.code
            unidad_denominacion = unidad_actual.name
            ruta_unidad = _ruta(unidades, str(unidad_actual.id))
        else:
            unidad_codigo = snapshot.get("unidad_codigo")
            unidad_denominacion = None
            ruta_unidad = unidad_codigo or ""

        titulos = sorted(docs_por_cargo.get(str(cargo.id), []))
        competencias = snapshot.get("competencias") or []
        autoridad = efectiva.get(str(cargo.id), {"ejerce": None, "delegaciones": []})
        ejerce = autoridad["ejerce"]
        fuente_cargo = _fuente_de_fila(ejerce, ver_personas) if ejerce is not None else None
        base_fila = {
            "cargo_id": str(cargo.id),
            "cargo_codigo": snapshot.get("codigo", cargo.code),
            "cargo_denominacion": snapshot.get("denominacion", cargo.name),
            "unidad_id": str(unidad_snapshot_id) if unidad_snapshot_id else str(cargo.unit_id),
            "unidad_codigo": unidad_codigo,
            "unidad_denominacion": unidad_denominacion,
            "ruta_unidad": ruta_unidad,
            "vigente_desde": cargo.valid_from,
            "vigente_hasta": cargo.valid_to,
            "estado_cargo": cargo.status,
            "acto_soporte": titulos,
            "version": {
                "version": version.version,
                "registrada_en": _utc(version.created_at),
                "motivo": version.reason,
            },
        }
        # Delegaciones: solo lo efectivamente delegado, con el límite que guardó ORG-04 (D-EA-05, D-EA-06).
        fundamentos = {(c["accion"], c["materia"]): c.get("fundamento") for c in competencias}
        for delegacion in autoridad["delegaciones"]:
            fuente_delegacion = _fuente_de_fila(delegacion, ver_personas)
            for delegada in delegacion["competencias"]:
                filas.append(
                    {
                        **base_fila,
                        "id": f"{delegacion['asignacion_id']}:{delegada['accion']}:{delegada['materia']}",
                        "accion": delegada["accion"],
                        "materia": delegada["materia"],
                        "tipo_limite": delegada.get("tipo_limite") or "",
                        "monto": delegada.get("monto"),
                        "moneda": delegada.get("moneda"),
                        "fundamento": fundamentos.get((delegada["accion"], delegada["materia"])),
                        "origen": str(delegacion["figura"]),
                        "fuente": fuente_delegacion,
                    }
                )
        for competencia in competencias:
            accion_valor = competencia["accion"]
            materia_valor = competencia["materia"]
            filas.append(
                {
                    "id": f"{str(cargo.id)}:{accion_valor}:{materia_valor}",
                    "cargo_id": str(cargo.id),
                    "cargo_codigo": snapshot.get("codigo", cargo.code),
                    "cargo_denominacion": snapshot.get("denominacion", cargo.name),
                    "unidad_id": str(unidad_snapshot_id) if unidad_snapshot_id else str(cargo.unit_id),
                    "unidad_codigo": unidad_codigo,
                    "unidad_denominacion": unidad_denominacion,
                    "ruta_unidad": ruta_unidad,
                    "accion": accion_valor,
                    "materia": materia_valor,
                    "tipo_limite": competencia.get("tipo_limite", ""),
                    "monto": competencia.get("monto"),
                    "moneda": competencia.get("moneda"),
                    "fundamento": competencia.get("fundamento"),
                    "vigente_desde": cargo.valid_from,
                    "vigente_hasta": cargo.valid_to,
                    "estado_cargo": cargo.status,
                    "acto_soporte": titulos,
                    "version": {
                        "version": version.version,
                        "registrada_en": _utc(version.created_at),
                        "motivo": version.reason,
                    },
                    "origen": _origen(ejerce),
                    "fuente": fuente_cargo,
                }
            )

    filas.sort(key=_clave_orden)
    return est, d, _filtrar(filas, unidades, cargos_todos, unidad_id, cargo_id, accion, materia, texto)


RESERVADO = "Reservado"


def _celdas_fuente(fuente: dict[str, Any] | None) -> list[str]:
    """Columnas de la fuente en el CSV, con la misma reserva de personas que la pantalla (OD-EA-01)."""
    if fuente is None:
        return ["", "", "", "", "", "", "", "", ""]
    persona = fuente["persona"]
    sustituye = fuente["sustituye_a"]
    hasta = fuente["fin_efectivo"] or fuente["hasta"]
    acto = fuente["acto"]
    cargo_origen = fuente["cargo_origen"]
    return [
        fuente["figura_etiqueta"],
        persona["codigo"] if persona else "",
        persona["nombre"] if persona else (RESERVADO if fuente["persona_reservada"] else ""),
        sustituye["nombre"] if sustituye else (RESERVADO if fuente["sustituye_reservado"] else ""),
        fuente["asignacion_codigo"],
        fuente["desde"].isoformat(),
        hasta.isoformat() if hasta else "",
        f"{acto['tipo']} {acto['numero']}" if acto else "",
        cargo_origen["codigo"] if cargo_origen else "",
    ]


def matriz(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    *,
    fecha: date | None,
    unidad_id: str | None,
    cargo_id: str | None,
    accion: str | None,
    materia: str | None,
    texto: str | None,
    pagina: int,
    por_pagina: int,
    ver_personas: bool = False,
) -> dict[str, Any]:
    """Proyecta la matriz de autoridad paginada a una fecha de corte."""
    est, d, filtradas = _filas_filtradas(
        db,
        ctx,
        ejercicio,
        fecha=fecha,
        unidad_id=unidad_id,
        cargo_id=cargo_id,
        accion=accion,
        materia=materia,
        texto=texto,
        ver_personas=ver_personas,
    )
    total = len(filtradas)
    inicio = (pagina - 1) * por_pagina
    items_pagina = filtradas[inicio : inicio + por_pagina]
    return {
        "ejercicio": ejercicio,
        "fecha": d,
        "estructura": {"estado": est.status},
        "items": items_pagina,
        "total": total,
        "cargos": len({f["cargo_id"] for f in filtradas}),
        "pagina": pagina,
        "por_pagina": por_pagina,
    }


def exportar_matriz_csv(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    *,
    fecha: date | None,
    unidad_id: str | None,
    cargo_id: str | None,
    accion: str | None,
    materia: str | None,
    texto: str | None,
    ver_personas: bool = False,
) -> tuple[str, bytes]:
    """Exporta todas las filas filtradas de la matriz a CSV y audita la exportación."""
    est, d, filas = _filas_filtradas(
        db,
        ctx,
        ejercicio,
        fecha=fecha,
        unidad_id=unidad_id,
        cargo_id=cargo_id,
        accion=accion,
        materia=materia,
        texto=texto,
        ver_personas=ver_personas,
    )

    salida = io.StringIO()
    writer = csv.writer(salida, lineterminator="\n")
    writer.writerow(
        [
            "fecha_corte",
            "codigo_unidad",
            "unidad",
            "ruta_unidad",
            "codigo_cargo",
            "denominacion_cargo",
            "estado_cargo",
            "vigente_desde",
            "vigente_hasta",
            "accion",
            "materia",
            "tipo_limite",
            "monto",
            "moneda",
            "fundamento",
            "acto_soporte",
            "version_cargo",
            "origen",
            "figura",
            "persona_codigo",
            "persona",
            "sustituye_a",
            "asignacion",
            "asignacion_desde",
            "asignacion_hasta",
            "acto",
            "cargo_origen",
        ]
    )
    for fila in filas:
        writer.writerow(
            [
                d.isoformat(),
                fila["unidad_codigo"] or "",
                fila["unidad_denominacion"] or "",
                fila["ruta_unidad"],
                fila["cargo_codigo"],
                fila["cargo_denominacion"],
                fila["estado_cargo"],
                fila["vigente_desde"].isoformat() if fila["vigente_desde"] else "",
                fila["vigente_hasta"].isoformat() if fila["vigente_hasta"] else "",
                fila["accion"],
                fila["materia"],
                fila["tipo_limite"],
                fila["monto"] or "",
                fila["moneda"] or "",
                fila["fundamento"] or "",
                " · ".join(fila["acto_soporte"]),
                str(fila["version"]["version"]),
                fila["origen"],
                *_celdas_fuente(fila.get("fuente")),
            ]
        )

    filtros_audit = {
        "fecha": fecha.isoformat() if fecha is not None else None,
        "unidad_id": unidad_id,
        "cargo_id": cargo_id,
        "accion": accion,
        "materia": materia,
        "texto": texto,
    }
    filtros_audit = {k: v for k, v in filtros_audit.items() if v is not None}
    _auditar(
        db,
        ctx,
        "GOV_AUTHORITY_MATRIX_EXPORTED",
        "GovernmentStructure",
        str(est.id),
        None,
        {
            "ejercicio": ejercicio,
            "fecha": d.isoformat(),
            "filtros": filtros_audit,
            "filas": len(filas),
        },
    )
    return f"autoridad-{ejercicio}-{d.isoformat()}.csv", salida.getvalue().encode("utf-8")


def detalle_cargo(db: Session, ctx: CompanyContext, ejercicio: int, cargo_id: str) -> dict[str, Any]:
    """Devuelve el detalle actual y el historial de versiones de un cargo."""
    est = _estructura(db, ctx, ejercicio, bloquear=False)
    stmt = select(GovernmentPosition).where(
        GovernmentPosition.id == cargo_id,
        GovernmentPosition.structure_id == est.id,
        GovernmentPosition.company_id == est.company_id,
        GovernmentPosition.status != "BORRADOR",
    )
    cargo = db.execute(stmt).scalar_one_or_none()
    if cargo is None:
        raise NotFoundError("GOV_POSITION_NOT_FOUND", "El cargo no existe en esta estructura")

    stmt_unidades = select(GovernmentUnit).where(
        GovernmentUnit.structure_id == est.id,
        GovernmentUnit.company_id == est.company_id,
    )
    unidades = list(db.execute(stmt_unidades).scalars().all())
    cargo_unit_id = str(cargo.unit_id)
    unidad = next((u for u in unidades if str(u.id) == cargo_unit_id), None)
    unidad_codigo: str | None = unidad.code if unidad else None
    unidad_denominacion: str | None = unidad.name if unidad else None
    ruta_unidad = _ruta(unidades, cargo_unit_id) if unidad else ""

    stmt_docs = (
        select(Document)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            DocumentLink.resource_type == "GovernmentPosition",
            DocumentLink.resource_id == cargo.id,
            DocumentLink.company_id == est.company_id,
            Document.company_id == est.company_id,
            Document.status == "ACTIVE",
        )
        .order_by(Document.title.asc())
    )
    documentos = list(db.execute(stmt_docs).scalars().all())

    stmt_versiones = (
        select(GovernmentPositionVersion)
        .where(
            GovernmentPositionVersion.position_id == cargo.id,
            GovernmentPositionVersion.structure_id == est.id,
            GovernmentPositionVersion.company_id == est.company_id,
        )
        .order_by(GovernmentPositionVersion.version.asc())
    )
    versiones = list(db.execute(stmt_versiones).scalars().all())

    return {
        "cargo": {
            "id": str(cargo.id),
            "codigo": cargo.code,
            "denominacion": cargo.name,
            "unidad_codigo": unidad_codigo,
            "unidad_denominacion": unidad_denominacion,
            "ruta_unidad": ruta_unidad,
            "estado": cargo.status,
            "vigente_desde": cargo.valid_from,
            "vigente_hasta": cargo.valid_to,
        },
        "acto_soporte": [{"documento_id": str(d.id), "titulo": d.title} for d in documentos],
        "versiones": [
            {
                "version": v.version,
                "estado": v.status,
                "motivo": v.reason,
                "creado_en": _utc(v.created_at),
                "competencias": (v.snapshot or {}).get("competencias", []),
            }
            for v in versiones
        ],
    }
