# SOURCE_INVENTORY — P3 Enterprise rebaseline

Ciclo `P3-ENTERPRISE-REBASELINE-AND-COMPLETION-MATRIX` · 2026-11-20 · `develop` en `b726c1da` (más `b3b53046`, herramientas).
Cada fuente se extrajo a texto (`pdftotext -layout`; los DOCX desde `word/document.xml`). Los hashes son los primeros 12 caracteres del SHA-256.

## 1. Fuentes del sponsor: requisitos funcionales Enterprise

| Fuente | Págs. | SHA-256 | Lectura | Uso en la matriz |
|---|---|---|---|---|
| `00_Kontrol_Indice_General_y_Mapa_de_Entregables.pdf` (Vol. 0) | 3 | `92f676caf2df` | completa | Alcance, puertas de decisión y prevalencia de las fuentes |
| `01_Kontrol_Documento_Maestro_de_Requerimientos.pdf` (Vol. 1) | 6 | `8b84124cc897` | completa | Módulos (§4), reglas no negociables (§5), perfiles (§6), maestros (§7), catálogo (§8), fiscal (§9), regulatorio (§10), requisitos no funcionales (§11) y aceptación (§12) |
| `02_Kontrol_Arquitectura_Funcional_Menu_Maestros_y_Procesos.pdf` (Vol. 2) | 6 | `0bb63f15844a` | completa | Menú (§1), estándar de pantalla (§2), maestros (§3–5), compras (§6), ventas (§7), inventario (§8), CxC/CxP (§9), tesorería (§10), fiscal (§11), SoD (§12) e incorporación (§13) |
| `03_Kontrol_Modelo_de_Datos_Reglas_y_Maquinas_de_Estado.pdf` (Vol. 3) | 7 | `af040ec1222c` | completa | Entidades (§2–11), integridad (§12), máquinas de estado (§13), API (§14) y eventos (§15) |
| `04_Kontrol_Wireframes_Funcionales_y_Sistema_de_Diseno.pdf` (Vol. 4) | 27 | `e397c5985263` | completa (texto; los dibujos son de baja fidelidad) | Reglas de las 24 pantallas, responsive (§28) y usabilidad (§29) |
| `05_Kontrol_Arquitectura_Tecnica_Seguridad_e_Infraestructura.pdf` (Vol. 5) | 6 | `268969ea19c3` | completa | Seguridad (§4), multiempresa (§5), concurrencia (§6), rendimiento (§7), migraciones (§10), continuidad (§11) y observabilidad (§12) |
| `06_Kontrol_SpecKit_Implementacion_QA_y_Homologacion.pdf` (Vol. 6) | 5 | `fea8966b2b1a` | completa | Casos E2E mínimos (§6), homologación (§8) y definición de terminado (§11) |
| `Procesos - Importacion - Recepcion de Importación y Distribucion en Almacen.docx` | — | `bb9b568ef3cd` | completa | §1–§4, zonas y controles críticos; es la autoridad de la Spec 018 |
| `procesos.png` (mapa de procesos de importación, «versión preliminar AS-IS/TO-BE») | — | `1f496ed59151` | completa | Confirma el DOCX. Las zonas A–E figuran como «Ejemplo de zonas» y los controles clave incluyen «evidencia fotográfica» |
| `Pedido - Organizar Pedido - Confirmar - Facturar - Despachar.docx` | — | `a92fda7e58c0` | completa | Procesos 1–9 de gestión de pedido, preparación, facturación y despacho (filas PED-01..09) |
| `KONTROL_SPEC057_Ingenieria_Requerimientos_Activos_Fijos.pdf` | 24 | `4c92a6e8bf4a` | índice, alcance y estado | Dominio nuevo de Enterprise en estado `PLANNED / NOT STARTED`: filas AF-01..05, agrupadas por bloque de secciones |

## 2. Fuentes normativas y regulatorias (soporte de reglas, no de menú)

