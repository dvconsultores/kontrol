# PROC-06 · Delta «Monto de la oferta» (OBS-PROC08-MONTO-01, parte de oferta)

- **Autorización.** Encargo de la dueña «P2 · GOBIERNO · SIGUIENTE CICLO · ROUTING PRODUCT-FIRST», ruta B, del 2026-11-14.
- **Decisión que lo habilita.** `OQ-PROC09-01 = A`, ratificada por la dueña el 2026-11-14. Se le preguntó si ratificaba A y respondió «elige siempre lo recomendado»; la opción recomendada era A. La ratificación queda en `specs/gov-proc-09-responsabilidad-social/DECISIONES.md`.
- **Spec dueña.** PROC-06, recepción de ofertas.
- **Evidencia.** `evidence/monto-oferta/`.

## Qué podrá hacer el usuario que antes no podía

En la ficha de una oferta, quien tenga «Ofertas: declarar monto» registra lo que la oferta declara:
- la moneda;
- el monto del objeto sin IVA;
- los tributos;
- el total con tributos;
- el documento que lo soporta: un documento de la propia oferta o el acta de apertura que la abrió.

El monto se puede corregir con motivo; cada corrección es una versión nueva y la anterior queda en la historia. A partir de ese dato:
- **REP-03** muestra el monto declarado de las ofertas adjudicadas, por moneda;
- **PROC-10** evalúa la garantía de mantenimiento fijada como porcentaje de la oferta;
- **PROC-08** muestra el monto de cada oferta abierta.

KONTROL no inventa, no estima y no recalcula ningún monto.

## Requisitos

| Id | Requisito |
|---|---|
| OMA-01 | **Autoridad.** El monto es el declarado en la oferta recibida. Se transcribe tal cual, y el soporte es obligatorio |
| OMA-02 | **Exactitud.** `NUMERIC(18,2)`, recibido como texto decimal exacto (`app/shared/money.texto_decimal`), sin `float` ni redondeo. Monto sin IVA ≥ 0, tributos ≥ 0 y total > 0. Si la suma no coincide con el total, no se corrige ni se rechaza: se muestra «La suma declarada no coincide con el total (diferencia X)» |
| OMA-03 | **Moneda.** Una de `MONEDAS_LIMITE` (VES, USD o EUR), el mismo catálogo de los límites de ORG-03 y de PROC-10. No se convierte moneda |
| OMA-04 | **Soporte.** `DOCUMENTO_OFERTA`: un documento fijado en esa oferta, con su versión y huella. `ACTA_APERTURA`: el acta del acto que abrió la oferta. Cualquier otro documento → 422 |
| OMA-05 | **Confidencialidad.** El monto de una oferta sellada solo se registra después de abrirla, porque antes nadie puede leer el sobre (PROC-06 FR-007 y PROC-07 FR-004). Una oferta sin sello admite el monto desde su recepción. Sin monto no hay nada que filtrar. La cronología y la auditoría nunca llevan importes |
| OMA-06 | **Frontera.** Se puede declarar y corregir mientras el expediente esté ABIERTO y la evaluación no esté concluida (PROC-07 FR-007). Después → 409 `GOV_OFFER_AMOUNT_CLOSED`. Un sobre de calificación no lleva precio (LCP art. 78) → 422 `GOV_OFFER_AMOUNT_NOT_APPLICABLE` |
| OMA-07 | **Corrección.** Versión N+1 con motivo de al menos 10 caracteres, `reemplaza_id` igual a la versión vigente y la versión esperada en la entrada. La tabla es de solo inserción, con disparadores de inmutabilidad, y la historia completa queda visible |
| OMA-08 | **Legado.** Las ofertas existentes quedan `NO_DECLARADO`, sin backfill. Si su expediente sigue dentro de la frontera, se completan con el flujo normal |
| OMA-09 | **PROC-08.** El estado de decisión muestra el monto vigente de cada oferta abierta. **No** valida límites de autoridad: no hay regla aprobada de comparación con `limit_amount` (OQ-OMA-01) |
| OMA-10 | **PROC-10.** La regla MANT-OFERTA-1 (`base = MONTO_OFERTA`) usa el porcentaje del requisito, que fija el pliego, nunca KONTROL, sobre el monto de la oferta de la garantía. Como «porcentaje de la oferta presentada» (RLCP art. 135) no precisa si incluye tributos: **CUMPLE** si cubre el porcentaje del mayor de los dos montos; **NO_CUMPLE** si no cubre el del menor; en medio, **NO_EVALUABLE**, nombrando la ambigüedad. Si la moneda es distinta, NO_EVALUABLE. Se compara sin redondear (`monto × 100 ≥ % × base`) |
| OMA-11 | **REP-03.** El bloque «Monto» da, por moneda, la suma del total con tributos y del monto sin IVA de las ofertas adjudicadas vigentes del periodo, junto con el número de adjudicaciones con monto y sin monto. Nunca se mezclan monedas. Sin datos: «No declarado: ninguna oferta adjudicada del periodo tiene monto declarado». También va en el CSV |
| OMA-12 | **PROC-09.** Se cierra solo `DOMAIN_DEPENDENCY_ON_AMOUNT`. PROC-09 sigue BLOCKED (U.T., porcentaje, PROC-04, contrato, exclusiones y OQ-PROC09-02..04) |
| OMA-13 | **Aislamiento.** Todo filtra por `company_id`; la oferta de otro ente → 404 |
| OMA-14 | **Concurrencia.** If-Match con la versión del expediente y bloqueo de su fila, que serializa la declaración con la apertura y con la conclusión. UNIQUE(company_id, offer_id, version) y UNIQUE(reemplaza_id): ante una carrera, uno obtiene 201 y el resto 409, sin pérdida silenciosa |
| OMA-15 | **Pantalla, E2E y UAT.** Panel «Monto declarado» en la ficha de la oferta, sin UUID; E2E con Axe a 1280, 390 y 320; tarjeta de la dueña |

