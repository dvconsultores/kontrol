# Validación normativa · N34 (CTL-09-DELIVERY-ACT-POLICY)

## Fuente

| Campo | Valor |
|---|---|
| Norma | Normas para Regular la Entrega de los Órganos y Entidades de la Administración Pública y de sus Respectivas Oficinas o Dependencias |
| Instrumento | Resolución CGR Nº 01-00-000162, del 27-07-2009 |
| Publicación | G.O. 39.229 (28-07-2009) |
| Vigencia | Desde su publicación (art. 29); deroga la Res. Nº 01-00-247 de 2005 (art. 28). Sin derogación posterior conocida |
| Copia custodiada | `requerimientos/gobierno/normativa-n34/N34_GO_39229_Res_CGR_01-00-000162_copia_CEBM.pdf` |
| SHA-256 | `436856805eabb9f80a85f30610adf09eeaf3f8b5793e7245dd5bd76800d5cd90` |
| Procedencia | cebm.gob.ve, página «Normas», descargada el 2026-11-18. La Biblioteca Normativa Oficial (N34, clase A) remite a esa misma fuente |

## Reglas

| Regla | Artículo | Clase | Aplicabilidad verificada en el texto | Vigencia | Representación en KONTROL | ¿En código? |
|---|---|---|---|---|---|---|
| Toda acta lleva los anexos 1–6 | 11 (con 5 y 10) | LEGAL_MANDATORY | Todo servidor de los órganos y entidades nacionales, estadales, distritales y municipales, institutos, personas de derecho público, sociedades y fundaciones con participación pública (art. 5). El art. 11 rige para el «órgano, entidad, oficina o dependencia» | 2009-07-28 – | `SUPUESTOS[N34_ART11]`, vínculo UNIVERSAL; anexos A11_1..A11_6 (A11_6 opcional) | Sí: catálogo legal versionado con fuente (piso estructural) |
| Unidad administradora | 12 | LEGAL_MANDATORY (sujeto declarado) | «El acta de entrega correspondiente a una unidad administradora». Los anexos remiten al Reglamento Nº 1 de la LOAFSP, que no está custodiado | 2009-07-28 – | `N34_ART12`, declarable en ENTE o UNIDAD, sin anexos enumerados: el ente define los requisitos (D-AE-04) | Solo el supuesto; **MATERIAL_NORMATIVE_UNKNOWN** para sus anexos |
| Ramos específicos | 13 | LEGAL_MANDATORY (sujeto declarado) | «Oficinas o dependencias … a quienes corresponda el manejo de ramos específicos» | 2009-07-28 – | `N34_ART13`, solo UNIDAD; A13_1 | Sí, declarable |
| Órganos de control fiscal | 14 | LEGAL_MANDATORY (sujeto declarado) | «Órganos de control fiscal» | 2009-07-28 – | `N34_ART14`, ENTE o UNIDAD; A14_1 | Sí, declarable |
| Ministerio de Finanzas | 15 | LEGAL_MANDATORY (sujeto declarado) | «Cuando el órgano a entregar sea el Ministerio de Finanzas» | 2009-07-28 – | `N34_ART15`, solo entes NACIONALES y ENTE; A15_1..A15_4 | Sí, declarable |
| Gobernación o hacienda estadal | 16 | LEGAL_MANDATORY (sujeto declarado) | «Gobernación, oficina o dependencia de hacienda estadal» | 2009-07-28 – | `N34_ART16`, solo entes ESTADALES, ENTE o UNIDAD; A16_1..A16_3 | Sí, declarable |
| **Alcaldía o Dirección de hacienda** | **17** | LEGAL_MANDATORY (sujeto declarado) | «Acta de entrega correspondiente a una **Alcaldía o Dirección de hacienda distrital o municipal**». No a todo ente municipal: ni a un instituto, una fundación, un Concejo o una Contraloría municipal. La Dirección de hacienda es una **dependencia** | 2009-07-28 – | `N34_ART17`, solo entes MUNICIPALES, ENTE (Alcaldía) o UNIDAD (Dirección de hacienda); A17_1..A17_5 | Sí, declarable (OD-AE-01). **El defecto P0 era inferirlo del nivel** |
| Corte al cese | 18 | LEGAL_MANDATORY | Toda acta | 2009-07-28 – | Fecha de corte; el saliente debe ejercer ese día (ORG-04, D-AE-08) | Invariante del servicio |
| Constancia si falta información | 19 | LEGAL_MANDATORY | Toda acta y anexo | 2009-07-28 – | La constancia resuelve cualquier anexo (`anexo_resuelto`) | Sí |
| Errores y deficiencias | 20 | LEGAL_MANDATORY | Toda acta | 2009-07-28 – | Campo al suscribir (ya existía) | Sí |
| Dos testigos y auditor si levanta el receptor | 9 | LEGAL_MANDATORY | Acta que levanta quien recibe porque el saliente no la hizo | 2009-07-28 – | `TESTIGOS_LEGALES`; la política solo puede exigir además testigos en la entrega por el saliente | Sí, con fuente |
| Entrega en la toma de posesión o en 3 días hábiles | 4 | LEGAL_MANDATORY | Toda acta | 2009-07-28 – | `PLAZOS_LEGALES[ELABORACION]`, días hábiles, sin vencimiento calculado: no hay calendario hábil oficial (DOC-03) | Sí, informativo |
| Copia a la UAI en 5 días hábiles | 21 | LEGAL_MANDATORY | Toda acta | 2009-07-28 – | `PLAZOS_LEGALES[REMISION_UAI]` | Sí, informativo |
| Observaciones en 120 días hábiles | 22 | LEGAL_MANDATORY | Quien recibe | 2009-07-28 – | `PLAZOS_LEGALES[OBSERVACIONES]` | Sí, informativo |
| Máxima autoridad entrega el órgano; los jefes, su dependencia | 6 | LEGAL_MANDATORY | Órganos y entidades del art. 5 | 2009-07-28 – | Ámbito ENTE si suple a la máxima autoridad o si ocupa el cargo declarado en la política (D-AE-14); si no, UNIDAD | El criterio sí; el cargo es dato del ente |

## Lo que la fuente no permite afirmar

- **Que «municipal» equivalga a «Alcaldía».** El art. 17 nombra al órgano. Los datos del ente no lo identifican, así que lo declara el ente (OD-AE-01).
- **Los anexos del art. 12:** su fuente, el Reglamento Nº 1 de la LOAFSP, no está custodiada.
- **El nivel DISTRITAL:** KONTROL no lo modela (`NIVELES_TERRITORIALES`). El art. 17 se admite en entes MUNICIPALES; el distrital queda como deuda (OBS-AE-DISTRITAL-01).
