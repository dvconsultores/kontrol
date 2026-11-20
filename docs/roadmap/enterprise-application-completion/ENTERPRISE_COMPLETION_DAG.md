# KONTROL Enterprise · DAG de cierre

Ciclo `P3-ENTERPRISE-REBASELINE-AND-COMPLETION-MATRIX` · 2026-11-20. Se construye sobre la matriz `ENTERPRISE_REQUIREMENTS_REBASELINE.csv` y el registro `ENTERPRISE_CURRENT_DEFECTS.md`.

**Reglas del DAG**
- Cada nodo es una **vertical funcional completa**: backend, frontend, menú, permisos, auditoría, pruebas, E2E en PostgreSQL y tarjeta de la dueña. Nunca es una pantalla.
- No se asigna un nodo cuyas aristas de entrada no estén satisfechas.
- `◆` marca un nodo que necesita antes una decisión de la dueña o de ChatGPT (`OWNER_OR_CHATGPT_DECISION_REQUIRED`). Sin ella, el nodo no arranca.
- **Prioridad (§31 del encargo):**
  - P0: PRODUCT_DEFECT;
  - P1: NOT_BUILT que bloquea;
  - P2: PARTIAL con hueco funcional;
  - P3: COMPLETE sin UAT de la dueña;
  - P4: validación del sponsor;
  - P5: deuda no bloqueante.

## Grafo

```text
                       ┌──────────────────────────────┐
                       │ D0 Decisiones de la dueña    │  ◆ escala de tasa, VED, maker-checker,
                       │ (bloque de decisiones)       │    alcance vacío, anulación de factura
                       └──────────────┬───────────────┘
              ┌───────────────────────┼─────────────────────────┬──────────────────────┐
              ▼                       ▼                         ▼                      ▼
   V1 FISCAL-EMISSION-INTEGRITY  V4 INVENTORY-LEDGER-        V6 TENANT-SCOPE-AND-   V9 MASTERS-COMMERCIAL
      (P0, S1) ◆                   VALUATION-INTEGRITY         SEGREGATION (P0, S1) ◆   COMPLETION (P2) ◆
              │                    (P0, S1)                       │                      │
              ▼                       │                           │                      │
   V2 RECEIVABLES-PAYABLES-           │                           │                      │
      APPLICATION-INTEGRITY ◄─────────┼───────────── V7 TREASURY-CASH-BANK-INTEGRITY (P0, S1)
      (P0, S1)                        │                           │
        │        │                    │                           │
        │        └──────────┐         │                           │
        ▼                   ▼         ▼                           │
   V5 PROCURE-TO-PAY    V3 ORDER-TO-CASH-STATE-INTEGRITY ◄─────────┘ (maker-checker del crédito)
      COMPLETION (P0/P2)    (P0, S1/S2)
        │                   │
        │                   ▼
        │            V8 REGULATED-DISPATCH-MATCHING (P0, S2) ◆
        ▼                   │
   V10 IMPORTS-OWNER-UAT-READY (P0 IMP-28 + P2 IMP-21 + A11Y + P4 Zonas A–E ◆)
                            │
                            ▼
   V11 REPORTING-DASHBOARD-CURRENCY (P0 D-DASH-CCY, P2)   V12 SPEC057 FIXED ASSETS (P1 nuevo alcance ◆, sin dependencias de Enterprise operativo)
```

## Nodos

