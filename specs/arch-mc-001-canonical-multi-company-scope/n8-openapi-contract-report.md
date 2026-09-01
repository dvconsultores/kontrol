# CONTRATO OPENAPI — N8

## 1. Antes y después

| | Antes | Después |
|---|---:|---:|
| Rutas | 294 | **294** |
| Operaciones que declaran la cabecera de empresa | **0** | **332** |
| Operaciones que no la declaran | 404 | 72 |

Ninguna ruta se perdió ni se añadió. Lo que cambió es que el contrato describe
algo que antes ocultaba.

## 2. El desajuste que se corrige

La cabecera funciona desde N1, la usan 112 pruebas y el frontend la envía desde
N6. Pero la dependencia la leía de `request.headers` en lugar de declararla como
parámetro, así que FastAPI no tenía forma de publicarla.

Un cliente escrito contra ese contrato habría recibido
`400 COMPANY_CONTEXT_REQUIRED` sin nada que le explicara por qué.

## 3. Las 72 que no la declaran

Autenticación, la propia lista de empresas —que es lo que se pide *antes* de
tener contexto—, instalación, licencia, salud y diagnóstico.

Una prueba comprueba las dos direcciones: que aparezca donde aplica y que **no**
aparezca donde no. Declararla en todas partes sería tan falso como no declararla
en ninguna.

## 4. Opcional, con la razón escrita

Se declara `required: false`. El servidor la resuelve solo cuando el usuario
puede operar en una sola empresa, y esa auto-resolución es una decisión de N1:
con una única empresa, exigir que se diga cuál sería pedir que se conteste una
pregunta con una sola respuesta posible.

La descripción publicada explica cuándo hace falta, qué error responde cada
situación, y termina con lo más importante: **la cabecera selecciona, no
concede**.

## 5. Una sola fuente

El valor viene del parámetro declarado. Una prueba de arquitectura comprueba que
nadie lo lea además de `request.headers`: dos lecturas del mismo dato serían dos
autoridades sobre la misma decisión, y tarde o temprano una se quedaría atrás.

## 6. Comprobado por comportamiento, no solo por contrato

| Caso | Resultado |
|---|---|
| Una empresa, sin cabecera | **200**, resuelta sola |
| Dos empresas, sin cabecera | **400 COMPANY_CONTEXT_REQUIRED** |
| Ruta que no es de empresa, sin cabecera | **200** |

El contrato y el runtime dicen lo mismo porque se comprueban los dos.
