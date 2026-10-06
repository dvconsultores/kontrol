# SPEC 004 · DELTA DIRIGIDO — EL ANCLA DE CONFIANZA ES LA CLAVE DEL PROPIETARIO

> Iniciado el 2026-10-06. Dueño: **Spec 004 global — Licenciamiento**
> (`spec-equivalence-map.md` línea 11: «004 Licenciamiento · `001-fundacion` +
> `010-licenciamiento-central`»). Vive junto a `spec004-licencia-import-delta.md`. No se crea
> otra Spec. Cierra `LICENCIA-ANCLA-AUTOFIRMADA`.
>
> Este delta es de **frontera de confianza criptográfica**: quién es el emisor en quien la
> instalación confía. Algoritmo, formato de firma, canonicalización, payload, identidad de
> instalación, fechas y `America/Caracas` **no se tocan**. `LICENCIA-DOWNGRADE-FIRMADO`
> (si una licencia válida es más nueva o más vieja que la vigente) **sigue abierta**.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `f096b1d` / **`f096b1d`** / `f096b1d` / `develop` / limpio · `COMMITS_AFTER_F096B1D = 0` · 0 bases de corrida |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 · `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2` |
| `PRIMARY_OWNER` | **SPEC004** — `010-licenciamiento-central` (aquí) + `001-fundacion` (FR-001-050: «verifica la firma de la licencia … con la clave pública»; FR-001-055: «la clave privada del propietario no reside en la instalación») |
| `SECURITY_OWNER` | Master 002 → `001-fundacion` |
| `INSTALLATION_OWNER` | Master 052 → `001-fundacion`: **aplica**, porque el ancla se provisiona desde el despliegue (`compose.yaml`, `.env.example`) y los guiones de instalación activan una licencia de prueba |
| `QA_OWNER` | SPEC054 → `012-auditoria-integral-e2e`: el lanzador E2E y los ayudantes cambian |
| `OWNER_IDENTITY_CONFLICT` | **0** |

**Decisión de la dueña, ya tomada:** en producción el ancla del propietario/vendedor debe estar
configurada y, si falta, se falla cerrado; la clave de la instalación nunca es ancla; los
mecanismos sintéticos de prueba son explícitos, identificados como solo-prueba, imposibles en
producción y nunca un fallback silencioso; `qa/licencia_firmada.py` puede quedarse si firma con
un firmante cuya pública se declara explícitamente como ancla de esa corrida.

## 2. Inventario del material de confianza (W05–W13)