| Nodo | Prioridad | Requisitos | Defectos que cierra | Depende de | Decisión previa |
|---|---|---|---|---|---|
| **D0** Decisiones | — | — | — | — | Escala de tasa: porcentaje o fracción (D-RATE-SCALE). Moneda funcional configurable en vez de «VED» fijo. Si la factura emitida se anula o solo admite nota de crédito. Qué excepciones llevan maker-checker que no se puede apagar. Si un usuario sin alcance ve todas las empresas o ninguna. Política de crédito y exposición. Valoración de RECHAZADO. Backfill DISPATCH-COST-RELIEF-HISTORICO. Zonas A–E |
| **V1** FISCAL-EMISSION-INTEGRITY | P0 S1 | FMA-02..07, FMA-10, FIS-01..07, FIS-10, FIS-12, TRV-05, TRV-09 | D-FIS-NUM-RACE, D-FIS-CTRL-OVERLAP, D-RATE-SCALE, D-FIS-RATE-1, D-SALES-EMIT-BYPASS, D-FIS-NOTE-BYPASS, D-FIS-EMIT-ANY-STATE, D-FMA-VALIDITY, D-FIS-PRINT, D-PERIOD-NO-EFFECT | D0 (escala de tasa, anulación) | ◆ |
| **V2** RECEIVABLES-PAYABLES-APPLICATION-INTEGRITY | P0 S1 | CXC-01..10, CXP-01..07, VEN-12, VEN-13 | D-APPLY-UNCHECKED, D-WHT-REAPPLY, D-CXC-DRAFT-NOTE, D-CXP-POST-NO-TREASURY, D-CXP-AGING, D-CXC-DUE-DATE | V1 (retención y nota fiscal correctas), V7 (el pago pasa por tesorería) | Diferencial cambiario: política y tasa |
| **V3** ORDER-TO-CASH-STATE-INTEGRITY | P0 S1/S2 | VEN-03..16, PED-01..09 | D-ORDER-BYPASS, D-ORDER-CANCEL-INVOICED, D-SHIP-CLIENT-LINES, D-PICK-CORRECTION-DEADEND, D-DISCOUNT, D-PRICE-LIST; UI de picking con SKU y ubicación (PED-03) | V1 (factura única con numeración), V2 (CxC), V6 (maker-checker del crédito) | Factura antes del despacho configurable por empresa. Despacho parcial ante faltante |
| **V4** INVENTORY-LEDGER-VALUATION-INTEGRITY | P0 S1 | INV-01, INV-05..13, INV-15..18 | D-INV-TRANSFER-COST, D-INV-REVERSE-STATE, D-INV-RECOMPUTE, D-INV-ADJ-NO-APPLY, D-INV-COUNT-STUCK, D-INV-TRANSFER-RECEIPT, D-INV-LEDGER-LOT, D-APPROVAL-QTY-AS-VED | — (independiente) | Valoración de RECHAZADO (INV-16). Destinos de devolución (INV-12). Política de congelamiento. Backfill histórico (INV-15) |
| **V5** PROCURE-TO-PAY-COMPLETION | P0/P2 | CMP-02..05, CMP-07, CMP-08, CMP-10..17 | D-3WAY-TAX, D-PO-SYNC, D-RET-LINE; triple match con pantalla y resolución; retenciones practicadas ligadas a la factura y al pago; devolución con máquina y movimiento; notas de proveedor aplicadas | V2, V1 | Tolerancias del triple match. Presupuesto de la requisición. Categoría y excepción de la OC |
| **V6** TENANT-SCOPE-AND-SEGREGATION | P0 S1 | SEG-02, SEG-03, SEG-04, SEG-06, APR-03..07, PRD-11 | D-PROFILE-XCOMPANY, D-APPROVAL-ROLE-TENANT, D-PAY-SELF-APPROVE; UI de alcances de usuario; edición de roles; sesiones de otros usuarios | D0 (alcance vacío, maker-checker) | ◆ |
| **V7** TREASURY-CASH-BANK-INTEGRITY | P0 S1 | TES-01..09, FIN-01..06 | D-TES-ARQUEO, D-TES-CCY, D-TES-TRANSFER, D-TES-RECON, D-TES-IGTF-500, D-IDEMP | D0 (moneda funcional) | Hechos y base del IGTF (fuente fiscal) |
| **V8** REGULATED-DISPATCH-MATCHING | P0 S2 | REGM-01..06, REG-01..09 | D-REG-GUIDE, D-REG-PROFILE, D-REG-HASH; vencimientos con alertas | V3 (despacho íntegro) | Rubros obligatorios, quién anula un bloqueo, contingencia ◆ |
| **V9** MASTERS-COMMERCIAL-COMPLETION | P2 | ORG-02..10, TER-03, TER-06, TER-09, PRD-*, COM-01..08 | D-RIF, D-CUST-DECORATIVE, D-PRD-ROUTE, D-SERVICES-LIST, D-UOM-LEGACY, D-WIZARD, D-EST-ISSUANCE; centros de costo (DT-04), unidades de negocio, marcas, modelos, plantillas, comisiones | — | Centros de costo (DT-04), precedencia de precios, comisiones, autoridad de conductores ◆ |
| **V10** IMPORTS-OWNER-UAT-READY | P0 + P2 + P3 + P4 | IMP-01..42, CMP-06, CMP-09 | D-IMP-PARTIAL-ACCEPTED; evidencia en la incidencia (IMP-21); A11Y-IMPORT-SCROLL-REGIONS | V4 (costo de la transferencia y valoración de la recepción). Hoy no depende de V1 ni de V2 | Zonas A–E (P4) ◆ |
| **V11** REPORTING-DASHBOARD-CURRENCY | P0/P2 | INI-01, INI-02, INI-05, INI-06, RPT-01..05 | D-DASH-CCY, D-RPT-JOB; vencimientos consolidados | V1, V2 (cifras fiables) | Indicadores por rol y moneda de presentación |
| **V12** SPEC057 FIXED ASSETS | P1 (alcance nuevo) | AF-01..05 | — | Ninguna operativa. La integración contable espera el libro mayor (043, no construido) | Priorización y marco contable ◆ |

## Orden de ejecución propuesto (sujeto a ChatGPT y a la dueña)

1. **D0:** paquete de decisiones de la dueña. No es código.
2. **V4:** es independiente de D0 en lo esencial: los defectos de costo y permisos no esperan decisión, y las que lo hacen se aíslan.
3. **V1:** en cuanto D0 fije la escala de tasa y la anulación.
4. **V7.**
5. **V6:** en cuanto D0 resuelva el alcance vacío y el maker-checker. Puede ir en paralelo a V4.
6. **V2:** tras V1 y V7.
7. **V3:** tras V1, V2 y V6.
8. **V5:** tras V1 y V2.
9. **V10:** cierra Importaciones hasta OWNER_UAT_READY. Requiere V4 por el costo.
10. **V8, V11, V9 y V12.**

`DEPENDENCY_DAG_CREATED=YES`. Ningún nodo se asigna con aristas pendientes. Los nodos `◆` no arrancan sin su decisión.
