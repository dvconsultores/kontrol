# CRITERIOS DE ACEPTACIÓN — SPEC 012

Cada criterio es verificable por una prueba. Si no se puede probar, no es un
criterio.

## Catálogo y `P8`

| Id | Criterio |
|---|---|
| AC-012-01 | Una instalación recién creada tiene **0** condiciones de pago, **0** zonas, **0** canales, **0** listas y **0** políticas |
| AC-012-02 | `grep` de porcentajes, plazos o nombres de lista en el código del módulo devuelve **0** |
| AC-012-03 | La precedencia por defecto vive en **tabla**, no en código, y se puede reordenar |
| AC-012-04 | Una `DiscountPolicy` sin `max_percent` no impone límite ni pide aprobación |

## Listas y versiones

| Id | Criterio |
|---|---|
| AC-012-05 | Crear una versión asigna correlativo **del servidor**; el del cliente se ignora |
| AC-012-06 | Activar una versión que solapa vigencia con otra devuelve **409** |
| AC-012-07 | Editar los ítems de una versión `ACTIVE` se rechaza; hay que crear otra versión |
| AC-012-08 | Borrar una versión referenciada por un documento devuelve **409** con el número de referencias |
| AC-012-09 | Archivar una versión **conserva** sus ítems |
| AC-012-10 | Un precio se declara sobre una presentación; sin ella, no se acepta |

## Resolución — el corazón

| Id | Criterio |
|---|---|
| AC-012-11 | Con lista específica del cliente y lista general vigentes, gana la del cliente **según la precedencia declarada** |
| AC-012-12 | Reordenando la precedencia y repitiendo la consulta, **cambia el resultado** — la prueba de que es dato |
| AC-012-13 | La respuesta incluye siempre `price_source_version_id` |
| AC-012-14 | Dos reglas de igual precedencia y distinta vigencia: gana la más reciente |
| AC-012-15 | Dos reglas de igual precedencia y misma vigencia: gana el menor precio |
| AC-012-16 | Empate irresoluble → **422 `PRICE_PRECEDENCE_TIE`** con los candidatos |
| AC-012-17 | Sin lista aplicable → `resolved:false`, `unit_price:null`. **Nunca** cero |
| AC-012-18 | El precio se resuelve en la presentación pedida, convirtiendo con el motor de la Spec 011 |
| AC-012-19 | Un rango de volumen aplica solo dentro de su rango |
| AC-012-20 | La resolución de una empresa **nunca** ve listas de otra |

## Descuentos

| Id | Criterio |
|---|---|
| AC-012-21 | Descuento bajo el límite: `allowed:true`, sin aprobación |
| AC-012-22 | Descuento sobre el límite: `allowed:false`, `requires_approval:true`, **sin bloquear** |
| AC-012-23 | 012 **no** crea la solicitud: la abre el consumidor con el motor 045 |
| AC-012-24 | Descuento de línea y de documento se evalúan con políticas distintas |
| AC-012-25 | Políticas incompatibles declaradas no se acumulan |

## Snapshot e histórico — `P5`

| Id | Criterio |
|---|---|
| AC-012-26 | Aprobado un documento, **editar la lista no cambia** su precio |
| AC-012-27 | Aprobado un documento, **crear una versión nueva no cambia** su precio |
| AC-012-28 | El documento aprobado conserva la versión que produjo el precio y permite explicarlo sin consultar el maestro |
| AC-012-29 | `pricing_source` distingue `RESOLVED`, `MANUAL_JUSTIFIED` y `LEGACY_FREETEXT` |
| AC-012-30 | Un precio manual exige justificación; no se acepta en silencio |

## Fronteras

