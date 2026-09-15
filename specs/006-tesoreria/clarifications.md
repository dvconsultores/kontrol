# CLARIFICACIONES — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/006-tesoreria/clarifications.md` |

## 1. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-006-01 | Ejecución de pagos/cobros | ¿006 reimplementa los pagos/cobros? | **No.** 006 **consume** los pagos de 004 y cobros de 005 (contratos v1) y los **ejecuta** contra caja/banco y concilia. No duplica la lógica de 004/005 | Arquitecto | Resuelto |
| CL-006-02 | IGTF | ¿006 calcula el IGTF completo? | 006 estructura el IGTF **por regla y evento** (no confundir con IVA adicional) y lo refiere a **reglas versionadas**; el motor fiscal completo es de **007** | Contador/fiscal | Resuelto |
| CL-006-03 | Cajas | ¿Cómo se controlan las cajas? | Por **sesiones** (apertura → movimientos → arqueo → pre-cierre → cierre) con diferencias explícitas; una caja no se cierra con diferencia sin aprobación | Tesorería | Resuelto |
| CL-006-04 | Conciliación | ¿Automática o manual? | **Asistida con reglas** (match score) y **resolución manual auditada** | Contador | Resuelto |
| CL-006-05 | Maestros financieros | ¿Bancos/cuentas/cajas/monedas/tasas existen? | No están implementados; 006 los crea como **prerequisito** (DOC-02 §3 "Maestros / Financiero") — similar a cómo 003 tomó los almacenes | Arquitecto | Resuelto |
| CL-006-06 | Dependencias | ¿Se implementa 006 sin 004/005? | Requiere **001 certificada**, **002/004/005 implementados** y autorización expresa. La fase documental no requiere nada | Producto | Resuelto |
| CL-006-07 | Anticipos | ¿Cómo se manejan? | Sin aplicación inicial y **posterior imputación** (reutiliza el motor de 004/005) | Tesorería | Resuelto |
| CL-006-08 | Comisiones/diferencias | ¿Alteran el IVA original? | No: se registran al conciliar sin alterar el IVA causado (DOC-02 §9/§10) | Contador | Resuelto |

## 2. Supuestos declarados

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-006-01 | El cálculo completo de IGTF/retenciones es de 007; 006 estructura por regla/evento | Cálculo fiscal incompleto | Reglas versionadas; migración sin reescritura |
| SU-006-02 | Los maestros financieros son prerequisito de 006 (no estaban en 002) | Sin maestros no hay tesorería | Crear en la migración `0006` |
| SU-006-03 | La conciliación usa reglas de match configurables (referencia/importe/fecha) | Emparejamiento imperfecto | Reglas versionadas + resolución manual auditada |
| SU-006-04 | Cada transacción conserva snapshot de moneda y tasa histórica | Cambios de tasa no alteran histórico | Snapshot por transacción |
| SU-006-05 | 006 no concilia bancos con 004/005: los consume vía contrato | Acoplamiento | Contratos de API v1 |

## 3. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-006-09 | Reglas de match de conciliación por banco (tolerancias) | Conciliación | No la fase documental |
| CL-006-10 | Política de cierres de caja (horarios, responsable de diferencias) | Arqueos | No la fase documental |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |

## 5. Delta FLOAT-038-A — decisiones del owner (Spec 038 · 2026-09-14)

| ID | Pregunta | Decisión | Descartadas | Razón | Estado |
|---|---|---|---|---|---|
| OQ-FLOAT-038-A-01 | ¿Cómo viaja el importe del movimiento bancario en el contrato público? | **Texto decimal**, al entrar y al salir, para `amount` y `commission`. Un número JSON se rechaza con 422 | B: número con degradación documentada · C: número literal con serializador propio | la exactitud tiene que sobrevivir a JavaScript, HTTP y Python; un número JSON no sobrevive a la primera | `CLOSED_BY_OWNER_DECISION` |
| OQ-FLOAT-038-A-02 | ¿Qué pasa con más decimales que la escala? | **Rechazo con 422**. Escala efectiva de este contrato: 2, la de `numeric(18,2)` | redondeo de PostgreSQL · cuantización de `_money` | ninguna transformación económica silenciosa | `CLOSED_BY_OWNER_DECISION` |

El cambio de número a texto es **incompatible y está autorizado**. Una escala por
moneda (`Currency.decimal_places`) exigiría otro delta con contrato, modelo y
migración.

## 6. Delta FLOAT-038-B — decisiones heredadas y perímetro (Spec 038 · 2026-09-15)

No hay preguntas nuevas. El arqueo y el cierre heredan las decisiones de §5:

| Tema | Decisión | Autoridad |
|---|---|---|
| `counted_amount` en la API | texto decimal; un número JSON → 422 | OQ-FLOAT-038-A-01 |
| Exceso de escala del conteo | 422, sin redondeo | OQ-FLOAT-038-A-02 |
| Cero del cierre | exacto, sin épsilon ni tolerancia; ninguna fuente autoriza un margen | decisión cerrada · FR-006-003 |
| Importes en la auditoría | texto decimal; sin consumidores que lean esos valores | `KQA-100` · inventario del delta |
| Signo del conteo | se conserva `≥ 0` | contrato previo |
| Fórmula y signo de la diferencia | `contado − esperado`, sin cambio | Spec 038 |

**Perímetro.** La respuesta de la sesión de caja se corrige entera —fondo, esperado,
conteo, diferencia e importes de movimientos— porque sale de un único serializador
en siete rutas. Las entradas `opened_amount` y el importe de movimiento, y la
respuesta de `POST …/movements`, son otros contratos y siguen abiertos.
