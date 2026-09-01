# ESTADO DE S3 Y DE LA RETENCIÓN — N9

## 1. S3

| | |
|---|---|
| Requisito | `FR-046-032` — proveedor compatible con S3, sin acoplar a ningún fabricante |
| Prioridad | **P1** |
| Adaptador | Implementado |
| Servicio real disponible en este entorno | **No** |
| Estado | **`IMPLEMENTED_NOT_VERIFIED`** |
| Pruebas saltadas | **8** |
| Requisito obligatorio oculto por un salto | **0** |

`FR-046-032` es P1, así que S3 **no es obligatorio** para cerrar 046. Los ocho
saltos son legítimos y su mensaje lo dice sin adornos: *«la conformidad de este
adaptador queda SIN VERIFICAR en este entorno»*.

No se inventa una verificación. Montar un servicio para que un contador diga
«cero saltos» sería cambiar la medida en vez del sistema.

## 2. Sistema de ficheros

Es el proveedor operativo y **sí** se verifica de verdad: subida, lectura,
descarga, hash y detección de objeto alterado o ausente.

**`FILESYSTEM VERIFIED`**

## 3. Retención

| | |
|---|---|
| Requisito | `FR-046-065` — política de retención configurable por tipo |
| Prioridad | **P1** |
| Operación de purga | Implementada y probada (`test_una_version_referenciada_no_se_purga`) |
| Planificador periódico | No implementado |
| Dueño | Fuera de 046: corresponde a la Spec de instalación y actualización |

La purga existe y respeta lo que no debe borrarse. Lo que no hay es un
planificador que la ejecute sola, y eso no es requisito P0 de 046.

Se documenta con su dueño en lugar de esconderlo entre los completados.