| Símbolo | Fichero | Propósito | Origen | Entornos | Secreto | Producto o prueba | Fallback |
|---|---|---|---|---|---|---|---|
| `Settings.license_public_key_pem` | `app/core/config.py` | **ancla del propietario**: clave pública Ed25519 con la que la instalación verifica cada licencia | `KONTROL_LICENSE_PUBLIC_KEY_PEM` (entorno); `compose.yaml` la pasa desde el `.env` del despliegue, opcional (`:-`); `.env.example` decía «opcional; si falta se usa la clave de la instalación» | todos | no (pública) | producto | **sin validación**: ausente → `None` |
| `Settings.environment` | `app/core/config.py` | entorno: `local\|dev\|qa\|uat\|staging\|prod`; `compose.yaml` por defecto **`prod`** | entorno | — | no | producto | — |
| `Settings._secret_key_not_default` | `app/core/config.py` | **precedente**: configuración de seguridad obligatoria que **falla al inicio** si falta («obligatoria: falla al inicio si falta») | validador pydantic | todos | — | producto | — |
| `Installation.public_key` · `installation_private_key.pem` | `organization/models.py` · `licensing/service.py::get_or_create_installation` | **identidad de la instalación**: el par Ed25519 que la instalación genera en el primer arranque; la pública viaja en `GET /license/installation-request` para que el propietario emita la licencia; la privada queda en `installation_volume_path` con `0600` | generado por la instalación | todos | privada: sí | producto | — |
| `import_license` línea 174 | `licensing/service.py` | verificar la firma del artefacto | `get_settings().license_public_key_pem **or installation.public_key**` | todos | — | producto | **sí: la clave de la propia instalación** |
| `verify_license_signature` · `load_public_key` | `app/core/license.py` | verificación Ed25519; una PEM que no parsea devuelve `False` (se confunde con firma inválida); una clave de otro tipo (RSA) lanzaría `TypeError` → 500 | — | — | — | producto | — |
| `public_key_from_settings` | `app/core/license.py` | devuelve el ancla configurada; **sin usos** | — | — | — | producto | — |
| Sincronización central (`sync_license`) | `licensing/service.py` | envía `license_jws` al servidor central; **no verifica firmas** localmente; `LicenseCentralConfig.public_key` es la del servidor central, para otro contrato | — | — | — | producto | ninguno |
| Clave **privada** del propietario | — | **no existe en el repositorio ni en la instalación** (FR-001-055): firma fuera, en el propietario | — | — | — | — | `OWNER_PRIVATE_KEY_IN_CLIENT = 0` |
| `scripts/setup.sh` paso 6 · `scripts/activate-test-license.sh` | guiones de despliegue | licencia **de prueba** «autofirmada con la clave privada de la propia instalación (solo válida mientras `KONTROL_LICENSE_PUBLIC_KEY_PEM` esté vacío)» | leen `installation_private_key.pem` dentro del contenedor | el que tenga el contenedor (**`prod` por defecto**) | — | prueba, **apoyada en el fallback** | — |
| `qa/pg-e2e-seed.py` | siembra E2E | genera un par efímero por proceso, declara su pública en el entorno **de ese proceso** e importa; el backend de la corrida arranca después **sin** ancla | generado | QA | — | prueba (explícito) | — |
| `qa/licencia_firmada.py` (ciclo anterior) | ayudante E2E | firmaba con **la clave de la instalación de la corrida**, contando con el fallback | volumen de la corrida | QA | — | prueba, **apoyada en el fallback** | — |
| `qa/*-bootstrap.py`, `qa/perf-smoke.py`, `qa/repro-*.py`, `tests/audit_world.py`, `tests/test_licensing_central.py`, `tests/test_spec004_installation_race.py` | QA y pruebas | generan un par y lo **declaran explícitamente** en el entorno antes de importar | generado | QA/test | — | prueba (explícito) | ninguno |
| Rotación de claves | — | `license_public_key_kid` y `kid` en el payload existen, **sin** verificación por `kid` ni haz de claves | — | — | — | — | no se inventa (§12) |

**Dos claves, dos papeles:** (A) la **del propietario** autentica al emisor y es externa a la
instalación; (B) la **de la instalación** la identifica ante el propietario. El defecto es que
(B) sustituía a (A) cuando (A) faltaba. `INSTALACION-KEY-REFERENCE-120` (la referencia a esa
clave) no se toca.

### Reproducción, antes del arreglo (`evidence/licencia-ancla/antes.txt`)

Mundo nuevo, **`KONTROL_ENVIRONMENT=prod`**, sin `KONTROL_LICENSE_PUBLIC_KEY_PEM`, volumen con la
clave privada que la propia instalación generó. El administrador (`license:create`) importa una
licencia firmada **con esa clave**: `200 {"ok":true,"license_id":"LIC-AUTOFIRMADA","mode":
"FULL_ACCESS"}`, estado hasta 2036 con `{'companies': 999, 'users': 9999}`. Idéntico en `local`.

`OWNER_KEY_CONFIGURED = False` · `INSTALLATION_KEY_AVAILABLE = True` · `FALLBACK_USED = True` ·
`SELF_SIGNED_TEST_LICENSE_ACCEPTED = True` · **causa raíz probada en modo producción**.

QA/E2E: la siembra declaraba su propio ancla efímera en su proceso (correcto), pero el backend de
la corrida arrancaba sin ancla y `qa/licencia_firmada.py` firmaba con la clave de la instalación:
E2E-LICIMP-04 dependía del fallback.

## 3. Modelo de amenaza

