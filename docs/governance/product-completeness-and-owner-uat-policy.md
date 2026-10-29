# PRODUCT_COMPLETENESS_AND_OWNER_UAT_POLICY

| Campo | Valor |
|---|---|
| Estado | **PERMANENT PROJECT NORM** (vinculante desde el 2026-10-29) |
| Origen | Encargo de la dueña GOV-PRODUCT-COMPLETENESS-RETRO-01 (§0–§89) |
| Alcance | Todo ciclo de producto de KONTROL (Empresarial y Gobierno) y todo informe de cierre de Claude |
| Precedencia | Debajo de la Constitución y de las decisiones de la dueña; por encima de las instrucciones de cada tarea |
| Primera aplicación | Retrospectiva de Gobierno: `docs/roadmap/government-product-completeness/` |

## 1. Para qué existe

Una Spec, una API, una tabla, muchas pruebas verdes o un `CLOSED` técnico **no** significan que el usuario pueda trabajar. Esta norma separa dos preguntas que antes se mezclaban:

- ¿está bien construida la pieza técnica?
- ¿puede una persona del negocio hacer su trabajo con ella, desde el menú, de principio a fin?

Una funcionalidad de producto está terminada solo cuando la segunda respuesta es «sí» y está demostrada.

## 2. Las tres preguntas obligatorias

Toda revisión y todo informe de cierre empiezan respondiéndolas, antes de cualquier recuento técnico:

1. **¿Dónde está en el menú?** Menú principal › submenú › ruta › pantalla › acción › roles que la ven. Si es funcionalidad de usuario y no tiene una entrada clara, **no está terminada**.
2. **¿Qué puede hacer el usuario?** En verbos del negocio, según lo que aplique: entra, consulta, crea, modifica, procesa, envía, aprueba, rechaza, corrige, anula, adjunta, genera, imprime, exporta, consulta el historial. Está prohibido responder con «hay 14 endpoints» o «la Spec tiene 85 requisitos». Si no se puede describir el flujo completo, **no está terminada**.
3. **¿Está listo para que la dueña lo pruebe?** Debe existir una tarjeta de prueba concreta (§7). Si para probarlo hace falta curl, un guion, la API directa, mirar una tabla, o «falta la pantalla», entonces `OWNER_UAT_READY = NO`.

## 3. Taxonomía de estados

Cada entregable lleva exactamente uno:

| Estado | Significa |
|---|---|
| `NOT_STARTED` | No hay implementación demostrada |
| `TECHNICAL_FOUNDATION` | Infraestructura o prerrequisito técnico válido (seguridad, MFA, auditoría, zona horaria, copia, aislamiento, permisos). No es funcionalidad visible |
| `BACKEND_IMPLEMENTED` | Hay lógica, base de datos o API; el frontend o el proceso están incompletos |
| `FRONTEND_PARTIAL` | Hay UI, pero el proceso o el contrato no están completos |
| `PRODUCT_PARTIAL` | Hay backend y frontend, pero falla al menos una compuerta obligatoria |
| `OWNER_UAT_READY` | Completo y preparado para la prueba manual de la dueña |
| `OWNER_ACCEPTED` | La dueña ejecutó la prueba y lo aceptó de forma expresa |
| `BLOCKED` | Hay una dependencia material sin resolver (decisión del sponsor, norma sin validar, infraestructura) |
| `DEPRECATED` | Existe técnicamente, pero ya no pertenece al producto objetivo |

Quedan prohibidas las fórmulas «casi listo», «básicamente hecho» o «certificado suficiente».

## 4. Definición de terminado para producto (regla binaria)

`PRODUCT_COMPLETE = 1` solo si **todas** las compuertas aplicables están en PASS:

