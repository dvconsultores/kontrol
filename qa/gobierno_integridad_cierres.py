"""Controles de integridad posteriores a la E2E para CTL-10 (políticas de cierre).

Cada consulta devuelve el número de violaciones en toda la base.
"""

GRUPO = "CTL-10"

INFO: dict[str, str] = {
    "politicas": "SELECT count(*) FROM gov_closure_policies",
    "politicas vigentes": (
        "SELECT count(*) FROM gov_closure_policies WHERE estado = 'VIGENTE'"
    ),
    "politicas retiradas": (
        "SELECT count(*) FROM gov_closure_policies WHERE estado = 'RETIRADA'"
    ),
    "controles": "SELECT count(*) FROM gov_closure_controls",
    "eventos de historia": "SELECT count(*) FROM gov_closure_policy_history",
}

CHECKS: list[tuple[str, str, str]] = [
    (
        "CC1",
        "dos vigentes para la misma empresa y acción",
        "SELECT count(*) FROM ("
        "SELECT company_id, accion_cierre FROM gov_closure_policies "
        "WHERE estado = 'VIGENTE' "
        "GROUP BY company_id, accion_cierre HAVING count(*) > 1"
        ") t",
    ),
    (
        "CC2",
        "control de otra empresa que su política",
        "SELECT count(*) FROM gov_closure_controls c "
        "JOIN gov_closure_policies p ON p.id = c.policy_id "
        "WHERE c.company_id <> p.company_id",
    ),
    (
        "CC3",
        "historia de otra empresa que su política",
        "SELECT count(*) FROM gov_closure_policy_history h "
        "JOIN gov_closure_policies p ON p.id = h.policy_id "
        "WHERE h.company_id <> p.company_id",
    ),
    (
        "CC4",
        "política vigente sin controles",
        "SELECT count(*) FROM gov_closure_policies p "
        "WHERE p.estado = 'VIGENTE' AND NOT EXISTS ("
        "SELECT 1 FROM gov_closure_controls c WHERE c.policy_id = p.id"
        ")",
    ),
    (
        "CC5",
        "política sin evento CREADA",
        "SELECT count(*) FROM gov_closure_policies p "
        "WHERE NOT EXISTS ("
        "SELECT 1 FROM gov_closure_policy_history h "
        "WHERE h.policy_id = p.id AND h.evento = 'CREADA'"
        ")",
    ),
    (
        "CC6",
        "política vigente sin evento ACTIVADA, sin activada_por o sin activada_en",
        "SELECT count(*) FROM gov_closure_policies p "
        "WHERE p.estado = 'VIGENTE' AND ("
        "p.activada_por IS NULL OR p.activada_en IS NULL OR NOT EXISTS ("
        "SELECT 1 FROM gov_closure_policy_history h "
        "WHERE h.policy_id = p.id AND h.evento = 'ACTIVADA'"
        "))",
    ),
    (
        "CC7",
        "política retirada sin evento RETIRADA, sin retirada_por, sin retirada_en o sin motivo_retiro",
        "SELECT count(*) FROM gov_closure_policies p "
        "WHERE p.estado = 'RETIRADA' AND ("
        "p.retirada_por IS NULL OR p.retirada_en IS NULL "
        "OR p.motivo_retiro IS NULL OR NOT EXISTS ("
        "SELECT 1 FROM gov_closure_policy_history h "
        "WHERE h.policy_id = p.id AND h.evento = 'RETIRADA'"
        "))",
    ),
    (
        "CC8",
        "política en borrador con datos de activación o retirada no nulos",
        "SELECT count(*) FROM gov_closure_policies p "
        "WHERE p.estado = 'BORRADOR' AND ("
        "p.activada_por IS NOT NULL OR p.activada_en IS NOT NULL "
        "OR p.retirada_por IS NOT NULL OR p.retirada_en IS NOT NULL"
        ")",
    ),
    (
        "CC9",
        "control HALLAZGOS_ABIERTOS sin riesgo_minimo o ACTOS_SIN_EFICACIA con riesgo_minimo",
        "SELECT count(*) FROM gov_closure_controls c "
        "WHERE (c.tipo = 'HALLAZGOS_ABIERTOS' AND c.riesgo_minimo IS NULL) "
        "OR (c.tipo = 'ACTOS_SIN_EFICACIA' AND c.riesgo_minimo IS NOT NULL)",
    ),
]