| Actor | Antes | Después |
|---|---|---|
| Quien pueda leer `installation_private_key.pem` (respaldo del volumen, acceso al servidor, imagen copiada) en una instalación sin ancla configurada | se emite a sí mismo una licencia de diez años con los derechos que quiera | la instalación no verifica nada sin ancla del propietario (503) y en `prod` ni arranca sin ella |
| Despliegue en `prod` que olvida la variable | funciona y acepta autofirmadas | el backend **no arranca**, con el nombre de la variable en el error |
| Operador con un ancla rota (PEM corrupta, clave RSA) | corrupta → «firma inválida» engañosa; RSA → 500 | 503 `LICENSE_TRUST_ANCHOR_INVALID`, sin material en la respuesta ni en el registro |
| Atacante que pega su clave pública dentro del artefacto | nunca se usó | sigue sin usarse: el ancla es la configurada |
| QA | dependía del fallback | firmante sintético explícito por corrida |

## 4. `/speckit.specify`

FR-010-148..171 (los FR-TRUST-001..024 del encargo, uno a uno):

| FR | Requisito |
|---|---|
| FR-010-148 | En producción, la licencia se verifica **exclusivamente** contra el ancla del propietario configurada fuera de la instalación (`KONTROL_LICENSE_PUBLIC_KEY_PEM`) |
| FR-010-149 | La clave de la instalación no es fallback del ancla, en producción ni en ningún entorno |
| FR-010-150 | Sin ancla en producción: la configuración no carga y el backend no arranca (contrato existente de `secret_key`); en cualquier entorno, la importación falla cerrada (503 `LICENSE_TRUST_ANCHOR_MISSING`) |
| FR-010-151 | Un ancla que no parsea o no es Ed25519 nunca activa un fallback: 503 `LICENSE_TRUST_ANCHOR_INVALID` (y en `prod`, fallo al inicio) |
| FR-010-152 | El sistema no genera ni se fabrica un ancla propia para certificarse |
| FR-010-153 | La clave de la instalación conserva solo su papel: identidad y solicitud de activación |
| FR-010-154 | QA/test usan un ancla sintética **explícita**: la pública del firmante que la corrida genera, declarada en el entorno del backend de esa corrida |
| FR-010-155 | Ningún mecanismo de prueba se habilita en producción: la licencia de prueba de los guiones se niega en `prod` y nada depende de la ausencia de configuración |
| FR-010-156 | `qa/licencia_firmada.py` se conserva firmando con el firmante sintético de la corrida, nunca con la clave de la instalación |
| FR-010-157 | La autorización del llamador (`license:create`) sigue independiente y **antes** de la verificación del artefacto |
| FR-010-158 · 159 | Firma inválida → 423 `LICENSE_SIGNATURE_INVALID`; otra instalación → 423 `LICENSE_INSTALLATION_MISMATCH`, como hoy |
| FR-010-160 · 161 · 162 | Sin cambios de algoritmo, formato de firma, payload, canonicalización, fechas ni zona horaria |
| FR-010-163 · 164 · 165 | `/license/status` público y mínimo (sin detalle de seguridad) · diagnóstico con sesión + `license:view` · health como quedaron |
| FR-010-166 | Sin esquema ni migración |
| FR-010-167 | `LICENCIA-DOWNGRADE-FIRMADO` no se resuelve aquí |
| FR-010-168 | Existen pruebas que fallan si se reintroduce la confianza en la propia clave |
| FR-010-169 | Certificación E2E con `qa/e2e-run.py`, base efímera y ancla sintética explícita por corrida |
| FR-010-170 | No hay clave privada del propietario en la instalación |
| FR-010-171 | El contrato arranque/petición está definido por el repositorio: no hay decisión material abierta |

