"""Controles de integridad posteriores a la E2E para TRE-02 (caja y programas de tesorería).

Cada consulta devuelve el número de violaciones en toda la base.
"""

GRUPO = "TRE-02"

INFO: dict[str, str] = {
    "programas": "SELECT count(*) FROM gov_cash_programs",
    "programas vigentes": (
        "SELECT count(*) FROM gov_cash_programs WHERE estado = 'VIGENTE'"
    ),
    "programas cerrados": (
        "SELECT count(*) FROM gov_cash_programs WHERE estado = 'CERRADO'"
    ),
    "versiones": "SELECT count(*) FROM gov_cash_program_versions",
    "declaraciones": "SELECT count(*) FROM gov_cash_program_declarations",
    "líneas": "SELECT count(*) FROM gov_cash_program_lines",
    "rubros": "SELECT count(*) FROM gov_cash_items",
}

CHECKS: list[tuple[str, str, str]] = [
    (
        "K1",
        "versión de otra empresa que su programa",
        "SELECT count(*) FROM gov_cash_program_versions v "
        "JOIN gov_cash_programs p ON p.id = v.program_id "
        "WHERE v.company_id <> p.company_id",
    ),
    (
        "K2",
        "declaración de otra empresa que su programa",
        "SELECT count(*) FROM gov_cash_program_declarations d "
        "JOIN gov_cash_programs p ON p.id = d.program_id "
        "WHERE d.company_id <> p.company_id",
    ),
    (
        "K3",
        "declaración con cuenta de otra empresa",
        "SELECT count(*) FROM gov_cash_program_declarations d "
        "JOIN gov_bank_accounts c ON c.id = d.account_id "
        "WHERE c.company_id <> d.company_id",
    ),
    (
        "K4",
        "declaración con cuenta de otra moneda que el programa",
        "SELECT count(*) FROM gov_cash_program_declarations d "
        "JOIN gov_cash_programs p ON p.id = d.program_id "
        "JOIN gov_bank_accounts c ON c.id = d.account_id "
        "WHERE c.moneda <> p.moneda",
    ),
    (
        "K5",
        "línea de otra empresa que su versión",
        "SELECT count(*) FROM gov_cash_program_lines l "
        "JOIN gov_cash_program_versions v ON v.id = l.version_id "
        "WHERE l.company_id <> v.company_id",
    ),
    (
        "K6",
        "línea con rubro de otra empresa",
        "SELECT count(*) FROM gov_cash_program_lines l "
        "JOIN gov_cash_items i ON i.id = l.item_id "
        "WHERE i.company_id <> l.company_id",
    ),
    (
        "K7",
        "línea con mes anterior al mes inicial del programa",
        "SELECT count(*) FROM gov_cash_program_lines l "
        "JOIN gov_cash_program_versions v ON v.id = l.version_id "
        "JOIN gov_cash_programs p ON p.id = v.program_id "
        "WHERE l.mes < p.mes_inicial",
    ),
    (
        "K8",
        "programa vigente sin exactamente una versión vigente",
        "SELECT count(*) FROM gov_cash_programs p "
        "WHERE p.estado = 'VIGENTE' AND ("
        "SELECT count(*) FROM gov_cash_program_versions v "
        "WHERE v.program_id = p.id AND v.estado = 'VIGENTE') <> 1",
    ),
    (
        "K9",
        "programa con más de una versión borrador",
        "SELECT count(*) FROM gov_cash_programs p "
        "WHERE ("
        "SELECT count(*) FROM gov_cash_program_versions v "
        "WHERE v.program_id = p.id AND v.estado = 'BORRADOR') > 1",
    ),
    (
        "K10",
        "programa cerrado sin datos de cierre o con versión vigente o borrador",
        "SELECT count(*) FROM gov_cash_programs p "
        "WHERE p.estado = 'CERRADO' AND ("
        "p.cerrado_por IS NULL"
        " OR p.cerrado_en IS NULL"
        " OR p.motivo_cierre IS NULL"
        " OR EXISTS ("
        "SELECT 1 FROM gov_cash_program_versions v "
        "WHERE v.program_id = p.id AND v.estado IN ('VIGENTE', 'BORRADOR')))",
    ),
    (
        "K11",
        "versión vigente o cerrada sin activada_por o activada_en",
        "SELECT count(*) FROM gov_cash_program_versions v "
        "WHERE v.estado IN ('VIGENTE', 'CERRADA') "
        "AND (v.activada_por IS NULL OR v.activada_en IS NULL)",
    ),
    (
        "K12",
        "historia con version_numero sin versión en su programa",
        "SELECT count(*) FROM gov_cash_program_history h "
        "WHERE NOT EXISTS ("
        "SELECT 1 FROM gov_cash_program_versions v "
        "WHERE v.program_id = h.program_id AND v.numero = h.version_numero)",
    ),
]
