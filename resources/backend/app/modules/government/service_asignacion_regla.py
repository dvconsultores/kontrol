"""Autoridad única de la regla de asignación de ORG-04 (ORG-04-AUTHORITY-ASSIGNMENT-POLICY).

La regla aplicada a una asignación tiene dos fuentes:

* los **pisos legales** (LEGAL_MANDATORY), versionados con su fuente y su aplicabilidad por nivel territorial
  del ente (OD-AP-02): LOAP y LEFP rigen en todo nivel; la LOPPM art. 87, solo en el municipal;
* la **política** del ente para la figura (INSTITUTIONAL_POLICY), si hay una VIGENTE cuya vigencia cubra la fecha
  de inicio. La política solo endurece: los pisos se aplican siempre (D-AP-03).

Sin política vigente rigen solo los pisos (OD-AP-01). Una asignación activada antes de las políticas conserva su
regla histórica (OD-AP-03), que es la de los pisos.

El backend valida con `verificar`; la UI pide la misma regla por la API: no hay una segunda autoridad.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError
from app.modules.documents.models import Document, DocumentLink, DocumentType
from app.modules.government.models import (
    GovernmentAct,
    GovernmentAssignment,
    GovernmentAssignmentPolicy,
    GovernmentAssignmentPolicyCompetency,
    GovernmentAssignmentPolicyDocument,
    GovernmentEntity,
    GovernmentPosition,
)
from app.modules.government.service_autoridad import competencias_en_vigor

RESOURCE_ASIGNACION = "GovernmentAssignment"

#: Taxonomía de plataforma (D-AP-01): no es regla institucional.
FIGURAS_DELEGACION = ("DELEGACION_ATRIBUCIONES", "DELEGACION_FIRMA")
FIGURAS_CON_FIN = ("SUPLENCIA", "COMISION_SERVICIO")
FIGURAS_OTRO_EMISOR = ("TITULAR", "ENCARGADURIA", "COMISION_SERVICIO")

ETIQUETAS_ORIGEN = {
    "POLITICA": "Política institucional",
    "PISO_LEGAL": "Regla legal base, sin política institucional",
    "HISTORICA": "Regla histórica (anterior a las políticas)",
}
ETIQUETAS_ETAPA = {"ACTIVACION": "activación", "REVOCACION": "revocación"}
ETIQUETAS_MEDIO = {"GACETA": "gaceta", "PERSONAL": "notificación personal", "PRENSA": "prensa"}

#: Pisos legales verificados en las copias normativas del repositorio (delta §2 de la Spec ORG-04).
PISOS: tuple[dict[str, Any], ...] = (
    {
        "codigo": "LOAP_DELEGACION",
        "fuente": "LOAP (G.O. 6.147 Ext., 17-11-2014), arts. 2, 34, 35, 40 y 41",
        "version": "LOAP-2014",
        "vigente_desde": date(2014, 11, 17),
        "niveles": None,
        "figuras": FIGURAS_DELEGACION,
        "exigencias": {
            "acto_medio": {"medio": "GACETA", "mensaje": "La delegación debe estar publicada en gaceta (LOAP art. 40)"},
            "emisor": "DELEGANTE",
            "admite_avocacion": True,
        },
    },
    {
        "codigo": "LEFP_COMISION",
        "fuente": "LEFP (G.O. 37.522, 06-09-2002), arts. 1, 71 y 72",
        "version": "LEFP-2002",
        "vigente_desde": date(2002, 9, 6),
        "niveles": None,
        "figuras": ("COMISION_SERVICIO",),
        "exigencias": {
            "limite": {
                "valor": 1,
                "unidad": "ANIOS",
                "ambito": "TODAS",
                "mensaje": "La comisión de servicio no puede exceder un año (LEFP art. 72)",
            },
        },
    },
    {
        "codigo": "LOPPM_ART87",
        "fuente": "LOPPM (G.O. 6.015 Ext., 28-12-2010), arts. 87 y 95.18",
        "version": "LOPPM-2010",
        "vigente_desde": date(2010, 12, 28),
        "niveles": ("MUNICIPAL",),
        "figuras": ("SUPLENCIA",),
        "exigencias": {
            "autorizacion": {
                "etiqueta": "Autorización del Concejo Municipal",
                "ambito": "MAXIMA_AUTORIDAD",
                "mas_de_dias": 15,
                "fuente": "LOPPM art. 87",
            },
            "limite": {
                "valor": 90,
                "unidad": "DIAS",
                "ambito": "MAXIMA_AUTORIDAD",
                "mensaje": "Más de 90 días: el Concejo Municipal debe evaluar la ausencia (LOPPM art. 87)",
            },
        },
    },
)


def _invalida(codigo: str, mensaje: str) -> KontrolError:
    return KontrolError(code=codigo, message=mensaje, status_code=422)


def nivel_del_ente(db: Session, ctx: CompanyContext) -> str | None:
    """Nivel territorial del ente de la empresa (NACIONAL, ESTADAL, MUNICIPAL o sin declarar)."""
    return db.scalar(
        select(GovernmentEntity.nivel_territorial).where(GovernmentEntity.company_id == ctx.company_id)
    )


def pisos_aplicables(nivel: str | None, figura: str, fecha: date) -> list[dict[str, Any]]:
    """Pisos legales que rigen para la figura, el nivel del ente y la fecha."""
    return [
        piso
        for piso in PISOS
        if figura in piso["figuras"]
        and (piso["niveles"] is None or nivel in piso["niveles"])
        and piso["vigente_desde"] <= fecha
    ]


def regla_base(nivel: str | None, figura: str, fecha: date, origen: str = "PISO_LEGAL") -> dict[str, Any]:
    """Regla con solo los pisos legales y las invariantes de la figura."""
    pisos = pisos_aplicables(nivel, figura, fecha)
    if figura in FIGURAS_DELEGACION:
        emisor_regla = "DELEGANTE"
    elif figura in FIGURAS_OTRO_EMISOR:
        emisor_regla = "OTRO_CARGO"
    else:
        emisor_regla = "CUALQUIERA"

    limites: list[dict[str, Any]] = []
    autorizaciones: list[dict[str, Any]] = []
    acto_medio: dict[str, Any] | None = None
    admite_avocacion = False
    for piso in pisos:
        exigencias = piso["exigencias"]
        if "limite" in exigencias:
            limites.append({**exigencias["limite"], "fuente": piso["codigo"]})
        if "autorizacion" in exigencias:
            autorizaciones.append(dict(exigencias["autorizacion"]))
        if "acto_medio" in exigencias:
            acto_medio = dict(exigencias["acto_medio"])
        if exigencias.get("admite_avocacion"):
            admite_avocacion = True

    return {
        "origen": origen,
        "origen_etiqueta": ETIQUETAS_ORIGEN[origen],
        "politica": None,
        "regla_version": "Pisos legales",
        "figura": figura,
        "nivel_territorial": nivel,
        "pisos": [{"codigo": p["codigo"], "fuente": p["fuente"], "version": p["version"]} for p in pisos],
        "fundamentos": [p["fuente"] for p in pisos],
        "exige_fin": figura in FIGURAS_CON_FIN,
        "limites": limites,
        "acto_medio": acto_medio,
        "emisor": {"regla": emisor_regla, "tipo": "CUALQUIERA", "position_id": None, "accion": None, "materia": None},
        "autorizaciones": autorizaciones,
        "competencias_permitidas": None,
        "admite_avocacion": admite_avocacion,
        "documentos": [],
    }


def instantanea(
    db: Session, ctx: CompanyContext, politica: GovernmentAssignmentPolicy, nivel: str | None, fecha: date
) -> dict[str, Any]:
    """Pisos más la política, fusionados de modo que la política solo endurece (D-AP-03)."""
    regla = regla_base(nivel, politica.figura, fecha, origen="POLITICA")
    etiqueta = f"{politica.codigo} v{politica.numero_version}"
    regla["politica"] = {
        "id": str(politica.id),
        "codigo": politica.codigo,
        "numero_version": politica.numero_version,
        "nombre": politica.nombre,
    }
    regla["regla_version"] = etiqueta
    if politica.fundamento:
        regla["fundamentos"].append(politica.fundamento)

    regla["exige_fin"] = regla["exige_fin"] or politica.exige_fin or politica.max_dias is not None
    if politica.max_dias is not None:
        regla["limites"].append(
            {
                "valor": politica.max_dias,
                "unidad": "DIAS",
                "ambito": "TODAS",
                "mensaje": f"La política {etiqueta} admite como máximo {politica.max_dias} días",
                "fuente": etiqueta,
            }
        )
    if regla["acto_medio"] is None and politica.acto_medio:
        regla["acto_medio"] = {
            "medio": politica.acto_medio,
            "mensaje": f"El acto debe darse a conocer por {ETIQUETAS_MEDIO.get(politica.acto_medio, politica.acto_medio)} (política {etiqueta})",
        }
    if politica.emisor_tipo != "CUALQUIERA":
        regla["emisor"].update(
            {
                "tipo": politica.emisor_tipo,
                "position_id": politica.emisor_position_id,
                "accion": politica.emisor_competencia_accion,
                "materia": politica.emisor_competencia_materia,
            }
        )
    if politica.autorizacion_requerida:
        regla["autorizaciones"].append(
            {
                "etiqueta": politica.autorizacion_etiqueta,
                "ambito": politica.autorizacion_ambito,
                "mas_de_dias": politica.autorizacion_mas_de_dias or 0,
                "fuente": f"política {etiqueta}",
            }
        )

    permitidas = db.scalars(
        select(GovernmentAssignmentPolicyCompetency)
        .where(
            GovernmentAssignmentPolicyCompetency.policy_id == str(politica.id),
            GovernmentAssignmentPolicyCompetency.company_id == ctx.company_id,
        )
        .order_by(GovernmentAssignmentPolicyCompetency.accion, GovernmentAssignmentPolicyCompetency.materia)
    ).all()
    if permitidas:
        regla["competencias_permitidas"] = [{"accion": c.accion, "materia": c.materia} for c in permitidas]

    regla["admite_avocacion"] = regla["admite_avocacion"] and not politica.prohibe_avocacion

    documentos = db.execute(
        select(GovernmentAssignmentPolicyDocument, DocumentType.name)
        .join(DocumentType, DocumentType.id == GovernmentAssignmentPolicyDocument.document_type_id)
        .where(
            GovernmentAssignmentPolicyDocument.policy_id == str(politica.id),
            GovernmentAssignmentPolicyDocument.company_id == ctx.company_id,
            DocumentType.company_id == ctx.company_id,
        )
        .order_by(GovernmentAssignmentPolicyDocument.etapa, DocumentType.name)
    ).all()
    regla["documentos"] = [
        {
            "document_type_id": str(doc.document_type_id),
            "document_type_nombre": nombre,
            "etapa": doc.etapa,
            "obligatorio": doc.obligatorio,
        }
        for doc, nombre in documentos
    ]
    return regla


def politica_aplicable(
    db: Session, ctx: CompanyContext, figura: str, fecha: date
) -> GovernmentAssignmentPolicy | None:
    """La política VIGENTE de la figura cuya vigencia cubre la fecha (a lo sumo una, D-AP-02)."""
    return db.scalar(
        select(GovernmentAssignmentPolicy)
        .where(
            GovernmentAssignmentPolicy.company_id == ctx.company_id,
            GovernmentAssignmentPolicy.figura == figura,
            GovernmentAssignmentPolicy.estado == "VIGENTE",
            GovernmentAssignmentPolicy.vigente_desde <= fecha,
            or_(
                GovernmentAssignmentPolicy.vigente_hasta.is_(None),
                GovernmentAssignmentPolicy.vigente_hasta >= fecha,
            ),
        )
        .order_by(GovernmentAssignmentPolicy.vigente_desde.desc())
        .limit(1)
    )


def regla_aplicable(
    db: Session, ctx: CompanyContext, figura: str, fecha: date
) -> tuple[dict[str, Any], GovernmentAssignmentPolicy | None]:
    """Regla que aplicaría hoy a una asignación de la figura que empieza en `fecha`, y su política."""
    nivel = nivel_del_ente(db, ctx)
    politica = politica_aplicable(db, ctx, figura, fecha)
    if politica is None:
        return regla_base(nivel, figura, fecha), None
    return instantanea(db, ctx, politica, nivel, fecha), politica


def regla_de(db: Session, ctx: CompanyContext, asignacion: GovernmentAssignment) -> dict[str, Any]:
    """La regla congelada de la asignación o, si es de legado, su regla histórica (OD-AP-03)."""
    if asignacion.regla:
        return dict(asignacion.regla)
    return regla_base(nivel_del_ente(db, ctx), asignacion.figura, asignacion.desde, origen="HISTORICA")


def _aplica(ambito: str, maxima_autoridad: bool) -> bool:
    return ambito == "TODAS" or (ambito == "MAXIMA_AUTORIDAD" and maxima_autoridad)


def _excede(limite: dict[str, Any], desde: date, hasta: date) -> bool:
    if limite["unidad"] == "ANIOS":
        try:
            tope = desde.replace(year=desde.year + limite["valor"])
        except ValueError:
            tope = desde.replace(year=desde.year + limite["valor"], day=28)
        return hasta > tope
    return (hasta - desde).days + 1 > limite["valor"]


def autorizaciones_exigidas(regla: dict[str, Any], desde: date, hasta: date | None, maxima_autoridad: bool) -> list[dict[str, Any]]:
    """Autorizaciones especiales que la regla exige a esa vigencia (también la consulta la UI por la API)."""
    exigidas = []
    for autorizacion in regla.get("autorizaciones") or []:
        if not _aplica(autorizacion["ambito"], maxima_autoridad):
            continue
        if hasta is None or (hasta - desde).days + 1 > autorizacion["mas_de_dias"]:
            exigidas.append(autorizacion)
    return exigidas


def verificar_vigencia(regla: dict[str, Any], datos: Any) -> None:
    """Fin obligatorio, límites de duración y autorización especial."""
    maxima = bool(getattr(datos, "maxima_autoridad", False))
    if regla["exige_fin"] and datos.hasta is None:
        raise _invalida("GOV_ASSIGNMENT_INVALID", f"La regla aplicada ({regla['regla_version']}) exige fecha de fin")
    if datos.hasta is not None:
        for limite in regla.get("limites") or []:
            if _aplica(limite["ambito"], maxima) and _excede(limite, datos.desde, datos.hasta):
                raise _invalida("GOV_ASSIGNMENT_LIMIT_EXCEEDED", limite["mensaje"])
    if not getattr(datos, "autorizacion_especial", None):
        for autorizacion in autorizaciones_exigidas(regla, datos.desde, datos.hasta, maxima):
            if autorizacion["mas_de_dias"]:
                mensaje = f"Más de {autorizacion['mas_de_dias']} días exige {autorizacion['etiqueta']} ({autorizacion['fuente']})"
            else:
                mensaje = f"Exige {autorizacion['etiqueta']} ({autorizacion['fuente']})"
            raise _invalida("GOV_ASSIGNMENT_LIMIT_EXCEEDED", mensaje)


def verificar_acto(db: Session, regla: dict[str, Any], acto: GovernmentAct, cargo: GovernmentPosition) -> None:
    """Medio de publicación y autoridad emisora del acto."""
    medio = regla.get("acto_medio")
    if medio and acto.medio != medio["medio"]:
        raise _invalida("GOV_ASSIGNMENT_ACT_INVALID", medio["mensaje"])
    verificar_emisor(db, regla, acto, cargo)


def verificar_emisor(db: Session, regla: dict[str, Any], acto: GovernmentAct, cargo: GovernmentPosition) -> None:
    """Autoridad emisora del acto: la figura (plataforma y LOAP) y la política (cargo o competencia, ORG-03)."""
    emisor = regla["emisor"]
    if emisor["regla"] == "DELEGANTE" and acto.cargo_id != cargo.id:
        raise _invalida("GOV_ASSIGNMENT_ISSUER_INVALID", "La delegación la confiere el cargo delegante (LOAP art. 34)")
    if emisor["regla"] == "OTRO_CARGO" and acto.cargo_id == cargo.id:
        raise _invalida("GOV_ASSIGNMENT_ISSUER_INVALID", "El cargo no puede designarse a sí mismo")

    if emisor["tipo"] == "CARGO" and acto.cargo_id != emisor["position_id"]:
        raise _invalida(
            "GOV_ASSIGNMENT_ISSUER_INVALID",
            f"El acto debe emitirlo el cargo que fija la política ({regla['regla_version']})",
        )
    if emisor["tipo"] == "COMPETENCIA":
        cargo_emisor = db.scalar(
            select(GovernmentPosition).where(
                GovernmentPosition.id == acto.cargo_id,
                GovernmentPosition.company_id == acto.company_id,
            )
        )
        tiene = cargo_emisor is not None and any(
            c.get("accion") == emisor["accion"] and c.get("materia") == emisor["materia"]
            for c in competencias_en_vigor(db, cargo_emisor, acto.fecha)
        )
        if not tiene:
            raise _invalida(
                "GOV_ASSIGNMENT_ISSUER_INVALID",
                f"El cargo emisor del acto no tiene la competencia {emisor['accion']} sobre {emisor['materia']} "
                f"que exige la política ({regla['regla_version']})",
            )


def verificar_competencias(regla: dict[str, Any], competencias: list[Any]) -> None:
    """Solo se transfieren las competencias que la política permite (ORG-03 sigue resolviendo las del cargo)."""
    permitidas = regla.get("competencias_permitidas")
    if permitidas is None:
        return
    pares = {(c["accion"], c["materia"]) for c in permitidas}
    for c in competencias:
        if (c.accion, c.materia) not in pares:
            raise _invalida(
                "GOV_ASSIGNMENT_NOT_DELEGABLE",
                f"La política ({regla['regla_version']}) no permite transferir {c.accion} sobre {c.materia}",
            )


def verificar(
    db: Session, regla: dict[str, Any], datos: Any, acto: GovernmentAct, cargo: GovernmentPosition
) -> None:
    """Todo lo que la regla exige a una asignación al crearla, editarla o activarla."""
    verificar_acto(db, regla, acto, cargo)
    verificar_vigencia(regla, datos)
    verificar_competencias(regla, list(getattr(datos, "competencias", None) or []))


def documentos_faltantes(
    db: Session, company_id: str, regla: dict[str, Any], etapa: str, asignacion_id: str
) -> list[str]:
    """Documentos obligatorios de la etapa que no están adjuntos a la asignación."""
    faltan: list[str] = []
    for documento in regla.get("documentos") or []:
        if documento["etapa"] != etapa or not documento["obligatorio"]:
            continue
        adjunto = db.scalar(
            select(DocumentLink.id).where(
                DocumentLink.company_id == company_id,
                DocumentLink.resource_type == RESOURCE_ASIGNACION,
                DocumentLink.resource_id == str(asignacion_id),
                DocumentLink.document_id == Document.id,
                Document.company_id == company_id,
                Document.status == "ACTIVE",
                Document.document_type_id == documento["document_type_id"],
            )
        )
        if adjunto is None:
            faltan.append(
                f"Falta el documento «{documento['document_type_nombre']}» de la etapa de {ETIQUETAS_ETAPA[etapa]}"
            )
    return faltan
