# UAT viva de KONTROL Gobierno para el sponsor · runbook de Infraestructura

**Estado (2026-11-15):** el repositorio está preparado. El despliegue real está **BLOCKED**: falta que Infraestructura entregue el servidor, el dominio, la base de datos, los secretos y la licencia (§2).

Decisiones de la dueña del 2026-11-15:
- preparar el repositorio y este runbook;
- desplegar con un **runner autohospedado** de GitHub Actions en el servidor UAT, sin SSH entrante.

## 1. Cómo funciona

```text
P1/P2 → push a develop → GitHub Actions «build»
  · 4 imágenes (backend, frontend, nginx, clamd), cada una con :latest y :uat-<sha7>
  · verifica que existen las 4 :uat-<sha7>
  → job «deploy-uat» (solo si vars.UAT_DEPLOY_ENABLED == 'true')
      corre en el runner [self-hosted, linux, kontrol-uat] del servidor UAT, environment «uat», sin despliegues en paralelo
      → deploy/uat/deploy.sh: preflight → pull → cabeza Alembic única → respaldo previo → up -d → health de contenedores
        → imágenes = etiqueta nueva → base en la cabeza → health HTTPS → smoke → manifiesto → historial
  → artefacto de CI uat-deploy-uat-<sha7> (manifest.json + deployments.tsv)
```

- La URL del sponsor no cambia; lo que cambia es la etiqueta interna.
- Watchtower no se usa: el profile `watchtower` no se levanta (WATCHTOWER_AUTO_DEPLOY=DISABLED).
- Si un despliegue falla, queda registrado como `DEPLOY_FAILED` y GitHub notifica el job en rojo. No hay rollback ni `alembic downgrade` automáticos sobre los datos del sponsor. La última versión sana es la última fila `DEPLOYED` del historial.

## 2. Lo que debe entregar Infraestructura (bloqueantes)

| # | Elemento | Detalle |
|---|---|---|
| I-1 | Servidor Linux estable | Docker Engine y Compose v2, salida a Docker Hub y GitHub, disco persistente, NTP activo |
| I-2 | Dominio | Registro DNS A/AAAA hacia el servidor (por ejemplo, `kontrol-gobierno-uat.<dominio>`), con los puertos 80 y 443 abiertos para Let's Encrypt y el sponsor |
| I-3 | PostgreSQL 18 exclusiva de UAT | Base y usuario propios. Firewall: solo desde el servidor UAT. No es producción ni QA y no se recrea en cada despliegue |
| I-4 | Runner autohospedado | Registrado en el repositorio con las etiquetas `self-hosted, linux, kontrol-uat`, ejecutado como un usuario del grupo `docker` y no como root |
| I-5 | Entorno GitHub `uat` | Repositorio › Settings › Environments › `uat`. La variable de repositorio `UAT_DEPLOY_ENABLED=true` se activa solo cuando I-1..I-7 estén listos |
| I-6 | Secretos en el servidor | El fichero `/etc/kontrol-uat/uat-env` (§3), propiedad del usuario del runner, con permisos 600 |
| I-7 | Licencia de UAT | La firma el propietario de KONTROL con la Autoridad Central real (no las claves sintéticas de QA). Debe incluir los módulos de Gobierno. Se configura su ancla de confianza pública (PEM + KID) |

Los secretos nunca pasan por Git, por el chat ni por el proveedor externo de IA. Infraestructura los genera y custodia.

## 3. Fichero de secretos `/etc/kontrol-uat/uat-env` (solo nombres)

```text
KONTROL_DB_URL=<postgresql+psycopg2://usuario:clave@host:5432/kontrol_uat>
KONTROL_SECRET_KEY=<aleatoria, ≥ 32 bytes>
KONTROL_MFA_KEYS=<k1:...  (ver instalar.md · Segundo factor)>
KONTROL_BACKUP_KEY=<ver instalar.md · Copias de seguridad; custodiar aparte>
KONTROL_LICENSE_PUBLIC_KEY_PEM=<PEM público del propietario>
KONTROL_LICENSE_PUBLIC_KEY_KID=<kid>
KONTROL_CORS_ORIGINS=["https://<dominio-uat>"]
KONTROL_TZ=America/Caracas
UAT_DOMAIN=<dominio-uat>
UAT_ACME_EMAIL=<correo de Infraestructura para Let's Encrypt>
# Smoke autenticado. Es un usuario propio, de solo consulta en Gobierno, con MFA; no es el usuario del sponsor.
UAT_SMOKE_TENANT=<código>
UAT_SMOKE_USERNAME=<usuario>
UAT_SMOKE_PASSWORD=<clave>
UAT_SMOKE_TOTP_SECRET=<secreto base32 del alta MFA de ese usuario>
UAT_SMOKE_COMPANY_ID=<uuid de la empresa/ente>
UAT_SMOKE_PATHS=/gobierno/modulo,/gobierno/ente,/gobierno/estructuras,/gobierno/actos,/gobierno/contrataciones/expedientes,/gobierno/hallazgos,/gobierno/bitacora
UAT_REQUIRE_AUTH_SMOKE=true
```

- `KONTROL_BACKUP_KEY` la lee solo el respaldo previo, que se ejecuta con `exec -e`. La API residente no la recibe, igual que en `instalar.md`.
- Antes de fijar `UAT_SMOKE_PATHS`, compruebe con el usuario de smoke que cada ruta responde 200.

## 4. Primera publicación (una vez, con intervención)

