# PROC-02 · Plan

**Núcleo compartido:** SHARED_CORE_CHANGE_REQUIRED = 0. Solo catálogo de auditoría y permisos, como en cada vertical.

**Datos.** Migración sobre la cabeza real. `gov_procurement_committees`, `gov_procurement_committee_members`, `gov_procurement_committee_conflicts`, `gov_procurement_committee_history` (inmutable). Índices parciales en PostgreSQL: un funcionario una vez activo por comisión, un suplente por principal, un secretario principal y uno suplente.

**API `/gobierno/contrataciones/comisiones`:** catálogo, opciones, lista, CSV, alta, detalle a fecha, edición, descarte, activación, cierre, notificación al SNC, miembros (añadir, retirar, terminar), inhibiciones (declarar, resolver).

**Reutiliza:** funcionarios y ocupación de ORG-04, actos de DOC-02, SoD de CTL-01 (proceso PROC-02), bitácora de CTL-02, actor efectivo de ORG-06.

**Frontend.** Sección de menú «Gobierno · Contrataciones»; lista, formulario y ficha con composición, inhibiciones, historia y paneles en línea, sin modales.

**Constitución.** P8: reglas con versión y fuente. P5: historia inmutable. P6: alcance en backend. Gate superado: 0 decisiones materiales abiertas.
