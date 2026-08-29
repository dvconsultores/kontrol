# Matriz de Conflictos Documentales de KONTROL

| Campo | Valor |
|---|---|
| Documento | Matriz de conflictos y resolución |
| Versión | 1.0 |
| Fecha | 2026-08-03 |
| Responsable | Especialista en convergencia de especificaciones |
| Ruta | `docs/governance/document-conflicts.md` |

## 1. Propósito

Registrar contradicciones entre fuentes, la autoridad aplicable, la decisión y el responsable. No se corrigen silenciosamente los documentos; no se selecciona una versión arbitrariamente. Todo conflicto no resuelto se eleva a `/speckit.clarify` y bloquea la parte afectada.

## 2. Conflictos identificados

| ID | Tema | Fuente A | Fuente B | Diferencia | Autoridad | Decisión propuesta | Responsable | Estado |
|---|---|---|---|---|---|---|---|---|
| CON-01 | Versión de PostgreSQL | DOC-05/Modelo (s/n) | DOC-08 Estándar (PostgreSQL 18.x) | DOC-08 fija 18.x; otros documentos no fijan versión | Nivel 3 (DOC-08) | **RESUELTO 2026-08-30**: PostgreSQL 18.6 validado por ejecución (migraciones 0001→0016 + 276/276 pruebas + drift idéntico a 16.2). `ADR-D0-001` `CONFIRMED_BY_EXECUTION`. Mínima soportada 16, objetivo 18.x | Arquitecto de datos | **CERRADO** — `postgresql-version-validation.md` |
| CON-02 | Versión de Vite | DOC-08 (Vite 8.x) | DOC-00/01 (no mencionan) | DOC-08 propone Vite 8.x | Nivel 3 (DOC-08) | Validar disponibilidad real de Vite 8 y compatibilidad con React 19 en `research.md`; si no existe, registrar ADR | Arquitecto frontend | Pendiente de research |
| CON-03 | Versión de Python | DOC-08 (Python 3.13.x) | DOC-01 (no fija) | DOC-08 propone 3.13.x | Nivel 3 (DOC-08) | Validar soporte de FastAPI/Pydantic/SQLAlchemy para 3.13 en `research.md` | Arquitecto backend | Pendiente de research |
| CON-04 | Mecanismo de sesión | DOC-08 (cookies HttpOnly para refresh; access token en memoria) | DOC-01 (JWT/session rotation genérico) | DOC-08 es más específico y prohibitivo de localStorage | Nivel 3 (DOC-08) | Cookies HttpOnly/Secure/SameSite + CSRF; access token corto; ADR-004 | Arquitecto de seguridad | Propuesta — requiere ADR |
| CON-05 | Cola de trabajos | DOC-08 (Celery + Redis 5.x/7.x) | DOC-05 (opcional sujeto a ADR) | DOC-08 fija Celery+Redis; DOC-05 lo condiciona a necesidad | Nivel 3 | No incluir worker/cola en 001-fundacion sin ADR y necesidad; diferir a Spec posterior. ADR-009 | Arquitecto de infraestructura | Propuesta — requiere ADR |
| CON-06 | Almacenamiento de archivos | DOC-08 (storage volumen o MinIO opcional) | DOC-05 (object storage/CDN) | MinIO/S3 opcionales | Nivel 3 | En 001-fundacion: volúmenes persistentes locales; MinIO/S3 fuera de alcance (ADR-008) | Arquitecto de infraestructura | Propuesta |
| CON-07 | Estructura de tenant | DOC-03 (Tenant/Company) | DOC-07 (licenciamiento por instalación) | Relación Tenant ↔ Instalación ↔ Company no está formalmente definida en un solo documento | Nivel 3 | Tenant = instalación (una instalación por cliente); Company = entidad legal dentro del tenant; documentar en data-model | Arquitecto de datos | Pendiente de clarificación |
| CON-08 | Alcance de licenciamiento central | DOC-07 (autoridad central separada) | DOC-00/01 (no contemplan portal central) | El portal central es una Spec posterior (010-licenciamiento-central) | Nivel 3 | En 001-fundacion: subsistema local (verificar/importar/aplicar); portal central fuera de alcance | Product Owner | Resuelto |
| CON-09 | Nombres de módulos | DOC-05 (organization, identity_access, master_data, ...) | DOC-08 (resources/frontend/src/modules) | Estructura backend vs estructura frontend | Nivel 3 | Estandarizar nombres en `plan.md`; dominios compartidos backend/frontend | Arquitecto de software | Pendiente de plan |
| CON-10 | Modalidad inicial de facturación | DOC-00 (forma libre computarizada como modalidad fiscal inicial) | DOC-09/10 (facturación digital y homologación) | La forma libre inicial requiere autorización/homologación aplicable | Nivel 1 (norma) | Documentar la modalidad como `LEGAL_VALIDATION_REQUIRED`; no implementar emisión fiscal en 001-fundacion | Especialista legal | Resuelto (fuera de alcance de 001) |
| CON-11 | Fechas y reglas fiscales | DOC-09 (revisión 22-07-2026) | DOC-11 (corte 03-08-2026) | Cortes documentales distintos | Nivel 1 | Revalidar antes de cada liberación; usar corte más reciente y marcar `LEGAL_VALIDATION_REQUIRED` | Especialista legal | Registrado |
| CON-12 | Resolución SICA | DOC-11 indica DM/N.º 025-12 vigente y derogó DM/N.º 22-12 | Referencias históricas | Riesgo de usar norma derogada | Nivel 1 | Usar DM/N.º 025-12 (G.O. 39.949); conservar 22-12 como antecedente | Especialista regulatorio | Resuelto |
| CON-13 | Nombre del producto/marca | DOC-00: "Kontrol es el nuevo nombre del producto" | Fuente F1 (INNOVA v1.1) | Marca heredada | Nivel 3 | Usar KONTROL en todo artefacto nuevo; INNOVA solo en documentos fuente históricos | Product Owner | Resuelto |
| CON-14 | Configurabilidad de atributos (EAV libre vs gobernada) | DOC-13 (Saint: "tablas adicionales" = creación libre de campos/tablas) | DOC-01 (KONTROL: "Inventario, impuestos, lotes, seriales, vencimientos y regulación no deben quedar exclusivamente en JSON o EAV libre") | Saint permite EAV libre; KONTROL exige configurabilidad gobernada | Nivel 3 (DOC-01) | Atributos configurados con tipo, unidad, obligatoriedad, validación y permisos; comportamientos críticos con modelo, API, migración y pruebas. No se copia el mecanismo libre de Saint | Arquitecto de datos | Resuelto (diferencia de diseño documentada) |

