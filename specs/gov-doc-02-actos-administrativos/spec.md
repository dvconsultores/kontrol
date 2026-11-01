# Spec · GOV-DOC-02 Actos administrativos con autoridad, competencia, motivación, eficacia y notificación (DOC-02)

## 1. Lo que podrá hacer el usuario (vista del sponsor)

Cuando este ciclo termine, el responsable de los actos del ente podrá, desde **Gobierno › Actos administrativos**, registrar cada acto
que la autoridad ya firmó: su tipo, número y fecha; qué cargo lo dicta y con qué competencia y fundamento legal; quién lo firmó y con
qué titularidad (titular, por delegación, encargado o suplente); a quién va dirigido; los hechos, los fundamentos legales y lo que
decide. Adjuntará el PDF firmado y lo dará por emitido; luego registrará su publicación en Gaceta o su notificación, con su soporte, y
el sistema le dirá desde qué fecha es eficaz. Si hubo un error material lo corregirá dejando versión y motivo; si otro acto lo revoca o
declara su nulidad, lo dejará constando con referencia a ese acto. Consultará el registro del año con filtros, verá el historial de
cada acto, exportará el registro a CSV, y el auditor verá cada paso en la auditoría.

## 2. Fuentes y decisiones

| Tipo | Id | Contenido |
|---|---|---|
| Requisito | GOV-DOC-003 (P0; N02, N25) | «Registrar actos administrativos con tipo, autoridad, competencia, motivación, fecha de eficacia y notificación» |
| Vecinos | GOV-DOC-001 (DOC-01 expediente, BLOCKED N40), GOV-DOC-005 (DOC-04 notificaciones con constancia por canal), GOV-DOC-006 (DOC-05 firma, BLOCKED), GOV-ORG-004/009 (ORG-04 delegación y catálogo por ente, BLOCKED N37), GOV-ORG-003 (ORG-03 cargos, OWNER_UAT_READY), GOV-ORG-007 (ORG-06 persona, BLOCKED N40) | Fronteras en §4 |
| Norma | N25 LOPA, G.O. 2.818 Ext., 01-07-1981 (clase A; texto oficial alojado por CONATEL, verificado el 2026-11-01) | art. 7 (definición), 9 (motivación de actos particulares, salvo simple trámite), 14 y 17 (jerarquía y formas), 18 (contenido: organismo, órgano, lugar y fecha, destinatario, hechos y fundamentos, decisión, funcionario con titularidad y, por delegación, número y fecha del acto de delegación; firma autógrafa), 72 (publicación en Gaceta de los actos generales, salvo asuntos internos), 73–76 (notificación de los particulares; defectuosa no produce efecto; personal con recibo firmado; por prensa, notificado 15 días después), 82 (revocación), 83 (nulidad absoluta), 84 (corrección de errores materiales) |
| Norma | N02 LOAP (clase A) | competencia y autoridad del ente (control derivado: «modelar competencia/autoridad y ámbito del ente») |
| Dueña | **OD-DOC02-01** | KONTROL **registra actos ya suscritos**: número y fecha los del propio acto (no los genera el sistema); el PDF firmado es obligatorio para darlo por emitido |
| Dueña | **OD-DOC02-02** | Tipos: catálogo cerrado de la **jerarquía de la LOPA** (arts. 14 y 17): decreto, resolución, orden, providencia, instrucción, circular y «otra decisión» con su denominación |
| Dueña | **OD-DOC02-03** | Autoridad = **cargo vigente de ORG-03 + una de sus competencias + fundamento legal**; funcionario y titularidad se transcriben del acto; KONTROL no valida la persona (ORG-06) ni la delegación (ORG-04) |
| Dueña | **OD-DOC02-04** | DOC-02 registra el **requisito de eficacia y su cumplimiento** (general → publicación; particular → notificación; interno → ninguno), con fecha y soporte, y de ahí la fecha de eficacia; canal autorizado y constancia gestionada son DOC-04 |