## 5. `/speckit.clarify` — 32 preguntas

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Dueña | SPEC004 (`010` + `001`); apoyos 002, 052, 054 |
| 2–3 | Origen del ancla y del fallback | `KONTROL_LICENSE_PUBLIC_KEY_PEM`; fallback en una línea de `import_license` |
| 4–5 | Papel de cada clave | instalación: identidad y solicitud; propietario: emisor confiable |
| 6 | Clave privada del propietario | fuera de la instalación; no está en el repo ni en el runtime |
| 7 | Verificador | `verify_license_signature(payload, firma, pem)`; nuevo `trust_anchor.load_trust_anchor` lo precede y distingue `missing`/`invalid` |
| 8–9 | Hoy en producción y en QA | acepta autofirmadas (§2); QA dependía del fallback en el ayudante |
| 10–12 | Firmante E2E, ayudante, lanzador | la corrida genera un par; la pública va al backend, la siembra y la suite; la privada queda en el estado efímero (`0600`) para la siembra y el ayudante |
| 13–14 | Detección de entorno | `Settings.environment` con patrón cerrado; `prod` es producción; `local/dev/qa` son los de QA (guardas ya existentes en `qa/*`) |
| 15 | Mecanismo explícito de ancla de prueba | la misma variable `KONTROL_LICENSE_PUBLIC_KEY_PEM`, poblada por quien firma (lanzador, siembra, guiones) con su firmante sintético: nada nuevo ni genérico |
| 16–17 | Ancla ausente/inválida | 503 con código propio; sin evento de licencia (no es un artefacto malo); registro sin material |
| 18 | ¿Arranque o petición? | **ambos**, por contrato existente: `secret_key` fija «obligatoria: falla al inicio» para configuración de seguridad en `prod`; fuera de `prod` el backend arranca y la importación falla cerrada. Sin decisión material |
| 19 | Readiness | sin cambio: `ready` no habla de licencia (D4, cerrado) y nada contractual lo pide; en `prod` sin ancla no hay proceso que responder |
| 20 | Estado público | sin cambio ni mención del ancla |
| 21–22 | Regresiones de llamador e identidad | TRUST-06/07, 05 |
| 23 | Criptografía | sin cambios |
| 24 | Rotación | no existe (`kid` sin verificación); no se inventa; se anota en §12 |
| 25–26 | Provisión y secreto | entorno/`.env` del despliegue; es pública; `compose.yaml` sigue `:-` para que `local/dev/qa` arranquen sin ella (el validador la exige solo en `prod`) |
| 27 | Registro | una línea `warning` con el motivo (`missing`/`invalid`), sin PEM, firma ni rutas |
| 28 | Esquema | 0 |
| 29–31 | Pruebas | `tests/test_license_trust_anchor.py` (hostiles, dos motores), `tests/test_settings_trust_anchor.py` (validador puro), sonda del lanzador en `tests/test_e2e_corrida.py`; E2E dirigido y global; 9 mutaciones |
| 32 | DeepSeek | solo las pruebas puras del validador (T05) |

`MATERIAL OQ = 0`: arranque/petición y ancla de prueba explícita están resueltos por el repositorio.

## 6. `/speckit.plan` y compuerta

**Backend.** `app/core/trust_anchor.py` (nuevo): `TrustAnchorError(reason)` y
`load_trust_anchor(pem) -> Ed25519PublicKey`, sin fallback. `config.py`: `model_validator` que en
`prod` exige y carga el ancla (mismo contrato que `secret_key`). `licensing/service.py`: el ancla
se carga **antes** de mirar el artefacto; ausente/inválida → 503 sin evento; la línea `or
installation.public_key` desaparece; `logger.warning` sin material.

**QA.** `qa/e2e_corrida.py`: `generar_firmante()` al crear la base; el entorno de todos los procesos
lleva `KONTROL_LICENSE_PUBLIC_KEY_PEM` (pública del firmante) y `KONTROL_E2E_LICENSE_SIGNING_KEY`
(privada en el estado efímero, `0600`). `qa/pg-e2e-seed.py`: usa ese firmante si existe; si no
(siembra manual), uno efímero declarado explícitamente; se niega fuera de `local/dev/qa`.
`qa/licencia_firmada.py`: firma con el firmante de la corrida. `scripts/setup.sh` y
`activate-test-license.sh`: firmante efímero explícito, se niegan en `prod`. `.env.example`.

**Compuerta (G01–G28):** HEAD, orquestación, dueña ✅ · fallback reproducido en `prod` y `local` ✅
· papeles de las claves, clave privada del propietario ausente ✅ · verificador, provisión,
firmante QA, mecanismo explícito, entorno ✅ · contrato arranque/petición por precedente ✅ ·
readiness y estado público sin cambio ✅ · autorización del llamador intacta ✅ · criptografía
intacta, downgrade fuera ✅ · esquema = migración = 0 ✅ · pruebas, mutaciones, tareas ✅ ·
`MATERIAL OQ = 0`, `UNKNOWN = 0`, trazabilidad 100 % ✅. Constitución: P1, P2, P3, P6, P9
(instalación independiente: su identidad no es su licencia), P10, P12, P14 (infraestructura
reproducible: el despliegue declara el ancla), P15, P21, P24, P27 ✅; P26 no aplica.

