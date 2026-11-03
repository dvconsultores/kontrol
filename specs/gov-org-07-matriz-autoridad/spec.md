# Spec · GOV-ORG-07 Matriz auditable de autoridad «quién puede qué» (ORG-07, GOV-ORG-010)

## 1. Lo que podrá hacer el usuario (vista del sponsor)

Cuando este ciclo termine, el usuario podrá abrir **Gobierno › Matriz de autoridad**, elegir el ejercicio y la fecha, y ver
qué **cargos** del ente pueden solicitar, comprometer, causar, ordenar el pago, pagar, registrar, custodiar, aprobar, auditar o
firmar; sobre qué materia; en qué unidad (con su ruta en la estructura); hasta qué monto por operación; con qué vigencia y con
qué acto soporte. Podrá:
- filtrar por unidad (con sus subunidades), cargo, acción y materia, y buscar por texto;
- abrir el detalle de un cargo con su acto soporte y su historial de versiones;
- exportar a CSV lo que está viendo.

Con la fecha puede responder «¿quién podía aprobar compras el 15 de marzo?»: la matriz se reconstruye desde las versiones
registradas de cada cargo.

## 2. Fuentes y decisiones

| Tipo | Id | Contenido |
|---|---|---|
| Requisito | GOV-ORG-010 (P0; N03, N18, N20, N23) | «Producir matriz auditable de quien puede solicitar, comprometer, causar, ordenar, pagar, registrar, custodiar, aprobar y auditar» (IR §7.1) |
| Requisito relacionado | GOV-ORG-003 | Autoridad «por cargo y no solo por usuario nominal» (ORG-03, OWNER_UAT_READY) |
| Modelo lógico | IR §9 | `AuthorityGrant` = cargo VIGENTE con sus competencias (ORG-03 §5 AUTHORITY_MODEL) |
| Actor | IR §5 | Control Interno/Auditoría: acceso read-only; Administrador técnico sin autoridad funcional |
| OWNER | OD-ORG07-01 | «Quién» = **cargo institucional**; sin columna de persona hasta ORG-06 (bloqueado) |
| OWNER | OD-ORG07-02 | **Corte a una fecha**: por defecto, la autoridad de hoy; con otra fecha, reconstruida desde las versiones del cargo |
| OWNER | OD-ORG07-03 | **Capacidad propia** `gobierno_autoridad:view`; la exportación queda auditada; la migración solo la concede a FUNCIONAL_COMPLETO |
| OWNER | OD-ORG07-04 | Las **10 acciones** de ORG-03 (las 9 de GOV-ORG-010 + Firmar); «ordenar» = `ORDENAR_PAGO` |

**Prueba de bloqueo material: 0.**
- SECURITY 0: se reutilizan la empresa del contexto, el módulo y una capacidad de lectura.
- DATA_INTEGRITY 0: es una proyección de lectura sin almacenamiento propio.
- LEGAL / NORMATIVE 0: GOV-ORG-010 pide la matriz de autoridad institucional; ORG-03 ya la registra.
- ARCHITECTURAL 0.
- TESTABILITY 0.
- DOMAIN_DEPENDENCY 0:
  - ORG-06 no hace falta (OD-ORG07-01: «quién» es el cargo);
  - ORG-04 no hace falta: la autoridad propia del cargo se representa entera; las delegaciones se declaran «no disponibles hasta ORG-04» sin dejar la matriz incompleta;
  - la aplicación en transacciones (BUD/TRE) y la SoD (CTL-01) son otros procesos: GOV-ORG-010 pide la matriz, no su ejecución.

## 3. Modelo del proceso

| Elemento | Valor |
|---|---|
| PROCESS_ID / NAME | ORG-07 · Matriz auditable de quién puede qué |
| Propósito | Mostrar y exportar, por ejercicio y fecha, la autoridad institucional registrada en ORG-03 |
| Dueño de negocio | Máxima autoridad; usuario principal: Control Interno / auditor |
| Actor | Quien tenga `gobierno_autoridad:view` (lectura); no escribe nada |
| Disparador | Una revisión de control, una auditoría, o la duda «¿quién puede firmar esto?» |
| Precondiciones | Sesión; licencia con `gobierno`; empresa activa; estructura del ejercicio (ORG-02) |
| Pasos | menú → ejercicio → fecha → filtros → detalle del cargo → exportar |
| Salidas | Tabla filtrada, detalle del cargo con su historial, CSV |
| Auditoría | Exportación: `GOV_AUTHORITY_MATRIX_EXPORTED`; los cambios de autoridad ya los audita ORG-03 |
| Estados | No aplica: la matriz no tiene estado propio |

