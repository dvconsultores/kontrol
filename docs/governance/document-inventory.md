# Inventario Documental de KONTROL

| Campo | Valor |
|---|---|
| Documento | Inventario documental del repositorio |
| Versión | 1.0 |
| Fecha | 2026-08-03 |
| Responsable | Especialista en documentación funcional y técnica |
| Autoridad | Nivel 3 — Documentos maestros vigentes de KONTROL |
| Ruta | `docs/governance/document-inventory.md` |

## 1. Propósito

Inventariar, clasificar y auditar todas las fuentes documentales de KONTROL ubicadas en `requerimientos/`.
Permite detectar duplicidades, conflictos, vacíos y referencias heredadas de INNOVA antes de implementar.

## 2. Metodología

- Lectura íntegra del contenido de cada documento (no solo del nombre).
- Cálculo de hash SHA-256 y tamaño de cada archivo.
- Clasificación según el esquema definido en el apartado 4.
- Registro de duplicidades, conflictos y referencias internas.

## 3. Inventario de archivos

| ID | Documento | Ruta | Tamaño | Hash SHA-256 | Tipo | Versión declarada | Fecha declarada |
|---|---|---|---|---|---|---|---|
| DOC-00 | Índice General y Mapa de Entregables | `requerimientos/00_Kontrol_Indice_General_y_Mapa_de_Entregables.pdf` | 108 KB | ver apartado 9 | PDF | 1.0 | 2026-08-03 |
| DOC-01 | Documento Maestro de Requerimientos | `requerimientos/01_Kontrol_Documento_Maestro_de_Requerimientos.pdf` | 176 KB | ver apartado 9 | PDF | 1.0 | 2026-08-03 |
| DOC-02 | Arquitectura Funcional, Menú, Maestros y Procesos | `requerimientos/02_Kontrol_Arquitectura_Funcional_Menu_Maestros_y_Procesos.pdf` | 184 KB | ver apartado 9 | PDF | 1.0 | 2026-08-03 |
| DOC-03 | Modelo de Datos, Reglas y Máquinas de Estado | `requerimientos/03_Kontrol_Modelo_de_Datos_Reglas_y_Maquinas_de_Estado.pdf` | 236 KB | ver apartado 9 | PDF | 1.0 | 2026-08-03 |
| DOC-04 | Wireframes Funcionales y Sistema de Diseño | `requerimientos/04_Kontrol_Wireframes_Funcionales_y_Sistema_de_Diseno.pdf` | 1,6 MB | ver apartado 9 | PDF | 1.0 | 2026-08-03 |
| DOC-05 | Arquitectura Técnica, Seguridad e Infraestructura | `requerimientos/05_Kontrol_Arquitectura_Tecnica_Seguridad_e_Infraestructura.pdf` | 180 KB | ver apartado 9 | PDF | 1.0 | 2026-08-03 |
| DOC-06 | Spec Kit, Implementación, QA y Homologación | `requerimientos/06_Kontrol_SpecKit_Implementacion_QA_y_Homologacion.pdf` | 172 KB | ver apartado 9 | PDF | 1.0 | 2026-08-03 |
| DOC-07 | Especificación de Licenciamiento Anual para Instalaciones Docker | `requerimientos/KONTROL_Especificacion_Licenciamiento_Anual_Instalaciones_Docker.pdf` | 396 KB | ver apartado 9 | PDF | 1.0 | 2026-08-03 |
| DOC-08 | Estándar Maestro de Frontend y Arquitectura Técnica | `requerimientos/KONTROL_Estandar_Maestro_Frontend_y_Arquitectura_Tecnica_v1.0.pdf` | 560 KB | ver apartado 9 | PDF | 1.0 | 2026-08-03 |
| DOC-09 | Leyes Venezolanas (base jurídico-funcional) | `requerimientos/Leyes Venezolanas.docx` | 24 KB | ver apartado 9 | DOCX | s/n | 2026-07-22 (revisión normativa) |
| DOC-10 | Compilación de Providencias Administrativas SENIAT (INNOVA) | `requerimientos/Compilacion_Providencias_Administrativas_SENIAT_INNOVA.pdf` | 7,5 MB | ver apartado 9 | PDF | s/n | 2026-08-03 |
| DOC-11 | Expediente Normativo SICA, SIGESAI y Decreto N.º 1.808 (INNOVA) | `requerimientos/INNOVA_Expediente_Normativo_SICA_SIGESAI_Decreto_1808.pdf` | 456 KB | ver apartado 9 | PDF | 1.0 | 2026-08-03 |
| DOC-12 | Guías SENIAT, SICA y SIGESAI (INNOVA) | `requerimientos/INNOVA_Guias_SENIAT_SICA_SIGESAI_Venezuela.pdf` | 200 KB | ver apartado 9 | PDF | s/n | 2026-07-29 |
| DOC-13 | Manual Administrativo Saint | `requerimientos/ManualAdministrativoSaint.pdf` | 4,7 MB | ver apartado 9 | PDF | s/n (82 páginas) | s/n |
| DOC-99 | Archivo de bloqueo (no documental) | `requerimientos/.~lock.INNOVA_Documento_Maestro_Requerimientos_Venezuela_v1.1_Completo.docx#` | 4 KB | s/n | Lock | s/n | s/n |