Ningún número de artículo de esta Spec viene de memoria: todos se leyeron en el texto oficial (sha256 del PDF en la evidencia).

## 3. Modelo del proceso

| Elemento | Valor |
|---|---|
| PROCESS_ID / NAME | DOC-02 · Actos administrativos con autoridad, motivación y eficacia |
| Propósito | Dejar constancia estructurada y verificable de cada acto del ente: quién, con qué competencia, qué decide, por qué y desde cuándo produce efectos |
| Actor principal | Responsable de actos (registra: `gobierno_actos:edit`; da por emitido, registra eficacia y corrige: `gobierno_actos:issue`; registra revocación o nulidad: `gobierno_actos:annul`) |
| Secundarios | Consulta (`gobierno_actos:view`); auditor (`audit:view`) |
| Precondiciones | Ente configurado (ORG-01); estructura del año del acto con el cargo emisor VIGENTE o INACTIVO cuya vigencia cubre la fecha (ORG-02/03) |
| Pasos | registrar borrador → adjuntar PDF firmado → emitir → (general/particular) registrar publicación o notificación con soporte → eficaz → (en adelante) corregir error material / revocación / nulidad |
| Estado final | EFICAZ, REVOCADO o NULO; nunca se borra un acto emitido |

### Máquina de estados

| Desde | Acción | Capacidad | Precondición | Hacia | Efecto | Auditoría |
|---|---|---|---|---|---|---|
| — | registrar | `edit` | ente; autoridad válida (§5); número libre | BORRADOR | versión 1 | GOV_ACT_CREATED |
| BORRADOR | modificar | `edit` | `If-Match` | BORRADOR | versión + 1 | GOV_ACT_UPDATED |
| BORRADOR | eliminar | `edit` | sin documentos vinculados; `If-Match` | — | borra acto e historia de borrador | GOV_ACT_DELETED |
| BORRADOR | emitir | `issue` | faltantes = ∅ (§4.4); documento del acto vinculado y ACTIVO; autoridad revalidada; `If-Match` | EMITIDO (GENERAL, PARTICULAR) o EFICAZ (INTERNO, con su fecha de eficacia) | congela los vínculos documentales (Spec 046 `freeze_links`); versión + 1 | GOV_ACT_ISSUED |
| EMITIDO | registrar eficacia | `issue` | §4.5; soporte vinculado, ACTIVO y distinto del documento del acto; `If-Match` | EFICAZ | fecha de eficacia; congela vínculos; versión + 1 | GOV_ACT_EFFECTIVENESS_RECORDED |
| EMITIDO, EFICAZ | corregir error material (LOPA art. 84) | `issue` | solo campos descriptivos (§4.6); motivo; `If-Match` | igual | versión + 1 con antes/después | GOV_ACT_CORRECTED |
| EMITIDO, EFICAZ | registrar revocación (art. 82) | `annul` | acto revocatorio registrado, EMITIDO o EFICAZ, del mismo ente, distinto, con fecha ≥ fecha del acto; motivo; `If-Match` | REVOCADO | `revocado_por`, fecha = la del acto revocatorio; versión + 1 | GOV_ACT_REVOKED |
| EMITIDO, EFICAZ | registrar nulidad (art. 83) | `annul` | ídem con el acto que la declara | NULO | `anulado_por`; versión + 1 | GOV_ACT_NULLIFIED |
| REVOCADO, NULO | — | — | — | (solo lectura) | — | — |

## 4. Contratos

### 4.1 Acto (ACT_CONTRACT)

- Un **acto administrativo** es la declaración que dictó una autoridad del ente (LOPA art. 7); el PDF es su **evidencia**, no el acto
  (DOCUMENT FILE ≠ ADMINISTRATIVE ACT). El acto no es un expediente (DOC-01), ni una delegación (ORG-04), ni una firma (DOC-05).
