# Política de firmas

Caché validada por el preflight (CLEAN + EICAR + falso seguro) → se reutiliza; falta de alguna base o `--refrescar` → `freshclam`
(red; `database.clamav.net`); cada certificación registra motor y versión/fecha de `main`, `daily`, `bytecode` (`sigtool --info`);
sin base usable el preflight falla y la certificación no se declara. Las firmas (≈ 108 MB) y los `.deb` (15 MB) viven solo en el
prefijo de usuario: **no entran en Git** (CLAM-12 lo comprueba contra el índice). No se promete reproducibilidad bit a bit de la
base: se registra exactamente la usada (en esta certificación: main 63 · daily 28153 · bytecode 339).
