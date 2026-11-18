from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.documents.models import Document, DocumentLink, DocumentType
from app.modules.government.models import (
    AREAS_COMISION,
    GovernmentAct,
    GovernmentAssignment,
    GovernmentCommissionPolicy,
    GovernmentCommissionPolicyDocument,
    GovernmentCommissionPolicyRequirement,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentProcurementCommittee,
    GovernmentProcurementCommitteeConflict,
    GovernmentProcurementCommitteeMember,
    GovernmentUnit,
)
from app.modules.government.service_autoridad import competencias_en_vigor

REGLA_VERSION_LCP = "LCP-2014+RLCP-2009"
FUENTE_LCP = (
    "Decreto Ley de Contrataciones Públicas, G.O. 6.154 Ext. (2014), art. 14; "
    "Reglamento, G.O. 39.181 (2009), arts. 15, 18 y 20"
)
PISO_LCP_ART14: dict[str, Any] = {
    "codigo": "LCP_ART14",
    "version": REGLA_VERSION_LCP,
    "fuente": FUENTE_LCP,
    "exige_impar": True,
    "suplente_por_principal": True,
    "exige_secretario": True,
    "exige_suplente_secretario": True,
    "areas": list(AREAS_COMISION),
    "acto_medio": "GACETA",
}

ETIQUETAS_AREA = {
    "JURIDICA": "Jurídica",
    "TECNICA": "Técnica",
    "ECONOMICO_FINANCIERA": "Económico financiera",
}

ETIQUETAS_MAYORIA = {
    "ABSOLUTE_COUNT": "Número fijo de miembros",
    "SIMPLE_MAJORITY": "Mayoría simple",
    "QUALIFIED_MAJORITY": "Mayoría calificada",
    "UNANIMITY": "Unanimidad",
}

ETIQUETAS_ETAPA = {
    "CONSTITUCION": "constitución",
    "APERTURA": "apertura de ofertas",
    "RECOMENDACION": "recomendación",
}

REGLA_LEGADO: dict[str, Any] = {
    "origen": "LEGADO",
    "politica_id": None,
    "politica_codigo": None,
    "politica_version": None,
    "politica_nombre": None,
    "etiqueta": "Regla anterior a las políticas: mayoría simple de los principales con voto (OD-PROC07-01)",
    "base_normativa": "LCP_ART14",
    "piso": PISO_LCP_ART14,
    "fundamento": None,
    "tipo_comision": "CUALQUIERA",
    "aplica_apertura": True,
    "aplica_recomendacion": True,
    "min_principales": 1,
    "max_principales": None,
    "exige_impar": True,
    "suplente_por_principal": True,
    "exige_secretario": True,
    "exige_suplente_secretario": True,
    "exige_presidente": False,
    "quorum": {"tipo": "SIMPLE_MAJORITY", "cantidad": None, "numerador": None, "denominador": None},
    "decision": {
        "tipo": "SIMPLE_MAJORITY",
        "cantidad": None,
        "numerador": None,
        "denominador": None,
        "base": "MIEMBROS_CON_VOTO",
    },
    "presidente_vota": True,
    "presidente_dirimente": False,
    "acto_requerido": True,
    "acto_medio": "GACETA",
    "requisitos": [],
    "documentos": [],
}


def _nombre_funcionario(db: Session, company_id: str, official_id: str) -> str:
    """Devuelve el nombre del funcionario o su id si no existe."""
    official = db.scalar(
        select(GovernmentOfficial).where(
            GovernmentOfficial.id == official_id,
            GovernmentOfficial.company_id == company_id,
        )
    )
    return official.nombre if official else official_id


def _cargos_vigentes(db: Session, company_id: str, official_id: str, fecha: date) -> list[GovernmentPosition]:
    """Devuelve los cargos vigentes de un funcionario en una fecha."""
    filas = db.scalars(
        select(GovernmentPosition)
        .distinct()
        .join(GovernmentAssignment, GovernmentAssignment.position_id == GovernmentPosition.id)
        .where(
            GovernmentAssignment.company_id == company_id,
            GovernmentAssignment.official_id == official_id,
            GovernmentAssignment.status == "ACTIVO",
            GovernmentAssignment.grupo.in_(("TITULARIDAD", "TEMPORAL")),
            GovernmentAssignment.desde <= fecha,
            or_(
                GovernmentAssignment.hasta.is_(None),
                GovernmentAssignment.hasta >= fecha,
            ),
            or_(
                GovernmentAssignment.fin_efectivo.is_(None),
                GovernmentAssignment.fin_efectivo >= fecha,
            ),
            GovernmentPosition.company_id == company_id,
        )
    ).all()
    return list(filas)