1. Cumplir I-1..I-4 y I-6. Dejar `UAT_DEPLOY_ENABLED` sin definir.
2. En el servidor, `git clone` del repositorio. Desde la raíz, con el fichero de secretos cargado en el entorno:

   ```bash
   docker compose -f compose.yaml -f deploy/uat/compose.uat.yaml --profile proxy up -d
   ```

   El primer despliegue usa la etiqueta del HEAD publicado (`KONTROL_IMAGE_TAG=uat-<sha7>`, `KONTROL_IMAGE_REGISTRY=<registro>`). Las migraciones se aplican solas.
3. Crear el administrador inicial y activar la licencia I-7 por los mecanismos del producto (`POST /api/v1/license/activate` con sesión y `license:create`). Nada de inserciones directas en la base.
4. Crear, con la UI de administración, dos usuarios con MFA:
   - el del sponsor, con los roles de Gobierno acordados; sus credenciales se le entregan por un canal seguro;
   - el de smoke, de solo consulta.
5. Completar `UAT_SMOKE_*` en el fichero de secretos.
6. Activar la variable `UAT_DEPLOY_ENABLED=true` y relanzar el último run de «build-dev» (o esperar al siguiente push). Ese despliegue ya es automático y deja la primera fila `DEPLOYED`.

Hasta el paso 5 se puede usar `UAT_REQUIRE_AUTH_SMOKE=false`: el smoke queda `MANUAL_PENDING` y no `PASS`. Hay que volver a `true` antes del cierre.

## 5. OBS-09: evidencia Docker externa (una vez, aislada)

En el servidor y desde la raíz del checkout:

```bash
python3 qa/compose_qa.py
```

- Construye su propia composición efímera, con su propia base, y la elimina al terminar. **No toca la base del sponsor ni sus volúmenes.**
- Registrar el bloque `OBS09_EXTERNAL_DOCKER_EVIDENCE` que imprime: versión de clamd, firmas, build, health, subida limpia, EICAR rechazado y fallo cerrado con clamd caído.
- Ejecutarlo antes del primer despliegue o en una ventana sin el sponsor, porque compite por CPU.

## 6. Prohibido contra la UAT

- `docker compose down -v`, `docker volume rm` y `docker system prune --volumes`;
- `alembic downgrade` y `drop database`;
- `qa/e2e-run.py` y cualquier siembra o reseteo;
- el profile `watchtower`;
- publicar 8000, 3310 o PostgreSQL;
- `KONTROL_ENVIRONMENT=prod`;
- imprimir `uat-env`.

## 7. Comprobaciones de cierre (las registra Infraestructura)

```text
UAT_URL=  INITIAL_DEPLOY_SHA=  INITIAL_ALEMBIC_HEAD=  POSTGRES_VERSION=
HTTPS=  FRONTEND_HEALTH=  BACKEND_LIVE=  BACKEND_READY=  CLAMD_HEALTH=
SPONSOR_LOGIN=  MFA=  PERSISTENCE_TEST=  BACKUP_TEST=  AUTO_DEPLOY_FROM_DEVELOP=
DEPLOYMENT_HISTORY_LOCATION=/var/lib/kontrol-uat/deployments.tsv (+ artefacto de CI)
OBS09_EXTERNAL_DOCKER_EVIDENCE=
```

- **Persistencia:** el sponsor crea un dato y se redespliega un push. El dato sigue ahí.
- **Respaldo:** `python -m app.ops.backup verify <paquete>` sobre el respaldo previo del último despliegue, dentro del backend con `exec -T -e KONTROL_BACKUP_KEY`.
- **Redespliegue automático controlado:** un push documental a `develop` debe aparecer en la URL sin trabajo manual, con la fila `DEPLOYED` y el manifiesto con el SHA nuevo.

## 8. Ficheros

| Fichero | Rol |
|---|---|
| `.github/workflows/build-dev.yml` | Build de las 4 imágenes con `uat-<sha7>`, verificación y job `deploy-uat` |
| `deploy/uat/compose.uat.yaml` | Override de UAT: `KONTROL_ENVIRONMENT=uat`, CORS obligatorio, KID de licencia y proxy Caddy (único servicio con 80/443) |
| `deploy/uat/Caddyfile` | TLS automático, HTTP→HTTPS, `/api/v1/*` → kontrol-api:8000 y el resto → kontrol-web:80 |
| `deploy/uat/deploy.sh` | Los 12 pasos, el respaldo previo, el historial y el manifiesto |
| `deploy/uat/smoke.py` | Smoke no destructivo: health, login con MFA, lecturas de Gobierno y cierre de sesión |

## 9. Verificación hecha en el repositorio (2026-11-15)

- `bash -n` de deploy.sh; `py_compile` y ruff de smoke.py; YAML del workflow y del override válidos; vector TOTP RFC 6238 (`287082`) correcto.
- deploy.sh se probó con un `docker` simulado en 7 escenarios:
  - primer despliegue y segundo despliegue con respaldo previo;
  - fallos de smoke, health y backend ausente para el respaldo, cada uno registrado una sola vez y con su paso;
  - permisos del fichero de secretos y etiqueta inválida, ambos rechazados.
  Ningún secreto apareció en la salida.
- Sin probar contra un Docker real: no hay Docker en la estación de desarrollo. La primera ejecución real es la §4. Tampoco se ejecutó shellcheck, porque no está instalado.
- El primer push con este workflow construye y verifica las 4 imágenes `uat-<sha7>`; el resultado consta en GitHub Actions.

## 10. Observaciones abiertas

- **OBS-UAT-SMOKE-LOG-01 (baja):** si el smoke falla, su motivo queda en `/var/lib/kontrol-uat/smoke-<DEPLOY_ID>.log` del servidor, pero no en el log de CI.
- **OBS-UAT-HEALTHZ-01 (por confirmar en el primer despliegue):** el healthcheck del frontend en compose.yaml consulta `/healthz` y el Dockerfile crea `healthz.json`. Se confirma con la primera ejecución real.
