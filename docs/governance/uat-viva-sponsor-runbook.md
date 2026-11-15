# UAT viva de KONTROL Gobierno para el sponsor · runbook de Infraestructura

**Estado:** el repositorio está preparado. La tarea sigue en **BLOCKED_BY_INFRASTRUCTURE** y el sponsor aún no tiene acceso (SPONSOR_UAT_AVAILABLE=NO). Faltan el servidor, PostgreSQL, el DNS, los secretos, la licencia, HTTPS y el acceso del sponsor (§2).

Decisiones de la dueña (2026-11-15):
- preparar el repositorio y este runbook;
- desplegar con un runner autohospedado, sin SSH entrante;
- que un candidato fallido no sustituya nunca a la versión sana (delta final sobre c6b1aaa).

## 1. Estrategia de publicación: validar sobre una copia restaurada y cortar solo después

**Por qué no es blue/green:**
- `compose.yaml` fija los nombres de contenedor (`kontrol-api`, `kontrol-web`, `kontrol-clamd`) y la red `kontrol-net`, así que no pueden convivir dos versiones de la pila principal.
- El backend aplica `alembic upgrade head` sobre la base al arrancar. Una versión candidata que arrancara contra la base real del sponsor la migraría antes de demostrar que funciona.
- Las migraciones de KONTROL no garantizan compatibilidad expand-contract con la versión anterior.

Por eso **el candidato nunca toca la base del sponsor hasta haber pasado la validación**:

```text
green (versión sana) sigue atendiendo en la URL del sponsor durante todo el tramo A
A · VALIDACIÓN DEL CANDIDATO (proyecto Docker aislado «kontrol-cand»)
  4  respaldo B1 desde green (exec -e KONTROL_BACKUP_KEY)
  5  verify B1 → installation_id
  6  PostgreSQL 18.6 efímera (kontrol-cand-db) en volúmenes kontrol-cand-*
  7  restaurar B1 en la copia con la imagen GREEN (misma versión de esquema que la copia)
  8  arrancar backend/frontend/clamd del CANDIDATO sobre la copia → migra la copia → health + cabeza Alembic
  9  smoke autenticado contra la copia (Caddy candidato en 127.0.0.1:18081, solo loopback)
 10  destruir la pila candidata (siempre, también si falla: down -v SOLO del proyecto kontrol-cand)
     Si algo falla en 4–9: DEPLOY_FAILED, FAILED_STAGE=CANDIDATE. El proyecto principal no se toca: green sigue atendiendo.
B · CORTE (solo si A = PASS)
 11  respaldo B2 desde green (respaldo previo al corte)
 12  up -d con la etiqueta nueva → migra la base real (ya ensayado en A sobre una copia del mismo día)
 13  health de contenedores + etiqueta en ejecución + base en la cabeza
 14  health HTTPS + smoke autenticado
 15  manifiesto · 16 historial DEPLOYED
```

Resultados de la estrategia:

```text
CURRENT_GREEN_SHA          = última fila DEPLOYED (PREVIOUS_SHA del historial)
CANDIDATE_SHA              = GIT_SHA de la fila
CANDIDATE_VALIDATION       = PASS | FAILED | FAILED_SIMULATED | FIRST_DEPLOY_NOT_APPLICABLE
TRAFFIC_SWITCH_ONLY_AFTER_PASS=1      (el paso 12 solo se alcanza con CANDIDATE_VALIDATION=PASS)
FAILED_CANDIDATE_REMOVED=1            (down -v del proyecto kontrol-cand en el paso 10 y en el trap)
CURRENT_GREEN_PRESERVED_ON_FAILURE=1  (un fallo de candidato no ejecuta ningún up en el proyecto principal)
```

