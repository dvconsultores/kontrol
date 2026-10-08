# Contrato — health y sync autenticado de la Autoridad Central

## Health (sin cambios)

`GET /health/live` → `{"status": "ok", "service": "kontrol-central-authority"}` ·
`GET /health/ready` → `{"status", "service", "database"}`. Sin `/docs`, sin `/openapi.json`, sin API de
administración pública (las operaciones del propietario van por la CLI).

## Sync autenticado (FR-010-367..429) — `CENTRAL-SYNC-AUTHORITY-UNDEFINED`, implementado

Tres autoridades que no se mezclan: la **clave privada de la instalación** (Ed25519, la que la
instalación genera al activarse) prueba «esta petición viene de la instalación X»; la **clave del
propietario** firma licencias; **TLS** protege el canal (HTTPS obligatorio en producción; HTTP solo
en local/dev/qa). Sin secretos compartidos, sin autorregistro, sin confianza aportada por el llamador.

### Enrolamiento (fuera de banda, controlado por el vendor)

`central_authority register-installation --installation-id … --public-key-file …` vincula la clave
pública que el operador exporta en la instalación con `python scripts/clave_publica_instalacion.py`
(deriva la pública de la privada del volumen; nunca imprime ni transmite la privada). La autoridad
guarda el PEM y su **huella** (SHA-256 del DER SPKI), única: la misma clave para otra instalación →
`INSTALLATION_KEY_ALREADY_BOUND`; otra clave para la misma instalación → `INSTALLATION_CONFLICT`
(no hay rotación: procedimiento aparte). Nadie se registra solo; una clave que llegue en una petición
se ignora.

### Protocolo (versión `1`)

1. `POST /v1/license/sync/challenge` · cuerpo `{"installation_id": "<id>"}` → `200 {"protocol_version":
   1, "challenge_id": "<uuid opaco>", "nonce": "<64 hex, 256 bits>", "expires_at": "<ISO UTC>"}`.
   Responde igual para una identidad desconocida (la fila queda sin instalación y nunca autentica).
   Caducidad: `KONTROL_CENTRAL_SYNC_CHALLENGE_TTL_SECONDS` (120 s por defecto, 5–900). La autoridad
   guarda el **resumen** del nonce, no el nonce; estado en su PostgreSQL, nunca en memoria.
2. El cliente serializa el cuerpo del sync **una vez** (`canonical_body`: JSON UTF-8, claves ordenadas,
   `separators=(",", ":")`), calcula `body_sha256` (hex minúsculo) de esos bytes y construye el sobre:
   ```json
   {"body_sha256":"…","challenge_id":"…","installation_id":"…","method":"POST","nonce":"…","protocol_version":1,"target":"/v1/license/sync"}
   ```
   (siete campos exactos, claves ordenadas, sin espacios; `app/core/sync_auth_contract.py`, compartido).
   Firma los bytes del sobre con la clave privada de la instalación.
3. `POST /v1/license/sync` con **esos mismos bytes** y cabeceras `X-Kontrol-Sync-Protocol: 1`,
   `X-Kontrol-Installation`, `X-Kontrol-Challenge`, `X-Kontrol-Nonce`, `X-Kontrol-Signature` (hex).
   Sin consulta (`?`) en la URL. El cuerpo de negocio es el del contrato v1 (`version`,
   `installation_id`, `license_jws`, `modules`, `requested_at`); su `installation_id` debe ser el del
   sobre.
