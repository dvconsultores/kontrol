# Convergencia — Autoridad Central Fase 1 (2026-10-07)

**Núcleo del emisor: CONVERGIDO.** Servicio independiente con base, migraciones, configuración y
clave propias; registro de instalaciones; libro de emisiones; `revision` firmada, monótona por
instalación + período y segura en concurrencia (PostgreSQL); paquete firmado que el cliente verifica
e importa; CLI del propietario; health mínimo; imagen y compose propios; prueba de grafo de
importación.

**API de sync: IMPLEMENTADA y autenticada** (`CENTRAL-SYNC-AUTHORITY-UNDEFINED`, convergida el 2026-10-07,
`spec004-central-sync-auth-delta.md`). Lo que sigue describe el estado al cierre de la Fase 1: el cliente existente la
llama sin autenticación ligada a la instalación. No se expone ni se afirma lista.

**D0-06:** CLOSED / IMPLEMENTED en cuanto a frontera y hospedaje lógico (vendor-hosted, aislado,
agnóstico de proveedor); el proveedor físico no es condición.

**Siguiente paso de la familia (hecho el 2026-10-07):** `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN`
se cerró en el cliente con este emisor como fuente de los artefactos
(`spec004-licencia-revision-cliente-delta.md`); la autoridad no cambió. Sigue pendiente la
autenticación de la instalación para sync (`CENTRAL-SYNC-AUTHORITY-UNDEFINED`), implementada el mismo día.
