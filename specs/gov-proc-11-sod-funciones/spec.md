# PROC-11 · Funciones incompatibles en contratación (GOV-PROC-017)

**Autorización:** mandato de la dueña «KONTROL — PROGRAMMER 1 · KONTROL GOVERNMENT · POST REP-10 · SIGUIENTE VERTICAL
FUNCIONAL», 2026-11-12. **Fuentes:** `FUENTES.md`. **Decisiones de diseño:** `DECISIONES.md` (PDD-PROC11-01 a 12).

## Qué podrá hacer el usuario que antes no podía

Control Interno, en Gobierno › Contrataciones › «Funciones incompatibles»:

1. Declara la **matriz institucional** de funciones incompatibles del procedimiento de contratación: qué dos funciones
   del expediente no puede ejercer la misma persona (por ejemplo, «quien recibe las ofertas no las evalúa»).
2. La pone en vigor con firma reforzada (MFA) desde una fecha y la cierra cuando deja de aplicar, sin borrar historia.
3. Ve, para un período o para un expediente, **qué expedientes tienen un conflicto real**: la misma persona ejerció dos
   funciones que la matriz declara incompatibles, con la evidencia de cada función (fecha, cargo y registro que la prueba).
4. Exporta ese listado en CSV, auditado.

Y la Unidad Contratante deja de poder producir el conflicto: con la matriz en vigor, el sistema **impide** que una
persona asuma una función incompatible con otra que ya ejerce en el mismo expediente, explicando qué regla aplica, qué
función ejerció antes y con qué registro. El intento queda auditado como rechazo.

## Alcance declarado de las funciones

La cadena del requisito es «solicitante / evaluador / adjudicador / receptor / pagador». En Gobierno existen hoy cuatro
de esas funciones y una no:

| Función | Dónde vive en el producto |
|---|---|
| `SOLICITANTE` | quien registra el expediente y el `REQUIRENTE` designado en el expediente (PROC-03) |
| `RECEPTOR` | quien recibe cada oferta (PROC-06: funcionario receptor y usuario que la registra) |
| `EVALUADOR` | miembros de la comisión vinculada, asistentes a la apertura, aportes de evaluación y firmantes de la recomendación (PROC-02/PROC-07/PROC-08) |
| `ADJUDICADOR` | quien decide el resultado del procedimiento (PROC-08) |
| `PAGADOR` | **no existe en Gobierno**: el pago es de GOV-TRE-004 (TRE-04), fuera de este ciclo |

`PAGADOR` no se simula ni se declara disponible: el catálogo lo publica como no disponible con su requisito habilitante y
la matriz no puede referenciarlo. El motor es de datos, de modo que cuando TRE-04 exista se incorpora sin rediseño.
Esta limitación se declara en la tarjeta de UAT y en las matrices como observación abierta, no como compuerta cumplida.

## Historias

- **US1 (P0) Declarar la matriz.** Como Control Interno declaro pares de funciones incompatibles del procedimiento, los
  pongo en vigor con MFA y los cierro sin borrar historia.
- **US2 (P0) Impedir el conflicto.** Como backend impido que una persona asuma una función incompatible con otra que ya
  ejerce en el mismo expediente, con explicación y evento de rechazo.
- **US3 (P0) Ver los conflictos reales.** Como Control Interno veo, por período y por expediente, los conflictos que ya
  existen (anteriores a la regla, o producidos por vías no cubiertas), con evidencia de ambas funciones.

## Requisitos

- **FR-001 Catálogo de funciones.** Cerrado y en código: `SOLICITANTE`, `RECEPTOR`, `EVALUADOR`, `ADJUDICADOR` con
  etiqueta y fuente de ocupación declarada; `PAGADOR` publicado como no disponible con su requisito habilitante.
- **FR-002 Matriz versionada.** Regla de funciones: proceso (`PROC-03`), función A, función B distintas, nombre,
  descripción del riesgo, fundamento y vigencia desde/hasta. Estados `BORRADOR`, `VIGENTE`, `CERRADA`. Código `RF-0001`.
  Una regla vigente no se edita: se cierra y se crea otra.