- Pertenece al ente (empresa del contenedor, OD-GOV0-03). Su año es el de su fecha.
- **Numeración (OD-DOC02-01):** el número es el que consta en el acto (procedencia externa, texto). No hay numeración del sistema.
  Para impedir el doble registro: único por (cargo emisor, tipo, denominación del tipo normalizada, número normalizado), con
  normalización = recortar y pasar a mayúsculas; colisión → 409 `GOV_ACT_NUMBER_DUPLICATE`.
- Historia: cada operación guarda una versión inmutable (instantánea completa, motivo, actor). Un acto emitido nunca se borra ni se
  reescribe; solo se corrige con motivo (art. 84) o cambia de estado por otro acto (arts. 82–83).

### 4.2 Tipo (OD-DOC02-02)

`DECRETO`, `RESOLUCION`, `ORDEN`, `PROVIDENCIA`, `INSTRUCCION`, `CIRCULAR`, `OTRA_DECISION`. Con `OTRA_DECISION` es obligatoria la
denominación (p. ej. «Punto de cuenta», 3–80); con los demás debe ir vacía. La validación de qué forma corresponde a qué órgano
(arts. 15–17) y los tipos propios de cada ente son de ORG-04 (GOV-ORG-009): fuera de alcance.

### 4.3 Autoridad, competencia y titularidad (OD-DOC02-03; APPLICATION PERMISSION ≠ INSTITUTIONAL AUTHORITY)

- **Cargo emisor** (`cargo_id`, FK a `gov_positions`): de la estructura del ejercicio igual al año de la fecha del acto, del mismo
  ente, en estado VIGENTE o INACTIVO, con `vigente_desde ≤ fecha ≤ (vigente_hasta o 31-dic)`. Si no → 422 `GOV_ACT_INVALID_AUTHORITY`.
  El órgano emisor (LOPA art. 18.2) es la unidad del cargo y el organismo (18.1) es el ente: se derivan, no se teclean.
- **Competencia**: una (acción, materia) de las competencias **actuales** del cargo (catálogos de ORG-03). Se guarda como instantánea
  (acción, materia); no es FK, para que ORG-03 pueda seguir retirando competencias. Si el cargo no la tiene → 422
  `GOV_ACT_INVALID_COMPETENCY`. Se revalida al emitir.
- **Fundamento de la competencia**: norma que atribuye la competencia (5–500), obligatorio.
- **Funcionario que suscribe** (art. 18.8): nombre tal como consta (3–200), obligatorio. **Titularidad**: `TITULAR`, `DELEGACION`,
  `ENCARGADURIA`, `SUPLENCIA`. Con `DELEGACION` son obligatorios el número (1–60) y la fecha (≤ fecha del acto) del acto de delegación;
  con las demás deben ir vacíos. Es transcripción del acto: KONTROL no comprueba la persona ni la delegación.
- El usuario de KONTROL que registra **no** es la autoridad: sus capacidades `gobierno_actos:*` solo permiten operar el registro.

### 4.4 Motivación y contenido (MOTIVATION_CONTRACT; motivación ≠ motivo de cambio)

- **Carácter**: `GENERAL` (interesa a un número indeterminado de personas: publicación, art. 72), `PARTICULAR` (afecta derechos o
  intereses de destinatarios determinados: notificación, art. 73) o `INTERNO` (asuntos internos de la administración, art. 72: sin
  publicación ni notificación).
- **Simple trámite** (art. 9): solo para `PARTICULAR`; si es verdadero, hechos y fundamentos legales son opcionales.
- **Hechos** (≤ 8000) y **fundamentos legales** (≤ 4000): obligatorios para emitir salvo simple trámite (arts. 9 y 18.5).
- **Asunto** (3–200), **decisión** (3–8000, art. 18.6) y **lugar** (2–120, art. 18.3): obligatorios. **Destinatario** (art. 18.4,
  3–200): obligatorio para emitir si `PARTICULAR`.
