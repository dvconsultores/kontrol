"""Controles de integridad posteriores a la E2E de Gobierno (OBS-CERT-GOV-01).

Los controles de integridad posteriores a la E2E de Gobierno vivían fuera
del repositorio y se perdieron. Se reconstruyen versionados en `qa/`.

Cada control es una consulta SQL de PostgreSQL de SOLO LECTURA que devuelve
UN entero: el número de violaciones (0 = sano). Se ejecutan sobre la base de
una corrida E2E (todas las empresas a la vez), por eso cada control compara
empresa y relaciones en toda la base.
"""

GRUPO = "ORG-02/ORG-03/ORG-07"

INFO: dict[str, str] = {
    "estructuras": "SELECT count(*) FROM gov_structures",
    "unidades": "SELECT count(*) FROM gov_units",
    "versiones (de unidad)": "SELECT count(*) FROM gov_unit_versions",
    "cargos": "SELECT count(*) FROM gov_positions",
    "exportaciones_matriz": "SELECT count(*) FROM audit_events WHERE action = 'GOV_AUTHORITY_MATRIX_EXPORTED'",
    "eventos GOV_*": "SELECT count(*) FROM audit_events WHERE action LIKE 'GOV_%'",
}

CHECKS: list[tuple[str, str, str]] = [
    (
        "C1",
        "unidad con empresa distinta de su estructura",
        """
        SELECT count(*)
        FROM gov_units u
        JOIN gov_structures s ON s.id = u.structure_id
        WHERE u.company_id <> s.company_id
        """,
    ),
    (
        "C2",
        "versión con empresa o estructura distinta de su unidad",
        """
        SELECT count(*)
        FROM gov_unit_versions v
        JOIN gov_units u ON u.id = v.unit_id
        WHERE v.company_id <> u.company_id
           OR v.structure_id <> u.structure_id
        """,
    ),
    (
        "C3",
        "estructura con ente de otra empresa",
        """
        SELECT count(*)
        FROM gov_structures s
        JOIN gov_entities e ON e.id = s.entity_id
        WHERE s.company_id <> e.company_id
        """,
    ),
    (
        "C4",
        "superior en otra estructura",
        """
        SELECT count(*)
        FROM gov_units u
        JOIN gov_units p ON p.id = u.parent_id
        WHERE u.structure_id <> p.structure_id
        """,
    ),
    (
        "C5",
        "estructura VIGENTE/CERRADA sin acto vinculado de la misma empresa",
        """
        SELECT count(*)
        FROM gov_structures s
        WHERE s.status IN ('VIGENTE', 'CERRADA')
          AND NOT EXISTS (
              SELECT 1
              FROM document_links dl
              JOIN documents d ON d.id = dl.document_id
              WHERE dl.resource_type = 'GovernmentStructure'
                AND dl.resource_id = s.id
                AND dl.company_id = s.company_id
                AND d.company_id = s.company_id
                AND d.status = 'ACTIVE'
          )
        """,
    ),
    (
        "C6",
        "versión de la unidad sin su fila de historial",
        """
        SELECT count(*)
        FROM gov_units u
        WHERE NOT EXISTS (
            SELECT 1
            FROM gov_unit_versions v
            WHERE v.unit_id = u.id
              AND v.version = u.version
        )
        """,
    ),
    (
        "C7",
        "unidad INACTIVA sin fin de vigencia",
        """
        SELECT count(*)
        FROM gov_units
        WHERE status = 'INACTIVA'
          AND valid_to IS NULL
        """,
    ),
    (
        "C8",
        "unidad ACTIVA bajo superior INACTIVO",
        """
        SELECT count(*)
        FROM gov_units u
        JOIN gov_units p ON p.id = u.parent_id
        WHERE u.status = 'ACTIVA'
          AND p.status = 'INACTIVA'
        """,
    ),
    (
        "C9",
        "estructura VIGENTE/CERRADA sin auditoría de puesta en vigor",
        """
        SELECT count(*)
        FROM gov_structures s
        WHERE s.status IN ('VIGENTE', 'CERRADA')
          AND NOT EXISTS (
              SELECT 1
              FROM audit_events ae
              WHERE ae.action = 'GOV_STRUCTURE_PUBLISHED'
                AND ae.entity_type = 'GovernmentStructure'
                AND ae.entity_id = s.id
                AND ae.company_id = s.company_id
          )
        """,
    ),
    (
        "C10",
        "vigencia fuera del ejercicio",
        """
        SELECT count(*)
        FROM gov_units u
        JOIN gov_structures s ON s.id = u.structure_id
        WHERE (u.valid_from::date < make_date(s.exercise, 1, 1))
           OR (u.valid_to::date > make_date(s.exercise, 12, 31))
        """,
    ),
    (
        "C11",
        "cargo con empresa distinta de su estructura",
        """
        SELECT count(*)
        FROM gov_positions p
        JOIN gov_structures s ON s.id = p.structure_id
        WHERE p.company_id <> s.company_id
        """,
    ),
    (
        "C12",
        "cargo en una unidad de otra estructura",
        """
        SELECT count(*)
        FROM gov_positions p
        JOIN gov_units u ON u.id = p.unit_id
        WHERE u.structure_id <> p.structure_id
        """,
    ),
    (
        "C13",
        "competencia con empresa distinta de su cargo",
        """
        SELECT count(*)
        FROM gov_position_competencies c
        JOIN gov_positions p ON p.id = c.position_id
        WHERE c.company_id <> p.company_id
        """,
    ),
    (
        "C14",
        "cargo sin la versión de historial de su versión actual",
        """
        SELECT count(*)
        FROM gov_positions p
        WHERE NOT EXISTS (
            SELECT 1
            FROM gov_position_versions v
            WHERE v.position_id = p.id
              AND v.version = p.version
        )
        """,
    ),
    (
        "C15",
        "cargo VIGENTE/INACTIVO sin ninguna versión VIGENTE (la matriz no podría reconstruirlo)",
        """
        SELECT count(*)
        FROM gov_positions p
        WHERE p.status IN ('VIGENTE', 'INACTIVO')
          AND NOT EXISTS (
              SELECT 1
              FROM gov_position_versions v
              WHERE v.position_id = p.id
                AND v.status = 'VIGENTE'
          )
        """,
    ),
    (
        "C16",
        "versión de cargo con empresa o estructura distinta de su cargo",
        """
        SELECT count(*)
        FROM gov_position_versions v
        JOIN gov_positions p ON p.id = v.position_id
        WHERE v.company_id <> p.company_id
           OR v.structure_id <> p.structure_id
        """,
    ),
    (
        "C17",
        "cargo INACTIVO sin fin de vigencia o VIGENTE con fin",
        """
        SELECT count(*)
        FROM gov_positions
        WHERE (status = 'INACTIVO' AND valid_to IS NULL)
           OR (status = 'VIGENTE' AND valid_to IS NOT NULL)
        """,
    ),
    (
        "C18",
        "cargo VIGENTE/INACTIVO sin competencias",
        """
        SELECT count(*)
        FROM gov_positions p
        WHERE p.status IN ('VIGENTE', 'INACTIVO')
          AND NOT EXISTS (
              SELECT 1
              FROM gov_position_competencies c
              WHERE c.position_id = p.id
          )
        """,
    ),
    (
        "C19",
        "exportación de la matriz sin empresa, sobre estructura ajena o sin recuento",
        """
        SELECT count(*)
        FROM audit_events ae
        WHERE ae.action = 'GOV_AUTHORITY_MATRIX_EXPORTED'
          AND (
              ae.company_id IS NULL
              OR ae.entity_type <> 'GovernmentStructure'
              OR ae.entity_id IS NULL
              OR NOT EXISTS (
                  SELECT 1
                  FROM gov_structures s
                  WHERE s.id::text = ae.entity_id::text
                    AND s.company_id = ae.company_id
              )
              OR (ae.after::json)->>'filas' IS NULL
          )
        """,
    ),
    (
        "C20",
        "permiso gobierno_autoridad:view ausente o sin FUNCIONAL_COMPLETO",
        """
        SELECT CASE
            WHEN EXISTS (
                SELECT 1
                FROM roles r
                JOIN role_permissions rp ON rp.role_id = r.id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE r.code = 'FUNCIONAL_COMPLETO'
                  AND r.company_id IS NULL
                  AND p.resource = 'gobierno_autoridad'
                  AND p.action = 'view'
            ) THEN 0
            ELSE 1
        END
        """,
    ),
]
