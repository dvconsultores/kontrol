# ACCESIBILIDAD — N6

WCAG 2.2 AA · axe-core · **0 violaciones críticas o serias** atribuibles a N6.

## Un defecto real, encontrado por la propia prueba

La primera versión del selector usaba `role="listbox"` con elementos de lista
intercalados entre el contenedor y las opciones. Eso rompe la relación que el
lector de pantalla usa para anunciar «opción 2 de 3»: axe lo reportó como
`aria-required-children`, `aria-required-parent` y `listitem`.

Las opciones cuelgan ahora directamente del listbox, con `aria-activedescendant`
siguiendo el foco. El texto secundario —código y RIF— subió de contraste.

## Comprobado

| Aspecto | Resultado |
|---|---|
| Pantalla de selección de empresa | sin violaciones serias |
| Selector desplegado | sin violaciones serias |
| Etiqueta del botón | anuncia la empresa activa y su función |
| `aria-haspopup` / `aria-expanded` | correctos |
| Apertura con teclado | ↓, Enter o Espacio |
| Recorrido con teclado | ↑ ↓ |
| Selección con teclado | Enter o Espacio |
| Cierre | Escape, sin cambiar nada |
| Foco tras elegir o cerrar | vuelve al botón |
| Empresa activa distinguida | icono + `aria-selected` + peso tipográfico |
| Estados de carga y vacío | anunciados con `role="status"` |
| Error de lista | `role="alert"` con reintento |

## El foco

Devolverlo al botón después de elegir o cerrar no es un detalle: perderlo dejaría
a quien navega con teclado al principio del documento después de **cada** cambio
de empresa, obligándole a recorrer toda la cabecera otra vez.

## Sin depender del color

La empresa activa se marca con un icono y con `aria-selected`, además del peso
tipográfico. Distinguirla solo por color dejaría fuera a quien no lo percibe, y
en un selector de empresa equivocarse de fila tiene consecuencias.
