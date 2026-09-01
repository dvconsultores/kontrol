# OBLIGATORIEDAD — N7

## 1. Qué se endureció

Nueve tablas de configuración de empresa admitían `company_id` nulo:
`attribute_definitions`, `costing_profiles`, `movement_types`, `presentations`,
`product_presentation_versions`, `product_templates`, `profile_versions`,
`service_templates`, `taxonomy_nodes`.

Se revisó **cada punto de creación** de las nueve. Todos fijan la empresa,
tomándola del contexto validado o del artículo padre. La columna era anulable
por inercia, no porque existiera un caso legítimo de ausencia.

## 2. Un método que falló primero

La primera medición fue un `grep` que contaba constructores multilínea como si
no fijaran la empresa, y daba cuatro falsos positivos. Se comprobó leyendo cada
sitio.

Merece quedar escrito porque la conclusión contraria —«hay código que crea filas
sin empresa»— habría llevado a dejar las nueve anulables por una razón
inexistente.

## 3. Las dos excepciones

| Tabla | Razón |
|---|---|
| `units_of_measure` | Spec 011 y `OQ-MC-01`: las unidades del sistema son globales y las de negocio de empresa. El nulo **es** esa distinción. |
| `stored_files` | Un archivo existe antes de saber a qué documento pertenecerá. |

Ambas conservan su clave foránea: una empresa nula es distinta de una empresa
inventada.

## 4. Sobre instalaciones con datos

En una instalación limpia no hay filas nulas que migrar. En una hipotética con
datos, `0035` fallaría en vez de inventarse una empresa — que es el
comportamiento correcto, y lo que la prueba del fixture hostil comprueba.

## 5. Resultado

| Medida | Valor |
|---|---:|
| Columnas revisadas | 11 |
| Endurecidas | 9 |
| Mantenidas anulables con razón escrita | 2 |
| Autoridades obligatorias todavía anulables | **0** |