| Compuerta | Qué se verifica |
|---|---|
| A · BACKEND_COMPLETE | Lógica de dominio, máquina de estados, transiciones válidas, validación, permisos, alcance, concurrencia, idempotencia donde aplique, persistencia, restricciones, corrección, reverso/anulación, errores, auditoría, documentos, reportes y API. «Existe un CRUD» no es PASS |
| B · FRONTEND_COMPLETE | Pantalla real con integración real: formularios, tablas, acciones, estados (carga, vacío, sin permiso, confirmación, validación, éxito, conflicto), responsive y accesibilidad. Una maqueta o un componente sin uso es FAIL |
| C · MENU_NAVIGATION_COMPLETE | Se llega desde el menú con el rol requerido. Que exista la ruta directa no basta |
| D · PROCESS_COMPLETE | El procedimiento se recorre de punta a punta: evento de inicio, actor, pasos, estado final, salida, documento, reporte y evidencia de auditoría, con aprobación, rechazo, corrección, devolución, anulación, reapertura y cierre cuando el proceso los requiere |
| E · SCREEN_FORM_COMPLETENESS | Cada pantalla, formulario, lista, detalle, modal, asistente, tablero o reporte tiene su ficha (propósito, actores, pre y poscondiciones, campos, acciones, estados, validaciones, visibilidad y edición por rol, documentos, efecto en reportes y auditoría, errores, concurrencia, responsive, accesibilidad y E2E). Objetivo: 0 pantallas, formularios, campos, acciones y estados requeridos faltantes |
| F · FIELD_CONTRACT_COMPLETE | Cada campo tiene contrato completo (significado, tipos de BD y API, obligatoriedad, fuente, validación, formato, precisión, catálogo, visibilidad y edición por rol y estado, auditoría, reporte, error y ayuda), reconciliado con requisitos, proceso, norma y pantalla. Un campo olvidado es FAIL |
| G · ROLE_PERMISSION_COMPLETE | Matriz actor × acción (ver, crear, editar, enviar, aprobar, rechazar, cancelar, anular, imprimir, exportar, administrar), aplicada en el backend, proyectada igual en el frontend y probada con llamadas hostiles directas a la API. Ningún rol se infiere por su nombre visible |
| H · DOCUMENT_PROCESS_COMPLETE | Documentos requeridos: se adjuntan o generan, se validan, se ven, se descargan, se sustituyen o anulan y se auditan desde la pantalla. PASS o N/A justificado |
| I · REPORT_PROCESS_COMPLETE | Los reportes que el proceso requiere se eligen, se filtran (período, alcance), se generan, se ven y se exportan desde la pantalla, con valores y alcance verificados. PASS o N/A justificado |
| J · AUDIT_COMPLETE | Quién, qué, cuándo, tenant, empresa o ente, estado anterior y nuevo, motivo, soporte, correlación y acción catalogada; y el auditor autorizado lo encuentra en la pantalla de auditoría. Si la auditoría solo existe en la base, la auditoría técnica puede pasar y la institucional fallar |
| K · E2E_USER_FLOW_COMPLETE | Menú → pantalla → formulario/acción → API → dominio → BD → resultado → auditoría → documento/reporte, en los navegadores del estándar del proyecto, con casos negativos (rol equivocado, empresa equivocada, estado inválido, datos inválidos, URL o API directa). Una E2E solo de backend no basta |
| L · OWNER_UAT_CARD_COMPLETE | Tarjeta de prueba de la dueña escrita y ejecutable (§7) |

Si una sola compuerta material falla, `PRODUCT_COMPLETE = 0`. Ningún promedio la oculta: «backend 100, frontend 80, reportes 40 → 80 %» puede usarse como indicador interno de trabajo, nunca como estado de terminación. `OWNER_UAT_READY` solo puede ser **YES** o **NO**.

Para `OWNER_UAT_READY` además: ningún hallazgo P0 ni HIGH abierto en ese proceso, 0 controles muertos y todos los «faltantes» de la ficha de pantalla en 0.

## 5. Excepción: fundamento técnico