| Id | Criterio |
|---|---|
| AC-012-31 | `CommercialZone` y `WarehouseZone` son tablas distintas, **sin FK entre ellas** |
| AC-012-32 | No existe un catálogo de monedas propio: se referencia `currencies` |
| AC-012-33 | Condición de pago y método de pago siguen siendo cosas distintas |
| AC-012-34 | 012 no crea permisos, auditoría ni aprobaciones propias |
| AC-012-35 | 012 no emite eventos |

## Legado

| Id | Criterio |
|---|---|
| AC-012-36 | La migración de anotación crea **0** maestros y modifica **0** columnas heredadas |
| AC-012-37 | Una cadena ambigua queda `MANUAL_REVIEW_REQUIRED`, no convertida |
| AC-012-38 | El texto original se conserva íntegro en `legacy_value` |
| AC-012-39 | Los documentos históricos quedan `LEGACY_FREETEXT`, **sin snapshot inventado** |
| AC-012-40 | La migración informa el recuento por clase y es reversible sin pérdida |

## Plataforma

| Id | Criterio |
|---|---|
| AC-012-41 | Toda la aceptación se ejecuta sobre **PostgreSQL 18.x** |
| AC-012-42 | Ningún importe usa `float` |
| AC-012-43 | Sin violaciones serias de WCAG 2.2 AA en las cinco pantallas |
| AC-012-44 | Sin desbordamiento horizontal entre 320 y 1440 |
| AC-012-45 | Cross-browser en Chromium, Firefox y WebKit |

---

## Criterios multiempresa — posteriores a ARCH-MC-001

| Id | Criterio | Prueba |
|---|---|---|
| AC-012-MC-01 | Las once entidades declaran alcance; ninguna indeterminada | A-01 |
| AC-012-MC-02 | Las ocho directas tienen `company_id` obligatoria con FK a `companies` | A-02, B-01 |
| AC-012-MC-03 | Las tres derivadas declaran su ruta, obligatoria y con FK | A-03 |
| AC-012-MC-04 | Ninguna derivada lleva `company_id` redundante | A-04 |
| AC-012-MC-05 | El mismo código de lista existe en A y en B sin colisionar | B-03 |
| AC-012-MC-06 | El mismo código repetido dentro de A falla | B-04 |
| AC-012-MC-07 | Dos versiones `ACTIVE` de una lista no pueden solapar | B-05 |
| AC-012-MC-08 | Dos borradores **sí** pueden solapar | B-06 |
| AC-012-MC-09 | Contexto A con lista de B: `404` | N-02 |
| AC-012-MC-10 | Contexto A con lista de otro tenant: `404` | N-03 |
| AC-012-MC-11 | Usuario A+B en contexto A con lista de B: `404` | N-06 |
| AC-012-MC-12 | Versión de una lista ajena, con lista propia válida: `404` | N-08 |
| AC-012-MC-13 | Ninguna ruta acepta la empresa desde el cuerpo | A-07, E-07 |
| AC-012-MC-14 | La resolución es determinista y devuelve su versión | E-01, E-02 |
| AC-012-MC-15 | Sin lista aplicable declara ausencia; no devuelve cero | E-03 |
| AC-012-MC-16 | A y B resuelven distinto con la misma precedencia configurada distinta | E-04 |
| AC-012-MC-17 | Un documento aprobado no cambia al superar la versión | F-01 |
| AC-012-MC-18 | Ni al cambiar la tasa de cambio | F-03 |
| AC-012-MC-19 | Un aprobador de B no es elegible en una solicitud de A | G-04 |
| AC-012-MC-20 | Los once catálogos nacen vacíos | I-01 |
| AC-012-MC-21 | Ningún valor comercial aparece como literal en el código | I-02 |
| AC-012-MC-22 | Toda consulta de 012 queda separada por empresa en la caché | H-01 |
| AC-012-MC-23 | Formulario abierto en A, cambio a B, envío: no se convierte en B | H-03 |

Cada criterio de bloqueo debe fallar **por la frontera de empresa**. Si falla
por carga útil, por estado o por autenticación, no comprueba lo que dice.