| Fuente | Págs. | SHA-256 | Lectura | Uso |
|---|---|---|---|---|
| `INNOVA_Guias_SENIAT_SICA_SIGESAI_Venezuela.pdf` (F5) | 8 | `fdb5ea459a24` | delegada a la auditoría de Regulación | Diferencia entre documento fiscal, guía SICA y permiso SIGESAI, y reglas de validación (REG-*) |
| `INNOVA_Expediente_Normativo_SICA_SIGESAI_Decreto_1808.pdf` (F4) | 17 | `224c39acd46d` | delegada a la auditoría de Regulación | Retenciones ISLR, control agroalimentario y bloqueos (REG-*, FMA-04) |
| `Compilacion_Providencias_Administrativas_SENIAT_INNOVA.pdf` (F3) | 63 | `ecd411ecb680` | no se extraen requisitos | Texto normativo. Este ciclo no inventa regulación: lo fiscal se mide contra el Vol. 1 §9 y el Vol. 2 §11 |
| `Leyes Venezolanas.docx` (F6–F9) | — | `082b2e03bf08` | no se extraen requisitos | Texto legal; mismo criterio que F3 |

## 3. Fuentes de referencia o fuera de la línea Enterprise

| Fuente | SHA-256 | Motivo |
|---|---|---|
| `ManualAdministrativoSaint.pdf` (F2, 82 págs.) | `1792ba27ce55` | El Vol. 0 lo declara «referencia comparativa, no diseño obligatorio ni fuente legal». No genera filas |
| `KONTROL_Estandar_Maestro_Frontend_y_Arquitectura_Tecnica_v1.0.pdf` (17 págs.) | `5f721bca7011` | Estándar técnico transversal. Se refleja en TRV-06 y TRV-07 |
| `KONTROL_Especificacion_Licenciamiento_Anual_Instalaciones_Docker.pdf` (16 págs.) | `95e843b3f0ae` | Plataforma y licenciamiento (Spec 010), compartido entre líneas. No es requisito funcional del cliente Enterprise |
| `requerimientos/gobierno/**` (14 ficheros) | — | Línea Gobierno (P1/P2). Fuera de la frontera de P3 |

## 4. Fuentes del repositorio contrastadas

- Matriz antigua: `docs/roadmap/enterprise-application-completion/SPONSOR_APPLICATION_COVERAGE_MATRIX.{md,csv}` (92 filas; última modificación el 2026-11-10, `60c5b2d7`).
- Matriz de la Spec 018: `specs/018-importaciones/IMPORT_FULL_SPONSOR_COMPLETENESS_MATRIX.md` (42 filas) y `specs/018-importaciones/evidence/SPEC018_REMAINING_DECISIONS.md`.
- Línea base Enterprise: `docs/roadmap/enterprise-baseline/ENTERPRISE_BASELINE_CURRENT.md` y `ENTERPRISE_WORK_MATRIX_CURRENT.md`.
- Specs Enterprise con artefactos: 001 (235 md, 38 deltas), 002, 003, 004 (7 deltas), 005, 006, 007, 008-almacenes-fisicos, 008-regulacion-traslados, 009, 010 (compartida), 011-homologación, 011-unidades, 012-auditoría-integral, 012-maestros-comerciales, 013, 015 (3 deltas), 018 (10 deltas), 045, 046, 047 y arch-mc-001.
- Código del HEAD:
  - menú `resources/frontend/src/layout/Sidebar.tsx` y router `resources/frontend/src/app/router.tsx`;
  - rutas del backend en `resources/frontend/src/tests/fixtures/openapi-routes.json` (1 154 operaciones, regenerado desde la aplicación real el 2026-11-19);
  - 129 ficheros E2E y 136 migraciones Alembic (cabeza única `0128_gov_tre04_pago`).

## 5. Resultado

`ALL_ENTERPRISE_SOURCE_DOCUMENTS_INVENTORIED = YES`.

- **Fuentes funcionales:** las 11 se leyeron completas.
- **Fuentes normativas:**
  - las dos de base funcional (F4 y F5) se delegaron a la auditoría de Regulación;
  - las dos de texto legal (F3 y F6–F9) se registran sin extraer requisitos, para no inventar regulación.
- **Fuentes de referencia y de Gobierno:** se excluyen con su motivo.