**Riesgo residual, y es explícito: falla el corte con un candidato ya validado.**
- Es el caso de B, cuando los pasos 13–14 fallan aunque la validación pasó (por ejemplo, red, certificado o datos introducidos entre B1 y B2).
- La versión nueva queda en ejecución y el despliegue queda como `DEPLOY_FAILED` con `FAILED_STAGE=CUTOVER`.
- **No hay recuperación automática ni `alembic downgrade` sobre los datos del sponsor.** La recuperación es manual (§11) con B2 y la etiqueta green.
- El corte tiene una interrupción breve, mientras se recrean los contenedores. Es aceptable en UAT.

**Primer despliegue:** no hay green ni datos que proteger. Se omite A y queda `CANDIDATE_VALIDATION=FIRST_DEPLOY_NOT_APPLICABLE`.

**Defensas en `deploy.sh`:**
- Antes de usar la pila candidata, exige que sus volúmenes sean solo `kontrol-cand-*` o `uat-backups`. Este último es el de respaldos del sponsor, declarado `external` y montado en solo lectura, así que `down -v` no lo borra.
- Exige que `kontrol-api` esté ejecutando la etiqueta green que figura en el historial; si no coincide, aborta por deriva de estado.

## 2. Lo que debe entregar Infraestructura (bloqueantes)

```text
LINUX_SERVER=            DOCKER_ENGINE=           DOCKER_COMPOSE_V2=
DNS=                     PORT_80=                 PORT_443=
POSTGRESQL_18=           GITHUB_SELF_HOSTED_RUNNER=   UAT_ENV_FILE=
REAL_GOVERNMENT_LICENSE=
```

| Elemento | Detalle |
|---|---|
| Servidor | Linux estable, Docker Engine, Compose v2, salida a Docker Hub y GitHub, disco persistente, NTP. Necesita margen para la pila candidata temporal: otra PG, backend, frontend y clamd durante unos minutos |
| DNS + 80/443 | Un registro A/AAAA hacia el servidor. Los puertos 80 y 443 abiertos para Let's Encrypt y el sponsor |
| PostgreSQL 18 | Exclusiva de UAT. Firewall: solo desde el servidor UAT. No es producción ni QA y no se recrea |
| Runner | Etiquetas `self-hosted, linux, kontrol-uat`. Un usuario del grupo `docker`, **no root**. Con escritura en `/var/lib/kontrol-uat` |
| Entorno GitHub `uat` | Settings › Environments › `uat`. La variable de repositorio `UAT_DEPLOY_ENABLED` solo se activa en el §9 |
| Licencia | La firma el propietario con la Autoridad Central real e incluye los módulos de Gobierno. Su ancla pública (PEM + KID) va en el fichero de secretos |

## 3. Secretos: `/etc/kontrol-uat/uat-env` (permisos 600, propiedad del usuario del runner)

Su contenido nunca va a Git, al chat, a tickets ni a proveedores de IA. Estos son solo los nombres:

```text
KONTROL_DB_URL  KONTROL_SECRET_KEY  KONTROL_MFA_KEYS  KONTROL_BACKUP_KEY
KONTROL_LICENSE_PUBLIC_KEY_PEM  KONTROL_LICENSE_PUBLIC_KEY_KID
KONTROL_CORS_ORIGINS=["https://<dominio-uat>"]  KONTROL_TZ=America/Caracas
UAT_DOMAIN  UAT_ACME_EMAIL
UAT_SMOKE_TENANT  UAT_SMOKE_USERNAME  UAT_SMOKE_PASSWORD  UAT_SMOKE_TOTP_SECRET  UAT_SMOKE_COMPANY_ID
UAT_SMOKE_PATHS=/gobierno/modulo,/gobierno/ente,/gobierno/estructuras,/gobierno/actos,/gobierno/contrataciones/expedientes,/gobierno/hallazgos,/gobierno/bitacora
UAT_REQUIRE_AUTH_SMOKE=true
```

- **`KONTROL_BACKUP_KEY` queda fuera del entorno residente del backend**, como fijó la corrección de c6b1aaa. Solo la reciben `exec -T -e KONTROL_BACKUP_KEY` (crear y verificar respaldos) y el servicio efímero `restore` de la pila candidata.
- La contraseña de la PG candidata la genera cada despliegue, nunca se imprime y desaparece con la pila.