- En BORRADOR la motivación y la decisión pueden estar incompletas; **emitir** exige la lista cerrada de faltantes vacía:
  `DOCUMENTO_ACTO`, `HECHOS`, `FUNDAMENTOS`, `DECISION`, `DESTINATARIO`, `AUTORIDAD` → si no, 422 `GOV_ACT_INCOMPLETE` con
  `details.faltantes`.
- Tras emitir, la motivación solo cambia por **corrección de error material** (§4.6), con motivo de cambio aparte.

### 4.5 Temporal y eficacia (TEMPORAL_CONTRACT; OD-DOC02-04)

Fechas civiles (`Date`, America/Caracas, `hoy_de_negocio`); instantes técnicos en UTC.

| Carácter | Requisito | Se registra | Fecha de eficacia |
|---|---|---|---|
| INTERNO | ninguno | al emitir, `fecha_eficacia` opcional | por defecto la fecha del acto; si se indica, ≥ fecha del acto (puede ser futura) |
| GENERAL | publicación en Gaceta (art. 72) | `medio = GACETA`, referencia de la publicación (3–120), fecha de publicación (≥ fecha del acto, ≤ hoy), soporte | por defecto la de publicación; si se indica, ≥ esa fecha |
| PARTICULAR | notificación (arts. 73–76) | `medio = PERSONAL` (fecha de recepción del recibo, art. 75) o `PRENSA` (referencia del diario y fecha de publicación, art. 76), fecha (≥ fecha del acto, ≤ hoy), soporte (recibo firmado o ejemplar) | PERSONAL: la de notificación; PRENSA: la de publicación + 15 días (art. 76); si se indica, ≥ esa fecha |

- Nada es retroactivo: ninguna fecha de eficacia es anterior a la fecha del acto ni a su publicación o notificación.
- El soporte es un documento ya vinculado al acto, ACTIVO, de la misma empresa y distinto del documento del acto
  (422 `GOV_ACT_INVALID_DOCUMENT`).
- Se registra una sola vez (EMITIDO → EFICAZ). Canal autorizado, varios interesados y constancia gestionada: DOC-04.
- La UI muestra «Eficaz desde dd/mm/aaaa» o, si la fecha es futura, «Eficaz a partir de dd/mm/aaaa».

### 4.6 Corrección, revocación y nulidad

- **Corrección de error material (art. 84)**: en EMITIDO o EFICAZ; solo `lugar`, `asunto`, `destinatario`, `funcionario`, `hechos`,
  `fundamentos`, `decision`, `fundamento_competencia`; motivo obligatorio (5–255). Tipo, número, fecha, cargo, competencia,
  titularidad, carácter, eficacia y documentos no se corrigen (otro campo → 422 por el esquema). Sin cambios → 422 `GOV_ACT_NO_CHANGES`.
- **Revocación (art. 82)** y **nulidad (art. 83)**: se registran por referencia a **otro acto del registro** (el que revoca o declara
  la nulidad), EMITIDO o EFICAZ, del mismo ente, distinto del afectado y con fecha ≥ la del afectado (si no → 422
  `GOV_ACT_INVALID_REFERENCE`); motivo obligatorio. La fecha de la revocación o nulidad es la del acto que la dispone. Si ese acto
  está fuera del registro, primero se registra. El juicio de si procede (p. ej. que no cree derechos, art. 82) es de la autoridad.
- Sustitución o derogación por un acto posterior se registra como revocación.

### 4.7 Documentos (DOCUMENT_CONTRACT)

- Infraestructura canónica 046: `ResourceKind("GovernmentAct", …, "gobierno_actos:view")`; panel `AdjuntosPanel`; sin almacenamiento
  propio; analizador real y hash del núcleo.
