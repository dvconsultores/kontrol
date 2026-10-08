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
| `KONTROL_CENTRAL_SIGNING_KID` | no (`kontrol-lic-2026-01`) | el `kid` **activo**: identifica la clave que firma las emisiones nuevas y debe existir en el conjunto |
| `KONTROL_CENTRAL_SIGNING_KEYS` | no | JSON `kid → PEM privada` para rotar con solapamiento (se suma al par anterior); `kid` duplicado con otra clave o la misma clave bajo dos `kid` → no arranca; runbook: `specs/010-licenciamiento-central/central-authority/runbook-rotacion-de-clave.md` |
| `KONTROL_CENTRAL_ENVIRONMENT` | no (`local`) | `prod` exige la clave al arrancar |
| `KONTROL_CENTRAL_SYNC_CHALLENGE_TTL_SECONDS` | no (120) | vida de un desafío del sync (5–900) |
| `KONTROL_CENTRAL_SYNC_CHALLENGE_RATE_LIMIT_ENABLED` | no (`true`) | límite de tasa **global** del endpoint de desafío; en `prod` no se puede apagar |
| `KONTROL_CENTRAL_SYNC_CHALLENGE_RATE_LIMIT_CAPACITY` | no (120) | desafíos admitidos dentro de cualquier ventana (1–100000); la ráfaga admitida es la capacidad entera |
| `KONTROL_CENTRAL_SYNC_CHALLENGE_RATE_LIMIT_WINDOW_SECONDS` | no (60) | ventana deslizante en segundos (1–3600) |

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
En producción el cliente exige `https://`.

## Límite de tasa del endpoint de desafío (`CENTRAL-SYNC-SIN-LIMITE-DE-TASA`)

`POST /v1/license/sync/challenge` es pre-autenticación por necesidad, así que tiene un límite **global**
por autoridad: `KONTROL_CENTRAL_SYNC_CHALLENGE_RATE_LIMIT_CAPACITY` desafíos dentro de cualquier
ventana de `…_WINDOW_SECONDS` (120 por 60 s por defecto: una sincronización legítima es un desafío, el
sync es manual y la renovación anual; acota también la tabla `cla_sync_challenges` a ≤ capacidad por
ventana). Ventana deslizante exacta sobre las filas que la autoridad ya persiste (sin tabla nueva, sin
memoria por proceso, sin Redis): vale para varios trabajadores y réplicas (candado consultivo de
PostgreSQL alrededor de «contar + insertar») y no tiene un modo de fallo propio (si la base no responde,
tampoco se emite). Se decide **antes** de crear la fila; el rechazo es `429 {"code":
"SYNC_RATE_LIMITED", "message": …}` con `Retry-After` determinista, **idéntico** para una identidad
conocida o desconocida, y no toca ningún desafío ya emitido (que sigue valiendo hasta su caducidad o su
consumo). El cliente lo recibe como `502 CENTRAL_SYNC_REJECTED` (`central_code: SYNC_RATE_LIMITED`), sin
reintentos automáticos ni retroceso. Los rechazos no van a la auditoría: un aviso de registro por
ventana con el recuento, sin identidad del llamador. Es defensa en profundidad: **no sustituye** a la
identidad Ed25519, al desafío de un solo uso ni a la firma del sobre, y **no protege** de un ataque
volumétrico de red (eso es de la pasarela, el proveedor o un WAF, a elección del operador).

**Pasarela (recomendado, fuera de este repositorio).** La aplicación no usa la IP de origen porque no
hay contrato de proxy de confianza: la IP real solo la conoce la pasarela que usted ponga delante.
Ponga ahí un límite **por origen** (p. ej. `limit_req` de nginx o `rate_limit` de Caddy, con valores
conservadores: varias instalaciones legítimas pueden compartir NAT), no publique 8010 directamente
(el compose no lo publica) y no reenvíe `X-Forwarded-For`/`Forwarded` a la autoridad esperando que
decida con ellas: no lo hace. Si en el futuro se definiera un proxy de confianza, sería una decisión
nueva, no una ampliación de esta.
