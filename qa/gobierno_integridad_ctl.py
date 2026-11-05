"""
Controles de integridad posteriores a la E2E de Gobierno.

Origen: OBS-CERT-GOV-01.
Los controles de integridad posteriores a la E2E de Gobierno vivían fuera
del repositorio y se perdieron. Se reconstruyen versionados en `qa/`.

Cada control es una consulta SQL de PostgreSQL de SOLO LECTURA que devuelve
UN entero: el número de violaciones (0 = sano). Se ejecutan sobre la base de
una corrida E2E (todas las empresas a la vez), por eso cada control compara
empresa y relaciones en toda la base.
"""

GRUPO = "CTL-04/CTL-06/DOC-08/CTL-01"

INFO: dict[str, str] = {
    "muestras": "SELECT count(*) FROM gov_audit_samples",
    "partidas": "SELECT count(*) FROM gov_audit_sample_items",
    "hallazgos": "SELECT count(*) FROM gov_findings",
    "hallazgos cerrados": "SELECT count(*) FROM gov_findings WHERE estado = 'CERRADO'",
    "acciones": "SELECT count(*) FROM gov_corrective_actions",
    "avances": "SELECT count(*) FROM gov_corrective_action_progress",
    "paquetes": "SELECT count(*) FROM gov_audit_packages",
    "verificaciones": "SELECT count(*) FROM gov_audit_package_verifications",
    "reglas SoD": "SELECT count(*) FROM gov_sod_rules",
    "reglas SoD vigentes": "SELECT count(*) FROM gov_sod_rules WHERE estado = 'VIGENTE'",
    "conflictos SoD": (
        "SELECT count(*) FROM audit_events "
        "WHERE action = 'GOV_SOD_CONFLICT_BLOCKED' "
        "AND entity_type = 'GovernmentSoDRule'"
    ),
}