4. La autoridad verifica en este orden: versión (`400 SYNC_PROTOCOL_UNSUPPORTED`) → cabeceras →
   destino sin consulta (`401 SYNC_TARGET_MISMATCH`) → desafío bajo `FOR UPDATE`, de esa instalación,
   con ese nonce y esa versión (`401 SYNC_CHALLENGE_INVALID`) → no consumido (`401 SYNC_CHALLENGE_USED`)
   → no caducado (`401 SYNC_CHALLENGE_EXPIRED`) → firma del sobre reconstruido con el hash de los bytes
   **recibidos**, contra la clave pública **del registro** (`401 SYNC_AUTH_INVALID`; una firma inválida
   **no consume** el desafío) → consumo atómico (`UPDATE … WHERE consumed_at IS NULL AND expires_at >
   now`, exactamente una fila, confirmado; dos peticiones idénticas concurrentes → una sola autentica)
   → identidad del cuerpo = identidad del sobre (`403 SYNC_INSTALLATION_MISMATCH`). Identidad
   desconocida y firma inválida comparten `SYNC_AUTH_INVALID`; cuerpo, método o destino alterados también
   acaban en `SYNC_AUTH_INVALID`, porque el servidor los deriva de la petición real. Los errores son
   `{"code", "message"}` y no llevan clave, firma, nonce, registro ni licencia.
5. Respuesta: `{"version": "1", "status": "LICENSE", "server_time": "<ISO UTC>", "license": {"payload",
   "signature_hex"}, "license_id", "revision"}` con el artefacto **exacto** del libro (período más
   reciente, mayor `revision`; nunca por fecha de emisión), o `{"version": "1", "status": "NO_LICENSE",
   "server_time", "license": null}`. Auditoría: `SYNC_CHALLENGE` y `SYNC` con resultado, instalación,
   `challenge_id` y, si procede, emisión.

### En el cliente

`POST /api/v1/licensing/sync` (sesión + `license:create`; sin bloqueo de escritura: renovar en
`READ_ONLY` es legítimo) → `sync_license`: desafío nuevo por intento, firma con la clave canónica de la
instalación, envío de los bytes exactos. Lo recibido pasa por `import_license` con **todas** sus
compuertas (firma del propietario con `KONTROL_LICENSE_PUBLIC_KEY_PEM`, identidad, período, `revision`):
la autenticación remota no sustituye la validación. `server_time` alimenta `last_reliable_date` de
forma monótona; la matriz de módulos sale de `entitlements.modules` del paquete firmado. Sin retroceso
a sync anónimo; sin reintentos ocultos; en `prod`, `server_url` debe ser `https://` (`422
CENTRAL_URL_INSECURE`). Fallos: `503 CENTRAL_UNREACHABLE`, `502 CENTRAL_SYNC_REJECTED`
(`details.central_code`), `502 CENTRAL_RESPONSE_INVALID`, `503 INSTALLATION_KEY_UNAVAILABLE`, y los
códigos de `import_license` si el artefacto no supera las compuertas.

### Fuera de alcance

Rotación de la clave de la instalación o del propietario; mTLS (posible defensa en profundidad de
infraestructura, no contrato).

## Límite de tasa del desafío (FR-010-538..576) — `CENTRAL-SYNC-SIN-LIMITE-DE-TASA`, implementado

`POST /v1/license/sync/challenge` admite `capacity` desafíos dentro de cualquier ventana deslizante de
`window_seconds` (**global** por autoridad; 120/60 s por defecto; `KONTROL_CENTRAL_SYNC_CHALLENGE_RATE_LIMIT_*`;
en `prod` no se apaga). Se decide antes de persistir nada: con la ventana llena → `429 {"code":
"SYNC_RATE_LIMITED", "message": "<genérico>"}` + cabecera `Retry-After: <1..window_seconds>` (segundos
hasta que el desafío más antiguo de la ventana salga de ella). Idéntico para identidad conocida o
desconocida; sin `installation_id`, nonce, recuentos ni estado interno en el cuerpo. Un rechazo no crea
fila, no consume ni altera desafíos emitidos, no escribe auditoría y no toca el registro ni las
emisiones; los desafíos ya emitidos siguen valiendo y `POST /v1/license/sync` no se limita por esta
política. El límite es exacto entre trabajadores/réplicas (estado en PostgreSQL + candado consultivo
transaccional). El cliente trata el 429 como un rechazo acotado (`502 CENTRAL_SYNC_REJECTED`,
`details.central_code = SYNC_RATE_LIMITED`), sin reintentos automáticos. No es protección volumétrica:
el límite por origen va en la pasarela del operador.
