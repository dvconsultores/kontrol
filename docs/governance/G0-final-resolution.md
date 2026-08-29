# GATE G0 — RESULTADO

| Campo | Valor |
|---|---|
| Gate | G0 — Regularización de gobierno arquitectónico |
| Fecha | 2026-08-29 |
| Rama · HEAD | `develop` · `def2b52` |
| Cambios en código productivo | **0** |

---

## Estado general

**PASSED_WITH_NON_BLOCKING_PENDING_ITEMS**

Ningún bloqueante de gobierno permanece activo. Los pendientes que subsisten son empresariales,
legales y técnicos, y ninguno impide iniciar una Spec.

---

## ADR históricos

| Resultado | Cantidad | ADR |
|---|---:|---|
| **APPROVED** | **11** | 001, 002, 004, 006, 007, 009, 010, 012, 013, 014, 015 |
| **UPDATED_AND_APPROVED** | **4** | 003, 005, 008, 011 |
| **SUPERSEDED** | **0** | — (1 supersesión *parcial de sección*: ADR-008 §Consecuencias) |
| **REJECTED** | **0** | — |
| **TOTAL** | **15** | ✔ |

**ADR en `PROPUESTO`: 0.**

### Qué se corrigió en los cuatro actualizados

| ADR | Corrección |
|---|---|
| **003** PostgreSQL | Versión fijada en 18.x (cierra la validación pendiente CL-11/CON-01). Se documenta que `ADR-D0-001` lo extiende con paridad de producción: su omisión original permitió que toda la evidencia se generara sobre SQLite |
| **005** Firma asimétrica | Se cierra el diferimiento del portal central, ahora definido en `ADR-D0-006`. La decisión criptográfica se ratifica sin cambios |
| **008** Archivos | Se ratifica la estrategia de almacenamiento; el modelo de entidades queda superseded por `ADR-D0-008` (supersesión parcial y explícita) |
| **011** Multiempresa | La cadena organizacional incorpora `WarehouseZone`, `CostCenter` y `BusinessUnit`, para que dos ADR aprobados no describan cadenas distintas |

---

## ADR-D0

| Métrica | Valor |
|---|---:|
| Total | **13** |
| `APPROVED` | **13** |
| Conflictos con ADR históricos | **4 detectados · 4 resueltos** |
| Conflictos sin resolver | **0** |

---

## Constitución

| Métrica | Valor |
|---|---|
| Enmiendas propuestas | **3** |
| **Aprobadas** | **3** — E-01, E-02, E-03 |
| Rechazadas | **0** |
| Bloqueadas | **0** |
| **Nueva versión** | **1.1** (2026-08-29) |

| Enmienda | Nuevo principio | Refuerza | Specs afectadas |
|---|---|---|---|
| E-01 | **P21** Paridad del motor de persistencia | P10, P13 | las 56 |
| E-02 | **P22** Autoridad única por capacidad transversal | P17 | 045, 046, 047, 048, 051 y todas las que consuman una capacidad transversal |
| E-03 | **P23** Captura anticipada de datos no reconstruibles | P3, P5 | 011, 034 y las 18 con líneas transaccionales |

Ninguna de las tres contradice un principio vigente; las tres cierran huecos que la auditoría
demostró explotables: P10 no decía *dónde* se demuestra la calidad, P17 prohibía la divergencia en
interfaz pero no en dominio, y P5 protegía lo registrado pero no obligaba a registrar.

**Ratificación:** aprobadas en el Gate por Arquitectura, Seguridad y QA. La ratificación de Producto
y Legal queda registrada como **pendiente no bloqueante** — ninguna enmienda altera alcance funcional
ni compromiso normativo, por lo que su ratificación es confirmatoria y no condiciona el trabajo.

---

## Corrección D0

**Cantidad correcta de Specs desbloqueadas: 22.**

Las cifras anteriores —13 en el texto y 17 en la enumeración— eran ambas incorrectas, y las dos
matrices de origen daban 21 cada una con conjuntos distintos.

| Fuente | Cifra |
|---|---:|
| Texto de `D0-final-resolution.md` §11 | 13 ✗ |
| Enumeración del mismo párrafo | 17 ✗ |
| `D0-spec-dependencies.md` | 21 (omitía 023) |
| `D0-impact-matrix.md` | 21 (omitía 019) |
| **Unión verificada** | **22** ✔ |

**Lista definitiva:**

`007, 008, 011, 012, 015, 017, 018, 019, 020, 021, 022, 023, 025, 029, 030, 031, 032, 033, 034, 035, 045, 046`

Derivación auditable y verificación de los dos elementos divergentes en
`docs/governance/G0-correction-note.md`. Los tres documentos D0 quedaron corregidos con nota visible
de corrección; ninguna cifra incoherente permanece en el repositorio.

---

## Pendientes no bloqueantes

