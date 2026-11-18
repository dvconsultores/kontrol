# Auditoría de hardcode · PROC-07/PROC-08-COMMISSION-POLICY (2026-11-17)

**Alcance:** los 32 ficheros de código del ciclo (backend y frontend), sin pruebas, E2E ni el script excluido.

## Búsquedas literales

| Búsqueda | Resultado |
|---|---|
| `naguanagua\|alcald\|gobernaci\|ayuntamiento\|municipio de` | 0 apariciones |
| `director\|contralor\|consultor jur\|síndico\|sindico\|alcalde` | 0 apariciones |
| `// 2 + 1`, `/ 2) + 1`, `quorum = <n>`, `members_required`, `miembros_requeridos = <n>` | 1 aparición, en `service_comision_regla.py:303` (ver abajo) |
| `Math.floor(... / 2)` en `src/modules/gobierno` | 0 apariciones. Se eliminaron las 2 anteriores, de `ExpedienteEvaluacion.tsx` y `ExpedienteDecision.tsx` (H1 en el frontend) |
| `min_principales = <n>`, `max_principales = <n>`, `== 3`, `quorum_cantidad = <n>` en los servicios | 0 apariciones |

## Clasificación de lo que queda

| Elemento | Dónde | Clase | Por qué no es hardcode institucional |
|---|---|---|---|
| `base // 2 + 1` | `umbral()`, rama `SIMPLE_MAJORITY` | PLATFORM_INVARIANT | Es la definición de la opción «mayoría simple». El ente la elige entre cuatro tipos (cantidad fija, simple, calificada n/d, unanimidad) en su política. |
| `AREAS_COMISION` (jurídica, técnica, económico financiera) | `PISO_LCP_ART14` | LEGAL_MANDATORY | Es la LCP art. 14, una ley nacional con fuente verificada, guardada con versión `LCP-2014+RLCP-2009`. Solo aplica si la política declara la base `LCP_ART14`; con `NINGUNA` no hay piso. |
| `REGLA_LEGADO` (mayoría simple sobre los miembros con voto) | `service_comision_regla.py` | Regla histórica | Es la regla con la que se activaron las comisiones anteriores a las políticas (OD-PROC07-01 y OD-CP-04), mostrada de forma explícita. Las comisiones nuevas exigen una política. |
| Funciones MIEMBRO y SECRETARIO; condiciones PRINCIPAL y SUPLENTE; presidencia | Modelos | PLATFORM_INVARIANT | Son roles genéricos de producto, no cargos institucionales. Los requisitos por cargo, unidad, competencia o funcionario son datos de la política. |
| «Quien registró la comisión no puede activarla» | `service_comisiones.activar` | Deuda declarada | Es un control de cuatro ojos que ya existía. Pasarlo a CTL-01 cambiaría el comportamiento actual: deuda `OBS-PROC02-SELF-ACTIVATION-CTL01-01`, fuera del alcance de este ciclo. |

## Resultado

| Indicador | Valor |
|---|---|
| ZERO_INSTITUTIONAL_HARDCODE | 1 |
| TENANT_CONFIGURABLE | 1 |
| NATIONAL_REUSABLE_PRODUCT | 1 |
| NAGUANAGUA_SPECIFIC_CODE | 0 |
| TENANT_SPECIFIC_CODE | 0 |