## 4. Contratos

### 4.1 Fuente única (SOURCE_OF_TRUTH)
- La autoridad propia del cargo es la de ORG-03: `gov_positions`, `gov_position_competencies` y `gov_position_versions`.
- ORG-07 **no** crea tablas de matriz ni copia datos. Es una consulta determinista.

### 4.2 Regla de corte a la fecha D (OD-ORG07-02)
Un cargo de la estructura del ejercicio entra en la matriz a la fecha D si:
1. su estado **actual** es VIGENTE o INACTIVO;
2. y `vigente_desde ≤ D ≤ (vigente_hasta o 31/12 del ejercicio)`.

Es la misma ventana que usa DOC-02 para validar la autoridad de un acto.

Sus competencias y límites a la fecha D salen de la **versión en vigor en D**:
- la última versión del cargo con estado VIGENTE o INACTIVO registrada antes de que termine el día D (hora de Caracas);
- si ninguna se registró hasta ese día (puesta en vigor registrada después, con vigencia retroactiva), la primera versión VIGENTE.

La denominación del cargo y la unidad de la fila salen de esa misma versión. El nombre y la ruta de la unidad salen del registro actual de la unidad.
- **D por defecto:** hoy si el ejercicio es el año en curso; el 31/12 si es anterior; el 01/01 si es posterior.
- D debe caer dentro del ejercicio (422 `GOV_AUTHORITY_DATE_OUT_OF_EXERCISE` en el campo `fecha`).
- Los cargos en BORRADOR nunca entran: no tienen autoridad.
- Una estructura CERRADA se sigue consultando.

### 4.3 Acciones (OD-ORG07-04)
Catálogo y orden de ORG-03:

| Código | Etiqueta |
|---|---|
| `SOLICITAR` | Solicitar |
| `COMPROMETER` | Comprometer |
| `CAUSAR` | Causar |
| `ORDENAR_PAGO` | Ordenar el pago |
| `PAGAR` | Pagar |
| `REGISTRAR` | Registrar |
| `CUSTODIAR` | Custodiar |
| `APROBAR` | Aprobar |
| `AUDITAR` | Auditar |
| `FIRMAR` | Firmar |

Ni nuevas ni renombradas.

### 4.4 Materias
Catálogo y orden de ORG-03:

| Código | Etiqueta |
|---|---|
| `PRESUPUESTO` | Presupuesto |
| `CONTRATACIONES` | Contrataciones |
| `TESORERIA` | Tesorería |
| `CONTABILIDAD` | Contabilidad |
| `BIENES` | Bienes públicos |
| `EXPEDIENTE` | Expediente y documentos |

Cada fila es **una acción sobre una materia** de un cargo.

### 4.5 Límite
- `SIN_LIMITE` → «Sin límite».
- `MONTO` → «Hasta 1.500.000,00 VES por operación».

Sin conversión de moneda. ORG-07 informa la autoridad, no la ejecuta.

### 4.6 Origen de la autoridad
Toda fila es **«Propia del cargo»** (`origen = CARGO`). La pantalla avisa:
- las delegaciones, suplencias y encargadurías llegarán con ORG-04;
- las personas que ocupan cada cargo, con ORG-06.

Ninguna fila inventa una persona.

### 4.7 Acto soporte e historia
- **Acto soporte:** los documentos ACTIVE vinculados al cargo (el acto con el que se puso en vigor), por título.
- **Historia:** las versiones del cargo (número, estado, registrada el, motivo, competencias). La fila indica la versión usada para la fecha.
- Se reutilizan las tablas de ORG-03; no hay historia duplicada.

## 5. Campos (FIELD_CONTRACT)