### Empresariales
Umbrales y niveles de aprobación (OQ-02) · disparador y vigencia de reserva (OQ-03) · precedencia de
precio, límites de descuento y alcance de comisiones (OQ-06) · modalidad de facturación y plazo de
homologación (OQ-09) · **hospedaje de la autoridad de licencias (OQ-07)**, que bloquea el *cierre* de
la Spec 004 pero no su trabajo.

### Legales
Las **24 reglas** de `D0-fiscal-validation-matrix.md`, ninguna en `VALIDATED`. Bloquean el cierre de
014, 039-043 y 056; no impiden especificarlas ni construirlas.

### Técnicos
Instancia PostgreSQL (BLK-D0-01) — bloquea `COMPLETE_100` de las 56, no el inicio de ninguna.
Deuda de código registrada: `latest` por defecto en `compose.yaml` (contradice ADR-014, prevalece el
ADR); `outbox_events` y `feature_flags` sin consumidor; auditoría no instrumentada en `organization`
y `master_data`.

### De gobierno
Ratificación de Producto y Legal de la Constitución v1.1.

---

## Bloqueantes

**NINGUNO.**

Las siete contradicciones arquitectónicas detectadas quedaron resueltas con autoridad explícita
(`G0-governance-matrix.md` §Contradicciones). No existe contradicción BLOCKER activa entre
Constitución, ADR aprobados y decisiones D0.

---

## Baseline arquitectónica

**`docs/governance/KONTROL_ARCHITECTURE_BASELINE.md`** — versión 1.0.

Consolida en veinte secciones únicamente decisiones formalmente aprobadas: arquitectura general,
frontend, backend, PostgreSQL, Docker e instalación, autenticación, permisos y multiempresa,
auditoría, licenciamiento, aprobaciones, inventario y reservas, almacenes, archivos, unidades y
snapshots, reglas comerciales, facturación y confirmación, gobierno fiscal, pruebas y seguridad.
No introduce ninguna decisión nueva. Su §20 declara expresamente lo que **no** decide y quién lo decide.

---

## Artefactos producidos

| Ruta | Contenido |
|---|---|
| `docs/governance/architecture-decision-register.md` | Registro maestro — 29 ADR vigentes |
| `docs/governance/KONTROL_ARCHITECTURE_BASELINE.md` | Baseline arquitectónica única |
| `docs/governance/G0-governance-matrix.md` | 30 temas · 7 contradicciones resueltas · 0 BLOCKER |
| `docs/governance/G0-correction-note.md` | Corrección 13/17 → 22 con derivación |
| `docs/governance/G0-final-resolution.md` | Este documento |
| `.specify/memory/constitution.md` | **v1.1** con P21, P22 y P23 |
| `specs/001-fundacion/adr/ADR-001..015` | 15 ADR regularizados |
| `specs/012-.../adr-012-numeric-precision.md` | Renumerado a **ADR-016** |
| `docs/governance/d0-foundational-decisions/` | 3 documentos corregidos |

---

## Hallazgos propios de este Gate

Dos que no venían de D0:

**Colisión de numeración de ADR.** Existían dos ADR distintos numerados 012 —Auditoría y Precisión
numérica— porque el segundo tomó su número de la Spec que lo originó. Citar «ADR-012» era ambiguo en
todo el repositorio. Resuelto: el de precisión numérica pasa a **ADR-016**; regla derivada de
numeración global única.

**Contradicción ADR-014 frente al código.** `compose.yaml` usa `latest` como tag por defecto, que el
ADR prohíbe. Se resuelve por jerarquía: el código es Nivel 7 y no justifica contradicciones. El ADR
prevalece y el código queda registrado como deuda. Es la aplicación práctica del principio de que el
código no es autoridad funcional.

---

## Veredicto

# ARQUITECTURA FORMALMENTE AUTORIZADA PARA CONTINUAR CON NUEVAS SPECS

29 ADR vigentes sin contradicción activa · Constitución v1.1 con las tres enmiendas incorporadas ·
baseline arquitectónica única publicada · 0 ADR en `PROPUESTO` · 0 bloqueantes de gobierno ·
inconsistencia numérica corregida y trazable.

---

## Próxima Spec recomendada

**`045 — Motor de aprobaciones y segregación`**

Fundamento: nodo de mayor grado de salida del grafo de dependencias (bloquea 015, 017, 025, 030, 033
y 047); ya existen cuatro implementaciones divergentes que crecerán con cada Spec nueva; su
arquitectura está cerrada en `ADR-D0-002` y `POL-D0-001`; y el nuevo **P22** la convierte en
obligación constitucional, no en preferencia. Los umbrales desconocidos no la bloquean: son
configuración de implantación.

Orden posterior vigente: **008** → **011** → **046** → **012**.

**No se crea en este Gate. Se solicita autorización expresa.**
