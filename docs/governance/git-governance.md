# Gobierno de Git de KONTROL

| Campo | Valor |
|---|---|
| Documento | Gobierno inicial del repositorio y convenciones Git |
| Versión | 1.0 |
| Fecha | 2026-08-03 |
| Responsable | Especialista en gobierno de producto / DevSecOps |
| Ruta | `docs/governance/git-governance.md` |

## 0. Norma vigente: rama única (2026-11-01, vinculante)

KONTROL utiliza exclusivamente la rama `develop`. Está prohibido crear o trabajar sobre cualquier rama adicional
(de iniciativa, de Spec, de QA, temporal, de Claude o de DeepSeek), integrar mediante PR entre ramas, y fusionar o
rebasar ramas de trabajo. Todo ciclo empieza y termina en `develop` con `HEAD == origin/develop`. La rama por
defecto del repositorio en GitHub es `develop` y es la única rama remota. DeepSeek y los subagentes no hacen
operaciones Git; Git lo controla Claude.

Normalización del 2026-11-01 (ciclo GOV-0-FUNCTIONAL-03, orden de la dueña): `feature/001-fundacion` (`8c82289`) era
ancestro de `develop` (`e993792`), con 0 commits propios y 249 por detrás; se cambió la rama por defecto a `develop`
y se eliminó `feature/001-fundacion` del remoto. Las secciones 2 y 4 son el registro histórico del montaje inicial y
quedan sustituidas por esta norma.

## 1. Estado inicial auditado (2026-08-03)

| Elemento | Valor |
|---|---|
| Repositorio | `https://github.com/dvconsultores/kontrol` |
| Rama inicial | `develop` (creada al inicio de la sesión) |
| Commits | 0 (ningún commit todavía) |
| Archivos sin seguimiento | `requerimientos/` (13 documentos + 1 lock) |
| Secretos | No detectados en el inventario inicial (verificar con escaneo) |
| Archivos grandes/binarios | `Compilacion_Providencias_Administrativas_SENIAT_INNOVA.pdf` (7,5 MB); los PDF no deben versionarse como texto |
| `.gitignore` | Creado en esta iniciativa |
| `.dockerignore` | Creado en esta iniciativa |
| Cambios del usuario | Ninguno fuera de `requerimientos/` (sin commits previos) |

## 2. Rama de trabajo de la iniciativa (histórico, sustituido por §0)

- Rama creada: **`feature/001-fundacion`** (derivada de `develop`).
- La rama `develop` es la integración; no se trabaja directamente en ella.
- Ramas protegidas propuestas: `main`, `develop`.

## 3. Convención de commits

Cada commit se relaciona con una tarea de `specs/001-fundacion/tasks.md` y usa Conventional Commits con el sufijo de iniciativa:

| Tipo | Ejemplo |
|---|---|
| `docs(001)` | `docs(001): inventario documental` |
| `spec(001)` | `spec(001): crear spec.md de fundacion` |
| `adr(001)` | `adr(001): ADR-004 autenticacion con cookies` |
| `test(001)` | `test(001): casos de prueba de licencia` |
| `build(001)` | `build(001): compose base de fundacion` |
| `chore(001)` | `chore(001): gitignore y dockerignore` |

Formato: `tipo(001): descripción breve (#T-ID o ref. tarea)`.

## 4. Estrategia de Pull Request (histórico, sustituido por §0: no hay PR entre ramas)

- Una iniciativa por PR.
- Referencia a la Spec (`specs/001-fundacion/spec.md`).
- Referencia a las tareas ejecutadas.
- Evidencia de pruebas.
- Checklist de la iniciativa completado.
- Sin cambios no relacionados.
- Sin secretos.
- Sin errores de lint.
- Sin fallos de build.
- Sin fallos de pruebas.
- Revisión por al menos un responsable de arquitectura/QA.

## 5. Reglas de seguridad Git

- No se ejecuta `git reset --hard`, `git clean -fd`, ni force push.
- No se borran cambios del usuario ni se revierten sin comparar.
- No se incluyen secretos, respaldos, temporales, datos productivos, volúmenes PostgreSQL, licencias privadas ni claves privadas.
- Antes de cada commit se ejecuta escaneo de secretos (ver `security-baseline.md`).
- Los PDF de `requerimientos/` se versionan como documentos fuente (decisión de producto); la evidencia binaria generada va a `evidence/generated/` (ignorada).

## 6. Estado de aprobación

| Elemento | Estado |
|---|---|
| Rama `feature/001-fundacion` creada | ✔ |
| Convención de commits definida | ✔ |
| Estrategia de PR definida | ✔ |
| `.gitignore` / `.dockerignore` | ✔ |
| Aprobación | Pendiente |
