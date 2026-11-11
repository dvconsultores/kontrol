# Plan PROC-10 · Garantías y cauciones

Base: `4f069bc` (+ `e3004a8`, deuda de matriz de PROC-06). Cabeza de Alembic al empezar: `0094_gov_proc08_decision` (única).
Migración nueva: `0096_gov_proc10_garantias` sobre `0095_fusion_gov_planning`. Nació como `0095_gov_proc10_garantias` y se
reposicionó en el bloque 2 (2026-11-10): al
integrar `e22a394`, la cabeza pública pasó a ser `0095_fusion_gov_planning` (fusión de PROC-08 y Spec 015); la revisión inédita
de PROC-10 se renombró a `0096_gov_proc10_garantias` con padre `0095_fusion_gov_planning`, sin migración de fusión. Módulo `government` existente (FastAPI, SQLAlchemy,
PostgreSQL, React + TanStack Query).

## Autoridad normativa: `app/modules/government/garantias_reglas.py`

Catálogo de código inmutable y único (PDD-PROC10-01, Principio 19). `ReglaGarantia` (dataclass congelada) con `codigo`, `version`,
`tipo`, `nombre`, `fuente`, `gaceta`, `vigente_desde`, `vigente_hasta`, `etapa`, `requiere_adjudicacion`, `forma`, `base`,
`porcentaje_min`, `porcentaje_max`, `moneda_exigida`, `emisores_admitidos`, `permite_sustitucion`, `permite_coexistencia`,
`retencion_alternativa_pct`, `vigencia_exigida`, `condicion_liberacion` y `condicion_ejecucion`. Las 9 reglas iniciales (versión 1,
vigentes desde 2014-11-19):

| Código | Tipo | Forma | Base | % mín-máx | Otros |
|---|---|---|---|---|---|
| MANT-PRESUPUESTO-1 | MANTENIMIENTO_OFERTA | PORCENTAJE | PRESUPUESTO_ESTIMADO_SIN_TRIBUTOS | 1,50-2,50 | etapa PROCEDIMIENTO, sin adjudicación |
| MANT-OFERTA-1 | MANTENIMIENTO_OFERTA | PORCENTAJE | MONTO_OFERTA | (0]-100 | ídem |
| MANT-FIJO-1 | MANTENIMIENTO_OFERTA | MONTO_FIJO | — | — | moneda exigida VES |
| ANTICIPO-1 | ANTICIPO | PORCENTAJE | MONTO_ANTICIPO | 100-100 | FORMALIZACION, adjudicación |
| FIEL-1 | FIEL_CUMPLIMIENTO | PORCENTAJE | MONTO_CONTRATO_CON_TRIBUTOS | 20-100 | sustitución, coexistencia, retención 10 % |
| LABORAL-1 | LABORAL | PORCENTAJE | COSTO_PERSONAL_OFERTA | (0]-10 | emisores BANCO, ASEGURADORA, SGR; sustitución, coexistencia, retención 5 % |
| RESP-CIVIL-1 | RESPONSABILIDAD_CIVIL | MONTO_FIJO | — | — | FORMALIZACION, adjudicación |
| OTRA-FIJO-1 | OTRA | MONTO_FIJO | — | — | FORMALIZACION, adjudicación |
| OTRA-PORC-1 | OTRA | PORCENTAJE | BASE_DEL_PLIEGO | (0]-100 | ídem |

`base_disponible(base)` devuelve `None` para toda base: la plataforma no registra ninguna (PDD-PROC10-05). Es la única costura que CNT-01
ampliará.

## Datos (migración 0095, paridad con los modelos)

- `gov_guarantee_issuers`: tipo, nombre, RIF (único por ente), banco de TRE-01 (si y solo si BANCO), estado. Sin DELETE ni TRUNCATE en PG.
- `gov_guarantee_requirements`: expediente, número, código de regla e instantánea JSON, tipo, etapa, nombre, forma, porcentaje o monto
  fijo, moneda (si y solo si MONTO_FIJO), vigencia mínima, fundamento, documento fijado (id, versión, número, sha256), registro y
  funcionario. Inmutable en PG.
- `gov_guarantee_instruments`: expediente, número, requisito, tipo, etapa, oferta, decisión (post-adjudicación), emisor, referencia del
  emisor, monto (> 0), moneda, fechas, documento fijado, observación, origen (REGISTRO, RENOVACION, SUSTITUCION) y antecesor (único),
  estado y `afectada_en`. Guarda PG: solo REGISTRADA → estado final, una vez, sin tocar el resto. Índice único parcial (ente, emisor,
  referencia) entre REGISTRADAS.
- `gov_guarantee_events`: expediente, instrumento, acción (REGISTRO, RENOVACION, SUSTITUCION, LIBERACION, EJECUCION), fecha, motivo,
  acto y cargo, documento fijado, instrumento nuevo, monto y moneda ejecutados, precondición y detalle, registro y funcionario.
  Inmutable en PG. Índices únicos parciales: un REGISTRO por instrumento y una actuación final por instrumento.
- `gov_procurement_file_events.clase` admite `GARANTIA`.
- Permisos `gobierno_garantias` view, manage, release y execute, concedidos a FUNCIONAL_COMPLETO.