def instantanea(
    db: Session,
    politica: GovernmentCommissionPolicy,
) -> dict[str, Any]:
    """Genera una instantánea JSON-serializable de la política."""
    requisitos = db.scalars(
        select(GovernmentCommissionPolicyRequirement)
        .where(
            GovernmentCommissionPolicyRequirement.policy_id == politica.id,
            GovernmentCommissionPolicyRequirement.company_id == politica.company_id,
        )
        .order_by(GovernmentCommissionPolicyRequirement.orden)
    ).all()

    documentos = db.scalars(
        select(GovernmentCommissionPolicyDocument)
        .where(
            GovernmentCommissionPolicyDocument.policy_id == politica.id,
            GovernmentCommissionPolicyDocument.company_id == politica.company_id,
        )
        .order_by(
            GovernmentCommissionPolicyDocument.etapa,
            GovernmentCommissionPolicyDocument.document_type_id,
        )
    ).all()

    requisitos_dict: list[dict[str, Any]] = []
    for requisito in requisitos:
        position_nombre: str | None = None
        if requisito.position_id:
            position = db.get(GovernmentPosition, requisito.position_id)
            if position and position.company_id == politica.company_id:
                position_nombre = position.name

        unit_nombre: str | None = None
        if requisito.unit_id:
            unit = db.get(GovernmentUnit, requisito.unit_id)
            if unit and unit.company_id == politica.company_id:
                unit_nombre = unit.name

        official_nombre: str | None = None
        if requisito.official_id:
            official = db.scalar(
                select(GovernmentOfficial).where(
                    GovernmentOfficial.id == requisito.official_id,
                    GovernmentOfficial.company_id == politica.company_id,
                )
            )
            official_nombre = official.nombre if official else None

        requisitos_dict.append(
            {
                "orden": requisito.orden,
                "etiqueta": requisito.etiqueta,
                "funcion": requisito.funcion,
                "condicion": requisito.condicion,
                "tipo": requisito.tipo,
                "area": requisito.area,
                "area_etiqueta": ETIQUETAS_AREA.get(requisito.area) if requisito.area else None,
                "position_id": requisito.position_id,
                "position_nombre": position_nombre,
                "unit_id": requisito.unit_id,
                "unit_nombre": unit_nombre,
                "competencia_accion": requisito.competencia_accion,
                "competencia_materia": requisito.competencia_materia,
                "official_id": requisito.official_id,
                "official_nombre": official_nombre,
                "minimo": requisito.minimo,
                "maximo": requisito.maximo,
            }
        )

    documentos_dict: list[dict[str, Any]] = []
    for documento in documentos:
        document_type_nombre: str | None = None
        document_type = db.get(DocumentType, documento.document_type_id)
        if document_type and document_type.company_id == politica.company_id:
            document_type_nombre = document_type.name
        documentos_dict.append(
            {
                "document_type_id": str(documento.document_type_id),
                "document_type_nombre": document_type_nombre or str(documento.document_type_id),
                "etapa": documento.etapa,
                "obligatorio": documento.obligatorio,
                "condicion": documento.condicion,
            }
        )
    documentos_dict.sort(key=lambda d: (d["etapa"], d["document_type_nombre"]))

    return {
        "origen": "POLITICA",
        "politica_id": str(politica.id),
        "politica_codigo": politica.codigo,
        "politica_version": politica.numero_version,
        "politica_nombre": politica.nombre,
        "etiqueta": f"{politica.codigo} v{politica.numero_version} · {politica.nombre}",
        "base_normativa": politica.base_normativa,
        "piso": dict(PISO_LCP_ART14) if politica.base_normativa == "LCP_ART14" else None,
        "fundamento": politica.fundamento,
        "tipo_comision": politica.tipo_comision,
        "aplica_apertura": politica.aplica_apertura,
        "aplica_recomendacion": politica.aplica_recomendacion,
        "min_principales": politica.min_principales,
        "max_principales": politica.max_principales,
        "exige_impar": politica.exige_impar,
        "suplente_por_principal": politica.suplente_por_principal,
        "exige_secretario": politica.exige_secretario,
        "exige_suplente_secretario": politica.exige_suplente_secretario,
        "exige_presidente": politica.exige_presidente,
        "quorum": {
            "tipo": politica.quorum_tipo,
            "cantidad": politica.quorum_cantidad,
            "numerador": politica.quorum_numerador,
            "denominador": politica.quorum_denominador,
        },
        "decision": {
            "tipo": politica.decision_tipo,
            "cantidad": politica.decision_cantidad,
            "numerador": politica.decision_numerador,
            "denominador": politica.decision_denominador,
            "base": politica.decision_base,
        },
        "presidente_vota": politica.presidente_vota,
        "presidente_dirimente": politica.presidente_dirimente,
        "acto_requerido": politica.acto_requerido,
        "acto_medio": politica.acto_medio,
        "requisitos": requisitos_dict,
        "documentos": documentos_dict,
    }


