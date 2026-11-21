# Plan · BUD-02-CLASSIFIER-PARENT-LEVEL

1. **Backend (`service_presupuesto.py`).**
   - Añadir `NIVEL_RAIZ_PARTIDA` y `validar_padre_partida`.
   - Hacer que `_mapa_codigos_partidas` devuelva `(tipo, codigo) → nivel`.
   - En la importación, el lote guarda el nivel de cada fila validada.
   - `_validar_partida` delega en la regla y, en el alta, añade `field_errors.codigo_padre`.
2. **PG (`tests/test_gov_bud02_jerarquia.py`).**
   - Prueba unitaria de la regla.
   - El defecto: nivel 3 con padre de nivel 1.
   - Raíz, mismo nivel, salto, padre superior, inexistente y otro tipo.
   - Otro clasificador, otra versión aprobada y otra empresa.
   - CSV válido, inválido (salto, mismo nivel, padre de la base en otro nivel, orden) y atomicidad.
   - Árbol de 12 niveles.
3. **Mutaciones M1–M8** con un script fuera del repositorio.
4. **E2E** `gobierno-presupuesto-jerarquia.spec.ts`: alta inválida y corregida en la pantalla, CSV con salto rechazado entero y Axe a 1280, 390 y 320.
5. **Regresión.**
   - PG dirigida: BUD-01 a BUD-09, CNT-01, CNT-03, TRE-03, TRE-04 y TRE-09, catálogo de auditoría, OpenAPI y CTL-02.
   - E2E del presupuesto y humo.
   - PG completa.
6. **Cierre.** Roadmap (BUD-02 sin defecto), tarjeta UAT, auditoría de hardcode, registro de intentos y cierre.

**Frontend:** sin cambio funcional. El campo es de texto libre y el error del servidor ya se muestra bajo «Código superior».

**Único cambio de marcado:** la lista de errores del CSV pasa de `<ul role="alert">` a `<div role="alert"><ul>`. El Axe de la E2E lo detectó (`listitem`, seria). La regresión de Vitest pasa sin cambios (VITEST_MATERIAL_CHANGE=NO).