| Id | Etiqueta | Significado | Fuente | API | Formato UI | Filtra | Ordena | CSV |
|---|---|---|---|---|---|---|---|---|
| M01 | Cargo | Cargo que porta la autoridad | versión en D: `codigo`, `denominacion`; `cargo_id` | str | «DIR-ADM · Director de Administración» | sí (`cargo_id`) | 2.º | `codigo_cargo`, `denominacion_cargo` |
| M02 | Unidad | Unidad del cargo y su ruta | versión en D: `unidad_id`; unidad actual: código, denominación, ruta por `parent_id` | str | denominación + ruta «DESP › DIR-ADM» | sí (`unidad_id`, con subunidades) | 1.º (ruta) | `codigo_unidad`, `unidad`, `ruta_unidad` |
| M03 | Acción | Qué puede hacer | competencia en D | enum (10) | etiqueta §4.3 | sí | 3.º (orden del catálogo) | `accion` |
| M04 | Materia | Sobre qué | competencia en D | enum (6) | etiqueta §4.4 | sí | 4.º | `materia` |
| M05 | Límite | Hasta cuánto por operación | competencia en D: `tipo_limite`, `monto` (texto, 2 decimales), `moneda` | str | §4.5 | no | no | `tipo_limite`, `monto`, `moneda` |
| M06 | Fundamento | Artículo o norma de la competencia | competencia en D | str \| null | texto o «—» | por texto | no | `fundamento` |
| M07 | Vigencia | Ventana del cargo | cargo actual: `vigente_desde`, `vigente_hasta` | date | «Desde dd/mm/aaaa» o «dd/mm/aaaa – dd/mm/aaaa» | no | no | `vigente_desde`, `vigente_hasta` |
| M08 | Estado del cargo | Vigente / Inactivo hoy | cargo actual | enum | insignia con texto | no | no | `estado_cargo` |
| M09 | Acto soporte | Documentos activos vinculados | `DocumentLink` → `Document.title` | list | títulos o «Sin documento» | no | no | `acto_soporte` (títulos con « · ») |
| M10 | Versión de origen | Versión usada para D | versión: `version`, `creado_en`, `motivo` | obj | en el detalle | no | no | `version_cargo` |
| M11 | Origen | Propia del cargo | constante `CARGO` | enum | aviso de §4.6 | no | no | `origen` |
| F01 | Ejercicio | Año de la estructura | ruta | int | selector | — | — | nombre del fichero |
| F02 | A la fecha | Corte D | query `fecha` | date | campo de fecha (por defecto §4.2) | — | — | `fecha_corte` y nombre del fichero |
| F03 | Buscar | Texto libre | query `texto` (1–100, recortado) | str | caja de búsqueda | sobre M01, M02, M06 sin distinguir mayúsculas | — | — |

`MISSING_REQUIRED_FIELDS = 0`. Fila: `id = "<cargo_id>:<accion>:<materia>"`.

## 6. Datos
- Sin tablas nuevas.
- Migración `0068_gov_org07_autoridad`: solo añade el permiso `gobierno_autoridad:view` y lo concede a FUNCIONAL_COMPLETO en las instalaciones existentes; el downgrade lo retira.
- La integridad sigue en las tablas de ORG-03.

## 7. API (`/api/v1/gobierno/autoridad`; guardas: permiso `gobierno_autoridad:view` → empresa → módulo `gobierno`)

| Operación | Ruta | Respuesta | Errores |
|---|---|---|---|
| Ejercicios | `GET /ejercicios` | `{items: [{ejercicio, estado}]}` (estructuras de la empresa, ejercicio descendente) | 401/403 |
| Filtros | `GET /{ejercicio}/filtros` | `{unidades: [{id, codigo, denominacion, ruta}], cargos: [{id, codigo, denominacion}]}`: unidades de la estructura; cargos VIGENTES o INACTIVOS | 404 `GOV_STRUCTURE_NOT_FOUND` |
| Matriz | `GET /{ejercicio}?fecha&unidad_id&cargo_id&accion&materia&texto&pagina&por_pagina` | `MatrizAutoridad {ejercicio, fecha, estructura: {estado}, items: [FilaAutoridad], total, cargos, pagina, por_pagina}` | 404 estructura; 422 `GOV_AUTHORITY_DATE_OUT_OF_EXERCISE` (`fecha`); 422 `GOV_AUTHORITY_INVALID_FILTER` (`unidad_id` / `cargo_id` ajenos a la estructura); 422 acción, materia o paginación inválidas |
| Exportar | `GET /{ejercicio}/exportar?` (mismos filtros, sin paginación) | CSV `autoridad-<ejercicio>-<fecha>.csv` con las columnas de §5 más `fecha_corte` | ídem; audita `GOV_AUTHORITY_MATRIX_EXPORTED` {ejercicio, fecha, filtros, filas} |
| Detalle del cargo | `GET /{ejercicio}/cargos/{cargo_id}` | `{cargo: {id, codigo, denominacion, unidad_codigo, unidad_denominacion, ruta_unidad, estado, vigente_desde, vigente_hasta}, acto_soporte: [{documento_id, titulo}], versiones: [{version, estado, motivo, creado_en, competencias}]}` | 404 `GOV_POSITION_NOT_FOUND` (de otra estructura o empresa, o en BORRADOR) |