> **Nota DOC-99:** El archivo `.~lock.INNOVA_Documento_Maestro_Requerimientos_Venezuela_v1.1_Completo.docx#` es un artefacto de bloqueo de LibreOffice/Office. No es documentación. No debe versionarse ni considerarse fuente. Sugerencia: eliminar o ignorar mediante `.gitignore` (ya incluido como `.~lock.*#`).

## 4. Clasificación de documentos

| ID | Autoridad | Dominio | Clasificación | Vigencia | Conflictos |
|---|---|---|---|---|---|
| DOC-00 | Nivel 3 | Gobierno | Índice general / mapa de entregables | Vigente | Ninguno |
| DOC-01 | Nivel 3 | General | Autoridad actual de KONTROL | Vigente | Documenta la decisión central de núcleo fiscal separado |
| DOC-02 | Nivel 3 | Funcional | Autoridad actual de KONTROL | Vigente | Menú y flujos; sujeto a clarificación de alcance |
| DOC-03 | Nivel 3 | Datos | Autoridad actual de KONTROL | Vigente | Versiones tecnológicas de PostgreSQL en otros docs |
| DOC-04 | Nivel 3 | UI/UX | Wireframe | Vigente | 24 wireframes de referencia; sin imágenes en extracción de texto |
| DOC-05 | Nivel 3 | Técnica | Autoridad actual de KONTROL | Vigente | Menciona cola, workers, Redis, MinIO como opcionales |
| DOC-06 | Nivel 3 | Proceso | Autoridad actual de KONTROL (método) | Vigente | Define el flujo Spec Kit y las Specs 001-010 |
| DOC-07 | Nivel 3 | Licenciamiento | Documento de licenciamiento | Vigente | Modelo de despliegue independiente por cliente |
| DOC-08 | Nivel 3 | Frontend | Estándar obligatorio | Vigente | Stack: Vite 8, React 19, PostgreSQL 18, Python 3.13 |
| DOC-09 | Nivel 1 | Legal | Norma legal (análisis de leyes) | Vigente, requiere revalidación legal | Alícuotas IVA/IGTF; modalidades de facturación |
| DOC-10 | Nivel 1 | Legal | Norma regulatoria (compilación) | Requiere validación jurídica | Contiene el texto de providencias SENIAT |
| DOC-11 | Nivel 1/8 | Legal/Regulatorio | Norma regulatoria + antecedente INNOVA | Requiere validación | Decreto 1.808, SICA, SIGESAI, SACS; marca INNOVA |
| DOC-12 | Nivel 1/8 | Regulatorio | Norma regulatoria + antecedente INNOVA | Requiere validación | Alcance de guías SICA/SIGESAI; marca INNOVA |
| DOC-13 | Nivel 8 | Referencia comparativa | Manual de terceros (Saint Enterprise Administrativo) | Referencia (no autoridad) | Correlativos, retenciones, impuestos, roles, tablas adicionales |

## 5. Duplicidades detectadas

