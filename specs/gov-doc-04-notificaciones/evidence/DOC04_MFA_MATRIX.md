# DOC-04 · matriz de roles, capacidades y MFA (PDD-DOC04-04)

| Capacidad | Qué permite | Clase MFA (`mfa_policy`) | Rol de QA que la tiene | Prueba |
|---|---|---|---|---|
| `gobierno_notificaciones:view` | Lista del año, CSV, notificación, historial, sección «Notificaciones» del acto | STANDARD | FUNCIONAL_COMPLETO (migración 0067) · CONSULTA_NOTIFICACIONES (E2E) | GN-16, GN-14, NTL-01, NTP-01, NDA-01, DOC4-E2E-02 |
| `gobierno_notificaciones:edit` | Agregar destinatario, corregir datos (PENDIENTE sin intentos), anular | SENSITIVE | FUNCIONAL_COMPLETO | GN-16, GN-14, NTP-04, NDA-06, DOC4-E2E-02 |
| `gobierno_notificaciones:record` | Registrar entrega, intento fallido y publicación en prensa (llevan el acto a EFICAZ) | SENSITIVE | FUNCIONAL_COMPLETO | GN-16, GN-14 (`notipreparador` con edit sin record → 403), NTP-04, UN-13 |

Reglas verificadas:
- Guardas del API en el orden del proyecto: permiso → empresa → módulo `gobierno` (licencia).
- Permiso de la aplicación ≠ autoridad institucional: el usuario registra la notificación; el acto lo dictó el cargo (DOC-02).
- Aislamiento: una notificación de otra empresa responde 404 GOV_NOTIFICATION_NOT_FOUND (GN-15, DOC4-E2E-03); la lista de otro ente no
  incluye nada de A; `scope_scan` 0 sobre la base tras la E2E.
- Recuentos de la guarda MFA tras el ciclo: 47 sensibles / 39 estándar (`test_mfa_policy`), techo de delegación 103
  (`test_delegation_ceiling`).
