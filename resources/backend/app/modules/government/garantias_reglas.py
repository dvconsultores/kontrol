"""Catálogo normativo versionado de garantías y cauciones (PROC-10).

Autoridad normativa única: este módulo no importa nada de la aplicación.
Los porcentajes legales viven exclusivamente aquí.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

TIPOS_GARANTIA = (
    "MANTENIMIENTO_OFERTA",
    "ANTICIPO",
    "FIEL_CUMPLIMIENTO",
    "LABORAL",
    "RESPONSABILIDAD_CIVIL",
    "OTRA",
)

ETAPAS_GARANTIA = ("PROCEDIMIENTO", "FORMALIZACION", "EJECUCION_CONTRACTUAL")

FORMAS_GARANTIA = ("PORCENTAJE", "MONTO_FIJO")

TIPOS_EMISOR = ("BANCO", "ASEGURADORA", "SOCIEDAD_GARANTIAS_RECIPROCAS", "OTRO")

ESTADOS_EMISOR = ("ACTIVO", "INACTIVO")

ESTADOS_GARANTIA = ("REGISTRADA", "RENOVADA", "SUSTITUIDA", "LIBERADA", "EJECUTADA")

ORIGENES_GARANTIA = ("REGISTRO", "RENOVACION", "SUSTITUCION")

ACCIONES_GARANTIA = ("REGISTRO", "RENOVACION", "SUSTITUCION", "LIBERACION", "EJECUCION")

PRECONDICIONES_LIBERACION = ("VERIFICADA", "SOPORTADA_POR_ACTO")

# PDD-PROC10-07, días naturales.
DIAS_POR_VENCER = 15

ETIQUETA_TIPO: dict[str, str] = {
    "MANTENIMIENTO_OFERTA": "Mantenimiento de oferta",
    "ANTICIPO": "Anticipo",
    "FIEL_CUMPLIMIENTO": "Fiel cumplimiento",
    "LABORAL": "Laboral",
    "RESPONSABILIDAD_CIVIL": "Responsabilidad civil",
    "OTRA": "Otra garantía",
}

ETIQUETA_ETAPA: dict[str, str] = {
    "PROCEDIMIENTO": "Procedimiento",
    "FORMALIZACION": "Formalización",
    "EJECUCION_CONTRACTUAL": "Ejecución contractual",
}

ETIQUETA_EMISOR: dict[str, str] = {
    "BANCO": "Banco",
    "ASEGURADORA": "Aseguradora",
    "SOCIEDAD_GARANTIAS_RECIPROCAS": "Sociedad de Garantías Recíprocas",
    "OTRO": "Otro",
}

ETIQUETA_ESTADO: dict[str, str] = {
    "REGISTRADA": "Registrada",
    "RENOVADA": "Renovada",
    "SUSTITUIDA": "Sustituida",
    "LIBERADA": "Liberada",
    "EJECUTADA": "Ejecutada",
}

ETIQUETA_ACCION: dict[str, str] = {
    "REGISTRO": "Registro",
    "RENOVACION": "Renovación",
    "SUSTITUCION": "Sustitución",
    "LIBERACION": "Liberación",
    "EJECUCION": "Ejecución",
}

ETIQUETA_PRECONDICION: dict[str, str] = {
    "VERIFICADA": "Verificada",
    "SOPORTADA_POR_ACTO": "Soportada por el acto",
}

BASES_GARANTIA: dict[str, str] = {
    "PRESUPUESTO_ESTIMADO_SIN_TRIBUTOS": "presupuesto estimado sin tributos (lo fija el pliego, PROC-04)",
    "MONTO_OFERTA": "monto de la oferta (la oferta no registra monto)",
    "MONTO_ANTICIPO": "monto del anticipo (lo fija el contrato, CNT-01)",
    "MONTO_CONTRATO_CON_TRIBUTOS": "monto del contrato con tributos (CNT-01)",
    "COSTO_PERSONAL_OFERTA": "costo del personal de la estructura de costos de la oferta",
    "BASE_DEL_PLIEGO": "base de cálculo señalada en el pliego (PROC-04)",
}


@dataclass(frozen=True)
class ReglaGarantia:
    codigo: str
    version: int
    tipo: str
    nombre: str
    fuente: str
    gaceta: str
    vigente_desde: date
    vigente_hasta: date | None
    etapa: str
    requiere_adjudicacion: bool
    forma: str
    base: str | None
    porcentaje_min: Decimal | None
    porcentaje_max: Decimal | None
    moneda_exigida: str | None
    emisores_admitidos: tuple[str, ...] | None
    permite_sustitucion: bool
    permite_coexistencia: bool
    retencion_alternativa_pct: Decimal | None
    vigencia_exigida: str
    condicion_liberacion: str
    condicion_ejecucion: str


GACETA_LCP = "Decreto-Ley de Contrataciones Públicas, G.O. N.º 6.154 Extraordinario, 19-11-2014"
GACETA_RLCP = "Reglamento de la Ley de Contrataciones Públicas, G.O. N.º 39.181, 19-05-2009"

REGLAS: tuple[ReglaGarantia, ...] = (
    ReglaGarantia(
        codigo="MANT-PRESUPUESTO-1",
        version=1,
        tipo="MANTENIMIENTO_OFERTA",
        nombre="Mantenimiento de oferta: porcentaje del presupuesto estimado",
        fuente="LCP arts. 63, 64 y 71; RLCP art. 135",
        gaceta=f"{GACETA_LCP}; {GACETA_RLCP}",
        vigente_desde=date(2014, 11, 19),
        vigente_hasta=None,
        etapa="PROCEDIMIENTO",
        requiere_adjudicacion=False,
        forma="PORCENTAJE",
        base="PRESUPUESTO_ESTIMADO_SIN_TRIBUTOS",
        porcentaje_min=Decimal("1.50"),
        porcentaje_max=Decimal("2.50"),
        moneda_exigida=None,
        emisores_admitidos=None,
        permite_sustitucion=False,
        permite_coexistencia=False,
        retencion_alternativa_pct=None,
        vigencia_exigida="Hasta la suscripción del contrato; con prórroga de la oferta, el tiempo del pliego más la prórroga (LCP arts. 64 y 71; RLCP art. 135)",
        condicion_liberacion="Firma del contrato o fin del procedimiento para los oferentes no adjudicados (LCP art. 64)",
        condicion_ejecucion="El oferente no mantiene su oferta o el adjudicatario no firma el contrato (LCP arts. 63 y 110)",
    ),
    ReglaGarantia(
        codigo="MANT-OFERTA-1",
        version=1,
        tipo="MANTENIMIENTO_OFERTA",
        nombre="Mantenimiento de oferta: porcentaje de la oferta",
        fuente="LCP arts. 63, 64 y 71; RLCP art. 135",
        gaceta=f"{GACETA_LCP}; {GACETA_RLCP}",
        vigente_desde=date(2014, 11, 19),
        vigente_hasta=None,
        etapa="PROCEDIMIENTO",
        requiere_adjudicacion=False,
        forma="PORCENTAJE",
        base="MONTO_OFERTA",
        porcentaje_min=None,
        porcentaje_max=Decimal("100"),
        moneda_exigida=None,
        emisores_admitidos=None,
        permite_sustitucion=False,
        permite_coexistencia=False,
        retencion_alternativa_pct=None,
        vigencia_exigida="Hasta la suscripción del contrato; con prórroga de la oferta, el tiempo del pliego más la prórroga (LCP arts. 64 y 71; RLCP art. 135)",
        condicion_liberacion="Firma del contrato o fin del procedimiento para los oferentes no adjudicados (LCP art. 64)",
        condicion_ejecucion="El oferente no mantiene su oferta o el adjudicatario no firma el contrato (LCP arts. 63 y 110)",
    ),
    ReglaGarantia(
        codigo="MANT-FIJO-1",
        version=1,
        tipo="MANTENIMIENTO_OFERTA",
        nombre="Mantenimiento de oferta: monto fijo en bolívares",
        fuente="LCP arts. 63, 64 y 71; RLCP art. 135",
        gaceta=f"{GACETA_LCP}; {GACETA_RLCP}",
        vigente_desde=date(2014, 11, 19),
        vigente_hasta=None,
        etapa="PROCEDIMIENTO",
        requiere_adjudicacion=False,
        forma="MONTO_FIJO",
        base=None,
        porcentaje_min=None,
        porcentaje_max=None,
        moneda_exigida="VES",
        emisores_admitidos=None,
        permite_sustitucion=False,
        permite_coexistencia=False,
        retencion_alternativa_pct=None,
        vigencia_exigida="Hasta la suscripción del contrato; con prórroga de la oferta, el tiempo del pliego más la prórroga (LCP arts. 64 y 71; RLCP art. 135)",
        condicion_liberacion="Firma del contrato o fin del procedimiento para los oferentes no adjudicados (LCP art. 64)",
        condicion_ejecucion="El oferente no mantiene su oferta o el adjudicatario no firma el contrato (LCP arts. 63 y 110)",
    ),
    ReglaGarantia(
        codigo="ANTICIPO-1",
        version=1,
        tipo="ANTICIPO",
        nombre="Anticipo: cien por ciento del anticipo",
        fuente="LCP art. 122; RLCP art. 91",
        gaceta=f"{GACETA_LCP}; {GACETA_RLCP}",
        vigente_desde=date(2014, 11, 19),
        vigente_hasta=None,
        etapa="FORMALIZACION",
        requiere_adjudicacion=True,
        forma="PORCENTAJE",
        base="MONTO_ANTICIPO",
        porcentaje_min=Decimal("100"),
        porcentaje_max=Decimal("100"),
        moneda_exigida=None,
        emisores_admitidos=None,
        permite_sustitucion=False,
        permite_coexistencia=False,
        retencion_alternativa_pct=None,
        vigencia_exigida="Mientras exista anticipo por amortizar (contrato, CNT-01)",
        condicion_liberacion="Amortización total del anticipo o recepción definitiva (LCP art. 151)",
        condicion_ejecucion="Incumplimiento del contratista o rescisión del contrato (RLCP art. 194)",
    ),
    ReglaGarantia(
        codigo="FIEL-1",
        version=1,
        tipo="FIEL_CUMPLIMIENTO",
        nombre="Fiel cumplimiento: al menos veinte por ciento del contrato con tributos",
        fuente="LCP art. 123",
        gaceta=f"{GACETA_LCP}; {GACETA_RLCP}",
        vigente_desde=date(2014, 11, 19),
        vigente_hasta=None,
        etapa="FORMALIZACION",
        requiere_adjudicacion=True,
        forma="PORCENTAJE",
        base="MONTO_CONTRATO_CON_TRIBUTOS",
        porcentaje_min=Decimal("20"),
        porcentaje_max=Decimal("100"),
        moneda_exigida=None,
        emisores_admitidos=None,
        permite_sustitucion=True,
        permite_coexistencia=True,
        retencion_alternativa_pct=Decimal("10"),
        vigencia_exigida="Hasta la recepción definitiva del bien u obra o la terminación del servicio (LCP art. 123)",
        condicion_liberacion="Recepción definitiva y certificación del cumplimiento (LCP art. 151)",
        condicion_ejecucion="Rescisión por causa imputable al contratista (LCP art. 155; RLCP art. 194)",
    ),
    ReglaGarantia(
        codigo="LABORAL-1",
        version=1,
        tipo="LABORAL",
        nombre="Laboral: hasta diez por ciento del costo de personal",
        fuente="LCP art. 124; RLCP art. 136",
        gaceta=f"{GACETA_LCP}; {GACETA_RLCP}",
        vigente_desde=date(2014, 11, 19),
        vigente_hasta=None,
        etapa="FORMALIZACION",
        requiere_adjudicacion=True,
        forma="PORCENTAJE",
        base="COSTO_PERSONAL_OFERTA",
        porcentaje_min=None,
        porcentaje_max=Decimal("10"),
        moneda_exigida=None,
        emisores_admitidos=("BANCO", "ASEGURADORA", "SOCIEDAD_GARANTIAS_RECIPROCAS"),
        permite_sustitucion=True,
        permite_coexistencia=True,
        retencion_alternativa_pct=Decimal("5"),
        vigencia_exigida="Desde el inicio del contrato hasta seis meses después de su terminación o recepción definitiva (LCP art. 124)",
        condicion_liberacion="Seis meses después de la terminación o recepción definitiva (LCP art. 124)",
        condicion_ejecucion="Reclamos de los trabajadores de la contratación, beneficiarios directos (LCP art. 124)",
    ),
    ReglaGarantia(
        codigo="RESP-CIVIL-1",
        version=1,
        tipo="RESPONSABILIDAD_CIVIL",
        nombre="Póliza de responsabilidad civil",
        fuente="LCP art. 125",
        gaceta=f"{GACETA_LCP}; {GACETA_RLCP}",
        vigente_desde=date(2014, 11, 19),
        vigente_hasta=None,
        etapa="FORMALIZACION",
        requiere_adjudicacion=True,
        forma="MONTO_FIJO",
        base=None,
        porcentaje_min=None,
        porcentaje_max=None,
        moneda_exigida=None,
        emisores_admitidos=None,
        permite_sustitucion=False,
        permite_coexistencia=False,
        retencion_alternativa_pct=None,
        vigencia_exigida="La fijada en el contrato (LCP art. 125)",
        condicion_liberacion="Terminación del contrato (LCP art. 151)",
        condicion_ejecucion="Daños a personas o bienes de terceros con ocasión de la obra o servicio (LCP art. 125)",
    ),
    ReglaGarantia(
        codigo="OTRA-FIJO-1",
        version=1,
        tipo="OTRA",
        nombre="Otra garantía del pliego: monto fijo",
        fuente="LCP art. 126; RLCP art. 137",
        gaceta=f"{GACETA_LCP}; {GACETA_RLCP}",
        vigente_desde=date(2014, 11, 19),
        vigente_hasta=None,
        etapa="FORMALIZACION",
        requiere_adjudicacion=True,
        forma="MONTO_FIJO",
        base=None,
        porcentaje_min=None,
        porcentaje_max=None,
        moneda_exigida=None,
        emisores_admitidos=None,
        permite_sustitucion=False,
        permite_coexistencia=False,
        retencion_alternativa_pct=None,
        vigencia_exigida="La señalada en el pliego o en las condiciones de la contratación",
        condicion_liberacion="La señalada en el pliego o en las condiciones de la contratación",
        condicion_ejecucion="La señalada en el pliego o en las condiciones de la contratación",
    ),
    ReglaGarantia(
        codigo="OTRA-PORC-1",
        version=1,
        tipo="OTRA",
        nombre="Otra garantía del pliego: porcentaje",
        fuente="LCP art. 126; RLCP art. 137",
        gaceta=f"{GACETA_LCP}; {GACETA_RLCP}",
        vigente_desde=date(2014, 11, 19),
        vigente_hasta=None,
        etapa="FORMALIZACION",
        requiere_adjudicacion=True,
        forma="PORCENTAJE",
        base="BASE_DEL_PLIEGO",
        porcentaje_min=None,
        porcentaje_max=Decimal("100"),
        moneda_exigida=None,
        emisores_admitidos=None,
        permite_sustitucion=False,
        permite_coexistencia=False,
        retencion_alternativa_pct=None,
        vigencia_exigida="La señalada en el pliego o en las condiciones de la contratación",
        condicion_liberacion="La señalada en el pliego o en las condiciones de la contratación",
        condicion_ejecucion="La señalada en el pliego o en las condiciones de la contratación",
    ),
)


def regla(codigo: str) -> ReglaGarantia | None:
    for r in REGLAS:
        if r.codigo == codigo:
            return r
    return None


def reglas_vigentes(fecha: date) -> list[ReglaGarantia]:
    return [
        r
        for r in REGLAS
        if r.vigente_desde <= fecha and (r.vigente_hasta is None or r.vigente_hasta >= fecha)
    ]


def instantanea(r: ReglaGarantia) -> dict[str, Any]:
    return {
        "codigo": r.codigo,
        "version": r.version,
        "tipo": r.tipo,
        "nombre": r.nombre,
        "fuente": r.fuente,
        "gaceta": r.gaceta,
        "vigente_desde": r.vigente_desde.isoformat(),
        "vigente_hasta": r.vigente_hasta.isoformat() if r.vigente_hasta else None,
        "etapa": r.etapa,
        "requiere_adjudicacion": r.requiere_adjudicacion,
        "forma": r.forma,
        "base": r.base,
        "porcentaje_min": str(r.porcentaje_min) if r.porcentaje_min is not None else None,
        "porcentaje_max": str(r.porcentaje_max) if r.porcentaje_max is not None else None,
        "moneda_exigida": r.moneda_exigida,
        "emisores_admitidos": list(r.emisores_admitidos) if r.emisores_admitidos else None,
        "permite_sustitucion": r.permite_sustitucion,
        "permite_coexistencia": r.permite_coexistencia,
        "retencion_alternativa_pct": str(r.retencion_alternativa_pct)
        if r.retencion_alternativa_pct is not None
        else None,
        "vigencia_exigida": r.vigencia_exigida,
        "condicion_liberacion": r.condicion_liberacion,
        "condicion_ejecucion": r.condicion_ejecucion,
    }


def base_disponible(base: str | None) -> Decimal | None:
    """La plataforma no registra hoy ninguna base de cálculo (PDD-PROC10-05). CNT-01 aportará el monto contractual aquí."""
    return None