## 7. Pruebas y mutaciones

**`tests/test_license_trust_anchor.py`** (mundo `local`, ancla sintética en el entorno, se quita o
se sustituye por prueba): TRUST-01 con el ancla del propietario, su licencia entra · 02 sin ancla:
503 `LICENSE_TRUST_ANCHOR_MISSING`, sin evento, sin sustituto · 03 sin ancla, autofirmada con la
clave de la instalación → 503 (nunca se verifica) · 03b con ancla, la autofirmada → 423 · 04 otra
autoridad → 423 · 04b una clave pública pegada en el payload no es ancla → 423 · 05 otra
instalación → 423 · 06/07 orden: 401/403 antes que el ancla; con el ancla, 200 y un solo evento ·
10 ancla malformada, PEM basura, en blanco → 503 `INVALID`/`MISSING`, sin caer en la clave propia ·
10b clave RSA → 503 `INVALID`, no 500 · 11 sin ancla no se fabrica una ni se toca el volumen · 12
la clave de la instalación no cambia y sigue en la solicitud de activación · 09 registros sin
material · 06..08 estado público, diagnóstico y health sin cambios.

**`tests/test_settings_trust_anchor.py`** (DeepSeek, puro): CFG-01 `prod` sin ancla no carga · 01b
en blanco · 02 no-PEM · 03 RSA · 04 con ancla carga · 05 fuera de `prod` no es obligatoria al
arrancar · 06 el error no lleva material · 07 el cargador distingue `missing` de `invalid` · 08 (Claude) el error de arranque no reproduce `secret_key` ni el ancla.

**Sonda del lanzador** (`tests/test_e2e_corrida.py`): el entorno de la corrida lleva el ancla
pública y el firmante existe con `0600`.

**E2E**: dirigido `licencia-import` + `licencia` + `diagnostico` (24) con el ancla explícita de la
corrida; dos globales.

**Mutaciones:** M-01 restaurar `or installation.public_key` → TRUST-03 · M-02 aceptar ancla ausente
(saltar la carga) → TRUST-02 · M-03 el validador ignora el entorno → CFG-01 · M-04 confiar en la
clave del payload → TRUST-04b · M-05 saltar la identidad → TRUST-05 · M-06 quitar la autorización →
LICIMP-01 · M-07 el ayudante firma con la clave de la instalación → E2E-LICIMP-04 (dirigido) ·
M-08 registrar el PEM → TRUST-09 · M-09 fallback al fallar el parseo → TRUST-10.

## 8. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T01 | Reconciliación, inventario, reproducción (`prod` y `local`), amenaza, diseño | todos | CLAUDE | YES | n-a | este documento, `evidence/licencia-ancla/antes.txt` |
| T02 | `trust_anchor.py`, validador en `config.py`, `import_license` sin fallback | 148–153, 157 | CLAUDE | **YES** | n-a | `app/core/`, `licensing/service.py` |
| T03 | `tests/test_license_trust_anchor.py` | 168 | CLAUDE | **YES** | n-a | `tests/` |
| T04 | Lanzador con firmante por corrida; siembra; `licencia_firmada.py`; guiones; `.env.example`; sonda | 154–156, 169 | CLAUDE | **YES** | n-a | `qa/`, `scripts/`, `.env.example`, `tests/test_e2e_corrida.py` |
| T05 | `tests/test_settings_trust_anchor.py` CFG-01..07 | 150, 151 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES (claves generadas en la prueba) | nuevo |
| T06 | Auditar y aplicar T05; mutaciones M-01..M-09 | 168 | CLAUDE | NO | n-a | — |
| T07 | Backend dirigido y completo (dos motores); E2E dirigido y globales | 169 | CLAUDE | NO | n-a | — |
| T08 | `analyze` final, trazabilidad, convergencia, hoja de ruta, Git | — | CLAUDE | NO | n-a | documentos |