- `FilaAutoridad`: `{id, cargo_id, cargo_codigo, cargo_denominacion, unidad_id, unidad_codigo, unidad_denominacion, ruta_unidad, accion, materia, tipo_limite, monto, moneda, fundamento, vigente_desde, vigente_hasta, estado_cargo, acto_soporte: [titulos], version: {version, registrada_en, motivo}, origen}`.
- Paginación: `pagina` ≥ 1 (por defecto 1) y `por_pagina` 10–200 (por defecto 50).
- Orden fijo: ruta de la unidad, código del cargo, acción y materia en el orden del catálogo.
- `total` cuenta filas; `cargos` cuenta cargos distintos del resultado filtrado.
- Sin escrituras.

## 8. Roles, MFA y auditoría
- `gobierno_autoridad:view` es STANDARD: lectura, sin MFA.
- La migración y la semilla la conceden a FUNCIONAL_COMPLETO. ADMIN no la recibe por ser ADMIN: el administrador técnico no recibe autoridad funcional (IR §5).
- Se puede dar a un rol de Control Interno sin `gobierno_cargos`.
- Auditoría: `GOV_AUTHORITY_MATRIX_EXPORTED` (entity `GovernmentStructure`). Consultar no se audita, como en las demás lecturas.

## 9. Menú, pantallas y estados
- Menú: **Gobierno › Matriz de autoridad** (`/gobierno/autoridad`, icono propio), visible con `gobierno_autoridad:view` y el módulo `gobierno`.
- Pantalla única `MatrizAutoridadPage`:
  - encabezado y aviso de §4.6;
  - filtros: Ejercicio, A la fecha, Unidad, Cargo, Acción, Materia, Buscar; «Limpiar filtros»; «Exportar CSV»;
  - resumen «N autorizaciones de M cargos al dd/mm/aaaa»;
  - tabla dentro de un contenedor con desplazamiento horizontal propio;
  - paginación;
  - panel de detalle en la página (sin modal): datos del cargo, acto soporte, historial con la versión usada marcada «Usada para esta fecha», y enlace «Abrir el cargo» solo con `gobierno_cargos:view`.
- Estados: cargando; módulo no habilitado; sin acceso; sin estructuras; sin autoridad a la fecha; filtro sin resultados; fecha fuera del ejercicio (error de campo); error de red con reintento.
- Accesible a 1280, 768 y 320 px: sin desbordamiento de página; filtros con teclado; el estado se dice con texto, no solo con color.

## 10. Escenario de éxito para la prueba de la dueña
1. Con la estructura del ejercicio VIGENTE y dos cargos VIGENTES (p. ej. «DIR-ADM» con Aprobar/Contrataciones hasta 1.500.000,00 VES y Firmar/Expediente sin límite, y «JEF-TES» con Pagar/Tesorería hasta 500.000,00 VES), abre Gobierno › Matriz de autoridad.
2. Ve las 3 filas con unidad, límite, vigencia y acto.
3. Filtra por Acción = Pagar: solo JEF-TES. Filtra por la unidad padre: aparecen los cargos de sus subunidades.
4. Abre el detalle de DIR-ADM: su acto y su historial.
5. Exporta el CSV: trae solo lo filtrado y queda en la auditoría.
6. Cambia «A la fecha» a un día anterior a la vigencia de un cargo: ese cargo desaparece.
7. Un usuario sin `gobierno_autoridad:view` no ve el menú. Desde otro ente, el detalle responde «no encontrado».
