"""Controles de integridad posteriores a la E2E para ORG-06 (identidad y cuentas).

Cada consulta devuelve el número de violaciones en toda la base.
"""

GRUPO = "ORG-06"

INFO: dict[str, str] = {
    "vinculos": "SELECT count(*) FROM gov_user_official_links",
    "vinculos activos": (
        "SELECT count(*) FROM gov_user_official_links WHERE status = 'ACTIVO'"
    ),
    "vinculos cerrados": (
        "SELECT count(*) FROM gov_user_official_links WHERE status = 'CERRADO'"
    ),
    "vinculos revocados": (
        "SELECT count(*) FROM gov_user_official_links WHERE status = 'REVOCADO'"
    ),
    "eventos de historia": "SELECT count(*) FROM gov_user_official_link_history",
    "categorias": "SELECT count(*) FROM gov_role_categories",
    "politicas con exigencia activa": (
        "SELECT count(*) FROM gov_identity_policies WHERE exige_identidad = true"
    ),
}

CHECKS: list[tuple[str, str, str]] = [
    (
        "ID1",
        "cuenta de otro tenant",
        "SELECT count(*) FROM gov_user_official_links l "
        "JOIN users u ON u.id = l.user_id "
        "JOIN companies c ON c.id = l.company_id "
        "WHERE u.tenant_id <> c.tenant_id",
    ),
    (
        "ID2",
        "funcionario de otra empresa",
        "SELECT count(*) FROM gov_user_official_links l "
        "JOIN gov_officials o ON o.id = l.official_id "
        "WHERE l.company_id <> o.company_id",
    ),
    (
        "ID3",
        "solape por cuenta",
        "SELECT count(*) FROM gov_user_official_links a "
        "JOIN gov_user_official_links b ON a.user_id = b.user_id "
        "AND a.company_id = b.company_id AND a.id < b.id "
        "AND a.status = 'ACTIVO' AND b.status = 'ACTIVO' "
        "AND daterange(a.desde, COALESCE(a.fin_efectivo, a.hasta), '[]') "
        "&& daterange(b.desde, COALESCE(b.fin_efectivo, b.hasta), '[]')",
    ),
    (
        "ID4",
        "solape por funcionario",
        "SELECT count(*) FROM gov_user_official_links a "
        "JOIN gov_user_official_links b ON a.official_id = b.official_id "
        "AND a.company_id = b.company_id AND a.id < b.id "
        "AND a.status = 'ACTIVO' AND b.status = 'ACTIVO' "
        "AND daterange(a.desde, COALESCE(a.fin_efectivo, a.hasta), '[]') "
        "&& daterange(b.desde, COALESCE(b.fin_efectivo, b.hasta), '[]')",
    ),
    (
        "ID5",
        "ACTIVO sin activated_at o sin activated_by",
        "SELECT count(*) FROM gov_user_official_links "
        "WHERE status = 'ACTIVO' AND (activated_at IS NULL OR activated_by IS NULL)",
    ),
    (
        "ID6",
        "CERRADO o REVOCADO sin fin_efectivo, sin ended_by o sin motivo_fin",
        "SELECT count(*) FROM gov_user_official_links "
        "WHERE status IN ('CERRADO','REVOCADO') AND ("
        "fin_efectivo IS NULL OR ended_by IS NULL OR motivo_fin IS NULL"
        ")",
    ),
    (
        "ID7",
        "fin_efectivo anterior a desde",
        "SELECT count(*) FROM gov_user_official_links "
        "WHERE fin_efectivo IS NOT NULL AND fin_efectivo < desde",
    ),
    (
        "ID8",
        "maker-checker roto: activated_by = created_by",
        "SELECT count(*) FROM gov_user_official_links "
        "WHERE activated_by = created_by",
    ),
    (
        "ID9",
        "historia de otra empresa",
        "SELECT count(*) FROM gov_user_official_link_history h "
        "JOIN gov_user_official_links l ON l.id = h.link_id "
        "WHERE h.company_id <> l.company_id",
    ),
    (
        "ID10",
        "vínculo no BORRADOR sin evento CREADO en su historia",
        "SELECT count(*) FROM gov_user_official_links l "
        "WHERE l.status <> 'BORRADOR' AND NOT EXISTS ("
        "SELECT 1 FROM gov_user_official_link_history h "
        "WHERE h.link_id = l.id AND h.tipo = 'CREADO'"
        ")",
    ),
    (
        "ID11",
        "vínculo ACTIVO, CERRADO o REVOCADO sin evento ACTIVADO",
        "SELECT count(*) FROM gov_user_official_links l "
        "WHERE l.status IN ('ACTIVO','CERRADO','REVOCADO') AND NOT EXISTS ("
        "SELECT 1 FROM gov_user_official_link_history h "
        "WHERE h.link_id = l.id AND h.tipo = 'ACTIVADO'"
        ")",
    ),
    (
        "ID12",
        "CERRADO sin evento CERRADO o REVOCADO sin evento REVOCADO",
        "SELECT count(*) FROM gov_user_official_links l "
        "WHERE (l.status = 'CERRADO' AND NOT EXISTS ("
        "SELECT 1 FROM gov_user_official_link_history h "
        "WHERE h.link_id = l.id AND h.tipo = 'CERRADO'"
        ")) OR (l.status = 'REVOCADO' AND NOT EXISTS ("
        "SELECT 1 FROM gov_user_official_link_history h "
        "WHERE h.link_id = l.id AND h.tipo = 'REVOCADO'"
        "))",
    ),
    (
        "ID13",
        "categoría con rol de otro tenant",
        "SELECT count(*) FROM gov_role_categories c "
        "JOIN roles r ON r.id = c.role_id "
        "JOIN companies comp ON comp.id = c.company_id "
        "WHERE r.tenant_id IS NOT NULL AND r.tenant_id <> comp.tenant_id",
    ),
    (
        "ID14",
        "categorías ACTIVA solapadas del mismo role_id, categoria y empresa",
        "SELECT count(*) FROM gov_role_categories a "
        "JOIN gov_role_categories b ON a.role_id = b.role_id "
        "AND a.categoria = b.categoria AND a.company_id = b.company_id "
        "AND a.id < b.id AND a.status = 'ACTIVA' AND b.status = 'ACTIVA' "
        "AND daterange(a.desde, a.hasta, '[]') && daterange(b.desde, b.hasta, '[]')",
    ),
    (
        "ID15",
        "categoría RETIRADA sin hasta",
        "SELECT count(*) FROM gov_role_categories "
        "WHERE status = 'RETIRADA' AND hasta IS NULL",
    ),
    (
        "ID16",
        "historia de categoría o de política de otra empresa",
        "SELECT count(*) FROM ("
        "SELECT h.id FROM gov_role_category_history h "
        "JOIN gov_role_categories c ON c.id = h.category_id "
        "WHERE h.company_id <> c.company_id "
        "UNION ALL "
        "SELECT h.id FROM gov_identity_policy_history h "
        "JOIN gov_identity_policies p ON p.id = h.policy_id "
        "WHERE h.company_id <> p.company_id"
        ") t",
    ),
    (
        "ID17",
        "autoridad sin vínculo",
        "SELECT count(*) FROM audit_events ae "
        "JOIN gov_identity_policies p ON p.company_id = ae.company_id "
        "WHERE ae.action = 'GOV_ACT_ISSUED' "
        "AND p.exige_identidad = true AND p.updated_at <= ae.event_time "
        "AND NOT EXISTS ("
        "SELECT 1 FROM gov_user_official_links l "
        "WHERE l.user_id = ae.user_id AND l.company_id = ae.company_id "
        "AND l.status IN ('ACTIVO','CERRADO','REVOCADO') "
        "AND l.desde <= ae.event_time::date "
        "AND COALESCE(l.fin_efectivo, l.hasta, 'infinity'::date) >= ae.event_time::date"
        ")",
    ),
    (
        "ID18",
        "conflicto SoD sin resolver",
        "SELECT count(*) FROM gov_user_official_links l "
        "JOIN gov_sod_rules r ON r.company_id = l.company_id "
        "WHERE l.status = 'ACTIVO' AND r.proceso = 'ORG-06' "
        "AND r.estado = 'VIGENTE' "
        "AND r.vigente_desde <= current_date "
        "AND (r.vigente_hasta IS NULL OR r.vigente_hasta >= current_date) "
        "AND EXISTS ("
        "SELECT 1 FROM user_roles ur "
        "JOIN gov_role_categories c ON c.role_id = ur.role_id "
        "AND c.company_id = l.company_id AND c.status = 'ACTIVA' "
        "AND c.desde <= current_date AND (c.hasta IS NULL OR c.hasta >= current_date) "
        "WHERE ur.user_id = l.user_id "
        "AND (ur.company_id IS NULL OR ur.company_id = l.company_id) "
        "AND 'ORG06_CAT_' || c.categoria = r.accion_a"
        ") AND EXISTS ("
        "SELECT 1 FROM user_roles ur "
        "JOIN gov_role_categories c ON c.role_id = ur.role_id "
        "AND c.company_id = l.company_id AND c.status = 'ACTIVA' "
        "AND c.desde <= current_date AND (c.hasta IS NULL OR c.hasta >= current_date) "
        "WHERE ur.user_id = l.user_id "
        "AND (ur.company_id IS NULL OR ur.company_id = l.company_id) "
        "AND 'ORG06_CAT_' || c.categoria = r.accion_b"
        ")",
    ),
]
