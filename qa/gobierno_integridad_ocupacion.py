"""Controles de integridad posteriores a la E2E para ORG-04 (ocupación de cargos).

Cada consulta devuelve el número de violaciones en toda la base.
"""

GRUPO = "ORG-04"

INFO: dict[str, str] = {
    "asignaciones": "SELECT count(*) FROM gov_assignments",
    "activas": "SELECT count(*) FROM gov_assignments WHERE status = 'ACTIVO'",
    "revocadas": "SELECT count(*) FROM gov_assignments WHERE status = 'REVOCADO'",
    "finalizadas": "SELECT count(*) FROM gov_assignments WHERE status = 'FINALIZADO'",
    "funcionarios": "SELECT count(*) FROM gov_officials",
    "competencias delegadas": "SELECT count(*) FROM gov_assignment_competencies",
    "eventos de historia": "SELECT count(*) FROM gov_assignment_history",
}

CHECKS: list[tuple[str, str, str]] = [
    (
        "OC1",
        "funcionario de otra empresa",
        "SELECT count(*) FROM gov_assignments a "
        "JOIN gov_officials o ON o.id = a.official_id "
        "WHERE a.company_id <> o.company_id",
    ),
    (
        "OC2",
        "cargo de otra empresa",
        "SELECT count(*) FROM gov_assignments a "
        "JOIN gov_positions p ON p.id = a.position_id "
        "WHERE a.company_id <> p.company_id",
    ),
    (
        "OC3",
        "acto de otra empresa",
        "SELECT count(*) FROM gov_assignments a "
        "JOIN gov_acts act ON act.id = a.act_id "
        "WHERE a.company_id <> act.company_id",
    ),
    (
        "OC4",
        "cargo de origen de otra empresa",
        "SELECT count(*) FROM gov_assignments a "
        "JOIN gov_positions p ON p.id = a.cargo_origen_id "
        "WHERE a.company_id <> p.company_id",
    ),
    (
        "OC5",
        "acto de revocación de otra empresa",
        "SELECT count(*) FROM gov_assignments a "
        "JOIN gov_acts act ON act.id = a.revocation_act_id "
        "WHERE a.company_id <> act.company_id",
    ),
    (
        "OC6",
        "ocupación solapada",
        "SELECT count(*) FROM gov_assignments a "
        "JOIN gov_assignments b ON a.position_id = b.position_id "
        "AND a.grupo = b.grupo AND a.grupo IN ('TITULARIDAD','TEMPORAL') "
        "AND a.id < b.id AND a.status = 'ACTIVO' AND b.status = 'ACTIVO' "
        "AND daterange(a.desde, COALESCE(a.fin_efectivo, a.hasta), '[]') "
        "&& daterange(b.desde, COALESCE(b.fin_efectivo, b.hasta), '[]')",
    ),
    (
        "OC7",
        "delegación solapada",
        "SELECT count(*) FROM gov_assignments a "
        "JOIN gov_assignments b ON a.position_id = b.position_id "
        "AND a.official_id = b.official_id AND a.grupo = 'DELEGACION' "
        "AND b.grupo = 'DELEGACION' AND a.id < b.id "
        "AND a.status = 'ACTIVO' AND b.status = 'ACTIVO' "
        "AND daterange(a.desde, COALESCE(a.fin_efectivo, a.hasta), '[]') "
        "&& daterange(b.desde, COALESCE(b.fin_efectivo, b.hasta), '[]')",
    ),
    (
        "OC8",
        "status='REVOCADO' sin revocation_act_id o sin fin_efectivo",
        "SELECT count(*) FROM gov_assignments a "
        "WHERE a.status = 'REVOCADO' "
        "AND (a.revocation_act_id IS NULL OR a.fin_efectivo IS NULL)",
    ),
    (
        "OC9",
        "asignación no borrador ni descartada con acto sin fecha_eficacia y acto no NULO ni REVOCADO",
        "SELECT count(*) FROM gov_assignments a "
        "JOIN gov_acts act ON act.id = a.act_id "
        "WHERE a.status NOT IN ('BORRADOR','DESCARTADO') "
        "AND act.fecha_eficacia IS NULL "
        "AND act.status NOT IN ('NULO','REVOCADO')",
    ),
    (
        "OC10",
        "no borrador ni descartada con desde anterior a gov_acts.fecha_eficacia",
        "SELECT count(*) FROM gov_assignments a "
        "JOIN gov_acts act ON act.id = a.act_id "
        "WHERE a.status NOT IN ('BORRADOR','DESCARTADO') "
        "AND a.desde < act.fecha_eficacia",
    ),
    (
        "OC11",
        "status='ACTIVO' y gov_positions.valid_to IS NOT NULL y a.desde > valid_to",
        "SELECT count(*) FROM gov_assignments a "
        "JOIN gov_positions p ON p.id = a.position_id "
        "WHERE a.status = 'ACTIVO' AND p.valid_to IS NOT NULL "
        "AND a.desde > p.valid_to",
    ),
    (
        "OC12",
        "sin historia tipo 'CREADA'",
        "SELECT count(*) FROM gov_assignments a "
        "WHERE NOT EXISTS ("
        "SELECT 1 FROM gov_assignment_history h "
        "WHERE h.assignment_id = a.id AND h.tipo = 'CREADA'"
        ")",
    ),
    (
        "OC13",
        "status en ACTIVO, REVOCADO, FINALIZADO sin historia 'ACTIVADA'",
        "SELECT count(*) FROM gov_assignments a "
        "WHERE a.status IN ('ACTIVO','REVOCADO','FINALIZADO') "
        "AND NOT EXISTS ("
        "SELECT 1 FROM gov_assignment_history h "
        "WHERE h.assignment_id = a.id AND h.tipo = 'ACTIVADA'"
        ")",
    ),
    (
        "OC14",
        "REVOCADO sin 'REVOCADA'",
        "SELECT count(*) FROM gov_assignments a "
        "WHERE a.status = 'REVOCADO' AND NOT EXISTS ("
        "SELECT 1 FROM gov_assignment_history h "
        "WHERE h.assignment_id = a.id AND h.tipo = 'REVOCADA'"
        ")",
    ),
    (
        "OC15",
        "FINALIZADO sin 'FINALIZADA'",
        "SELECT count(*) FROM gov_assignments a "
        "WHERE a.status = 'FINALIZADO' AND NOT EXISTS ("
        "SELECT 1 FROM gov_assignment_history h "
        "WHERE h.assignment_id = a.id AND h.tipo = 'FINALIZADA'"
        ")",
    ),
    (
        "OC16",
        "historia de otra empresa que su asignación",
        "SELECT count(*) FROM gov_assignment_history h "
        "JOIN gov_assignments a ON a.id = h.assignment_id "
        "WHERE h.company_id <> a.company_id",
    ),
    (
        "OC17",
        "competencia de otra empresa que su asignación",
        "SELECT count(*) FROM gov_assignment_competencies c "
        "JOIN gov_assignments a ON a.id = c.assignment_id "
        "WHERE c.company_id <> a.company_id",
    ),
    (
        "OC18",
        "grupo='DELEGACION' y status='ACTIVO' sin competencias",
        "SELECT count(*) FROM gov_assignments a "
        "WHERE a.grupo = 'DELEGACION' AND a.status = 'ACTIVO' "
        "AND NOT EXISTS ("
        "SELECT 1 FROM gov_assignment_competencies c "
        "WHERE c.assignment_id = a.id"
        ")",
    ),
    (
        "OC19",
        "activated_by = created_by",
        "SELECT count(*) FROM gov_assignments a "
        "WHERE a.activated_by = a.created_by",
    ),
    (
        "OC20",
        "disparadores de inmutabilidad ausentes",
        "SELECT 5 - count(*) FROM pg_trigger "
        "WHERE tgname IN ("
        "'trg_gov_assignment_history_no_update',"
        "'trg_gov_assignment_history_no_delete',"
        "'trg_gov_official_history_no_update',"
        "'trg_gov_official_history_no_delete',"
        "'trg_gov_assignments_no_delete'"
        ")",
    ),
    (
        "OC21",
        "dos funcionarios con igual (company_id, tipo_documento, numero_documento)",
        "SELECT count(*) FROM ("
        "SELECT company_id, tipo_documento, numero_documento "
        "FROM gov_officials "
        "GROUP BY company_id, tipo_documento, numero_documento "
        "HAVING count(*) > 1"
        ") t",
    ),
    (
        "OC22",
        "status en ACTIVO, REVOCADO, FINALIZADO sin fila audit_events con action='GOV_ASSIGNMENT_ACTIVATED' y entity_id = a.id::text",
        "SELECT count(*) FROM gov_assignments a "
        "WHERE a.status IN ('ACTIVO','REVOCADO','FINALIZADO') "
        "AND NOT EXISTS ("
        "SELECT 1 FROM audit_events ae "
        "WHERE ae.action = 'GOV_ASSIGNMENT_ACTIVATED' "
        "AND ae.entity_id = a.id::text"
        ")",
    ),
]
