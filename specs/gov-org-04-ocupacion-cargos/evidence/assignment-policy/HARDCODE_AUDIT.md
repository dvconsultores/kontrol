# Auditoría de hardcode · ORG-04-AUTHORITY-ASSIGNMENT-POLICY (2026-11-18)

**Alcance:** el código del ciclo, sin pruebas ni E2E:
- backend: `service_ocupacion.py`, `service_asignacion_regla.py`, `service_asignacion_politicas.py`, `schemas_asignacion_politicas.py`, `api_asignacion_politicas.py`, `schemas_ocupacion.py`, `api_ocupacion.py` y `models.py` (ORG-04);
- frontend: `NuevaAsignacionPage.tsx`, `AsignacionPage.tsx`, `PoliticasAsignacionPage.tsx`, `PoliticaAsignacionPage.tsx`, `PoliticaAsignacionFormPage.tsx` y `politicasAsignacion.ts`.

## Búsquedas

| Búsqueda | Resultado |
|---|---|
| `naguanagua\|alcald\|gobernaci\|ayuntamiento` | 0 en código (el único comentario que nombraba la carpeta de copias normativas se reescribió) |
| `alcalde\|director\|contralor\|síndico` (autoridad por nombre de cargo) | 0 |
| `LOPPM`, `Concejo`, `MUNICIPAL` | Solo en el piso `LOPPM_ART87` de `PISOS` (ver abajo) |
| `15`, `90`, `365`, `days =`, `dias >` | Solo en `PISOS` (LOPPM 15 y 90) y en el cálculo genérico de `autorizacionesExigidas`, que lee el valor de la regla |
| «Autorización del Concejo» en el frontend | 0. La etiqueta sale de `regla.autorizaciones[].etiqueta` |
| `base_legal` en catálogo, UI o tipos | 0. La quitó D-AP-01; la base legal sale de `regla.pisos`/`fundamentos` |

## Clasificación de lo que queda

| Elemento | Dónde | Clase | Por qué no es hardcode institucional |
|---|---|---|---|
| `LOAP_DELEGACION` (gaceta, emisor delegante, avocación) | `service_asignacion_regla.PISOS` | LEGAL_MANDATORY | LOAP, G.O. 6.147 Ext. Por el art. 2 rige en la Administración nacional, estadal, distrital y municipal (verificado en la copia, p. 8). Versionado (`LOAP-2014`) y con fuente |
| `LEFP_COMISION` (un año) | `PISOS` | LEGAL_MANDATORY | LEFP, G.O. 37.522, arts. 1 y 72 (verificado en el texto). Rige en todo nivel |
| `LOPPM_ART87` (más de 15 días, autorización del Concejo Municipal; tope de 90) | `PISOS`, `niveles=("MUNICIPAL",)` | LEGAL_MANDATORY | LOPPM, G.O. 6.015 Ext., arts. 87 y 95.18 (verificado en la copia, p. 70). **Solo** se aplica a entes MUNICIPALES (M1 lo prueba) |
| No subdelegar, dependencia del delegado y solo competencias propias | `service_ocupacion.validar` (paso 8) | LEGAL_MANDATORY | LOAP arts. 34 y 35, nacional. Ya existían y no dependen del régimen |
| 6 figuras, grupo, cargo de origen y firma = FIRMAR | `models.FIGURAS_ASIGNACION`, `service_ocupacion.FIGURAS` | PLATFORM_INVARIANT | Taxonomía nacional estable (D-AP-01). Sus **reglas** viven en pisos y políticas |
| Un cargo no se designa a sí mismo; suplencia solo de un titular; nadie formaliza su propia ocupación | `service_asignacion_regla.verificar_emisor`, `service_ocupacion` | PLATFORM_INVARIANT | Integridad del dominio. La SoD configurable sigue en CTL-01 (D-AP-06) |
| Límite de días, fin obligatorio, medio, emisor, autorización, competencias permitidas, avocación y documentos | `gov_assignment_policies` | INSTITUTIONAL_POLICY | Los configura el ente, con versiones |
| Códigos `ASG-`/`FUN-`, etiquetas y textos de ayuda | Servicios y UI | OPERATIONAL_CONFIGURATION | No sustantivos |

## Resultado

| Indicador | Valor |
|---|---|
| ZERO_INSTITUTIONAL_HARDCODE | 1 |
| TENANT_CONFIGURABLE | 1 |
| NATIONAL_REUSABLE_PRODUCT | 1 |
| NAGUANAGUA_SPECIFIC_CODE | 0 |
| TENANT_SPECIFIC_CODE | 0 |
| HARDCODED_MUNICIPAL_POLICY_GLOBAL | 0 |
| HARDCODED_COUNCIL_AUTHORIZATION_GLOBAL | 0 |
| HARDCODED_INSTITUTIONAL_DEADLINES | 0 |
| HARDCODED_AUTHORITY_NAMES | 0 |
