# MATRIZ DE NORMALIZACIÓN POR DOMINIO — N5

Estado al cierre de N5, verificado sobre PostgreSQL 18.6 con dos empresas del
mismo tenant.

| Estado | Significado |
|---|---|
| `FUNCTIONALLY_NORMALIZED` | Escribe y lee la empresa real, **y tiene suite A/B propia** |
| `NORMALIZED_PENDING_AB_PROOF` | Escribe y lee la empresa real; sin suite A/B propia |

## 1. Dominios

| Dominio | Entidades | Escritura | Lectura | Auditoría | Aislamiento A/B | Estado |
|---|---:|---|---|---|---|---|
| **master_data** | 10 | empresa real | por contexto | no audita | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **organization** | 8 | empresa real | por contexto | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **treasury** | 11 | empresa real | por contexto | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **purchasing** | 14 | empresa real | por contexto | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **sales** | 8 | empresa real | por contexto | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **inventory** | 11 | empresa real | por contexto | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **regulatory** | 11 | empresa real | por contexto | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **fiscal** | 11 | empresa real | por contexto | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **approvals** (045) | 4 | empresa real | por contexto | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **documents** (046) | 8 | empresa real | por contexto | sí | **probado** | `FUNCTIONALLY_NORMALIZED` |
| **reporting** | 2 | empresa real | por contexto | sí | por herencia | `NORMALIZED_PENDING_AB_PROOF` |

## 2. La única fila que no cierra, y por qué se dice

`reporting` no tiene escritura propia de negocio: sus consultas se apoyan en el
`CompanyContext` de los dominios que ya tienen evidencia. Pero **no tiene suite
A/B propia**, y marcarla como probada sería el error que este proyecto viene
corrigiendo: afirmar por construcción lo que no se ha verificado.

No bloquea `N5 COMPLETE` porque no introduce escritores ni lectores nuevos.
Queda anotada para que nadie la dé por cubierta sin mirarla.

## 3. Qué cambió respecto al checkpoint anterior

En el checkpoint previo, siete dominios figuraban como
`NORMALIZED_PENDING_AB_PROOF`. Eran los que escribían y leían bien pero nadie
había interrogado con dos empresas.

Al interrogarlos aparecieron **once defectos reales**, entre ellos dos
vulnerabilidades P0 en dominios que se daban por cerrados y una fuga de lectura
en el módulo que se citaba como referencia positiva.

## 4. Las dos Specs que estaban diferidas

| Spec | Hallazgo | Estado |
|---|---|---|
| **046** | El alcance admitía cualquier empresa del tenant | **CLOSED** |
| **045** | El cuerpo imponía la empresa; el listado no filtraba nada | **CLOSED** |

El cierre formal de 046 —los cuatro tipos de recurso, el 19/19, la
reconvergencia— sigue siendo N9. La vulnerabilidad no podía esperar; el trámite
sí.

## 5. La clase de defecto que N5 añadió al barrido

N2 buscaba el patrón `company_id = tenant_id`. `deactivate_party` no lo tenía
porque **no acotaba en absoluto**.

De ahí salieron dos familias de pruebas de arquitectura que buscan por
estructura, sobre el AST y las dependencias declaradas: la ruta que carga una
entidad por id sin contexto de empresa, y la ruta que deja al cuerpo elegir
dónde escribir. La segunda encontró `create_branch`, que ninguna prueba de
dominio había tocado.
