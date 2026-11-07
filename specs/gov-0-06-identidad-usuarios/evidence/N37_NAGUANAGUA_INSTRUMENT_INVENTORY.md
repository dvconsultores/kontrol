# N37_NAGUANAGUA_INSTRUMENT_INVENTORY

Investigación del 2026-11-07 para la Alcaldía del Municipio Naguanagua. N37_OWNER_DECISION_BLOCKER = 0. Hashes en `SOURCE_HASHES.txt`. Las reglas de Naguanagua son datos del ente, no reglas universales. Vigencia comprobada técnicamente; no es validación jurídica.

| TITLE | AUTHORITY | GAZETTE | DATE | OFFICIAL_SOURCE | SHA256 | VIGENCY | RELEVANT_ARTICLE | RULE | IMPACT |
|---|---|---|---|---|---|---|---|---|---|
| Ley Orgánica del Poder Público Municipal | Asamblea Nacional | G.O. 6.015 Ext. | 28-12-2010 | Portal de la Alcaldía, escaneada | Ver hashes | CURRENT_NOT_CONFIRMED; es la que publica la Alcaldía | 54, 56.h, 76, 78, 87, 88.3, 88.7 | Instrumentos jurídicos; estatuto por ordenanza; suplencia del alcalde; máxima autoridad de personal | ORG-04 |
| Ordenanza de Reforma Parcial de Actividades Económicas | Concejo Municipal | Gaceta Municipal 512 Ext. | 10-12-2025 | Portal de la Alcaldía | Ver hashes | CURRENT_CONFIRMED (reciente) | 119, 120 | Decreto reglamentario; acto delegatorio | Prueba de uso local |
| Ordenanza de expendio de bebidas alcohólicas | Concejo Municipal | Gaceta Municipal 096 Ext. | 02-02-2026 | Portal de la Alcaldía | Ver hashes | CURRENT_CONFIRMED (reciente) | Dirección de Hacienda | Nomina dependencias | Estructura parcial |
| Ordenanza sobre procedimientos de construcción | Concejo Municipal | Gaceta Municipal 482 Ext. | 14-11-2025 | Portal de la Alcaldía | Ver hashes | CURRENT_CONFIRMED (reciente) | Dirección de Planeamiento; Sindicatura | Nomina dependencias | Estructura parcial |
| Ordenanza de impuestos sobre espectáculos públicos | Concejo Municipal | Gaceta Municipal 051 Ext. | 19-01-2024 | Portal de la Alcaldía | Ver hashes | CURRENT_NOT_CONFIRMED | Dirección de Hacienda; Seguridad Ciudadana | Nomina dependencias | Estructura parcial |
| Ordenanza Heroínas de la Revolución | Concejo Municipal | Gaceta Municipal 128 Ext. | 11-03-2025 | Portal de la Alcaldía | Ver hashes | CURRENT_NOT_CONFIRMED | — | Sin efecto en ORG-04 | Ninguno |
| Ordenanza sobre Gaceta Municipal | Concejo Municipal | NOT_FOUND | 11-01-2007 | Citada en cada Gaceta | — | CURRENT_NOT_CONFIRMED | 7 | Lo publicado obliga, salvo disposición contraria | Documento pendiente |

## Normativa nacional del conjunto de reglas

| Instrumento | Gaceta | Copia | Artículos |
|---|---|---|---|
| N02 LOAP | G.O. 6.147 Ext., 17-11-2014 | SUSCERTE, escaneada | 34 a 37, 40, 41 |
| N32 LEFP | G.O. 37.522, 06-09-2002 | MPPPST | 1, 20, 70 a 73 |
| N25 LOPA | G.O. 2.818 Ext. | SUSCERTE | Forma del acto |

La LOAP vista en la Gaceta se aplicó a alcaldes porque su art. 34 los nombra. Su alcance completo en municipios no se midió.

## Estado

**N37_RESEARCH_STATUS = PUBLIC_SOURCES_PARTIAL.** Se revisó el portal de la Alcaldía completo. No se pudo acceder al del Concejo: `cmbnaguanagua.gob.ve` no resuelve por DNS, tampoco en resolutores públicos, y sus copias archivadas respondieron 429. Dos búsquedas amplias no hallaron estatuto ni instrumento de organización.

**N37_IMPLEMENTATION_RULESET_READY = 1 para ORG-04.** GOV-ORG-004 no cita N37; solo GOV-ORG-009 lo hace, por el catálogo de actos, y LOPPM art. 54 fija los instrumentos municipales. Las figuras, formalidades y límites salen de N02, N24 y N32. Lo local entra como **datos parametrizables, versionados y auditables**: actos concretos, cargos y plazos que el estatuto fije. Ninguna regla de Naguanagua se codifica.

N37 **sigue siendo bloqueo** de REQ-01, PROC-01, TRE-04, BUD-07, DOC-06 y otros: allí sí se necesitan manuales y procedimientos locales que no se hallaron.
