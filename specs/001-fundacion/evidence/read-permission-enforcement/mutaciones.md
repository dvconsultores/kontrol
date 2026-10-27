# READ-PERMISSION ENFORCEMENT · Mutaciones (2026-10-27)

Herramientas de Claude fuera del árbol (`scratchpad/tools/mutaciones_lectura.py`, `mutaciones_lectura_ui.py`, y las de regresión `mutaciones_alcance.py`, `mutaciones_delegacion.py` y `mutaciones_ui.py`).

Funcionamiento común:
- Cada mutante es un reemplazo exacto con una sola coincidencia.
- Se ejecutan las pruebas indicadas; el backend corre en PostgreSQL de QA, con `PYTHONDONTWRITEBYTECODE=1` y sin `__pycache__`.
- El fichero se restaura y se comprueba la huella SHA-256 (backend) o la igualdad byte a byte (frontend).
- Ningún mutante llegó a Git, y no quedó ningún `.mutbak`.

Contabilidad según la regla permanente (§6 del encargo):

| Campaña | TOTAL | KILLED | EQUIVALENT | BEHAVIORALLY_SURVIVING | INVALID |
|---|---|---|---|---|---|
| Ciclo · backend (B01..B20) | 20 | 20 | 0 | **0** | 0 |
| Ciclo · frontend (F01..F07) | 7 | 6 | 1 (F04) | **0** | 0 |
| Regresión 02B · autorización por empresa (S01..S21 y variantes) | 23 | 23 | 0 | **0** | 0 |
| Regresión 02B · techo de delegación (D01..D21) | 21 | 21 | 0 | **0** | 0 |
| Regresión 02C · frontend (R/P/G/A/S/C) | 20 | 19 | 1 (P1, ya demostrado en 02C) | **0** | 0 |
| **Total** | **91** | **89** | **2** | **0** | **0** |

## 1. Backend del ciclo

| Mutante | Qué rompe | 1.ª corrida | Final | Prueba que lo mata |
|---|---|---|---|---|
| B01 | Solo autenticado: `require_permission` no exige la capacidad | MUERTO | MUERTO | RPE-01 (espera `PERMISSION_DENIED`) |
| B02 | Solo empresa: el contexto no exige la capacidad en la empresa | MUERTO | MUERTO | RPE-05 (capacidad solo en D2 → D1) |
| B03 | Lista de terceros sin capacidad | MUERTO | MUERTO | RPE-01 |
| B04 | Detalle de tercero sin capacidad | MUERTO | MUERTO | RPE-02 |
| B05 | Búsqueda de ítems sin capacidad | MUERTO | MUERTO | RPE-03 |
| B06 | Agregado (aging de compras) sin capacidad | MUERTO | MUERTO | RPE-04 |
| B07 | Reporte sin capacidad de origen | MUERTO | MUERTO | RPE-10 |
| B08 | Vista previa sin `reportes:view` | MUERTO | MUERTO | RPE-10 |
| B09 | Descarga sin capacidad de origen | MUERTO | MUERTO | RPE-11 |
| B10 | Descarga sin `reportes:export` | MUERTO | MUERTO | RPE-11 |
| B11 | Exportación sin capacidad de origen | MUERTO | MUERTO | RPE-11 |
| B12 | Crear trabajo de reporte sin capacidad de origen | **SOBREVIVE** | MUERTO | **nueva** RPE-16 (T-M1) |
| B13 | Ejecutar trabajo de reporte sin capacidad de origen | **SOBREVIVE** | MUERTO | **nueva** RPE-16 (T-M1) |
| B14 | Tablero sin filtro por indicador (ADMIN lee negocio) | MUERTO | MUERTO | RPE-08 / RPE-09 |
| B15 | Línea de auditoría de reportes sin `audit:view` | MUERTO | MUERTO | RPE-12 |
| B16 | Catálogo global (fuentes legales) sin capacidad | MUERTO | MUERTO | RPE-13 |
| B17 | FUNCIONAL_COMPLETO como todas las empresas | MUERTO | MUERTO | RPE-05 / RPE-14 |
| B18 | `require_capability` sin el paso 1 | MUERTO | MUERTO | RCA-01 |
| B19 | `require_capability` sin el paso 2 | MUERTO | MUERTO | RCA-02 |
| B20 | Ruta nueva sin capacidad ni clasificación | MUERTO | MUERTO | puerta `test_toda_lectura_declara_capacidad_o_esta_clasificada` |

