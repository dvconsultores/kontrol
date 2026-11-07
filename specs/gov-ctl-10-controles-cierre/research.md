# Research: CTL-10 Controles de cierre

Fuentes leídas: DISENO.md cerrado; IR GOV-CTL-012 (N20, N21); modelos `gov_findings`, `gov_acts`, `gov_structures`, `gov_cash_programs`; CTL-01 (guarda SoD y `conflictos`), CTL-04. Sin NEEDS CLARIFICATION pendientes.

| Tema | Decisión | Razón | Alternativas descartadas |
|---|---|---|---|
| Inventario de cierres | Siete acciones de «cierre» existentes; dos integradas (ORG-02 cerrar estructura, TRE-02 cerrar programa) | OD-CTL10-02 | Integrar todas: fuera de alcance. TRE-01 no por decisión |
| Tipos de control | HALLAZGOS_ABIERTOS y ACTOS_SIN_EFICACIA, catálogo cerrado | Hay datos reales: `gov_findings.estado/riesgo`, `gov_acts.status/fecha` | Motor de reglas: prohibido (OD-CTL10-03) |
| Alcance de hallazgos | Todo el ente, sin ejercicio | Un hallazgo abierto es material sin importar su año | Filtrar por ejercicio: oculta riesgos |
| Alcance de actos | Estado EMITIDO con `fecha` en el ejercicio del objeto | Un acto emitido sin eficacia es una promesa sin cumplir del periodo | Todos los actos: ruido de ejercicios viejos |
| Lugar de la guarda | Dentro del servicio de cierre, tras estado y SoD, fila bloqueada | Nadie la evade por otra vía; errores de estado y SoD tienen precedencia | Dependencia de ruta: evadible por servicio |
| Serialización con retirar | FOR SHARE sobre la política efectiva | Cierre y retiro no se cruzan | Sin bloqueo: cierre pasa tras retirada o lo contrario |
| Auditoría del bloqueo | `record_audit_after_rollback`, acción REJECTION | La reversión no pierde la evidencia | Auditar antes de revertir: se pierde |
| Pantalla de bloqueos | Leída de auditoría | Una fuente, como `conflictos` de CTL-01 | Tabla propia: segunda fuente |
| Política activada | No se edita: se retira y se crea otra | Evidencia histórica | Editar: destruye evidencia |
| Aprobación | Control Interno con MFA, sin acto ni documento (OD-CTL10-04) | Decisión de la dueña | Acto DOC-02: descartado |
| Reportes y documentos | NOT_APPLICABLE | GOV-CTL-012 no los exige | CSV de relleno prohibido |
| Fecha efectiva | Fecha civil America/Caracas | Regla de producto | UTC: error en el borde del día |