## 4. Primera publicación (orden obligatorio)

1. Servidor.
2. PostgreSQL.
3. DNS.
4. Proxy y HTTPS.
5. Primera pila. **El candidato es el HEAD real del momento**, nunca un SHA fijo:

   ```bash
   git fetch origin && git rev-parse origin/develop
   ```

   Se registran INITIAL_DEPLOY_SHA, INITIAL_OWNER_UAT_READY_COUNT (de `OWNER_UAT_READY_CATALOG.md` en ese SHA) e INITIAL_ALEMBIC_HEAD. Desde la raíz del checkout de ese SHA, con `uat-env` cargado:

   ```bash
   KONTROL_IMAGE_REGISTRY=<registro> KONTROL_IMAGE_TAG=uat-<sha7> \
     docker compose -f compose.yaml -f deploy/uat/compose.uat.yaml --profile proxy up -d
   ```

6. Migraciones: son automáticas. Comprobar `alembic current` contra la cabeza.
7. Administrador inicial, por los mecanismos del producto.
8. Licencia real (`POST /api/v1/license/activate`).
9. Configuración de Gobierno.
10. Usuario del sponsor, con los roles acordados. Credenciales por canal seguro.
11. MFA del sponsor.
12. Usuario de smoke, de solo consulta en Gobierno, con MFA. Su secreto TOTP va a `uat-env`.
13. Smoke autenticado: `python3 deploy/uat/smoke.py https://<dominio>` → `PASS`.
14. Persistencia: el sponsor crea un dato, se recrean los contenedores y el dato sigue ahí.
15. Respaldo y verificación: `exec -T -e KONTROL_BACKUP_KEY backend python -m app.ops.backup create --dest /data/backups`, y después `verify <path>`.
16. OBS-09 (§5).
17. Activar el despliegue continuo (§9).

## 5. OBS-09: evidencia Docker real (una vez, aislada)

En el servidor y desde la raíz del checkout: `python3 qa/compose_qa.py`. Crea su propia composición y su propia base efímeras, y las elimina al terminar. **No toca la base ni los volúmenes del sponsor.** Hay que ejecutarlo en una ventana sin uso.

Se registran:

```text
OBS09_EXTERNAL_DOCKER_EVIDENCE=  CLAMD_VERSION=  SIGNATURE_DATABASE_VERSION=
CLEAN_UPLOAD=  EICAR_REJECTED=  CLAMD_DOWN_FAILS_CLOSED=
```

## 6. Prohibido contra la UAT

- `down -v` sobre el proyecto principal, `docker volume rm` y `system prune --volumes`;
- `alembic downgrade` y `drop database`;
- `qa/e2e-run.py` y cualquier siembra o reseteo;
- el profile `watchtower` (WATCHTOWER_AUTO_DEPLOY=DISABLED);
- publicar 8000, 3310 o PostgreSQL;
- `KONTROL_ENVIRONMENT=prod`;
- imprimir `uat-env`.

El único `down -v` permitido es el de la pila candidata, y lo ejecuta `deploy.sh` (`-p kontrol-cand -f deploy/uat/compose.candidate.yaml`).

## 7. Historial, manifiesto y logs

- Historial: `/var/lib/kontrol-uat/deployments.tsv`, una fila por despliegue con estas columnas: DEPLOY_ID, DEPLOY_DATE, GIT_SHA, IMAGE_TAG, ALEMBIC_HEAD, RESULT, FAILED_STAGE, PREVIOUS_SHA, PREVIOUS_TAG, BACKUP_ID, HEALTH, SMOKE, CANDIDATE_VALIDATION y VALIDATION_BACKUP_ID. La última fila `DEPLOYED` es la green vigente.
- Manifiesto: `/var/lib/kontrol-uat/manifest.json` (solo se escribe en un despliegue sano).
- Smoke:
  - el log completo queda en el servidor (`smoke-<etapa>-<id>.log`);
  - el sanitizado (`*.sanitized.log`, con los valores de los secretos y los tokens Bearer ocultos) aparece agrupado en el log de CI y se sube como artefacto;
  - si el smoke falla, su causa aparece como `::error::` en CI (SMOKE_FAIL_REASON_VISIBLE_IN_CI=1).