- **Documento del acto** (`documento_acto_id`, FK a `documents`): obligatorio para emitir; elegido entre los vinculados al acto.
- **Soporte de eficacia** (`documento_eficacia_id`, FK a `documents`): obligatorio para GENERAL y PARTICULAR.
- Al emitir y al registrar la eficacia se congelan los vínculos (`freeze_links`): queda atada la versión usada y no se pueden
  desvincular (046 `LINK_FROZEN`). Eliminar un borrador con documentos → 409 `GOV_ACT_HAS_DOCUMENTS`.

### 4.8 Fronteras

- **Notificación (DOC-04)**: DOC-02 guarda el requisito y su cumplimiento (fecha, medio, soporte); no envía, no gestiona canales ni
  varios interesados ni constancias por canal. DOC-04 podrá producir lo que DOC-02 registra.
- **Expediente (DOC-01)**: el acto existe sin expediente; DOC-01 lo referenciará desde el expediente. Sin campo ni placeholder.
- **ORG-01/02/03**: sus documentos de acto actuales no se migran ni se reinterpretan (fuera de alcance; posible integración futura).
- **ORG-04/ORG-06/DOC-05**: no se adelantan.

## 5. Campos (FIELD_CONTRACT)

| Id | Etiqueta | Tipo / BD / API | Oblig. | Validación | Editable | Ayuda |
|---|---|---|---|---|---|---|
| A01 | Tipo de acto | enum (7) / `String(16)` | sí | catálogo §4.2 | BORRADOR | «Según la jerarquía de la LOPA» |
| A02 | Denominación | texto / `String(80)` (`''` si no aplica) | si OTRA_DECISION | 3–80; vacía en los demás | BORRADOR | «Ej.: Punto de cuenta» |
| A03 | Número | texto / `String(60)` | sí | 1–60; único §4.1 | BORRADOR | «Tal como consta en el acto» |
| A04 | Fecha del acto | fecha / `Date` | sí | ≤ hoy | BORRADOR | — |
| A05 | Lugar | texto / `String(120)` | sí | 2–120 | BORRADOR; corrección | — |
| A06 | Cargo que lo dicta | uuid / FK `gov_positions` | sí | §4.3 | BORRADOR | «Cargo vigente en la fecha del acto» |
| A07 | Competencia | (acción, materia) / 2 × `String(16)` | sí | §4.3 | BORRADOR | — |
| A08 | Fundamento de la competencia | texto / `String(500)` | sí | 5–500 | BORRADOR; corrección | «Norma que atribuye la competencia» |
| A09 | Funcionario que suscribe | texto / `String(200)` | sí | 3–200 | BORRADOR; corrección | «Tal como consta en el acto» |
| A10 | Titularidad | enum (4) / `String(16)` | sí | §4.3 | BORRADOR | — |
| A11 | Nº del acto de delegación | texto / `String(60)` | si DELEGACION | 1–60; vacío si no | BORRADOR | — |
| A12 | Fecha del acto de delegación | fecha | si DELEGACION | ≤ A04; nula si no | BORRADOR | — |
| A13 | Carácter | enum (3) / `String(16)` | sí | §4.4 | BORRADOR | «General: se publica · Particular: se notifica · Interno» |
| A14 | De simple trámite | bool | — | solo PARTICULAR | BORRADOR | «LOPA art. 9» |
| A15 | Destinatario | texto / `String(200)` nulo | para emitir si PARTICULAR | 3–200 | BORRADOR; corrección | «Persona u órgano a quien va dirigido» |
| A16 | Asunto | texto / `String(200)` | sí | 3–200 | BORRADOR; corrección | — |
| A17 | Hechos | texto / `Text` | para emitir (salvo simple trámite) | ≤ 8000 | BORRADOR; corrección | — |
| A18 | Fundamentos legales | texto / `Text` | para emitir (salvo simple trámite) | ≤ 4000 | BORRADOR; corrección | — |
| A19 | Decisión | texto / `Text` | para emitir | 3–8000 | BORRADOR; corrección | «Lo que el acto dispone» |
| E01 | Documento del acto | uuid / FK `documents` | para emitir | vinculado, ACTIVO, misma empresa | al emitir | «El PDF firmado» |
| E02 | Medio | enum `GACETA`/`PERSONAL`/`PRENSA` | al registrar eficacia | según carácter | una vez | — |
| E03 | Referencia de la publicación | texto / `String(120)` | GACETA, PRENSA | 3–120 | una vez | «Gaceta Oficial Nº… / diario» |
| E04 | Fecha de publicación o notificación | fecha | GENERAL, PARTICULAR | ≥ A04, ≤ hoy | una vez | — |
| E05 | Soporte | uuid / FK `documents` | GENERAL, PARTICULAR | ≠ E01; vinculado, ACTIVO | una vez | «Gaceta, recibo firmado o ejemplar» |
| E06 | Fecha de eficacia | fecha | derivada (opcional explícita) | §4.5 | una vez | — |
| R01 | Acto que revoca / declara la nulidad | uuid / FK `gov_acts` | al revocar o anular | §4.6 | una vez | — |
| M01 | Motivo del cambio | texto / `String(255)` | corregir, revocar, anular | 5–255 | — | «Queda en el historial y la auditoría» |
| — | Estado · Versión | enum (5) · entero | sistema | `If-Match` | no | — |

