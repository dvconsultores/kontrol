# ADR-004-CLA-001 — Frontera de la Autoridad Central de Licencias

| | |
|---|---|
| Estado | APROBADO (dueña, 2026-10-06; materializa D0-06) |
| Decisión | La Autoridad Central es un servicio del propietario, **vendor-hosted, aislado del cliente y agnóstico de proveedor**: backend, PostgreSQL, secretos y clave privada de firma propios; despliegue independiente (`Dockerfile.central`, `compose.central.yaml`); nunca forma parte del Compose, la base, los volúmenes ni los secretos de una instalación cliente |
| Código | vive en `resources/backend/central_authority/` para compartir entorno, lockfile y base de imagen con una sola tecnología; comparte con el cliente **solo** el módulo puro `app/core/license_contract.py` (una prueba de grafo de importación lo garantiza) |
| Criptografía | la clave privada del propietario existe solo en la autoridad (configuración externa); el cliente conserva su clave de identidad y la pública del propietario como única ancla |
| Proveedor | no se fija ninguno; cualquier plataforma que ejecute contenedores y PostgreSQL 16 con los requisitos de ADR-D0-006 (TLS, custodia cifrada, auditoría, respaldo) sirve |
| Consecuencias | D0-06 cerrada en cuanto a frontera y hospedaje lógico; la API de sync requiere decidir la autenticación de la instalación antes de exponerse (`CENTRAL-SYNC-AUTHORITY-UNDEFINED`) |
