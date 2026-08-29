# NOTA DE CORRECCIÓN — CIFRA DE SPECS DESBLOQUEADAS POR D0

| Campo | Valor |
|---|---|
| Emitida en | Gate G0 · 2026-08-29 |
| Documentos corregidos | `D0-final-resolution.md` §11 · `D0-spec-dependencies.md` · `D0-impact-matrix.md` |
| Cifra anterior publicada | **13** (en el texto) y **17** (en la enumeración) |
| **Cifra correcta** | **22** |

## Qué estaba mal

La entrega de la Fase D0 contenía **tres cifras incompatibles** para la misma magnitud:

1. El texto de `D0-final-resolution.md` §11 decía «Las **13** que estaban bloqueadas».
2. La enumeración inmediatamente debajo listaba **17** Specs.
3. Las dos matrices de origen daban **21 cada una**, pero con conjuntos distintos.

Ninguna de las tres era correcta.

## Criterio aplicado para resolverla

> **Criterio G0-DEF.** Una Spec estaba bloqueada si una decisión D0 define un elemento de su
> **modelo de datos o de su máquina de estados** — algo que no puede añadirse después sin rehacer la
> Spec. Aprobación, reserva, ubicación, unidad de medida, presentación, estados de mercancía, vínculo
> documental, dimensiones organizacionales y evidencia documental son todos elementos de modelo.

Este criterio es el que ya enunciaba `D0-spec-dependencies.md` («escribirla sin la decisión
produciría un diseño que habría que rehacer, no meramente ajustar»); lo que faltaba era aplicarlo de
forma consistente en ambas matrices.

## Derivación

| Fuente | Cardinalidad | Conjunto |
|---|---:|---|
| `D0-spec-dependencies.md` | 21 | 007, 008, 011, 012, 015, 017, 018, **019**, 020, 021, 022, 025, 029, 030, 031, 032, 033, 034, 035, 045, 046 |
| `D0-impact-matrix.md` | 21 | 007, 008, 011, 012, 015, 017, 018, 020, 021, 022, **023**, 025, 029, 030, 031, 032, 033, 034, 035, 045, 046 |
| Solo en la primera | — | **019** |
| Solo en la segunda | — | **023** |
| **Unión** | **22** | ambas más los dos divergentes |

## Verificación de los dos elementos divergentes

Ambos resisten el criterio, de modo que la unión —y no la intersección— es la respuesta correcta:

**019 Recepción física.** `ADR-D0-004` R-D0-04-2 exige `location_id` con FK real en
`GoodsReceiptLine`; `ADR-D0-009` R-D0-09-1 exige unidad, presentación, factor y cantidad base en la
misma línea. Son cuatro columnas de modelo. Especificar la recepción sin ellas obliga a rehacerla.

**023 Núcleo de inventario y Kardex.** `ADR-D0-010` añade siete valores a `InventoryBalance.state`;
`ADR-D0-003` R-D0-03-3 y R-D0-03-5 añaden la dimensión de ubicación a `Reservation` y una restricción
de base de datos contra la sobre-reserva. Son modelo y máquina de estados, no ajuste.

## Conclusión

**22 Specs** estaban bloqueadas por decisión implícita y quedaron desbloqueadas al cerrar D0:

`007, 008, 011, 012, 015, 017, 018, 019, 020, 021, 022, 023, 025, 029, 030, 031, 032, 033, 034, 035, 045, 046`

Las **34** restantes (56 − 22) nunca estuvieron bloqueadas por una decisión D0.

## Lección de gobierno

Las dos matrices se construyeron desde la misma evidencia y llegaron a conjuntos distintos porque
ninguna declaró explícitamente su criterio de corte antes de aplicarlo. La corrección no consistió en
elegir una cifra sino en **fijar primero el criterio y volver a derivar**. Se incorpora como práctica:
toda matriz de gobierno debe enunciar su criterio de inclusión en su encabezado.