## 6. Datos

| Tabla | Alcance | Claves | Restricciones |
|---|---|---|---|
| `gov_acts` (`GovernmentAct`) | COMPANY | `company_id` → `companies`; `cargo_id` → `gov_positions.id`; `documento_acto_id`, `documento_eficacia_id` → `documents.id`; `revocado_por_id`, `anulado_por_id` → `gov_acts.id`; `numero_clave`, `denominacion_clave` | UNIQUE(`cargo_id`,`tipo`,`denominacion_clave`,`numero_clave`); CHECKs de tipo, titularidad, carácter, medio, estado, competencia (catálogos de ORG-03), denominación↔OTRA_DECISION, delegación↔DELEGACION, simple trámite solo PARTICULAR, `version ≥ 1`, EMITIDO/EFICAZ/REVOCADO/NULO ⇒ documento del acto, EFICAZ ⇒ fecha de eficacia, REVOCADO ⇔ `revocado_por_id`, NULO ⇔ `anulado_por_id`; índices (`company_id`, `fecha`), (`company_id`, `estado`) |
| `gov_act_versions` (`GovernmentActVersion`) | COMPANY | `act_id` → `gov_acts.id`, `company_id`, `version`, `estado`, `snapshot` JSON, `motivo`, `actor_id` | UNIQUE(`act_id`,`version`); solo inserción |

Migración `0066_gov_doc02_actos`, sin relleno; concede `gobierno_actos:view/edit/issue/annul` a FUNCIONAL_COMPLETO.

## 7. API (`/api/v1/gobierno/actos`; guardas: permiso → contexto de empresa → módulo `gobierno`)

