# FUENTES · REP-10 Reporte de control interno

| Fuente | Qué fija | Uso |
|---|---|---|
| IR v1.0 §12 «Reportes y tableros mínimos» | «Control interno: overrides, conflictos SoD, operaciones duplicadas, hallazgos y acciones correctivas.» | Contenido mínimo del reporte (las 5 categorías) |
| CTL-01 (specs/gov-ctl-01-*) · `MODOS_REGLA_SOD = ("BLOQUEAR",)` | La segregación de funciones solo bloquea, sin excepción ni dispensa | Overrides: categoría sin fuente por diseño (no existe un mecanismo de excepción en Gobierno) |
| CTL-01 · evento `GOV_SOD_CONFLICT_BLOCKED` (clase REJECTION, `record_audit_after_rollback`) | Cada intento bloqueado queda persistido con regla, proceso, acción, acción previa y objeto | Conflictos SoD |
| ORG-06 / CTL-03 · evento `GOV_IDENTITY_GUARD_BLOCKED` | Rechazos por política de identidad institucional | Bloqueos de identidad (control preventivo) |
| CTL-10 · evento `GOV_MATERIAL_CLOSE_BLOCKED` | Cierres bloqueados por controles materiales (hallazgos abiertos, actos sin eficacia) | Bloqueos de cierre |
| CTL-06 · `GovernmentFinding`, `GovernmentCorrectiveAction`, regla R14 `_accion_vencida` | Estados, riesgo, plan de acciones, responsable (cargo y unidad), fecha objetivo y avance | Hallazgos y acciones correctivas (vencidas según R14) |
| TRE-03 / TRE-04 (BLOCKED, sin modelo) | Órdenes de pago y pagos no existen en Gobierno | Operaciones duplicadas: sin fuente hasta que existan |

No se universaliza ninguna regla local (Naguanagua): el reporte solo consolida hechos ya registrados por procesos de KONTROL.
