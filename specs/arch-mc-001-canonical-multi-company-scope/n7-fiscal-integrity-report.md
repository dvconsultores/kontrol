# INTEGRIDAD FISCAL — N7

Fiscal es donde una empresa equivocada deja de ser un problema de software: cada
empresa es un contribuyente distinto ante el SENIAT, con su RIF, sus series
autorizadas y sus libros.

## 1. La cadena, con referencia real en cada eslabón

| Entidad | Empresa | Estado |
|---|---|---|
| Configuración fiscal (`tax_profiles`) | directa | clave foránea real, obligatoria |
| Series de numeración (`fiscal_number_series`) | directa | clave foránea real, obligatoria |
| Lotes de control (`control_number_batches`) | directa | clave foránea real, obligatoria |
| Números de control (`control_numbers`) | directa | clave foránea real, obligatoria |
| Documentos fiscales (`fiscal_documents`) | directa | clave foránea real, obligatoria |
| Eventos de impresión (`print_events`) | derivada del documento | clave real y obligatoria |
| Notas de crédito y débito | directa | clave foránea real, obligatoria |
| Reglas de retención | directa | clave foránea real, obligatoria |
| Periodos y declaraciones | directa | clave foránea real, obligatoria |

Once tablas fiscales, todas con la empresa referenciada y obligatoria. Antes de
N7, todas eran texto suelto.

## 2. Lo que ahora rechaza PostgreSQL

| Intento | Resultado |
|---|---|
| Serie fiscal bajo una empresa inexistente | `23503` |
| Documento fiscal bajo el identificador del tenant | `23503` |
| Cualquier fila fiscal sin empresa | `23502` |

Comprobado con `INSERT` directo, sin pasar por la aplicación, verificando el
código de error concreto: que una inserción falle no significa nada si falla por
una columna mal escrita en vez de por la invariante que se quería demostrar.

## 3. Numeración

El correlativo de cada serie vive en `fiscal_number_series.next_number`, y la
serie pertenece a una empresa por clave foránea obligatoria. La numeración no
puede mezclarse entre empresas porque no hay forma de que una serie pertenezca a
dos.

Los números de control heredan la empresa de su lote, y ambos la llevan
explícita y referenciada.

## 4. Paridad de cálculo

N7 no toca ninguna fórmula, ninguna alícuota, ninguna base imponible ni ningún
total. Solo cambia de quién es cada fila y qué acepta la base.

La suite fiscal existente pasa sin modificaciones, que es la comprobación de
paridad: mismas entradas, mismos importes.

## 5. Lo que sigue en los servicios

Que un documento de la empresa A no se ampare con la serie de la B es una regla
sobre dos objetos que existen y son válidos por separado. Una clave foránea no
la expresa; la guarda de N5 sí, y sigue donde estaba con sus trece pruebas A/B.
