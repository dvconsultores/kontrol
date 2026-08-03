# Matriz de Autoridad Documental de KONTROL

| Campo | Valor |
|---|---|
| Documento | Matriz de autoridad y jerarquía de fuentes |
| Versión | 1.0 |
| Fecha | 2026-08-03 |
| Responsable | Especialista en gobernanza normativa y documental |
| Ruta | `docs/governance/authority-matrix.md` |

## 1. Propósito

Establecer la jerarquía de autoridad que resuelve conflictos entre fuentes y determina qué documento prevalece en cada decisión de KONTROL. Complementa la sección "Jerarquía de autoridad" de la Constitución.

## 2. Jerarquía de autoridad

| Nivel | Fuente | Uso | Peso |
|---|---|---|---|
| 1 | Normas oficiales venezolanas vigentes (leyes, decretos, providencias, resoluciones, Gacetas, instructivos oficiales, publicaciones SENIAT/BCV/SUNAGRO/INSAI/SACS) | Reglas obligatorias, alícuotas, sujetos, documentos, sanciones, vigencia | Máxima autoridad. No se declara cumplimiento con duda |
| 2 | Constitución de KONTROL | Principios no negociables | Vinculante |
| 3 | Documentos maestros vigentes de KONTROL | Línea base funcional, fiscal, técnica, UX, licenciamiento, QA | Vinculante salvo contradicción con Nivel 1 o 2 |
| 4 | Specs aprobadas | Gobiernan la implementación de su iniciativa | Vinculante dentro de su iniciativa |
| 5 | ADR aprobados | Decisiones técnicas específicas | Vinculante dentro de su alcance |
| 6 | Contratos (OpenAPI, eventos, archivos, esquemas) | Integración | Vinculante para integración |
| 7 | Código y pruebas | Deben obedecer la Spec; no justifican contradicciones | Subordinado |
| 8 | Antecedentes INNOVA y manuales de terceros (Saint, etc.) | Referencia comparativa y normativa; no autoridad arquitectónica ni legal | No vinculante |

## 3. Estado de validación normativa

Cada norma recibe uno de estos estados:

- `VIGENTE` — fuente oficial verificada.
- `LEGAL_VALIDATION_REQUIRED` — no puede verificarse vigencia, existen normas contradictorias, falta fuente oficial o la interpretación afecta un documento fiscal/alícuota/retención/obligación/homologación.
- `REFERENCIA` — fuente de apoyo no certificada.

> Regla: cuando una norma fiscal o regulatoria tenga estado `LEGAL_VALIDATION_REQUIRED`, no se implementa la parte afectada hasta resolución, y se incluye en `/speckit.clarify`.

## 4. Matriz normativa inicial (base jurídico-funcional)