- Artefacto de CI: `uat-deploy-uat-<sha7>`, con el manifiesto, el historial y los logs sanitizados.

## 8. Ficheros

| Fichero | Rol |
|---|---|
| `.github/workflows/build-dev.yml` | Build de las 4 imágenes con `uat-<sha7>` y verificación. Job `deploy-uat` (runner autohospedado, entorno `uat`, sin despliegues en paralelo, 60 min). `workflow_dispatch` con `simulate_candidate_failure` para el §10 |
| `deploy/uat/compose.uat.yaml` | Override del proyecto principal: `KONTROL_ENVIRONMENT=uat`, CORS obligatorio, KID de licencia y Caddy (único servicio con 80/443) |
| `deploy/uat/Caddyfile` | TLS automático, HTTP→HTTPS, `/api/v1/*` → kontrol-api:8000 y el resto → kontrol-web:80 |
| `deploy/uat/compose.candidate.yaml` | Pila candidata efímera: PG 18.6, `restore` (imagen green), backend, frontend y clamd candidatos, y Caddy en loopback |
| `deploy/uat/Caddyfile.candidate` | Enrutado local del candidato (solo HTTP, solo 127.0.0.1) |
| `deploy/uat/deploy.sh` | Los 16 pasos de §1, el trap con una sola fila y la limpieza del candidato |
| `deploy/uat/smoke.py` | Smoke no destructivo: health, login con MFA, lecturas de Gobierno y cierre de sesión |

## 9. Activación del despliegue continuo

Solo después del §4 completo: crear la variable de repositorio `UAT_DEPLOY_ENABLED=true` y hacer un push controlado (por ejemplo, documental). Se comprueba:

```text
PUSH_DEVELOP=1  BUILD_4_IMAGES=PASS  IMMUTABLE_TAG=PASS  AUTOMATIC_DEPLOY=PASS  DATABASE_MIGRATION=PASS
HTTPS=PASS  AUTHENTICATED_SMOKE=PASS  SPONSOR_DATA_PERSISTS=PASS  DEPLOYMENT_HISTORY=PASS
```

## 10. Prueba obligatoria de fallo (antes de entregar al sponsor)

Con una green ya `DEPLOYED`: GitHub › Actions › «Build and Push Docker Image (develop)» › *Run workflow* sobre `develop` con **simulate_candidate_failure = true**. El candidato recorre el tramo A completo (respaldo, restauración, migración de la copia y health) y falla a propósito en el paso 9. Se comprueba:

```text
CANDIDATE=FAILED                 → fila con CANDIDATE_VALIDATION=FAILED_SIMULATED
DEPLOY_RESULT=DEPLOY_FAILED      → RESULT=DEPLOY_FAILED, FAILED_STAGE=CANDIDATE
SPONSOR_URL_STILL_AVAILABLE=YES  → https://<dominio>/api/v1/health/ready = ok durante y después
PREVIOUS_GREEN_SHA_STILL_SERVING=YES → docker inspect kontrol-api = imagen :<etiqueta green>
DATABASE_NOT_DOWNGRADED=YES      → alembic current = cabeza green; ningún downgrade en el log
SPONSOR_DATA_PRESERVED=YES       → el dato de prueba del sponsor sigue visible
FAILED_CANDIDATE_REMOVED=YES     → docker ps -a / docker volume ls sin kontrol-cand-*
```

## 11. Recuperación manual tras un fallo de corte (FAILED_STAGE=CUTOVER)

La decide y ejecuta Infraestructura, con la dueña informada. Nunca es automática.

