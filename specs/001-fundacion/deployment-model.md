# MODELO DE DESPLIEGUE — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | Arquitecto de infraestructura |
| Ruta | `specs/001-fundacion/deployment-model.md` |

## 1. Modelo

Instalación independiente por cliente mediante Docker Compose (ADR-002). Cada instalación es un tenant aislado con volúmenes, secretos, identidad y licencia propios.

## 2. Arquitectura física

```text
Servidor del cliente
├── kontrol-proxy   (Nginx: TLS, SPA, proxy, headers)
├── kontrol-web     (frontend React, sin persistencia)
├── kontrol-api     (FastAPI, motor de licencias local)
├── kontrol-db      (PostgreSQL, volumen obligatorio)
└── Volúmenes: kontrol-db-data, kontrol-storage, kontrol-license-state, kontrol-backups
```

- PostgreSQL y Redis (futuro) nunca se exponen a Internet.
- El backend no se expone directamente salvo decisión de infraestructura.
- Swagger no se expone en producción sin autenticación/configuración explícita.

## 3. Ciclo de vida

| Etapa | Acción |
|---|---|
| Instalación | `kontrol install` (preflight, pull, volumes, health) |
| Inicialización | Identidad de instalación + solicitud de activación |
| Activación | Importar licencia firmada (online u offline) |
| Actualización | `kontrol update` (preflight, backup, pull, migrate, health, rollback) |
| Backup | `kontrol backup` |
| Restauración | `kontrol restore` |
| Diagnóstico | `kontrol diagnose` |
| Migración de servidor | Sustitución formal aprobada por el propietario |

## 4. Puertos

- Los puertos públicos se configuran por instalación.
- `frontend` (80/443 vía proxy), `backend` interno (8000), `db` interno (5432), `storage` volumen.

## 5. Requisitos de la instalación

- Docker Engine + Docker Compose (Compose Specification).
- DNS y TLS configurados.
- Respaldo y monitoreo definidos.
- Usuario PostgreSQL restringido (sin superusuario en la app).

## 6. Estado

| Elemento | Estado |
|---|---|
| Modelo de despliegue | ✔ |
| Ciclo de vida | ✔ |
| Aprobación | Pendiente |