- **FR-003 Activación con MFA.** `gobierno_sod:activate` (capacidad ya existente de CTL-01, sensible con MFA). Sin
  solapamiento de la misma pareja en vigor; la fecha de vigencia es de negocio.
- **FR-004 Ocupación calculada.** Para un expediente, la ocupación de cada función se deriva de sus registros reales
  (expediente, responsables, ofertas, comisión, apertura, aportes, recomendación, decisión), con equivalencia de actor
  (ORG-06: usuarios del mismo funcionario y delegaciones cuentan como la misma persona).
- **FR-005 Detección.** Un conflicto es una función A y una función B de una regla en vigor a la fecha de referencia,
  ejercidas por la misma persona en el mismo expediente. Devuelve la persona, la regla, ambas funciones y la evidencia
  (registro, fecha, etiqueta del cargo).
- **FR-006 Bloqueo preventivo.** Antes de que una persona asuma una función, el servicio comprueba los pares en vigor y
  responde 409 `GOV_SOD_ROLE_CONFLICT` con la explicación, sin mutar nada, dejando evento `GOV_SOD_ROLE_CONFLICT_BLOCKED`
  (REJECTION) con la regla, la función previa y el registro previo.
- **FR-007 Consulta por período.** Listado institucional por fecha de negocio (`desde`, `hasta`), con filtro opcional de
  función y expediente; `desde > hasta` → 422 `INVALID_DATE_RANGE`; default: 1 de enero del año de negocio → hoy.
- **FR-008 Consulta por expediente.** La ficha del expediente muestra sus conflictos y la matriz aplicable.
- **FR-009 Exportación.** CSV del listado con el período y los filtros; auditado `GOV_SOD_ROLE_CONFLICTS_EXPORTED`.
- **FR-010 Permisos y aislamiento.** `gobierno_sod:view` para consultar, `gobierno_sod:manage` para borradores,
  `gobierno_sod:activate` para activar o cerrar. Otro ente: 404. Módulo apagado: 403. El frontend nunca decide.
- **FR-011 Concurrencia.** Alta de regla, activación y cierre con `If-Match` de la versión; activar y cerrar se excluyen.
- **FR-012 Auditoría y cronología.** 4 eventos CTL-02; la detección no muta nada (solo lectura).
- **FR-013 Interfaz.** Pantalla «Funciones incompatibles» con matriz, formulario de regla, listado de conflictos por
  período, exportación, y bloque de explicación legible en la ficha del expediente. Sin UUID visibles; 1280, 390 y 320 px;
  Axe sin violaciones serias ni críticas.

## Fuera de alcance

La función `PAGADOR` (TRE-04), las funciones de almacén (WH-01), el rol de contratista (PROC-05), la declaración de
inhibición de un miembro de comisión (PROC-02), el bloqueo por acción de CTL-01 (ya existe y no se duplica) y cualquier
pago, contrato o monto.

## Criterios de aceptación

- **SC-001** Control Interno crea la regla `RECEPTOR ≠ EVALUADOR`, la activa con MFA y ve la regla en vigor (E2E).
- **SC-002** Con la regla en vigor, la persona que recibió una oferta no puede registrar un aporte de evaluación del mismo
  expediente: 409 con explicación, sin mutación, con evento de rechazo (E2E, E2E-07).
- **SC-003** Un conflicto anterior a la regla aparece en el listado del período con la evidencia de ambas funciones (E2E).
- **SC-004** Otro ente no ve las reglas ni los conflictos; sin capacidad, 403 (PostgreSQL).
- **SC-005** La exportación CSV descarga el listado y deja su evento con filas y filtros (PostgreSQL).
- **SC-006** La pantalla y la ficha del expediente funcionan a 1280, 390 y 320 px, por teclado, sin violaciones serias de
  Axe y con el contenido terminado de pintar antes de medir.
