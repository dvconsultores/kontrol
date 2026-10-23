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
