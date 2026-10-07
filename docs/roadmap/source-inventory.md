# INVENTARIO DOCUMENTAL FUENTE

18 archivos en `requerimientos/` (no renombrar — README y Constitución lo prohíben).

| # | Documento | Tipo | Autoridad | Uso en esta auditoría |
|---|---|---|---|---|
| 1 | `00_Kontrol_Indice_General_y_Mapa_de_Entregables.pdf` | Vol. 0 | Nivel 3 | Puertas de decisión, convenciones de producto, matriz de fuentes F1-F10 |
| 2 | `01_Kontrol_Documento_Maestro_de_Requerimientos.pdf` | Vol. 1 | Nivel 3 | Alcance funcional (§4), maestros (§7), reglas fiscales (§9), reglas no negociables (§5) |
| 3 | `02_Kontrol_Arquitectura_Funcional_Menu_Maestros_y_Procesos.pdf` | Vol. 2 | Nivel 3 | **Menú canónico de 20 ramas** — base del contraste de navegación |
| 4 | `03_Kontrol_Modelo_de_Datos_Reglas_y_Maquinas_de_Estado.pdf` | Vol. 3 | Nivel 3 | Entidades y máquinas de estado esperadas |
| 5 | `04_Kontrol_Wireframes_Funcionales_y_Sistema_de_Diseno.pdf` | Vol. 4 | Nivel 3 | 24 wireframes de referencia, patrones de interacción |
| 6 | `05_Kontrol_Arquitectura_Tecnica_Seguridad_e_Infraestructura.pdf` | Vol. 5 | Nivel 3 | Seguridad, observabilidad, respaldos, despliegue |
| 7 | `06_Kontrol_SpecKit_Implementacion_QA_y_Homologacion.pdf` | Vol. 6 | Nivel 3 | Flujo Spec Kit, QA, liberación fiscal |
| 8 | `KONTROL_Estandar_Maestro_Frontend_y_Arquitectura_Tecnica_v1.0.pdf` | Estándar | Nivel 3 | Design system, política de modales, DataTables |
| 9 | `KONTROL_Especificacion_Licenciamiento_Anual_Instalaciones_Docker.pdf` | Estándar | Nivel 3 | Licenciamiento anual, modos, fechas |
| 10 | `Compilacion_Providencias_Administrativas_SENIAT_INNOVA.pdf` | Normativa | **Nivel 1** | SNAT/2011/00071, 2018/0141, 2024/000102, 2024/000121, 2025/000054, IGTF |
| 11 | `INNOVA_Expediente_Normativo_SICA_SIGESAI_Decreto_1808.pdf` | Normativa | **Nivel 1** | Retenciones ISLR, control agroalimentario, movilización |
| 12 | `INNOVA_Guias_SENIAT_SICA_SIGESAI_Venezuela.pdf` | Normativa | **Nivel 1** | Diferenciación de documentos fiscales y guías |
| 13 | `Leyes Venezolanas.docx` | Normativa | **Nivel 1** | IVA, ISLR, IGTF, COT |
| 14 | `ManualAdministrativoSaint.pdf` | Referencia | Nivel 8 | Comparación funcional — **no autoridad legal** |
| 15 | `.~lock.INNOVA_...docx#` | Artefacto | — | Archivo de bloqueo residual de LibreOffice; sin contenido |
| 16 | **`Procesos - Importacion - Recepcion de Importación y Distribucion en Almacen.docx`** | **Proceso** | Nivel 3 | **Sin track (2026-08-25).** Autoridad de las Specs 015-026 |
| 17 | **`Pedido - Organizar Pedido - Confirmar - Facturar - Despachar.docx`** | **Proceso** | Nivel 3 | **Sin track (2026-08-25).** Autoridad de las Specs 029-035 |
| 18 | `procesos.png` | Diagrama | Nivel 3 | Sin track. Diagrama de procesos (no interpretado en esta pasada) |
| 19 | **`KONTROL_SPEC057_Ingenieria_Requerimientos_Activos_Fijos.pdf`** | **Requerimientos** | Nivel 3 | **Con track desde el 2026-10-07.** Ingeniería de Requerimientos v1.0 de la Spec **057 — Gestión Integral de Activos Fijos** (24 páginas; RF-AF-001..202, RN-AF-001..006, AF-INV-01..24, RNF-AF-001..018; dependencias §33; exclusiones §31). Entrada de su futuro `/speckit.specify` |

## Documentación interna del proyecto

| Ruta | Contenido |
|---|---|
| `.specify/memory/constitution.md` | 20 principios no negociables + jerarquía de autoridad |
| `docs/governance/` | Matriz de autoridad, conflictos documentales, inventario, DoD, gobierno Git |
| `docs/evidence/` | Revisión CVE, revisión legal, checklist Docker, hashes |
| `docs/seniat/` | Expediente de homologación fiscal (separadores 01-07) |
| `docs/manual-usuario/` | Manual de usuario con flujos de proceso |
| `docs/auditoria/` | Auditoría profunda 001-011 |
| `specs/001..012/` | 12 iniciativas con juego documental completo |
| `qa/runs/`, `qa/audits/` | 2 corridas QA + auditoría integral `KONTROL-AUDIT-20260812` |

## Observación crítica sobre las fuentes

Los documentos **16 y 17 son posteriores** (2026-08-25) a la última auditoría del proyecto
(`KONTROL-AUDIT-20260812`, 2026-08-12). Describen etapas operativas —ruta de picking por
ubicación, confirmación independiente de pedido, put-away por zonas, incidencias de recepción,
importaciones— que **ninguna Spec existente cubre y ningún modelo soporta**.

Esto explica por qué las auditorías previas dieron `CONDITIONAL GO`: auditaban KONTROL contra las
Specs escritas, no contra estos procesos. El alcance real es mayor que el alcance especificado.
