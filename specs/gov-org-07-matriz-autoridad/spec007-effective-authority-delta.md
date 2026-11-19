# Delta ORG-07 · Matriz de autoridad efectiva (ORG-07-EFFECTIVE-AUTHORITY-MATRIX)

**Spec dueña:** `specs/gov-org-07-matriz-autoridad/spec.md`. **Encargo:** «P2 — ORG-07 · Matriz de autoridad efectiva con ORG-04» (2026-11-19). **Prioridad:** P1, ciclo dirigido, sin rediseño.

## 1. Defecto vigente

- `service_autoridad._filas_filtradas` solo proyecta la autoridad del cargo (ORG-03): toda fila es `"origen": "CARGO"` y la matriz no dice **quién** la ejerce.
- No incorpora las delegaciones, suplencias, encargadurías ni comisiones de servicio de ORG-04.
- La pantalla (`MatrizAutoridadPage.tsx`) avisa que «llegarán con ORG-04».
- Reproducción: con una delegación vigente de APROBAR/PRESUPUESTO, la matriz a una fecha dentro de su vigencia no muestra al delegado (`test_org07_ea01_defecto_delegacion_visible`, que falla contra 65651eff).

## 2. Arqueología (§5)

| Elemento | Estado de entrada |
|---|---|
| CURRENT_MATRIX_SOURCES | Solo ORG-03: versiones del cargo (`_version_en_vigor`) y documentos vinculados al cargo |
| CURRENT_MATRIX_COLUMNS | Unidad, cargo, acción, materia, límite (tipo, monto, moneda), fundamento, vigencia del cargo, estado, acto de soporte, versión, `origen` (`Literal["CARGO"]`) |
| CURRENT_DATE_LOGIC | `_fecha_corte(ejercicio, fecha)`: la fecha pedida, dentro del ejercicio. La versión del cargo es la registrada antes del fin del día |
| CURRENT_FILTERS | Unidad (con subunidades), cargo, acción, materia y texto libre |
| CURRENT_EXPORT_LOGIC | `exportar_matriz_csv` reutiliza `_filas_filtradas` (mismo universo) y audita GOV_AUTHORITY_MATRIX_EXPORTED |
| CURRENT_ORG04_CONSUMPTION | Ninguno. ORG-04 consume ORG-07 (`competencias_en_vigor`), no al revés |
| Resolución canónica de ORG-04 | `service_ocupacion._vigentes_en(cargos, fecha)`: por cargo, el titular, quién **ejerce** (la temporal vigente más reciente; si no hay, el titular) y las delegaciones vigentes. La situación (`situacion_en`) aplica revocación, finalización, vencimiento, acto nulo o revocado y fin del cargo |

### Figuras de ORG-04 (§11)

| Figura | Grupo | ¿Cambia quién puede hacer qué? | En la matriz |
|---|---|---|---|
| TITULAR | TITULARIDAD | Ocupa el cargo: ejerce su autoridad | Actor de las filas del cargo, `origen` CARGO |
| ENCARGADURIA | TEMPORAL | Ejerce el cargo en lugar del titular | Actor de las filas del cargo, `origen` ENCARGADURIA |
| SUPLENCIA | TEMPORAL | Suple al titular ausente | Actor de las filas del cargo, `origen` SUPLENCIA, con el titular sustituido |
| COMISION_SERVICIO | TEMPORAL | Ejerce temporalmente otro cargo | Actor de las filas del cargo, `origen` COMISION_SERVICIO |
| DELEGACION_ATRIBUCIONES | DELEGACION | Transfiere el ejercicio de las competencias delegadas | Filas propias, solo de lo delegado |
| DELEGACION_FIRMA | DELEGACION | Transfiere la firma (FIRMAR) | Filas propias, solo de lo delegado |

Ninguna figura es meramente informativa: las seis se proyectan.

## 3. Decisión de la dueña (2026-11-19)

| Id | Decisión |
|---|---|
| OD-EA-01 | **Mínimo privilegio.** Las personas solo se ven con `gobierno_ocupacion:view`, además de `gobierno_autoridad:view`. Sin él, las filas derivadas aparecen igual, con su fuente, vigencia, acto y límites, pero la persona figura como «Reservado» en pantalla y en el CSV, y el texto libre no busca por nombre |

## 4. Decisiones de diseño de Claude

