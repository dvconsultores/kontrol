# Spec · CTL-05 Expediente de cuenta y reportes de rendición

**Requisitos sponsor:** GOV-CTL-006 y GOV-CTL-007, ambos P0.
**Actor principal:** Control Interno o el cuentadante.
**Fuentes:** [FUENTES.md](FUENTES.md). **Decisiones:** [DECISIONES.md](DECISIONES.md).

## Historias

- **US1 (P0) · Formar la cuenta.** La persona responsable crea un expediente de cuenta para el ente, con período, fecha de corte, responsable institucional (una ocupación de ORG-04) y denominación. Ve los hechos reales del período que hay en Gobierno, filtrados y paginados en el servidor. Incorpora y retira piezas y revisa el índice provisional.
  - *Aceptación:*
    1. Solo aparecen hechos del ente y del corte.
    2. Una pieza no puede repetirse.
    3. Un hecho fuera de [desde, corte], de otro ente o inexistente se rechaza.
- **US2 (P0) · Cerrar la formación.** Al formar, el índice queda enumerado 1..n y la cuenta, congelada. Se generan el reporte de rendición, con cifras reproducibles, y su PDF.
  - *Aceptación:*
    1. Un hecho posterior no altera la cuenta formada.
    2. Toda cifra declara fuente, filtro, período, conjunto, regla y resultado.
    3. El PDF y el CSV salen del snapshot.
- **US3 (P0) · Trazabilidad e integridad.** Cada pieza abre su fuente: el evento en la bitácora, el objeto si existe y sus soportes. La verificación compara cada pieza congelada con su origen y declara VALIDO o INCOMPLETO, sin ocultar faltantes.
- **US4 (P0) · Rendición y calificación.** Se registran la participación (fecha, oficio y plazo de 90 días), la calificación (conforme u objetada, según el informe definitivo del órgano de control) y el fenecimiento (auto).
  - *Aceptación:*
    1. Quien registra la calificación no puede ser quien formó la cuenta ni el cuentadante.
    2. No hay calificación automática.
- **US5 (P0) · Subsanación.** Mientras no esté calificada, una cuenta formada o participada puede sustituirse por una versión nueva con motivo. La anterior queda SUSTITUIDA e intacta.
- **US6 (P0) · Listado, ficha e historial.**
  - El listado tiene filtros de período, responsable, unidad, estado y texto, con paginación en el servidor.
  - La ficha muestra las seis preguntas del encargo (§19).
  - El historial se lee de la bitácora.

## Requisitos funcionales

| Id | Requisito |
|---|---|
| FR-01 | Crear el expediente con: denominación (3 a 200), ejercicio opcional, `periodo_desde` ≤ `periodo_hasta`, `fecha_corte` ∈ [desde, hasta], asignación ORG-04 del ente con vigencia solapada y observaciones (≤1000). El código es CTA-AAAA-NNNN y empieza en la versión 1, EN_FORMACION. |
| FR-02 | Editar la cabecera solo en EN_FORMACION y con If-Match de versión. |
| FR-03 | Las candidatas son los eventos de Gobierno del ente en [desde, corte] (salvo los de CTL-05), con filtros de proceso, acción y texto, paginados (≤50) y con la marca de incluida. |
| FR-04 | Incorporar o retirar piezas solo en EN_FORMACION. La unicidad (expediente, evento) la impone PostgreSQL. |
| FR-05 | Formar exige al menos 1 pieza. Hace ordinales deterministas, congela las piezas y la huella, guarda el snapshot con SHA-256 y el PDF en storage con SHA-256, y serializa con FOR UPDATE. |
| FR-06 | El reporte se ofrece en JSON (provisional antes de formar) y en PDF e índice CSV (solo con la cuenta formada). Cada descarga queda auditada. |
| FR-07 | La verificación de integridad (PDD-CTL05-08) queda auditada. |
| FR-08 | Registrar la participación (FORMADA → PARTICIPADA). |
| FR-09 | Registrar la calificación, desde PARTICIPADA, con maker-checker y MFA. |
| FR-10 | Registrar el fenecimiento desde CALIFICADA. Si la calificación fue OBJETADA, el fundamento es obligatorio (art. 33). |
| FR-11 | Crear una versión nueva desde FORMADA o PARTICIPADA. |
| FR-12 | Aislamiento: el id de otro ente responde 404 y un evento de otro ente no se incorpora. |
| FR-13 | Permisos `gobierno_rendicion:view`, `:form` y `:qualify`. La interfaz oculta lo no autorizado. |
| FR-14 | Interfaz: menú Gobierno › Expedientes de cuenta, con listado, alta, ficha (índice, piezas, reporte, historial) y acciones. Responsive a 1280/390/320 y WCAG 2.2 AA. |

## Fuera de alcance

- Presupuesto, compromisos, pagos, contabilidad, bienes, contratos y montos.
- El expediente electrónico general (DOC-01).
- El examen por muestreo dentro de la cuenta, que es del órgano de control.
- La notificación electrónica al órgano de control.
