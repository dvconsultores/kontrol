# CIERRE · CTL-09 Actas de entrega (GOV-CTL-011) · 2026-11-11

```text
PRODUCT_STATUS=OWNER_UAT_READY   (sujeto a humo UAT ACCESSIBLE)
OWNER_ACCEPTED=NO
MENÚ=Gobierno › Actas de entrega
MIGRACIÓN=0102_gov_ctl09_actas (down 0101_receipt_count_independence; cabeza única)
CAPACIDAD=gobierno_actas view | manage | verify (suscribir y verificar: SENSITIVE / MFA)
DEEPSEEK_CALLS=10 (8 dentro del tope + 2 autorizadas por la dueña) · COSTE≈0,091 USD
CLAUDE_AUTHORED_PRODUCT_CODE=0
```

## Qué se entregó

- **Backend:**
  - modelos `GovernmentHandoverAct`, `GovernmentHandoverAnnex` y `GovernmentHandoverObservation`, con disparadores PostgreSQL de inmutabilidad: acta congelada tras suscribir; anexos editables solo en BORRADOR, borrado con `RETURN OLD`; observaciones solo de alta;
  - servicio, esquemas y API `/gobierno/actas-entrega` (12 rutas);
  - catálogo de auditoría (+9), MFA, `PROCESOS` (CTL-09), `ResourceKind` y semilla N9.
- **Contrato:**
  - saliente = ocupación de ORG-04; ámbito ENTE / UNIDAD;
  - anexos art. 11 y art. 17 (municipal + ENTE);
  - A11_1, A11_2 y A11_5 generados al corte desde TRE-01, CTL-05, ORG-03/04, PROC-03 y DOC-02;
  - resolución por documentos o constancia (art. 19);
  - suscripción con instantánea, sha256 y PDF (ReportLab);
  - remisión (art. 21), observaciones (art. 22) y verificación de la UAI con maker-checker (403 `GOV_HANDOVER_SAME_ACTOR`).
- **Frontend:**
  - menú, listado con filtros, alta y ficha completa: anexos, adjuntos, suscripción, PDF, remisión, observaciones, verificación, integridad legible e historial;
  - rutas, pantallas, gate-coverage y humo UAT.

## Pruebas

| Comprobación | Resultado |
|---|---|
| CTL-09 PG (ae01..ae08) | 8/8 |
| Transversales tras la fusión | 242/242 |
| Migración up/down/up PG | OK, cabeza única 0102 |
| ruff / mypy | limpio / 154 = línea base Enterprise, 0 nuevos |
| PG completa con analizador | 5343 passed / 6 failed / 18 skipped |
| Vitest completo (Node 22) | 1934/1934 (+12) |
| tsc, eslint, build canónico | verde |
| E2E CTL-09 (base efímera, 0 reintentos) | 1/1 |

Las 6 rojas de la suite PG fallan igual, con salida idéntica salvo identificadores aleatorios, en `origin/develop` = `2cc6a19` sin CTL-09: 2 de `test_spec019_receipt`, el runner de integridad, N10, `pip check` y el guardia de datetime. CTL-09 no añade ninguna (`NEW_BACKEND_FAILURES=0`).

## Observaciones abiertas (no bloquean)

- **OBS-CTL09-A11Y-01 (LOW):** los controles por anexo («Constancia (art. 19)», «Guardar constancia», «Guardar documentos») repiten nombre accesible en cada fila. Axe no lo marca como serio. Convendría el sufijo con el código del anexo.
- **OBS-CTL09-PLAZOS-01:** sin plazos en días hábiles (arts. 13, 21 y 22) hasta que exista calendario oficial (DOC-03 BLOCKED).
- **OBS-CTL09-ORCH-01:** 10 llamadas (tope 8). Las 2 extra las autorizó la dueña: K7, una variable sin uso, y K8, la colisión de migración con Spec 021 de P2. Ver `ATTEMPT_LOG.md`.