## 3. Conflictos no resueltos (elevados a `/speckit.clarify`)

| ID | Tema | Por qué no se resuelve | Impacto | ¿Bloquea? |
|---|---|---|---|---|
| CON-01 | PostgreSQL 16 vs 18 | **RESUELTO**: 18.6 validado por ejecución el 2026-08-30 | Fundacional (DB) | **Cerrado**; versión objetivo 18.x fijada con evidencia |
| CON-02 | Vite 8 | Requiere verificar disponibilidad real | Fundacional (frontend) | No bloquea la fase documental; bloquea fijar lockfile |
| CON-03 | Python 3.13 | Requiere verificar compatibilidad | Fundacional (backend) | No bloquea la fase documental |
| CON-04 | Sesión JWT/cookies | Requiere ADR | Seguridad | Se resuelve con ADR-004 |
| CON-05 | Cola/worker | Requiere ADR y necesidad demostrada | Operación | Se difiere (no entra en 001-fundacion) |
| CON-07 | Tenant/Instalación/Company | Requiere clarificación con Producto | Datos | Se documenta en data-model con supuesto |

## 4. Reglas de resolución

1. La autoridad se determina según la jerarquía del Nivel 1 al Nivel 8.
2. Cuando la autoridad es Nivel 1 y hay duda de vigencia → `LEGAL_VALIDATION_REQUIRED`; no implementar la parte afectada.
3. Cuando el conflicto es entre documentos del mismo nivel → abrir clarificación y/o ADR.
4. Toda decisión registra responsable, fecha y estado.
5. Un conflicto sin resolver que afecte la implementación se registra como bloqueo en `analysis-report.md`.

## 5. Estado de aprobación

| Elemento | Estado |
|---|---|
| Conflictos identificados | ✔ |
| Decisiones registradas | ✔ |
| Conflictos elevados a clarify | ✔ (CON-01..05, CON-07) |
| Aprobación | Pendiente — revisión del comité de arquitectura y producto |
