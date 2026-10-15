# D7 · Propiedad de la limpieza
Una raíz **ajena** con el mismo prefijo (`kontrol-test-almacen-<otro>`) y un marcador dentro existe mientras corre el
proceso aislado; el proceso termina y limpia.
| Registro | Valor |
|---|---|
| La raíz ajena existía durante la corrida | sí |
| El proceso ve algo en **su** almacén | `[]` |
| La raíz ajena sigue tras la limpieza | **YES** (la limpieza usa la raíz exacta del stash, nunca un patrón) |
| La raíz propia desaparece | **YES** |
(Una ruta absoluta ajena sigue siendo alcanzable por el sistema de ficheros, como cualquier fichero del usuario: el
aislamiento es de espacio de nombres, no de permisos; lo que importa es que nadie la toca ni la lista como propia.)
