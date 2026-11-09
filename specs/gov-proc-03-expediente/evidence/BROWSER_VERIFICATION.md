# PROC-03 · verificación en navegador (Chromium, frontend + backend + PostgreSQL reales)

EXPEDIENT_LIST_BROWSER_VERIFIED = 1 · EXPEDIENT_CREATE_BROWSER_VERIFIED = 1 · EXPEDIENT_DETAIL_BROWSER_VERIFIED = 1 · EXPEDIENT_EDIT_BROWSER_VERIFIED = 1
TIMELINE_BROWSER_VERIFIED = 1 · DOCUMENTS_BROWSER_VERIFIED = 1 · MILESTONES_BROWSER_VERIFIED = 1

ACCIONES SCREEN_EXISTS_NOT_BROWSER_VERIFIED: terminar responsable, descartar, declarar que no interviene comisión, reservar un folio, reprogramar hito, marcar hito «no aplica», paginación y filtros distintos de la búsqueda.
De ellas, por API en PostgreSQL: terminar responsable, descartar y reprogramar. Sin prueba alguna: no interviene comisión, reserva de folio y hito «no aplica». Sin Axe ni comprobación a 320 px.