| Norma | Instrumento / Gaceta | Dominio | Estado | Impacto en KONTROL |
|---|---|---|---|---|
| Código Orgánico Tributario | Decreto Constituyente; G.O. N.º 6.507 Ext. 29-01-2020 | Deberes formales, fiscalización, ilícitos | `LEGAL_VALIDATION_REQUIRED` (revalidar) | Marco de conservación documental y responsabilidad |
| Ley del IVA | Reforma; G.O. N.º 6.507 Ext. 29-01-2020 | IVA, débito/crédito, alícuotas, facturación | `LEGAL_VALIDATION_REQUIRED` | Motor IVA versionado; alícuotas 16/8/0/adicional 15 |
| Ley de ISLR | G.O. N.º 6.210 Ext. | ISLR, retenciones | `LEGAL_VALIDATION_REQUIRED` | Retenciones ISLR |
| Ley de IGTF | Reforma; G.O. N.º 6.687 Ext. 25-02-2022 | IGTF | `LEGAL_VALIDATION_REQUIRED` | Motor IGTF ligado al pago |
| Decreto N.º 4.972 (IGTF) | G.O. N.º 6.821 Ext. 12-07-2024 | Alícuotas IGTF 0%/3% | `LEGAL_VALIDATION_REQUIRED` | Reglas IGTF por numeral |
| Providencia SNAT/2011/00071 | G.O. N.º 39.795 08-11-2011 | Emisión de facturas y otros documentos | `LEGAL_VALIDATION_REQUIRED` | Forma libre, requisitos, guías de despacho |
| Providencia SNAT/2018/0141 | G.O. N.º 41.518 06-11-2018 | Imprentas y máquinas fiscales | `LEGAL_VALIDATION_REQUIRED` | Lotes de números de control |
| Providencia SNAT/2024/000102 | G.O. N.º 43.032 19-12-2024 | Medios digitales de emisión | `LEGAL_VALIDATION_REQUIRED` | Facturación digital, contingencia, conservación 10 años |
| Providencia SNAT/2024/000121 | G.O. N.º 43.032 19-12-2024 | Requisitos proveedores de sistemas / homologación | `LEGAL_VALIDATION_REQUIRED` | Homologación, registro inalterable, eventos |
| Providencia SNAT/2025/000054 | G.O. N.º 43.171 16-07-2025 | Agentes de retención IVA (75%/100%) | `LEGAL_VALIDATION_REQUIRED` | Motor retención IVA |
| Providencia SNAT/2016/0004 | G.O. N.º 40.834 22-01-2016 | IGTF sector bancario (percepción) | `LEGAL_VALIDATION_REQUIRED` | Percepción IGTF |
| Providencia SNAT/2016/0005 | G.O. N.º 40.835 25-01-2016 | Declaración y pago IGTF | `LEGAL_VALIDATION_REQUIRED` | Declaración IGTF |
| Providencia SNAT/2022/000013 | G.O. N.º 42.339 17-03-2022 | SPE como agentes de percepción IGTF | `LEGAL_VALIDATION_REQUIRED` | Percepción IGTF |
| Providencia SNAT/2025/000091 | G.O. N.º 43.273 09-12-2025 | Calendario fiscal 2026 SPE | `LEGAL_VALIDATION_REQUIRED` | Calendario y plazos |
| Decreto N.º 1.808 | Reglamento ISLR retenciones; G.O. N.º 36.203 12-05-1997 | Retenciones ISLR | `LEGAL_VALIDATION_REQUIRED` | Catálogo de conceptos art. 9, sustraendo, UT |
| Ley Sistema Nacional Integral Agroalimentario | Decreto N.º 1.405; G.O. Ext. N.º 6.150 18-11-2014 | SICA | `LEGAL_VALIDATION_REQUIRED` | Control agroalimentario |
| Resolución DM/N.º 025-12 (SICA) | G.O. N.º 39.949 21-06-2012 | Guía Única de Movilización | `LEGAL_VALIDATION_REQUIRED` | Guía SICA; derogó DM/N.º 22-12 |
| Ley de Salud Agrícola Integral | Decreto N.º 6.129; G.O. Ext. N.º 5.890 31-07-2008 | SIGESAI / INSAI | `LEGAL_VALIDATION_REQUIRED` | Permisos de movilización |
| Resolución INSAI (vigencia importación) | G.O. N.º 43.147 11-06-2025 | Vigencia 6 meses permisos importación | `LEGAL_VALIDATION_REQUIRED` | Vigencias separadas por tipo |
| Providencia SACS N.º 122-2016 | SACS | Guía Sanitaria de Movilización de Alimentos | `LEGAL_VALIDATION_REQUIRED` | Requisito SACS por rubro |

## 5. Criterio de prevalencia (textual, de los documentos maestros)

> "Las fuentes oficiales y las Gacetas Oficiales prevalecen sobre manuales comerciales, documentación histórica, comportamiento actual del código o prácticas de mercado. Saint se usa como referencia comparativa, no como autoridad legal. Antes de producción, la matriz normativa debe ser revisada por abogado tributario venezolano, contador público y equipo de homologación." — Volúmenes 0–6.

## 6. Decisiones de autoridad en 001-fundacion

| Tema | Autoridad | Estado |
|---|---|---|
| Nombre del producto | KONTROL (decisión de producto en Volumen 0) | Vigente |
| Núcleo fiscal separado | Volumen 1, regla no negociable | Vigente |
| Flujo Spec Kit | Volumen 6 | Vigente |
| Estándar frontend | DOC-08 (Estándar Maestro Frontend v1.0) | Vigente |
| Modelo de licenciamiento | DOC-07 (Especificación Licenciamiento) | Vigente |
| Stack tecnológico | DOC-08 (Vite 8, React 19, PostgreSQL 18, Python 3.13) | Sujeto a validación en `research.md` |

## 7. Estado de aprobación

| Elemento | Estado |
|---|---|
| Matriz de autoridad creada | ✔ |
| Normas con estado `LEGAL_VALIDATION_REQUIRED` | ✔ (todas las fiscales/regulatorias; se revalidan antes de cada liberación) |
| Revisión por abogado tributario | ✔ **CERTIFICADO** (2026-08-04) |
| Revisión por contador público | ✔ **CERTIFICADO** (2026-08-04) |
| Aprobación | ✔ certificado por los profesionales (ver `docs/evidence/legal-review-package.md`) |