`RETRY_MAX: 2` en T05; su encargo lleva interfaces y nombres de prueba; las claves se generan en la
prueba. `analyze` previo: `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0;
huérfanos = 0; `MATERIAL OQ` = 0; `UNKNOWN` = 0; trazabilidad 100 % (§14).

**Autorización de `implement`:** la del encargo `LICENCIA-ANCLA-AUTOFIRMADA`, cumplidas sus
condiciones.

## 9. Implementación

**Backend (T02, Claude).** `app/core/trust_anchor.py` (nuevo, 40 líneas): `TrustAnchorError(reason)`
—`missing` o `invalid`, nunca con el material— y `load_trust_anchor(pem)`, que exige una clave
pública **Ed25519** en PEM y no tiene sustituto. `app/core/config.py`: `model_validator` que en
`prod` carga el ancla y, si falta o no sirve, hace fallar `Settings` con «`KONTROL_LICENSE_PUBLIC_KEY_PEM`
es obligatoria en prod … (ancla missing|invalid)»: el mismo contrato de `secret_key`. Fuera de
`prod` la configuración carga. Además `hide_input_in_errors=True` en `Settings`: pydantic reproduce por
defecto el valor de entrada en el error, y aquí ese valor es toda la configuración —con `secret_key`
y el ancla dentro— camino del registro de arranque (visto al generar `despues.txt`; CFG-08 lo fija). `licensing/service.py::import_license`: carga el ancla **antes** de
mirar el artefacto; ausente o inválida → `KontrolError` 503 `LICENSE_TRUST_ANCHOR_MISSING|INVALID`,
sin evento de licencia (no es un artefacto malo) y con un `warning` que solo lleva el motivo; la
línea `or installation.public_key` desaparece. `core/license.py`, payload, canonicalización,
`models.py`, `alembic/`: sin cambios.

**QA (T04, Claude).** `qa/e2e_corrida.py`: `generar_firmante()` al crear la base —par Ed25519 por
corrida; la privada en `<estado>/license/qa_license_signing_key.pem` con `0600`; la pública es el
`KONTROL_LICENSE_PUBLIC_KEY_PEM` de la siembra, del backend y de la suite; `KONTROL_E2E_LICENSE_SIGNING_KEY`
apunta a la privada—. `qa/pg-e2e-seed.py`: usa el firmante de la corrida si existe, si no uno
efímero declarado explícitamente; se niega fuera de `local/dev/qa`. `qa/licencia_firmada.py`: firma
con el firmante de la corrida; ya no conoce la clave de la instalación. `scripts/setup.sh` y
`activate-test-license.sh`: la licencia de prueba la firma un firmante efímero cuya pública se
declara en ese proceso; **se niegan en `prod`** con el mensaje de qué configurar. `.env.example`:
obligatoria en `prod`, nunca sustituida. Sonda del lanzador en `tests/test_e2e_corrida.py`.

**T05 (DeepSeek `deepseek-v4-flash`, 2 086/2 028 tokens, $0,0008, `AUDIT_PASS` al primer intento,
fichero nuevo):** `tests/test_settings_trust_anchor.py`, 12 ejecuciones, más CFG-08 de Claude (el error de arranque no reproduce la configuración). **T03 (Claude):**
`tests/test_license_trust_anchor.py`, 16.

Reintentos: 0. Rechazos: 0. Coste DeepSeek: **$0,0008**. Egress: interfaces y nombres de prueba;
las claves se generan en la prueba. `EGRESS_CHECK` a cero. Frontend de producto: **0 cambios**
(no hay flujo de licencia en la UI que toque el ancla); no se corre la suite de frontend por ritual.

## 10. Pruebas y mutaciones

`evidence/licencia-ancla/mutaciones-backend.txt`, cada una GOOD→PASS, MUTATED→FAIL, RESTORED→PASS:

| Mutación | La mata |
|---|---|
| M-01 vuelve `or installation.public_key` | TRUST-03 |
| M-02 se acepta un ancla ausente | TRUST-02 |
| M-03 el validador ignora el entorno | CFG-01 |
| M-04 se confía en la clave que trae el artefacto | TRUST-04b |
| M-05 no se comprueba la instalación | TRUST-05 |
| M-06 `/license/activate` sin autorización | LICIMP-01 |
| M-07 el ayudante firma con la clave de la instalación (E2E, base nueva) | E2E-LICIMP-04 y 06: 2 fallos / 6 |
| M-08 el registro lleva el material del ancla | TRUST-09 |
| M-09 un ancla que no parsea cae en la clave de la instalación | TRUST-10 |

**9/9 muertas**, todas con cambio observable.

## 11. Resultados

### El contrato, después (`evidence/licencia-ancla/despues.txt`)

`prod` sin ancla: `Settings` no carga —«KONTROL_LICENSE_PUBLIC_KEY_PEM es obligatoria en prod …
(ancla missing)»— y el backend no arranca. `local` sin ancla: el administrador con una licencia
firmada con la clave de la propia instalación recibe **503 `LICENSE_TRUST_ANCHOR_MISSING`**, estado
`ninguno`, 0 eventos. `OWNER_KEY_CONFIGURED = False` → `FALLBACK_USED = False` →
`SELF_SIGNED_TEST_LICENSE_ACCEPTED = False`.

### Certificación E2E, base nueva por corrida y ancla explícita (`corridas-globales.txt`)

| Corrida | Resultado |
|---|---|
| Dirigida: `licencia-import` + `licencia` + `diagnostico` | **24/24** (el ayudante firma con el firmante de la corrida; el backend confía solo en su pública) |
| Mutante M-07 | 2 fallos / 6: E2E-LICIMP-04 y 06 (el artefacto firmado con la clave de la instalación es ahora «firma inválida») |
| Global 1 | **224 / 0 / 40** (147,6 s) |
| Global 2 | **224 / 0 / 40** (164,1 s) |
| Tras hacer idempotente el firmante (§11, backend): la máquina se reinició a mitad de la dirigida de verificación (clúster y `/tmp` perdidos, 0 bases huérfanas); reprovisionado, dirigida **24/24** y Global 3 **224 / 0 / 40** |

Limpieza `LIMPIA`, 0 bases de corrida al terminar; la clave privada del firmante vive y muere con
el estado efímero de la corrida.

### Backend (`backend-y-frontend.txt`)

| Suite | Resultado | Línea base |
|---|---|---|
| Backend SQLite, completa | **44 fallos / 1 111 pasan / 1 005 omitidas** (119 s): 42 de documentos sin `clamscan` + las dos intermitentes de hilo de SQLite (`test_auth_session_rotation`, `test_warehouse_structure`), ya atribuidas en el ciclo anterior. Composición de línea base; +29 ejecuciones nuevas. (Una corrida previa al reinicio: 42 / 1 113 / 1 005) | 42 docs sin `clamscan` + 1–2 intermitentes de hilo |
| Backend PostgreSQL, completa | **37 fallos / 2 096 pasan / 27 omitidas** (12 min): 10 + 25 de documentos sin `clamscan`, 2 de `test_n9_integrity`. Composición idéntica a la línea base; `test_e2e_corrida.py` 14/14. (La corrida previa al reinicio dio 38: `test_e2ecorrida_13` pedía el entorno sin firmante generado; corregido haciéndolo idempotente y a demanda) | 37: docs sin `clamscan` + 2 de `test_n9_integrity` |
| Seguridad de licencia dirigida (6 ficheros) | **139/139** en PostgreSQL; `trust_anchor` 16/16 y `settings` 12/12 en SQLite | |
| `ruff` · `mypy` (ficheros tocados) | limpios | |

## 12. Deudas

**Cerrada:** `LICENCIA-ANCLA-AUTOFIRMADA`.

**Sigue abierta, no tocada:** `LICENCIA-DOWNGRADE-FIRMADO` (monotonicidad), `INSTALACION-KEY-REFERENCE-120`.

**Nueva, registrada sin absorber:**

| Deuda | Qué es | Dueña |
|---|---|---|
| `LICENCIA-SIN-ROTACION-DE-CLAVE` | el ancla es **una** clave; `license_public_key_kid` y el `kid` del payload existen pero no se comprueban ni hay haz de claves ni solapamiento: rotar la clave del propietario obliga a cambiar la variable en cada instalación y deja sin verificar las licencias firmadas con la anterior. No se inventa rotación aquí | 004 |

**Observación, dentro de lo cerrado:** `public_key_from_settings` en `core/license.py` no tiene usos;
se deja (no es de este delta borrarlo).

## 13. Veredicto

**`LICENCIA-ANCLA-AUTOFIRMADA`: cerrada.** La instalación verifica cada licencia solo contra la
clave pública del propietario, configurada fuera de ella. La clave de la instalación identifica a la
instalación y nada más. Sin ancla, o con una que no es una clave Ed25519 válida, no hay verificación:
en `prod` el backend no arranca; en cualquier entorno la importación responde 503 sin sustituto, sin
evento y sin generar nada. QA firma con un firmante sintético por corrida cuya pública declara
explícitamente como ancla de esa corrida; los guiones de prueba se niegan en `prod`. Autorización
del llamador, firma, identidad, fechas, zona horaria y criptografía intactas.

| | |
|---|---|
| `INSTALLATION_KEY_AS_OWNER_FALLBACK` · `PRODUCTION_OWNER_ANCHOR_OPTIONAL` · `SELF_SIGNED_INSTALLATION_LICENSE_ACCEPTED` · `INVALID_OWNER_KEY_FALLBACK` | 0 |
| `TEST_TRUST_ENABLED_IN_PRODUCTION` · `OWNER_PRIVATE_KEY_IN_CLIENT` · `DYNAMIC_TRUST_FROM_LICENSE_ARTIFACT` | 0 |
| `CALLER_AUTH_REGRESSION` · `INSTALLATION_IDENTITY_REGRESSION` · `PUBLIC_STATUS_REGRESSION` · `DIAGNOSTICS_REGRESSION` · `HEALTH_REGRESSION` | 0 |
| `CRYPTO_ALGORITHM_CHANGE` · `LICENSE_PAYLOAD_CHANGE` · `BUSINESS_TIMEZONE_CHANGE` · `DOWNGRADE_SCOPE_EXPANSION` · `PRODUCT_SCHEMA_CHANGE` · `PRODUCT_MIGRATION` | 0 |
| `SECRET_EXPOSURE` · `RETRY_WORKAROUND` · `SLEEP_WORKAROUND` · `SKIP_WORKAROUND` | 0 |
| `STATUS` | **`CONVERGED`** |

## 14. `analyze` final y trazabilidad

| Requisito | Prueba o evidencia | |
|---|---|---|
| FR-010-148, 149 solo el ancla del propietario; nunca la de la instalación | TRUST-01, 03, 03b; M-01; `despues.txt` | ✅ |
| FR-010-150 sin ancla: no arranca en `prod`; 503 al importar | CFG-01, 01b, 05; TRUST-02; M-02, M-03 | ✅ |
| FR-010-151 ancla inválida: sin fallback, sin 500 | CFG-02, 03; TRUST-10, 10b; M-09 | ✅ |
| FR-010-152 no se fabrica un ancla | TRUST-11 | ✅ |
| FR-010-153 la clave de la instalación conserva su papel | TRUST-12 | ✅ |
| FR-010-154, 156 ancla sintética explícita por corrida; ayudante | sonda del lanzador; E2E dirigido 24/24; M-07 | ✅ |
| FR-010-155 nada de prueba en `prod` | guardas de `pg-e2e-seed.py`, `setup.sh`, `activate-test-license.sh`; CFG-01 | ✅ |
| FR-010-157 llamador antes que ancla | TRUST-06/07; M-06 | ✅ |
| FR-010-158, 159 firma inválida y otra instalación | TRUST-04, 04b, 05; M-04, M-05 | ✅ |
| FR-010-160..162 criptografía, payload, fechas | `core/license.py` sin cambios en firma/parseo; diff | ✅ |
| FR-010-163..165 estado público, diagnóstico, health | TRUST-06..08; E2E dirigido | ✅ |
| FR-010-166 sin esquema | diff: `models.py`, `alembic/` sin cambios | ✅ |
| FR-010-167 downgrade fuera | LICIMP-10 sigue documentándolo; sin cambios | ✅ |
| FR-010-168 pruebas que fallan si vuelve la autoconfianza | M-01, M-09 | ✅ |
| FR-010-169 E2E con ancla explícita | dirigida y dos globales | ✅ |
| FR-010-170 sin clave privada del propietario en el cliente | inventario §2; `grep` del repo | ✅ |
| FR-010-171 contrato arranque/petición definido | precedente `secret_key` (§5 #18) | ✅ |

`BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0; huérfanos = 0; `MATERIAL OQ` = 0;
`UNKNOWN` = 0; trazabilidad 100 %.
