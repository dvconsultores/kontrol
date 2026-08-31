# REMEDIACIÓN DE SEGURIDAD — SPEC 046

`SECURITY REMEDIATION UNDER ARCH-MC-001` · No se ejecuta `/speckit.converge 046`.

## 1. Defecto

`P0 SECURITY — CROSS_COMPANY_DATA_LEAK`

Un usuario de la empresa A pedía un documento de la empresa B y recibía **200**.

## 2. Reproducción, antes del arreglo

```
GET /documentos/<documento de la empresa B>     contexto: empresa A
→ 200 con el documento completo
```

## 3. Causa

```python
def _company_ids(db, user):
    return [Company.id for Company where Company.tenant_id == user.tenant_id]
```

Todas las empresas del tenant. El comentario de `_get_document` ya decía la
intención correcta —«un documento de otra empresa se responde como
inexistente»— pero la implementación se había quedado en el mundo donde tenant
y empresa eran lo mismo. Era exacta cuando se escribió.

## 4. Corrección

El ayudante pasa a devolver la empresa del contexto validado, y solo esa.
Diecinueve rutas lo reciben. El cuerpo deja de designar la empresa en tipos,
categorías y documentos: se conserva el campo por compatibilidad, contradecirlo
es un error, y la entidad se construye siempre con la empresa del contexto.

## 5. Verificación

| Caso | Resultado |
|---|---|
| Documento propio | **200** |
| Documento de otra empresa | **404** |
| Listado documental | Sin documentos ajenos |
| Tipo documental ajeno usado para crear | **BLOCKED** |
| Listado de versiones ajeno | **BLOCKED** |
| Descarga del documento ajeno | **BLOCKED** |
| Descarga de una versión ajena | **BLOCKED** |
| Previsualización ajena | **BLOCKED** |
| Subir una versión a un documento ajeno | **BLOCKED** |
| Otro tenant | **404** |

**404 y no 403**: confirmar que el documento existe ya sería una filtración.

No se prueba solo el metadato. Bloquear el detalle y dejar abierta la descarga
sería cerrar la puerta y dejar la ventana: el contenido es justamente lo que
importa.

## 6. Alcance

Solo la lectura entre empresas. **No** se añaden los cuatro tipos de recurso
pendientes, **no** se cierra `REM-046-001`, **no** se reconverge 046, y no se
toca el almacenamiento, ClamAV, la retención ni S3.

**Regresión documental: sin fallos.**

Un fixture cambió, y merece explicación. `test_documents_security` creaba un
segundo tenant **sin ninguna empresa** y lo usaba como prueba de aislamiento.
Ese montaje no demuestra nada: ese usuario no ve documentos ajenos porque no
tiene dónde mirar, no porque el sistema lo separe. Ahora el segundo tenant tiene
empresa propia, que es el escenario donde el aislamiento se puede fallar de
verdad.

## 7. Estado

**`CLOSED`** en cuanto a la vulnerabilidad.

`REM-046-001` permanece **`BLOCKED_BY_ARCH_MC_001`**: le siguen faltando los
cuatro tipos de recurso, el 19/19 y la reconvergencia, que son N9.
