# Auditoría de hardcode · CTL-09-DELIVERY-ACT-POLICY (2026-11-18)

**Alcance:** el código del ciclo, sin pruebas ni E2E:
- backend: `service_actas.py`, `service_actas_regla.py`, `service_actas_politicas.py`, `api_actas.py`, `api_actas_politicas.py`, `schemas_actas.py`, `schemas_actas_politicas.py` y los modelos de actas;
- frontend: `src/modules/gobierno/actas/*`.

## Búsquedas

| Búsqueda | Resultado |
|---|---|
| `ANEXOS_CATALOGO`, `ANEXOS_MUNICIPALES` | 0. Eliminados: los sustituye el catálogo legal versionado `SUPUESTOS` |
| `naguanagua` | 0 |
| `alcald`, `hacienda`, `MUNICIPAL`, `A17_` | Solo en `service_actas_regla.SUPUESTOS[N34_ART17]` (sujeto, niveles en que se declara y anexos) y en el aviso OD-AE-02. Ninguna condición `if MUNICIPAL` decide los anexos |
| `A11_` | El catálogo `SUPUESTOS[N34_ART11]` y los generadores de contenido de `service_actas._contenido_anexo` (A11_1, A11_2, A11_5): son lo que KONTROL sabe generar con datos al corte, no qué se exige |
| `AE-` | Solo en `PATRON_POR_DEFECTO`, la configuración operativa por defecto (OD-AE-04), y en referencias `D-AE-*` de los comentarios |
| `timedelta`, días | Solo en `plazos()`, que calcula el vencimiento de los plazos **internos** en días continuos; los valores salen de la regla. Los legales (3, 5 y 120 días hábiles) están en `PLAZOS_LEGALES`, con fuente |
| Testigos «2» | Solo en `TESTIGOS_LEGALES` (art. 9). El mínimo en la entrega sale de la política |
| Artículos en la UI | 0. «N34 art. {articulo}» se arma con el dato de la regla. La frase «Solo rige el art. 11» se reemplazó por un texto neutro |
| Nombre de cargo para la autoridad | 0. La máxima autoridad la da ORG-04 (suplencia) o el **código** de cargo que declara la política (D-AE-14) |

## Clasificación

| Elemento | Clase | Por qué no es hardcode institucional |
|---|---|---|
| `SUPUESTOS` (arts. 11–17), `TESTIGOS_LEGALES` (art. 9), `PLAZOS_LEGALES` (arts. 4, 21 y 22) | LEGAL_MANDATORY | N34 verificada en la copia custodiada (ver `N34_VALIDATION.md`). Versión `N34-2009`, con vigencia y fuente en cada elemento |
| Niveles en que se puede declarar cada supuesto (art. 15 NACIONAL, art. 16 ESTADAL, art. 17 MUNICIPAL) | LEGAL_MANDATORY | Literal de los artículos. Que el ente lo declare no se infiere |
| Vínculos, requisitos con evidencia, testigos en la entrega, plazos internos y cargo de máxima autoridad | INSTITUTIONAL_POLICY | `gov_handover_policies` y tablas hijas: el ente los configura con versiones e historia |
| Patrón de numeración y su valor por defecto | OPERATIONAL_CONFIGURATION | Política del ente; por defecto el formato previo (OD-AE-04) |
| Saliente que ejerce al corte, receptor distinto del saliente, una acta por ocupación, acta suscrita congelada y aislamiento | PLATFORM_INVARIANT | Integridad del dominio |

## Resultado

| Indicador | Valor |
|---|---|
| ZERO_INSTITUTIONAL_HARDCODE | 1 |
| TENANT_CONFIGURABLE | 1 |
| NATIONAL_REUSABLE_PRODUCT | 1 |
| HARDCODED_A17_GLOBAL | 0 |
| HARDCODED_DOCUMENT_POLICY | 0 |
| HARDCODED_WITNESS_POLICY | 0 |
| HARDCODED_INSTITUTIONAL_DEADLINES | 0 |
| HARDCODED_NUMBERING | 0 |
| NAGUANAGUA_SPECIFIC_CODE | 0 |
