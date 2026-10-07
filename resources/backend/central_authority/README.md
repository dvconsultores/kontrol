# Autoridad Central de Licencias de KONTROL — Fase 1

Servicio del **propietario** de KONTROL. Vive fuera de cualquier instalación cliente: backend,
PostgreSQL, secretos y clave privada de firma propios. Comparte con el cliente solo el contrato puro
`app/core/license_contract.py`. Agnóstico de proveedor: cualquier plataforma que ejecute
contenedores y PostgreSQL 16 sirve (ADR-D0-006: TLS, custodia cifrada de la clave, auditoría,
respaldo con recuperación probada, aislamiento del entorno de emisión).

## Configuración (`KONTROL_CENTRAL_*`)

| Variable | Obligatoria | Uso |
|---|---|---|
| `KONTROL_CENTRAL_DB_URL` | sí | la base **propia** de la autoridad |
| `KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM` | sí en `prod` | clave privada Ed25519 del propietario; nunca se genera ni se registra |
| `KONTROL_CENTRAL_SIGNING_KID` | no (`kontrol-lic-2026-01`) | identificador de la clave: una sola activa en Fase 1 |
| `KONTROL_CENTRAL_ENVIRONMENT` | no (`local`) | `prod` exige la clave al arrancar |

La clave pública correspondiente es la que cada instalación cliente recibe como
`KONTROL_LICENSE_PUBLIC_KEY_PEM`.

## Despliegue

```sh
docker compose -f compose.central.yaml up -d        # postgres propio + API de health (migra al arrancar)
docker compose -f compose.central.yaml exec central-api \
  python -m central_authority.cli register-installation --operator ana \
    --installation-id KTL-XX-... --public-key-file /run/claves/instalacion.pem \
    --customer-id CUS-... --contract-id CON-... --company-tax-id J-...
docker compose -f compose.central.yaml exec central-api \
  python -m central_authority.cli issue-license --operator ana --installation-id KTL-XX-... --anio 2027 \
    --entitlements '{"companies": 3, "users": 25}'
```

`issue-license` imprime el paquete firmado (`payload` + `signature_hex`), que el administrador de la
instalación importa con `POST /api/v1/license/activate` (sesión + `license:create`). Volver a
emitir el mismo período es una reemisión: la autoridad asigna la siguiente `revision`.

## Lo que la Fase 1 no hace

Sync remoto (bloqueado hasta decidir la autenticación de la instalación), rotación de claves,
portales, pagos, revocación remota.

## Sincronización autenticada (`CENTRAL-SYNC-AUTHORITY-UNDEFINED`)

`POST /v1/license/sync/challenge` y `POST /v1/license/sync`: la instalación prueba su identidad con su
clave privada Ed25519 (desafío de un solo uso, nonce de 256 bits, sobre canónico ligado a la petición,
SHA-256 de los bytes exactos del cuerpo); la autoridad verifica contra la clave pública vinculada en el
alta (`register-installation --public-key-file`, huella única) y devuelve el artefacto exacto de su
libro. Caducidad del desafío: `KONTROL_CENTRAL_SYNC_CHALLENGE_TTL_SECONDS` (120 s por defecto). El
estado de los desafíos vive en la base de la autoridad (`cla_sync_challenges`), nunca en memoria.
Contrato completo: `specs/010-licenciamiento-central/central-authority/contracts/health-and-sync.md`.
En producción el cliente exige `https://`; el endpoint de desafío no tiene límite de tasa propio
(`CENTRAL-SYNC-SIN-LIMITE-DE-TASA`): póngalo detrás de la pasarela que corresponda.