| # | Método | Ruta | Capacidad | Respuesta | Errores principales | Auditoría |
|---|---|---|---|---|---|---|
| 1 | GET | `?anio=AAAA` | view | `{anio, items: [ActoResumen], total}` | 404 ente; 422 anio | — |
| 2 | POST | `` | edit | 201 `ActoOut` | 404 ente; 409 NUMBER_DUPLICATE; 422 AUTHORITY / COMPETENCY / validación | GOV_ACT_CREATED |
| 3 | GET | `/exportar?anio=AAAA` | view | `text/csv` `actos-AAAA.csv` | 404 | GOV_ACTS_EXPORTED |
| 4 | GET | `/autoridades?fecha=AAAA-MM-DD` | view | `{fecha, items: [{cargo_id, codigo, denominacion, unidad_codigo, unidad_denominacion, estado, competencias: [{accion, materia}]}]}` | 404 | — |
| 5 | GET | `/{acto_id}` | view | `ActoOut` | 404 `GOV_ACT_NOT_FOUND` | — |
| 6 | PATCH | `/{acto_id}` | edit | `ActoOut` | 428; 409 STALE / INVALID_STATE / NUMBER_DUPLICATE; 422 NO_CHANGES / AUTHORITY / COMPETENCY | GOV_ACT_UPDATED |
| 7 | DELETE | `/{acto_id}` | edit | 204 | 428; 409 STALE / INVALID_STATE / HAS_DOCUMENTS | GOV_ACT_DELETED |
| 8 | POST | `/{acto_id}/emitir` `{documento_acto_id, fecha_eficacia?}` | issue | `ActoOut` | 428; 409 STALE / INVALID_STATE; 422 INCOMPLETE (`faltantes`) / INVALID_DOCUMENT / AUTHORITY / COMPETENCY / fecha | GOV_ACT_ISSUED |
| 9 | POST | `/{acto_id}/eficacia` `{medio, referencia?, fecha, documento_eficacia_id, fecha_eficacia?}` | issue | `ActoOut` | 428; 409 STALE / INVALID_STATE; 422 INVALID_DOCUMENT / medio / fecha | GOV_ACT_EFFECTIVENESS_RECORDED |
| 10 | POST | `/{acto_id}/corregir` `{cambios…, motivo}` | issue | `ActoOut` | 428; 409 STALE / INVALID_STATE; 422 NO_CHANGES / validación | GOV_ACT_CORRECTED |
| 11 | POST | `/{acto_id}/revocar` `{acto_id_referencia, motivo}` | annul | `ActoOut` | 428; 409 STALE / INVALID_STATE; 422 INVALID_REFERENCE | GOV_ACT_REVOKED |
| 12 | POST | `/{acto_id}/anular` `{acto_id_referencia, motivo}` | annul | `ActoOut` | ídem | GOV_ACT_NULLIFIED |
| 13 | GET | `/{acto_id}/versiones` | view | `{items: [VersionActo], total}` | 404 | — |

`exportar` y `autoridades` se declaran antes de `{acto_id}`. Esquemas con `extra="forbid"`; fechas sin hora; `If-Match` obligatorio en
6–12 con la versión del acto (428 sin él); toda escritura bloquea la fila del acto (`FOR UPDATE`) y, en 11–12, también la del acto
de referencia. Recursos ajenos o inexistentes: 404. Parámetros de consulta: solo los declarados (contrato global, 422). Ningún error
de negocio es 500.

`ActoOut`: `id, tipo, denominacion_tipo, numero, fecha, lugar, cargo {id, codigo, denominacion, unidad_codigo, unidad_denominacion},
competencia {accion, materia}, fundamento_competencia, funcionario, titularidad, delegacion_numero, delegacion_fecha, caracter,
simple_tramite, destinatario, asunto, hechos, fundamentos, decision, estado, faltantes_para_emitir, documento_acto_id, medio,
referencia_publicacion, fecha_publicacion_notificacion, documento_eficacia_id, fecha_eficacia, revocado_por {id, tipo, numero,
fecha} | null, anulado_por {…} | null, revoca_a [{id, tipo, numero}], anula_a [{…}], version, emitido_en, emitido_por, creado_en`.
`ActoResumen`: id, tipo, denominacion_tipo, numero, fecha, cargo (código y denominación), unidad, caracter, asunto, estado,
fecha_eficacia.

## 8. Roles, MFA y auditoría

| Actor | view | edit | issue | annul | audit |
|---|---|---|---|---|---|
| Responsable de actos (FUNCIONAL_COMPLETO) | ✓ | ✓ | ✓ | ✓ | — |
| Registrador (view + edit) | ✓ | ✓ (borradores) | — | — | — |
| Consulta | ✓ | — | — | — | — |
| Auditor | — | — | — | — | `audit:view` |
| ADMIN técnico | sin autoridad funcional (GOV-CTL-004) | | | | |

