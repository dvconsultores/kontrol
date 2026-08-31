# MATRIZ DE NORMALIZACIÓN POR DOMINIO — N5

Estado real, verificado sobre PostgreSQL 18.6.

| Estado | Significado |
|---|---|
| `FUNCTIONALLY_NORMALIZED` | Escribe y lee la empresa real, y su aislamiento A/B está probado |
| `NORMALIZED_PENDING_AB_PROOF` | Escribe y lee la empresa real; falta la prueba A/B específica del dominio |
| `DEFERRED_TO_N9` | Hallazgo confirmado; su corrección pertenece a otra fase |

## 1. Dominios

| Dominio | Entidades | Escritura | Lectura | Auditoría | Aislamiento A/B | Estado |
|---|---:|---|---|---|---|---|
| **master_data** | 10 | empresa real | por contexto | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **purchasing** | 14 | empresa real | por contexto | sí | por dominio | `NORMALIZED_PENDING_AB_PROOF` |
| **inventory** | 11 | empresa real | por contexto | sí | por dominio | `NORMALIZED_PENDING_AB_PROOF` |
| **sales** | 8 | empresa real | por contexto | sí | por dominio | `NORMALIZED_PENDING_AB_PROOF` |
| **treasury** | 11 | empresa real | por contexto | sí | por dominio | `NORMALIZED_PENDING_AB_PROOF` |
| **fiscal** | 11 | empresa real | por contexto | sí | por dominio | `NORMALIZED_PENDING_AB_PROOF` |
| **regulatory** | 11 | empresa real | por contexto | sí | por dominio | `NORMALIZED_PENDING_AB_PROOF` |
| **reporting** | 2 | empresa real | por contexto | — | — | `NORMALIZED_PENDING_AB_PROOF` |
| **organization** | 8 | ya correcta (Spec 008) | ya correcta | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **approvals** | 4 | empresa del **cuerpo** | por tenant | sí | **fuga confirmada** | `DEFERRED_TO_N9` |
| **documents** | 8 | empresa real | **por tenant** | sí | **fuga confirmada** | `DEFERRED_TO_N9` |

## 2. Qué significa «por contexto»

Los ocho dominios de negocio pasaron en N2 de usar `actor.tenant_id` a usar
`ctx.company_id`, en 234 puntos. Eso los deja escribiendo y leyendo la empresa
real: verificado en `master_data` consultando PostgreSQL directamente, y por
construcción en el resto, ya que comparten el mismo `CompanyContext`.

Lo que distingue `FUNCTIONALLY_NORMALIZED` de `NORMALIZED_PENDING_AB_PROOF` no
es el código: es si existe una prueba A/B **de ese dominio**. Marcar como
probado lo que no se ha probado sería exactamente el error que este proyecto
viene corrigiendo.

## 3. Los dos diferidos

| Spec | Hallazgo | Comprobado |
|---|---|---|
| **046** | `_get_document` admite cualquier empresa del tenant | `UA` lee un documento de B con **200** |
| **045** | Toma la empresa del cuerpo sin contrastar el contexto | Operando en A se guarda una política en B |

Ambos por comportamiento, no leyendo el código, y con prueba que fallará el día
que se corrijan. Su fase es **N9**: tocarlos aquí reabriría dos Specs cerradas.

## 4. La clase de defecto que N5 añadió al barrido

N2 buscaba `company_id = tenant_id`. `deactivate_party` no lo tenía porque **no
acotaba en absoluto**: devolvía 200 al desactivar un tercero de otra empresa.

Un barrido específico de «rutas que cargan una entidad de empresa sin comprobar
la empresa» encontró 13 candidatas: 1 real en dominio normalizado —corregida— y
12 en las Specs diferidas.
