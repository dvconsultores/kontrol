# CRITERIOS DE ACEPTACIÓN — SPEC 045

Formato Gherkin abreviado. Toda ejecución sobre **PostgreSQL** (P21).

## AC-01 · Política versionada no altera lo resuelto
**Dado** una solicitud aprobada bajo la política v1
**Cuando** se activa la v2 con umbrales distintos
**Entonces** la solicitud conserva `policy_version = 1` y su `policy_snapshot` intacto,
y el documento no se reevalúa.

## AC-02 · No hay dos políticas activas solapadas
**Dado** una política `ACTIVE` para (empresa, `PURCHASE_ORDER`)
**Cuando** se intenta activar otra con vigencia solapada
**Entonces** la operación falla con `APPROVAL_POLICY_OVERLAP` y la restricción de base de datos lo
impide aunque se intente por dos transacciones concurrentes.

## AC-03 · El monto se evalúa en moneda base
**Dado** un umbral expresado en moneda base
**Y** dos órdenes de igual importe nominal en monedas distintas
**Cuando** se evalúan
**Entonces** los niveles resultantes se corresponden con el **equivalente en moneda base** calculado
con la tasa snapshot de cada documento, no con el importe nominal.

## AC-04 · Condición no evaluable no pasa en silencio
**Dado** una regla que depende de `cost_center_id`
**Cuando** el documento no lo trae
**Entonces** se devuelve `APPROVAL_CONDITION_UNEVALUABLE` (422)
**Y** en ningún caso se concluye «no requiere aprobación».

## AC-05 · Segregación impide al creador resolver
**Dado** una política con `requires_segregation = true`
**Cuando** el creador del documento intenta aprobar
**Entonces** recibe 403 `APPROVAL_SEGREGATION_VIOLATION`
**Y** no aparece en `eligible_actors`
**Y** su `allowed_actions` es `[]`.

## AC-06 · La delegación no elude la segregación
**Dado** que el creador tiene una delegación del aprobador
**Cuando** intenta resolver su propia solicitud con segregación activa
**Entonces** recibe 403: la delegación **no** habilita lo que la segregación prohíbe.

## AC-07 · Obsolescencia por cambio de documento
**Dado** una solicitud `IN_REVIEW` cuya huella incluye `amount`
**Cuando** el documento cambia su `amount`
**Entonces** la solicitud pasa a `OBSOLETE`
**Y** cualquier intento de resolverla devuelve 409 `APPROVAL_REQUEST_OBSOLETE`.

## AC-08 · Un cambio ajeno a la condición NO invalida
**Dado** la misma solicitud
**Cuando** el documento cambia una observación interna que no participa en ninguna condición
**Entonces** la solicitud permanece `IN_REVIEW`.

## AC-09 · Concurrencia sobre el mismo paso
**Dado** un paso `IN_REVIEW` con cuórum `ANY`
**Cuando** dos aprobadores elegibles resuelven simultáneamente
**Entonces** exactamente una decisión se registra y la otra recibe 409
`APPROVAL_STEP_VERSION_CONFLICT`
**Y** no existen dos decisiones para el mismo paso del mismo actor.

## AC-10 · Idempotencia de creación
**Dado** un documento sin cambios
**Cuando** se solicita aprobación dos veces
**Entonces** existe **una sola** `ApprovalRequest` y la segunda llamada devuelve la misma.

## AC-11 · Cuórum N de M
**Dado** un nivel con `N_OF_M`, N=2, M=3
**Cuando** hay una decisión favorable
**Entonces** el paso sigue `IN_REVIEW`
**Cuando** hay una segunda favorable
**Entonces** el paso pasa a `APPROVED` y se abre el nivel siguiente si existe.

## AC-12 · Una negativa basta, cualquiera sea el cuórum
**Dado** un nivel con cuórum `ALL`
**Cuando** un solo actor rechaza
**Entonces** el paso pasa a `REJECTED` y la solicitud a `REJECTED`, sin esperar a los demás.

## AC-13 · Rechazo es terminal y devuelve el documento a editable
**Dado** una solicitud rechazada en el nivel 2
**Entonces** su estado es `REJECTED`, no admite más decisiones,
**Y** el documento vuelve a estado editable.

## AC-14 · Devolución conserva historial y encadena
**Dado** una solicitud devuelta
**Cuando** se corrige el documento y se reenvía
**Entonces** se crea una solicitud nueva con `previous_request_id` apuntando a la anterior
**Y** el historial del documento muestra ambas.

## AC-15 · Motivo obligatorio en negativas
**Cuando** se rechaza o devuelve sin `reason`
**Entonces** 422 `APPROVAL_REASON_REQUIRED`.

## AC-16 · Vencimiento no resuelve
**Dado** un paso con `due_at` superado
**Entonces** queda `EXPIRED` y emite evento
**Y** la solicitud **no** queda aprobada ni rechazada por el paso del tiempo.

## AC-17 · El documento no avanza sin aprobación
**Dado** una política que exige aprobación
**Cuando** se intenta avanzar el documento con la solicitud `IN_REVIEW`
**Entonces** la transición se rechaza en backend, no solo en la interfaz.

## AC-18 · Revocar delegación no reescribe historia
**Dado** una decisión tomada bajo una delegación
**Cuando** la delegación se revoca
**Entonces** la decisión permanece válida y registra la delegación con la que se ejerció.

## AC-19 · Bandeja transversal
**Dado** solicitudes de compras, ventas, inventario y regulatorio
**Cuando** un aprobador abre «Mis aprobaciones»
**Entonces** ve las de todos los dominios en una sola lista, con monto en moneda base y antigüedad.

## AC-20 · Migración sin cambio de comportamiento
**Dado** el comportamiento de aprobación de compras antes de migrar
**Cuando** se activa la política equivalente y se redirige al motor
**Entonces** el mismo caso produce el mismo resultado observable.

## AC-21 · Ningún módulo conserva lógica propia
**Cuando** se busca lógica de aprobación fuera de `approvals`
**Entonces** no hay coincidencias en `purchasing`, `sales`, `inventory` ni `regulatory` (P22).

## AC-22 · Histórico migrado sin inventar
**Dado** aprobaciones anteriores al motor
**Entonces** figuran cerradas con `policy_version = LEGACY_UNVERSIONED` y marca explícita,
**Y** ninguna declara una política que no existió.

## AC-23 · Nada de negocio en el código
**Cuando** se busca cualquier umbral, nivel, rol o moneda literal en `approvals`
**Entonces** no hay coincidencias: todo procede de datos (P8).

## AC-24 · Accesibilidad y responsive
**Entonces** las pantallas de políticas, bandeja e historial pasan axe WCAG 2.2 AA,
son operables solo con teclado y no producen scroll horizontal entre 320 y 1920 px.