Las pantallas usan además `documentos:*` (panel 046). DOC02_MFA_MATRIX: `view` ESTÁNDAR; `edit`, `issue`, `annul` SENSIBLES (crean o
cambian la constancia oficial de un acto, como `gobierno_cargos:edit/publish`).

Auditoría (catálogo cerrado, ámbito COMPANY, `entity_type="GovernmentAct"` salvo la exportación, que usa `GovernmentEntity`):
`GOV_ACT_CREATED`, `GOV_ACT_UPDATED`, `GOV_ACT_DELETED`, `GOV_ACT_ISSUED`, `GOV_ACT_EFFECTIVENESS_RECORDED`, `GOV_ACT_CORRECTED`
(antes/después, motivo), `GOV_ACT_REVOKED`, `GOV_ACT_NULLIFIED` (acto de referencia, motivo), `GOV_ACTS_EXPORTED`. Contexto: actor,
tenant, empresa, acto (tipo, número, fecha), cargo, versión, documento, motivo.

## 9. Menú, pantallas y estados

| Menú | Ruta | Pantalla |
|---|---|---|
| Gobierno › **Actos administrativos** | `/gobierno/actos` | Registro del año (selector de año, por defecto el actual): búsqueda por número o asunto, filtros por tipo, carácter, estado y cargo; tabla (número, tipo, fecha, cargo, asunto, carácter, estado, eficacia); «Registrar acto», «Exportar CSV» |
| (desde la tabla) | `/gobierno/actos/:actoId` | Acto: datos, autoridad, motivación, requisitos para emitir, documentos (panel 046), eficacia, relaciones (revoca a / revocado por), historial; acciones Editar, Eliminar, Emitir, Registrar publicación o notificación, Corregir error material, Registrar revocación, Registrar nulidad |

Estados de UI: módulo no habilitado; sin acceso; ente no configurado; año sin actos; filtro sin resultados; sin cargos elegibles en la
fecha; borrador con faltantes («Emitir» deshabilitado y descrito); emitido pendiente de publicación o notificación (aviso); eficaz
(«Eficaz desde» / «a partir de»); revocado o nulo (aviso con referencia, solo lectura); conflicto de versión; errores de campo, de
autoridad, de número duplicado, de documento y de referencia; error de red con reintento.

Etiquetas de negocio: tipos «Decreto, Resolución, Orden, Providencia, Instrucción, Circular, Otra decisión»; titularidad «Titular, Por
delegación, Encargado, Suplente»; carácter «General (se publica), Particular (se notifica), Interno»; medio «Gaceta Oficial,
Notificación personal, Publicación en prensa»; estados «Borrador, Emitido, Eficaz, Revocado, Nulo». Ningún código técnico como rótulo.

## 10. Escenario de éxito para la prueba de la dueña

Con el ente, su estructura del año y un cargo vigente con competencia (ORG-01/02/03), entra en Gobierno › Actos administrativos,
registra la «Resolución Nº DA-001-AAAA» dictada por el Director de Administración con la competencia Aprobar · Contrataciones y su
fundamento, firmada por el titular, de carácter particular, con destinatario, hechos, fundamentos y decisión. Intenta emitir sin PDF:
el sistema dice qué falta. Adjunta el PDF firmado y la emite: queda «Emitido, pendiente de notificación». Adjunta el recibo firmado y
registra la notificación personal: queda «Eficaz desde» esa fecha. Corrige un error material del asunto con motivo y lo ve en el
historial. Registra otra resolución que revoca la primera y lo deja constando. Exporta el CSV y ve los pasos en la auditoría. Un usuario
de solo consulta ve el registro pero no puede registrar ni emitir.
