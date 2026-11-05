"""Controles de integridad posteriores a la E2E para TRE-01 (cuentas bancarias públicas).

Cada consulta devuelve el número de violaciones en toda la base.
"""

GRUPO = "TRE-01"

INFO: dict[str, str] = {
    "bancos": "SELECT count(*) FROM gov_banks",
    "cuentas": "SELECT count(*) FROM gov_bank_accounts",
    "cuentas vigentes": "SELECT count(*) FROM gov_bank_accounts WHERE estado = 'VIGENTE'",
    "cuentas cerradas": "SELECT count(*) FROM gov_bank_accounts WHERE estado = 'CERRADA'",
    "autorizaciones": "SELECT count(*) FROM gov_bank_account_authorizations",
    "autorizaciones en vigor": (
        "SELECT count(*) FROM gov_bank_account_authorizations WHERE vigente_hasta IS NULL"
    ),
}

CHECKS: list[tuple[str, str, str]] = [
    (
        "T1",
        "cuenta con banco de otra empresa",
        "SELECT count(*) FROM gov_bank_accounts c "
        "JOIN gov_banks b ON b.id = c.bank_id "
        "WHERE b.company_id <> c.company_id",
    ),
    (
        "T2",
        "cuenta con acto de otra empresa",
        "SELECT count(*) FROM gov_bank_accounts c "
        "JOIN gov_acts a ON a.id = c.acto_id "
        "WHERE a.company_id <> c.company_id",
    ),
    (
        "T3",
        "autorización de otra empresa que su cuenta",
        "SELECT count(*) FROM gov_bank_account_authorizations z "
        "JOIN gov_bank_accounts c ON c.id = z.account_id "
        "WHERE z.company_id <> c.company_id",
    ),
    (
        "T4",
        "autorización con cargo de otra empresa",
        "SELECT count(*) FROM gov_bank_account_authorizations z "
        "JOIN gov_positions p ON p.id = z.position_id "
        "WHERE p.company_id <> z.company_id",
    ),
    (
        "T5",
        "autorización con acto de alta de otra empresa",
        "SELECT count(*) FROM gov_bank_account_authorizations z "
        "JOIN gov_acts a ON a.id = z.acto_alta_id "
        "WHERE a.company_id <> z.company_id",
    ),
    (
        "T6",
        "autorización con acto de fin de otra empresa",
        "SELECT count(*) FROM gov_bank_account_authorizations z "
        "JOIN gov_acts a ON a.id = z.acto_fin_id "
        "WHERE a.company_id <> z.company_id",
    ),
    (
        "T7",
        "historia de otra empresa que su cuenta",
        "SELECT count(*) FROM gov_bank_account_history h "
        "JOIN gov_bank_accounts c ON c.id = h.account_id "
        "WHERE h.company_id <> c.company_id",
    ),
    (
        "T8",
        "número que no empieza por el código del banco",
        "SELECT count(*) FROM gov_bank_accounts c "
        "JOIN gov_banks b ON b.id = c.bank_id "
        "WHERE left(c.numero, 4) <> b.codigo",
    ),
    (
        "T9",
        "número que no son 20 dígitos",
        "SELECT count(*) FROM gov_bank_accounts WHERE numero !~ '^[0-9]{20}$'",
    ),
    (
        "T10",
        "dos autorizaciones en vigor del mismo cargo en una cuenta",
        "SELECT count(*) FROM ("
        "SELECT account_id, position_id FROM gov_bank_account_authorizations "
        "WHERE vigente_hasta IS NULL GROUP BY account_id, position_id "
        "HAVING count(*) > 1"
        ") d",
    ),
    (
        "T11",
        "cuenta cerrada con autorizaciones en vigor",
        "SELECT count(*) FROM gov_bank_account_authorizations z "
        "JOIN gov_bank_accounts c ON c.id = z.account_id "
        "WHERE c.estado = 'CERRADA' AND z.vigente_hasta IS NULL",
    ),
    (
        "T12",
        "cuenta sin historia CREADA",
        "SELECT count(*) FROM gov_bank_accounts c "
        "WHERE NOT EXISTS ("
        "SELECT 1 FROM gov_bank_account_history h "
        "WHERE h.account_id = c.id AND h.tipo = 'CREADA'"
        ")",
    ),
    (
        "T13",
        "cuenta activada sin evento de auditoría",
        "SELECT count(*) FROM gov_bank_accounts c "
        "WHERE c.activada_en IS NOT NULL AND NOT EXISTS ("
        "SELECT 1 FROM audit_events e "
        "WHERE e.action = 'GOV_BANK_ACCOUNT_ACTIVATED' AND e.entity_id::text = c.id"
        ")",
    ),
    (
        "T14",
        "número completo en la auditoría",
        "SELECT count(*) FROM audit_events e "
        "JOIN gov_bank_accounts c ON e.entity_id::text = c.id "
        "WHERE e.entity_type = 'GovernmentBankAccount' AND ("
        "coalesce(e.after::text, '') LIKE '%' || c.numero || '%' OR "
        "coalesce(e.before::text, '') LIKE '%' || c.numero || '%' OR "
        "coalesce(e.reason, '') LIKE '%' || c.numero || '%'"
        ")",
    ),
    (
        "T15",
        "número completo en la historia",
        "SELECT count(*) FROM gov_bank_account_history h "
        "JOIN gov_bank_accounts c ON c.id = h.account_id "
        "WHERE coalesce(h.detalle::text, '') LIKE '%' || c.numero || '%'",
    ),
    (
        "T16",
        "fin de autorización anterior al alta",
        "SELECT count(*) FROM gov_bank_account_authorizations "
        "WHERE vigente_hasta < vigente_desde",
    ),
    (
        "T17",
        "permisos gobierno_cuentas sin FUNCIONAL_COMPLETO",
        "SELECT 3 - count(DISTINCT p.action) FROM permissions p "
        "JOIN role_permissions rp ON rp.permission_id = p.id "
        "JOIN roles r ON r.id = rp.role_id "
        "WHERE p.resource = 'gobierno_cuentas' "
        "AND p.action IN ('view', 'manage', 'activate') "
        "AND r.code = 'FUNCIONAL_COMPLETO' AND r.company_id IS NULL",
    ),
]
