"""Autoridad única de la regla de un acta de entrega (CTL-09-DELIVERY-ACT-POLICY).

La regla aplicada a un acta = el catálogo legal versionado de N34 (LEGAL_MANDATORY) + la política vigente del ente
(INSTITUTIONAL_POLICY). El catálogo no se copia a la política, así que la política solo puede añadir: vínculos a los
supuestos de los arts. 12-17, requisitos, testigos en la entrega y plazos internos (D-AE-02).

Fuente verificada: Resolución CGR Nº 01-00-000162, G.O. 39.229 (28-07-2009); copia oficial en
`requerimientos/gobierno/normativa-n34/`. El sujeto de los arts. 12-17 no se infiere de los datos del ente: lo declara
el ente en su política (OD-AE-01).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError
from app.modules.documents.models import Document, DocumentType
from app.modules.government.models import (
    GovernmentAssignment,
    GovernmentEntity,
    GovernmentHandoverAct,
    GovernmentHandoverAnnex,
    GovernmentHandoverPolicy,
    GovernmentHandoverPolicyBinding,
    GovernmentHandoverPolicyDeadline,
    GovernmentHandoverPolicyRequirement,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentUnit,
)

NORMA_N34: dict[str, Any] = {
    "codigo": "N34",
    "version": "N34-2009",
    "titulo": (
        "Normas para Regular la Entrega de los Órganos y Entidades de la Administración Pública "
        "y de sus Respectivas Oficinas o Dependencias"
    ),
    "instrumento": "Resolución CGR Nº 01-00-000162",
    "gaceta": "G.O. 39.229 (28-07-2009)",
    "vigente_desde": date(2009, 7, 28),
    "vigente_hasta": None,
}


def _fuente(articulo: str) -> str:
    return f"N34 art. {articulo} ({NORMA_N34['gaceta']})"


def _anexo(codigo: str, titulo: str, articulo: str, *, obligatorio: bool = True, generable: bool = False) -> dict[str, Any]:
    return {
        "codigo": codigo,
        "titulo": titulo,
        "obligatorio": obligatorio,
        "generable": generable,
        "evidencia": "DOCUMENTO",
        "fuente": _fuente(articulo),
    }


# Catálogo legal (D-AE-01). `vinculo`: UNIVERSAL rige en toda acta (art. 5); DECLARADO solo donde el ente lo vincula.
# `niveles`: niveles territoriales en que se puede declarar (None = todos). `ambitos`: entidad o dependencia.
SUPUESTOS: list[dict[str, Any]] = [
    {
        "codigo": "N34_ART11",
        "articulo": "11",
        "titulo": "Anexos de toda acta de entrega",
        "sujeto": "Todo órgano, entidad, oficina o dependencia (arts. 5 y 11)",
        "vinculo": "UNIVERSAL",
        "niveles": None,
        "ambitos": ("ENTE", "UNIDAD"),
        "nota": None,
        "anexos": [
            _anexo("A11_1", "Estado de cuentas (situación presupuestaria, financiera y patrimonial)", "11.1", generable=True),
            _anexo("A11_2", "Cargos existentes", "11.2", generable=True),
            _anexo("A11_3", "Inventario de bienes muebles e inmuebles", "11.3"),
            _anexo("A11_4", "Situación de la ejecución del plan operativo", "11.4"),
            _anexo("A11_5", "Índice general del archivo", "11.5", generable=True),
            _anexo("A11_6", "Otra información o documentación", "11.6", obligatorio=False),
        ],
    },
    {
        "codigo": "N34_ART12",
        "articulo": "12",
        "titulo": "Unidad administradora",
        "sujeto": "Unidad administradora",
        "vinculo": "DECLARADO",
        "niveles": None,
        "ambitos": ("ENTE", "UNIDAD"),
        "nota": (
            "Los anexos los fija el Reglamento Nº 1 de la LOAFSP sobre el Sistema Presupuestario, que no está "
            "custodiado: el ente los define como requisitos de su política."
        ),
        "anexos": [],
    },
    {
        "codigo": "N34_ART13",
        "articulo": "13",
        "titulo": "Ramos específicos",
        "sujeto": "Oficina o dependencia que maneja ramos específicos",
        "vinculo": "DECLARADO",
        "niveles": None,
        "ambitos": ("UNIDAD",),
        "nota": None,
        "anexos": [
            _anexo(
                "A13_1",
                "Detalle de lo liquidado y recaudado por los rubros y derechos pendientes de recaudación",
                "13",
            ),
        ],
    },
    {
        "codigo": "N34_ART14",
        "articulo": "14",
        "titulo": "Órgano de control fiscal",
        "sujeto": "Órgano de control fiscal",
        "vinculo": "DECLARADO",
        "niveles": None,
        "ambitos": ("ENTE", "UNIDAD"),
        "nota": None,
        "anexos": [
            _anexo(
                "A14_1",
                "Expedientes de potestad de investigación y de determinación de responsabilidades, con su estado",
                "14",
            ),
        ],
    },
    {
        "codigo": "N34_ART15",
        "articulo": "15",
        "titulo": "Ministerio de Finanzas",
        "sujeto": "Ministerio de Finanzas",
        "vinculo": "DECLARADO",
        "niveles": ("NACIONAL",),
        "ambitos": ("ENTE",),
        "nota": None,
        "anexos": [
            _anexo("A15_1", "Situación del Tesoro Nacional", "15.1"),
            _anexo("A15_2", "Ejecución del presupuesto nacional de ingresos y egresos y derechos pendientes", "15.2"),
            _anexo("A15_3", "Monto de la deuda pública nacional interna y externa", "15.3"),
            _anexo("A15_4", "Situación de las cuentas de la Nación", "15.4"),
        ],
    },
    {
        "codigo": "N34_ART16",
        "articulo": "16",
        "titulo": "Gobernación o hacienda estadal",
        "sujeto": "Gobernación, oficina o dependencia de hacienda estadal",
        "vinculo": "DECLARADO",
        "niveles": ("ESTADAL",),
        "ambitos": ("ENTE", "UNIDAD"),
        "nota": None,
        "anexos": [
            _anexo("A16_1", "Situación del Tesoro Estadal", "16.1"),
            _anexo("A16_2", "Ejecución del presupuesto estadal de ingresos y egresos y derechos pendientes", "16.2"),
            _anexo("A16_3", "Situación de las cuentas del estado", "16.3"),
        ],
    },
    {
        "codigo": "N34_ART17",
        "articulo": "17",
        "titulo": "Alcaldía o hacienda municipal",
        "sujeto": "Alcaldía o Dirección de hacienda distrital o municipal",
        "vinculo": "DECLARADO",
        "niveles": ("MUNICIPAL",),
        "ambitos": ("ENTE", "UNIDAD"),
        "nota": None,
        "anexos": [
            _anexo("A17_1", "Situación del Tesoro municipal", "17.1"),
            _anexo("A17_2", "Ejecución del presupuesto de ingresos y egresos y derechos pendientes", "17.2"),
            _anexo("A17_3", "Situación de las cuentas municipales", "17.3"),
            _anexo("A17_4", "Inventario de terrenos ejidos y propios", "17.4"),
            _anexo("A17_5", "Ingresos por venta de terrenos ejidos o propios", "17.5"),
        ],
    },
]

_SUPUESTOS_POR_CODIGO = {s["codigo"]: s for s in SUPUESTOS}

TESTIGOS_LEGALES: dict[str, Any] = {
    "modalidad": "LEVANTADA_POR_RECEPTOR",
    "testigos": 2,
    "auditor_interno": True,
    "fuente": _fuente("9"),
}

# Plazos legales en días hábiles (arts. 4, 21 y 22). Sin calendario hábil oficial no se calcula su vencimiento (D-AE-06).
PLAZOS_LEGALES: list[dict[str, Any]] = [
    {"hito": "ELABORACION", "valor": 3, "unidad": "DIAS_HABILES", "base": "TOMA_DE_POSESION", "fuente": _fuente("4")},
    {"hito": "REMISION_UAI", "valor": 5, "unidad": "DIAS_HABILES", "base": "SUSCRIPCION", "fuente": _fuente("21")},
    {"hito": "OBSERVACIONES", "valor": 120, "unidad": "DIAS_HABILES", "base": "SUSCRIPCION", "fuente": _fuente("22")},
]
_PLAZO_LEGAL_POR_HITO = {p["hito"]: p for p in PLAZOS_LEGALES}

PATRON_POR_DEFECTO = "AE-{ANIO}-{NUMERO:4}"
_LARGO_MAXIMO_CODIGO = 20
_TOKEN = re.compile(r"\{(ANIO|NUMERO:(\d))\}")
_RESERVADO = re.compile(r"^A1\d_")

AVISO_ART17 = (
    "Si el acta corresponde a una Alcaldía o Dirección de hacienda municipal, declárelo en la política de actas "
    "(N34 art. 17)."
)


def _invalida(codigo: str, mensaje: str, **extra: Any) -> KontrolError:
    return KontrolError(code=codigo, message=mensaje, status_code=422, **extra)


def supuesto(codigo: str) -> dict[str, Any] | None:
    return _SUPUESTOS_POR_CODIGO.get(codigo)


def ente_de(db: Session, ctx: CompanyContext) -> GovernmentEntity | None:
    return db.scalar(select(GovernmentEntity).where(GovernmentEntity.company_id == ctx.company_id))


# --- Validaciones del piso legal, que consume el servicio de políticas -------------------------------------------


def motivo_vinculo_invalido(nivel: str | None, codigo: str, alcance: str) -> str | None:
    """Por qué un supuesto no se puede declarar para el nivel del ente y el alcance; None si se puede."""
    s = supuesto(codigo)
    if s is None or s["vinculo"] != "DECLARADO":
        return "Ese supuesto no se declara: el art. 11 rige en toda acta."
    if s["niveles"] is not None and nivel not in s["niveles"]:
        return f"N34 art. {s['articulo']} solo aplica a entes de nivel {', '.join(s['niveles'])}."
    if alcance not in s["ambitos"]:
        return f"N34 art. {s['articulo']} solo se declara para: {', '.join(s['ambitos'])}."
    return None


def motivo_plazo_invalido(hito: str, valor: int, unidad: str) -> str | None:
    """Un plazo interno no puede ser más largo que el legal del mismo hito (D-AE-02)."""
    legal = _PLAZO_LEGAL_POR_HITO.get(hito)
    if legal is None:
        return "Hito no válido."
    if valor < 1:
        return "El plazo debe ser de al menos 1 día."
    if valor > legal["valor"]:
        return f"El plazo interno no puede superar el legal de {legal['valor']} días hábiles ({legal['fuente']})."
    if unidad not in ("DIAS_HABILES", "DIAS_CONTINUOS"):
        return "Unidad no válida."
    return None


def motivo_codigo_requisito_invalido(codigo: str) -> str | None:
    if not re.fullmatch(r"[A-Z0-9_]{2,8}", codigo):
        return "El código debe tener de 2 a 8 caracteres en mayúsculas, dígitos o guion bajo."
    if _RESERVADO.match(codigo):
        return "Los códigos A11_ a A19_ están reservados a los anexos legales de N34."
    return None


def motivo_patron_invalido(patron: str) -> str | None:
    tokens = _TOKEN.findall(patron)
    numeros = [t for t in tokens if t[0].startswith("NUMERO")]
    if len(numeros) != 1:
        return "El patrón debe incluir una vez {NUMERO:n}, con n de 3 a 6."
    if not 3 <= int(numeros[0][1]) <= 6:
        return "El número debe tener de 3 a 6 dígitos ({NUMERO:3} a {NUMERO:6})."
    resto = _TOKEN.sub("", patron)
    if "{" in resto or "}" in resto:
        return "El patrón solo admite {ANIO} y {NUMERO:n}."
    if not re.fullmatch(r"[A-Za-z0-9\-/._]*", resto):
        return "El patrón solo admite letras, dígitos y los separadores - / . _"
    if len(formatear_codigo(patron, 9999, 999999)) > _LARGO_MAXIMO_CODIGO:
        return f"El código resultante no puede pasar de {_LARGO_MAXIMO_CODIGO} caracteres."
    return None


def formatear_codigo(patron: str, anio: int, numero: int) -> str:
    def _sustituir(m: re.Match[str]) -> str:
        if m.group(1) == "ANIO":
            return str(anio)
        return f"{numero:0{int(m.group(2))}d}"

    return _TOKEN.sub(_sustituir, patron)


def vista_previa(patron: str, anio: int) -> dict[str, Any]:
    motivo = motivo_patron_invalido(patron)
    if motivo:
        return {"valido": False, "motivo": motivo, "ejemplos": []}
    return {"valido": True, "motivo": None, "ejemplos": [formatear_codigo(patron, anio, n) for n in (1, 2, 10)]}


def siguiente_codigo(db: Session, ctx: CompanyContext, regla: dict[str, Any], anio: int) -> str:
    """Siguiente código del patrón de la regla, secuencial por empresa y prefijo fijo del patrón."""
    patron = regla["numeracion"]["patron"]
    numero = next(m for m in _TOKEN.finditer(patron) if m.group(1).startswith("NUMERO"))
    prefijo = formatear_codigo(patron[: numero.start()], anio, 0)
    sufijo = formatear_codigo(patron[numero.end() :], anio, 0)
    existentes = db.scalars(
        select(GovernmentHandoverAct.codigo).where(
            GovernmentHandoverAct.company_id == ctx.company_id,
            GovernmentHandoverAct.codigo.like(f"{prefijo}%"),
        )
    ).all()
    patron_numero = re.compile(re.escape(prefijo) + r"(\d+)" + re.escape(sufijo) + "$")
    maximo = 0
    for existente in existentes:
        m = patron_numero.match(existente)
        if m:
            maximo = max(maximo, int(m.group(1)))
    return formatear_codigo(patron, anio, maximo + 1)


# --- Regla aplicada --------------------------------------------------------------------------------------------


def politica_aplicable(db: Session, ctx: CompanyContext, fecha: date) -> GovernmentHandoverPolicy | None:
    """Política VIGENTE de la empresa cuya vigencia cubre la fecha (D-AE-03)."""
    return db.scalar(
        select(GovernmentHandoverPolicy).where(
            GovernmentHandoverPolicy.company_id == ctx.company_id,
            GovernmentHandoverPolicy.estado == "VIGENTE",
            GovernmentHandoverPolicy.vigente_desde <= fecha,
            or_(GovernmentHandoverPolicy.vigente_hasta.is_(None), GovernmentHandoverPolicy.vigente_hasta >= fecha),
        )
    )


def ambito_de(
    db: Session, asignacion: GovernmentAssignment, politica: GovernmentHandoverPolicy | None
) -> tuple[str, str | None, str]:
    """Art. 6: entrega la ENTIDAD quien ejerce la máxima autoridad; los demás, su oficina o dependencia.

    Es máxima autoridad la suplencia marcada como tal (ORG-04) o quien ocupa el cargo cuyo código declara la
    política (D-AE-14). KONTROL no infiere la máxima autoridad por el nombre del cargo.
    """
    cargo = db.scalar(select(GovernmentPosition).where(GovernmentPosition.id == asignacion.position_id))
    unit_id = cargo.unit_id if cargo else None
    if asignacion.maxima_autoridad:
        return "ENTE", unit_id, "Suple a la máxima autoridad (Ocupación de cargos)."
    codigo = politica.cargo_maxima_autoridad_codigo if politica is not None else None
    if codigo and cargo is not None and cargo.code == codigo:
        return "ENTE", unit_id, f"Ocupa el cargo de máxima autoridad que declara la política ({codigo})."
    return "UNIDAD", unit_id, "Entrega de su oficina o dependencia (N34 art. 6)."


def _de_politica(politica: GovernmentHandoverPolicy | None) -> str | None:
    return f"Política {politica.codigo} v{politica.numero_version}" if politica is not None else None


def _vinculo_aplica(vinculo: GovernmentHandoverPolicyBinding, ambito: str, unit_id: str | None) -> bool:
    if vinculo.alcance == "ENTE":
        return ambito == "ENTE"
    return ambito == "UNIDAD" and unit_id is not None and vinculo.unit_id == unit_id


def _requisito_aplica(requisito: GovernmentHandoverPolicyRequirement, ambito: str, activos: set[str]) -> bool:
    if requisito.ambito not in ("TODAS", ambito):
        return False
    return requisito.supuesto is None or requisito.supuesto in activos


def instantanea(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentHandoverPolicy | None,
    *,
    ambito: str,
    fecha: date,
    unit_id: str | None = None,
) -> dict[str, Any]:
    """Catálogo legal + política, resueltos para el ámbito, la unidad y la fecha de corte."""
    ente = ente_de(db, ctx)
    nivel = ente.nivel_territorial if ente else None
    unidad = db.scalar(select(GovernmentUnit).where(GovernmentUnit.id == unit_id)) if unit_id else None

    vinculos: list[GovernmentHandoverPolicyBinding] = []
    requisitos: list[GovernmentHandoverPolicyRequirement] = []
    plazos_politica: list[GovernmentHandoverPolicyDeadline] = []
    if politica is not None:
        vinculos = list(
            db.scalars(select(GovernmentHandoverPolicyBinding).where(GovernmentHandoverPolicyBinding.policy_id == politica.id))
        )
        requisitos = list(
            db.scalars(
                select(GovernmentHandoverPolicyRequirement)
                .where(GovernmentHandoverPolicyRequirement.policy_id == politica.id)
                .order_by(GovernmentHandoverPolicyRequirement.codigo)
            )
        )
        plazos_politica = list(
            db.scalars(select(GovernmentHandoverPolicyDeadline).where(GovernmentHandoverPolicyDeadline.policy_id == politica.id))
        )

    supuestos: list[dict[str, Any]] = []
    anexos: list[dict[str, Any]] = []
    for s in SUPUESTOS:
        if s["vinculo"] == "UNIVERSAL":
            motivo = "Rige en toda acta de entrega (arts. 5 y 11)."
            alcance = None
        else:
            vinculo = next((v for v in vinculos if v.supuesto == s["codigo"] and _vinculo_aplica(v, ambito, unit_id)), None)
            if vinculo is None or (s["niveles"] is not None and nivel not in s["niveles"]):
                continue
            alcance = vinculo.alcance
            motivo = (
                "La política del ente lo declara para la entidad."
                if alcance == "ENTE"
                else f"La política del ente lo declara para la unidad {unidad.name if unidad else ''}."
            )
        supuestos.append(
            {
                "codigo": s["codigo"],
                "articulo": s["articulo"],
                "titulo": s["titulo"],
                "sujeto": s["sujeto"],
                "vinculo": s["vinculo"],
                "alcance": alcance,
                "motivo": motivo,
                "nota": s["nota"],
            }
        )
        for a in s["anexos"]:
            anexos.append(
                {
                    **a,
                    "origen": "LEGAL",
                    "supuesto": s["codigo"],
                    "document_type_id": None,
                    "document_type_nombre": None,
                }
            )

    activos = {s["codigo"] for s in supuestos}
    tipos: dict[str, str] = {}
    ids_tipo = [r.document_type_id for r in requisitos if r.document_type_id]
    if ids_tipo:
        tipos = {str(t.id): t.name for t in db.scalars(select(DocumentType).where(DocumentType.id.in_(ids_tipo)))}
    for r in requisitos:
        if not _requisito_aplica(r, ambito, activos):
            continue
        anexos.append(
            {
                "codigo": r.codigo,
                "titulo": r.titulo,
                "obligatorio": r.obligatorio,
                "generable": False,
                "evidencia": r.evidencia,
                "fuente": r.fuente or _de_politica(politica),
                "origen": "POLITICA",
                "supuesto": r.supuesto,
                "document_type_id": r.document_type_id,
                "document_type_nombre": tipos.get(str(r.document_type_id)) if r.document_type_id else None,
            }
        )

    plazos: list[dict[str, Any]] = [{**p, "origen": "LEGAL"} for p in PLAZOS_LEGALES]
    for p in plazos_politica:
        legal = _PLAZO_LEGAL_POR_HITO[p.hito]
        plazos.append(
            {
                "hito": p.hito,
                "valor": p.valor,
                "unidad": p.unidad,
                "base": legal["base"],
                "fuente": p.fuente or _de_politica(politica),
                "origen": "POLITICA",
            }
        )

    avisos: list[str] = []
    if nivel == "MUNICIPAL" and "N34_ART17" not in activos:
        avisos.append(AVISO_ART17)

    fundamentos = [f"{NORMA_N34['titulo']}, {NORMA_N34['instrumento']}, {NORMA_N34['gaceta']}."]
    if politica is not None and politica.fundamento:
        fundamentos.append(politica.fundamento)

    norma = {**NORMA_N34, "vigente_desde": NORMA_N34["vigente_desde"].isoformat()}
    return {
        "origen": "POLITICA" if politica is not None else "LEGAL",
        "origen_etiqueta": (
            "Política institucional sobre el catálogo legal" if politica is not None else "Catálogo legal, sin política institucional"
        ),
        "politica": (
            {
                "id": str(politica.id),
                "codigo": politica.codigo,
                "numero_version": politica.numero_version,
                "nombre": politica.nombre,
            }
            if politica is not None
            else None
        ),
        "regla_version": (
            f"{politica.codigo} v{politica.numero_version}" if politica is not None else f"Catálogo legal {NORMA_N34['version']}"
        ),
        "norma": norma,
        "fecha": fecha.isoformat(),
        "ambito": ambito,
        "unit_id": unit_id,
        "unidad": unidad.name if unidad else None,
        "nivel_territorial": nivel,
        "forma_organizativa": ente.forma_organizativa if ente else None,
        "supuestos": supuestos,
        "anexos": anexos,
        "testigos": {
            "levantada_por_receptor": dict(TESTIGOS_LEGALES),
            "entrega": {
                "minimo": politica.testigos_en_entrega if politica is not None else 0,
                "fuente": _de_politica(politica),
            },
        },
        "plazos": plazos,
        "numeracion": {
            "patron": politica.numeracion_patron if politica is not None and politica.numeracion_patron else PATRON_POR_DEFECTO,
            "origen": "POLITICA" if politica is not None and politica.numeracion_patron else "DEFECTO",
        },
        "fundamentos": fundamentos,
        "avisos": avisos,
    }


def regla_aplicable(
    db: Session, ctx: CompanyContext, *, ambito: str, unit_id: str | None, fecha: date
) -> tuple[dict[str, Any], GovernmentHandoverPolicy | None]:
    politica = politica_aplicable(db, ctx, fecha)
    return instantanea(db, ctx, politica, ambito=ambito, unit_id=unit_id, fecha=fecha), politica


def _supuesto_legado(codigo: str) -> str | None:
    m = re.match(r"^A(1\d)_", codigo)
    return f"N34_ART{m.group(1)}" if m else None


def regla_de(db: Session, acta: GovernmentHandoverAct) -> dict[str, Any]:
    """La regla congelada del acta o, para un acta anterior a la política, su regla HISTORICA (D-AE-10)."""
    if acta.regla:
        return acta.regla
    filas = list(
        db.scalars(
            select(GovernmentHandoverAnnex)
            .where(GovernmentHandoverAnnex.act_id == str(acta.id))
            .order_by(GovernmentHandoverAnnex.codigo)
        )
    )
    anexos = [
        {
            "codigo": f.codigo,
            "titulo": f.titulo,
            "obligatorio": f.obligatorio,
            "generable": f.generable,
            "evidencia": "DOCUMENTO",
            "fuente": None,
            "origen": "LEGAL",
            "supuesto": _supuesto_legado(f.codigo),
            "document_type_id": None,
            "document_type_nombre": None,
        }
        for f in filas
    ]
    return {
        "origen": "HISTORICA",
        "origen_etiqueta": "Regla anterior a la política de actas",
        "politica": None,
        "regla_version": "Regla anterior a la política de actas",
        "norma": {**NORMA_N34, "vigente_desde": NORMA_N34["vigente_desde"].isoformat()},
        "fecha": acta.fecha_corte.isoformat(),
        "ambito": acta.ambito,
        "unit_id": acta.unit_id,
        "unidad": None,
        "nivel_territorial": None,
        "forma_organizativa": None,
        "supuestos": [],
        "anexos": anexos,
        "testigos": {"levantada_por_receptor": dict(TESTIGOS_LEGALES), "entrega": {"minimo": 0, "fuente": None}},
        "plazos": [{**p, "origen": "LEGAL"} for p in PLAZOS_LEGALES],
        "numeracion": {"patron": PATRON_POR_DEFECTO, "origen": "DEFECTO"},
        "fundamentos": [],
        "avisos": [],
    }


# --- Validaciones del acta -----------------------------------------------------------------------------------


def validar_testigos(
    regla: dict[str, Any],
    modalidad: str,
    testigos: list[dict[str, Any]],
    auditor_valido: bool,
) -> None:
    """Art. 9 en el acta levantada por el receptor; el mínimo de la política en la entrega por el saliente."""
    legales = regla["testigos"]["levantada_por_receptor"]
    if modalidad == legales["modalidad"]:
        if len(testigos) != legales["testigos"]:
            raise _invalida(
                "GOV_HANDOVER_WITNESSES_REQUIRED",
                f"La modalidad por receptor exige exactamente {legales['testigos']} testigos ({legales['fuente']}).",
            )
    else:
        exigido = int(regla["testigos"]["entrega"]["minimo"] or 0)
        if len(testigos) < exigido:
            raise _invalida(
                "GOV_HANDOVER_WITNESSES_REQUIRED",
                f"La política del ente exige al menos {exigido} testigos en la entrega.",
            )
    for testigo in testigos:
        nombre = str(testigo.get("nombre", ""))
        documento = str(testigo.get("documento", ""))
        if not (3 <= len(nombre) <= 120) or not (3 <= len(documento) <= 20):
            raise _invalida(
                "GOV_HANDOVER_WITNESSES_REQUIRED",
                "Los testigos deben tener nombre (3..120) y documento (3..20).",
            )
    if modalidad == legales["modalidad"] and legales["auditor_interno"] and not auditor_valido:
        raise _invalida("GOV_HANDOVER_WITNESSES_REQUIRED", "La modalidad por receptor exige un auditor del ente.")


def tipos_de_documentos(db: Session, company_id: str, documento_ids: list[str]) -> dict[str, str | None]:
    if not documento_ids:
        return {}
    filas = db.execute(
        select(Document.id, Document.document_type_id).where(
            Document.company_id == company_id, Document.id.in_(documento_ids)
        )
    ).all()
    return {str(f[0]): (str(f[1]) if f[1] else None) for f in filas}


def anexo_resuelto(anexo: GovernmentHandoverAnnex, tipos: dict[str, str | None] | None = None) -> bool:
    """Un anexo queda resuelto según su evidencia (D-AE-04); la constancia del art. 19 vale siempre."""
    if (anexo.constancia or "").strip():
        return True
    if anexo.generable and anexo.incluir_generado:
        return True
    evidencia = anexo.evidencia or "DOCUMENTO"
    if evidencia in ("DECLARACION", "DATO"):
        return len((anexo.declaracion or "").strip()) >= 10
    if not anexo.documento_ids:
        return False
    if anexo.document_type_id and tipos is not None:
        return any(tipos.get(str(d)) == anexo.document_type_id for d in anexo.documento_ids)
    return True


def anexos_pendientes(db: Session, company_id: str, anexos: list[GovernmentHandoverAnnex]) -> list[str]:
    ids = [str(d) for a in anexos for d in (a.documento_ids or [])]
    tipos = tipos_de_documentos(db, company_id, ids)
    return [a.codigo for a in anexos if a.obligatorio and not anexo_resuelto(a, tipos)]


# --- Responsabilidad (ORG-04 reutilizada, D-AE-08) --------------------------------------------------------------


def responsabilidad(
    db: Session,
    ctx: CompanyContext,
    *,
    asignacion: GovernmentAssignment,
    receptor: GovernmentOfficial,
    receptor_asignacion: GovernmentAssignment | None,
    fecha_corte: date,
    ambito: str,
    unit_id: str | None,
) -> dict[str, Any]:
    """Valida con la autoridad de ORG-04 que el saliente ejerce al corte y congela quién entrega y quién recibe."""
    from app.modules.government.service_ocupacion import detalle

    situacion = detalle(db, ctx, str(asignacion.id), fecha_corte).get("situacion")
    if situacion != "VIGENTE":
        raise _invalida(
            "GOV_HANDOVER_ASSIGNMENT_INVALID",
            "El saliente no ejerce esa ocupación en la fecha de corte (Ocupación de cargos).",
            details={"situacion": situacion},
        )
    relacion = "DESIGNADO"
    receptor_situacion = None
    if receptor_asignacion is not None:
        receptor_situacion = detalle(db, ctx, str(receptor_asignacion.id), fecha_corte).get("situacion")
        if receptor_situacion not in ("VIGENTE", "FUTURA"):
            raise _invalida(
                "GOV_HANDOVER_RECEIVER_INVALID",
                "La ocupación del receptor ya no está vigente en la fecha de corte.",
                details={"situacion": receptor_situacion},
            )
        if receptor_asignacion.position_id == asignacion.position_id:
            relacion = "SUCESOR"
    cargo = db.scalar(select(GovernmentPosition).where(GovernmentPosition.id == asignacion.position_id))
    return {
        "fecha_efectiva": fecha_corte.isoformat(),
        "ambito": ambito,
        "unit_id": unit_id,
        "saliente": {
            "assignment_id": str(asignacion.id),
            "official_id": str(asignacion.official_id),
            "figura": asignacion.figura,
            "cargo_id": str(asignacion.position_id),
            "cargo": cargo.name if cargo else "",
            "desde": asignacion.desde.isoformat() if asignacion.desde else None,
            "situacion_al_corte": situacion,
        },
        "receptor": {
            "official_id": str(receptor.id),
            "funcionario": receptor.nombre,
            "assignment_id": str(receptor_asignacion.id) if receptor_asignacion is not None else None,
            "desde": receptor_asignacion.desde.isoformat() if receptor_asignacion is not None and receptor_asignacion.desde else None,
            "situacion_al_corte": receptor_situacion,
            "relacion": relacion,
        },
    }


# --- Plazos (D-AE-06) ------------------------------------------------------------------------------------------


def _base_y_hecho(acta: GovernmentHandoverAct, hito: str, responsable: dict[str, Any] | None) -> tuple[date | None, date | None]:
    if hito == "ELABORACION":
        desde = (responsable or {}).get("receptor", {}).get("desde")
        base = date.fromisoformat(desde) if desde else acta.fecha_corte
        if base < acta.fecha_corte:
            base = acta.fecha_corte
        return base, acta.fecha_suscripcion
    if hito == "REMISION_UAI":
        return acta.fecha_suscripcion, acta.remision_uai_fecha
    return acta.fecha_suscripcion, None


def plazos(acta: GovernmentHandoverAct, regla: dict[str, Any], hoy: date) -> list[dict[str, Any]]:
    """Estado de cada plazo: los hábiles se registran sin vencimiento; los continuos se calculan."""
    responsable = regla.get("responsabilidad")
    salida: list[dict[str, Any]] = []
    for p in regla.get("plazos", []):
        base, hecho = _base_y_hecho(acta, p["hito"], responsable)
        vence = None
        if p["unidad"] == "DIAS_HABILES":
            estado = "REGISTRADO" if hecho else "SIN_CALENDARIO_HABIL"
        elif base is None:
            estado = "PENDIENTE"
        else:
            vence = base + timedelta(days=int(p["valor"]))
            if hecho is not None:
                estado = "CUMPLIDO" if hecho <= vence else "CUMPLIDO_FUERA_DE_PLAZO"
            else:
                estado = "VENCIDO" if hoy > vence else "EN_PLAZO"
        salida.append(
            {
                **p,
                "base_fecha": base.isoformat() if base else None,
                "vence": vence.isoformat() if vence else None,
                "hecho": hecho.isoformat() if hecho else None,
                "estado": estado,
            }
        )
    return salida


def politicas_que_usan(db: Session, ctx: CompanyContext, politica_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(GovernmentHandoverAct).where(
            GovernmentHandoverAct.company_id == ctx.company_id,
            GovernmentHandoverAct.policy_id == politica_id,
        )
    ) or 0
