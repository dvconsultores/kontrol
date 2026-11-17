# Motor normativo · baseline de arquitectura (GOV-ROADMAP-REBASELINE-02)

**Autoridad sobre:** cómo se representan, versionan, verifican y aplican las normas y las reglas que de ellas derivan.

- **Estado:** diseño de referencia; no se implementa en este ciclo.
- **Relación con lo existente:** desarrolla la sección «Normative Versioning» de `government-architecture-baseline.md` (`NormativeSource`, `NormativeVersion`, `RuleBinding`, `TenantPolicy`) y respeta el registro de fuentes `kontrol-gobierno-source-register.md`, que sigue siendo la autoridad sobre el corpus N01..N40 y sus clases A/B/C.

## 1. Entidades

| Entidad | Contenido | Notas |
|---|---|---|
| `Jurisdiction` | NACIONAL, ESTADAL, MUNICIPAL, ENTE | Jerarquía fija de producto (es invariante, §3) |
| `EntityType` | Tipo de ente: alcaldía, gobernación, instituto autónomo, fundación, servicio autónomo… | Determina qué instrumentos aplican; lo elige el ente en ORG-01 |
| `NormativeSource` | Código N.., título, emisor, jurisdicción y clase A/B/C | Una fila por instrumento del corpus |
| `NormativeInstrument` | Ley, reglamento, providencia, instructivo, ordenanza o acto interno | El acto interno del ente es un instrumento de nivel ENTE |
| `NormativeVersion` | Gaceta u otro identificador, `effective_from` / `effective_to`, `source_hash` (SHA-256 de la copia custodiada), fecha de obtención y `verification_status` | Estados: `VERIFIED`, `PENDING_PIN`, `SUPERSEDED` |
| `NormativeRule` | Regla atómica derivada: qué exige, a qué proceso y etapa aplica, parámetros y tipo | Tipo `LEGAL_MANDATORY` o `INSTITUTIONAL_POLICY` (ver la política de parametrización §4) |
| `RuleBinding` | Regla → `ProcessVersion` / `TransitionDefinition` / `ControlRule`, con vigencia | Conecta el motor normativo con el de procesos |

## 2. Verificación

- **`VERIFIED`** (clase A/B con copia custodiada y hash): la regla `LEGAL_MANDATORY` está **activa** y protegida.
- **`PENDING_PIN`** (clase C o sin copia): la regla legal se muestra como «pendiente de verificación» y **no se impone como ley**.
  - El ente puede adoptar el mismo contenido como `INSTITUTIONAL_POLICY`, rotulado como adoptado por el ente, con fundamento y responsable.
  - Cuando llegue la copia oficial, la regla legal pasa a `VERIFIED` y la política del ente queda sujeta a ella.
- **`SUPERSEDED`:** la versión deja de regir desde `effective_to`. Las instancias que empezaron bajo ella conservan la evidencia de qué regla aplicó.

## 3. Jerarquía

```text
NACIONAL → ESTADAL → MUNICIPAL → ENTE → POLÍTICA INTERNA
```

- Una regla inferior **no puede neutralizar** una obligación superior. Al publicar una versión de política o de proceso, el motor la valida contra las reglas superiores vigentes y rechaza la publicación si debilita una obligación `LEGAL_MANDATORY` activa.
- La regla inferior **sí puede endurecer** la superior: más documentos, menor umbral o un plazo interno más corto.
- **Conflictos entre normas del mismo nivel o entre ley y reglamento** (p. ej. PROC-09: 3 % LCP art. 31 frente a 1-5 % RLCP art. 35):
  - el motor **no los resuelve**; se registran como `NORMATIVE_CONFLICT`;
  - hace falta validación jurídica (`FUNCTIONAL_LEGAL_VALIDATION`) antes de activar la regla;
  - el proceso queda `NORMATIVE_VALIDATION_PENDING`.

## 4. Valores normativos con procedencia

Los valores que cambian por acto oficial (U.T., alícuotas o tasas oficiales):
- se registran como parámetros versionados con procedencia: fuente, gaceta, fecha y hash, siguiendo el patrón ya publicado de TRE-09 (tasas BCV con procedencia);
- nunca son constantes en el código.

## 5. Evidencia

Cada decisión que aplicó una regla guarda qué `NormativeVersion` y qué `NormativeRule` estaban vigentes. Así la auditoría (CTL-04, DOC-08) reproduce el porqué de una transición años después.

## 6. Paquete normativo por tenant

- Biblioteca §6: el ente tiene un **paquete normativo**, es decir, las versiones aplicables según su `EntityType` y su jurisdicción, más sus instrumentos internos.
- Para Naguanagua, las ordenanzas y la Gaceta Municipal (N37, clase C) son instrumentos MUNICIPAL/ENTE de **su** paquete.
- Nada de N37 entra en el código del producto.
