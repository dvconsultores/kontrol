# KONTROL — Plataforma Administrativa Empresarial para Venezuela

KONTROL es una plataforma administrativa empresarial para empresas venezolanas:
multiempresa, multisucursal, multimoneda y multirrubro, con **núcleo fiscal
venezolano separado, versionado e inalterable**.

> Iniciativa actual: **001-fundacion** — base arquitectónica, de seguridad, de
> licenciamiento y operativa. Consulta `specs/001-fundacion/spec.md`.

## Documentación

- **Constitución:** `.specify/memory/constitution.md`
- **Gobierno:** `docs/governance/`
- **Spec 001:** `specs/001-fundacion/`
- **Requerimientos fuente:** `requerimientos/` (no renombrar)

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React 19 · TypeScript · Vite · Tailwind 4 · TanStack Query · React Router · RHF · Zod · Vitest · Playwright |
| Backend | Python 3.13 · FastAPI · Pydantic 2 · SQLAlchemy 2 · Alembic · Pytest · Ruff · Mypy |
| Base de datos | PostgreSQL 18 |
| Infraestructura | Docker Compose · Nginx · ClamAV (`clamd` como servicio) · ReportLab |

Detalle y versiones resueltas: `specs/001-fundacion/dependency-matrix.md`.

## Inicio rápido (desarrollo)

```bash
# Backend
cd resources/backend
python -m venv .venv && . .venv/bin/activate
# runtime + pruebas y calidad (la imagen de producción instala solo requirements.lock)
pip install -r requirements-test.txt
KONTROL_SECRET_KEY=<clave-segura> uvicorn app.main:app --reload --timeout-keep-alive 75

# Frontend
cd resources/frontend
npm install
npm run dev

# Pruebas
cd resources/backend && pytest tests/ -q
cd resources/frontend && npm run test
```

## Certificación de release

`python3 qa/certificar-release.py` es la única orden de certificación de release. Reconstruye V6R
(runtime de producto) y V6C (V6R más dependencias de test) y ejecuta por etapas preflight, validez del
entorno, locks, ambos entornos, PostgreSQL de QA, backend SQLite y PostgreSQL, E2E, OpenAPI, pip-audit,
residuos, manifiesto y veredicto. Se lanza con el `python3` del sistema desde la raíz.

```bash
python3 qa/certificar-release.py
python3 qa/certificar-release.py --solo-preflight
```

- Códigos de salida: 0 certificación superada; 1 fallo de certificación; 3 INVALID_ENVIRONMENT;
  4 `--solo-preflight` correcto; 70 preflight, error interno o interrupción. No leer el RC por tubería.
- Evidencia en `qa/certificaciones/<run_id>/manifest.json` con registros saneados (fuera de Git);
  espacio de trabajo en `~/.cache/kontrol-qa/certificacion/<run_id>/`, con una sola corrida a la vez.
- Requisitos del anfitrión: Debian 13 con `apt-get` y `dpkg-deb`, `node`, `uv`, `git`, red a Docker Hub
  y PyPI, el PostgreSQL de QA fijado de `qa/postgres_qa.json` (sin `.venv` ni compilador) y el ClamAV de QA de `qa/clamav_qa.py`.
- E2E canónica: siempre 6 workers y 0 reintentos (`--workers=6 --retries=0`), sin importar el número de CPU ni `CI`; la corrida
  comprueba en `suite.log` que Playwright usó 6 workers.
- Política de entorno v1: `CI` y las variables de Python excluidas se canonicalizan; los secretos no llegan a los sujetos; el
  preflight falla (RC 70) si hay variables heredadas que cambiarían la carga certificada (`PYTEST_*`, `PLAYWRIGHT_*` salvo
  `PLAYWRIGHT_BROWSERS_PATH`, `NODE_OPTIONS`, `KONTROL_*` salvo `KONTROL_QA_CERT_HOME`/`KONTROL_CLAMSCAN_PATH`/`KONTROL_CLAMAV_DB`,
  `UV_*`, `PIP_*`, `PG*`, `GIT_*`, `LD_PRELOAD`…); el manifiesto solo registra nombres (`ENVIRONMENT_POLICY`).
- PostgreSQL de QA: sale de `qa/postgres_qa.json` (rueda `pgserver` 0.1.4 con PostgreSQL 16.2 y `btree_gist` del paquete PGDG
  `postgresql-16_16.2-1.pgdg120+2`, ambos por sha256), instalado y verificado en `<HOME de certificación>/postgres-qa/`;
  `qa/pg-provision.sh` usa `KONTROL_PGBIN` cuando está definido (sin volver al `.venv`) y con `KONTROL_PG_SIN_COMPILAR=1`
  nunca compila `btree_gist`; si hay un PostgreSQL de QA en marcha con otros binarios, la corrida lo rechaza (pararlo con
  `bash qa/pg-provision.sh stop`).
- Árbol certificado: `CERTIFICATION_INPUT_TREE_HASH` (árbol Git con índice y objetos temporales; política de exclusiones v1:
  evidencia y `.md` de `specs/`, `docs/roadmap/`, `requerimientos/` y ficheros con secretos) entra en
  `CANONICAL_RUN_INPUT_HASH` v2 y se recalcula al cerrar, debe coincidir; `--solo-preflight` da el árbol sin certificar
  (procedencia entre anfitriones). La certificación oficial se ejecuta en un anfitrión dedicado (OD-CERT-27): requisitos en
  `specs/012-auditoria-integral-e2e/evidence/canonicalize-certification-environment/certification-host-requirements.md`.
- No usa Docker: reconstruye el rootfs de la imagen certificada, pero no certifica el contenido exacto
  de la imagen desplegada (EXACT_RUNTIME_IMAGE_CONTENTS_CERTIFIED = 0).
- `--incluir-v0-historico` es un control histórico (marcado HISTORICAL_CONTROL, nunca cambia el
  veredicto y nunca está por defecto); un cambio intencionado del contrato HTTP actualiza
  `qa/certificacion_referencia.json` en el mismo commit.

## Instalación por cliente (producción)

```bash
cp .env.example .env   # complete los secretos
./scripts/install.sh   # o: python3 kontrol.py install
```

## Gobernanza

- Flujo **Spec Kit**: `/speckit.specify → clarify → plan → checklist → tasks → analyze → [autorización] → implement → converge`.
- Rama de trabajo: `feature/001-fundacion`.
- No se implementa sin autorización expresa (Constitución P2).
- Referencias INNOVA/Saint: solo fuente de requerimientos y referencia comparativa.
