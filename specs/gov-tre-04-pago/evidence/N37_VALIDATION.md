# TRE-04 · Validación N37 (2026-11-18)

## Qué es N37

- **Ficha (Biblioteca Normativa v1.0):** «Ordenanzas, leyes presupuestarias y manuales internos de cada organismo». Referencia: gaceta estadal o municipal, o el acto administrativo aplicable. **Clase C**; fuente local por tenant.
- **Impacto declarado:** parametrización local obligatoria (niveles de aprobación, pagos, piezas justificativas, procedimientos internos).
- **Controles derivados de la ficha:** configurar reglas por tenant, exigir documento o acto fuente y vigencia, y no propagar una regla local a otros organismos.
- **Requisitos que la citan para TRE-04:** GOV-TRE-005 (N05, N37), sobre los medios autorizados con referencia bancaria y fecha valor. GOV-TRE-004 (N05, N20, N23) y GOV-TRE-010 (N20, N23) no citan N37.

## Fuentes verificadas

| Fuente | Clase | Qué dice para TRE-04 |
|---|---|---|
| N05, Reglamento N.º 3 de la LOAFSP (G.O. 38.433) | A | Controles derivados: «Maker-checker de pagos y conciliación bancaria»; «Trazabilidad de orden de pago a causado/compromiso» |
| N20, Normas Generales de Control Interno (G.O. 40.851) | A | Segregación de funciones y auditoría append-only |
| N23, Ley contra la Corrupción (G.O. 6.699 Ext.) | A | Trazabilidad y responsabilidad |
| Copias del piloto en `requerimientos/gobierno/normativa-n37-naguanagua/` | C | La Gaceta Municipal 512 Ext. es una reforma de la ordenanza de actividades económicas (tributos). La LEFP trata de función pública. La copia de la LOPPM es una imagen sin texto extraíble y no se cita. Ninguna fija medios de pago, número de firmantes ni límites por monto |

## Reglas

| RULE | CLASSIFICATION | SOURCE | SOURCE_CLASS | APPLICABILITY | PRODUCT REPRESENTATION | HARD_CODED? |
|---|---|---|---|---|---|---|
| Separar quien prepara de quien autoriza el pago | PLATFORM_INVARIANT | N05, GOV-TRE-004 | A | Todos los entes | Maker ≠ checker por identidad en el servicio | Sí: es invariante de plataforma, no regla local |
| Pagar solo órdenes emitidas y nunca más de lo ordenado | PLATFORM_INVARIANT | N05, GOV-TRE-012 | A | Todos | Proyección única + bloqueo `FOR UPDATE` | Sí (invariante) |
| Historia y auditoría append-only | PLATFORM_INVARIANT | N20, N23 | A | Todos | Historias e índices; disparadores PG | Sí (invariante) |
| Bloquear duplicados | PLATFORM_INVARIANT (mecanismo) + INSTITUTIONAL_POLICY (respuesta al duplicado funcional) | GOV-TRE-010 (N20, N23) | A | Todos | Idempotencia y referencia única por medio; BLOQUEAR o ADVERTIR en la política | Solo el mecanismo |
| Qué medios de pago están autorizados | INSTITUTIONAL_POLICY | N37 | C · **UNVERIFIED** | Por ente | Catálogo de medios del ente + medios permitidos de la política, con `fundamento` | No |
| Si un medio exige referencia, si es única y su formato | OPERATIONAL_CONFIGURATION | N37 / banco | C · **UNVERIFIED** | Por ente y medio | Campos del medio | No |
| Cuántas autorizaciones y de qué competencia | INSTITUTIONAL_POLICY | N37 | C · **UNVERIFIED** | Por ente | Bandas con requisitos `{acción, materia, cantidad}` | No |
| Límites por monto | INSTITUTIONAL_POLICY | N37 | C · **UNVERIFIED** | Por ente, en la moneda de la política | Bandas `desde`/`hasta` | No |
| Firmantes autorizados de la cuenta | INSTITUTIONAL_POLICY | TRE-01 (acto del ente) | dato del ente | Por cuenta | `exige_cargo_autorizado_cuenta` + autorizaciones TRE-01 | No |
| Documentos por etapa | INSTITUTIONAL_POLICY | N37 | C · **UNVERIFIED** | Por ente | Documentos de la política por etapa | No |
| Pago parcial permitido | INSTITUTIONAL_POLICY | N37 | C · **UNVERIFIED** | Por ente | `permite_pago_parcial` | No |
| Competencia del preparador | INSTITUTIONAL_POLICY | N37 | C · **UNVERIFIED** | Por ente | Competencia opcional de la política | No |
| Numeración | OPERATIONAL_CONFIGURATION | — | — | Por ente | Patrón | No |

## Conclusión

- `N37_HARDCODED_RULES=0`: ninguna regla N37 se convierte en código.
- `N37_RULES_AS_VERSIONED_DATA=1`: cada regla local es un campo de una política versionada con vigencia.
- `N37_PROVENANCE_REQUIRED=1`: activar exige `fundamento` y admite un acto DOC-02 y la clase de regla.
- **La institución debe cargar y adoptar sus reglas:** medios, bandas, documentos y pago parcial. KONTROL no afirma que la configuración de un ente cumpla su normativa local; eso lo sostiene el acto o el fundamento que el ente registra.
- N37 sigue en clase C. Esta validación no la promueve.