Lo que no tiene un actor de negocio que lo use (copia y restauración operativa, restricciones de BD, aplicación del alcance, internos de MFA, inmutabilidad de auditoría, núcleo temporal) lleva `MENU = FRONTEND = OWNER_UAT_READY = NOT_APPLICABLE`. La justificación es obligatoria y se escribe. Se clasifica `TECHNICAL_FOUNDATION` y **nunca** cuenta como módulo funcional terminado.

## 6. Dueña: listo para probar frente a aceptado

- `OWNER_UAT_READY`: lo decide Claude con evidencia (todas las compuertas en PASS y la tarjeta escrita). Una E2E verde es necesaria, pero no suficiente.
- `OWNER_ACCEPTED`: solo lo concede la dueña, de forma expresa, después de ejecutar la prueba. Claude no lo infiere, ninguna prueba automática lo concede y un «certificado» histórico no lo implica. Sin evidencia expresa, `OWNER_ACCEPTED = NO`.

## 7. Tarjeta de prueba de la dueña (OWNER UAT CARD)

```
MÓDULO: · PROCESO: · ESTADO:
DÓNDE ENTRAR: Menú > … > …
ROL A USAR:
PRECONDICIONES:
DATOS DE PRUEBA: (sintéticos; nunca PII ni secretos)
PASOS: 1. … 2. … 3. …
RESULTADO ESPERADO:
DOCUMENTOS A VERIFICAR:
REPORTES A VERIFICAR:
AUDITORÍA A VERIFICAR:
PRUEBA NEGATIVA:
LIMPIEZA:
DEUDAS CONOCIDAS NO BLOQUEANTES:
```

Si la tarjeta no se puede escribir y ejecutar, `OWNER_UAT_READY = NO`. Las tarjetas de los procesos listos forman el `OWNER_UAT_READY_CATALOG`. Puede estar vacío, y si lo está se dice. Nunca se sube un proceso parcial para no dejarlo vacío.

## 8. Porcentajes: tres métricas separadas

Queda prohibido publicar un único «avance» ambiguo. Se publican siempre por separado, con fórmula y denominador:

| Métrica | Fórmula |
|---|---|
| A · Technical Foundation Readiness | fundamentos técnicos aplicables COMPLETE ÷ fundamentos aplicables. Un fundamento cuenta solo si cumple su propia DoD técnica |
| B · Functional Product Completeness | Σ compuertas funcionales aplicables en PASS ÷ Σ compuertas aplicables, sobre el inventario de procesos (compuertas: backend, frontend, menú, proceso, campos, roles, documentos si aplica, reportes si aplica, auditoría, E2E y ficha de pantalla). **No** significa que un módulo esté terminado |
| C · Owner UAT Readiness | procesos requeridos con `OWNER_UAT_READY = YES` u `OWNER_ACCEPTED` ÷ procesos requeridos; `OWNER_ACCEPTED %` se informa aparte |

Nunca se combinan sin mostrar sus componentes y nunca se redondea al alza. Pruebas, líneas de código, propiedades, rutas, tablas o Specs son **evidencia**, no unidades de entrega: no se convierten en porcentaje de producto.

Un módulo está completo solo cuando **todos** sus procesos requeridos están en `OWNER_UAT_READY` u `OWNER_ACCEPTED`.

## 9. Recorridos obligatorios para declarar un proceso listo

- **Menú primero:** se empieza en el login, no desde la URL, Swagger ni pytest.
- **Por rol:** operador, supervisor, aprobador, auditor y administrador, según apliquen. Un proceso que solo funciona como superadministrador no está completo si los requisitos piden otros actores.
- **Documento:** desde la pantalla se adjunta o genera, se valida, se ve, se descarga, se sustituye, corrige o anula, y se audita.
- **Reporte:** desde la pantalla se elige, se filtra, se genera, se ve, se descarga y se verifican valores, alcance y período. Si el reporte esperado no tiene menú o pantalla, `REPORT_STATUS = FAIL`.
- **Auditoría:** se hace la acción y luego, como auditor autorizado, se encuentra el evento en la pantalla de auditoría.
- **Controles muertos:** cada control se clasifica DEAD_CONTROL / PARTIAL_CONTROL / PLACEHOLDER / COMPLETE.
- **Backend oculto:** lo que no tiene pantalla se clasifica TECHNICAL_ONLY / PLANNED_FRONTEND / LEGACY / PRODUCT_GAP. Un PRODUCT_GAP nunca cuenta como hecho.