| Id | Decisión |
|---|---|
| D-EA-01 | **ORG-04 resuelve; ORG-07 proyecta.** `service_ocupacion.autoridad_efectiva_en(cargos, fecha)` es la API pública de ORG-04 sobre `_vigentes_en`. ORG-07 no decide vigencias, precedencia, revocaciones ni competencias delegadas. AUTHORITY_ENGINES_CREATED=0 |
| D-EA-02 | **Identidad de fila.** Las filas del cargo conservan `{cargo}:{accion}:{materia}` y llevan a quien ejerce el cargo; hay una sola fila porque ORG-04 da un único `ejerce`. Las filas de delegación son `{asignacion}:{accion}:{materia}`. Cargo y delegación son materialmente distintos: el delegante conserva la titularidad y puede avocar |
| D-EA-03 | **`origen`** usa el vocabulario de ORG-04 (`FIGURAS`): CARGO cuando ejerce el titular o el cargo está vacante; la figura cuando ejerce una temporal o hay delegación. Pasa de `Literal["CARGO"]` a texto. Compatible: CARGO sigue siendo el valor de las filas base |
| D-EA-04 | **Fuente trazable.** Bloque `fuente`: figura, asignación (id y código), vigencia (`desde`, `hasta` y `fin_efectivo`), funcionario, titular sustituido, cargo de origen, acto y avocaciones registradas a la fecha. Es nulo si el cargo está vacante |
| D-EA-05 | **Límites.** La fila del cargo usa el límite de la versión del cargo. La de delegación usa el límite que guardó la asignación de ORG-04; no se recalcula |
| D-EA-06 | **Alcance.** La delegación se proyecta en la unidad del cargo delegante, que es donde la competencia surte efecto; el cargo del delegado va en `fuente.cargo_origen`. Los filtros de unidad, cargo, acción, materia y texto se aplican por igual a todas las filas |
| D-EA-07 | **Avocación.** En ORG-04 (LOAP art. 41) la avocación es por asunto y no extingue la delegación, que sigue vigente. La matriz la muestra como número de avocaciones registradas, sin retirar la fila |
| D-EA-08 | **Sin migración ni persistencia.** La matriz es una proyección; ORG-04 ya guarda la fuente. MIGRATION_REQUIRED=0 |
| D-EA-09 | **CSV.** Mismo universo que la pantalla (`_filas_filtradas`). Columnas nuevas al final, para no romper a quien lee las existentes |
| D-EA-11 | **Defecto de ORG-04 destapado por la E2E.** En la app real (`autoflush=False`), activar una delegación daba 500: el INSERT de las competencias salía después del UPDATE a ACTIVO y lo rechazaba el disparador de inmutabilidad. Bloqueaba la autoridad delegada en el producto, así que se corrige en este ciclo (regresión directa del alcance): `_reemplazar_competencias` hace `flush` en BORRADOR. Prueba `test_org07_ea17_*` |
| D-EA-10 | **ORG-06.** No se necesita: el actor de la autoridad es el funcionario de ORG-04. La cuenta de usuario vinculada no cambia quién puede ejercer |

## 5. Requisitos

| Id | Requisito |
|---|---|
| FR-EA-01 | Las filas del cargo muestran a quien lo ejerce a la fecha de corte (titular o figura temporal), con su fuente |
| FR-EA-02 | Cada delegación vigente a la fecha añade filas de las competencias efectivamente delegadas, con sus límites |
| FR-EA-03 | Revocadas, finalizadas, vencidas, futuras o con acto sin efecto no aparecen después de su fin; sí en fechas en que estuvieron vigentes |
| FR-EA-04 | `origen` y `fuente` trazables (D-EA-03 y D-EA-04) |
| FR-EA-05 | Los filtros y el texto libre se aplican a todas las filas; el texto busca la persona solo si es visible |
| FR-EA-06 | OD-EA-01: la persona se reserva sin `gobierno_ocupacion:view`, en la pantalla y en el CSV |
| FR-EA-07 | El CSV tiene las mismas filas que la pantalla, más origen, persona, asignación, vigencia y acto |
| FR-EA-08 | Frontend: se quita el aviso «llegarán»; aparecen la columna «Ejerce» con su fuente y la sección «Fuente de autoridad» en el detalle |
| FR-EA-09 | Pruebas: PG, mutaciones M1–M8, Vitest y E2E (efectiva, histórica y CSV) con Axe en 1280, 390 y 320 |

## 6. Gate

BLOCKER=0 · CRITICAL=0 · CONTRADICTIONS=0 · OWNER CONFLICT=0 · MATERIAL OQ=0 (OD-EA-01 resuelta) · UNKNOWN=0 · trazabilidad 9/9.
