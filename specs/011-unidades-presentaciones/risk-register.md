# REGISTRO DE RIESGOS — SPEC 011

| ID | Riesgo | Prob. | Impacto | Sev. | Mitigación |
|---|---|---|---|---|---|
| **RSK-011-01** | **Pérdida de significado histórico**: se sigue escribiendo sin unidad mientras la Spec se implementa, y cada línea nueva es deuda irrecuperable | **Alta** | **Crítico** | **CRÍTICA** | F4 va **antes** que la API de consumo (P23). Es la razón de que 011 esté aquí en el roadmap y no más tarde |
| **RSK-011-02** | **Backfill que inventa historia**: se asigna la unidad «más probable» y el dato queda falso con apariencia de correcto | **Alta** | **Crítico** | **CRÍTICA** | Cuatro clases; clase C queda **nula y marcada**; `factor = 1` solo demostrado (R-011-4); prueba que exige que no se adivine |
| **RSK-011-03** | **Documento fiscal alterado**: se anota una unidad supuesta en una factura ya emitida ante la administración tributaria | Media | **Crítico** | **CRÍTICA** | Clase D: **cero escrituras** sobre líneas fiscales irreconstruibles; bloqueo de la migración por umbral |
| **RSK-011-04** | **Regresión en tres dominios a la vez**: `inventory`, `purchasing` y `sales` reciben columnas **y** cambio de tipo | **Alta** | **Alto** | **ALTA** | Migraciones separadas (esquema, tipo, columnas, datos); batería completa de los tres como criterio de salida |
| **RSK-011-05** | **`Float → NUMERIC` altera valores en silencio**: un `0.30000000000000004` se convierte y nadie se entera | **Alta** | Alto | **ALTA** | Se reporta toda fila cuyo valor cambie (FR-011-063); prueba de suma agregada antes y después |
| **RSK-011-06** | **Redondeo divergente**: frontend, backend y base de datos aplican reglas distintas y las cifras no cuadran | Media | **Alto** | **ALTA** | Un solo lugar de redondeo (FR-011-045); la vista previa del frontend es informativa y no vincula |
| **RSK-011-07** | **Versiones solapadas**: dos factores vigentes hacen la conversión no determinista | Media | **Alto** | **ALTA** | Índice único parcial sobre la versión abierta; validación de rango en transacción; prueba de concurrencia |
| **RSK-011-08** | **Mutación de unidad base**: alguien cambia `UND` por `CAJA` en un producto con historial y reinterpreta todas sus cantidades | Media | **Crítico** | **ALTA** | `base_unit_locked`, irreversible con el primer movimiento (R-011-3) |
| **RSK-011-09** | **Presentación convertida en SKU**: se crea un producto por presentación y el catálogo se duplica | Media | Alto | MEDIA | R-011-1; la interfaz lo dice explícitamente; las variantes son de la Spec 010 |
| **RSK-011-10** | **Presentación y despacho confundidos**: se asume que se despacha en la presentación vendida | Media | Medio | MEDIA | `dispatchable` separado; contrato de despacho declarado sin implementarse (§20) |
| **RSK-011-11** | **N+1 en documentos grandes**: mil líneas, mil consultas de conversión | **Alta** | Medio | MEDIA | `to_base_bulk`; índice compuesto; prueba que **cuenta consultas**, no tiempo |
| **RSK-011-12** | **Caché que sirve un factor obsoleto** y altera la precisión histórica | Media | **Alto** | **ALTA** | Caché **por petición**, nunca entre peticiones (NFR-011-02) |
| **RSK-011-13** | **Fuga entre empresas**: un producto de A referencia una presentación de B | Baja | Alto | MEDIA | `company_id` en presentación y versión; filtro en toda consulta; prueba de aislamiento |
| **RSK-011-14** | **`NOT NULL` prematuro**: forzar la obligatoriedad antes de resolver el histórico obliga a inventar un valor | Media | **Crítico** | **ALTA** | Las columnas nacen *nullable*; `NOT NULL` solo cuando el reporte demuestre 0 líneas sin resolver (plan §9) |
| **RSK-011-15** | **El motor de conversión se replica**: compras calcula por su cuenta y ventas de otra forma | Media | Alto | **ALTA** | P22; AC-011-34 busca cálculos duplicados como criterio de salida |
| **RSK-011-16** | **Sobreingeniería**: alias, peso variable y presentaciones genéricas inflan el MVP y retrasan lo urgente | Media | Medio | MEDIA | `FUTURE_CAPABILITY` explícito (CL-011-19); el modelo no los bloquea, tampoco los construye |
| **RSK-011-17** | **La migración paraliza el despliegue**: demasiadas líneas fiscales irreconstruibles y nadie puede actualizar | Media | Medio | MEDIA | Umbral **configurable** (ESC-011-01); el reporte dice exactamente qué líneas resolver |

## Riesgo dominante

**RSK-011-01**, y es de una naturaleza distinta a los demás: no es un riesgo de
la implementación, es el riesgo de **tardar**. Cada día que KONTROL opera sin
capturar la unidad añade líneas que ninguna migración futura podrá reparar,
porque el dato no se perdió: nunca se capturó.

Es exactamente lo que `ADR-D0-009` llamó «la deuda que más rápido se encarece», y
la razón por la que esta Spec ocupa esta posición del roadmap.

## Diferencia con el riesgo de la Spec 008

En la Spec 008 el riesgo era imponer integridad sobre referencias que **existían**
pero estaban rotas. Aquí el riesgo es asignar significado a un dato que **nunca se
capturó**. Es más grave: allí había algo que reparar; aquí, en el peor caso, solo
hay algo que **admitir que no se sabe**.

De ahí que la clase C de esta Spec no repare nada: deja la línea marcada como
irresuelta. Una cantidad sin unidad conocida es un dato incompleto honesto; una
cantidad con la unidad equivocada es un dato falso.