## 2. Frontend del ciclo

| Mutante | Qué rompe | 1.ª corrida | Final | Prueba |
|---|---|---|---|---|
| F01 | Pide el tablero sin `dashboard:view` | MUERTO | MUERTO | DSH-01 |
| F02 | Pinta la sección de indicadores aunque no traiga ninguna de sus claves | **SOBREVIVE** | MUERTO | DSH-03 reescrita (T19b) |
| F03 | Centro de reportes sin filtrar por capacidad de origen | MUERTO | MUERTO | CR-01, CR-02, CR-03 |
| F04 | Centro de reportes pide sin reporte disponible | SOBREVIVE | **EQUIVALENTE** | ver §3 |
| F05 | Botón de descarga siempre visible | MUERTO | MUERTO | EXP-02 |
| F06 | La bitácora de reportes vuelve a `reportes:view` | MUERTO | MUERTO | EXP-03, NAV-07 |
| F07 | Capacidades del reporte divergentes del backend | MUERTO | MUERTO | CR-01, CR-04 (paridad con la instantánea) |

Por qué sobrevivió F02: la primera DSH-03 era un falso verde de temporización. Comprobaba la ausencia de la sección cuando la petición se había hecho, pero aún no se había resuelto. La reescritura espera a que la otra sección se pinte, y así prueba que la respuesta ya llegó. El mismo defecto estaba en READ-E2E-05 y se corrigió igual: espera la respuesta de `/reporting/dashboard`.

## 3. F04, equivalente

**Mutación exacta.** En `CentroReportesPage.tsx`, `enabled: current !== undefined,` pasa a `enabled: true,`.

**Por qué el comportamiento externo es idéntico.**
- `current` solo puede ser `undefined` cuando no hay ningún reporte disponible. Si hay alguno, la categoría efectiva cae en `disponibles[0]`. Por tanto, con reportes disponibles `enabled` ya es verdadero sin mutación.
- Sin reportes, la `queryFn` lanza `Error("sin reporte")` antes de llamar a `apiFetch`, así que no sale ninguna petición. Esa rama tampoco pinta el resultado de la consulta: solo pinta el mensaje «No tiene autoridad…».

**Control independiente.** La guarda de la `queryFn` (motivo R5 del reintento 1 de T16b). Son dos defensas de la misma propiedad: no pedir un reporte que no se puede ver.

**Evidencia.** Con el mutante, CR-02 sigue en verde: `apiFetch` no se llamó y se ve el mensaje. Ningún estado observable cambia.

## 4. Regresión de 02B: cómo se reconstruyeron las herramientas

El anfitrión se reinició a las 19:00 y el directorio temporal del scratchpad se perdió.
- **Recuperación.** Las herramientas se recuperaron de la traza de la sesión: la última versión escrita de cada una, más los guiones que la modificaron. `mutaciones_alcance.py` tiene 23 mutantes y `mutaciones_delegacion.py`, 21, iguales a los de 02B.
- **Primera corrida.** S13 y D13 sobrevivieron con las listas de pruebas reconstruidas, que eran más estrechas que las de las corridas de certificación de 02B. Allí S13 murió con 28 pruebas y D13 con 19; aquí corrieron con 21 y 6.
- **Corrida contra la familia completa.** Con las pruebas de delegación, alcance, autoridad, arquitectura de alcance, almacenes, lecturas y UI, ambos mueren:
  - D13 lo mata `test_delegation_ceiling.py::test_dc_u01_usuario_inactivo_no_tiene_autoridad`;
  - S13 lo mata `test_company_scope_derived.py::test_csd_07_asignacion_a_empresa_sin_acceso_no_cuenta`.

La regresión es 23/23 y 21/21 con las pruebas actuales. No es una equivalencia: las mata una prueba que existe.