CHECKS: list[tuple[str, str, str]] = [
    (
        "M1",
        "partida con empresa distinta de su muestra",
        "SELECT count(*) FROM gov_audit_sample_items i JOIN gov_audit_samples s ON s.id = i.sample_id WHERE i.company_id <> s.company_id",
    ),
    (
        "M2",
        "partida que referencia un evento de otra empresa",
        "SELECT count(*) FROM gov_audit_sample_items i JOIN audit_events e ON e.id = i.audit_event_id WHERE i.company_id <> e.company_id",
    ),
    (
        "M3",
        "partida que referencia un evento ajeno a Gobierno",
        "SELECT count(*) FROM gov_audit_sample_items i JOIN audit_events e ON e.id = i.audit_event_id WHERE e.action NOT LIKE 'GOV\\_%' ESCAPE '\\'",
    ),
    (
        "M4",
        "tamaño distinto del número de partidas",
        "SELECT count(*) FROM gov_audit_samples s WHERE s.tamano <> (SELECT count(*) FROM gov_audit_sample_items i WHERE i.sample_id = s.id)",
    ),
    (
        "M5",
        "orden de partidas no correlativo 1..n",
        "SELECT count(*) FROM (SELECT sample_id, min(orden) AS min_orden, max(orden) AS max_orden, count(*) AS total, count(DISTINCT orden) AS distintos FROM gov_audit_sample_items GROUP BY sample_id) t WHERE t.min_orden <> 1 OR t.max_orden <> t.total OR t.distintos <> t.total",
    ),
    (
        "M6",
        "semilla incoherente con el método",
        "SELECT count(*) FROM gov_audit_samples WHERE (metodo = 'ALEATORIA') <> (semilla IS NOT NULL)",
    ),
    (
        "M7",
        "muestra sin auditoría de registro",
        "SELECT count(*) FROM gov_audit_samples s WHERE NOT EXISTS (SELECT 1 FROM audit_events e WHERE e.action = 'GOV_AUDIT_SAMPLE_CREATED' AND e.entity_type = 'GovernmentAuditSample' AND e.entity_id = CAST(s.id AS text) AND e.company_id = s.company_id)",
    ),
    (
        "M8",
        "muestra con tamaño mayor que su población",
        "SELECT count(*) FROM gov_audit_samples WHERE tamano > poblacion",
    ),
    (
        "H1",
        "hallazgo MUESTRA cuya muestra es de otra empresa",
        "SELECT count(*) FROM gov_findings f JOIN gov_audit_samples s ON s.id = f.sample_id WHERE f.company_id <> s.company_id",
    ),
    (
        "H2",
        "partida del hallazgo que no es partida de su muestra",
        "SELECT count(*) FROM gov_finding_events fe JOIN gov_findings f ON f.id = fe.finding_id WHERE f.sample_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM gov_audit_sample_items i WHERE i.sample_id = f.sample_id AND i.audit_event_id = fe.audit_event_id)",
    ),
    (
        "H3",
        "acción con cargo de otra empresa",
        "SELECT count(*) FROM gov_corrective_actions a JOIN gov_positions p ON p.id = a.position_id WHERE a.company_id <> p.company_id",
    ),
    (
        "H4",
        "acción con recomendación de otro hallazgo",
        "SELECT count(*) FROM gov_corrective_actions a JOIN gov_finding_recommendations r ON r.id = a.recommendation_id WHERE a.finding_id <> r.finding_id",
    ),
    (
        "H5",
        "avance con documento de otra empresa",
        "SELECT count(*) FROM gov_corrective_action_progress p JOIN documents d ON d.id = p.document_id WHERE p.company_id <> d.company_id",
    ),
    (
        "H6",
        "hallazgo CERRADO con acciones no COMPLETADA",
        "SELECT count(*) FROM gov_findings f WHERE f.estado = 'CERRADO' AND EXISTS (SELECT 1 FROM gov_corrective_actions a WHERE a.finding_id = f.id AND a.estado <> 'COMPLETADA')",
    ),
    (
        "H7",
        "hallazgo CERRADO sin verificador o verificado por quien presentó",
        "SELECT count(*) FROM gov_findings f WHERE f.estado = 'CERRADO' AND (f.verificado_por IS NULL OR f.verificado_por = f.presentado_por)",
    ),
    (
        "H8",
        "hallazgo CERRADO verificado por el autor de un avance",
        "SELECT count(DISTINCT f.id) FROM gov_findings f JOIN gov_corrective_actions a ON a.finding_id = f.id JOIN gov_corrective_action_progress p ON p.action_id = a.id WHERE f.estado = 'CERRADO' AND p.created_by = f.verificado_por",
    ),
    (
        "H9",
        "acción COMPLETADA sin documento ACTIVE vinculado",
        "SELECT count(*) FROM gov_corrective_actions a WHERE a.estado = 'COMPLETADA' AND NOT EXISTS (SELECT 1 FROM document_links dl JOIN documents d ON d.id = dl.document_id WHERE dl.resource_type = 'GovernmentCorrectiveAction' AND dl.resource_id = CAST(a.id AS text) AND d.status = 'ACTIVE')",
    ),
    (
        "H10",
        "hallazgo sin auditoría de alta",
        "SELECT count(*) FROM gov_findings f WHERE NOT EXISTS (SELECT 1 FROM audit_events e WHERE e.action = 'GOV_FINDING_CREATED' AND e.entity_type = 'GovernmentFinding' AND e.entity_id = CAST(f.id AS text) AND e.company_id = f.company_id)",
    ),
    (
        "H11",
        "hallazgo sin fila de historia CREADO",
        "SELECT count(*) FROM gov_findings f WHERE NOT EXISTS (SELECT 1 FROM gov_finding_history h WHERE h.finding_id = f.id AND h.tipo = 'CREADO')",
    ),
    (
        "H12",
        "permisos gobierno_hallazgos sin FUNCIONAL_COMPLETO",
        "SELECT 3 - count(DISTINCT p.action) FROM permissions p JOIN role_permissions rp ON rp.permission_id = p.id JOIN roles r ON r.id = rp.role_id WHERE p.resource = 'gobierno_hallazgos' AND p.action IN ('view', 'manage', 'verify') AND r.code = 'FUNCIONAL_COMPLETO' AND r.company_id IS NULL",
    ),
    (
        "H13",
        "porcentaje de la acción distinto del último avance",
        "SELECT count(*) FROM gov_corrective_actions a WHERE a.porcentaje <> (SELECT p2.porcentaje FROM gov_corrective_action_progress p2 WHERE p2.action_id = a.id ORDER BY p2.created_at DESC LIMIT 1) AND EXISTS (SELECT 1 FROM gov_corrective_action_progress p3 WHERE p3.action_id = a.id)",
    ),
    (
        "P1",
        "paquete con muestra de otra empresa",
        "SELECT count(*) FROM gov_audit_packages p JOIN gov_audit_samples s ON s.id = p.sample_id WHERE p.company_id <> s.company_id",
    ),
    (
        "P2",
        "verificación de un paquete de otra empresa",
        "SELECT count(*) FROM gov_audit_package_verifications v JOIN gov_audit_packages p ON p.id = v.package_id WHERE v.company_id <> p.company_id",
    ),
    (
        "P3",
        "paquete sin auditoría de generación",
        "SELECT count(*) FROM gov_audit_packages p WHERE NOT EXISTS (SELECT 1 FROM audit_events e WHERE e.action = 'GOV_AUDIT_PACKAGE_GENERATED' AND e.entity_type = 'GovernmentAuditPackage' AND e.entity_id = CAST(p.id AS text) AND e.company_id = p.company_id)",
    ),
    (
        "P4",
        "paquete cuyo manifiesto no lleva su código",
        "SELECT count(*) FROM gov_audit_packages p WHERE (p.manifiesto::json)->'paquete'->>'codigo' IS DISTINCT FROM p.codigo",
    ),
    (
        "P5",
        "paquete cuyo manifiesto no cuadra con sus contadores",
        "SELECT count(*) FROM gov_audit_packages p WHERE ((p.manifiesto::json)->'totales'->>'eventos')::bigint IS DISTINCT FROM p.eventos OR ((p.manifiesto::json)->'totales'->>'documentos_incluidos')::bigint IS DISTINCT FROM p.documentos_incluidos OR ((p.manifiesto::json)->'totales'->>'documentos_excluidos')::bigint IS DISTINCT FROM p.documentos_excluidos OR ((p.manifiesto::json)->'totales'->>'hallazgos')::bigint IS DISTINCT FROM p.hallazgos OR ((p.manifiesto::json)->'totales'->>'archivos')::bigint IS DISTINCT FROM p.archivos",
    ),
    (
        "P6",
        "paquete con más eventos que partidas tiene su muestra",
        "SELECT count(*) FROM gov_audit_packages p JOIN gov_audit_samples s ON s.id = p.sample_id WHERE p.eventos > s.tamano",
    ),
    (
        "P7",
        "verificación sin auditoría",
        "SELECT count(*) FROM gov_audit_package_verifications v WHERE NOT EXISTS (SELECT 1 FROM audit_events e WHERE (e.action = 'GOV_AUDIT_PACKAGE_VERIFIED' OR e.action = 'GOV_AUDIT_PACKAGE_VERIFICATION_FAILED') AND e.entity_id = CAST(v.package_id AS text) AND e.company_id = v.company_id AND e.event_time >= v.created_at - interval '5 minutes')",
    ),
    (
        "P8",
        "verificación VALIDO con motivos",
        "SELECT count(*) FROM gov_audit_package_verifications v WHERE v.resultado = 'VALIDO' AND json_array_length(v.motivos::json) <> 0",
    ),
    (
        "S1",
        "historia de regla con empresa distinta de su regla",
        "SELECT count(*) FROM gov_sod_rule_history h JOIN gov_sod_rules r ON r.id = h.rule_id WHERE h.company_id <> r.company_id",
    ),
    (
        "S2",
        "regla VIGENTE o CERRADA sin activación registrada",
        "SELECT count(*) FROM gov_sod_rules r WHERE r.estado IN ('VIGENTE', 'CERRADA') AND (r.activada_por IS NULL OR r.activada_en IS NULL)",
    ),
    (
        "S3",
        "regla CERRADA sin quién, cuándo o motivo",
        "SELECT count(*) FROM gov_sod_rules r WHERE r.estado = 'CERRADA' AND (r.cerrada_por IS NULL OR r.cerrada_en IS NULL OR r.motivo_cierre IS NULL)",
    ),
    (
        "S4",
        "regla sin auditoría de alta",
        "SELECT count(*) FROM gov_sod_rules r WHERE NOT EXISTS (SELECT 1 FROM audit_events e WHERE e.action = 'GOV_SOD_RULE_CREATED' AND e.entity_type = 'GovernmentSoDRule' AND e.entity_id = CAST(r.id AS text) AND e.company_id = r.company_id)",
    ),
    (
        "S5",
        "regla sin fila de historia CREADA",
        "SELECT count(*) FROM gov_sod_rules r WHERE NOT EXISTS (SELECT 1 FROM gov_sod_rule_history h WHERE h.rule_id = r.id AND h.tipo = 'CREADA')",
    ),
    (
        "S6",
        "conflicto bloqueado cuya regla no es de su empresa",
        "SELECT count(*) FROM audit_events e JOIN gov_sod_rules r ON r.id = e.entity_id WHERE e.action = 'GOV_SOD_CONFLICT_BLOCKED' AND e.entity_type = 'GovernmentSoDRule' AND e.company_id <> r.company_id",
    ),
    (
        "S7",
        "conflicto bloqueado sobre un acto u hallazgo de otra empresa",
        "SELECT count(*) FROM audit_events e WHERE e.action = 'GOV_SOD_CONFLICT_BLOCKED' AND e.entity_type = 'GovernmentSoDRule' AND ( ((e.after::json)->>'objeto_tipo' = 'GovernmentAct' AND NOT EXISTS (SELECT 1 FROM gov_acts a WHERE a.id = (e.after::json)->>'objeto_id' AND a.company_id = e.company_id)) OR ((e.after::json)->>'objeto_tipo' = 'GovernmentFinding' AND NOT EXISTS (SELECT 1 FROM gov_findings f WHERE f.id = (e.after::json)->>'objeto_id' AND f.company_id = e.company_id)) )",
    ),
    (
        "S8",
        "dos reglas VIGENTES con el mismo par en la misma empresa y proceso",
        "SELECT count(*) FROM gov_sod_rules a JOIN gov_sod_rules b ON a.estado = 'VIGENTE' AND b.estado = 'VIGENTE' AND a.company_id = b.company_id AND a.proceso = b.proceso AND a.id < b.id AND ((a.accion_a = b.accion_a AND a.accion_b = b.accion_b) OR (a.bidireccional OR b.bidireccional) AND a.accion_a = b.accion_b AND a.accion_b = b.accion_a)",
    ),
    (
        "S9",
        "permisos gobierno_sod sin FUNCIONAL_COMPLETO",
        "SELECT 3 - count(DISTINCT p.action) FROM permissions p JOIN role_permissions rp ON rp.permission_id = p.id JOIN roles r ON r.id = rp.role_id WHERE p.resource = 'gobierno_sod' AND p.action IN ('view', 'manage', 'activate') AND r.code = 'FUNCIONAL_COMPLETO' AND r.company_id IS NULL",
    ),
]
