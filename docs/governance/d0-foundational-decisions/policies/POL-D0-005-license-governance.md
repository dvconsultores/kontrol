# POL-D0-005 — Gobierno de licenciamiento

> Deriva de `ADR-D0-006` y ratifica `ADR-005`. Vinculante para las Specs 004, 048, 052, 053.

## 1. Modelo

Cada cliente opera una instalación independiente en su propio servidor mediante Docker Compose, con
su frontend, backend, PostgreSQL, volúmenes, `Installation ID` y licencia. Las instalaciones no
comparten base de datos, secretos, archivos, procesos ni logs (P9).

## 2. Separación de autoridad

| Propietario de KONTROL | Administrador local |
|---|---|
| Activa, renueva, suspende y revoca | Administra su empresa, usuarios, sucursales y operación |
| Custodia la clave privada | Nunca posee clave capaz de emitir licencia |
| Define derechos contratados | Configura su operación dentro de esos derechos |

## 3. Comunicación

Siempre **iniciada por la instalación** sobre HTTPS con verificación de certificado. La autoridad no
abre conexiones hacia el cliente ni requiere puertos entrantes en el servidor del cliente.

Operaciones: `activate` · `sync` · `renew` · `replace_installation` · `heartbeat`.
La revocación se entrega en el siguiente `sync`.

## 4. Calendario contractual

Período **1 de abril → 31 de marzo**. Aviso de renovación desde el **1 de abril**; aviso crítico
desde el **21 de abril**; **`READ_ONLY`** desde el **1 de mayo** sin renovación confirmada.

Las fechas **viajan en la licencia firmada**, no en el código.

## 5. Modo READ_ONLY

El cliente conserva **acceso completo de consulta y exportación de sus datos**. Solo se bloquea la
escritura transaccional. El licenciamiento nunca retiene datos ajenos (P15).

## 6. Seguridad

Ed25519 · clave privada solo en la autoridad · clave pública distribuida con `kid` · rotación por
vigencia de `kid` sin corte · `installation_id` en el payload · firma inválida → `SECURITY_SUSPENSION` ·
tolerancia offline anclada a fecha monótona confiable, resistente a manipulación del reloj.

## 7. Privacidad — límite duro

**Se envía:** `installation_id`, versión del producto, estado de licencia, marca temporal, huella de
entorno no identificable y métricas agregadas si el contrato lo exige.

**No se envía y no puede solicitarse:** facturas, clientes, proveedores, inventario, importes,
usuarios, correos ni ningún dato comercial. Un campo nuevo que transporte datos de negocio es
violación de P15 y exige enmienda del ADR.

## 8. Pendiente

**BUSINESS_DECISION_PENDING** — OQ-07: hospedaje de la autoridad. No se recomienda proveedor.
Riesgo asociado: la custodia de la clave privada es el activo más crítico del modelo comercial.
