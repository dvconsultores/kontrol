# Auditoría de hardcode · ORG-07-EFFECTIVE-AUTHORITY-MATRIX (2026-11-19)

**Alcance:** el código del ciclo, sin pruebas ni E2E:
- backend: `service_autoridad.py`, `schemas_autoridad.py`, `api_autoridad.py` y `service_ocupacion.autoridad_efectiva_en`;
- frontend: `MatrizAutoridadPage.tsx` y los tipos de la matriz en `modules/gobierno/api.ts`.

## Búsquedas sobre el diff

| Búsqueda | Resultado |
|---|---|
| `naguanagua`, `alcald`, `municip` | 0 |
| Literales de figura (`"DELEGACION…"`, `"SUPLENCIA"`, `"ENCARGADURIA"`, `"TITULAR"`, `"COMISION…"`) | 0 en decisiones. `origen` copia la figura que devuelve ORG-04 (`FIGURAS`) |
| Grupos `TITULARIDAD` / `DELEGACION` | Solo para ordenar (la fila del cargo antes que la delegación) y para decidir si la fuente es el titular. Son el vocabulario de plataforma de ORG-04 (D-AP-01) |
| Fechas literales y `timedelta` | 0. La fecha es la de corte que pide el usuario |
| Precedencia, vigencias, revocación o límites recalculados en ORG-07 | 0. Los resuelve `service_ocupacion.autoridad_efectiva_en` sobre `_vigentes_en` y `situacion_en`; ORG-07 los proyecta |
| Nombres de cargo o de persona | 0 |

## Clasificación

| Elemento | Clase | Por qué no es hardcode institucional |
|---|---|---|
| Figuras y grupos de ORG-04 | PLATFORM_TAXONOMY | Vocabulario nacional estable de ORG-04, reutilizado sin copiarlo |
| Persona reservada sin `gobierno_ocupacion:view` | PLATFORM_INVARIANT | Mínimo privilegio (OD-EA-01) |
| Identidad de fila (`cargo:acción:materia`, `asignación:acción:materia`) | PLATFORM_INVARIANT | Integridad de la proyección (D-EA-02) |

## Resultado

| Indicador | Valor |
|---|---|
| ZERO_INSTITUTIONAL_HARDCODE | 1 |
| TENANT_CONFIGURABLE | 1 (la autoridad sale de los cargos y las asignaciones del ente) |
| NATIONAL_REUSABLE_PRODUCT | 1 |
| AUTHORITY_ENGINES_CREATED | 0 |