def regla_de(
    db: Session,
    comision: GovernmentProcurementCommittee,
) -> dict[str, Any]:
    """Obtiene la regla aplicable a una comisión."""
    if comision.regla is not None:
        return comision.regla

    if comision.policy_id is not None:
        politica = db.scalar(
            select(GovernmentCommissionPolicy).where(
                GovernmentCommissionPolicy.id == comision.policy_id,
                GovernmentCommissionPolicy.company_id == comision.company_id,
            )
        )
        if politica:
            return instantanea(db, politica)

    return dict(REGLA_LEGADO)


def umbral(
    tipo: str,
    cantidad: int | None,
    numerador: int | None,
    denominador: int | None,
    base: int,
) -> int:
    """Calcula el umbral de votos exigido según el tipo de mayoría."""
    resultado: int
    if tipo == "ABSOLUTE_COUNT":
        if cantidad is None:
            raise ValueError("ABSOLUTE_COUNT requiere cantidad")
        resultado = cantidad
    elif tipo == "SIMPLE_MAJORITY":
        resultado = base // 2 + 1
    elif tipo == "QUALIFIED_MAJORITY":
        if numerador is None or denominador is None or denominador == 0:
            raise ValueError("QUALIFIED_MAJORITY requiere numerador y denominador válidos")
        resultado = -(-base * numerador // denominador)
    elif tipo == "UNANIMITY":
        resultado = base
    else:
        raise ValueError(f"Tipo de mayoría desconocido: {tipo}")

    return max(1, resultado)


def cumple_requisito(
    db: Session,
    company_id: str,
    requisito: dict[str, Any],
    miembro: GovernmentProcurementCommitteeMember,
    fecha: date,
) -> bool:
    """Verifica si un miembro cumple un requisito paramétrico."""
    if miembro.funcion != requisito["funcion"]:
        return False
    if requisito["condicion"] != "CUALQUIERA" and miembro.condicion != requisito["condicion"]:
        return False

    tipo = requisito["tipo"]
    if tipo == "AREA":
        return miembro.area == requisito["area"]

    if tipo == "FUNCIONARIO":
        return miembro.official_id == requisito["official_id"]

    cargos = _cargos_vigentes(db, company_id, miembro.official_id, fecha)

    if tipo == "CARGO":
        return any(cargo.id == requisito["position_id"] for cargo in cargos)

    if tipo == "UNIDAD":
        return any(cargo.unit_id == requisito["unit_id"] for cargo in cargos)

    if tipo == "COMPETENCIA":
        accion = requisito["competencia_accion"]
        materia = requisito["competencia_materia"]
        for cargo in cargos:
            for competencia in competencias_en_vigor(db, cargo, fecha):
                if competencia["accion"] == accion and competencia["materia"] == materia:
                    return True
        return False

    return False


def documentos_faltantes(
    db: Session,
    company_id: str,
    regla: dict[str, Any],
    etapa: str,
    resource_type: str,
    resource_id: str,
) -> list[str]:
    """Devuelve los documentos obligatorios que faltan en una etapa."""
    faltan: list[str] = []
    for documento in regla["documentos"]:
        if documento["etapa"] != etapa or not documento["obligatorio"]:
            continue

        link = db.scalar(
            select(DocumentLink).where(
                DocumentLink.company_id == company_id,
                DocumentLink.resource_type == resource_type,
                DocumentLink.resource_id == str(resource_id),
                DocumentLink.document_id == Document.id,
                Document.company_id == company_id,
                Document.status == "ACTIVE",
                Document.document_type_id == documento["document_type_id"],
            )
        )

        if link is None:
            faltan.append(
                f"Falta el documento «{documento['document_type_nombre']}» de la etapa de {ETIQUETAS_ETAPA[etapa]}"
            )

    return faltan


def faltantes(
    db: Session,
    company_id: str,
    regla: dict[str, Any],
    comision: GovernmentProcurementCommittee,
    miembros: Sequence[GovernmentProcurementCommitteeMember],
    fecha: date,
) -> list[str]:
    """Devuelve la lista de impedimentos para formalizar una comisión."""
    activos = [m for m in miembros if m.fin_efectivo is None]
    principales = [
        m for m in activos if m.funcion == "MIEMBRO" and m.condicion == "PRINCIPAL"
    ]
    piso = regla.get("piso")
    codigo_politica: str | None = regla.get("politica_codigo")
    ref = " (LCP art. 14)" if piso else f" (política {codigo_politica})"
    sufijo_codigo = f" (política {codigo_politica})" if codigo_politica else ""
    resultado: list[str] = []

    def exigencia(clave: str) -> bool:
        return bool(regla.get(clave)) or bool(piso and piso.get(clave))

    if exigencia("acto_requerido"):
        acto: GovernmentAct | None = None
        if comision.act_id:
            acto = db.scalar(
                select(GovernmentAct).where(
                    GovernmentAct.id == comision.act_id,
                    GovernmentAct.company_id == company_id,
                )
            )
        if not comision.act_id:
            resultado.append("Falta el acto que crea la comisión")
        elif (
            acto is None
            or acto.status != "EFICAZ"
            or acto.fecha_eficacia is None
            or acto.fecha_eficacia > comision.desde
        ):
            resultado.append("El acto debe estar eficaz al inicio de la vigencia")
        elif acto is not None:
            medio_exigido = (piso["acto_medio"] if piso else None) or regla.get("acto_medio")
            if medio_exigido and acto.medio != medio_exigido:
                if piso:
                    resultado.append("El acto debe estar publicado en gaceta (RLCP art. 15)")
                else:
                    resultado.append(
                        f"El acto debe estar publicado por el medio {str(medio_exigido).lower()} "
                        f"(política {codigo_politica})"
                    )

    if comision.tipo == "TEMPORAL" and comision.hasta is None:
        resultado.append("Una comisión temporal necesita fecha final")

    min_principales = regla["min_principales"]
    if len(principales) < min_principales:
        resultado.append(
            f"Se requieren al menos {min_principales} miembros principales; hay {len(principales)}"
            f"{sufijo_codigo}"
        )

    max_principales = regla.get("max_principales")
    if max_principales is not None and len(principales) > max_principales:
        resultado.append(
            f"Se admiten como máximo {max_principales} miembros principales; hay {len(principales)}"
            f" (política {codigo_politica})"
        )

    if exigencia("exige_impar") and len(principales) % 2 == 0:
        resultado.append(f"El número de miembros principales debe ser impar{ref}")

    if piso:
        for area in piso["areas"]:
            if not any(p.area == area for p in principales):
                resultado.append(f"Falta un principal del área {ETIQUETAS_AREA[area]} (LCP art. 14)")

    if exigencia("suplente_por_principal"):
        suplentes_activos = [
            m for m in activos if m.funcion == "MIEMBRO" and m.condicion == "SUPLENTE"
        ]
        for principal in principales:
            tiene_suplente = any(
                s.suplente_de_id == principal.id for s in suplentes_activos
            )
            if not tiene_suplente:
                nombre = _nombre_funcionario(db, company_id, principal.official_id)
                resultado.append(f"{nombre} no tiene suplente{ref}")

    if exigencia("exige_secretario") and not any(
        m.funcion == "SECRETARIO" and m.condicion == "PRINCIPAL" for m in activos
    ):
        resultado.append(f"Falta el secretario{ref}")

    if exigencia("exige_suplente_secretario") and not any(
        m.funcion == "SECRETARIO" and m.condicion == "SUPLENTE" for m in activos
    ):
        resultado.append(f"Falta el suplente del secretario{ref}")

    if exigencia("exige_presidente") and not any(
        m.preside for m in principales
    ):
        resultado.append(f"Falta designar al presidente (política {codigo_politica})")

    for requisito in regla["requisitos"]:
        cumplen = sum(
            1
            for m in activos
            if cumple_requisito(db, company_id, requisito, m, fecha)
        )
        if cumplen < requisito["minimo"]:
            resultado.append(
                f"{requisito['etiqueta']}: se requieren al menos {requisito['minimo']}; "
                f"cumplen {cumplen}"
            )
        if requisito["maximo"] is not None and cumplen > requisito["maximo"]:
            resultado.append(
                f"{requisito['etiqueta']}: se admiten como máximo {requisito['maximo']}; "
                f"cumplen {cumplen}"
            )

    for miembro in activos:
        official = db.scalar(
            select(GovernmentOfficial).where(
                GovernmentOfficial.id == miembro.official_id,
                GovernmentOfficial.company_id == company_id,
            )
        )
        if official is None or official.estado != "ACTIVO":
            nombre = _nombre_funcionario(db, company_id, miembro.official_id)
            resultado.append(f"{nombre} no está activo")

    resultado.extend(
        documentos_faltantes(
            db,
            company_id,
            regla,
            "CONSTITUCION",
            "GovernmentProcurementCommittee",
            str(comision.id),
        )
    )

    return resultado


def inhibidos(
    db: Session,
    company_id: str,
    committee_id: str,
    file_id: str,
) -> set[str]:
    """Devuelve los ids de miembros inhibidos en un expediente."""
    filas = db.scalars(
        select(GovernmentProcurementCommitteeConflict.member_id).where(
            GovernmentProcurementCommitteeConflict.company_id == company_id,
            GovernmentProcurementCommitteeConflict.committee_id == committee_id,
            GovernmentProcurementCommitteeConflict.file_id == file_id,
            GovernmentProcurementCommitteeConflict.estado == "ACEPTADA",
        )
    ).all()
    return {str(member_id) for member_id in filas}


def _suplente_presente(
    principal: GovernmentProcurementCommitteeMember,
    activos: Sequence[GovernmentProcurementCommitteeMember],
    presentes: set[str],
    inhibidos: set[str],
) -> GovernmentProcurementCommitteeMember | None:
    """Devuelve el suplente activo de un principal si está presente y no inhibido."""
    for suplente in activos:
        if (
            suplente.funcion == "MIEMBRO"
            and suplente.condicion == "SUPLENTE"
            and suplente.suplente_de_id == principal.id
            and str(suplente.id) in presentes
            and str(suplente.id) not in inhibidos
        ):
            return suplente
    return None


def evaluar_quorum(
    regla: dict[str, Any],
    miembros: Sequence[GovernmentProcurementCommitteeMember],
    presentes: Iterable[str],
    inhibidos: Iterable[str] = (),
) -> dict[str, Any]:
    """Evalúa el quórum de una sesión."""
    set_presentes = {str(p) for p in presentes}
    set_inhibidos = {str(i) for i in inhibidos}
    activos = [m for m in miembros if m.fin_efectivo is None]

    votantes: list[GovernmentProcurementCommitteeMember] = []
    for miembro in activos:
        if miembro.funcion == "MIEMBRO" and miembro.condicion == "PRINCIPAL":
            if miembro.preside and not regla["presidente_vota"]:
                continue
            votantes.append(miembro)

    asistentes_con_voto = 0
    votantes_presentes: list[str] = []
    for principal in votantes:
        presente_directa = (
            str(principal.id) in set_presentes
            and str(principal.id) not in set_inhibidos
        )
        suplente = _suplente_presente(principal, activos, set_presentes, set_inhibidos)

        if presente_directa or suplente is not None:
            asistentes_con_voto += 1
            votantes_presentes.append(str(principal.id))

    quorum = regla["quorum"]
    quorum_requerido = umbral(
        quorum["tipo"],
        quorum["cantidad"],
        quorum["numerador"],
        quorum["denominador"],
        len(votantes),
    )

    return {
        "miembros_con_voto": len(votantes),
        "asistentes_con_voto": asistentes_con_voto,
        "quorum_requerido": quorum_requerido,
        "hay_quorum": asistentes_con_voto >= quorum_requerido,
        "tipo": quorum["tipo"],
        "tipo_etiqueta": ETIQUETAS_MAYORIA[quorum["tipo"]],
        "regla": regla["etiqueta"],
        "votantes_presentes": votantes_presentes,
    }


def evaluar_decision(
    regla: dict[str, Any],
    miembros: Sequence[GovernmentProcurementCommitteeMember],
    presentes: Iterable[str],
    a_favor: Iterable[str],
    inhibidos: Iterable[str] = (),
) -> dict[str, Any]:
    """Evalúa si una decisión alcanza la mayoría requerida."""
    quorum = evaluar_quorum(regla, miembros, presentes, inhibidos)
    set_presentes = {str(p) for p in presentes}
    set_a_favor = {str(a) for a in a_favor}
    set_inhibidos = {str(i) for i in inhibidos}
    activos = [m for m in miembros if m.fin_efectivo is None]

    votantes_map: dict[str, GovernmentProcurementCommitteeMember] = {}
    for miembro in activos:
        if miembro.funcion == "MIEMBRO" and miembro.condicion == "PRINCIPAL":
            if miembro.preside and not regla["presidente_vota"]:
                continue
            votantes_map[str(miembro.id)] = miembro

    votos_a_favor = 0
    for id_votante in quorum["votantes_presentes"]:
        principal = votantes_map[id_votante]
        voto_directo = (
            str(principal.id) in set_a_favor
            and str(principal.id) not in set_inhibidos
        )
        suplente = _suplente_presente(
            principal, activos, set_presentes, set_inhibidos
        )
        voto_suplente = (
            suplente is not None
            and str(suplente.id) in set_a_favor
            and str(suplente.id) in set_presentes
            and str(suplente.id) not in set_inhibidos
        )
        if voto_directo or voto_suplente:
            votos_a_favor += 1

    decision = regla["decision"]
    base = (
        quorum["miembros_con_voto"]
        if decision["base"] == "MIEMBROS_CON_VOTO"
        else quorum["asistentes_con_voto"]
    )
    requerido = umbral(
        decision["tipo"],
        decision["cantidad"],
        decision["numerador"],
        decision["denominador"],
        base,
    )

    aprobada = quorum["hay_quorum"] and votos_a_favor >= requerido
    dirimente_usado = False

    if (
        not aprobada
        and quorum["hay_quorum"]
        and regla["presidente_dirimente"]
        and 2 * votos_a_favor == base
    ):
        presidente = next(
            (m for m in activos if m.preside),
            None,
        )
        if presidente is not None and str(presidente.id) in set_a_favor:
            aprobada = True
            dirimente_usado = True

    return {
        "quorum": quorum,
        "votos_a_favor": votos_a_favor,
        "base": base,
        "requerido": requerido,
        "aprobada": aprobada,
        "dirimente_usado": dirimente_usado,
        "tipo": decision["tipo"],
        "tipo_etiqueta": ETIQUETAS_MAYORIA[decision["tipo"]],
        "regla": regla["etiqueta"],
    }


def cuenta_voto(
    m: GovernmentProcurementCommitteeMember,
    *,
    presentes: set[str],
    inh: set[str],
    votantes_presentes: Iterable[str],
    presidente_vota: bool,
) -> bool:
    """Si el asistente o firmante cuenta voto: el principal presente y no inhibido; el suplente solo si su principal no cuenta por sí mismo."""
    if m.funcion != "MIEMBRO":
        return False
    if m.condicion == "PRINCIPAL":
        return m.id in presentes and m.id not in inh and (presidente_vota or not m.preside)
    principal = m.suplente_de_id
    if principal is None or principal not in set(votantes_presentes):
        return False
    return principal not in presentes or principal in inh
