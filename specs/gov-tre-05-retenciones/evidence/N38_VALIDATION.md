# TRE-05 · Validación normativa N37 y N38 (2026-11-20)

## Qué dice el catálogo

- **N38 (Biblioteca Normativa Oficial v1.0):** «Normativa tributaria aplicable a retenciones del ente público». Remite al COT, IVA, ISLR y a las providencias SENIAT vigentes según la operación.
  - Es de clase **C**.
  - Impacto: retenciones, comprobantes y obligaciones fiscales del pagador, con reglas versionadas y sin alícuotas hardcodeadas sin vigencia.
  - Acción pendiente antes del freeze: obtener una copia oficial y archivarla con hash.
- **N37:** ordenanzas y normativa local de cada organismo, clase **C**. Hay copias custodiadas para el piloto Naguanagua en `requerimientos/gobierno/normativa-n37-naguanagua/`.

## Fuentes localizadas

| Fuente | Custodia | Hash (SHA-256) | Vigencia | Jurisdicción |
|---|---|---|---|---|
| N38: COT, Ley de IVA, Ley de ISLR y su reglamento de retenciones, providencias SENIAT | **Ninguna copia custodiada** | — | No verificable | Nacional |
| N37: Gaceta Municipal Naguanagua 512 Ext. (10-12-2025), Ordenanza de Reforma Parcial de Actividades Económicas | Custodiada | `563f37fc…6619737` | CURRENT_CONFIRMED (inventario de N37) | Municipio Naguanagua |

## Lectura de la Gaceta 512 (N37)

- **Art. 8.2 y art. 10:** los agentes de retención designados por la ordenanza son sujetos pasivos en calidad de responsables.
- **Art. 14 a 18:**
  - Solo los **sujetos pasivos especiales** están obligados a retener el impuesto en sus operaciones con sociedades mercantiles, y declaran la retención dentro de los 15 días continuos del mes siguiente.
  - Son personas jurídicas calificadas por resolución del Director de Hacienda, por ingresos ≥ 312 veces la moneda de mayor valor publicada por el BCV.
  - La alícuota es la del Clasificador de Actividades Económicas.
- **Art. 120:** los instructivos sobre agentes de retención se delegan en actos del Alcalde. No están custodiados.
- **Art. 123 y anexo:** el Clasificador Armonizado trae alícuotas (p. ej., 3 %) y mínimos tributarios por actividad.
- **Conclusión:** la Gaceta 512 **no designa a la Alcaldía como agente de retención de sus propios pagos**. Sus alícuotas son del impuesto municipal, no una regla de retención del pagador público. No se precargan.

## Reglas evaluadas

| RULE | SOURCE | ARTICLE/REFERENCE | SOURCE_CLASS | JURISDICTION | APPLICABILITY | EFFECTIVE_FROM | EFFECTIVE_TO | BASE | RATE | THRESHOLD | EXCLUSIONS | DOCUMENT/RECEIPT | PRODUCT_REPRESENTATION | HARD_CODED? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Retención de IVA por el ente público | N38 (sin copia) | — | C | Nacional | No verificable | — | — | — | — | — | — | — | Regla del ente: política `INSTITUTIONAL_POLICY`, `PENDING_PIN`, con fuente declarada | NO |
| Retención de ISLR por el ente público | N38 (sin copia) | — | C | Nacional | No verificable | — | — | — | — | — | — | — | Ídem | NO |
| Retención del impuesto municipal de actividades económicas | N37 Gaceta 512 | arts. 14–18, 120, 123 | C | Naguanagua | Obliga a sujetos pasivos especiales; la Alcaldía como pagador, no verificado | 2025-12-10 | — | Ingreso bruto de la operación (art. 18) | Clasificador (anexo), por actividad | 312 × moneda BCV para calificar (no es un umbral de retención) | — | Declaración en 15 días (no es un comprobante) | Regla del ente si la adopta, con fuente «Gaceta 512 art. …» y umbral `MULTIPLO_TASA` si lo necesita | NO |
| Retención contractual | Contrato o acto del ente | — | — | Ente | La configura el ente | — | — | — | — | — | — | — | Concepto CONTRACTUAL con fuente; sin leer cláusulas (CNT-06) | NO |

## Representación en el producto

- **Ninguna regla es `LEGAL_MANDATORY`.** El servicio rechaza ese tipo mientras `estado_verificacion` no sea `VERIFIED`, y este ciclo no abre una vía para fijarlo (`GOV_WITHHOLDING_LEGAL_SOURCE_UNVERIFIED`).
- **Lo que configura el ente:** conceptos, condiciones, alícuotas, bases, umbrales, sustraendos, topes, exclusiones, comprobantes y redondeo. Cada política lleva su fuente (descripción, referencia y documento opcional) y se rotula «adoptada por el ente; verificación normativa pendiente».
- **Valores:** el producto no trae ningún valor precargado.
- **Umbrales en unidades:** se expresan como múltiplo de una tasa oficial TRE-09 (N39, clase A), congelada en el cálculo. No se crea un maestro de unidad tributaria.
- **Cumplimiento:** no se afirma cumplimiento fiscal general.

```ini
N37_VALIDATION=DONE (1 fuente custodiada; 0 reglas de retención del pagador verificadas)
N38_VALIDATION=DONE (0 fuentes custodiadas; 0 reglas verificadas)
MATERIAL_NORMATIVE_UNKNOWN=YES (toda alícuota, base, umbral y exclusión → configuración del ente con procedencia)
MATERIAL_DATA_GAP=YES (beneficiario sin datos fiscales → declaración por liquidación, OD-TRE05-01)
N37_HARDCODED_RULES=0
N38_HARDCODED_RULES=0
```