## API (`/api/v1/gobierno/contrataciones`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| GET `/garantias/emisores` | view | emisores del ente y bancos activos de TRE-01 |
| POST `/garantias/emisores` | manage | emisor (201) |
| GET `/expedientes/{id}/garantias` | view | estado completo |
| POST `/expedientes/{id}/garantias/requisitos` | manage + If-Match | estado (201) |
| POST `/expedientes/{id}/garantias` | manage + If-Match | estado (201) |
| POST `/expedientes/{id}/garantias/{gid}/renovar` | manage + If-Match | estado (201) |
| POST `/expedientes/{id}/garantias/{gid}/sustituir` | manage + If-Match | estado (201) |
| POST `/expedientes/{id}/garantias/{gid}/liberar` | release (MFA) + If-Match | estado (201) |
| POST `/expedientes/{id}/garantias/{gid}/ejecutar` | execute (MFA) + If-Match | estado (201) |

El estado devuelve:
- la versión y la fecha de negocio;
- los permisos efectivos (`puede`);
- el resumen;
- la adjudicación vigente;
- los requisitos, con la regla y la cobertura por sujeto;
- los instrumentos, con suficiencia, criterios, vigencia, días, acciones e historial de su cadena;
- las ofertas, los emisores, los documentos del expediente, los actos elegibles y las reglas vigentes.

Sin UUID en los textos: se usan las referencias REQ-nn, GAR-nn, O-nn y DEC-nn.

## Interfaz

`ExpedienteGarantias.tsx` (`SeccionGarantias`), montada en `ExpedientePage.tsx` tras «Recomendación y decisión», visible con
`gobierno_garantias:view`.

La sección muestra:
- un resumen textual;
- requisitos, con un formulario condicional por forma y tipo;
- emisores, con el banco elegido del catálogo;
- garantías, con su suficiencia y criterios, vigencia, días y alertas.

Las acciones se ejecutan en línea con confirmación en la misma pantalla, como en PROC-08. El historial va por garantía. Las acciones se ocultan sin permiso.

## Pruebas

- **Backend PostgreSQL** (`tests/test_gov_proc10_garantias.py`):
  - flujo de mantenimiento con monto fijo: insuficiente por vigencia, renovación, suficiente y liberación con precondición verificada;
  - fiel cumplimiento del adjudicatario NO_EVALUABLE, sustitución y ejecución;
  - negativas materiales del encargo §58;
  - concurrencia forzada (dos ejecuciones);
  - aislamiento entre entes;
  - inmutabilidad en PostgreSQL;
  - auditoría y cronología;
  - SoD configurada.
- **E2E** `e2e/gobierno-garantias.spec.ts` (Chromium, PostgreSQL efímero, analizador):
  - SC-001, SC-002 y SC-003;
  - Axe en la sección, el formulario, la confirmación y el historial;
  - 390 y 320 px.
- **Regresión mínima:**
  - PROC-08 (E2E y backend);
  - cronología de PROC-03;
  - documentos;
  - guardas de recuento: delegación 151 y MFA 63/71; tras integrar `e22a394`, auditoría 460 (453 públicas + 7) y cabeza
    `0096_gov_proc10_garantias`.

## Llamadas a DeepSeek (máx. 5, objetivo 3, v4-pro, stream)

1. Backend completo: reglas, modelos, migración, registros, servicio, esquemas, API y guardas de recuento.
2. Pruebas de backend en PostgreSQL, más el frontend (API e interfaz de la sección).
3. E2E y los defectos reales que salgan.
4. Reserva funcional.
5. Solo para una causa raíz nueva.

## Constitution gate

| Principio | Cómo se cumple |
|---|---|
| 1 Spec antes que código; 2 autorización | Este Spec; mandato de la dueña del 2026-11-10 nombra PROC-10 |
| 3 Trazabilidad | `traceability.md`: GOV-PROC-013 → FR → tareas → pruebas |
| 5 Históricos protegidos; 13 integridad | Requisitos, instrumentos y actuaciones append-only; guardas PG; una transacción por actuación |
| 6 Seguridad en backend | Permisos, MFA, ente, If-Match, acto y SoD en el servidor; la interfaz solo oculta |
| 7, 11, 17 Frontend uniforme, accesible y responsive | Mismos componentes de la ficha; Axe y 320/390 |
| 8, 19 Reglas versionadas con fuente | Catálogo único con fuente, Gaceta, vigencia y versión; instantánea en el requisito |
| 12 Decisiones documentadas | `DECISIONES.md` |
| 18 Modales | Ninguno: confirmación en línea, como las secciones vecinas de la ficha |
| 20 Organismos oficiales | Se registra el instrumento del emisor; no se fabrica ni se valida contra la Superintendencia |
| 21, 24 PostgreSQL y base limpia | Pruebas y E2E en PostgreSQL; Alembic desde cero, abajo y arriba |
| 22 Autoridad única transversal | Documentos de Spec 046, auditoría CTL-02, actos DOC-02, SoD CTL-01, identidad ORG-06: reutilizados |
| 23 Captura anticipada | Se capturan las fechas, el emisor, el monto, la moneda y el documento con huella al registrar |
| 25 Concurrencia en la base | Índices únicos parciales; la violación esperada se traduce a 409 |
| 26 Paridad | Mismos nombres de restricciones en modelos y migración; prueba de paridad en el cierre |
| 27 Mutaciones válidas | Si se mutan, solo cuentan las observables |

Fuentes reconciliadas:
- GOV-PROC-013, N11 y N12 (`FUENTES.md`).
- PROC-03: expediente, cronología y `_para_escribir`.
- PROC-06: ofertas y documentos fijados.
- PROC-08: decisión vigente ADJUDICADA.
- DOC-02: actos.
- Spec 046: documentos.
- ORG-06: identidad.
- CTL-01: SoD.
- CTL-02: auditoría.
- TRE-01: bancos.
- `MONEDAS_LIMITE` (VES, USD, EUR).
- Party no se usa (Enterprise).

**CONSTITUTION_GATE = PASS** · `MATERIAL_DECISION_REQUIRED = 0` · `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`.