## 10. Brechas y severidad

Cada brecha se clasifica con una sola clase. No se acepta un «pendiente» genérico. Clases: BACKEND_GAP, FRONTEND_GAP, MENU_GAP, PROCESS_GAP, FIELD_GAP, ROLE_GAP, DOCUMENT_GAP, REPORT_GAP, AUDIT_GAP, E2E_GAP, UAT_GAP, NORMATIVE_GAP, DATA_GAP, INTEGRATION_GAP, UX_GAP, ACCESSIBILITY_GAP y RESPONSIVE_GAP.

Severidad:

| Severidad | Significa |
|---|---|
| P0 / BLOCKER | Falla fatal de seguridad, integridad o legal |
| HIGH | El proceso no se puede completar |
| MEDIUM | Deficiencia importante de flujo o calidad |
| LOW | Mejora no bloqueante |

La remediación se ordena por riesgo, no por facilidad: P0 → proceso faltante → frontend/menú → campos → roles → documentos → reportes → auditoría → E2E → UX y accesibilidad.

## 11. Normativa

Un proceso que depende de una regla legal se vincula a su fuente oficial. Si una regla material sigue en `LEGAL_VALIDATION_REQUIRED` (p. ej. fuentes de clase C sin pin oficial), el proceso es `BLOCKED`, no completo. No se inventan reglas para tapar el hueco.

## 12. Retrospectiva

- Se repite cuando cambia la definición de producto o antes de declarar listo un módulo entero.
- Las etiquetas históricas («listo», «70 %», «certificado») son afirmaciones a revalidar, no verdad actual.
- Se reconcilian sin acusar: un informe que era correcto con una definición más estrecha se marca **TECHNICALLY CLOSED BUT NOT PRODUCT COMPLETE**.

## 13. Informes y encargos futuros

**Todo informe de cierre de Claude** empieza, antes de los recuentos de pruebas, mutaciones o commits, con:

```
PRODUCT COMPLETENESS GATE
WHERE_IS_IT_IN_MENU:
WHAT_CAN_USER_DO:
OWNER_UAT_READY: YES / NO / NOT_APPLICABLE
PRODUCT_STATUS:
MISSING_GATES:
(fundamento técnico) WHY_UI_NOT_APPLICABLE:
```

**Todo encargo de producto** futuro incluye la NORMA DE COMPLETITUD DE PRODUCTO con, como mínimo: WHERE_IS_IT_IN_MENU, WHAT_CAN_USER_DO, OWNER_UAT_READY, BACKEND_COMPLETE, FRONTEND_COMPLETE, PROCESS_COMPLETE, FIELD_COMPLETE, ROLE_COMPLETE, DOCUMENT_COMPLETE, REPORT_COMPLETE, AUDIT_COMPLETE, E2E_COMPLETE y SCREEN_FORM_COMPLETE. Ningún encargo puede omitirla. El prompt del siguiente ciclo que Claude redacta la lleva siempre.

**Toda remediación de un módulo de producto** cubre de punta a punta requisitos, proceso, backend, BD, API, frontend, menú, campos, roles, documentos, reportes, auditoría, errores, concurrencia, responsive, accesibilidad, E2E y la tarjeta de la dueña. Una remediación solo de backend nunca se etiqueta como módulo completo.

## 14. Decisiones

Claude no crea `OD-*` ni las etiqueta como decisión de la dueña sin su ratificación expresa. Una ambigüedad material es una `MATERIAL_OWNER_QUESTION`; una elección técnica dentro de requisitos aprobados es una `ARCHITECTURE_DECISION` o una `PROJECT_DESIGN_DECISION`.