1. Leer en el historial `BACKUP_ID` (B2) y `PREVIOUS_TAG` (green) de la fila fallida.
2. Detener el backend nuevo: `docker compose -f compose.yaml -f deploy/uat/compose.uat.yaml --profile proxy stop backend`.
3. Restaurar B2 sobre una base vacía de la PostgreSQL de UAT, que el DBA crea vacía o renombra según su procedimiento. `restore` exige destino vacío y no sobrescribe. Usar la imagen green:

   ```bash
   docker compose ... run --rm -e KONTROL_BACKUP_KEY --entrypoint python backend -m app.ops.backup restore <path B2> --expected-installation-id <ID>
   ```

   con `KONTROL_IMAGE_TAG=<PREVIOUS_TAG>` y `KONTROL_DB_URL` apuntando a la base vacía.
4. Apuntar `KONTROL_DB_URL` en `uat-env` a la base restaurada y levantar con `KONTROL_IMAGE_TAG=<PREVIOUS_TAG>` (`up -d`).
5. Comprobar health y smoke. Registrar la recuperación en el historial a mano, en una fila `DEPLOYED` con la etiqueta green, para que el siguiente despliegue la tome como green.

Los datos que el sponsor introdujo entre B2 y el fallo se pierden; por eso hay que avisarle.

## 12. Cierre (no se cierra sin estos valores)

```text
UAT_URL=  ACTIVE_GIT_SHA=  ALEMBIC_HEAD=  POSTGRES_VERSION=
HTTPS=PASS  FRONTEND_HEALTH=PASS  BACKEND_LIVE=PASS  BACKEND_READY=PASS  CLAMD_HEALTH=PASS
SPONSOR_LOGIN=PASS  SPONSOR_MFA=PASS  AUTHENTICATED_SMOKE=PASS
PERSISTENCE_TEST=PASS  BACKUP_CREATE=PASS  BACKUP_VERIFY=PASS
OBS09_EXTERNAL_DOCKER_EVIDENCE=PASS
AUTO_DEPLOY_FROM_DEVELOP=PASS  FAILED_DEPLOY_PRESERVES_LAST_GREEN=PASS  DEPLOYMENT_HISTORY=PASS
WATCHTOWER_AUTO_DEPLOY=DISABLED  PRODUCTION_TOUCHED=0  SECRET_EXPOSURE=0  SNAT_TOUCHED=0
```

Mientras no estén: `INFRASTRUCTURE_STATUS=BLOCKED_BY_INFRASTRUCTURE`, `SPONSOR_UAT_AVAILABLE=NO`.

## 13. Verificación hecha en el repositorio y observaciones

- Pasan `bash -n`, YAML válido (workflow, override y pila candidata), ruff y py_compile de smoke.py, y el vector TOTP de la RFC 6238. El healthcheck de clamd candidato entrega `zPING\\0` igual que compose.yaml.
- `deploy.sh` (16 pasos) se probó con un `docker` simulado:
  - primer despliegue, y segundo con candidato PASS y corte;
  - candidato fallido de forma simulada (§10), por smoke y por restauración: ningún `up` en el proyecto principal, green sigue ejecutándose y la pila candidata se elimina;
  - volumen ajeno en la pila candidata: rechazado antes de empezar;
  - fallo de corte: `FAILED_STAGE=CUTOVER`, mensaje de recuperación manual y causa visible como `::error::`;
  - 14 columnas en cada fila, una sola fila por despliegue, ningún secreto en CI ni en los artefactos.
- **Sin probar contra un Docker real.** La primera prueba real son el §4 y el §10. Tampoco se ejecutó shellcheck.
- **OBS-UAT-HEALTHZ-01: CLOSED.** `resources/nginx/nginx.conf` declara `location = /healthz { return 200 … }`; el `healthz.json` del Dockerfile es adicional.
- **OBS-UAT-SMOKE-LOG-01: CLOSED.** La causa sanitizada aparece en CI, el log completo queda en el servidor y el sanitizado va al artefacto.
- **Nota:** la salida de `smoke.py --solo-health` va sin sanitizar. Ese modo termina antes de leer cualquier credencial (smoke.py líneas 135 y 161), así que no puede contener secretos.