Capacidad nueva: `gobierno_ofertas:amount`, SENSITIVE (pide MFA), concedida a FUNCIONAL_COMPLETO por la migración.

Auditoría: `GOV_PROCUREMENT_OFFER_AMOUNT_DECLARED` y `GOV_PROCUREMENT_OFFER_AMOUNT_CORRECTED`, con referencia, versión y moneda, sin importes. Cronología de PROC-03: clase OFERTA, «Monto declarado R-000N» o «Monto corregido R-000N», también sin importes.

## Decisiones de diseño (Claude; reversibles; ninguna material)

| Id | Decisión | Por qué |
|---|---|---|
| OD-OMA-01 | Tabla nueva `gov_procurement_offer_amounts`, de solo inserción. `gov_procurement_offers` es inmutable por disparador y no se toca | No se rompe el contrato de la oferta sellada |
| OD-OMA-02 | Sobre sellado: el monto se registra solo después de la apertura | Es lo único que permite el sello. No se cifra nada ni se crea una ruta de lectura previa |
| OD-OMA-03 | La frontera es la conclusión de la evaluación | El aspecto económico se examina en la evaluación (LCP art. 95). PROC-08 y PROC-10 consumen después un dato estable |
| OD-OMA-04 | Los tres importes se guardan tal como se declaran y la incoherencia solo se señala | Corregirla sería inventar. El error aritmético lo corrige la Comisión con una corrección motivada |
| OD-OMA-05 | La base de PROC-10 se trata por bandas, con NO_EVALUABLE en la zona ambigua | No hay PASS ni FAIL falsos mientras no se precise la base (OQ-OMA-02) |
| OD-OMA-06 | REP-03 suma solo las ofertas adjudicadas y separa por moneda | La adjudicación es de la oferta completa (OBS-PROC08-PARCIAL-01 sigue abierta). Sumar monedas sería falso |
| OD-OMA-07 | Capacidad propia `amount`, separada de `receive` | La declaran el receptor (sin sello) o la Comisión (tras la apertura). El ente decide a quién se la concede |

## Preguntas abiertas que este delta NO decide

- **OQ-OMA-01** (dueña). La regla para comparar el monto de la oferta con el límite de la competencia del firmante (ORG-03 `limit_amount`): qué monto, si bloquea o avisa y qué pasa con otra moneda. Hasta entonces, PROC-08 muestra el monto y no valida límites.
- **OQ-OMA-02** (profesional del derecho). Si «porcentaje de la oferta presentada» (RLCP art. 135) se calcula sobre el total con tributos o sin ellos. Hasta entonces se evalúa por bandas.
- **OQ-PROC09-02, 03 y 04:** siguen abiertas.

## Constitution Gate

```text
OWNER_DECISION_PRESENT=1 (OQ-PROC09-01=A, 2026-11-14)
AMOUNT_AUTHORITY_CLEAR=1 (declarado en la oferta, con soporte)
MONETARY_SCALE_CLEAR=1 (NUMERIC(18,2), texto exacto, sin redondeo)
CURRENCY_CLEAR=1 (MONEDAS_LIMITE, sin conversión)
DOCUMENT_SUPPORT_CLEAR=1 (documento de la oferta o acta de apertura)
CONFIDENTIALITY_CLEAR=1 (sellada: solo tras la apertura)
SEALING_BOUNDARY_CLEAR=1 (frontera = evaluación concluida)
LEGACY_BEHAVIOR_CLEAR=1 (NO_DECLARADO, sin backfill)
MATERIAL_DECISION_REQUIRED=0 (OQ-OMA-01 y OQ-OMA-02 se declaran sin construir)
CONSTITUTION_GATE=PASS
```

## Plan

**Ficheros:**

| Capa | Ficheros |
|---|---|
| Modelo | `models.py`: `GovernmentProcurementOfferAmount` y su DDL de inmutabilidad |
| Migración | `0110_gov_proc06_monto_oferta.py`: tabla, disparadores y permiso concedido a FUNCIONAL_COMPLETO |
| Servicio | `service_ofertas_montos.py`, nuevo: declarar o corregir, estado, historia y soportes. Además, `service_ofertas._serializar_oferta` expone el monto |
| Esquemas y API | `schemas_ofertas.py` y `api_ofertas.py`: `POST .../ofertas/{oferta_id}/montos` |
| Registros | `setup/api.py`, `mfa_policy.py` y el catálogo de auditoría, con sus recuentos (catálogo 524→526, delegación 163→164, MFA sensibles 70→71) y la cabeza Alembic en las 3 pruebas |
| Consumidores | `service_garantias.py` (criterios de moneda y monto), `service_reporte_contrataciones.py` (monto y CSV) y `service_decision.py` (monto por oferta) |
| Frontend | `OfertaMonto.tsx`, nuevo, más `ExpedienteOfertas.tsx`, `ExpedienteDecision.tsx` y `ReporteContratacionesPage.tsx` |
| Pruebas | `test_gov_proc06_montos.py`, nuevo, más los ajustes en las pruebas de REP-03, con Vitest y E2E |

**Llamadas previstas a DeepSeek, por frontera semántica (5 de un tope de 8):**
- A, backend núcleo;
- B, consumidores;
- C, pruebas de backend;
- D, frontend;
- E, E2E.
