# Contrato de pantalla · CNT-09

| Pantalla | Ruta | Permiso | Contenido |
|---|---|---|---|
| Alertas (Spec 047, reutilizada) | `/alertas` | `alertas:view` | Filtros Estado, Severidad y Origen. Cada `li[data-testid=alerta]` lleva severidad (con texto), categoría («Vencimiento de hito», …), fecha, estado, mensaje y «Abrir origen» |
| Ficha del contrato › Alertas de vencimiento | `/gobierno/contratos/{id}` (FORMALIZADO) | `gobierno_contratos:view` | `section[aria-labelledby=alertas-contrato-titulo]`: aviso «informan; no sustituyen…», «Alertas activas: N», la lista con enlace al origen y «Ver todas las alertas» (con `alertas:view`) |
| Alertas de vencimiento (preaviso) | `/gobierno/contratos-alertas` | ver: `gobierno_contratos:view`; editar: `notificaciones:configure` | Reglas fijas (15 días de PROC-10; sin calendario hábil). Por fuente (Contratos, Hitos, Entregables): «Activar preaviso» y «Días de anticipación» (1–365); botón «Guardar preaviso»; sin permiso de edición, controles deshabilitados |

- **Enlaces de origen:**
  - `gov_contract` → ficha del contrato;
  - `gov_contract_execution` → ejecución;
  - `gov_procurement_file` → expediente, con `gobierno_expedientes:view`.
- **Severidad:** INFO «Informativa», WARNING «Advertencia», CRITICAL «Crítica». Siempre va escrita, no solo con color. Contraste ≥ 4,5:1 (D7).
- **Responsive y accesibilidad:** 1280, 390 y 320 sin desbordamiento; Axe sin violaciones serias ni críticas en `/alertas` y en la ficha (E2E).
