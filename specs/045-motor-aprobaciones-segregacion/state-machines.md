# MÁQUINAS DE ESTADO — SPEC 045

## 1. `ApprovalRequest`

```
                    ┌──────────────────────────────► OBSOLETE
                    │  (huella del documento cambió)
                    │
  DRAFT ──► PENDING ──► IN_REVIEW ──┬──► APPROVED
              │            │        ├──► REJECTED
              │            │        ├──► RETURNED ──► (nueva solicitud vinculada)
              └────────────┴────────┴──► CANCELLED
```

| Estado | Significado | Terminal |
|---|---|---|
| `DRAFT` | Creada y aún no enviada. Uso interno de simulación | No |
| `PENDING` | Enviada; ningún paso abierto todavía | No |
| `IN_REVIEW` | Al menos un paso abierto esperando decisión | No |
| `APPROVED` | Todos los niveles resueltos favorablemente | **Sí** |
| `REJECTED` | Rechazada en cualquier nivel — terminal (CL-045-03) | **Sí** |
| `RETURNED` | Devuelta para corrección; el documento vuelve a editable | **Sí** |
| `CANCELLED` | Cancelada sin resolver | **Sí** |
| `OBSOLETE` | El documento cambió tras solicitarla; no admite resolución | **Sí** |

### Transiciones permitidas

| Desde | Hacia | Disparador | Regla |
|---|---|---|---|
| `DRAFT` | `PENDING` | Envío del documento | — |
| `PENDING` | `IN_REVIEW` | Apertura del primer paso | Actores elegibles congelados |
| `PENDING`/`IN_REVIEW` | `OBSOLETE` | Cambio de huella | Automática, sin actor |
| `PENDING`/`IN_REVIEW` | `CANCELLED` | Solicitante o política | Motivo registrado |
| `IN_REVIEW` | `IN_REVIEW` | Cuórum de un nivel alcanzado y quedan niveles | Abre el siguiente |
| `IN_REVIEW` | `APPROVED` | Último nivel resuelto favorablemente | Documento avanza |
| `IN_REVIEW` | `REJECTED` | Rechazo en cualquier nivel | **Motivo obligatorio**; documento a editable |
| `IN_REVIEW` | `RETURNED` | Devolución en cualquier nivel | **Motivo obligatorio**; historial conservado |

**Prohibido:** salir de un estado terminal. Reintentar tras `RETURNED`, `REJECTED` u `OBSOLETE`
**crea una solicitud nueva** con `previous_request_id` (FR-045-030).

## 2. `ApprovalStep`

```
  PENDING ──► IN_REVIEW ──┬──► APPROVED
                          ├──► REJECTED
                          ├──► RETURNED
                          └──► EXPIRED   (vencido; NO resuelve — CL-045-06)

  PENDING ──► SKIPPED   (la solicitud terminó antes de abrirse este nivel)
```

| Estado | Regla |
|---|---|
| `PENDING` | Creado, aún no abierto porque el nivel anterior no ha concluido |
| `IN_REVIEW` | Abierto; `eligible_actors` congelado; `due_at` calculado si hay `sla_hours` |
| `APPROVED` | Cuórum alcanzado favorablemente |
| `REJECTED` / `RETURNED` | Una sola decisión negativa basta, cualquiera sea el cuórum |
| `EXPIRED` | Superado `due_at`. **Marca y emite evento; no aprueba ni rechaza** |
| `SKIPPED` | La solicitud concluyó antes; no se abre |

> Un rechazo o devolución **no** requiere cuórum: basta una decisión negativa. Exigir unanimidad para
> frenar algo invertiría el sentido del control.

## 3. Cuórum

| Tipo | Aprueba cuando | Rechaza/devuelve cuando |
|---|---|---|
| `ANY` | 1 decisión favorable | 1 decisión negativa |
| `ALL` | Todos los elegibles favorables | 1 decisión negativa |
| `N_OF_M` | `quorum_n` favorables | 1 decisión negativa |

Un mismo actor **no** puede emitir dos decisiones sobre el mismo paso.

## 4. Efecto sobre el documento de origen

El motor no manipula el documento: **informa**. El dominio consumidor reacciona.

| Estado de la solicitud | Efecto esperado en el documento |
|---|---|
| `PENDING` / `IN_REVIEW` | Bloqueado para avanzar y para editar los campos de la huella |
| `APPROVED` | Habilitado para su siguiente transición |
| `REJECTED` | Vuelve a estado editable |
| `RETURNED` | Vuelve a estado editable con observaciones visibles |
| `CANCELLED` | Vuelve a estado editable |
| `OBSOLETE` | Editable; debe volver a solicitarse antes de avanzar |

> **FR-045-029:** ningún documento avanza a su siguiente estado sin solicitud `APPROVED`, cuando la
> política determina que la requiere.

## 5. `ApprovalDelegation`

```
  ACTIVE ──┬──► EXPIRED  (superado valid_to)
           └──► REVOKED  (revocación explícita)
```

Ni `EXPIRED` ni `REVOKED` invalidan decisiones ya tomadas bajo la delegación (FR-045-046, P5).

## 6. Invariantes verificables

| ID | Invariante |
|---|---|
| INV-01 | Una solicitud terminal no cambia de estado nunca más |
| INV-02 | No existen dos solicitudes no terminales para el mismo documento y huella |
| INV-03 | `current_level` siempre apunta al paso abierto de menor orden, o a nulo si no hay ninguno |
| INV-04 | Toda decisión `REJECT` o `RETURN` tiene `reason` no vacío |
| INV-05 | Con `requires_segregation`, `requested_by` no aparece en `eligible_actors` de ningún paso |
| INV-06 | Un actor no emite dos decisiones sobre el mismo paso |
| INV-07 | `policy_snapshot` es inmutable durante toda la vida de la solicitud |
| INV-08 | La suma de decisiones favorables de un paso `APPROVED` satisface su cuórum |
