# CIERRE · CTL-05 (GOV-CTL-006, GOV-CTL-007) · 2026-11-11

- **Base:** `6e778a4` (origin; tiene integrado el trabajo de P2 `b73c171` y `6e778a4`).
- **Migración:** `0100_gov_ctl05_rendicion`, sobre `0099_quote_award` (P2). Es la cabeza única.
- **Menú:** Gobierno › Expedientes de cuenta.
- **API:** `/gobierno/rendicion/*`, 16 rutas.
- **Capacidades:** `gobierno_rendicion:view` (estándar), `:form` y `:qualify` (MFA).
- **Fuente:** Resolución CGR 01-00-000167 (N21). Leí el texto oficial. La calificación (art. 28) se **registra**; KONTROL no la calcula.

## Evidencia
| Puerta | Resultado |
|---|---|
| E2E Chromium `gobierno-rendicion.spec.ts` | 1/1 PASS |
| Backend CTL-05 en PostgreSQL (rn01..rn11) | 11/11 |
| Integración con P2 en PG (CTL-05, transversales, CTL-04, delegación, MFA, quote_award de P2) | 198/198 |
| Suite backend completa en PostgreSQL con analizador (`qa/suite_tiempos.py`) | 5321 en verde, 6 rojos |
| Alembic | instalación nueva PG, upgrade→downgrade→upgrade y `heads` = 1 |
| Paridad ORM/base (N10) | sin diferencias nuevas (la salida es idéntica a la de origin) |
| OpenAPI frente a origin `6e778a4` | +16 rutas y +7 esquemas `Rendicion*`; 0 retirados, 0 cambiados, 0 operaciones cambiadas |
| Fixtures (`qa/fixtures_de_frontend.py`) | solo altas |
| tsc, ESLint (todo el frontend) y build | PASS |
| Vitest completo | 1899 en verde, 23 rojos |
| Vitest de Gobierno, contratos y consumidores de fixtures tras la integración | 1086/1086 |
| mypy y ruff en los ficheros de CTL-05 | limpios |

**Detalle de la E2E:**
- **Recorrido:** menú, crear, incorporar 2 hechos reales (DOC-02 y ORG-04), reporte provisional, formar, PDF, snapshot inmutable ante un hecho posterior, integridad VALIDO, participación, calificación por otro usuario e historial.
- **Negativas:** otro ente da 404; incorporar a una cuenta formada da 409 `GOV_RENDITION_STATE`; una pieza inexistente da 404.
- **Accesibilidad:** Axe sin violaciones serias ni críticas.
- **Responsive:** 390 y 320 px sin desbordamiento.

**Suite backend completa, atribución medida en un worktree de origin:**
- los 5 rojos que quedan son preexistentes (pip check del entorno, N10, guarda de fechas sin zona y 2 de spec019);
- el sexto (techo de delegación, 151 frente a 154) es un recuento que CTL-05 cambia a propósito; se corrigió en C31.

**Vitest completo:** los 23 rojos son preexistentes en origin (importaciones 9, requisiciones 8, necesidades 5 y terceros 1).

## Defectos de producto que hallaron las pruebas (todos corregidos por DeepSeek)

1. **Formación de la cuenta:** el estado FORMADA se escribía antes que las huellas, y el CHECK de PostgreSQL lo rechazaba.
2. **Validación del contrato:**
   - la paginación devolvía un 422 genérico en vez de `GOV_RENDITION_INVALID_PAGE`;
   - el motivo de la nueva versión daba VALIDATION_ERROR en vez de `GOV_RENDITION_REASON_REQUIRED`.
3. **Integridad y PDF:**
   - el detalle de integridad devolvía un dict;
   - el PDF se regeneraba en vez de servir los bytes guardados;
   - las piezas sin documentos salían como SIN_EVIDENCIA.
4. **`/opciones`:** usaba `pos` sin definir.
5. **Listado:**
   - el filtro de período se aplicaba con OR en vez de solapamiento;
   - la lista no tenía semántica de lista.
6. **Migración (la vio la E2E):** faltaba el `server_default` de las fechas y había paridad incorrecta del tipo de versión.
7. **Documentos vinculados (la vio la E2E):** llegaban como tuplas a la consulta, y daban un 500.
8. **Huella de las piezas con documentos (la vio la E2E):** se calculaba sobre una lista distinta de la usada al verificar, y todas salían ALTERADA.
9. **Doble incorporación:** la lista no se refrescaba antes de reactivar el botón, y daba un 409.
10. **Fechas civiles:** se mostraban como instantes UTC, con riesgo de mostrar el día anterior en Caracas.
11. **Edición de cabecera:** no existía en la interfaz (laguna).
12. **Versión anterior:** se mostraba con el UUID como texto.

## Declarado

**Retoques mecánicos de Claude, sin semántica:**
- quitar la valla markdown exterior de C1;
- `ruff --fix` (orden de imports e imports sin uso);
- los RENAME de la migración, aplicados tal como los indicó DeepSeek.

**Regresión introducida por un retoque mecánico:** un `ruff --fix` quitó un import que usaba la API. DeepSeek lo corrigió en C4R.

**Fuera del alcance de CTL-05:**
- muestra CTL-04 y hallazgo CTL-06: no entran en la E2E como datos propios. Las piezas son eventos genéricos de la bitácora, y hallazgos y muestras entran por el mismo mecanismo; la prueba lo cubre con actos (DOC-02) y ocupación (ORG-04);
- SoD (CTL-01): las acciones de CTL-05 no se registran en su catálogo (PDD-CTL05-12);
- sin montos: no hay dominios monetarios en Gobierno;
- `_documentos_de_pieza` consulta dos veces los vínculos. Es ineficiente pero correcto.

## DeepSeek

- **Llamadas y coste:** 32 llamadas `deepseek-v4-pro`, aproximadamente $0,151.
- **Bloques rechazados:** 26 (C1 5, C2 2, C3 8, C4R 5, C5 4, C6 1 y C28 1). Todos se volvieron a pedir a DeepSeek; ninguno se arregló a mano.
- **Autoría:** todo el código y todas las pruebas son de DeepSeek.
- **Incidente del puente:** ver DEEPSEEK_BRIDGE_INCIDENT_CTL05.md. Tres intentos no llegaron a DeepSeek y no consumieron llamadas.

`OWNER_UAT_READY = YES · OWNER_UAT_ACCESSIBLE = YES (tras levantar la pila) · OWNER_ACCEPTED = NO`