| Duplicidad | Documentos | Acción |
|---|---|---|
| Tabla de fuentes F1–F10 repetida | DOC-00, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06 | No es duplicidad crítica: es una sección común de "Fuentes, criterio de prevalencia y control de vigencia". Mantener el artefacto normativo consolidado en `docs/governance/authority-matrix.md` y referenciar desde aquí. |
| Reglas de frontend (modales, tablas, botones) | DOC-08 y DOC-04 | DOC-08 es la autoridad normativa; DOC-04 es el wireframe. No corregir en paralelo; DOC-08 prevalece. |
| Requisitos de facturación/números de control | DOC-01, DOC-09, DOC-10 | DOC-09 y DOC-10 son fuentes legales; DOC-01 es la línea base funcional. Prevalece la norma (Nivel 1). |

## 6. Vacíos documentales

| ID | Vacío | Impacto | Acción |
|---|---|---|---|
| GAP-01 | No hay un documento único de "matriz normativa" aprobado con vigencia por norma | Riesgo de declarar cumplimiento sin evidencia | Crear `docs/governance/authority-matrix.md` con estado `LEGAL_VALIDATION_REQUIRED` por norma |
| GAP-02 | No existe la Constitución del proyecto en el repositorio | Sin principio no negociable de referencia | Creada en `.specify/memory/constitution.md` |
| GAP-03 | No existen Specs aprobadas | No se puede implementar | Crear `specs/001-fundacion/` mediante este flujo |
| GAP-04 | No existe estructura `specs/`, `docs/`, `adr/`, `contracts/`, `wireframes/` | Sin artefactos del flujo Spec Kit | Crear estructura completa en esta iniciativa |
| GAP-05 | El `Manual Técnico de INNOVA` y el `Manual Saint` estaban referenciados como fuentes F1/F2 pero no presentes en `requerimientos/` | Sin acceso al antecedente técnico | El `Manual Saint` fue agregado por el usuario el 2026-08-03 (DOC-13). El `Manual Técnico de INNOVA` sigue ausente; registrar como referencia pendiente; no usarlo como autoridad arquitectónica |

## 7. Referencias INNOVA clasificadas como legado

| Documento | Tratamiento |
|---|---|
| DOC-10 (Compilación Providencias SENIAT INNOVA) | Fuente normativa. Conservar nombre original (documento fuente). El contenido es norma Nivel 1. |
| DOC-11 (Expediente SICA/SIGESAI/Decreto 1.808 INNOVA) | Antecedente normativo + funcional. Conservar nombre original. No usar la marca INNOVA en artefactos nuevos. |
| DOC-12 (Guías SENIAT/SICA/SIGESAI INNOVA) | Antecedente funcional. Conservar nombre original. |
| Fuente F1 (Manual INNOVA v1.1) | Antecedente de requerimientos. No disponible en el repositorio. |
| Fuente F2 (Manual Saint) | Referencia comparativa. No constituye fuente legal ni diseño obligatorio. |

## 8. Reglas de no renombrado

- No se renombran archivos históricos dentro de `requerimientos/`.
- Las referencias históricas conservan su nombre original cuando forman parte de documentos fuente.
- Todo artefacto nuevo debe usar la marca **KONTROL** (producto, paquetes `kontrol`, base `kontrol`, prefijo de contenedores `kontrol`, variables `KONTROL_*`, CLI `kontrol`).

## 9. Cálculo de hashes (verificación)

Los hashes SHA-256 se verifican con:

```bash
sha256sum requerimientos/*
```

Se registran en `docs/evidence/hashes-documental.txt` (archivo de evidencia) y se re-verifican antes de cada liberación. La verificación de integridad de los documentos fuente forma parte del checklist de la fundación (T-003 en `tasks.md`).

## 10. Estado de aprobación

| Elemento | Estado |
|---|---|
| Inventario completo | ✔ |
| Clasificación | ✔ |
| Duplicidades identificadas | ✔ |
| Conflictos | Ver `document-conflicts.md` |
| Vacíos | ✔ |
| Referencias INNOVA como legado | ✔ |
| Aprobación del inventario | Pendiente — requiere revisión del Analista de negocio y del Especialista en documentación |
