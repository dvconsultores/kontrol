# Base tras la E2E (ciclo 04)

**Método.** `qa/e2e-run.py --con-analizador --orden <envoltorio>`, sobre la base efímera de la corrida:
1. Playwright de `audit-catalog`, `documents`, `auditoria-fecha` y `auditoria-sobre` en Chromium: 17/17;
2. inspección de solo lectura de `audit_events` antes de eliminar la base.

Corrida `r20261028t150731p78857n3e5ce3`, limpieza LIMPIA.

| Comprobación | Resultado |
|---|---|
| Eventos | 183: 28 de empresa y 155 de tenant |
| Fuera del catálogo | 0 |
| Eventos de empresa sin empresa | 0 |
| Eventos de tenant con empresa | 0 |
| Claves prohibidas en el detalle, a cualquier nivel | 0 |
| Fragmento de la muestra o nombre del fichero | 0 |
| `DOCUMENT_SCAN_REJECTED` | 2, ambos con empresa y `request_id`, `reason=MALWARE_DETECTED` y exactamente las 8 claves de evidencia |
| Triggers | `trg_audit_events_no_delete`, `trg_audit_events_no_truncate` y `trg_audit_events_no_update` |
| Revisión | `0061_spec001_audit_immutability` |
| Documento rechazado | Sin versión (lo comprueban SCAN-E2E-01 y la E2E documental) |
| Base efímera | Eliminada; bases de corrida: 0 |

Una primera ejecución dio un falso positivo **del guion de Claude**: buscaba la subcadena «eicar» en el título «Contrato <RUN>-EICAR» de la E2E documental. Se corrigió el guion para recorrer las claves del JSON y buscar un fragmento real de la muestra; el producto no se tocó.

**POST_E2E_DB_CERTIFICATION = PASS.**
